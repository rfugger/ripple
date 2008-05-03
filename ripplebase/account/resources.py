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


class UnitListHandler(RippleObjectListHandler):
    DAO = UnitDAO
    required_fields = ('name',)

class UnitHandler(RippleObjectHandler):
    allowed_methods = ('GET', 'HEAD', 'DELETE')
    DAO = UnitDAO

    
class AddressListHandler(RippleObjectListHandler):
    DAO = AddressDAO
    required_fields = ('address',)
    optional_fields = ('owner', 'accounts',)

class AddressHandler(RippleObjectHandler):
    DAO = AddressDAO
    mutable_fields = AddressDAO.db_fields.keys()


account_request_fields = {
    'address': 'source_address',
    'partner': 'dest_address',
    'unit': 'unit',
    'note': 'note',
}

class AccountListHandler(RippleObjectListHandler):
    DAO = AccountDAO
    required_fields = ('name', 'balance', 'unit')
    optional_fields = ('owner', 'upper_limit', 'lower_limit',
                       'limits_expiry_time',
                       # these are for initial account only
                       'address', 'partner', 'note',
                       # these are required for confirmation only
                       'relationship')
                       
    def create(self, data_dict):
        if 'relationship' not in data_dict:
            for field in ('address', 'partner'):
                if field not in data_dict:
                    raise ValueError("%s is a required field." % field)
            # create relationship and account request
            acct_address = data_dict['address']
            rel = RelationshipDAO.create()
            data_dict['relationship'] = rel.id
            req_dict = {'relationship': rel.id}
            for key, req_key in account_request_fields.items():
                req_dict[req_key] = data_dict[key]
                if key != 'unit':
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
    mutable_fields = ('name', 'owner', 'balance', 'upper_limit', 'lower_limit',
                      'limits_expiry_time')

class AccountRequestListHandler(RippleObjectListHandler):
    allowed_methods = ('GET', 'HEAD')
    DAO = AccountRequestDAO

class ExchangeRateListHandler(RippleObjectListHandler):
    DAO = ExchangeRateDAO
    required_fields = ('name', 'value')
    optional_fields = ('expiry_time',)
    
class ExchangeRateHandler(RippleObjectHandler):
    DAO = ExchangeRateDAO
    mutable_fields = ('name', 'value', 'expiry_time')
    
class ThruExchangeListHandler(RippleObjectListHandler):
    DAO = ExchangeDAO
    required_fields = ('source_account', 'target_account', 'rate')

    def repr(self, dao):
        return dao.thru_data_dict()

class ThruExchangeHandler(RippleObjectHandler):
    DAO = ExchangeDAO
    mutable_fields = ('rate',)

    def _get_dao(self, *keys):
        keys = keys + (None,)  # add in 'unit' key for ExchangeDAO
        return super(ThruExchangeHandler, self)._get_dao(*keys)
    
    def repr(self, dao):
        return dao.thru_data_dict()
    
class InExchangeListHandler(RippleObjectListHandler):
    DAO = ExchangeDAO
    required_fields = ('unit', 'target_account', 'rate')

    def repr(self, dao):
        return dao.in_data_dict()

class InExchangeHandler(RippleObjectHandler):
    DAO = ExchangeDAO
    mutable_fields = ('rate',)

    def _get_dao(self, *keys):
        keys = (None,) + keys  # add in 'source_account' key for ExchangeDAO
        return super(InExchangeHandler, self)._get_dao(*keys)

    def repr(self, dao):
        return dao.in_data_dict()
    
class OutExchangeListHandler(RippleObjectListHandler):
    DAO = ExchangeDAO
    required_fields = ('unit', 'source_account', 'rate')

    def repr(self, dao):
        return dao.out_data_dict()

class OutExchangeHandler(RippleObjectHandler):
    DAO = ExchangeDAO
    mutable_fields = ('rate',)

    def _get_dao(self, *keys):
        keys = (keys[0], None, keys[1])  # add in 'target_account' key for ExchangeDAO
        return super(OutExchangeHandler, self)._get_dao(*keys)

    def repr(self, dao):
        return dao.out_data_dict()
    
