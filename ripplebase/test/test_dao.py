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
                    print data_dict
                    self.fail(ve)
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

class NodeDAOTest(DAOTest):
    dao = NodeDAO

    data = [
        {'name': u'my_name',
         'client': ClientDAOTest.data[0]['name']},
        {'name': u'other_node',
         'client': ClientDAOTest.data[1]['name']},
        {'name': u'good_node',
         'client': ClientDAOTest.data[0]['name']},
    ]

    filter_kwargs = [
        {},
        {'name': u'my_name'},
        {'client': ClientDAOTest.data[0]['name']},
        {'name': u'other_node',
         'client': ClientDAOTest.data[1]['name']},
    ]

    def setUp(self):
        super(NodeDAOTest, self).setUp()
        ClientDAOTest.create()

    
class AddressDAOTest(DAOTest):
    dao = AddressDAO

    data = [
        {'address': u'node1',
         'client': NodeDAOTest.data[0]['client'],
         'nodes': [NodeDAOTest.data[0]['name']]},
        {'address': u'node2',
         'client': NodeDAOTest.data[1]['client'],
         'nodes': [NodeDAOTest.data[1]['name']]},
        {'address': u'node3',
         'client': NodeDAOTest.data[2]['client'],
         'nodes': [NodeDAOTest.data[2]['name']]},
        {'address': u'person',
         'client': NodeDAOTest.data[0]['client'],
         'nodes': [NodeDAOTest.data[0]['name'],
                   NodeDAOTest.data[2]['name']]}
    ]

    filter_kwargs = [
        {},
        {'address': u'node2'},
        {'address': u'person'},
        {'client': ClientDAOTest.data[0]['name']},
        {'client': ClientDAOTest.data[0]['name'],
         'address': u'node1'},
        # cannot query by nodes...
    ]

    def setUp(self):
        super(AddressDAOTest, self).setUp()
        ClientDAOTest.create()
        NodeDAOTest.create()

# *** do some DAO tests with invalid fields
        
# *** do some addresses with faulty data
# (mismatched node and address client)
# or does this not matter at this layer?

class AccountDAOTest(DAOTest):
    dao = AccountDAO

    data = [
        {'name': u'my_account',
         'node': NodeDAOTest.data[0]['name'],
         'balance': D('0.00'),
         'upper_limit': D('100.00'),
         'lower_limit': D('-50.00'),
         'limits_effective_time': datetime(2008, 3, 10, 23, 21, 23, 945000),
         'limits_expiry_time': datetime(2008, 3, 11, 23, 21, 23, 945000)}
    ]

    def setUp(self):
        super(AccountDAOTest, self).setUp()
        ClientDAOTest.create()
        NodeDAOTest.create()
        
