"""Phase 2 AI Content Studio tests."""


def test_generate_and_list_content(client, auth_headers) -> None:
    headers, brand_id = auth_headers
    res = client.post(
        "/api/ai/generate",
        headers=headers,
        json={
            "brand_id": brand_id,
            "topic": "Promote irrigation management this week",
            "objective": "awareness",
            "platforms": ["linkedin", "instagram", "facebook"],
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "draft"
    assert len(body["versions"]) == 3

    listed = client.get("/api/content", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == body["id"] for item in listed.json())


def test_ideas_and_assets(client, auth_headers) -> None:
    headers, brand_id = auth_headers
    ideas = client.post("/api/ai/ideas", headers=headers, json={"brand_id": brand_id, "count": 3})
    assert ideas.status_code == 200
    assert len(ideas.json()) == 3

    asset = client.post(
        "/api/assets",
        headers=headers,
        json={
            "brand_id": brand_id,
            "name": "Irrigation reel cover",
            "asset_type": "image_prompt",
            "url_or_path": "prompt://irrigation-reel-cover",
            "prompt": "Farmer reviewing irrigation dashboard at sunrise",
            "tags": "irrigation,reel",
        },
    )
    assert asset.status_code == 200
    assets = client.get("/api/assets", headers=headers)
    assert any(a["name"] == "Irrigation reel cover" for a in assets.json())


def test_status_workflow(client, auth_headers) -> None:
    headers, brand_id = auth_headers
    created = client.post(
        "/api/content",
        headers=headers,
        json={
            "brand_id": brand_id,
            "title": "Manual draft",
            "topic": "Weekly tips",
            "versions": [{"platform": "linkedin", "body": "Hello LinkedIn"}],
        },
    ).json()
    updated = client.patch(
        f"/api/content/{created['id']}",
        headers=headers,
        json={"status": "review"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "review"
