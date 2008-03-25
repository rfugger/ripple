from twisted.web import resource

from ripplebase.resource import ObjectListResource, ObjectResource
from ripplebase.account.dao import *

class NodeResource(ObjectResource):
    """Nodes don't need to report their client since
    only that client could be making this request,
    and it knows who it is already.
    """
    DAO = NodeDAO
    def get(self, request, key):
        "Restrict to calling client; remove client field."
        # *** replace with actual client
        from ripplebase import settings
        client = settings.TEST_CLIENT
        d = ObjectResource.get(self, request, key, client)
        del d['client']
        return d
node = NodeResource()
    
class NodeListResource(ObjectListResource):
    DAO = NodeDAO
    resource_instance_class = NodeResource

    def create(self, data_dict):
        "Add client key to data_dict."
        from ripplebase import settings
        data_dict['client'] = settings.TEST_CLIENT
        ObjectListResource.create(self, data_dict)

    def filter(self):
        # *** replace with actual client
        from ripplebase import settings
        client = settings.TEST_CLIENT
        for obj in self.DAO.filter(client=client):
            d = obj.data_dict()
            del d['client']
            yield d
nodes = NodeListResource()

class AddressResource(ObjectResource):
    DAO = AddressDAO
address = AddressResource()
class AddressListResource(ObjectListResource):
    DAO = AddressDAO
addresses = AddressListResource()

class AccountResource(ObjectResource):
    DAO = AccountDAO
account = AccountResource()
class AccountListResource(ObjectListResource):
    DAO = AccountDAO
accounts = AccountListResource()

# class ExchangeResource(ObjectListResource):
#     DAO = ExchangeDAO
# acct_root.putChild('exchange', ExchangeResource())
