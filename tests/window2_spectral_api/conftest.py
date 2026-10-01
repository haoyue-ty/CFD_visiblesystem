import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend import create_app  # noqa: E402
from fake_spectral_adapter import FakeSpectralAdapter  # noqa: E402


@pytest.fixture
def adapter():
    return FakeSpectralAdapter()


@pytest.fixture
def app(adapter):
    application = create_app(spectral_adapter=adapter)
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()
