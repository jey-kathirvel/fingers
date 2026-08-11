"""Phase 3 publishing tests."""

from datetime import datetime, timedelta, timezone


def _create_approved_content(client, headers, brand_id: str) -> dict:
    created = client.post(
        "/api/content",
        headers=headers,
        json={
            "brand_id": brand_id,
            "title": "Irrigation tip",
            "topic": "Weekly irrigation",
            "status": "approved",
            "versions": [
                {"platform": "linkedin", "body": "LinkedIn body about irrigation"},
                {"platform": "instagram", "body": "IG reel script"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    return created.json()


def test_connect_schedule_and_publish_now(client, auth_headers) -> None:
    headers, brand_id = auth_headers
    content = _create_approved_content(client, headers, brand_id)
    linkedin_version = next(v for v in content["versions"] if v["platform"] == "linkedin")

    account = client.post(
        "/api/social-accounts",
        headers=headers,
        json={
            "brand_id": brand_id,
            "platform": "linkedin",
            "account_name": "Fingers LinkedIn Sim",
            "connection_mode": "simulation",
        },
    )
    assert account.status_code == 200, account.text
    account_id = account.json()["id"]

    when = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    scheduled = client.post(
        "/api/scheduled-posts",
        headers=headers,
        json={
            "content_item_id": content["id"],
            "content_version_id": linkedin_version["id"],
            "social_account_id": account_id,
            "scheduled_for": when,
        },
    )
    assert scheduled.status_code == 200, scheduled.text
    assert scheduled.json()["status"] == "scheduled"

    published = client.post(
        "/api/publishing/publish-now",
        headers=headers,
        json={
            "content_item_id": content["id"],
            "content_version_id": linkedin_version["id"],
            "social_account_id": account_id,
        },
    )
    assert published.status_code == 200, published.text
    body = published.json()
    assert body["status"] == "published"
    assert body["external_post_id"]
    assert body["external_post_id"].startswith("sim_linkedin_")

    calendar = client.get(f"/api/calendar?brand_id={brand_id}", headers=headers)
    assert calendar.status_code == 200
    assert any(item["id"] == body["id"] for item in calendar.json())

    logs = client.get("/api/publishing-logs", headers=headers)
    assert logs.status_code == 200
    assert any(log["action"] == "publish" and log["status"] == "published" for log in logs.json())


def test_cancel_and_retry(client, auth_headers) -> None:
    headers, brand_id = auth_headers
    content = _create_approved_content(client, headers, brand_id)
    ig_version = next(v for v in content["versions"] if v["platform"] == "instagram")

    account = client.post(
        "/api/social-accounts",
        headers=headers,
        json={
            "brand_id": brand_id,
            "platform": "instagram",
            "account_name": "Fingers IG Sim",
            "connection_mode": "simulation",
        },
    ).json()

    when = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    post = client.post(
        "/api/scheduled-posts",
        headers=headers,
        json={
            "content_item_id": content["id"],
            "content_version_id": ig_version["id"],
            "social_account_id": account["id"],
            "scheduled_for": when,
        },
    ).json()

    cancelled = client.delete(f"/api/scheduled-posts/{post['id']}", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["ok"] is True

    retried = client.post(f"/api/scheduled-posts/{post['id']}/retry", headers=headers)
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "published"


def test_integration_health_includes_phase3(client, auth_headers) -> None:
    headers, _brand_id = auth_headers
    res = client.get("/api/integration-health", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert int(body["phase"]) >= 3
    assert "platforms" in body
    assert "meta_configured" in body
    assert "linkedin_configured" in body
