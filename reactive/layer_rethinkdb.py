#!/usr/bin/python3
# Copyright (C) 2017  Qrama
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# pylint: disable=c0111,c0103,c0301
import os
import subprocess
from base64 import b64encode
from charmhelpers.core import unitdata
from charmhelpers.core.templating import render
from charmhelpers.core.host import service_restart
from charms.reactive import when, when_not, set_state
from charmhelpers.core.hookenv import status_set, open_port, close_port, config, unit_public_ip, unit_private_ip

@when('apt.installed.rethinkdb')
@when_not('rethinkdb.configured')
def configure_rethinkdb():
    status_set('maintenance', 'configuring RethinkDB')
    conf = config()
    port = conf['port']
    driver_port = conf['driver_port']
    render(source='rethinkdb.conf',
           target='/etc/rethinkdb/instances.d/instance1.conf',
           context={
               'port': str(port),
               'driver_port': str(driver_port)
           })
    open_port(port)
    set_state('rethinkdb.configured')

@when('rethinkdb.configured')
@when_not('rethinkdb.running')
def start_rethinkdb():
    subprocess.check_call(['sudo', '/etc/init.d/rethinkdb', 'restart'])
    status_set('active', 'RethinkDB running')
    set_state('rethinkdb.running')

@when('rethinkdb.running', 'config.changed')
def change_configuration():
    status_set('maintenance', 'configuring RethinkDB')
    conf = config()
    port = conf['port']
    driver_port = conf['driver_port']
    old_port = conf.previous('port')
    old_driver_port = conf.previous('driver_port')
    if conf.changed('port') or conf.changed('driver_port'):
        render(source='rethinkdb.conf',
               target='/etc/rethinkdb/instances.d/instance1.conf',
               context={
                   'port': str(port),
                   'driver_port': str(driver_port)
               })
        if old_port is not None:
            close_port(old_port)
        if old_driver_port is not None:
            close_port(old_driver_port)
        open_port(port)
        open_port(driver_port)
    subprocess.check_call(['sudo', '/etc/init.d/rethinkdb', 'restart'])
    status_set('active', 'RethinkDB running')
