import urllib2 as urllib
import subprocess
import os
import ctypes

from twisted.trial import unittest

import ripplebase
from ripplebase import db, settings, json

ripplebase_path = ripplebase.__path__[0]

root_url = 'http://localhost:%d' % settings.HTTP_PORT

def make_server():
    return subprocess.Popen(['python',
            os.path.join(ripplebase_path, 'server.py')])

class ClientTest(unittest.TestCase):
    def setUp(self):
        db.reset()
        self.server = make_server()

    def tearDown(self):
        pass
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
        url = root_url + '/nodes/'
        data_dict = {u'name': u'my_node'}
        data = json.encode(data_dict)
        headers = {'content-type':
                       'application/json; charset=utf-8'}
        req = urllib.Request(url, data, headers)
        while True:  # try connecting until server is up
            try:
                response = urllib.urlopen(req)
            except urllib.HTTPError, he:
                # anything but 200 raises HTTPError (!?)
                if he.code == 201:  # created
                    break
                raise
            except urllib.URLError, ue:
                if ue.reason.args[0] in (10061, 111):  # connection refused
                    # wait for server to be up
                    import time
                    time.sleep(0.5)
                    continue
                raise

        # check node is there
        req = urllib.Request(url)
        response = urllib.urlopen(req)
        json_data = response.read()
        recv_data = json.decode(json_data)[0]
        self.assertEquals(recv_data, data_dict)

        req = urllib.Request(url + 'my_node')
        response = urllib.urlopen(req)
        json_data = response.read()
        recv_data = json.decode(json_data)
        self.assertEquals(recv_data, data_dict)

        
#     def test_address(self):
#         pass
