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

# db.mapper provides contextual session with autosave
from ripplebase import db
from ripplebase.account.tables import *

class Client(object):
    pass
db.mapper(Client, client_table)

class Address(object):
    pass
db.mapper(Address, address_table, properties={
    'client': orm.relation(Client)})

class Node(object):
    pass
db.mapper(Node, node_table, properties={
    'client': orm.relation(Client),
    'addresses': orm.relation(Address,
                              secondary=node_addresses_table,
                              backref='nodes')})  # m2m
class Relationship(object):
    pass
class Account(object):
    pass
class AccountLimits(object):
    pass

db.mapper(Relationship, relationship_table)
db.mapper(Account, account_table, properties={
    'relationship': orm.relation(Relationship),
    'node': orm.relation(Node),
    # *** eager load active limits
    })
db.mapper(AccountLimits, account_limits_table, properties={
    'account': orm.relation(Account, primaryjoin=
        account_limits_table.c.account_id==account_table.c.id)})

class Exchange(object):
    pass
class ExchangeRate(object):
    pass
class ExchangeRateEntry(object):
    pass

db.mapper(Exchange, exchange_table, properties={
    'source_account': orm.relation(Account, primaryjoin=
        exchange_table.c.source_account_id==account_table.c.id),
    'target_account': orm.relation(Account, primaryjoin=
        exchange_table.c.target_account_id==account_table.c.id),
    # *** eager load active exchange rate
    })

db.mapper(ExchangeRate, exchange_rate_table)
db.mapper(ExchangeRateEntry, exchange_rate_entry_table, properties={
    'exchange_rate': orm.relation(ExchangeRate, primaryjoin=
        exchange_rate_entry_table.c.exchange_rate_id==\
                                      exchange_rate_table.c.id)})

class AccountRequest(object):
    pass
db.mapper(AccountRequest, account_request_table, properties={
    'relationship': orm.relation(Relationship),
    'source_address': orm.relation(Address, primaryjoin=
        account_request_table.c.source_address_id==address_table.c.id),
    'dest_address': orm.relation(Address, primaryjoin=
        account_request_table.c.dest_address_id==address_table.c.id)})
    
