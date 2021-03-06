import click
import os
import sqlite3
from flask import (
    g,
    Flask,
    current_app
)
from flask.cli import with_appcontext

# Sqlite's Row factory works well, however, I REALLY
# want to return my records as plain dictionaries.
# Makes it easier to handle in any modules that use 
# this module.
# See https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.row_factory
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db():
    """
    Get a connection to the configured database
    A new one is created if it does not exist
    """
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'],
                               detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = dict_factory

    # Sqlite3 doesn't enable foreign keys by default.
    # See 2nd secion of the following link:
    # https://sqlite.org/foreignkeys.html
    g.db.execute("PRAGMA foreign_keys = ON;")

    return g.db

def close_db(e=None):
    """
    Close the connection to the database if it exists
    """
    db = g.pop('db', None)

    if db is not None:
        db.close()


def initialize_database():
    """
    Setup database schema 
    """
    db = get_db()

    with current_app.open_resource('sql/schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


def populate_database_with_test_data():
    """
    Populates the already existing database with test data
    """
    db = get_db()

    with current_app.open_resource('sql/bootstrap_db.sql') as f:
        db.executescript(f.read().decode('utf8'))



@click.command('init-db')
@with_appcontext
def init_db_command():
    """
    Clear the existing data and create new tables
    """
    initialize_database()
    populate_database_with_test_data()
    click.echo('Initialized database.')
    

def initialize_application(app):
    """
    Initialize the application by registering the `close_db` function to run on
    request teardown.

    Additionally, register cli commands
    """
    # Application teardown
    app.teardown_appcontext(close_db)

    # Cli commands
    app.cli.add_command(init_db_command)


def create_app(test_config=None):
    app = Flask("mirthful_rcis", instance_relative_config=True)

    # Initial configuration 
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, 'rci.sqlite')
    )

    if test_config is None:
        # load actual configuration
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test configuration
        app.config.from_mapping(test_config)

    # Ensure that the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    initialize_application(app)

    from mirthful_rcis.controllers import auth 
    from mirthful_rcis.controllers import dashboard
    from mirthful_rcis.controllers import rci
    from mirthful_rcis.controllers import damage
    from mirthful_rcis.controllers import settings

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(rci.bp)
    app.register_blueprint(damage.bp)
    app.register_blueprint(settings.bp)

    return app

