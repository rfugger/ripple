"SQLAlchemy data mappers."

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

class Account(object):
    pass
class AccountLimits(object):
    pass

db.mapper(Account, account_table, properties={
    'node': orm.relation(Node)
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
