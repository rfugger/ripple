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
                    raise ValueError("'%s' is a required field." % field)
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

    
class ExchangeListHandler(RippleObjectListHandler):
    DAO = ExchangeDAO
    required_fields = ('from', 'to', 'rate')
    dao_fields = {}  # define in subclasses
    unused_dao_field = None
    
    def _convert_to_dao_fields(self, **kwargs):
        d = {}
        for api_field, dao_field in self.dao_fields.items():
            if api_field in kwargs:
                d[dao_field] = kwargs[api_field]
        return d
    
    def create(self, data_dict):
        d = self._convert_to_dao_fields(**data_dict)
        return super(ExchangeListHandler, self).create(d)

    def filter(self, **kwargs):
        kwargs = self._convert_to_dao_fields(**kwargs)
        kwargs[self.unused_dao_field] = None
        return super(ExchangeListHandler, self).filter(**kwargs)

    def repr(self, dao):
        data_dict = dao.data_dict()
        d = {}
        for api_field, dao_field in self.dao_fields.items():
            d[api_field] = data_dict[dao_field]
        return d

class ExchangeHandler(RippleObjectHandler):
    DAO = ExchangeDAO
    mutable_fields = ('rate',)
    dao_fields = {}
    
    def repr(self, dao):
        data_dict = dao.data_dict()
        d = {}
        for api_field, dao_field in self.dao_fields.items():
            d[api_field] = data_dict[dao_field]
        return d
    
class ThruExchangeListHandler(ExchangeListHandler):
    dao_fields = {
        'from': 'source_account',
        'to': 'target_account',
        'rate': 'rate',
    }
    unused_dao_field = 'unit'
    
class ThruExchangeHandler(ExchangeHandler):
    dao_fields = ThruExchangeListHandler.dao_fields
    
    def _get_dao(self, *keys):
        keys = keys + (None,)  # add in 'unit' key for ExchangeDAO
        return super(ThruExchangeHandler, self)._get_dao(*keys)
    
class InExchangeListHandler(ExchangeListHandler):
    dao_fields = {
        'from': 'source_account',
        'to': 'unit',
        'rate': 'rate',
    }
    unused_dao_field = 'target_account'
    
class InExchangeHandler(ExchangeHandler):
    dao_fields = InExchangeListHandler.dao_fields

    def _get_dao(self, *keys):
        keys = (keys[0], None, keys[1])  # add in 'target_account' key for ExchangeDAO
        return super(InExchangeHandler, self)._get_dao(*keys)
    
class OutExchangeListHandler(ExchangeListHandler):
    dao_fields = {
        'from': 'unit',
        'to': 'target_account',
        'rate': 'rate',
    }
    unused_dao_field = 'source_account'
    
    
class OutExchangeHandler(ExchangeHandler):
    dao_fields = OutExchangeListHandler.dao_fields

    def _get_dao(self, *keys):
        keys = (None, keys[1], keys[0])  # add in 'source_account' key for ExchangeDAO
        return super(OutExchangeHandler, self)._get_dao(*keys)

    
