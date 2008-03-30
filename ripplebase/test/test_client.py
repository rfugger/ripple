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
from decimal import Decimal as D

from twisted.trial import unittest
from twisted.web import http

import ripplebase
from ripplebase import db, settings, json

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
                import time
                time.sleep(0.5)
                continue
            raise
    if response:
        json_response = json.decode(response.read())
        return json_response

def create_node(data_dict):
    urlopen('/nodes/', data_dict, code=http.CREATED)

def create_address(data_dict):
    urlopen('/addresses/', data_dict, code=http.CREATED)

def create_account(data_dict):
    urlopen('/accounts/', data_dict, code=http.CREATED)

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

    def test_node(self):
        data_dict = {u'name': u'my_node', u'addresses': []}
        create_node(data_dict)
            
        # check node is in list
        recv_data = urlopen('/nodes')
        self.assertEquals(recv_data[0], data_dict)

        # check node is at own url
        recv_data = urlopen('/nodes/my_node/')
        self.assertEquals(recv_data, data_dict)

        # update node a few times and check
        data_dict = {u'name': u'new_name'}
        urlopen('/nodes/my_node', data_dict)
        recv_data = urlopen('/nodes/new_name')
        data_dict['addresses'] = []
        self.assertEquals(recv_data, data_dict)
        create_address({u'address': u'my_address'})
        data_dict = {u'addresses': [u'my_address']}
        urlopen('/nodes/new_name', data_dict)
        recv_data = urlopen('/nodes/new_name/')
        data_dict['name'] = u'new_name'
        self.assertEquals(recv_data, data_dict)

    def test_address(self):
         node_dict = {u'name': u'my_node'}
         address_dict = {u'address': u'my_address',
                         u'nodes': [u'my_node']}
         create_node(node_dict)
         create_address(address_dict)

         # check list
         recv_data = urlopen('/addresses')
         self.assertEquals(recv_data[0], address_dict)
         
         # check url
         recv_data = urlopen('/addresses/my_address/')
         self.assertEquals(recv_data, address_dict)

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
            create_node(node)
            create_address(address)

        create_account(init_acct)
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

        recv_data = urlopen('/accounts/%s' % init_acct['name'])
        self.process_acct_recv_data(recv_data)
        self.assertEquals(recv_data, expected_data)
        
        # check request
        recv_data = urlopen('/accountrequests')
        self.assertEquals(recv_data[0], req_data)

        # create other account
        partner_acct['relationship'] = req_data['relationship']
        create_account(partner_acct)

        # check other account
        recv_data = urlopen('/accounts/%s' % partner_acct['name'])
        self.process_acct_recv_data(recv_data)
        expected_data = partner_acct.copy()
        expected_data['is_active'] = True
        self.assertEquals(recv_data, expected_data)
        
        # check request is gone
        recv_data = urlopen('/accountrequests/')
        self.assertEquals(recv_data, [])
        
        # check original account status
        recv_data = urlopen('/accounts/%s' % init_acct['name'])
        self.process_acct_recv_data(recv_data)
        self.assertEquals(recv_data['is_active'], True)

    def process_acct_recv_data(self, recv_data):
        effective_time = recv_data['limits_effective_time']
        del recv_data['limits_effective_time']
        try:
            time.strptime(effective_time,
                          '%s %s' % (json.RippleJSONEncoder.DATE_FORMAT,
                                     json.RippleJSONEncoder.TIME_FORMAT))
        except ValueError, ve:
            self.fail("Invalid 'limits_effective_time' returned: '%s'."
                      "Error was: %s." % (effective_time, ve))
        for field in self.acct_decimal_fields:
            recv_data[field] = D(recv_data[field])
    
