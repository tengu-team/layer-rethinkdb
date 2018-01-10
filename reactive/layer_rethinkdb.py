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
from charms import leadership
from charmhelpers.core import unitdata
from charmhelpers.core.templating import render
from charms.reactive import when, when_not, set_flag, is_flag_set
from charmhelpers.core.hookenv import status_set, open_port, close_port, config, leader_get, leader_set, unit_private_ip, local_unit

kv = unitdata.kv()

########################################################################
# Installation
########################################################################
@when('apt.installed.rethinkdb', 'secrets.configured')
@when_not('rethinkdb.installed')
def configure_rethinkdb():
    status_set('maintenance', 'configuring RethinkDB')
    install_service()
    set_password()
    status_set('active', 'RethinkDB is running with admin password: {}'.format(kv.get('password')))
    set_flag('rethinkdb.installed')

@when('rethinkdb.installed', 'config.changed')
def change_configuration():
    status_set('maintenance', 'configuring RethinkDB')
    conf = config()
    change_config(conf)
    subprocess.check_call(['sudo', '/etc/init.d/rethinkdb', 'restart'])
    status_set('active', 'RethinkDB is running with admin password: {}'.format(kv.get('password')))

########################################################################
# Leadership
########################################################################
@when('leadership.is_leader')
@when_not('secrets.configured')
def set_secrets():
    password = config()['admin_password']
    if  password == '':
        password = b64encode(os.urandom(18)).decode('utf-8')
    leader_set({'password': password, 'leader_ip': unit_private_ip()})
    kv.set('password', password)
    set_flag('secrets.configured')

@when_not('leadership.is_leader', 'secrets.configured')
def set_secrets_local():
    kv.set('password', leader_get('password'))
    set_flag('secrets.configured')

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
    cluster_port = conf['cluster_port']
    unit = local_unit().replace('/', '_')
    if conf['admin_console']:
        admin_console = ''
    else:
        admin_console = 'no-http-admin'
    clustering = ''
    conf_parameters = [str(port), str(driver_port), str(cluster_port), unit, admin_console, clustering]
    render_conf_file(conf_parameters)
    if conf['admin_console']:
        open_port(port)
    open_port(driver_port)
    open_port(cluster_port)
    kv.set('initial_state', True)
    subprocess.check_call(['sudo', '/etc/init.d/rethinkdb', 'restart'])

def set_password():
    subprocess.check_call(['sudo', 'apt-get', 'install', 'python3-pip'])
    subprocess.check_call(['sudo', 'pip3', 'install', 'rethinkdb'])
    import rethinkdb as r
    conn = r.connect(host="localhost", port=config()['driver_port'], db='rethinkdb').repl()
    r.table('users').get('admin').update({'password': kv.get('password')}).run()
    conn.close()

def change_config(conf):
    port = conf['port']
    driver_port = conf['driver_port']
    cluster_port = conf['cluster_port']
    unit = local_unit().replace('/', '_')
    old_port = conf.previous('port')
    old_driver_port = conf.previous('driver_port')
    old_cluster_port = conf.previous('cluster_port')
    if conf['admin_console']:
        admin_console = ''
    else:
        admin_console = 'no-http-admin'
    clustering = ''
    if not is_flag_set('leadership.is_leader'):
        clustering = 'join=' + leader_get('leader_ip') + ':' + str(cluster_port)
    conf_parameters = [str(port), str(driver_port), str(cluster_port), unit, admin_console, clustering]
    conf_state = [conf.changed('port'), conf.changed('driver_port'), conf.changed('cluster_port'), conf.changed('admin_console')]
    if True in conf_state:
        render_conf_file(conf_parameters)
        for former_port in [old_port, old_driver_port, old_cluster_port]:
            if former_port is not None:
                close_port(former_port)
        if conf['admin_console']:
            open_port(port)
        open_port(driver_port)
        open_port(cluster_port)
    if conf.changed('admin_password') and not kv.get('initial_state'):
        new_password = conf['admin_password']
        if is_flag_set('leadership.is_leader'):
            old_password = leader_get('password')
            import rethinkdb as r
            conn = r.connect(host="localhost", port=driver_port, db='rethinkdb', password=old_password).repl()
            r.table('users').get('admin').update({'password': new_password}).run()
            conn.close()
            leader_set({'password': new_password})
        kv.set('password', new_password)
    kv.set('initial_state', False)

def install_cluster(units):
    leader_available = check_for_leader(units)
    if len(units) > 0 and unit_private_ip() != leader_get('leader_ip') and leader_available:
        conf = config()
        port = conf['port']
        driver_port = conf['driver_port']
        cluster_port = conf['cluster_port']
        unit = local_unit().replace('/', '_')
        if conf['admin_console']:
            admin_console = ''
        else:
            admin_console = 'no-http-admin'
        clustering = 'join=' + leader_get('leader_ip') + ':' + str(cluster_port)
        conf_parameters = [str(port), str(driver_port), str(cluster_port), unit, admin_console, clustering]
        render_conf_file(conf_parameters)
        subprocess.check_call(['sudo', '/etc/init.d/rethinkdb', 'restart'])

def render_conf_file(conf_parameters):
    render(source='rethinkdb.conf',
           target='/etc/rethinkdb/instances.d/rethinkd.conf',
           context={
               'port': conf_parameters[0],
               'driver_port': conf_parameters[1],
               'cluster_port': conf_parameters[2],
               'rethinkdb_data': conf_parameters[3],
               'admin_console': conf_parameters[4],
               'clustering': conf_parameters[5]
           })

def check_for_leader(units):
    if leader_get('leader_ip') in units:
        return True
    elif not leader_get('leader_ip') in units and is_flag_set('leadership.is_leader'):
        leader_set({'leader_ip': unit_private_ip()})
        return True
    else:
        return False
