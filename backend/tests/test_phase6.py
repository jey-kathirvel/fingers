"""Phase 6 campaigns and leads tests."""


def test_campaign_create_link_and_lead_pipeline(client, auth_headers) -> None:
    headers, brand_id = auth_headers

    campaign = client.post(
        "/api/campaigns",
        headers=headers,
        json={
            "brand_id": brand_id,
            "name": "Irrigation Push",
            "objective": "leads",
            "platforms": ["linkedin", "instagram"],
            "kpi_targets": "20 qualified leads",
        },
    )
    assert campaign.status_code == 200, campaign.text
    campaign_id = campaign.json()["id"]

    content = client.post(
        "/api/content",
        headers=headers,
        json={
            "brand_id": brand_id,
            "title": "Campaign post",
            "status": "approved",
            "versions": [{"platform": "linkedin", "body": "Join the irrigation demo"}],
        },
    ).json()

    linked = client.post(
        f"/api/campaigns/{campaign_id}/content",
        headers=headers,
        json={"content_item_id": content["id"]},
    )
    assert linked.status_code == 200
    assert content["id"] in linked.json()["content_item_ids"]

    activated = client.patch(
        f"/api/campaigns/{campaign_id}",
        headers=headers,
        json={"status": "active"},
    )
    assert activated.json()["status"] == "active"

    # Connect + sync inbox + convert
    client.post(
        "/api/social-accounts",
        headers=headers,
        json={
            "brand_id": brand_id,
            "platform": "linkedin",
            "account_name": "Leads Sim",
            "connection_mode": "simulation",
        },
    )
    synced = client.post("/api/inbox/sync", headers=headers)
    assert synced.status_code == 200
    item = client.get(f"/api/inbox?brand_id={brand_id}", headers=headers).json()[0]

    lead = client.post(
        f"/api/interactions/{item['id']}/convert-lead",
        headers=headers,
        json={"campaign_id": campaign_id, "product_interest": "Irrigation plan"},
    )
    assert lead.status_code == 200, lead.text
    assert lead.json()["status"] == "new"
    assert lead.json()["campaign_id"] == campaign_id
    assert lead.json()["score"] >= 10

    moved = client.patch(
        f"/api/leads/{lead.json()['id']}",
        headers=headers,
        json={"status": "contacted"},
    )
    assert moved.json()["status"] == "contacted"

    pipeline = client.get(f"/api/leads/pipeline?brand_id={brand_id}", headers=headers)
    assert pipeline.status_code == 200
    assert pipeline.json()["total"] >= 1
    assert pipeline.json()["open_count"] >= 1
