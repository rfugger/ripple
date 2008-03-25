#!/usr/bin/python

from twisted.web import server
from twisted.internet import reactor

from ripplebase.resource import JSONSiteResource
from ripplebase import settings, urls

root = JSONSiteResource(urls.urls)
site = server.Site(root)
reactor.listenTCP(settings.HTTP_PORT, site)
reactor.run()

