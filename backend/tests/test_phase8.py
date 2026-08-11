"""Phase 8 automation & listening tests."""

import json


def test_automations_and_listening(client, auth_headers) -> None:
    headers, brand_id = auth_headers

    # Seed inbox context for keyword rule
    account = client.post(
        "/api/social-accounts",
        headers=headers,
        json={
            "brand_id": brand_id,
            "platform": "linkedin",
            "account_name": "Auto Sim",
            "connection_mode": "simulation",
        },
    ).json()
    assert account["id"]

    synced = client.post("/api/inbox/sync", headers=headers)
    assert synced.status_code == 200

    rules = client.post(
        f"/api/automations/seed-defaults?brand_id={brand_id}",
        headers=headers,
    )
    assert rules.status_code == 200, rules.text
    assert len(rules.json()) >= 3

    listed = client.get(f"/api/automations?brand_id={brand_id}", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) >= 3

    # Custom keyword rule that should fire on simulation price thread
    created = client.post(
        "/api/automations",
        headers=headers,
        json={
            "brand_id": brand_id,
            "name": "Test price lead",
            "trigger_type": "inbox_keyword",
            "trigger_config_json": json.dumps({"keywords": ["price", "pricing", "cost"]}),
            "action_type": "create_lead",
            "action_config_json": json.dumps({"also_draft_reply": True, "intent": "sales_enquiry"}),
        },
    )
    assert created.status_code == 200, created.text

    run = client.post(f"/api/automations/run?brand_id={brand_id}", headers=headers)
    assert run.status_code == 200, run.text
    summary = run.json()
    assert summary["rules_evaluated"] >= 1
    assert summary["runs"] >= 1

    runs = client.get("/api/automations/runs", headers=headers)
    assert runs.status_code == 200
    assert len(runs.json()) >= 1
    assert runs.json()[0]["status"] in {"success", "failed", "skipped"}

    # Listening
    terms = client.post(
        f"/api/listening/terms/seed-defaults?brand_id={brand_id}",
        headers=headers,
    )
    assert terms.status_code == 200, terms.text
    assert len(terms.json()) >= 1

    mention_sync = client.post(f"/api/listening/sync?brand_id={brand_id}", headers=headers)
    assert mention_sync.status_code == 200
    assert mention_sync.json()["created"] >= 1

    mentions = client.get(f"/api/listening/mentions?brand_id={brand_id}", headers=headers)
    assert mentions.status_code == 200
    assert len(mentions.json()) >= 1

    summary_res = client.get(f"/api/listening/summary?brand_id={brand_id}", headers=headers)
    assert summary_res.status_code == 200
    body = summary_res.json()
    assert body["mention_count"] >= 1
    assert "by_sentiment" in body
    assert isinstance(body["share_of_voice"], list)

    health = client.get("/api/integration-health", headers=headers)
    assert health.status_code == 200
    assert health.json()["phase"] == "8"
