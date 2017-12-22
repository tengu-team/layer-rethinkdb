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

import subprocess
from charms import leadership
from charmhelpers.core.templating import render
from charms.reactive import when, when_not, set_flag
from charmhelpers.core.hookenv import status_set, open_port, close_port, config, leader_get, leader_set, unit_private_ip

########################################################################
# Installation
########################################################################
@when('apt.installed.rethinkdb')
@when_not('rethinkdb.installed')
def configure_rethinkdb():
    status_set('maintenance', 'configuring RethinkDB')
    install_service()
    status_set('active', 'RethinkDB is running')
    set_flag('rethinkdb.installed')

@when('rethinkdb.installed', 'config.changed')
def change_configuration():
    status_set('maintenance', 'configuring RethinkDB')
    conf = config()
    change_config(conf)
    subprocess.check_call(['sudo', '/etc/init.d/rethinkdb', 'restart'])
    status_set('active', 'RethinkDB is running')

########################################################################
# Leadership
########################################################################
@when('leadership.is_leader')
def locate_leader():
    leader_set({'leader_ip': unit_private_ip()})

########################################################################
# Clustering
########################################################################
@when('cluster.connected')
def configure_cluster(cluster):
    units = cluster.get_peer_addresses()
    install_cluster(units)

########################################################################
# Auxiliary methods
########################################################################
def install_service():
    conf = config()
    port = conf['port']
    driver_port = conf['driver_port']
    render(source='rethinkdb.conf',
           target='/etc/rethinkdb/instances.d/rethinkd.conf',
           context={
               'port': str(port),
               'driver_port': str(driver_port),
               'clustering': ''
           })
    open_port(port)
    open_port(driver_port)
    subprocess.check_call(['sudo', '/etc/init.d/rethinkdb', 'restart'])

def change_config(conf):
    port = conf['port']
    driver_port = conf['driver_port']
    old_port = conf.previous('port')
    old_driver_port = conf.previous('driver_port')
    if conf.changed('port') or conf.changed('driver_port'):
        render(source='rethinkdb.conf',
               target='/etc/rethinkdb/instances.d/rethinkd.conf',
               context={
                   'port': str(port),
                   'driver_port': str(driver_port),
                   'clustering': ''
               })
        if old_port is not None:
            close_port(old_port)
        if old_driver_port is not None:
            close_port(old_driver_port)
        open_port(port)
        open_port(driver_port)

def install_cluster(units):
    if len(units) > 0 and unit_private_ip() != leader_get('leader_ip'):
        conf = config()
        port = conf['port']
        driver_port = conf['driver_port']
        render(source='rethinkdb.conf',
               target='/etc/rethinkdb/instances.d/rethinkd.conf',
               context={
                   'port': str(port),
                   'driver_port': str(driver_port),
                   'clustering': 'join=' + leader_get('leader_ip') + ':29015'
               })
        subprocess.check_call(['sudo', '/etc/init.d/rethinkdb', 'restart'])
