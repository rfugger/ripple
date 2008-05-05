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

import urllib2 as urllib
import subprocess
import os
import ctypes
import time
from datetime import datetime, timedelta
from decimal import Decimal as D

from twisted.trial import unittest
from twisted.web import http

import ripplebase
from ripplebase import db, settings, json
from ripplebase.account.mappers import *

ripplebase_path = ripplebase.__path__[0]

server_url = 'http://localhost:%d' % settings.HTTP_PORT

headers = {'content-type':
               'application/json; charset=utf-8'}

def make_server():
    return subprocess.Popen(['python',
            os.path.join(ripplebase_path, 'server.py')])

def urlopen(path, data=None, code=http.OK):
    url = server_url + path
    json_data = data and json.encode(data) or None
    req = urllib.Request(url, json_data, headers)
    response = None
    while True:  # try connecting until server is up
        try:
            response = urllib.urlopen(req)
            break
        except urllib.HTTPError, he:
            # anything but 200 OK raises HTTPError (!?)
            # need to catch desired response code here
            if he.code == code:
                # *** how to capture response on code other than 200?
                #     maybe content is stored in HTTPError object?
                break
            print json.decode(he.read())  # display body
            raise
        except urllib.URLError, ue:
            if ue.reason.args[0] in (10061, 111):  # connection refused
                # wait for server to be up
                time.sleep(0.5)
                continue
            raise
    if response:
        response = response.read()
        if response:
            json_response = json.decode(response)
            return json_response

class ClientTest(unittest.TestCase):
    acct_decimal_fields = ('balance', 'upper_limit', 'lower_limit')
        
    def setUp(self):
        db.reset()
        self.server = make_server()

    def tearDown(self):
        if self.server:
            try:  # windows
                PROCESS_TERMINATE = 1
                handle = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_TERMINATE, False, self.server.pid)
                ctypes.windll.kernel32.TerminateProcess(handle, -1)
                ctypes.windll.kernel32.CloseHandle(handle)
            except AttributeError:  # unix
                subprocess.Popen(['kill', str(self.server.pid)])

    def test_bad_requests(self):
        urlopen('/abcdef', code=http.NOT_FOUND)
        urlopen('/addresses', {u'abcdef': u'mung'}, code=http.INTERNAL_SERVER_ERROR)
                
    def check_data(self, url, expected_data, process_recv_data=None):
        recv_data = urlopen(url)
        if process_recv_data:
            process_recv_data(recv_data)
        self.assertEquals(recv_data, expected_data)

    def update_and_check(self, update_url, new_data, check_url=None,
                         process_recv_data=None):
        if check_url is None:
            check_url = update_url
        orig_data = urlopen(update_url)
        if process_recv_data:
            process_recv_data(orig_data)
        urlopen(update_url, new_data)
        orig_data.update(new_data)
        self.check_data(check_url, orig_data, process_recv_data)

    def test_unit(self):
        unit_dict1 = {'name': u'ABC'}
        urlopen('/units/', unit_dict1)
        recv_data = urlopen('/units')
        self.failUnless(unit_dict1 in recv_data)  # may be other units already
        self.check_data('/units/%s' % unit_dict1['name'],
                        unit_dict1)
        
    def test_address(self):
         address_dict = {'address': u'my_address',
                         'owner': u'itchy scratchy',
                         'accounts': []}
         urlopen('/addresses/', address_dict)

         # check list
         self.check_data('/addresses', [address_dict])
         
         # check url
         self.check_data('/addresses/my_address/', address_dict)

         # update a few times and check
         self.update_and_check('/addresses/my_address',
                               {u'address': u'new_address'},
                               '/addresses/new_address')
         self.update_and_check('/addresses/new_address',
                               {'owner': u'bart homer'})
         self.update_and_check('/addresses/new_address',
                               {'address': u'old_address',
                                'owner': u'marge lisa'},
                               '/addresses/old_address/')

         # *** accounts m2m field is tested below in test_account
         
    def check_account_data(self, url, expected_data):
        self.check_data(url, expected_data, self.process_acct_recv_data)

    def update_and_check_account(self, update_url, new_data, check_url=None):
        self.update_and_check(update_url, new_data, check_url,
                              self.process_acct_recv_data)
         
    def process_acct_recv_data(self, recv_data):
        effective_time = recv_data['limits_effective_time']
        try:
            eff_datetime = str_to_datetime(effective_time)
        except ValueError, ve:
            self.fail("Invalid 'limits_effective_time' returned: '%s'."
                      "Error was: %s." % (effective_time, ve))
        del recv_data['limits_effective_time']
        for field in self.acct_decimal_fields:
            recv_data[field] = D(recv_data[field])

    def test_account(self):
        addresses = [{u'address': u'my_address',
                      'owner': 'guy'},
                     {u'address': u'other_address',
                      'owner': 'girl'}]
        init_acct = {u'name': u'my_account',
                     u'owner': u'blubby blub',
                     u'balance': D(u'0.00'),
                     u'unit': u'CAD',
                     u'upper_limit': D(u'100.00'),
                     u'lower_limit': D(u'-100.00'),
                     u'limits_expiry_time': None,
                     # the rest are for account request
                     u'address': u'my_address',
                     u'partner': u'other_address',
                     u'note': u'Hey.'}
        partner_acct = {u'name': u'other_account',
                        u'relationship': None,  # set in code once known
                        u'owner': u'noodie nood',
                        u'balance': D(u'0.00'),
                        u'unit': u'CAD',
                        u'upper_limit': D(u'150.00'),
                        u'lower_limit': D(u'-50.00'),
                        u'limits_expiry_time': None,}

        for address in addresses:
            urlopen('/addresses/', address)

        urlopen('/accounts/', init_acct)
        recv_data = urlopen('/accounts')
        expected_data = init_acct.copy()
        req_data = {}
        from ripplebase.account.resources import account_request_fields
        for field, req_field in account_request_fields.items():
            req_data[req_field] = init_acct[field]
            if field != 'unit':
                del expected_data[field]
        req_data['relationship'] = recv_data[0]['relationship']
        expected_data['relationship'] = req_data['relationship']
        expected_data['is_active'] = False
        self.process_acct_recv_data(recv_data[0])
        self.assertEquals(recv_data[0], expected_data)
        
        self.check_account_data('/accounts/my_account/', expected_data)
        
        # check request
        self.check_data('/accountrequests', [req_data])

        # check address has account now
        address_data = urlopen('/addresses/my_address')
        expected_address_data = addresses[0]
        expected_address_data['accounts'] = [u'my_account']
        self.assertEquals(address_data, expected_address_data)
        
        # create other account
        partner_acct['relationship'] = req_data['relationship']
        urlopen('/accounts/', partner_acct)

        # check other account
        expected_partner_data = partner_acct.copy()
        expected_partner_data['is_active'] = True
        self.check_account_data('/accounts/other_account/', expected_partner_data)
        
        # check request is gone
        self.check_data('/accountrequests/', [])
        
        # check original account status
        expected_data['is_active'] = True
        self.check_account_data('/accounts/my_account', expected_data)

        # check partner address has account now
        address_data = urlopen('/addresses/other_address')
        expected_address_data = addresses[1]
        expected_address_data['accounts'] = [u'other_account']
        self.assertEquals(address_data, expected_address_data)

        # update account in a few ways
        self.update_and_check_account('/accounts/my_account/',
                                      {u'name': u'new_account'},
                                      '/accounts/new_account')
        time.sleep(1)  # make sure to get a new timestamp on new limits object
        self.update_and_check_account('/accounts/new_account',
                                      {u'owner': u'blobby blob',
                                       u'upper_limit': D('823.00102')})
        # make sure old limits got stored
        limits = AccountLimits.query().order_by('effective_time')
        old_limits = limits[0]
        new_limits = limits[2]
        self.assertEquals(old_limits.upper_limit, init_acct['upper_limit'])
        self.assertEquals(new_limits.upper_limit, D('823.00102'))
        self.failUnless(old_limits.effective_time < new_limits.effective_time)
        self.failUnless(old_limits.is_active == False)
        self.failUnless(new_limits.is_active)

        # *** do some more various updating here

        # check adding accounts to addresses
        self.update_and_check('/addresses/my_address',
                              {'accounts': [u'new_account', u'other_account']})

        
    def check_rate_data(self, url, expected_data):
        self.check_data(url, expected_data, self.process_eff_time_recv_data)

    def update_and_check_rate(self, update_url, new_data, check_url=None):
        self.update_and_check(update_url, new_data, check_url,
                              self.process_eff_time_recv_data)
         
    def process_eff_time_recv_data(self, recv_data_list):
        if not isinstance(recv_data_list, list):
            recv_data_list = [recv_data_list]
        for recv_data in recv_data_list:
            effective_time = recv_data['effective_time']
            try:
                eff_datetime = str_to_datetime(effective_time)
            except ValueError, ve:
                self.fail("Invalid 'effective_time' returned: '%s'."
                          "Error was: %s." % (effective_time, ve))
            del recv_data['effective_time']
            recv_data['value'] = D(recv_data['value'])

    def test_exchangerate(self):
        rate1 = {'name': u'USDCAD',
                 'value': D('1.0232'),
                 'expiry_time': None}
        rate2 = {'name': u'gAuhrs',
                 'value': D('0.003943'),
                 'expiry_time': None}

        urlopen('/rates/', rate1)
        self.check_rate_data('/rates/', [rate1])
        self.check_rate_data('/rates/%s' % rate1['name'], rate1)

        urlopen('/rates/', rate2)
        self.check_rate_data('/rates', [rate1, rate2])
        self.check_rate_data('/rates/%s/' % rate2['name'], rate2)

        time.sleep(1)  # make sure different time appears on new rate
        self.update_and_check_rate('/rates/%s' % rate1['name'],
                                   {'value': D('0.8452342')})
        # make sure old values got stored
        values = ExchangeRateValue.query().order_by('effective_time')
        old_value = values[0]
        new_value = values[2]
        self.assertEquals(old_value.value, rate1['value'])
        self.assertEquals(new_value.value, D('0.8452342'))
        self.failUnless(old_value.effective_time < new_value.effective_time)
        self.failUnless(old_value.is_active == False)
        self.failUnless(new_value.is_active)

        
    def test_exchange(self):
        addresses = [{u'address': u'my_address',
                      'owner': 'guy'},
                     {u'address': u'other_address',
                      'owner': 'girl'}]
        accounts = [{u'name': u'acct1_girl',
                     u'owner': u'girl',
                     u'balance': D(u'0.00'),
                     u'unit': u'CAD',
                     u'upper_limit': D(u'100.00'),
                     u'lower_limit': D(u'-100.00'),
                     u'limits_expiry_time': None,
                     # the rest are for account request
                     u'address': u'other_address',
                     u'partner': u'my_address',
                     u'note': u'Hey.'},
                    {u'name': u'acct2_girl',
                     u'owner': u'girl',
                     u'balance': D(u'0.00'),
                     u'unit': u'USD',
                     u'upper_limit': D(u'100.00'),
                     u'lower_limit': D(u'-100.00'),
                     u'limits_expiry_time': None,
                     # the rest are for account request
                     u'address': u'other_address',
                     u'partner': u'my_address',
                     u'note': u'Heya.'}]
        rate1 = {'name': u'CADUSD',
                 'value': D('1.0232'),
                 'expiry_time': None}
        rate2 = {'name': u'gAuhrs',
                 'value': D('0.003943'),
                 'expiry_time': None}

        exchange = {'from': u'acct1_girl',
                    'to': u'acct2_girl',
                    'rate': rate1['name']}
        in_exchange = {'from': u'acct1_girl',
                       'to': u'USD',
                       'rate': rate1['name']}
        out_exchange = {'from': u'CAD',
                        'to': u'acct2_girl',
                        'rate': rate1['name']}
        
        for address in addresses:
            urlopen('/addresses/', address)
        for account in accounts:
            urlopen('/accounts', account)
        for rate in (rate1, rate2):
            urlopen('/rates', rate)

        urlopen('/exchanges', exchange)
        self.check_data('/exchanges/', [exchange])
        self.check_data('/exchanges/%s/%s' % (exchange['from'],
                                              exchange['to']),
                        exchange)

        # alter rate, check history is stored
        time.sleep(1)  # make sure time is different
        self.update_and_check('/exchanges/%s/%s' % (exchange['from'],
                                                    exchange['to']),
                              {'rate': rate2['name']})
        eers = list(db.query(ExchangeExchangeRate).order_by('effective_time'))
        self.assertEquals(eers[0].rate.name, rate1['name'])
        self.assertEquals(eers[1].rate.name, rate2['name'])
        self.failUnless(eers[0].effective_time < eers[1].effective_time)

        # try some in & out exchanges
        urlopen('/inexchanges', in_exchange)
        self.check_data('/inexchanges/', [in_exchange])
        self.check_data('/inexchanges/%s/%s' % (in_exchange['from'],
                                                in_exchange['to']),
                        in_exchange)
        
        urlopen('/outexchanges', out_exchange)
        self.check_data('/outexchanges/', [out_exchange])
        self.check_data('/outexchanges/%s/%s' % (out_exchange['from'],
                                                 out_exchange['to']),
                        out_exchange)
        
    def test_payment(self):
        addresses = [{u'address': u'guy_address',
                      'owner': 'guy'},
                     {u'address': u'girl_address',
                      'owner': 'girl'},
                     {u'address': u'girl_address2',
                      'owner': 'girl'}]
        accounts = [{u'name': u'acct1_girl',
                     u'owner': u'girl',
                     u'balance': D(u'0.00'),
                     u'unit': u'CAD',
                     u'upper_limit': D(u'100.00'),
                     u'lower_limit': D(u'-100.00'),
                     u'limits_expiry_time': None,
                     # the rest are for account request
                     u'address': u'girl_address',
                     u'partner': u'guy_address',
                     u'note': u'Hey.'},
                    {u'name': u'acct2_girl',
                     u'owner': u'girl',
                     u'balance': D(u'0.00'),
                     u'unit': u'USD',
                     u'upper_limit': D(u'100.00'),
                     u'lower_limit': D(u'-100.00'),
                     u'limits_expiry_time': None,
                     # the rest are for account request
                     u'address': u'girl_address',
                     u'partner': u'guy_address',
                     u'note': u'Heya.'}]
        partner_accts = [{u'name': u'acct1_guy',
                          u'relationship': 1,  # educated guess here :)
                          u'owner': u'guy',
                          u'balance': D(u'0.00'),
                          u'unit': u'CAD',
                          u'upper_limit': D(u'150.00'),
                          u'lower_limit': D(u'-50.00'),
                          u'limits_expiry_time': None,},
                         {u'name': u'acct2_guy',
                          u'relationship': 2,  # educated guess here :)
                          u'owner': u'guy',
                          u'balance': D(u'0.00'),
                          u'unit': u'USD',
                          u'upper_limit': D(u'150.00'),
                          u'lower_limit': D(u'-50.00'),
                          u'limits_expiry_time': None,}]
        rates = [{'name': u'USDCAD',
                  'value': D('1.0232'),
                  'expiry_time': None},
                 {'name': u'CADUSD',
                  'value': D('0.9985'),
                  'expiry_time': None},
                 {'name': u'identity',
                  'value': D('1.0'),
                  'expiry_time': None}]
        exchange = {'from': u'acct1_guy',
                    'to': u'acct2_guy',
                    'rate': u'USDCAD'}
        inexchange = {'from': u'acct2_girl',
                      'to': u'CAD',
                      'rate': u'CADUSD'}
        outexchange = {'from': u'CAD',
                       'to': u'acct1_girl',
                       'rate': u'identity'}

        payment = {'payer': 'girl_address',
                   'recipient': 'girl_address2',
                   'amount': D('10.00'),
                   'amount_for_recipient': True,
                   'units': 'CAD',
                   'is_request': False}
        
        for address in addresses:
            urlopen('/addresses/', address)
        for account, partner_acct in zip(accounts, partner_accts):
            urlopen('/accounts', account)
            urlopen('/accounts', partner_acct)
        urlopen('/addresses/girl_address',
                {'accounts': [u'acct1_girl']})
        urlopen('/addresses/girl_address2',
                {'accounts': [u'acct2_girl']})
        for rate in rates:
            urlopen('/rates', rate)
        urlopen('/exchanges', exchange)
        urlopen('/inexchanges', inexchange)
        urlopen('/outexchanges', outexchange)

        urlopen('/payments', payment)
        
        
def str_to_datetime(s):
    return datetime.strptime(s, '%s %s' % (json.RippleJSONEncoder.DATE_FORMAT,
                                           json.RippleJSONEncoder.TIME_FORMAT))
