"API resource -> data object mappers."

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

from sqlalchemy import sql

from ripplebase.account.mappers import *
from ripplebase import db
from ripplebase.account.tables import *


class UnitDAO(db.RippleDAO):
    model = Unit
    db_fields = {
        'name': 'name'
    }
    keys = ['name']

class RelationshipDAO(db.RippleDAO):
    model = Relationship
    db_fields = {
        'id': 'id',
    }
    keys = ['id']
        
class AccountDAO(db.RippleDAO):
    model = Account
    db_fields = {
        'name': 'name',  # *** map to 'id'?
        'relationship': 'relationship',
        'owner': 'owner',
        'is_active': 'is_active',
        'balance': 'balance',
        'unit': 'unit',
        'upper_limit': None,  # maps to AccountLimits.upper_limit
        'lower_limit': None,  # maps to AccountLimits.lower_limit
        'limits_effective_time': None,  # maps to AccountLimits.effective_time
        'limits_expiry_time': None, # maps to AccountLimits.expiry_time
    }
    keys = ['name']
    fk_daos = {
        'relationship': RelationshipDAO,
        'unit': UnitDAO,
    }
    has_client_field = True
    has_client_as_key = True
    
    limits_map = {
        'upper_limit': 'upper_limit',
        'lower_limit': 'lower_limit',
        'limits_effective_time': 'effective_time',  # set automatically
        'limits_expiry_time': 'expiry_time',
    }

    def _get_active_limits(self):
        if not hasattr(self, '_limits'):
            self._limits = db.query(AccountLimits).filter_by(
                account=self.data_obj, is_active=True).first()
        return self._limits
    def _set_active_limits(self, limits):
        self._limits = limits
    limits = property(_get_active_limits, _set_active_limits)
    
    def new_limits(self):
        """Call every time new limits are set.
        Sets old limits (if they exist) to inactive, creates
        new active limits record.
        Must then set upper, lower limits and effective,
        expiry times before flushing to db.
        """
        if self.limits:
            self.limits.is_active = False
            old_limits = self.limits
        else:
            old_limits = None
        self.limits = AccountLimits()
        self.limits.account = self.data_obj
        if old_limits:
            attrs_to_copy = self.limits_map.values()
            attrs_to_copy.remove('effective_time')
            for attr in attrs_to_copy:
                setattr(self.limits, attr, getattr(old_limits, attr))
        # *** may be outstanding transactions using old limits
        # *** must guard against this when committing transaction!
    
    def __setattr__(self, attr, value):
        if attr in self.limits_map:
            # make new limits obj if one doesn't exist
            if not self.limits:
                self.new_limits()
            setattr(self.limits, self.limits_map[attr], value)
        else:
            # *** create new relationship object if doesn't exist?
            #     or handle at higher level?
            super(AccountDAO, self).__setattr__(attr, value)

    def __getattr__(self, attr):
        if attr in self.limits_map:
            if self.limits:
                return getattr(self.limits, self.limits_map[attr])
            else:
                return None
        else:
            return super(AccountDAO, self).__getattr__(attr)

    def update(self, **kwargs):
        "Create new limits object if limits are being changed."
        limits_args = set(kwargs.keys()).intersection(self.limits_map.keys())
        if limits_args:
            self.new_limits()
        super(AccountDAO, self).update(**kwargs)

    @classmethod
    def filter(cls, **kwargs):
        limits_args = set(kwargs.keys()).intersection(cls.limits_map.keys())
        if limits_args:
            raise ValueError('Limits fields not implemented in filter: %s' %
                             limits_args)
        return super(AccountDAO, cls).filter(**kwargs)
        
class AddressDAO(db.RippleDAO):
    model = Address
    db_fields = {
        'address': 'address',
        'owner': 'owner',
        'accounts': None,  # maps to m2m association table
    }
    keys = ['address']
    m2m_daos = {
        'accounts': AccountDAO,
    }
    has_client_field = True

    def add_account(self, account_dao):
        self.data_obj.accounts.append(account_dao.data_obj)
        db.flush()
    
class AccountRequestDAO(db.RippleDAO):
    model = AccountRequest
    db_fields = {
        'relationship': 'relationship',
        'source_address': 'source_address',
        'dest_address': 'dest_address',
        'unit': 'unit',
        'note': 'note',
    }
    # FK key won't work if another DAO wants to reference this DAO
    keys = ['relationship']
    fk_daos = {
        'relationship': RelationshipDAO,
        'source_address': AddressDAO,
        'dest_address': AddressDAO,
        'unit': UnitDAO,
    }
    
class ExchangeDAO(db.RippleDAO):
    model = Exchange
    db_fields = {
        'source_account': 'source_account',
        'target_account': 'target_account',
        'unit': 'unit',
        'rate': None,  # mapped by ExchangeExchangeRate associaton/history table
    }
    # FK/multi keys won't work if another DAO wants to reference this DAO
    keys = ['source_account', 'target_account', 'unit']
    fk_daos = {
        'source_account': AccountDAO,
        'target_account': AccountDAO,
        'unit': UnitDAO,
    }

    def _get_active_exchange_exchange_rate(self):
        return db.query(ExchangeExchangeRate).filter_by(
            exchange=self.data_obj, is_active=True).first()
    
    def __getattr__(self, attr):
        if attr == 'rate':
            eer = self._get_active_exchange_exchange_rate()
            return eer.rate.name
        else:
            return super(ExchangeDAO, self).__getattr__(attr)

    def __setattr__(self, attr, value):
        if attr == 'rate':
            rate_dao = ExchangeRateDAO.get(value)
            old_eer = self._get_active_exchange_exchange_rate()
            if old_eer:
                old_eer.is_active = False
            new_eer = ExchangeExchangeRate()
            new_eer.exchange = self.data_obj
            new_eer.rate = rate_dao.data_obj
        else:
            super(ExchangeDAO, self).__setattr__(attr, value)

    @classmethod
    def filter(cls, **kwargs):
        if 'rate' in kwargs:
            raise ValueError('Rate field not implemented in filter.')
        return super(ExchangeDAO, cls).filter(**kwargs)

    def thru_data_dict(self):
        d = super(ExchangeDAO, self).data_dict()
        del d['unit']
        return d

    def in_data_dict(self):
        d = super(ExchangeDAO, self).data_dict()
        del d['source_account']
        return d

    def out_data_dict(self):
        d = super(ExchangeDAO, self).data_dict()
        del d['target_account']
        return d
    
            
class ExchangeRateDAO(db.RippleDAO):
    model = ExchangeRate
    db_fields = {
        'name': 'name',
        'value': None,  # maps to ExchangeRateValue.rate
        'effective_time': None,  # maps to ExchangeRateValue.effective_time 
        'expiry_time': None,  # maps to ExchangeRateValue.expiry_time
    }
    keys = ['name']
    has_client_field = True
    has_client_as_key = True
    
    value_map = {
        'value': 'value',
        'effective_time': 'effective_time',  # set automatically
        'expiry_time': 'expiry_time',
    }

    def _get_active_value_obj(self):
        if not hasattr(self, '_value_obj'):
            self._value_obj = db.query(ExchangeRateValue).filter_by(
                rate=self.data_obj, is_active=True).first()
        return self._value_obj
    def _set_active_value_obj(self, value_obj):
        self._value_obj = value_obj
    value_obj = property(_get_active_value_obj, _set_active_value_obj)
    
    def new_value_obj(self):
        """Call every time new value is set.
        Sets old value_obj (if it exists) to inactive, creates
        new active value_obj record.
        Must then set value and effective,
        expiry times before flushing to db.
        """
        if self.value_obj:
            self.value_obj.is_active = False
        self.value_obj = ExchangeRateValue()
        self.value_obj.is_active = True
        self.value_obj.rate = self.data_obj
        # *** may be outstanding transactions using old value
        # *** must guard against this when committing transaction!
    
    def __setattr__(self, attr, value):
        if attr in self.value_map:
            # make new value obj if one doesn't exist
            if not self.value_obj:
                self.new_value_obj()
            setattr(self.value_obj, self.value_map[attr], value)
        else:
            super(ExchangeRateDAO, self).__setattr__(attr, value)

    def __getattr__(self, attr):
        if attr in self.value_map:
            if self.value_obj:
                return getattr(self.value_obj, self.value_map[attr])
            else:
                return None
        else:
            return super(ExchangeRateDAO, self).__getattr__(attr)

    def update(self, **kwargs):
        "Create new value object if value is being changed."
        value_args = set(kwargs.keys()).intersection(self.value_map.keys())
        if value_args:
            self.new_value_obj()
        super(ExchangeRateDAO, self).update(**kwargs)

    @classmethod
    def filter(cls, **kwargs):
        value_args = set(kwargs.keys()).intersection(cls.value_map.keys())
        if value_args:
            raise ValueError('Value fields not implemented in filter: %s' %
                             value_args)
        return super(ExchangeRateDAO, cls).filter(**kwargs)
    
