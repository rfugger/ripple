"Site URL configuration"

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

from ripplebase.account import resources as acct

urls = (
    (r'^/nodes/?$', acct.node_list),
    (r'^/nodes/([^/]+)/?$', acct.node),

    (r'^/addresses/?$', acct.address_list),
    (r'^/addresses/([^/]+)/?$', acct.address),

    (r'^/accounts/?$', acct.account_list),
    (r'^/accounts/([^/]+)/?$', acct.account),    
)
