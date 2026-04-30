import json
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.auth.deps import get_current_user
from app.auth.models import CurrentUser
from app.kb.search_service import _json_default
from app.main import app


def test_kb_search_cache_json_serializes_uuid_and_decimal() -> None:
    """Regression: Redis cache must JSON-encode ORM types (WO-27)."""
    payload = {
        "items": [
            {
                "article_id": uuid4(),
                "title": "t",
                "snippet": "s",
                "category": None,
                "published_at": None,
                "rank": Decimal("0.123"),
            }
        ]
    }
    json.dumps(payload, default=_json_default)


@pytest.fixture
def client_kb_auth() -> TestClient:
    def fake_user() -> CurrentUser:
        return CurrentUser(sub="test-sub", oid="test-oid", email="t@example.com", roles=[])

    app.dependency_overrides[get_current_user] = fake_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_kb_search_requires_query_param(client_kb_auth: TestClient) -> None:
    r = client_kb_auth.get("/api/v1/kb/search")
    assert r.status_code == 422


def test_kb_search_response_shape(client_kb_auth: TestClient) -> None:
    r = client_kb_auth.get("/api/v1/kb/search?q=support&limit=10&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body and "total" in body and "limit" in body and "offset" in body
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert isinstance(body["data"], list)


def test_kb_search_limit_bounds(client_kb_auth: TestClient) -> None:
    r = client_kb_auth.get("/api/v1/kb/search?q=test&limit=99")
    assert r.status_code == 422
