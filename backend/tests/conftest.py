import os

# Force test-friendly config before `app` import (overrides user shell env).
os.environ["REDIS_URL"] = ""
os.environ["INTEGRATION_API_KEYS_JSON"] = '{"ivr":"test-ivr-key","chatbot":"test-chat-key"}'

from app.main import app
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
