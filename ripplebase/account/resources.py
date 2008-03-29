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

from datetime import datetime

from twisted.web import resource

from ripplebase.resource import (ObjectListResource, ObjectResource,
                                 ClientFieldAwareObjectListResource,
                                 ClientFieldAwareObjectResource)
from ripplebase.account.dao import *

def encode_node_name(node_name, client_id):
    return '%s/%s' % (client_id, node_name)
def decode_node_name(encoded_node_name):
    return encoded_node_name[encoded_node_name.find('/') + 1:]


def node_process_incoming(self, d):
    super(self.__class__, self).process_incoming(d)
    # *** replace with actual client
    from ripplebase import settings
    client = settings.TEST_CLIENT
    d['name'] = encode_node_name(d['name'], client)

def node_process_outgoing(self, d):
    super(self.__class__, self).process_outgoing(d)
    d['name'] = decode_node_name(d['name'])

class NodeListResource(ClientFieldAwareObjectListResource):
    DAO = NodeDAO
    process_incoming = node_process_incoming
    process_outgoing = node_process_outgoing
node_list = NodeListResource()

class NodeResource(ClientFieldAwareObjectResource):
    allowedMethods = ('GET', 'DELETE')  # can't post modifications to node
    DAO = NodeDAO
    process_incoming = node_process_incoming
    process_outgoing = node_process_outgoing

    def get_data_dict(self, key):
        "Encode key = name."
        # *** replace with actual client
        from ripplebase import settings
        client = settings.TEST_CLIENT
        key = encode_node_name(key, client)
        return super(NodeResource, self).get_data_dict(key)
node = NodeResource()


def address_process_incoming(self, data_dict):
    super(self.__class__, self).process_incoming(data_dict)
    # *** replace with actual client
    from ripplebase import settings
    client = settings.TEST_CLIENT
    data_dict['nodes'] = [encode_node_name(node, client) for node
                          in data_dict.get('nodes', ())]

def address_process_outgoing(self, data_dict):
    super(self.__class__, self).process_outgoing(data_dict)
    data_dict['nodes'] = [decode_node_name(node) for node
                          in data_dict.get('nodes', ())]

class AddressListResource(ClientFieldAwareObjectListResource):
    DAO = AddressDAO
    process_incoming = address_process_incoming
    process_outgoing = address_process_outgoing
address_list = AddressListResource()

class AddressResource(ClientFieldAwareObjectResource):
    DAO = AddressDAO
    process_incoming = address_process_incoming
    process_outgoing = address_process_outgoing
address = AddressResource()


account_request_fields = {
    'address': 'source_address',
    'partner': 'dest_address',
    'note': 'note',
}

def account_process_incoming(self, data_dict):
    if 'relationship' not in data_dict:
        # create relationship and account request
        rel = RelationshipDAO.create()
        data_dict['relationship'] = rel.id
        req_dict = {'relationship': rel.id}
        for key, req_key in account_request_fields.items():
            req_dict[req_key] = data_dict[key]
            del data_dict[key]
        req = AccountRequestDAO.create(**req_dict)
        data_dict['is_active'] = False
    else:  # confirming account by creating dual account
        # *** maybe ought to wait for exchanges?
        data_dict['is_active'] = True
    # *** this is only good for create, not for update
    data_dict['limits_effective_time'] = datetime.now()
    # *** replace with actual client
    from ripplebase import settings
    client = settings.TEST_CLIENT
    data_dict['node'] = encode_node_name(data_dict['node'], client)

def account_process_outgoing(self, data_dict):
    data_dict['node'] = decode_node_name(data_dict['node'])
    
class AccountListResource(ClientFieldAwareObjectListResource):
    DAO = AccountDAO
    process_incoming = account_process_incoming
    process_outgoing = account_process_outgoing
account_list = AccountListResource()

class AccountResource(ClientFieldAwareObjectResource):
    DAO = AccountDAO
    process_incoming = account_process_incoming
    process_outgoing = account_process_outgoing
account = AccountResource()

# class ExchangeResource(ObjectListResource):
#     DAO = ExchangeDAO
# acct_root.putChild('exchange', ExchangeResource())
