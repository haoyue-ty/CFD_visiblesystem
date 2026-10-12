import hmac
from urllib.parse import urlsplit

from flask import g, request

from backend.api.catalog import Operation
from backend.core.errors import system_error
from backend.models.auth import AuthSessionResponse, EmailChallengeResponse, EmailCodeRequest, EmailSignInRequest

SESSION_COOKIE = 'shockpath_session'
CSRF_COOKIE = 'shockpath_csrf'


def check_csrf(service):
    cookie, header = request.cookies.get(CSRF_COOKIE, ''), request.headers.get('X-CSRF-Token', '')
    origin = request.headers.get('Origin')
    if origin:
        parsed = urlsplit(origin)
        if (parsed.scheme not in ('http', 'https')
                or (origin != request.host_url.rstrip('/') and origin not in service.settings.auth_trusted_origins)):
            raise system_error('CSRF_FAILED', '请求来源验证失败，请刷新页面后重试。', status=403, domain='ACCOUNT')
    if (request.headers.get('Sec-Fetch-Site') == 'cross-site' or not service.valid_csrf(cookie)
            or not hmac.compare_digest(cookie.encode(), header.encode())):
        raise system_error('CSRF_FAILED', '会话验证失败，请刷新页面后重试。', status=403, domain='ACCOUNT')


def register_auth_operations(catalog, settings, service):
    def enabled():
        if not settings.enable_accounts:
            raise system_error('FEATURE_NOT_ENABLED', '账号功能未启用。', status=503, domain='ACCOUNT')

    def session_payload(user=None, *, rotate=False):
        csrf = request.cookies.get(CSRF_COOKIE, '') if service else ''
        if service and (rotate or not service.valid_csrf(csrf)):
            csrf = service.csrf_token()
            g.auth_csrf_cookie = csrf
        return AuthSessionResponse(request_id=g.request_id, data={
            'enabled': settings.enable_accounts, 'authenticated': bool(user), 'user': user,
            'csrf_token': csrf, 'mail_configured': bool(service and service.mailer.configured),
        })

    def session(query):
        user = service.user(request.cookies.get(SESSION_COOKIE)) if service else None
        return session_payload(user)

    def challenge(query, body):
        enabled()
        check_csrf(service)
        result = service.send_code(body.email, body.purpose, request.remote_addr or 'unknown')
        return EmailChallengeResponse(request_id=g.request_id, data=result)

    def sign_in(purpose):
        def handler(query, body):
            enabled()
            check_csrf(service)
            user, token = service.sign_in(body.email, body.code, purpose, request.remote_addr or 'unknown', request.cookies.get(SESSION_COOKIE))
            g.auth_session_cookie = token
            return session_payload(user, rotate=True)
        return handler

    def logout(query):
        enabled()
        check_csrf(service)
        service.logout(request.cookies.get(SESSION_COOKIE))
        g.auth_session_cookie = ''
        return session_payload(rotate=True)

    common = {400: ('INVALID_REQUEST', 'INVALID_EMAIL', 'INVALID_VERIFICATION_CODE'),
              403: ('CSRF_FAILED',), 415: ('UNSUPPORTED_MEDIA_TYPE',),
              429: ('RATE_LIMITED', 'CODE_SEND_TOO_FREQUENT'),
              503: ('MAIL_SERVICE_UNAVAILABLE', 'ACCOUNT_STORE_UNAVAILABLE', 'FEATURE_NOT_ENABLED')}
    for method, path, identity, handler, body, response, status in (
        ('GET', '/session', 'AUTH01', session, None, AuthSessionResponse, 200),
        ('POST', '/email-verification-challenges', 'AUTH02', challenge, EmailCodeRequest, EmailChallengeResponse, 200),
        ('POST', '/register', 'AUTH03', sign_in('register'), EmailSignInRequest, AuthSessionResponse, 201),
        ('POST', '/login', 'AUTH04', sign_in('login'), EmailSignInRequest, AuthSessionResponse, 200),
        ('POST', '/logout', 'AUTH05', logout, None, AuthSessionResponse, 200),
    ):
        catalog.register(Operation(method=method, path='/api/v1/auth' + path, operation_id=identity,
                                   blueprint='accounts', service='AuthService', request_model=None,
                                   request_body_model=body, response_model=response, handler=handler,
                                   success_status=status, documented_errors={**common, 404: ('ACCOUNT_NOT_FOUND',), 409: ('ACCOUNT_ALREADY_EXISTS',)},
                                   auth_policy='ANONYMOUS' if method == 'GET' else 'SAME_ORIGIN_CSRF',
                                   request_headers=() if method == 'GET' else ('X-CSRF-Token',),
                                   delivery_phase='ACCOUNTS', description='Email verification and persistent server-side sessions.'))


def apply_auth_cookies(response, settings, service):
    hostname = urlsplit(request.host_url).hostname
    secure = settings.auth_cookie_secure or request.is_secure or hostname not in ('127.0.0.1', 'localhost', '::1')
    options = dict(httponly=True, secure=secure, samesite='Lax', path='/')
    if hasattr(g, 'auth_session_cookie'):
        if g.auth_session_cookie:
            response.set_cookie(SESSION_COOKIE, g.auth_session_cookie, max_age=service.session_ttl, **options)
        else:
            response.delete_cookie(SESSION_COOKIE, **options)
    if hasattr(g, 'auth_csrf_cookie'):
        response.set_cookie(CSRF_COOKIE, g.auth_csrf_cookie, max_age=service.session_ttl, **options)
    if getattr(g, 'auth_retry_after', None):
        response.headers['Retry-After'] = str(g.auth_retry_after)
    return response
