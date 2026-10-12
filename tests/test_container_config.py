import pytest
from sqlalchemy.engine import make_url

from config import database_uri


def test_file_secret_selects_isolated_database(monkeypatch, tmp_path):
    path = tmp_path / 'test-secret'
    value = 'test' + ':@/only'
    path.write_text(value, encoding='utf-8')
    monkeypatch.setenv('DB_PASSWORD_FILE', str(path))
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    monkeypatch.setenv('DB_USER', 'isolated_user')
    monkeypatch.setenv('DB_HOST', 'db')
    monkeypatch.setenv('DB_NAME', 'isolated_db')
    monkeypatch.setenv('DB_PORT', '5432')
    url = make_url(database_uri())
    assert (url.host, url.database, url.username) == ('db', 'isolated_db', 'isolated_user')
    assert url.password == value
    assert value not in str(url)


def test_empty_secret_refused(monkeypatch, tmp_path):
    path = tmp_path / 'empty-secret'
    path.write_text('', encoding='utf-8')
    monkeypatch.setenv('DB_PASSWORD_FILE', str(path))
    with pytest.raises(RuntimeError, match='empty'):
        database_uri()


def test_explicit_url_without_secret_file(monkeypatch):
    monkeypatch.delenv('DB_PASSWORD_FILE', raising=False)
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    assert database_uri() == 'sqlite://'
