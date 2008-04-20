"SQLAlchemy data mappers."

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

from sqlalchemy import orm
from sqlalchemy.ext.associationproxy import association_proxy

# db.mapper provides contextual session with autosave
from ripplebase import db
from ripplebase.account.tables import *

class Client(object):
    pass
db.mapper(Client, client_table)

class Address(object):
    pass
class Relationship(object):
    pass
class Account(object):
    pass
class AccountLimits(object):
    pass

db.mapper(Address, address_table, properties={
    'client': orm.relation(Client),
    'accounts': orm.relation(Account,
                             secondary=account_address_association_table,
                             backref='addresses')})  # m2m
db.mapper(Relationship, relationship_table)
db.mapper(Account, account_table, properties={
    'relationship': orm.relation(Relationship),
    'client': orm.relation(Client),
    # *** eager load active limits
    })
db.mapper(AccountLimits, account_limits_table, properties={
    'account': orm.relation(Account, primaryjoin=
        account_limits_table.c.account_id==account_table.c.id)})

class AccountRequest(object):
    pass
db.mapper(AccountRequest, account_request_table, properties={
    'relationship': orm.relation(Relationship),
    'source_address': orm.relation(Address, primaryjoin=
        account_request_table.c.source_address_id==address_table.c.id),
    'dest_address': orm.relation(Address, primaryjoin=
        account_request_table.c.dest_address_id==address_table.c.id)})

class Exchange(object):
    pass
class ExchangeRate(object):
    pass
class ExchangeExchangeRate(object):
    pass
class ExchangeRateValue(object):
    pass

db.mapper(Exchange, exchange_table, properties={
    'source_account': orm.relation(Account, primaryjoin=
        exchange_table.c.source_account_id==account_table.c.id),
    'target_account': orm.relation(Account, primaryjoin=
        exchange_table.c.target_account_id==account_table.c.id),
    # *** eager load active exchange rate value?
    })

db.mapper(ExchangeRate, exchange_rate_table, properties={
    'client': orm.relation(Client)})
db.mapper(ExchangeExchangeRate, exchange_exchange_rate_table, properties={
    'exchange': orm.relation(Exchange),
    'rate': orm.relation(ExchangeRate)})
db.mapper(ExchangeRateValue, exchange_rate_value_table, properties={
    'rate': orm.relation(ExchangeRate)})

    
