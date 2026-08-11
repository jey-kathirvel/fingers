"""API smoke tests for Phase 1 foundation."""


def test_health(client) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["app"] == "Fingers"
    assert "ai_provider" in body


def test_login_and_brands(client, auth_headers) -> None:
    headers, _brand_id = auth_headers
    orgs = client.get("/api/organizations", headers=headers)
    assert orgs.status_code == 200
    org_id = orgs.json()[0]["id"]

    brands = client.get("/api/brands", headers={**headers, "X-Organization-Id": org_id})
    assert brands.status_code == 200
    assert any(b["slug"] == "fingers" for b in brands.json())

    overview = client.get("/api/analytics/overview", headers={**headers, "X-Organization-Id": org_id})
    assert overview.status_code == 200
    assert overview.json()["brands_count"] >= 1
