##################
# Copyright 2008, Ryan Fugger
#
# This file is part of Ripplebase.
#
# Ripplebase is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as 
# published by the Free Software Foundation, either version 3 of the 
# License, or (at your option) any later version.
#
# Ripplebase is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public 
# License along with Ripplebase, in the file LICENSE.txt.  If not,
# see <http://www.gnu.org/licenses/>.
##################

import sys

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker

from ripplebase import settings

DB_ECHO = settings.DEBUG

# Global metadata
meta = MetaData()

engine = create_engine(settings.DB_CONNECT_STR, echo=DB_ECHO)
session = scoped_session(sessionmaker(bind=engine,
                                      autoflush=False,
                                      autocommit=False,
                                      autoexpire=False))
mapper = session.mapper

SESSION_METHODS = (
    'save', 'flush', 'delete', 'expunge', 'update', 'save_or_update',
    'query', 'clear', 'execute', 'begin', 'commit', 'close',
)

# Make each session method a method of this module.
for session_method in SESSION_METHODS:
    # sys.modules[__name__] is this module!  Python is great, but strange sometimes.
    setattr(sys.modules[__name__], session_method, getattr(session, session_method))


def reset(drop=True, init_data=True):
    "Recreate all tables."
    engine.echo = False
    # make sure tables are loaded into metadata
    import ripplebase.account.tables
    import ripplebase.payment.tables
    assert meta.tables != {}, "Make sure to import ripplebase.db, not just db."
    if drop:
        meta.drop_all(bind=engine)
    meta.create_all(bind=engine)
    engine.echo = DB_ECHO
    
    # *** install a default client until multi-client support is ready
    if init_data:
        from ripplebase.account.mappers import Client
        test_client = Client()
        test_client.name=settings.TEST_CLIENT
        commit()
        # *** also install default units
        from ripplebase.account.dao import UnitDAO
        UnitDAO.create(name=u'CAD')
        UnitDAO.create(name=u'USD')
        commit()
        
class SimpleDAO(object):
    """Base class for DAOs.  Handles mapping API fields to
    DB fields in the local object.
    """
    # Define these in subclasses
    model = None  # an sqlalchemy mapper
    db_fields = {}  # api_field: db_field
    keys = []  # api_field
    
    def __init__(self, data_obj):
        self.data_obj = data_obj

    def __repr__(self):
        return repr(self.data_dict())
        
    @classmethod
    def create(cls, **kwargs):
        data_obj = cls.model()
        dao = cls(data_obj)
        dao.update(**kwargs)
        return dao
    
    def __setattr__(self, attr, value):
        if attr in self.db_fields:
            setattr(self.data_obj, self.db_fields[attr], value)
        else:
            super(SimpleDAO, self).__setattr__(attr, value)

    def __getattr__(self, attr):
        if attr in self.db_fields:
            return getattr(self.data_obj, self.db_fields[attr], None)
        else:
            raise AttributeError("'%s' object has no attribute '%s'." %
                                 (self.__class__, attr))

    @classmethod
    def _query(cls, *keys, **kwargs):
        """Returns APIQuery containing result.
        kwargs contains extra non-DAO-key arguments to filter."""
        kwargs.update(**dict(zip(cls.keys, keys)))
        return cls.filter(**kwargs)
    
    @classmethod
    def get(cls, *keys, **kwargs):
        data_obj = cls._query(*keys, **kwargs).query.one()
        return cls(data_obj)

    @classmethod
    def exists(cls, *keys, **kwargs):
        return cls._query(*keys, **kwargs).query.first() is not None
    
    @classmethod
    def delete(cls, *keys, **kwargs):
        data_obj = cls._query(*keys, **kwargs).query.one()
        delete(data_obj)

    @classmethod
    def _api_to_db(cls, **kwargs):
        "Converts DAO field names to DB field names, leaving unknown names alone."
        return dict([(cls.db_fields.get(api_field, api_field), value)
                     for api_field, value in kwargs.items()])
        
    @classmethod
    def filter(cls, **kwargs):
        "Can pass both DAO field names and extra DB field names as params."
        q = query(cls.model)
        if kwargs:
            q = q.filter_by(**cls._api_to_db(**kwargs))
        return APIQuery(cls, q)
        
    def data_dict(self):
        "Expose API data as a dict."
        return dict([(api_field, getattr(self, api_field))
                     for api_field in self.db_fields.keys()])

    def update(self, **kwargs):
        for field, value in kwargs.items():
            setattr(self, field, value)
        flush()
        

class DAO(SimpleDAO):
    """Adds ability to map API fields representing keys
    to other objects to those objects across FK relationships.
    Only works for relationships to DAOs with a single "primary" key.
    """
    # api_field: dao_class (DAO must have single api key)
    fk_daos = {}
    m2m_daos = {}

    def _get_foreign_dao(self, dao_class, *keys):
        if keys[0] is not None:
            return dao_class.get(*keys)
        else:
            return None
    
    def __setattr__(self, attr, value):
        if attr in self.fk_daos:
            # get FK DAO by API key
            dao = self._get_foreign_dao(self.fk_daos[attr], value)
            # set FK relation field to foreign data_obj
            setattr(self.data_obj, self.db_fields[attr],
                    getattr(dao, 'data_obj', None))
        elif attr in self.m2m_daos:
            dao_class = self.m2m_daos[attr]
            setattr(self.data_obj, attr, [])
            # *** inefficient to get foreign objects one at a time
            #     better to get all at once
            for key in value:  # value is list of m2m DAO keys
                dao = self._get_foreign_dao(dao_class, key)
                getattr(self.data_obj, attr).append(dao.data_obj)
        else:  # set like regular attribute
            super(DAO, self).__setattr__(attr, value)

    def __getattr__(self, attr):
        if attr in self.fk_daos:
            fk_obj = getattr(self.data_obj, self.db_fields[attr])
            if fk_obj:
                dao_key = get_dao_key_db_field(self.fk_daos[attr])
                return getattr(fk_obj, dao_key)
            else:
                return None
        elif attr in self.m2m_daos:
            dao_key = get_dao_key_db_field(self.m2m_daos[attr])
            return [getattr(data_obj, dao_key)
                    for data_obj in getattr(self.data_obj, attr)]
        else:
            return super(DAO, self).__getattr__(attr)

    @classmethod
    def filter(cls, **kwargs):
        key_set = set(kwargs.keys())
        # check for m2m fields
        m2m_fields = key_set.intersection(set(cls.m2m_daos.keys()))
        if m2m_fields:
            raise ValueError('M2M fields not implemented in filter: %s' %
                             m2mfields)
        fk_fields = key_set.intersection(set(cls.fk_daos.keys()))
        if fk_fields:
            # filter simple fields first
            simple_kwargs = kwargs.copy()
            fk_fields_to_query = []
            for fk_field in fk_fields:
                if kwargs[fk_field] is not None:
                    del simple_kwargs[fk_field]
                    fk_fields_to_query.append(fk_field)
            q = super(DAO, cls).filter(**simple_kwargs)
            # process fk joins
            for fk_field in fk_fields_to_query:
                dao_class = cls.fk_daos[fk_field]
                # filter_db_field is like 'Client.name',
                # where 'name' is the key for ClientDAO
                filter_db_field = getattr(
                    dao_class.model, get_dao_key_db_field(dao_class))
                q = q.join(cls.db_fields[fk_field], aliased=True).filter(
                    filter_db_field==kwargs[fk_field])
            return q
        else:
            return super(DAO, cls).filter(**kwargs)
    
def get_dao_key_db_field(DAO):
    return DAO.db_fields[DAO.keys[0]]

class RippleDAO(DAO):
    """Adds client-awareness.  Client field is special because it is
    implicit in client requests, and so must be injected by
    request handler.  For this reason, can use synthetic DB key for client
    instead of natural key, therefore need to handle this specially in
    the DAO.
    
    Users of this class must check for required client fields and keys and
    use it appropriately.  For example, when there is a client field, even
    only in a related object, you must pass it in to create as a kwarg.
    When the client field is a key, you must pass it in to get, etc.
    """
    has_client_field = False
    has_client_as_key = False

    @classmethod
    def create(cls, **kwargs):
        data_obj = cls.model()
        if cls.has_client_field:
            data_obj.client = kwargs['client']
        dao = cls(data_obj)
        dao.update(**kwargs)
        return dao

    def update(self, **kwargs):
        if 'client' in kwargs:
            self.client = kwargs['client']
            del kwargs['client']
        super(RippleDAO, self).update(**kwargs)
    
#     def __setattr__(self, attr, value):
#         if attr == 'client' and self.has_client_field:
#             setattr(self.data_obj, attr, value)
#         else:
#             super(RippleDAO, self).__setattr__(attr, value)

#     def __getattr__(self, attr):
#         if attr == 'client' and self.has_client_field:
#             return getattr(self.data_obj, attr)
#         else:
#             return super(RippleDAO, self).__getattr__(attr)

    def _get_foreign_dao(self, dao_class, *keys):
        "Be aware of foreign DAOs with Client fields."
        if getattr(dao_class, 'has_client_as_key', False) and keys[0] is not None:
            return dao_class.get(*keys, **dict(client=self.client))
        else:
            return super(RippleDAO, self)._get_foreign_dao(dao_class, *keys)

    def __getattr__(self, attr):
        if attr == 'client':
            return self.data_obj.client
        else:
            return super(RippleDAO, self).__getattr__(attr)

class APIQuery(object):
    """Wrapper for SQLAlchemy Query, returns DAO objects
    during iteration."""
    def __init__(self, dao_class, query):
        self.dao_class = dao_class
        self.query = query
        self._query_iter = None

    def __getattr__(self, attr):
        "Pass through function calls to self.query."
        # define a function that modifies self.query, returns self
        def db_wrapper_fcn(*args, **kwargs):
            self.query = getattr(self.query, attr)(*args, **kwargs)
            return self
        return db_wrapper_fcn

    def __iter__(self):
        "Initialize iteration over query."
        self._query_iter = self.query.__iter__()
        return self

    def next(self):
        """Return next object in query iteration,
        packaged in dao_class."""
        return self.dao_class(self._query_iter.next())

    def __getitem__(self, n):
        return self.dao_class(self.query[n])

    def one(self):
        "Return first element, raising exception if none exists."
        return self.dao_class(self.query.one())

    def first(self):
        "Return first element, or None if none exists."
        obj = self.query.first()
        return obj and self.dao_class(obj)
