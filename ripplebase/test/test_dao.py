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
    data = []
    filter_kwargs = []
    
    def setUp(self):
        if self.dao is None:
            raise unittest.SkipTest('Skipping superclass test.')
        db.reset(init_data=False)

    def tearDown(self):
        db.close()
        
    @classmethod
    def create(cls):
        "Install initial data."
        for fields in cls.data:
            cls.dao.create(**fields)
        db.commit()
        
    def test_create_and_get(self):
        "Create initial objects and get one at a time."
        self.create()
        for fields in self.data:
            keys = [fields[key] for key in self.dao.keys]
            obj = self.dao.get(*keys)
            for api_field in obj.db_fields:
                if api_field not in fields:
                    self.assertEquals(getattr(obj, api_field),
                                  fields[api_field])

    def test_filter(self):
        "Test filtering data by different criteria."
        self.create()
        for filter_kwargs in self.filter_kwargs:
            data_copy = self.data[:]
            # check that hits are correct
            for dao_inst in self.dao.filter(**filter_kwargs):
                data_dict = dao_inst.data_dict()
                for key, value in filter_kwargs.items():
                    self.assertEquals(data_dict[key], value)
                try:
                    data_copy.remove(data_dict)
                except ValueError, ve:
                    self.fail("Item found in filter not in initial data: %s."
                              "Error is: %s" % (data_dict, ve))
            # check that misses are correct too
            for data_dict in data_copy:  # remaining objects are misses
                # must not match at least one filter key
                match = True
                for key, value in filter_kwargs.items():
                    if data_dict[key] != value:
                        match = False
                        break
                if match:
                    self.fail("%s matches filter %s, but was not "
                              "in results." %
                              (data_dict, filter_kwargs))
                
class ClientDAOTest(DAOTest):
    dao = ClientDAO
    
    data = [
        {'name': u'test_client'},
        {'name': u'another_client'},
    ]

    filter_kwargs = [{}] + data

address_data = [
    {'address': u'address1',
     'client': ClientDAOTest.data[0]['name']},
    {'address': u'address2',
     'client': ClientDAOTest.data[1]['name']},
    {'address': u'address3',
     'client': ClientDAOTest.data[0]['name']},
]
    
class NodeDAOTest(DAOTest):
    dao = NodeDAO

    data = [
        {'name': u'my_name',
         'client': ClientDAOTest.data[0]['name'],
         'addresses': []},  # empty addresses
        {'name': u'other_node',
         'client': ClientDAOTest.data[1]['name'],
         'addresses': [address_data[1]['address']]},
        {'name': u'good_node',
         'client': ClientDAOTest.data[0]['name'],
         'addresses': [address_data[0]['address']]},
        {'name': u'nodeynode',
         'client': ClientDAOTest.data[0]['name'],
         'addresses': [address_data[0]['address'],
                       address_data[2]['address']]},
    ]

    filter_kwargs = [
        {},
        {'name': u'my_name'},
        {'client': ClientDAOTest.data[0]['name']},
        {'name': u'other_node',
         'client': ClientDAOTest.data[1]['name']},
    ]

    @classmethod
    def create(cls):
        ClientDAOTest.create()
        for data in address_data:
            AddressDAO.create(**data)
        super(NodeDAOTest, cls).create()

    def test_no_addresses(self):
        "Make sure it works with addresses left out."
        ClientDAOTest.create()
        data = {'name': u'no_addresses',
                'client': NodeDAOTest.data[0]['client']}
        NodeDAO.create(**data)
        data['addresses'] = []
        obj = NodeDAO.get(data['name'])
        self.assertEquals(obj.data_dict(), data)

    def test_address_nodes(self):
        "Make sure new addresses come up on nodes."
        self.create()
        address_nodes = {
            address_data[0]['address']: [self.data[2]['name'],
                                         self.data[3]['name']],
            address_data[1]['address']: [self.data[1]['name']],
            address_data[2]['address']: [self.data[3]['name']],
        }
        for address, nodes in address_nodes.items():
            obj = AddressDAO.get(unicode(address))
            self.assertEquals(obj.nodes, nodes)

node_data = [
    {'name': u'my_name',
     'client': ClientDAOTest.data[0]['name']},
    {'name': u'other_node',
     'client': ClientDAOTest.data[1]['name']},
    {'name': u'good_node',
     'client': ClientDAOTest.data[0]['name']},
]
    
class AddressDAOTest(DAOTest):
    dao = AddressDAO

    data = [
        {'address': u'address0',
         'client': node_data[0]['client'],
         'nodes': []},  # empty nodes field
        {'address': u'address1',
         'client': node_data[0]['client'],
         'nodes': [node_data[0]['name']]},
        {'address': u'address2',
         'client': node_data[1]['client'],
         'nodes': [node_data[1]['name']]},
        {'address': u'address3',
         'client': node_data[2]['client'],
         'nodes': [node_data[2]['name']]},
        {'address': u'person',
         'client': node_data[0]['client'],
         'nodes': [node_data[0]['name'],
                   node_data[2]['name']]}
    ]

    filter_kwargs = [
        {},
        {'address': u'address2'},
        {'address': u'person'},
        {'client': ClientDAOTest.data[0]['name']},
        {'client': ClientDAOTest.data[0]['name'],
         'address': u'address1'},
        # cannot query by nodes...
    ]

    @classmethod
    def create(cls):
        ClientDAOTest.create()
        for data in node_data:
            NodeDAO.create(**data)
        super(AddressDAOTest, cls).create()

    def test_no_nodes(self):
        "Make sure it works with nodes left out."
        ClientDAOTest.create()
        data = {'address': u'no_nodes',
                'client': node_data[0]['client']}
        AddressDAO.create(**data)
        data['nodes'] = []
        obj = AddressDAO.get(data['address'])
        self.assertEquals(obj.data_dict(), data)

    def test_node_addresses(self):
        "Make sure new addresses come up on nodes."
        self.create()
        node_addresses = {
            node_data[0]['name']: [self.data[1]['address'],
                                   self.data[4]['address']],
            node_data[1]['name']: [self.data[2]['address']],
            node_data[2]['name']: [self.data[3]['address'],
                                   self.data[4]['address']],
        }
        for node, addresses in node_addresses.items():
            obj = NodeDAO.get(node)
            self.assertEquals(obj.addresses, addresses)
        
# *** do some DAO tests with invalid fields
        
# *** do some addresses with faulty data
# (mismatched node and address client)
# or does this not matter at this layer?

class AccountDAOTest(DAOTest):
    dao = AccountDAO

    data = [
        {'name': u'my_account',
         'relationship': 0,
         'node': NodeDAOTest.data[0]['name'],
         'balance': D('0.00'),
         'upper_limit': D('100.00'),
         'lower_limit': D('-50.00'),
         'limits_effective_time': datetime(2008, 3, 10, 23, 21, 23, 945000),
         'limits_expiry_time': datetime(2008, 3, 11, 23, 21, 23, 945000)}
    ]

    def create(cls):
        NodeDAOTest.create()

        # *** ought to create relationship automatically in DAO if not in data
        from ripplebase.account.tables import RELATIONSHIP_STATUS
        RelationshipDAO.create(id=cls.data[0]['relationship'],
                               status=RELATIONSHIP_STATUS['invited'])
        
        super(AccountDAOTest, cls).create()
        
