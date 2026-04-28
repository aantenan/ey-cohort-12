def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "service" in body
    assert body["docs"] == "/docs"
    assert body["health"] == "/api/v1/health"


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ivr_webhook_with_api_key(client):
    r = client.post(
        "/api/v1/integrations/ivr/webhook",
        headers={"X-API-Key": "test-ivr-key"},
    )
    assert r.status_code == 200
    assert r.json()["received"] is True


def test_ivr_webhook_missing_key(client):
    r = client.post("/api/v1/integrations/ivr/webhook")
    assert r.status_code == 401
    err = r.json()["error"]
    assert err["code"] == "http_401"
