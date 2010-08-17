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

"""Regression test for dnsnamedimporter

Make sure you are running this against a database that can be destroyed.

DO NOT EVER RUN THIS TEST AGAINST A PRODUCTION DATABASE.
"""

__copyright__ = 'Copyright (C) 2009, Purdue University'
__license__ = 'BSD'
__version__ = '#TRUNK#'


import os
import sys
import socket

import unittest
import roster_core

CONFIG_FILE = 'test_data/roster.conf' # Example in test_data
SCHEMA_FILE = '../roster-core/data/database_schema.sql'
DATA_FILE = 'test_data/test_data.sql'
USERNAME = u'sharrell'
PASSWORD = u'test'
EXEC='../roster-config-manager/scripts/dnsnamedimporter'
NAMED_FILE = 'test_data/named.example.conf'

class TestDnsNamedImport(unittest.TestCase):

  def setUp(self):
    self.config_instance = roster_core.Config(file_name=CONFIG_FILE)

    db_instance = self.config_instance.GetDb()

    self.db_instance.CreateRosterDatabase()

    data = open(DATA_FILE, 'r').read()
    db_instance.StartTransaction()
    db_instance.cursor.execute(data)
    db_instance.EndTransaction()
    db_instance.close()

    self.core_instance = roster_core.Core(USERNAME, self.config_instance)

  def testNamedImport(self):
    command = os.popen('python %s -c %s -u %s -f %s -e set1' % (
        EXEC, CONFIG_FILE, USERNAME, NAMED_FILE))
    self.assertEqual(
        command.read(), '17 total records added\n23 total records added\n')
    command.close()

    self.assertEqual(self.core_instance.ListDnsServerSets(), ['set1'])

    self.assertEqual(self.core_instance.ListNamedConfGlobalOptions(
        dns_server_set=u'set1')[0]['options'],
        u'include "/etc/rndc.key";\nlogging { category "update-security" '
        '{ "security"; };\ncategory "queries" { "query_logging"; };\n'
        'channel "query_logging" { syslog local5;\nseverity info; };\n'
        'category "client" { "null"; };\nchannel "security" { file '
        '"/var/log/named-security.log" versions 10 size 10m;\nprint-time yes;\n'
        'print-time yes; }; };\noptions { directory "/var/domain";\n'
        'recursion yes;\nallow-query { any; };\nmax-cache-size 512M; };\n'
        'controls { keys { rndc-key; };\ninet * allow { control-hosts; }; };')

    self.assertEqual(self.core_instance.ListViews(),
        {u'authorized': u'allow-recursion { network-authorized; };\n'
                         'recursion yes;\nmatch-clients { network-authorized; '
                         '};\nallow-query-cache { network-authorized; };\n'
                         'additional-from-cache yes;\n'
                         'additional-from-auth yes;',
         u'unauthorized': u'recursion no;\nadditional-from-cache no;\n'
                           'match-clients { network-unauthorized; };\n'
                           'additional-from-auth no;'})

    self.assertEqual(self.core_instance.ListZones(),
        {u'university.edu':
            {u'authorized':
                {'zone_type': u'slave',
                 'zone_options': u'masters { 192.168.11.37; };\n'
                                  'check-names ignore;',
                 'zone_origin': u'university.edu.'},
             u'any': {'zone_type': u'slave',
                      'zone_options': u'masters { 192.168.11.37; };\n'
                                       'check-names ignore;',
                      'zone_origin': u'university.edu.'}},
         u'cache':
            {u'authorized': {'zone_type': u'hint',
                             'zone_options': u'', 'zone_origin': u'.'},
             u'unauthorized': {'zone_type': u'hint', 'zone_options': u'',
                               'zone_origin': u'.'},
             u'any': {'zone_type': u'hint', 'zone_options': u'',
                      'zone_origin': u'.'}},
         u'smtp.university.edu':
            {u'authorized': {'zone_type': u'master',
                             'zone_options': u'masters { 192.168.11.37; };',
                             'zone_origin': u'smtp.university.edu.'},
             u'any': {'zone_type': u'master',
                      'zone_options': u'masters { 192.168.11.37; };',
                      'zone_origin': u'smtp.university.edu.'}},
         u'1.210.128.in-addr.arpa':
            {u'any': {'zone_type': u'master',
                      'zone_options': u'allow-query { network-unauthorized; };',
                      'zone_origin': u'1.210.128.in-addr.arpa.'},
             u'unauthorized': {
                 'zone_type': u'master',
                 'zone_options': u'allow-query { network-unauthorized; };',
                 'zone_origin': u'1.210.128.in-addr.arpa.'}},
         u'0.0.127.in-addr.arpa':
            {u'any': {'zone_type': u'slave',
                      'zone_options': u'masters { 192.168.1.3; };',
                      'zone_origin': u'0.0.127.in-addr.arpa.'},
             u'unauthorized': {'zone_type': u'slave',
                               'zone_options': u'masters { 192.168.1.3; };',
                               'zone_origin': u'0.0.127.in-addr.arpa.'}}})

    self.assertEqual(self.core_instance.ListRecords(),
        [{u'admin_email': u'hostmaster.ns.university.edu.',
          u'expiry_seconds': 3600000,
          'last_user': u'sharrell',
          u'minimum_seconds': 86400,
          u'name_server': u'ns.university.edu.',
          'record_type': u'soa',
          u'refresh_seconds': 10800,
          u'retry_seconds': 3600,
          u'serial_number': 811,
          'target': u'@',
          'ttl': 3600,
          'view_name': u'authorized',
          'zone_name': u'smtp.university.edu'},
         {'last_user': u'sharrell',
          u'name_server': u'ns.sub.university.edu.',
          'record_type': u'ns',
          'target': u'@',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {'last_user': u'sharrell',
          u'name_server': u'ns2.sub.university.edu.',
          'record_type': u'ns',
          'target': u'@',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {'last_user': u'sharrell',
          u'mail_server': u'mail1.sub.university.edu.',
          u'priority': 10,
          'record_type': u'mx',
          'target': u'@',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {'last_user': u'sharrell',
          u'mail_server': u'mail2.sub.university.edu.',
          u'priority': 20,
          'record_type': u'mx',
          'target': u'@',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {'last_user': u'sharrell',
          u'quoted_text': u'"Contact 1:  Stephen Harrell (sharrell@university.edu)"',
          'record_type': u'txt',
          'target': u'@',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {u'assignment_ip': u'192.168.0.1',
          'last_user': u'sharrell',
          'record_type': u'a',
          'target': u'@',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {u'assignment_ip': u'3ffe:0800:0000:0000:02a8:79ff:fe32:1982',
          'last_user': u'sharrell',
          'record_type': u'aaaa',
          'target': u'desktop-1',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {u'assignment_ip': u'192.168.1.100',
          'last_user': u'sharrell',
          'record_type': u'a',
          'target': u'desktop-1',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {u'assignment_ip': u'192.168.1.104',
          'last_user': u'sharrell',
          'record_type': u'a',
          'target': u'ns2',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {u'hardware': u'PC',
          'last_user': u'sharrell',
          u'os': u'NT',
          'record_type': u'hinfo',
          'target': u'ns2',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {u'assignment_host': u'sub.university.edu.',
          'last_user': u'sharrell',
          'record_type': u'cname',
          'target': u'www',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {u'assignment_ip': u'192.168.1.103',
          'last_user': u'sharrell',
          'record_type': u'a',
          'target': u'ns',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {u'assignment_ip': u'127.0.0.1',
          'last_user': u'sharrell',
          'record_type': u'a',
          'target': u'localhost',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {u'assignment_host': u'ns.university.edu.',
          'last_user': u'sharrell',
          'record_type': u'cname',
          'target': u'www.data',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {u'assignment_ip': u'192.168.1.101',
          'last_user': u'sharrell',
          'record_type': u'a',
          'target': u'mail1',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {u'assignment_ip': u'192.168.1.102',
          'last_user': u'sharrell',
          'record_type': u'a',
          'target': u'mail2',
          'ttl': 3600,
          'view_name': u'any',
          'zone_name': u'smtp.university.edu'},
         {u'admin_email': u'hostmaster.university.edu.',
          u'expiry_seconds': 3600000,
          'last_user': u'sharrell',
          u'minimum_seconds': 86400,
          u'name_server': u'ns.university.edu.',
          'record_type': u'soa',
          u'refresh_seconds': 10800,
          u'retry_seconds': 3600,
          u'serial_number': 10,
          'target': u'@',
          'ttl': 86400,
          'view_name': u'unauthorized',
          'zone_name': u'1.210.128.in-addr.arpa'},
         {'last_user': u'sharrell',
          u'name_server': u'ns.university.edu.',
          'record_type': u'ns',
          'target': u'@',
          'ttl': 86400,
          'view_name': u'any',
          'zone_name': u'1.210.128.in-addr.arpa'},
         {'last_user': u'sharrell',
          u'name_server': u'ns2.university.edu.',
          'record_type': u'ns',
          'target': u'@',
          'ttl': 86400,
          'view_name': u'any',
          'zone_name': u'1.210.128.in-addr.arpa'},
         {u'assignment_host': u'router.university.edu.',
          'last_user': u'sharrell',
          'record_type': u'ptr',
          'target': u'1',
          'ttl': 86400,
          'view_name': u'any',
          'zone_name': u'1.210.128.in-addr.arpa'},
         {u'assignment_host': u'desktop-1.university.edu.',
          'last_user': u'sharrell',
          'record_type': u'ptr',
          'target': u'11',
          'ttl': 86400,
          'view_name': u'any',
          'zone_name': u'1.210.128.in-addr.arpa'},
         {u'assignment_host': u'desktop-2.university.edu.',
          'last_user': u'sharrell',
          'record_type': u'ptr',
          'target': u'12',
          'ttl': 86400,
          'view_name': u'any',
          'zone_name': u'1.210.128.in-addr.arpa'}])

if( __name__ == '__main__' ):
      unittest.main()