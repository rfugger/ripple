"SQLAlchemy tables for payments interface."

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

# Payment status codes
REQUESTED = 'RQ'
PENDING = 'PE'
COMPLETED = 'OK'
CANCELLED = 'CA'
REFUSED = 'RF'
FAILED = 'FA'

payment_table = sql.Table(
    'payment', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('date', sql.DateTime, nullable=False),
    sql.Column('unit', sql.Unicode(32), nullable=False),
    sql.Column('amount', sql.Numeric(PRECISION, SCALE), nullable=False),
    sql.Column('status', sql.Unicode(2), nullable=False),
)

payment_node_table = sql.Table(
    'payment_node', db.meta,
    sql.Column('payment_id', sql.Integer,
               sql.ForeignKey('payment.id'),
               nullable=False),
    sql.Column('node_id', sql.Integer,
               sql.ForeignKey('node.id'),
               nullable=False),
    sql.Column('is_outgoing', sql.Boolean, nullable=False),
    sql.UniqueConstraint('payment_id', 'node_id'),
)

