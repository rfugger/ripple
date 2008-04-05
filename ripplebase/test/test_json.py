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

from datetime import datetime
from decimal import Decimal as D

from twisted.trial import unittest

from ripplebase import json

class JsonTest(unittest.TestCase):
    def encode_decode_decimal(self, d):
        s = json.encode(d)
        self.assertEquals(s, u'"%s"' % d)
        d2 = json.decode(s)
        self.assertEquals(d2, unicode(d))
            
    def test_decimal(self):
        data = ['712', '12.3456', '-0.0283',
                '29803874920198365897234.12093849029378492601982734']
        for d in data:
            self.encode_decode_decimal(D(d))

    def encode_decode_datetime(self, d):
        s = json.encode(d)
        self.assertEquals(s, u'"%s"' % (str(d)[:-7]))
        d2 = json.decode(s)
        self.assertEquals(d2, unicode(d)[:-7])
        
            
    def test_datetime(self):
        data = [datetime(2008, 3, 13, 21, 52, 34, 231000),
                datetime(2008, 3, 13, 21, 52, 34, 931000)]
        for d in data:
            self.encode_decode_datetime(d)
