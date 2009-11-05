#!/usr/bin/python

# Copyright (c) 2009, Purdue University
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice, this
# list of conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.
# 
# Neither the name of the Purdue University nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Regression test for dnsrmview

Make sure you are running this against a database that can be destroyed.

DO NOT EVER RUN THIS TEST AGAINST A PRODUCTION DATABASE.
"""

__copyright__ = 'Copyright (C) 2009, Purdue University'
__license__ = 'BSD'
__version__ = '#TRUNK#'


import os
import sys
import socket
import threading
import time
import getpass

import unittest

import roster_core
from roster_user_tools import roster_client_lib
import roster_server

USER_CONFIG = 'test_data/roster_user_tools.conf'
CONFIG_FILE = 'test_data/roster.conf' # Example in test_data
SCHEMA_FILE = '../roster-core/data/database_schema.sql'
DATA_FILE = 'test_data/test_data.sql'
HOST = u'localhost'
USERNAME = u'sharrell'
PASSWORD = u'test'
KEYFILE=('test_data/dnsmgmt.key.pem')
CERTFILE=('test_data/dnsmgmt.cert.pem')
CREDFILE='%s/.dnscred' % os.getcwd()
EXEC = '../roster-user-tools/scripts/dnsrmview'

class options(object):
  password = u'test'
  username = u'sharrell'
  server = None
  ldap = u'ldaps://ldap.cs.university.edu:636'
  credfile = CREDFILE
  view_name = None
  ip_address = None
  target = u'machine1'
  ttl = 64

class DaemonThread(threading.Thread):
  def __init__(self, config_instance, port):
    threading.Thread.__init__(self)
    self.config_instance = config_instance
    self.port = port
    self.daemon_instance = None

  def run(self):
    self.daemon_instance = roster_server.Server(self.config_instance, KEYFILE,
                                                CERTFILE)
    self.daemon_instance.Serve(port=self.port)

class Testdnsrmview(unittest.TestCase):

  def setUp(self):

    def PickUnusedPort():
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.bind((HOST, 0))
      addr, port = s.getsockname()
      s.close()
      return port

    self.config_instance = roster_core.Config(file_name=CONFIG_FILE)

    db_instance = self.config_instance.GetDb()

    schema = open(SCHEMA_FILE, 'r').read()
    db_instance.StartTransaction()
    db_instance.cursor.execute(schema)
    db_instance.EndTransaction()

    data = open(DATA_FILE, 'r').read()
    db_instance.StartTransaction()
    db_instance.cursor.execute(data)
    db_instance.EndTransaction()
    db_instance.close()

    self.port = PickUnusedPort()
    self.server_name = 'https://%s:%s' % (HOST, self.port)
    self.daemon_thread = DaemonThread(self.config_instance, self.port)
    self.daemon_thread.start()
    self.core_instance = roster_core.Core(USERNAME, self.config_instance)
    self.password = 'test'
    time.sleep(1)
    roster_client_lib.GetCredentials(USERNAME, u'test', credfile=CREDFILE,
                                     server_name=self.server_name)

  def tearDown(self):
    if( os.path.exists(CREDFILE) ):
      os.remove(CREDFILE)

  def testRemoveZoneView(self):
    self.core_instance.MakeView(u'test_view')
    output = os.popen('python %s -v test_view '
                      '-s %s -u %s -p %s --config-file %s' % (
                          EXEC, self.server_name, USERNAME,
                          PASSWORD, USER_CONFIG))
    self.assertEqual(output.read(), 'REMOVED VIEW: test_view\n')
    output.close()
    self.assertEqual(self.core_instance.ListViews(), {})

  def testRemoveDnsServerSetViewAssignments(self):
    self.core_instance.MakeView(u'test_view')
    self.core_instance.MakeDnsServer(u'dns1')
    self.core_instance.MakeDnsServerSet(u'set1')
    self.core_instance.MakeDnsServerSetAssignments(u'dns1', u'set1')
    self.core_instance.MakeDnsServerSetViewAssignments(u'test_view', u'set1')
    self.assertEqual(self.core_instance.ListDnsServerSetViewAssignments(),
        {u'set1': [u'test_view']})
    self.assertEqual(self.core_instance.ListDnsServerSetAssignments(),
        {u'set1': [u'dns1']})
    self.assertEqual(self.core_instance.ListDnsServerSets(), [u'set1'])
    self.assertEqual(self.core_instance.ListDnsServers(), [u'dns1'])
    output = os.popen('python %s -v test_view -e set1 '
                      '-s %s -u %s -p %s --config-file %s' % (
                          EXEC, self.server_name, USERNAME,
                          PASSWORD, USER_CONFIG))
    self.assertEqual(output.read(),
                     'REMOVED DNS SERVER SET VIEW ASSIGNMENT: '
                     'view_name test_view dns_server_set: set1\n')
    output.close()
    self.assertEqual(self.core_instance.ListDnsServerSetViewAssignments(), {})
    self.assertEqual(self.core_instance.ListDnsServerSetAssignments(),
        {u'set1': [u'dns1']})

  def testRemoveAcl(self):
    self.core_instance.MakeACL(u'acl', u'192.168.0.0/24', 1)
    self.assertEqual(self.core_instance.ListACLs(),
                     {u'any': [{'cidr_block': None, 'range_allowed': 1}],
                      u'acl': [{'cidr_block': u'192.168.0.0/24',
                       'range_allowed': 1}]})
    output = os.popen('python %s --acl acl '
                      '--cidr-block 192.168.0.0/24 --allow '
                      '-s %s -u %s -p %s --config-file %s' % (
                          EXEC, self.server_name, USERNAME,
                          PASSWORD, USER_CONFIG))
    self.assertEqual(output.read(),
                     'REMOVED ACL: acl_name: acl cidr_block: 192.168.0.0/24 '
                     'range_allowed: True\n')
    output.close()
    self.assertEqual(self.core_instance.ListACLs(),
                     {u'any': [{'cidr_block': None, 'range_allowed': 1}]})

  def testErrors(self):
    output = os.popen('python %s -e test '
                      '-s %s -u %s -p %s --config-file %s' % (
                          EXEC, self.server_name, USERNAME,
                          PASSWORD, USER_CONFIG))
    self.assertEqual(output.read(), 'CLIENT ERROR: To remove a dns server set '
                                    'view assignment a view must be '
                                    'specified with the -v flag.\n')
    output.close()
    output = os.popen('python %s --acl acl '
                      '--allow '
                      '-s %s -u %s -p %s --config-file %s' % (
                          EXEC, self.server_name, USERNAME,
                          PASSWORD, USER_CONFIG))
    self.assertEqual(output.read(), 'CLIENT ERROR: To remove an ACL a CIDR '
                                    'block or ip address must be specified '
                                    'with the --cidr-block flag.\n')
    output.close()
    output = os.popen('python %s --acl acl '
                      '--cidr-block 192.168.0.0/24 --allow --deny '
                      '-s %s -u %s -p %s --config-file %s' % (
                          EXEC, self.server_name, USERNAME,
                          PASSWORD, USER_CONFIG))
    self.assertEqual(output.read(), 'CLIENT ERROR: --allow and --deny '
                                    'cannot be used simultaneously.\n')
    output.close()
    output = os.popen('python %s -v test --acl '
                      'test --cidr-block test '
                      '-s %s -u %s -p %s --config-file %s' % (
                          EXEC, self.server_name, USERNAME,
                          PASSWORD, USER_CONFIG))
    self.assertEqual(output.read(),
                     'CLIENT ERROR: The --acl flag cannot be used.\n'
                     'CLIENT ERROR: The --cidr-block flag cannot be used.\n')
    output.close()

if( __name__ == '__main__' ):
      unittest.main()
