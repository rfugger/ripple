"SQLAlchemy tables for account data interface."

import sqlalchemy as sql

from ripplebase import db
from ripplebase.settings import PRECISION, SCALE

client_table = sql.Table(
    'client', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('name', sql.Unicode(256), nullable=False, unique=True),
    # *** need login/auth data here
)

# A node where multiple accounts connect for transfer of value one to the other
node_table = sql.Table(
    'node', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('name', sql.Unicode(256), nullable=False, unique=True),
    sql.Column('client_id', sql.Integer,
               sql.ForeignKey('client.id'),
               nullable=False),
)

address_table = sql.Table(
    'address', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('address', sql.Unicode(256), nullable=False),
    sql.Column('client_id', sql.Integer,
               sql.ForeignKey('client.id'),
               nullable=False),
    sql.UniqueConstraint('address', 'client_id'),
)

node_addresses_table = sql.Table(
    'node_addresses', db.meta,
    sql.Column('node_id', sql.Integer,
               sql.ForeignKey('node.id'),
               nullable=False),
    sql.Column('address_id', sql.Integer,
               sql.ForeignKey('address.id'),
               nullable=False),
)

account_table = sql.Table(
    'account', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('name', sql.Unicode(256), nullable=False),
    sql.Column('node_id', sql.Integer,
               sql.ForeignKey('node.id'),
               nullable=False),
    # *** status column necessary here?
    sql.Column('balance', sql.Numeric(PRECISION, SCALE),
               nullable=False),
)

account_limits_table = sql.Table(
    'account_limits', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('account_id', sql.Integer,
               sql.ForeignKey('account.id'),
               nullable=False),
    sql.Column('is_active', sql.Boolean, nullable=False),
    sql.Column('effective_time', sql.DateTime, nullable=False),
    sql.Column('expiry_time', sql.DateTime, nullable=False),    
    sql.Column('upper_limit', sql.Numeric(PRECISION, SCALE)),
    sql.Column('lower_limit', sql.Numeric(PRECISION, SCALE)),
)

exchange_table = sql.Table(
    'exchange', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('source_account_id', sql.Integer,
               sql.ForeignKey('account.id'),
               nullable=False),
    sql.Column('target_account_id', sql.Integer,
               sql.ForeignKey('account.id'),
               nullable=False),
    sql.Column('rate_id', sql.Integer,
               sql.ForeignKey('exchange_rate.id'),
               nullable=True),
)

exchange_rate_table = sql.Table(
    'exchange_rate', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('name', sql.Unicode(256), nullable=False, unique=True),
)

exchange_rate_entry_table = sql.Table(
    'exchange_rate_entry', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('exchange_rate_id', sql.Integer,
               sql.ForeignKey('exchange_rate.id'),
               nullable=False),
    sql.Column('is_active', sql.Boolean, nullable=False),
    sql.Column('effective_time', sql.DateTime, nullable=False),
    sql.Column('expiry_time', sql.DateTime, nullable=False),    
    sql.Column('rate', sql.Numeric(PRECISION, SCALE),
               nullable=False),
)

