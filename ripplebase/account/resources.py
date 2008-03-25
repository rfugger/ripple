from twisted.web import resource

from ripplebase.resource import ObjectListResource, ObjectResource
from ripplebase.account.dao import *

class NodeListResource(ObjectListResource):
    DAO = NodeDAO

    def create(self, data_dict):
        "Add client key to data_dict."
        from ripplebase import settings
        data_dict['client'] = settings.TEST_CLIENT
        super(NodeListResource, self).create(data_dict)

    def filter(self):
        # *** replace with actual client
        from ripplebase import settings
        client = settings.TEST_CLIENT
        for obj in self.DAO.filter(client=client):
            d = obj.data_dict()
            del d['client']
            yield d
node_list = NodeListResource()

class NodeResource(ObjectResource):
    """Nodes don't need to report their client since
    only that client could be making this request,
    and it knows who it is already.
    """
    allowedMethods = ('GET', 'DELETE')
    DAO = NodeDAO

    def get(self, request, key):
        "Restrict to calling client; remove client field."
        # *** replace with actual client
        from ripplebase import settings
        client = settings.TEST_CLIENT
        d = super(NodeResource, self).get(request, key, client)
        del d['client']
        return d
node = NodeResource()
    
class AddressListResource(ObjectListResource):
    DAO = AddressDAO
address_list = AddressListResource()
class AddressResource(ObjectResource):
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
