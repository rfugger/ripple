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

class ClientTest(unittest.TestCase):
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
        data_dict = {u'name': u'my_node'}
        create_node(data_dict)
            
        # check node is in list
        recv_data = urlopen('/nodes')
        self.assertEquals(recv_data[0], data_dict)

        # check node is at own url
        recv_data = urlopen('/nodes/my_node/')
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
