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

from ripplebase.resource import (RippleObjectListHandler, RippleObjectHandler,
                                 RequestHandler)
from ripplebase.payment.dao import *
from ripplebase.account.dao import AddressDAO

# Payment status codes
REQUESTED = 'RQ'
APPROVED = 'AP'
COMPLETED = 'OK'
CANCELLED = 'CA'
REFUSED = 'RF'
FAILED = 'FA'


class PaymentListHandler(RippleObjectListHandler):
    DAO = PaymentDAO

    def create(self, data_dict):
        request_only = data_dict['request_only']
        del data_dict['request_only']
        if request_only:
            data_dict['status'] = REQUESTED
        else:
            # *** this is wrong - recipient must approve payment when
            # amount isn't defined on recipient end.
            payer_client_name = AddressDAO.get(data_dict['payer']).client
            if payer_client_name == self.client.name:
                data_dict['status'] = APPROVED
            else:
                raise ValueError("Payment from another client must be requested.")
            
        pmt = super(PaymentListHandler, self).create(data_dict)
        return {'id': pmt.id}
        
    def filter(self, **kwargs):
        "Return only payments to/from this client."
        
class PaymentHandler(RippleObjectHandler):
    allowed_methods = ('GET', 'HEAD', 'DELETE')  # no updates to payment
    DAO = PaymentDAO

class PathSearchHandler(RequestHandler):
    allowed_methods = ('GET', 'HEAD', 'POST')

    def get(self, payment_id):
        "Display results of previous search."
        
    def post(self, payment_id):
        "Search for paths and return results."

class PaymentCommitHandler(RequestHandler):
    allowed_methods = ('POST',)

    def post(self, payment_id):
        """Takes a set of paths and commits it.
        Paths must match what was most recently returned from
        path search handler.
        """
        
class PaymentRequestListHandler(RippleObjectListHandler):
    """Check payment requests to client.
    Gives a payment ID to then operate on payment directly.
    Could be done as filter in PaymentListHandler, but
    not clear how to filter on *client*, as opposed to address.
    """
    allowed_methods = ('GET', 'HEAD')
    DAO = PaymentDAO

    def filter(self, **kwargs):
        "Get payment requests for this client."


def path_search(pmt):
    "Find and store paths for payment."
    
def get_paths(pmt):
    "Retrieve stored paths for payment."
