"""Phase 4 engagement inbox tests."""


def _connect_account(client, headers, brand_id: str) -> str:
    res = client.post(
        "/api/social-accounts",
        headers=headers,
        json={
            "brand_id": brand_id,
            "platform": "linkedin",
            "account_name": "Engagement Sim",
            "connection_mode": "simulation",
        },
    )
    assert res.status_code == 200, res.text
    return res.json()["id"]


def test_sync_classify_reply_and_send(client, auth_headers) -> None:
    headers, brand_id = auth_headers
    _connect_account(client, headers, brand_id)

    synced = client.post("/api/inbox/sync", headers=headers)
    assert synced.status_code == 200, synced.text
    assert synced.json()["created"] >= 1

    inbox = client.get(f"/api/inbox?brand_id={brand_id}", headers=headers)
    assert inbox.status_code == 200
    items = inbox.json()
    assert len(items) >= 1
    item = items[0]
    assert item["sentiment"]
    assert item["intent"]
    assert item["priority"]

    draft = client.post(
        f"/api/interactions/{item['id']}/reply-draft",
        headers=headers,
        json={"tone": "helpful"},
    )
    assert draft.status_code == 200, draft.text
    assert draft.json()["body"]
    assert draft.json()["status"] == "suggested"

    sent = client.post(
        f"/api/interactions/{item['id']}/approve-send",
        headers=headers,
        json={"draft_id": draft.json()["id"], "body": draft.json()["body"]},
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "sent"
    assert sent.json()["external_reply_id"].startswith("sim_reply_")

    detail = client.get(f"/api/interactions/{item['id']}", headers=headers)
    assert detail.json()["status"] == "responded"

    stats = client.get(f"/api/inbox/stats?brand_id={brand_id}", headers=headers)
    assert stats.status_code == 200
    assert stats.json()["total"] >= 1


def test_ignore_interaction(client, auth_headers) -> None:
    headers, brand_id = auth_headers
    _connect_account(client, headers, brand_id)
    client.post("/api/inbox/sync", headers=headers)
    item = client.get(f"/api/inbox?brand_id={brand_id}", headers=headers).json()[0]
    updated = client.patch(
        f"/api/interactions/{item['id']}",
        headers=headers,
        json={"status": "ignored"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "ignored"
