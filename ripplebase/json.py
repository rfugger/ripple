"""Ripplebase JSON encoder/decoder
Handles encoding of Decimal and datetime objects to strings.
Ideally Decimal would encode to JSON number, but decoders for all
platforms decode that to float, which is a no-no for monetary
apps.  This isn't a big deal since the protocol defines the types
for each field, and databases accept string values for numeric
fields.
"""

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

import decimal, datetime

from twisted.web import resource

from ripplebase import simplejson
from ripplebase import settings

##### Convenience functions ##########

def encode(obj):
    if settings.DEBUG:  # make it look nice
        indent = 4
        separators = (', ', ': ')
    else:  # make it short
        indent = 0
        separators = (',', ':')
    encoder = RippleJSONEncoder(ensure_ascii=False,
                                check_circular=settings.DEBUG,
                                allow_nan=False,
                                indent=indent,
                                separators=separators,
                                )
    return encoder.encode(obj)

def decode(s):
    #decoder = DecimalJSONDecoder()
    decoder = simplejson.JSONDecoder()
    return decoder.decode(s)

##### Custom decimal/datetime encoder ##########3

class RippleJSONEncoder(simplejson.JSONEncoder):
    """ JSONEncoder subclass that knows how to encode date/time
    and decimal types.  Borrowed from django DjangoJSONEncoder.
    """

    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.strftime("%s %s" % (self.DATE_FORMAT, self.TIME_FORMAT))
        elif isinstance(o, datetime.date):
            return o.strftime(self.DATE_FORMAT)
        elif isinstance(o, datetime.time):
            return o.strftime(self.TIME_FORMAT)
        elif isinstance(o, decimal.Decimal):
            return str(o)
        else:
            return super(RippleJSONEncoder, self).default(o)


##### Custom decimal decoder #######
# Don't need to decode datetimes, because those strings
# are recognized by the database automatically.

# def JSONNumber(match, context):
#     "Returns Decimal instead of float."
#     match = JSONNumber.regex.match(match.string, *match.span())
#     integer, frac, exp = match.groups()
#     if frac or exp:
#         res = decimal.Decimal(match.string)
#     else:
#         res = int(integer)
#     return res, None
# simplejson.decoder.pattern(
#     r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?')(JSONNumber)

# ALL_TYPES = [
#     simplejson.decoder.JSONObject,
#     simplejson.decoder.JSONArray,
#     simplejson.decoder.JSONString,
#     simplejson.decoder.JSONConstant,
#     JSONNumber,  # custom version that decodes to Decimal
# ]

# class DecimalJSONDecoder(simplejson.JSONDecoder):
#     _scanner = simplejson.decoder.Scanner(ALL_TYPES)

