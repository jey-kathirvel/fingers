"""Phase 5 analytics tests."""


def _connect_and_publish(client, headers, brand_id: str) -> None:
    account = client.post(
        "/api/social-accounts",
        headers=headers,
        json={
            "brand_id": brand_id,
            "platform": "linkedin",
            "account_name": "Analytics Sim",
            "connection_mode": "simulation",
        },
    ).json()
    content = client.post(
        "/api/content",
        headers=headers,
        json={
            "brand_id": brand_id,
            "title": "Analytics tip",
            "status": "approved",
            "versions": [{"platform": "linkedin", "body": "Measure what matters"}],
        },
    ).json()
    version_id = content["versions"][0]["id"]
    published = client.post(
        "/api/publishing/publish-now",
        headers=headers,
        json={
            "content_item_id": content["id"],
            "content_version_id": version_id,
            "social_account_id": account["id"],
        },
    )
    assert published.status_code == 200, published.text


def test_analytics_sync_trends_and_posts(client, auth_headers) -> None:
    headers, brand_id = auth_headers
    _connect_and_publish(client, headers, brand_id)

    synced = client.post("/api/analytics/sync?days=14", headers=headers)
    assert synced.status_code == 200, synced.text
    body = synced.json()
    assert body["account_metrics"] >= 14
    assert body["post_metrics"] >= 1

    trends = client.get(f"/api/analytics/trends?brand_id={brand_id}&days=14", headers=headers)
    assert trends.status_code == 200
    assert len(trends.json()) >= 1
    assert "impressions" in trends.json()[-1]

    platforms = client.get(f"/api/analytics/platforms?brand_id={brand_id}", headers=headers)
    assert platforms.status_code == 200
    assert any(row["platform"] == "linkedin" for row in platforms.json())

    posts = client.get(f"/api/analytics/posts?brand_id={brand_id}", headers=headers)
    assert posts.status_code == 200
    assert len(posts.json()) >= 1
    assert posts.json()[0]["engagement_rate"] >= 0

    overview = client.get("/api/analytics/overview", headers=headers)
    assert overview.status_code == 200
    assert overview.json()["impressions"] > 0
    assert overview.json()["followers"] > 0
