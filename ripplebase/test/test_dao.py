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

from decimal import Decimal as D
from datetime import datetime

from twisted.trial import unittest

from ripplebase.account.dao import *
from ripplebase import db


class DAOTest(unittest.TestCase):
    dao = None
    data = []  # dicts
    filter_kwargs = []  # dicts
#     update_args = []  # keys, kwargs tuples
    
    def setUp(self):
        if self.dao is None:
            raise unittest.SkipTest('Skipping superclass test.')
        db.reset(init_data=False)
        create_client_data()

    def tearDown(self):
        db.close()

    @classmethod
    def load_client(cls, fields):
        if isinstance(fields.get('client'), basestring):
            fields['client'] = db.query(Client).filter_by(
                name=fields['client']).one()        
        
    @classmethod
    def create(cls):
        "Install initial data."
        for fields in cls.data:
            fields = fields.copy()
            cls.load_client(fields)
            keys = [fields[key] for key in cls.dao.keys]
            if cls.dao.has_client_as_key:
                exists = cls.dao.exists(*keys, **dict(client=fields['client']))
            else:
                exists = cls.dao.exists(*keys)
            if not exists:
                cls.dao.create(**fields)
        db.commit()
        
    def test_create_and_get(self):
        "Create initial objects and get one at a time."
        self.create()
        for fields in self.data:
            fields = fields.copy()
            self.load_client(fields)
            keys = [fields[key] for key in self.dao.keys]
            if self.dao.has_client_as_key:
                obj = self.dao.get(*keys, **dict(client=fields['client']))
            else:
                obj = self.dao.get(*keys)
            for api_field in obj.db_fields:
                self.assertEquals(getattr(obj, api_field),
                                  fields[api_field])
            if self.dao.has_client_field:
                self.assertEquals(obj.data_obj.client, fields['client'])

    def test_filter(self):
        "Test filtering data by different criteria."
        self.create()
        for filter_kwargs in self.filter_kwargs:
            self.load_client(filter_kwargs)
            data_copy = self.data[:]
            for data_dict in data_copy:
                if self.dao.has_client_field:
                    self.load_client(data_dict)
                else:
                    if 'client' in data_dict:
                        del data_dict['client']

            # check that hits are correct
            for dao_inst in self.dao.filter(**filter_kwargs):
                data_dict = dao_inst.data_dict()
                if self.dao.has_client_field:
                    data_dict['client'] = dao_inst.data_obj.client
                for key, value in filter_kwargs.items():
                    self.assertEquals(data_dict[key], value)
                try:
                    data_copy.remove(data_dict)
                except ValueError, ve:
                    self.fail("Item found in filter not in initial data: %s."
                              "Error is: %s" % (data_dict, ve))
            # check that misses are correct too
            for data_dict in data_copy:  # remaining objects are misses
                # must fail to match at least one filter key
                match = True
                for key, value in filter_kwargs.items():
                    if data_dict[key] != value:
                        match = False
                        break
                if match:
                    self.fail("%s matches filter %s, but was not "
                              "in results." %
                              (data_dict, filter_kwargs))

    # *** to get update test to work, probably need a 'compare' function
    # that can be defined per-DAO to account for auto-updated fields
#     def test_update(self):
#         self.create()
#         for keys, kwargs in self.update_args:
#             dao = self.dao.get(*keys)
#             dao.update(**kwargs)
#             ...
                    

client_data = [
    {'name': u'test_client'},
    {'name': u'another_client'},
]

def create_client_data():
    for client in client_data:
        c = Client()
        c.name = client['name']
    db.flush()
    db.commit()

    
class AccountDAOTest(DAOTest):
    dao = AccountDAO

    data = [
        {'name': u'my_account',
         'relationship': 0,
         'owner': u'some guy',
         'is_active': True,
         'balance': D('0.00'),
         'upper_limit': D('100.00'),
         'lower_limit': D('-50.00'),
         'limits_effective_time': datetime(2008, 3, 10, 23, 21, 23, 945000),
         'limits_expiry_time': datetime(2008, 4, 10, 23, 21, 23, 945000),
         'client': client_data[0]['name']},

        {'name': u'other_account',
         'relationship': 0,
         'owner': u'some other guy',
         'is_active': True,
         'balance': D('10.00'),
         'upper_limit': D('10.00'),
         'lower_limit': D('-40.00'),
         'limits_effective_time': datetime(2007, 3, 10, 23, 21, 23, 945000),
         'limits_expiry_time': datetime(2008, 4, 20, 23, 21, 23, 945000),
         'client': client_data[1]['name']},

        {'name': u'good_account',
         'relationship': 1,
         'owner': u'good guy',
         'is_active': False,
         'balance': D('11.00'),
         'upper_limit': D('11.00'),
         'lower_limit': D('-41.00'),
         'limits_effective_time': datetime(2007, 3, 1, 23, 21, 23, 945000),
         'limits_expiry_time': datetime(2008, 4, 30, 23, 21, 23, 945000),
         'client': client_data[0]['name']},
    ]

    filter_kwargs = [
        {},
        {'name': u'my_account'},
        {'owner': u'some guy'},
        {'is_active': True},
        {'is_active': False, 'name': u'my_account',
         'owner': u'some guy'},
        {'client': client_data[0]['name']},
    ]
    
    @classmethod
    def create(cls):
        RelationshipDAO.create(id=cls.data[0]['relationship'])
        RelationshipDAO.create(id=cls.data[2]['relationship'])
        db.commit()
        super(AccountDAOTest, cls).create()


class AddressDAOTest(DAOTest):
    dao = AddressDAO

    data = [
        {'address': u'address0',
         'client': client_data[0]['name'],
         'owner': u'blabby blab',
         'accounts': []},  # empty nodes field
        {'address': u'address1',
         'client': client_data[0]['name'],
         'owner': u'cratchy cratch',
         'accounts': [AccountDAOTest.data[0]['name']]},
        {'address': u'address2',
         'client': client_data[1]['name'],
         'owner': u'abcdef',
         'accounts': [AccountDAOTest.data[1]['name']]},
        {'address': u'address3',
         'client': client_data[0]['name'],
         'owner': u'blabby blab',
         'accounts': [AccountDAOTest.data[2]['name']]},
        {'address': u'person',
         'client': client_data[0]['name'],
         'owner': u'r2d2',
         'accounts': [AccountDAOTest.data[0]['name'],
                      AccountDAOTest.data[2]['name']]}
    ]

    filter_kwargs = [
        {},
        {'address': u'address2'},
        {'address': u'person'},
        {'client': client_data[0]['name']},
        {'client': client_data[0]['name'],
         'address': u'address1'},
        # cannot query by accounts...
    ]

    @classmethod
    def create(cls):
        AccountDAOTest.create()
        super(AddressDAOTest, cls).create()

    def test_no_accounts(self):
        "Make sure it works with accounts left out."
        data = {'address': u'no_accounts',
                'client': client_data[0]['name'],
                'owner': u'xomdofj fjkls'}
        self.load_client(data)
        AddressDAO.create(**data)
        db.commit()
        data['accounts'] = []
        obj = AddressDAO.get(data['address'])
        data_dict = obj.data_dict()
        data_dict['client'] = obj.data_obj.client
        self.assertEquals(data_dict, data)

        
# *** do some DAO tests with invalid fields
        
# *** do some addresses with faulty data
# (mismatched node and address client)
# or does this not matter at this layer?
        
class AccountRequestDAOTest(DAOTest):
    dao = AccountRequestDAO

    data = [
        {'relationship': 0,  # get id later
         'source_address': u'address0',
         'dest_address': u'address1',
         'note': u"Hey\n\nwhat's up?"},
    ]

    filter_kwargs = [
        {},
        {'relationship': 0},
        {'relationship': 1},
        {'source_address': u'address0'},
        {'dest_address': u'address1'},
        {'dest_address': u'address0'},
        {'source_address': u'address0', 'dest_address': u'address1'},
        {'source_address': u'address0', 'dest_address': u'bunk'},
    ]
    
    @classmethod
    def create(cls):
        AddressDAOTest.create()
        super(AccountRequestDAOTest, cls).create()

class ExchangeRateDAOTest(DAOTest):
    dao = ExchangeRateDAO

    data = [
        {'name': u'USDCAD',
         'client': client_data[0]['name'],
         'value': D('1.0244'),
         'effective_time': datetime(2008, 3, 10, 23, 21, 23, 945000),
         'expiry_time': datetime(2008, 3, 11, 23, 21, 23, 945000),}
    ]

    filter_kwargs = [
        {},
        {'name': u'USDCAD'},
        {'name': u'CADUSD'},
    ]

    @classmethod
    def create(cls):
        super(ExchangeRateDAOTest, cls).create()
        
class ExchangeDAOTest(DAOTest):
    dao = ExchangeDAO

    data = [
        {'source_account': AccountDAOTest.data[0]['name'],
         'target_account': AccountDAOTest.data[2]['name'],
         'rate': ExchangeRateDAOTest.data[0]['name'],
         'client': client_data[0]['name']}
    ]
    
    filter_kwargs = [
        {},
        {'source_account': u'bleh',
         'target_account': AccountDAOTest.data[2]['name']},
        {'source_account': u'blah'},
        {'source_account': AccountDAOTest.data[0]['name']},
        {'target_account': AccountDAOTest.data[2]['name']},
        {'source_account': AccountDAOTest.data[0]['name'],
         'target_account': AccountDAOTest.data[2]['name']},
    ]

    @classmethod
    def create(cls):
        AccountDAOTest.create()
        ExchangeRateDAOTest.create()
        super(ExchangeDAOTest, cls).create()
        
