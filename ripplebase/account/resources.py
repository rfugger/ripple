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


class AddressListHandler(RippleObjectListHandler):
    DAO = AddressDAO

class AddressHandler(RippleObjectHandler):
    DAO = AddressDAO

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
            acct_address = data_dict['address']
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
            acct_request = AccountRequestDAO.get(data_dict['relationship'])
            acct_address = acct_request.dest_address
            AccountRequestDAO.delete(data_dict['relationship'])
            init_acct = AccountDAO.filter(relationship=data_dict['relationship'])[0]
            init_acct.is_active = True  # gets committed later

        acct = super(AccountListHandler, self).create(data_dict)

        # add new account to appropriate address
        address = AddressDAO.get(acct_address)
        address.add_account(acct)
    
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
    
class ExchangeRateHandler(RippleObjectHandler):
    DAO = ExchangeRateDAO

class ExchangeListHandler(RippleObjectListHandler):
    DAO = ExchangeDAO
    
class ExchangeHandler(RippleObjectHandler):
    DAO = ExchangeDAO

    def update(self, keys, data_dict):
        if 'source_account' in data_dict or 'target_account' in data_dict:
            raise ValueError("Source and target accounts cannot be changed.")
        super(ExchangeHandler, self).update(keys, data_dict)
