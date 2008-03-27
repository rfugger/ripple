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

from twisted.web import resource

from ripplebase.resource import (ObjectListResource, ObjectResource,
                                 ClientFieldAwareObjectListResource,
                                 ClientFieldAwareObjectResource)
from ripplebase.account.dao import *

def encode_node_name(node_name, client_id):
    return '%s/%s' % (client_id, node_name)
def decode_node_name(encoded_node_name):
    return encoded_node_name[encoded_node_name.find('/') + 1:]


def node_add_client(self, d):
    super(self.__class__, self).add_client(d)
    # *** replace with actual client
    from ripplebase import settings
    client = settings.TEST_CLIENT
    d['name'] = encode_node_name(d['name'], client)

def node_strip_client(self, d):
    super(self.__class__, self).strip_client(d)
    d['name'] = decode_node_name(d['name'])

class NodeListResource(ClientFieldAwareObjectListResource):
    DAO = NodeDAO
    add_client = node_add_client
    strip_client = node_strip_client
node_list = NodeListResource()

class NodeResource(ClientFieldAwareObjectResource):
    allowedMethods = ('GET', 'DELETE')  # can't post modifications to node
    DAO = NodeDAO
    add_client = node_add_client
    strip_client = node_strip_client

    def get(self, request, key):
        "Encode key = name."
        # *** replace with actual client
        from ripplebase import settings
        client = settings.TEST_CLIENT
        key = encode_node_name(key, client)
        return super(NodeResource, self).get(request, key)
node = NodeResource()


def address_add_client(self, data_dict):
    super(self.__class__, self).add_client(data_dict)
    # *** replace with actual client
    from ripplebase import settings
    client = settings.TEST_CLIENT
    data_dict['nodes'] = [encode_node_name(node, client) for node
                          in data_dict.get('nodes', ())]

def address_strip_client(self, data_dict):
    super(self.__class__, self).strip_client(data_dict)
    data_dict['nodes'] = [decode_node_name(node) for node
                          in data_dict.get('nodes', ())]

class AddressListResource(ClientFieldAwareObjectListResource):
    DAO = AddressDAO
    add_client = address_add_client
    strip_client = address_strip_client
address_list = AddressListResource()

class AddressResource(ClientFieldAwareObjectResource):
    DAO = AddressDAO
    add_client = address_add_client
    strip_client = address_strip_client
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
