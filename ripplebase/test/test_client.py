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
from ripplebase.account.mappers import AccountLimits

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
        urlopen('/nodes', {u'abcdef': u'mung'}, code=http.INTERNAL_SERVER_ERROR)
                
    def check_data(self, url, expected_data):
        recv_data = urlopen(url)
        self.assertEquals(recv_data, expected_data)

    def update_and_check(self, update_url, new_data, check_url=None):
        if check_url is None:
            check_url = update_url
        orig_data = urlopen(update_url)
        urlopen(update_url, new_data)
        orig_data.update(new_data)
        self.check_data(check_url, orig_data)
        
    def test_node(self):
        data_dict = {u'name': u'my_node', u'addresses': []}
        urlopen('/nodes/', data_dict)
            
        # check node is in list
        self.check_data('/nodes', [data_dict])

        # check node is at own url
        self.check_data('/nodes/my_node/', data_dict)

        # update node a few times and check
        self.update_and_check('/nodes/my_node',
                              {u'name': u'new_name'},
                              '/nodes/new_name')
        urlopen('/addresses/', {u'address': u'my_address'})
        self.update_and_check('/nodes/new_name',
                              {u'addresses': [u'my_address']})
        self.update_and_check('/nodes/new_name',
                              {u'name': u'old_name'},
                              '/nodes/old_name')        

    def test_address(self):
         node_dict = {u'name': u'my_node'}
         address_dict = {u'address': u'my_address',
                         u'nodes': [u'my_node']}
         urlopen('/nodes/', node_dict)
         urlopen('/addresses/', address_dict)

         # check list
         self.check_data('/addresses', [address_dict])
         
         # check url
         self.check_data('/addresses/my_address/', address_dict)

         # update a few times and check
         self.update_and_check('/addresses/my_address',
                               {u'address': u'new_address'},
                               '/addresses/new_address')
         urlopen('/nodes/', {u'name': u'nother_node'})
         self.update_and_check('/addresses/new_address',
                               {u'nodes': [u'nother_node']})

    def check_account_data(self, url, expected_data, min_effective_time=None):
        recv_data = urlopen(url)
        self.process_acct_recv_data(recv_data)
        self.assertEquals(recv_data, expected_data)

    def update_and_check_account(self, update_url, new_data, check_url=None):
        if check_url is None:
            check_url = update_url
        orig_data = urlopen(update_url)
        self.process_acct_recv_data(orig_data)
        urlopen(update_url, new_data)
        orig_data.update(new_data)
        self.check_account_data(check_url, orig_data)
         
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
        nodes = [{u'name': u'my_node'},
                 {u'name': u'other_node'}]
        addresses = [{u'address': u'my_address',
                      u'nodes': [u'my_node']},
                     {u'address': u'other_address',
                      u'nodes': [u'other_node']}]
        init_acct = {u'name': u'my_account',
                     u'node': u'my_node',
                     u'balance': D(u'0.00'),
                     u'upper_limit': D(u'100.00'),
                     u'lower_limit': D(u'-100.00'),
                     u'limits_expiry_time': None,
                     # the rest are for account request
                     u'address': u'my_address',
                     u'partner': u'other_address',
                     u'note': u'Hey.'}
        partner_acct = {u'name': u'other_account',
                        u'relationship': None,  # set in code once known
                        u'node': u'other_node',
                        u'balance': D(u'0.00'),
                        u'upper_limit': D(u'150.00'),
                        u'lower_limit': D(u'-50.00'),
                        u'limits_expiry_time': None,}

        for node, address in zip(nodes, addresses):
            urlopen('/nodes/', node)
            urlopen('/addresses/', address)

        urlopen('/accounts/', init_acct)
        recv_data = urlopen('/accounts')
        expected_data = init_acct.copy()
        req_data = {}
        from ripplebase.account.resources import account_request_fields
        for field, req_field in account_request_fields.items():
            req_data[req_field] = init_acct[field]
            del expected_data[field]
        req_data['relationship'] = recv_data[0]['relationship']
        expected_data['relationship'] = req_data['relationship']
        expected_data['is_active'] = False
        self.process_acct_recv_data(recv_data[0])
        self.assertEquals(recv_data[0], expected_data)
        
        self.check_account_data('/accounts/my_account/', expected_data)
        
        # check request
        self.check_data('/accountrequests', [req_data])

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

        # update account in a few ways
        self.update_and_check_account('/accounts/my_account/',
                                      {u'name': u'new_account'},
                                      '/accounts/new_account')
        urlopen('/nodes/', {u'name': u'node2'})
        time.sleep(1)  # make sure to get a new timestamp on new limits object
        self.update_and_check_account('/accounts/new_account',
                                      {u'node': u'node2',
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
        
def str_to_datetime(s):
    return datetime.strptime(s, '%s %s' % (json.RippleJSONEncoder.DATE_FORMAT,
                                           json.RippleJSONEncoder.TIME_FORMAT))
