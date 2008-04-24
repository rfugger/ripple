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

class PaymentListHandler(RippleObjectListHandler):
    DAO = PaymentDAO

    def create(self, data_dict):
        "Init payment.  If payer's client, search for paths and return results."

    def filter(self, **kwargs):
        "Return only payments to/from this client."
        
class PaymentHandler(RippleObjectHandler):
    allowedMethods = ('GET', 'HEAD', 'DELETE')  # no updates to payment
    DAO = PaymentDAO

class PathSearchHandler(RequestHandler):
    allowedMethods = ('GET', 'HEAD', 'POST')

    def get(self, payment_id):
        "Display results of previous search."
        
    def post(self, payment_id):
        "Search for paths and return results."

class PaymentCommitHandler(RequestHandler):
    allowedMethods = ('POST',)

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
    allowedMethods = ('GET', 'HEAD')
    DAO = PaymentDAO

    def filter(self, **kwargs):
        "Get payment requests for this client."


def pathsearch(pmt):
    "Retrieve and store paths for payment."
    
