# Overview

RethinkDB is the first open-source, scalable JSON database built from
the ground up for the realtime web. This charm installs and
configures [RethinkDB](https://www.rethinkdb.com/).

# Usage

Deploy the RethinkDB charm with the following:

```bash
juju deploy cs:~tengu-team/rethinkdb-0
```
One can manage RethinkDB using:

- An appropriate client driver (see https://rethinkdb.com/docs/install-drivers/).

- The web interface, which can be made available at `http://x.x.x.x:port` (default port is 8080).

Note that the password for the admin user has to be given in the RethinkDB client in order to connect to the RethinkDB instance. The `admin_password` can be customized and it is shown in the *message* of charm's status. In order to access the web interface the option `admin_console` has to be set to `True`. The `admin_password` is not required in the case of the web console and we recommend to secure it by using proxies (see https://rethinkdb.com/docs/security/).  

Finally, clustering is possible by using the `juju add-unit` command.

# Contact Information

## Authors

 - Dixan Peña Peña <dixan.pena@tengu.io>
