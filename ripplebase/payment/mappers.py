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

from ripplebase import db
from ripplebase.payment.tables import *
from ripplebase.account.mappers import Address, Account
from ripplebase.account.tables import address_table, account_table

class Payment(object):
    pass
db.mapper(Payment, payment_table, properties={
    'payer': orm.relation(Address, primaryjoin=
        payment_table.c.payer_address_id==address_table.c.id),
    'recipient': orm.relation(Address, primaryjoin=
        payment_table.c.recipient_address_id==address_table.c.id)})

class PaymentAccount(object):
    pass
db.mapper(PaymentAccount, payment_account_table, properties={
    'payment': orm.relation(Payment),
    'account': orm.relation(Account)})

class PaymentPath(object):
    pass
db.mapper(PaymentPath, payment_path_table, properties={
    'payment': orm.relation(Payment)})

class PaymentLink(object):
    pass
db.mapper(PaymentLink, payment_link_table, properties={
    'path': orm.relation(PaymentPath),
    'paying_account': orm.relation(Account, primaryjoin=
        payment_link_table.c.paying_account_id==account_table.c.id),
    'receiving_account': orm.relation(Account, primaryjoin=
        payment_link_table.c.receiving_account_id==account_table.c.id)})
