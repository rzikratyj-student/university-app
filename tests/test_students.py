import pytest
from sqlalchemy.engine import make_url


def test_page_and_assets(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'Реєстр студентів' in response.get_data(as_text=True)
    assert client.get('/static/js/app.js').status_code == 200
    assert client.get('/static/css/style.css').status_code == 200


def test_crud_persists_between_requests(client, student):
    created = client.post('/api/students', json=student)
    assert created.status_code == 201
    record = created.get_json()
    assert record['created_at']
    assert client.get('/api/students').get_json()['items'][0]['email'] == student['email']
    updated = client.put(f"/api/students/{record['id']}", json=student | {'group': 'КН-22'})
    assert updated.status_code == 200
    assert client.get('/api/students').get_json()['items'][0]['group'] == 'КН-22'
    assert client.delete(f"/api/students/{record['id']}").status_code == 204
    result = client.get('/api/students').get_json()
    assert result['items'] == []
    assert result['groups'] == []
    assert result['all_count'] == 0


def test_duplicate_email_normalization_and_rollback(client, student):
    assert client.post('/api/students', json=student | {'email': ' OLENA@EXAMPLE.COM '}).status_code == 201
    duplicate = client.post('/api/students', json=student)
    assert duplicate.status_code == 409
    assert 'email' in duplicate.get_json()['fields']
    assert client.post('/api/students', json=student | {'email': 'another@example.com'}).status_code == 201
    assert client.get('/api/students').get_json()['total'] == 2


def test_conflicting_update_does_not_change_record(client, student):
    client.post('/api/students', json=student)
    other = client.post('/api/students', json=student | {'email': 'other@example.com'}).get_json()
    response = client.put(f"/api/students/{other['id']}", json=student | {'first_name': 'Змінено'})
    assert response.status_code == 409
    persisted = client.get('/api/students?q=other').get_json()['items'][0]
    assert persisted['first_name'] == student['first_name']
    assert persisted['email'] == 'other@example.com'


@pytest.mark.parametrize('changes,field', [
    ({'first_name': '  '}, 'first_name'), ({'last_name': None}, 'last_name'),
    ({'first_name': 42}, 'first_name'), ({'group': 'X' * 41}, 'group'),
    ({'email': 'wrong'}, 'email'), ({'last_name': 'X' * 81}, 'last_name'),
    ({'group': 'КН\n21'}, 'group'),
])
def test_validation(client, student, changes, field):
    response = client.post('/api/students', json=student | changes)
    assert response.status_code == 400
    assert field in response.get_json()['fields']
    assert client.get('/api/students').get_json()['total'] == 0


def test_invalid_json_and_missing_fields(client):
    assert client.post('/api/students', json=[]).status_code == 400
    assert client.post('/api/students', json={}).status_code == 400
    assert client.post('/api/students', data='{', content_type='application/json').status_code == 400
    assert client.post('/api/students', data='anything').status_code == 415


def test_missing_student(client, student):
    assert client.put('/api/students/123', json=student).status_code == 404
    assert client.delete('/api/students/123').status_code == 404


def test_search_filters_and_pagination(client, student):
    for index in range(12):
        assert client.post('/api/students', json=student | {
            'email': f'person{index}@example.com', 'group': 'КН-21' if index < 6 else 'КН-22',
        }).status_code == 201
    result = client.get('/api/students?page=2&per_page=10').get_json()
    assert len(result['items']) == 2
    assert result['total'] == 12
    filtered = client.get('/api/students', query_string={'q': 'Олена Коваль', 'group': 'КН-22'}).get_json()
    assert filtered['total'] == 6
    assert filtered['groups'] == ['КН-21', 'КН-22']
    assert filtered['all_count'] == 12
    assert client.get('/api/students?q=PERSON10').get_json()['total'] == 1
    assert client.get('/api/students?q=%25').get_json()['total'] == 0
    assert client.get('/api/students?q=_').get_json()['total'] == 0


def test_cyrillic_case_insensitive_search(client, student, app):
    if make_url(app.config['SQLALCHEMY_DATABASE_URI']).get_backend_name() == 'sqlite':
        pytest.skip('SQLite does not support Unicode case folding; run with PostgreSQL.')
    client.post('/api/students', json=student)
    assert client.get('/api/students', query_string={'q': 'олена'}).get_json()['total'] == 1


@pytest.mark.parametrize('query', ['page=0', 'page=abc', 'per_page=0', 'per_page=101'])
def test_invalid_pagination(client, query):
    assert client.get('/api/students?' + query).status_code == 400
