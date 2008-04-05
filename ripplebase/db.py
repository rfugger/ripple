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
                                      transactional=True))
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
    import ripplebase.account.tables  # *** payment tables later
    if drop:
        meta.drop_all(bind=engine)
    meta.create_all(bind=engine)
    engine.echo = DB_ECHO
    
    # *** install a default client until multi-client support is ready
    if init_data:
        from ripplebase.account.dao import ClientDAO
        ClientDAO.create(name=settings.TEST_CLIENT)
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
            return getattr(self.data_obj, self.db_fields[attr])
        else:
            raise AttributeError("'%s' object has no attribute '%s'." %
                                 (self.__class__, attr))

    @classmethod
    def _get_data_obj(cls, *keys):
        return cls.filter(**dict(zip(cls.keys, keys))).query.one()
    
    @classmethod
    def get(cls, *keys):
        data_obj = cls._get_data_obj(*keys)
        return cls(data_obj)
    
    @classmethod
    def delete(cls, *keys):
        data_obj = cls._get_data_obj(*keys)
        delete(data_obj)

    @classmethod
    def _api_to_db(cls, **kwargs):
        return dict([(cls.db_fields[api_field], value)
                     for api_field, value in kwargs.items()])
        
    @classmethod
    def filter(cls, **kwargs):
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
            # check that field is valid
            assert field in self.db_fields.keys(), \
                "Invalid field: '%s'." % field
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
    
    def __setattr__(self, attr, value):
        if attr in self.fk_daos:
            # get FK DAO by API key
            dao = self.fk_daos[attr].get(value)
            # set FK relation field to foreign data_obj
            setattr(self.data_obj,
                    self.db_fields[attr],
                    dao.data_obj)
        elif attr in self.m2m_daos:
            dao_class = self.m2m_daos[attr]
            setattr(self.data_obj, attr, [])
            for key in value:  # value is list of m2m DAO keys
                dao = dao_class.get(key)
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
            for fk_field in fk_fields:
                del simple_kwargs[fk_field]
            q = super(DAO, cls).filter(**simple_kwargs)
            # process fk joins
            for fk_field in fk_fields:
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
