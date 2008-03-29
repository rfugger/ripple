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

from ripplebase.resource import (ObjectListHandler, ObjectHandler,
                                 ClientFieldAwareObjectListHandler,
                                 ClientFieldAwareObjectHandler)
from ripplebase.account.dao import *

def encode_node_name(node_name, client_id):
    return '%s/%s' % (client_id, node_name)
def decode_node_name(encoded_node_name):
    return encoded_node_name[encoded_node_name.find('/') + 1:]


def node_process_incoming(self, d):
    super(self.__class__, self).process_incoming(d)
    d['name'] = encode_node_name(d['name'], self.client)

def node_process_outgoing(self, d):
    super(self.__class__, self).process_outgoing(d)
    d['name'] = decode_node_name(d['name'])

class NodeListHandler(ClientFieldAwareObjectListHandler):
    DAO = NodeDAO
    process_incoming = node_process_incoming
    process_outgoing = node_process_outgoing

class NodeHandler(ClientFieldAwareObjectHandler):
    DAO = NodeDAO
    process_incoming = node_process_incoming
    process_outgoing = node_process_outgoing

    def get_data_dict(self, key):
        "Encode key = name."
        key = encode_node_name(key, self.client)
        return super(NodeHandler, self).get_data_dict(key)


def address_process_incoming(self, data_dict):
    super(self.__class__, self).process_incoming(data_dict)
    data_dict['nodes'] = [encode_node_name(node, self.client) for node
                          in data_dict.get('nodes', ())]

def address_process_outgoing(self, data_dict):
    super(self.__class__, self).process_outgoing(data_dict)
    data_dict['nodes'] = [decode_node_name(node) for node
                          in data_dict.get('nodes', ())]

class AddressListHandler(ClientFieldAwareObjectListHandler):
    DAO = AddressDAO
    process_incoming = address_process_incoming
    process_outgoing = address_process_outgoing

class AddressHandler(ClientFieldAwareObjectHandler):
    DAO = AddressDAO
    process_incoming = address_process_incoming
    process_outgoing = address_process_outgoing


account_request_fields = {
    'address': 'source_address',
    'partner': 'dest_address',
    'note': 'note',
}

def account_process_incoming(self, data_dict):
    # *** only create, update not handled yet
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
        # *** maybe ought to wait for exchanges before activating acct?
        data_dict['is_active'] = True
        AccountRequestDAO.delete(data_dict['relationship'])
        init_acct = AccountDAO.filter(relationship=data_dict['relationship'])[0]
        init_acct.is_active = True  # gets committed later
        
    # *** this is only good for create, not for update
    data_dict['limits_effective_time'] = datetime.now()
    data_dict['node'] = encode_node_name(data_dict['node'], self.client)

def account_process_outgoing(self, data_dict):
    data_dict['node'] = decode_node_name(data_dict['node'])
    
class AccountListHandler(ClientFieldAwareObjectListHandler):
    DAO = AccountDAO
    process_incoming = account_process_incoming
    process_outgoing = account_process_outgoing

class AccountHandler(ClientFieldAwareObjectHandler):
    DAO = AccountDAO
    process_incoming = account_process_incoming
    process_outgoing = account_process_outgoing

class AccountRequestListHandler(ObjectListHandler):
    allowedMethods = ('GET', 'HEAD')
    DAO = AccountRequestDAO
    
# class ExchangeHandler(ObjectListHandler):
#     DAO = ExchangeDAO
# acct_root.putChild('exchange', ExchangeHandler())
