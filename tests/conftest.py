import os

os.environ.setdefault("ENABLE_REMINDER_SCHEDULER", "false")

import pytest
from app import create_app


@pytest.fixture
def app():
    class TestConfig:
        TESTING = True
        SECRET_KEY = "unit-test-secret-that-is-not-used-in-production"
        SESSION_COOKIE_SECURE = False
        FORCE_HTTPS = False
        TRUSTED_PROXY_HOPS = 0
        ENABLE_REMINDER_SCHEDULER = False
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()
