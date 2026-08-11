"""Phase 7 AI Advisor tests."""


def test_advisor_generate_and_update(client, auth_headers) -> None:
    headers, brand_id = auth_headers

    # Seed enough context: account + published post + metrics
    account = client.post(
        "/api/social-accounts",
        headers=headers,
        json={
            "brand_id": brand_id,
            "platform": "linkedin",
            "account_name": "Advisor Sim",
            "connection_mode": "simulation",
        },
    ).json()
    content = client.post(
        "/api/content",
        headers=headers,
        json={
            "brand_id": brand_id,
            "title": "Irrigation tip that converts",
            "status": "approved",
            "versions": [{"platform": "linkedin", "body": "Practical irrigation advice"}],
        },
    ).json()
    client.post(
        "/api/publishing/publish-now",
        headers=headers,
        json={
            "content_item_id": content["id"],
            "content_version_id": content["versions"][0]["id"],
            "social_account_id": account["id"],
        },
    )
    client.post("/api/analytics/sync?days=7", headers=headers)

    generated = client.post(
        "/api/advisor/generate",
        headers=headers,
        json={"brand_id": brand_id, "use_llm": False},
    )
    assert generated.status_code == 200, generated.text
    recs = generated.json()
    assert len(recs) >= 1
    assert recs[0]["title"]
    assert recs[0]["status"] == "active"

    listed = client.get(f"/api/advisor/recommendations?brand_id={brand_id}", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    updated = client.patch(
        f"/api/advisor/recommendations/{recs[0]['id']}",
        headers=headers,
        json={"status": "accepted"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "accepted"

    overview = client.get("/api/analytics/overview", headers=headers)
    assert overview.status_code == 200
    assert isinstance(overview.json()["recommendations"], list)
