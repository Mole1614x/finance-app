from backend.tests.test_auth import client
from backend.tests.test_ledger import headers, login, init, move, assert_reconciled
from backend.tests.test_payments import receive, send

BASE = "/api/v1/transactions"

def history(client, h, **params):
    response = client.get(BASE, headers=h, params=params)
    assert response.status_code == 200, response.text
    return response.json()

def test_history_receipts_and_scope(client):
    a, b = headers(client), login(client)
    assert client.get(BASE).status_code == 401
    assert history(client, a)["items"] == []
    init(client, a)
    init(client, b)
    move_result = move(client, a)
    assert move_result.status_code == 200
    payment = send(client, a, receive(client, b)["payment_id"])
    assert payment.status_code == 200
    assert send(client, a, receive(client, b)["payment_id"]).json() == payment.json()
    sent = history(client, a, kind="sent")["items"]
    received = history(client, b, kind="received")["items"]
    assert len(sent) == len(received) == 1
    assert sent[0]["id"] == received[0]["id"]
    assert sent[0]["payment_reference"] == payment.json()["id"]
    assert sent[0]["balance_change_minor"] == -50000
    assert received[0]["balance_change_minor"] == 50000
    assert sent[0]["destination"] == "another demo account"
    assert received[0]["source"] == "another demo account"
    assert history(client, a, kind="internal")["items"][0]["balance_change_minor"] == 0
    assert history(client, a, kind="opening")["items"][0]["balance_change_minor"] == 850000
    assert len(history(client, a)["items"]) == 3
    assert len(history(client, b)["items"]) == 2
    path = BASE + "/" + sent[0]["id"]
    assert client.get(path, headers=a).json() == sent[0]
    assert client.get(path, headers=b).json() == received[0]
    outsider = login(client, "outsider@example.com")
    assert client.get(path, headers=outsider).status_code == 404
    assert history(client, outsider)["items"] == []
    assert client.get("/api/v1/dashboard", headers=a).json()["recent_transactions"] == history(client, a)["items"]
    assert_reconciled()

def test_filters_pagination_and_validation(client):
    a = headers(client)
    init(client, a)
    assert move(client, a).status_code == 200
    all_rows = history(client, a)["items"]
    one = history(client, a, limit=1)
    two = history(client, a, limit=1, offset=one["next_offset"])
    assert one["items"] + two["items"] == all_rows
    assert two["next_offset"] is None
    assert history(client, a, since=all_rows[0]["created_at"]+1)["items"] == []
    assert client.get(BASE, headers=a, params={"since": 20, "until": 10}).status_code == 400
    assert client.get(BASE, headers=a, params={"kind": "invalid"}).status_code == 422
    assert client.get(BASE, headers=a, params={"limit": 101}).status_code == 422

def test_payment_lookup_is_read_only_and_sender_scoped(client):
    a, b = headers(client), login(client)
    init(client, a)
    init(client, b)
    target = receive(client, b)["payment_id"]
    key = {"idempotency_key": "demo-send-1"}
    path = BASE + "/payment-lookup"
    assert client.post(path, headers=a, json=key).json()["status"] == "unknown"
    assert send(client, a, target).status_code == 200
    known = client.post(path, headers=a, json=key).json()
    assert known["status"] == "completed"
    assert known["transaction"]["kind"] == "sent"
    assert client.post(path, headers=b, json=key).json()["status"] == "unknown"
    assert client.post(path, json=key).status_code == 401
    assert len(history(client, a, kind="sent")["items"]) == 1
    assert_reconciled()
