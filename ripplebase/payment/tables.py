"SQLAlchemy tables for payments interface."

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

