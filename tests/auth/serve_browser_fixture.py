"""Explicit browser QA fixture. Does not send real mail or use production accounts."""
import argparse
import json
from pathlib import Path

from waitress import serve

from backend import create_app
from backend.core.settings import Settings
from backend.services.auth import AuthService


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--port', type=int, default=5002)
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)

    class TestMailer:
        configured = True
        def send(self, email, code, purpose, ttl):
            (args.root / 'test-outbox.json').write_text(json.dumps({'email': email, 'code': code, 'purpose': purpose}), encoding='utf-8')

    settings = Settings(enable_accounts=True, auth_database_url='sqlite:///' + str(args.root / 'accounts.sqlite3'),
                        auth_secret_key='browser-test-only-secret-key', auth_trusted_origins=['http://127.0.0.1:5174'])
    service = AuthService(settings, mailer=TestMailer())
    app = create_app(settings, auth_service=service)
    print('Isolated browser QA account service ready. Real SMTP is disabled.', flush=True)
    serve(app, host='127.0.0.1', port=args.port, threads=8)


if __name__ == '__main__':
    main()
