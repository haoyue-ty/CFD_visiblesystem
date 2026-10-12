import concurrent.futures

import pytest

from backend import create_app
from backend.core.errors import DomainError
from backend.core.settings import Settings
from backend.services.auth import AuthService, QQMailer, account_error


class Clock:
    now = 1000000.0
    def __call__(self):
        return self.now


class Mailer:
    configured = True
    fail = False
    def __init__(self):
        self.messages = []
    def send(self, email, code, purpose, ttl):
        if self.fail:
            raise account_error('MAIL_SERVICE_UNAVAILABLE', 'Test mail failure', 503)
        self.messages.append((email, code, purpose))


@pytest.fixture
def auth(tmp_path):
    settings = Settings(enable_accounts=True, auth_database_url='sqlite:///' + str(tmp_path / 'accounts.sqlite3'),
                        auth_secret_key='test-only-hmac-key', qq_smtp_email='sender@qq.com', qq_smtp_auth_code='test-only-smtp-code')
    mailer, clock = Mailer(), Clock()
    service = AuthService(settings, mailer=mailer, clock=clock)
    app = create_app(settings=settings, auth_service=service)
    app.config['TESTING'] = True
    return app.test_client(), service, mailer, clock


def headers(client):
    token = client.get('/api/v1/auth/session').json['data']['csrf_token']
    return {'X-CSRF-Token': token}


def send(client, email='test@example.com', purpose='register'):
    return client.post('/api/v1/auth/email-verification-challenges', json={'email': email, 'purpose': purpose}, headers=headers(client))


def register(client, mailer, email='test@example.com'):
    assert send(client, email).status_code == 200
    return client.post('/api/v1/auth/register', json={'email': email, 'code': mailer.messages[-1][1]}, headers=headers(client))


def test_registration_session_persists_and_code_is_one_time(auth):
    client, service, mailer, clock = auth
    response = register(client, mailer, 'Test@Example.com')
    assert response.status_code == 201
    assert response.json['data']['user']['email'] == 'test@example.com'
    assert 'HttpOnly' in response.headers['Set-Cookie'] and 'SameSite=Lax' in response.headers['Set-Cookie']
    token = client.get_cookie('shockpath_session').value
    assert token not in response.text and mailer.messages[-1][1] not in response.text
    restarted = AuthService(service.settings, mailer=mailer, clock=clock)
    assert restarted.user(token)['email'] == 'test@example.com'
    with service.store.transaction() as db:
        row = db.execute('SELECT * FROM auth_challenges').fetchone()
        assert row['code_hash'] != mailer.messages[-1][1] and row['status'] == 'CONSUMED'
        assert db.execute('SELECT token_hash FROM auth_sessions').fetchone()['token_hash'] != token
    response = client.post('/api/v1/auth/register', json={'email': 'test@example.com', 'code': mailer.messages[-1][1]}, headers=headers(client))
    assert response.status_code == 400
    assert client.get('/api/v1/auth/session').json['data']['authenticated']
    clock.now += service.session_ttl + 1
    assert not client.get('/api/v1/auth/session').json['data']['authenticated']


def test_logout_revokes_session_and_login_rotates_cookie(auth):
    client, service, mailer, clock = auth
    assert register(client, mailer).status_code == 201
    old = client.get_cookie('shockpath_session').value
    response = client.post('/api/v1/auth/logout', headers=headers(client))
    assert response.status_code == 200 and not response.json['data']['authenticated']
    assert service.user(old) is None and client.get_cookie('shockpath_session') is None
    clock.now += 61
    assert send(client, purpose='login').status_code == 200
    response = client.post('/api/v1/auth/login', json={'email': 'test@example.com', 'code': mailer.messages[-1][1]}, headers=headers(client))
    assert response.status_code == 200
    assert client.get_cookie('shockpath_session').value != old


def test_wrong_attempts_commit_and_lock_code(auth):
    client, service, mailer, clock = auth
    assert send(client).status_code == 200
    correct = mailer.messages[-1][1]
    wrong = '999999' if correct != '999999' else '000000'
    for _ in range(5):
        response = client.post('/api/v1/auth/register', json={'email': 'test@example.com', 'code': wrong}, headers=headers(client))
        assert response.status_code == 400
    with service.store.transaction() as db:
        assert db.execute('SELECT attempts FROM auth_challenges').fetchone()['attempts'] == 5
    assert client.post('/api/v1/auth/register', json={'email': 'test@example.com', 'code': correct}, headers=headers(client)).status_code == 400


def test_expiry_and_purpose_binding(auth):
    client, service, mailer, clock = auth
    assert send(client).status_code == 200
    correct = mailer.messages[-1][1]
    assert client.post('/api/v1/auth/login', json={'email': 'test@example.com', 'code': correct}, headers=headers(client)).status_code == 400
    clock.now += service.code_ttl + 1
    assert client.post('/api/v1/auth/register', json={'email': 'test@example.com', 'code': correct}, headers=headers(client)).status_code == 400


def test_cooldown_hourly_limits_and_no_code_in_response(auth):
    client, service, mailer, clock = auth
    first = send(client)
    assert first.status_code == 200 and first.json['data']['delivery_status'] == 'SMTP_ACCEPTED'
    assert mailer.messages[-1][1] not in first.text
    limited = send(client)
    assert limited.status_code == 429 and limited.headers['Retry-After'] == '60'
    for _ in range(4):
        clock.now += 61
        assert send(client).status_code == 200
    clock.now += 61
    assert send(client).status_code == 429


def test_failed_smtp_does_not_replace_active_code(auth):
    client, service, mailer, clock = auth
    assert send(client).status_code == 200
    code = mailer.messages[-1][1]
    clock.now += 61
    mailer.fail = True
    assert send(client).status_code == 503
    assert client.post('/api/v1/auth/register', json={'email': 'test@example.com', 'code': code}, headers=headers(client)).status_code == 201


def test_csrf_origin_and_server_side_workspace_gate(auth):
    client, service, mailer, clock = auth
    url = '/api/v1/auth/email-verification-challenges'
    payload = {'email': 'test@example.com', 'purpose': 'register'}
    assert client.post(url, json=payload).status_code == 403
    assert client.post(url, json=payload, headers={**headers(client), 'Origin': 'https://foreign.example'}).status_code == 403
    assert client.post(url, json=payload, headers={'X-CSRF-Token': '非法'}).status_code == 403
    assert mailer.messages == []
    assert client.post(url, json={**payload, 'email': 'trusted@example.com'}, headers={**headers(client), 'Origin': 'http://127.0.0.1:5173'}).status_code == 200
    assert client.post('/api/v2/runs', json={}).status_code == 401
    assert register(client, mailer).status_code == 201
    assert client.post('/api/v2/runs', json={}).status_code == 403
    assert client.post('/api/v2/runs', json={}, headers=headers(client)).status_code == 400


def test_concurrent_code_consumption_creates_one_account(auth):
    client, service, mailer, clock = auth
    service.send_code('parallel@example.com', 'register', '127.0.0.1')
    code = mailer.messages[-1][1]
    def consume():
        try:
            service.sign_in('parallel@example.com', code, 'register', '127.0.0.1')
            return 'success'
        except DomainError:
            return 'rejected'
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: consume(), range(2)))
    assert sorted(results) == ['rejected', 'success']
    with service.store.transaction() as db:
        assert db.execute('SELECT COUNT(*) AS n FROM auth_users').fetchone()['n'] == 1


def test_email_validation_and_invalid_body(auth):
    client, service, mailer, clock = auth
    for value in ('bad', 'x\r\nBcc:other@example.com', 'a..b@example.com', 'a@-domain.com'):
        assert send(client, value).status_code == 400
    assert mailer.messages == []
    response = client.post('/api/v1/auth/register', data='email=abc', headers=headers(client))
    assert response.status_code == 415


def test_qq_mail_uses_verified_tls_and_requested_recipient(auth, monkeypatch):
    client, service, mailer, clock = auth
    captured = {}
    class SMTP:
        def __init__(self, host, port, timeout, context):
            import ssl
            assert host == 'smtp.qq.com' and port == 465 and timeout == 10
            assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def close(self): pass
        def login(self, email, password): captured['sender'] = email
        def send_message(self, message): captured['message'] = message; return {}
    monkeypatch.setattr('backend.services.auth.smtplib.SMTP_SSL', SMTP)
    QQMailer(service.settings).send('recipient@example.com', '123456', 'register', 600)
    assert captured['sender'] == 'sender@qq.com'
    assert captured['message']['To'] == 'recipient@example.com'
    assert '123456' in captured['message'].get_content()


def test_disabled_accounts_preserve_anonymous_mode(tmp_path):
    app = create_app(settings=Settings(enable_accounts=False))
    session = app.test_client().get('/api/v1/auth/session').json['data']
    assert not session['enabled'] and not session['authenticated']
    assert app.test_client().get('/api/v1/system').json['data']['account_extension']['enabled'] is False


def test_account_credentials_do_not_reach_solver_workers(tmp_path, monkeypatch):
    from backend.solver_runtime.case8_adapter import worker_environment
    for key in ('QQ_SMTP_EMAIL', 'QQ_SMTP_AUTH_CODE', 'AUTH_DATABASE_URL', 'AUTH_SECRET_KEY'):
        monkeypatch.setenv(key, 'test-only-server-value')
    environment = worker_environment(tmp_path)
    assert all(key not in environment for key in ('QQ_SMTP_EMAIL', 'QQ_SMTP_AUTH_CODE', 'AUTH_DATABASE_URL', 'AUTH_SECRET_KEY'))
