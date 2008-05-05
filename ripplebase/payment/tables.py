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

payment_table = sql.Table(
    'payment', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('init_date', sql.DateTime, nullable=False,
               default=sql.func.now()),
    sql.Column('commit_date', sql.DateTime, nullable=True),
    sql.Column('payer_address_id', sql.Integer,
               sql.ForeignKey('address.id'), nullable=False),
    sql.Column('recipient_address_id', sql.Integer,
               sql.ForeignKey('address.id'), nullable=False),
    sql.Column('amount', sql.Numeric(PRECISION, SCALE), nullable=False),
    sql.Column('amount_for_recipient', sql.Boolean, nullable=False),
    sql.Column('units', sql.Unicode(32), nullable=True),
    sql.Column('status', sql.Unicode(2), nullable=False),
)

payment_path_table = sql.Table(
    'payment_path', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('payment_id', sql.Integer,
               sql.ForeignKey('payment.id'), nullable=False),
    sql.Column('payer_amount', sql.Numeric(PRECISION, SCALE), nullable=False),
    sql.Column('recipient_amount', sql.Numeric(PRECISION, SCALE), nullable=False),
)

payment_link_table = sql.Table(
    'payment_link', db.meta,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('path_id', sql.Integer,
               sql.ForeignKey('payment_path.id'), nullable=False),
    sql.Column('paying_account_id', sql.Integer,
               sql.ForeignKey('account.id'), nullable=False),
    sql.Column('receiving_account_id', sql.Integer,
               sql.ForeignKey('account.id'), nullable=False),
    sql.Column('sequence_number', sql.Integer, nullable=False),
    sql.Column('amount', sql.Numeric(PRECISION, SCALE), nullable=False),
)             
