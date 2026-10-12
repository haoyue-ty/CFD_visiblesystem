import hashlib
import hmac
from email.message import EmailMessage
from email.utils import formataddr
import re
import secrets
import smtplib
import ssl
import time
from uuid import uuid4

from backend.core.errors import system_error
from backend.core.settings import WORKSPACE_ROOT
from backend.services.auth_store import AuthStore


def account_error(code, message, status=400, retry_after=None):
    error = system_error(code, message, status=status, domain='ACCOUNT', retryable=status in (429, 503))
    error.retry_after = retry_after
    return error


def normalize_email(email):
    email = email.strip().lower()
    if (not re.fullmatch(r"[a-z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", email)
            or len(email) > 254 or len(email.split('@')[0]) > 64 or '..' in email
            or email.startswith('.') or '.@' in email or any(p.startswith('-') or p.endswith('-') for p in email.split('@')[1].split('.'))):
        raise account_error('INVALID_EMAIL', '请输入有效的邮箱地址。')
    return email


class QQMailer:
    def __init__(self, settings):
        self.settings = settings

    @property
    def configured(self):
        return bool(self.settings.qq_smtp_email and self.settings.qq_smtp_auth_code.get_secret_value())

    def send(self, email, code, purpose, ttl):
        if not self.configured:
            raise account_error('MAIL_SERVICE_UNAVAILABLE', '验证码邮件服务尚未配置，请联系管理员。', 503)
        action = '注册' if purpose == 'register' else '登录'
        message = EmailMessage()
        message['Subject'] = f'ShockPath {action}验证码'
        message['From'] = formataddr(('ShockPath', self.settings.qq_smtp_email))
        message['To'] = email
        message.set_content(f'你的 ShockPath {action}验证码是：{code}\n\n有效期 {ttl // 60} 分钟，仅可使用一次。\n如果这不是你的操作，请忽略本邮件。')
        smtp = None
        try:
            smtp = smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=10, context=ssl.create_default_context())
            smtp.login(self.settings.qq_smtp_email, self.settings.qq_smtp_auth_code.get_secret_value())
            if smtp.send_message(message):
                raise smtplib.SMTPException('Recipient refused')
        except (smtplib.SMTPException, OSError):
            raise account_error('MAIL_SERVICE_UNAVAILABLE', '验证码邮件发送失败，请稍后重试。', 503) from None
        finally:
            if smtp:
                smtp.close()


class AuthService:
    code_ttl = 600
    cooldown = 60
    session_ttl = 86400
    max_attempts = 5

    def __init__(self, settings, *, store=None, mailer=None, clock=time.time):
        self.settings = settings
        self.store = store or AuthStore(settings.auth_database_url.get_secret_value())
        self.mailer = mailer or QQMailer(settings)
        self.clock = clock
        self._secret = None

    @property
    def secret(self):
        if self._secret is None:
            value = self.settings.auth_secret_key.get_secret_value()
            if not value:
                from backend.solver_runtime.run_store import file_lock
                root = WORKSPACE_ROOT / 'runtime' / 'auth'
                root.mkdir(parents=True, exist_ok=True)
                with file_lock(root / 'secret.lock'):
                    path = root / 'secret.key'
                    if not path.exists():
                        path.write_text(secrets.token_hex(32), encoding='ascii')
                    value = path.read_text(encoding='ascii').strip()
            self._secret = value.encode()
        return self._secret

    def digest(self, value):
        return hmac.new(self.secret, value.encode(), hashlib.sha256).hexdigest()

    def csrf_token(self):
        nonce = secrets.token_urlsafe(32)
        return nonce + '.' + self.digest('csrf:' + nonce)

    def valid_csrf(self, token):
        if not token or not re.fullmatch(r'[A-Za-z0-9_-]{43}\.[0-9a-f]{64}', token):
            return False
        nonce, signature = token.split('.', 1)
        return hmac.compare_digest(signature, self.digest('csrf:' + nonce))

    @staticmethod
    def token_hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def user(self, token):
        if not token or len(token) > 128:
            return None
        with self.store.transaction() as db:
            row = db.execute('SELECT u.id,u.email FROM auth_users u JOIN auth_sessions s ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?', (self.token_hash(token), self.clock())).fetchone()
            return dict(row) if row else None

    def send_code(self, email, purpose, ip):
        email = normalize_email(email)
        if purpose not in ('register', 'login'):
            raise account_error('INVALID_REQUEST', '验证码用途不合法。')
        if not self.mailer.configured:
            raise account_error('MAIL_SERVICE_UNAVAILABLE', '验证码邮件服务尚未配置，请联系管理员。', 503)
        now, identity, code = self.clock(), str(uuid4()), f'{secrets.randbelow(1000000):06d}'
        ip_hash = self.digest('ip:' + ip)
        with self.store.transaction() as db:
            db.execute('DELETE FROM auth_challenges WHERE created_at<?', (now - 86400,))
            db.execute('DELETE FROM auth_attempts WHERE created_at<?', (now - 86400,))
            db.execute('DELETE FROM auth_sessions WHERE expires_at<=?', (now,))
            latest = db.execute('SELECT created_at FROM auth_challenges WHERE email=? ORDER BY created_at DESC LIMIT 1', (email,)).fetchone()
            if latest and now - latest['created_at'] < self.cooldown:
                delay = max(1, int(self.cooldown - (now - latest['created_at']) + .999))
                raise account_error('CODE_SEND_TOO_FREQUENT', f'请等待 {delay} 秒后重新发送。', 429, delay)
            email_count = db.execute('SELECT COUNT(*) AS n FROM auth_challenges WHERE email=? AND created_at>?', (email, now - 3600)).fetchone()['n']
            ip_count = db.execute('SELECT COUNT(*) AS n FROM auth_challenges WHERE ip_hash=? AND created_at>?', (ip_hash, now - 3600)).fetchone()['n']
            if email_count >= 5 or ip_count >= 20:
                raise account_error('RATE_LIMITED', '验证码请求次数过多，请稍后重试。', 429, 3600)
            db.execute('INSERT INTO auth_challenges VALUES (?,?,?,?,?,?,?,?,?)', (identity, email, purpose, self.digest(f'code:{identity}:{email}:{purpose}:{code}'), ip_hash, now, now + self.code_ttl, 0, 'PENDING'))
        # No database lock is held during the SMTP network operation.
        try:
            self.mailer.send(email, code, purpose, self.code_ttl)
        except Exception:
            with self.store.transaction() as db:
                db.execute("UPDATE auth_challenges SET status='FAILED' WHERE id=?", (identity,))
            raise
        with self.store.transaction() as db:
            latest = db.execute("SELECT id,created_at FROM auth_challenges WHERE email=? AND purpose=? AND status IN ('ACTIVE','CONSUMED') ORDER BY created_at DESC LIMIT 1", (email, purpose)).fetchone()
            if not latest or latest['created_at'] <= now:
                db.execute("UPDATE auth_challenges SET status='REPLACED' WHERE email=? AND purpose=? AND status='ACTIVE'", (email, purpose))
                db.execute("UPDATE auth_challenges SET status='ACTIVE' WHERE id=?", (identity,))
            else:
                db.execute("UPDATE auth_challenges SET status='REPLACED' WHERE id=?", (identity,))
        return {'expires_in': self.code_ttl, 'retry_after': self.cooldown}

    def sign_in(self, email, code, purpose, ip, previous_token=None):
        email = normalize_email(email)
        now, failure, user, token = self.clock(), None, None, None
        ip_hash = self.digest('ip:' + ip)
        with self.store.transaction() as db:
            db.execute('DELETE FROM auth_attempts WHERE created_at<?', (now - 86400,))
            count = db.execute('SELECT COUNT(*) AS n FROM auth_attempts WHERE ip_hash=? AND created_at>?', (ip_hash, now - 900)).fetchone()['n']
            if count >= 20:
                raise account_error('RATE_LIMITED', '验证次数过多，请稍后重试。', 429, 900)
            db.execute('INSERT INTO auth_attempts VALUES (?,?,?)', (str(uuid4()), ip_hash, now))
            row = db.execute("SELECT * FROM auth_challenges WHERE email=? AND purpose=? AND status='ACTIVE' ORDER BY created_at DESC LIMIT 1", (email, purpose)).fetchone()
            if not row or row['expires_at'] <= now or row['attempts'] >= self.max_attempts:
                failure = account_error('INVALID_VERIFICATION_CODE', '验证码无效、已过期或验证次数已用尽，请重新获取。')
            elif not hmac.compare_digest(row['code_hash'], self.digest(f"code:{row['id']}:{email}:{purpose}:{code}")):
                db.execute('UPDATE auth_challenges SET attempts=attempts+1 WHERE id=?', (row['id'],))
                failure = account_error('INVALID_VERIFICATION_CODE', '验证码不正确，请检查邮件后重试。')
            else:
                record = db.execute('SELECT id,email FROM auth_users WHERE email=?', (email,)).fetchone()
                db.execute("UPDATE auth_challenges SET status='CONSUMED' WHERE id=?", (row['id'],))
                if purpose == 'register' and record:
                    failure = account_error('ACCOUNT_ALREADY_EXISTS', '该邮箱已注册，请切换到登录。', 409)
                elif purpose == 'login' and not record:
                    failure = account_error('ACCOUNT_NOT_FOUND', '该邮箱尚未注册，请先注册。', 404)
                else:
                    user = dict(record) if record else {'id': str(uuid4()), 'email': email}
                    if not record:
                        db.execute('INSERT INTO auth_users VALUES (?,?,?)', (user['id'], email, now))
                    token = secrets.token_urlsafe(32)
                    if previous_token:
                        db.execute('DELETE FROM auth_sessions WHERE token_hash=?', (self.token_hash(previous_token),))
                    db.execute('INSERT INTO auth_sessions VALUES (?,?,?)', (self.token_hash(token), user['id'], now + self.session_ttl))
        # Commit failed-attempt counters and one-time consumption before returning errors.
        if failure:
            raise failure
        return user, token

    def logout(self, token):
        if token:
            with self.store.transaction() as db:
                db.execute('DELETE FROM auth_sessions WHERE token_hash=?', (self.token_hash(token),))
