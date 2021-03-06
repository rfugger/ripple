#!/usr/bin/python

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

from twisted.web import server
from twisted.internet import reactor

from ripplebase.resource import ThreadedJSONSiteResource, JSONSiteResource
from ripplebase import settings, urls

root = ThreadedJSONSiteResource(urls.urls)
#root = JSONSiteResource(urls.urls)
site = server.Site(root)
reactor.listenTCP(settings.HTTP_PORT, site)
reactor.run()

