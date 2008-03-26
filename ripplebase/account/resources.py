from twisted.web import resource

from ripplebase.resource import (ObjectListResource, ObjectResource,
                                 ClientFieldAwareObjectListResource,
                                 ClientFieldAwareObjectResource)
from ripplebase.account.dao import *

class NodeListResource(ClientFieldAwareObjectListResource):
    DAO = NodeDAO
node_list = NodeListResource()

class NodeResource(ClientFieldAwareObjectResource):
    allowedMethods = ('GET', 'DELETE')  # can't post modifications to node
    DAO = NodeDAO
node = NodeResource()
    
class AddressListResource(ClientFieldAwareObjectListResource):
    DAO = AddressDAO
address_list = AddressListResource()
class AddressResource(ClientFieldAwareObjectResource):
    DAO = AddressDAO
address = AddressResource()

class AccountListResource(ObjectListResource):
    DAO = AccountDAO
account_list = AccountListResource()
class AccountResource(ObjectResource):
    DAO = AccountDAO
account = AccountResource()

# class ExchangeResource(ObjectListResource):
#     DAO = ExchangeDAO
# acct_root.putChild('exchange', ExchangeResource())
