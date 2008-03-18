#!/usr/bin/python

from twisted.web import server
from twisted.internet import reactor

from ripplebase.account.resources import acct_root
from ripplebase.payment.resources import pmt_root
from ripplebase.json import JSONResource
from ripplebase import settings

root = JSONResource()
root.putChild('acct', acct_root)
root.putChild('txn', pmt_root)

site = server.Site(root)
reactor.listenTCP(settings.HTTP_PORT, site)
reactor.run()

