import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app import create_app, db
from config import Config


def pytest_addoption(parser):
    parser.addoption('--postgres', action='store_true', help='Run against DATABASE_URL using isolated schemas.')


@pytest.fixture
def app(request):
    url = os.getenv('TEST_DATABASE_URL', 'sqlite://')
    if request.config.getoption('--postgres'):
        url = os.getenv('TEST_DATABASE_URL') or Config.SQLALCHEMY_DATABASE_URI
        if not url or make_url(url).get_backend_name() != 'postgresql':
            pytest.fail('--postgres requires a PostgreSQL DATABASE_URL in .env.')
    schema = None
    admin = None
    options = {}
    if make_url(url).get_backend_name() == 'postgresql':
        # Every test owns a fresh schema; existing application tables are untouched.
        schema = 'test_' + uuid.uuid4().hex
        admin = create_engine(url)
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        options = {'execution_options': {'schema_translate_map': {None: schema}}}
    application = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': url,
                              'SQLALCHEMY_ENGINE_OPTIONS': options})
    try:
        with application.app_context():
            db.create_all()
        yield application
    finally:
        with application.app_context():
            db.session.remove()
            db.engine.dispose()
        if admin:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def student():
    return {'first_name': 'Олена', 'last_name': 'Коваль',
            'email': 'olena@example.com', 'group': 'КН-21'}
