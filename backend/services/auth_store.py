"""Isolated account storage. MySQL in deployment; SQLite for offline tests."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import threading
from urllib.parse import unquote, urlsplit

import pymysql

from backend.core.errors import system_error


class AuthConnection:
    def __init__(self, connection, mysql):
        self.connection, self.mysql = connection, mysql

    def execute(self, sql, values=()):
        cursor = self.connection.cursor()
        cursor.execute(sql.replace('?', '%s') if self.mysql else sql, values)
        return cursor


class AuthStore:
    def __init__(self, database_url):
        self.url = database_url
        self.mysql = urlsplit(database_url).scheme == 'mysql+pymysql'
        self.ready = False
        self.lock = threading.Lock()

    def connect(self):
        if self.mysql:
            url = urlsplit(self.url)
            return pymysql.connect(host=url.hostname, port=url.port or 3306,
                                   user=unquote(url.username or ''), password=unquote(url.password or ''),
                                   database=url.path.lstrip('/'), charset='utf8mb4',
                                   cursorclass=pymysql.cursors.DictCursor, autocommit=False,
                                   connect_timeout=5, read_timeout=10, write_timeout=10)
        if not self.url.startswith('sqlite:///'):
            raise ValueError('Account database URL must use mysql+pymysql or sqlite')
        path = Path(self.url.removeprefix('sqlite:///'))
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self.lock:
            if self.ready:
                return
            connection = self.connect()
            try:
                db = AuthConnection(connection, self.mysql)
                suffix = ' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin' if self.mysql else ''
                for statement in (
                    'CREATE TABLE IF NOT EXISTS auth_mutex (id INTEGER PRIMARY KEY)',
                    'CREATE TABLE IF NOT EXISTS auth_users (id VARCHAR(36) PRIMARY KEY, email VARCHAR(254) NOT NULL UNIQUE, created_at DOUBLE NOT NULL)',
                    'CREATE TABLE IF NOT EXISTS auth_challenges (id VARCHAR(36) PRIMARY KEY, email VARCHAR(254) NOT NULL, purpose VARCHAR(16) NOT NULL, code_hash VARCHAR(64) NOT NULL, ip_hash VARCHAR(64) NOT NULL, created_at DOUBLE NOT NULL, expires_at DOUBLE NOT NULL, attempts INTEGER NOT NULL, status VARCHAR(16) NOT NULL)',
                    'CREATE TABLE IF NOT EXISTS auth_sessions (token_hash VARCHAR(64) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, expires_at DOUBLE NOT NULL)',
                    'CREATE TABLE IF NOT EXISTS auth_attempts (id VARCHAR(36) PRIMARY KEY, ip_hash VARCHAR(64) NOT NULL, created_at DOUBLE NOT NULL)',
                ):
                    db.execute(statement + suffix)
                db.execute(('INSERT IGNORE' if self.mysql else 'INSERT OR IGNORE') + ' INTO auth_mutex (id) VALUES (1)')
                connection.commit()
                self.ready = True
            finally:
                connection.close()

    @contextmanager
    def transaction(self):
        connection = None
        try:
            self.initialize()
            connection = self.connect()
            db = AuthConnection(connection, self.mysql)
            if self.mysql:
                connection.begin()
                db.execute('SELECT id FROM auth_mutex WHERE id=1 FOR UPDATE').fetchone()
            else:
                db.execute('BEGIN IMMEDIATE')
            yield db
            connection.commit()
        except (pymysql.MySQLError, sqlite3.Error, OSError, ValueError):
            if connection:
                connection.rollback()
            raise system_error('ACCOUNT_STORE_UNAVAILABLE', '账号数据库暂时不可用，请稍后重试。', status=503, domain='ACCOUNT', retryable=True) from None
        except Exception:
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                connection.close()
