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

from ripplebase.payment.mappers import *
from ripplebase.account.dao import AddressDAO

class PaymentDAO(db.RippleDAO):
    model = Payment
    fields = {
        'id': 'id',
        'payer': 'payer',
        'recipient': 'recipient',
        'amount': 'amount',
        'amount_for_recipient': 'amount_for_recipient',
        'units': 'units',
        'status': 'status',
        'accounts': None,  # custom field, (accountname, exchangerate) pairs
    }
    keys = ['id']
    fk_daos = {
        'payer': AddressDAO,
        'recipient': AddressDAO,
    }

    # *** handle accounts field -- different for payer and recipient

class PaymentPathDAO(db.RippleDAO):
    "For payer info only, before approving payment."
    model = PaymentPath
    fields = {
        'payment': 'payment',
        'paying_account': None,  # gotten from first PaymentLink
        'payer_amount': 'payer_amount',
        'recipient_amount': 'recipient_amount',
    }
    # no keys necessary - filter by payment
    fk_daos = {
        'payment': PaymentDAO,
    }
        
    
    
