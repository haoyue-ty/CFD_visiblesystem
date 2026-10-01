import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend import create_app  # noqa: E402
from fake_case8_adapter import FakeCase8Adapter  # noqa: E402


@pytest.fixture
def adapter():
    return FakeCase8Adapter()


@pytest.fixture
def app(adapter):
    application = create_app(case8_adapter=adapter, cylinder_adapter=None)
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()
