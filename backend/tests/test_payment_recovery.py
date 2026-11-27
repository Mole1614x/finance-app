from concurrent.futures import ThreadPoolExecutor
from backend.tests.test_auth import client
from backend.tests.test_ledger import headers, login, init, balances, assert_reconciled
from backend.tests.test_payments import receive, send
from backend.app.ledger import STARTING_MINOR

BASE = "/api/v1/payments"

def action(client, h, key, route="recover"):
    return client.post(BASE+"/"+route, headers=h, json={"idempotency_key":key})

def test_cancel_tombstone_and_scope(client):
    a,b = headers(client),login(client)
    init(client,a)
    init(client,b)
    target = receive(client,b)["payment_id"]
    key = "cancelled-key"
    assert action(client,a,key).json()["status"] == "unknown"
    assert action(client,a,key,"cancel").json()["status"] == "cancelled"
    assert action(client,a,key,"cancel").json()["status"] == "cancelled"
    assert action(client,b,key).json()["status"] == "unknown"
    assert send(client,a,target,key=key).status_code == 409
    assert balances(client,a)["checking"] == STARTING_MINOR
    assert action(client,{},key,"cancel").status_code == 401
    assert_reconciled()

def test_cancel_after_send_returns_receipt(client):
    a,b = headers(client),login(client)
    init(client,a)
    init(client,b)
    target = receive(client,b)["payment_id"]
    key = "completed-key"
    first = send(client,a,target,key=key).json()
    assert action(client,a,key).json()["receipt"] == first
    result = action(client,a,key,"cancel").json()
    assert result["status"] == "completed" and result["receipt"] == first
    assert send(client,a,target,key=key).json() == first
    assert balances(client,a)["checking"] == STARTING_MINOR-50000
    assert_reconciled()

def test_send_cancel_race(client):
    a,b = headers(client),login(client)
    init(client,a)
    init(client,b)
    target = receive(client,b)["payment_id"]
    key = "race-cancel-key"
    with ThreadPoolExecutor(max_workers=2) as pool:
        s = pool.submit(send,client,a,target,50000,key)
        c = pool.submit(action,client,a,key,"cancel")
        response, outcome = s.result(), c.result().json()
    if outcome["status"] == "cancelled":
        assert response.status_code == 409
        assert balances(client,a)["checking"] == STARTING_MINOR
    else:
        assert outcome["status"] == "completed" and response.status_code == 200
        assert balances(client,a)["checking"] == STARTING_MINOR-50000
    assert action(client,a,key).json() == outcome
    assert_reconciled()
