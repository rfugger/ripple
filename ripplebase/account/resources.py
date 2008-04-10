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

from ripplebase.resource import *
from ripplebase.account.dao import *


def node_process_incoming(self, d):
    super(self.__class__, self).process_incoming(d)
    if 'name' in d:
        d['name'] = encode_node_name(d['name'], self.client)

def node_process_outgoing(self, d):
    super(self.__class__, self).process_outgoing(d)
    if 'name' in d:
        d['name'] = decode_node_name(d['name'])

class NodeListHandler(RippleObjectListHandler):
    DAO = NodeDAO
    process_incoming = node_process_incoming
    process_outgoing = node_process_outgoing

class NodeHandler(RippleObjectHandler):
    DAO = NodeDAO
    process_incoming = node_process_incoming
    process_outgoing = node_process_outgoing

    def get_data_dict(self, key):
        "Encode key = name."
        key = encode_node_name(key, self.client)
        return super(NodeHandler, self).get_data_dict(key)

    def update(self, keys, data_dict):
        keys = (encode_node_name(keys[0], self.client),)
        return super(NodeHandler, self).update(keys, data_dict)

def address_process_incoming(self, data_dict):
    super(self.__class__, self).process_incoming(data_dict)
    if 'nodes' in data_dict:
        data_dict['nodes'] = [encode_node_name(node, self.client) for node
                              in data_dict.get('nodes', ())]

def address_process_outgoing(self, data_dict):
    super(self.__class__, self).process_outgoing(data_dict)
    if 'nodes' in data_dict:
        data_dict['nodes'] = [decode_node_name(node) for node
                              in data_dict.get('nodes', ())]

class AddressListHandler(RippleObjectListHandler):
    DAO = AddressDAO
    process_incoming = address_process_incoming
    process_outgoing = address_process_outgoing

class AddressHandler(RippleObjectHandler):
    DAO = AddressDAO
    process_incoming = address_process_incoming
    process_outgoing = address_process_outgoing


account_request_fields = {
    'address': 'source_address',
    'partner': 'dest_address',
    'note': 'note',
}

class AccountListHandler(RippleObjectListHandler):
    DAO = AccountDAO

    def create(self, data_dict):
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

        super(RippleObjectListHandler, self).create(data_dict)
    
class AccountHandler(RippleObjectHandler):
    DAO = AccountDAO

    def update(self, keys, data_dict):
        if 'limits_effective_time' in data_dict:
            raise ValueError("'limits_effective_time' is read-only.")
        if 'relationship' in data_dict:
            raise ValueError("'relationship' is read-only.")
        super(AccountHandler, self).update(keys, data_dict)

class AccountRequestListHandler(RippleObjectListHandler):
    allowedMethods = ('GET', 'HEAD')
    DAO = AccountRequestDAO

class ExchangeRateListHandler(RippleObjectListHandler):
    DAO = ExchangeRateDAO
    process_incoming = node_process_incoming
    process_outgoing = node_process_outgoing    
    
class ExchangeRateHandler(RippleObjectHandler):
    DAO = ExchangeRateDAO
    process_incoming = node_process_incoming
    process_outgoing = node_process_outgoing

    def get_data_dict(self, key):
        "Encode key = name."
        key = encode_node_name(key, self.client)
        return super(ExchangeRateHandler, self).get_data_dict(key)

    def update(self, keys, data_dict):
        keys = (encode_node_name(keys[0], self.client),)
        return super(ExchangeRateHandler, self).update(keys, data_dict)

class ExchangeListHandler(RippleObjectListHandler):
    DAO = ExchangeDAO
    
