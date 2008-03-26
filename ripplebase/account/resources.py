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

from twisted.web import resource

from ripplebase.resource import (ObjectListResource, ObjectResource,
                                 ClientFieldAwareObjectListResource,
                                 ClientFieldAwareObjectResource)
from ripplebase.account.dao import *

class NodeListResource(ClientFieldAwareObjectListResource):
    DAO = NodeDAO
node_list = NodeListResource()

class NodeResource(ClientFieldAwareObjectResource):
    allowedMethods = ('GET', 'DELETE')  # can't post modifications to node
    DAO = NodeDAO
node = NodeResource()
    
class AddressListResource(ClientFieldAwareObjectListResource):
    DAO = AddressDAO
address_list = AddressListResource()
class AddressResource(ClientFieldAwareObjectResource):
    DAO = AddressDAO
address = AddressResource()

class AccountListResource(ObjectListResource):
    DAO = AccountDAO
account_list = AccountListResource()
class AccountResource(ObjectResource):
    DAO = AccountDAO
account = AccountResource()

# class ExchangeResource(ObjectListResource):
#     DAO = ExchangeDAO
# acct_root.putChild('exchange', ExchangeResource())
