'''Test package initializer for `stuff/cron/tests`.

Cron scripts import `mysql.connector` at module load time so they can use
`mysql.connector.errorcode` for typed exception handling. The unit tests
in this directory never touch the database, so we stub the module out
before any cron script is imported. This lets the suite run on any
machine, regardless of whether the MySQL connector package is installed.
'''
import sys
import types


def _install_mysql_connector_stub() -> None:
    if 'mysql' in sys.modules:
        return
    mysql_pkg = types.ModuleType('mysql')
    connector_pkg = types.ModuleType('mysql.connector')
    errorcode_mod = types.ModuleType('mysql.connector.errorcode')
    # Only the constants the cron scripts actually reference need to exist.
    errorcode_mod.ER_LOCK_DEADLOCK = 1213
    errorcode_mod.ER_LOCK_WAIT_TIMEOUT = 1205
    connector_pkg.errorcode = errorcode_mod
    mysql_pkg.connector = connector_pkg
    sys.modules['mysql'] = mysql_pkg
    sys.modules['mysql.connector'] = connector_pkg
    sys.modules['mysql.connector.errorcode'] = errorcode_mod


_install_mysql_connector_stub()
