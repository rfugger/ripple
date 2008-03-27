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

from ripplebase.account.mappers import *
from ripplebase import db

class ClientDAO(db.DAO):
    model = Client
    db_fields = {
        'name': 'name',
    }
    keys = ['name']

class NodeDAO(db.DAO):
    model = Node
    db_fields = {
        'name': 'name',  # unique for whole server (encode with client at higher level)
        'client': 'client',  # maps to Client.name
        'addresses': None,  # maps to m2m association table
    }
    keys = ['name']
    fk_daos = {
        'client': ClientDAO,
    }
    # m2m_daos after AddressDAO, because it needs it.

class AddressDAO(db.DAO):
    model = Address
    db_fields = {
        'address': 'address',
        'client': 'client',  # maps to Client.name
        'nodes': None,  # maps to m2m association table
    }
    keys = ['address']
    fk_daos = {
        'client': ClientDAO,
    }
    m2m_daos = {
        'nodes': NodeDAO,
    }

# must define this after defining AddressDAO
NodeDAO.m2m_daos = {
    'addresses': AddressDAO,
}

class RelationshipDAO(db.DAO):
    model = Relationship
    db_fields = {
        'id': 'id',
        'status': 'status',
    }
    keys = ['id']
        
class AccountDAO(db.DAO):
    model = Account
    db_fields = {
        'name': 'name',
        'relationship': 'relationship',
        'node': 'node',
        'balance': 'balance',
        'upper_limit': None,  # maps to AccountLimits.upper_limit
        'lower_limit': None,  # maps to AccountLimits.lower_limit
        'limits_effective_time': None,  # maps to AccountLimits.effective_time
        'limits_expiry_time': None, # maps to AccountLimits.expiry_time
    }
    keys = ['name']
    fk_daos = {
        'relationship': RelationshipDAO,
        'node': NodeDAO,
    }

    limits_map = {
        'upper_limit': 'upper_limit',
        'lower_limit': 'lower_limit',
        'limits_effective_time': 'effective_time',
        'limits_expiry_time': 'expiry_time',
    }

    def get_active_limits(self):
        if not hasattr(self, '_limits'):
            db_limits = db.query(AccountLimits).filter_by(
                account=self.data_obj, is_active=True).all()
            if db_limits:
                self._limits = db_limits[0]
            else:
                self._limits = None
        return self._limits
    def set_active_limits(self, limits):
        self._limits = limits
    limits = property(get_active_limits, set_active_limits)
    
    def new_limits(self):
        """Call every time new limits are set.
        Sets old limits (if they exist) to inactive, creates
        new active limits record.
        Must then set upper, lower limits and effective,
        expiry times before flushing sessions to db.
        """
        # *** maybe better to set limit attributes in this
        # function to make sure?
        # nah, probably ok to treat these attributes like other
        # account attributes
        # but maybe should copy old limits attribute values?
        if self.limits:
            self.limits.is_active = False
        self.limits = AccountLimits()
        self.limits.is_active = True
        self.limits.account = self.data_obj
    
    def __setattr__(self, attr, value):
        if attr in self.limits_map:
            # make new limits obj if one doesn't exist
            if not self.limits:
                self.new_limits()
            setattr(self.limits, self.limits_map[attr], value)
        else:
            # *** create new relationship object if doesn't exist
            super(AccountDAO, self).__setattr__(attr, value)

    def __getattr__(self, attr):
        if attr in self.limits_map:
            if self.limits:
                return getattr(self.limits, self.limits_map[attr])
            else:
                return None
        else:
            return super(AccountDAO, self).__getattr__(attr)

class ExchangeDAO(db.DAO):
    model = Exchange
    db_fields = {
        'source_account': 'source_account',
        'target_account': 'target_account',
        'rate': 'rate',
    }
    # nothing refers to this, so don't need keys
    fk_daos = {
        'source_account': AccountDAO,
        'target_account': AccountDAO,
    }
        

class ExchangeRateDAO(db.DAO):
    model = ExchangeRate
    db_fields = {
        'name': 'name',
        'rate': 'rate',  # maps to ExchangeRateEntry.rate
        'effective_time': 'effective_time',  # maps to ExchangeRateEntry.effective_time 
        'expiry_time': 'expiry_time',  # maps to ExchangeRateEntry.expiry_time
    }
    keys = ['name']

    # *** handle nonstandard fields

    
class AccountRequestDAO(db.DAO):
    model = AccountRequest
    db_fields = {
        'id': 'id',
        'relationship': 'relationship',
        'source_address': 'source_address',
        'dest_address': 'dest_address',
        'note': 'note',
    }
    keys = ['id']
    fk_daos = {
        'relationship': RelationshipDAO,
        'source_address': AddressDAO,
        'dest_address': AddressDAO,
    }
