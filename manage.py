from __future__ import print_function
from webserver import create_app
import subprocess
import os
import click
import config

from metadb import db

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')

cli = click.Group()

def _run_psql(script, database=None):
    script = os.path.join(ADMIN_SQL_DIR, script)
    command = ['psql', '-p', config.PG_PORT, '-U', config.PG_SUPER_USER, '-f', script]
    if database:
        command.extend(['-d', database])
    exit_code = subprocess.call(command)

    return exit_code


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8080, show_default=True)
@click.option("--debug", "-d", type=bool,
              help="Turns debugging mode on or off. If specified, overrides "
                   "'DEBUG' value in the config file.")
def runserver(host, port, debug):
    create_app().run(host=host, port=port, debug=debug)


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
def init_db(force):
    """Initializes database.

    This process involves several steps:
    1. Table structure is created.
    2. Primary keys and foreign keys are created.
    3. Indexes are created.
    """
    if force:
        exit_code = _run_psql('drop_db.sql')
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating user and a database...')
    exit_code = _run_psql('create_db.sql')
    if exit_code != 0:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    print('Creating database extensions...')
    exit_code = _run_psql('create_extensions.sql', 'metadb')
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)

    print('Creating tables...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))

    print('Creating primary and foreign keys...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))

    print('Creating indexes...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
def init_test_db(force=False):
    """Same as `init_db` command, but creates a database that will be used to run tests.

    `TEST_SQLALCHEMY_DATABASE_URI` variable must be defined in the config file.
    """
    if force:
        exit_code = _run_psql('drop_test_db.sql')
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating database and user for testing...')
    exit_code = _run_psql('create_test_db.sql')
    if exit_code != 0:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    exit_code = _run_psql('create_extensions.sql', 'mdb_test')
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    db.init_db_engine(config.TEST_SQLALCHEMY_DATABASE_URI)

    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


if __name__ == '__main__':
    cli()
