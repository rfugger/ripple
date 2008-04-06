"SQLAlchemy tables for account data interface."

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
    sql.Column('is_deleted', sql.Boolean, nullable=False, default=False),
)

address_table = sql.Table(
    'address', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('address', sql.Unicode(256), nullable=False, unique=True),
    sql.Column('client_id', sql.Integer,
               sql.ForeignKey('client.id'),
               nullable=False),
)

# *** may eventually want to track historical node-address associations
#     for payment accountability
node_addresses_table = sql.Table(
    'node_addresses', db.meta,
#     sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('node_id', sql.Integer,
               sql.ForeignKey('node.id'),
               nullable=False),
    sql.Column('address_id', sql.Integer,
               sql.ForeignKey('address.id'),
               nullable=False),
#     sql.Column('effective_time', sql.DateTime, nullable=False),
#     sql.Column('is_active', sql.Boolean, nullable=False),
)

# A relationship (link/connection between two nodes) contains two accounts,
# one for each node.
# *** could probably do away with this table entirely.
relationship_table = sql.Table(
    'relationship', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
)

account_table = sql.Table(
    'account', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('relationship_id', sql.Integer,
               sql.ForeignKey('relationship.id'),
               nullable=False),
    sql.Column('name', sql.Unicode(256), nullable=False),
    sql.Column('node_id', sql.Integer,
               sql.ForeignKey('node.id'),
               nullable=False),
    sql.Column('is_active', sql.Boolean, nullable=False, default=True),
    sql.Column('balance', sql.Numeric(PRECISION, SCALE),
               nullable=False),
)

account_limits_table = sql.Table(
    'account_limits', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('account_id', sql.Integer,
               sql.ForeignKey('account.id'),
               nullable=False),
    sql.Column('is_active', sql.Boolean, nullable=False, default=True),
    sql.Column('effective_time', sql.DateTime, nullable=False,
               default=sql.func.now()),
    sql.Column('expiry_time', sql.DateTime, nullable=True),
    sql.Column('upper_limit', sql.Numeric(PRECISION, SCALE)),
    sql.Column('lower_limit', sql.Numeric(PRECISION, SCALE)),
)

account_request_table = sql.Table(
    'account_request', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('relationship_id', sql.Integer,
               sql.ForeignKey('relationship.id'),
               nullable=False),
    sql.Column('source_address_id', sql.Integer,
               sql.ForeignKey('address.id'),
               nullable=False),
    sql.Column('dest_address_id', sql.Integer,
               sql.ForeignKey('address.id'),
               nullable=False),
    sql.Column('note', sql.Text, nullable=False)
)

exchange_table = sql.Table(
    'exchange', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('is_active', sql.Boolean, nullable=False, default=True),
    sql.Column('effective_time', sql.DateTime, nullable=False,
               default=sql.func.now()),
    sql.Column('source_account_id', sql.Integer,
               sql.ForeignKey('account.id'),
               nullable=False),
    sql.Column('target_account_id', sql.Integer,
               sql.ForeignKey('account.id'),
               nullable=False),
    # *** maybe cache current rate value here for easy access?
)

# allow exchanges to have named exchange rates so client can update
# 'USDCAD' instead of having to update many exchanges in identical ways
exchange_rate_table = sql.Table(
    'exchange_rate', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('name', sql.Unicode(256), nullable=False, unique=True),
    sql.Column('client_id', sql.Integer,
               sql.ForeignKey('client.id'),
               nullable=False),
)

# exchange-exchange rate association/history table
exchange_exchange_rate_table = sql.Table(
    'exchange_exchange_rate', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),    
    sql.Column('exchange_id', sql.Integer,
               sql.ForeignKey('exchange.id'),
               nullable=False),
    sql.Column('rate_id', sql.Integer,
               sql.ForeignKey('exchange_rate.id'),
               nullable=False),
    sql.Column('is_active', sql.Boolean, nullable=False, default=True),
    sql.Column('effective_time', sql.DateTime, nullable=False,
               default=sql.func.now()),
)

# history of values of each exchange rate, for auditability
exchange_rate_value_table = sql.Table(
    'exchange_rate_value', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('rate_id', sql.Integer,
               sql.ForeignKey('exchange_rate.id'),
               nullable=False),
    sql.Column('is_active', sql.Boolean, nullable=False, default=True),
    sql.Column('effective_time', sql.DateTime, nullable=False,
               default=sql.func.now()),
    sql.Column('expiry_time', sql.DateTime, nullable=False),    
    sql.Column('value', sql.Numeric(PRECISION, SCALE),
               nullable=False),
)
