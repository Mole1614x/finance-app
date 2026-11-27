from concurrent.futures import ThreadPoolExecutor
from backend.tests.test_auth import client
from backend.tests.test_ledger import headers, login, init, balances, assert_reconciled
from backend.app.ledger import STARTING_MINOR

BASE = "/api/v1/payments"

def receive(client, h):
    r = client.get(BASE + "/receive", headers=h)
    assert r.status_code == 200, r.text
    return r.json()

def send(client, h, target, amount=50000, key="demo-send-1"):
    return client.post(BASE + "/send", headers={**h, "Idempotency-Key": key},
                       json={"payment_id": target, "amount_minor": amount})

def test_send_and_receive(client):
    a, b = headers(client), login(client)
    assert client.get(BASE + "/receive", headers=a).status_code == 409
    init(client, a)
    init(client, b)
    info = receive(client, b)
    target = info["payment_id"]
    matrix = info["qr_matrix"]
    assert target.startswith("arth-demo:")
    assert len(matrix) >= 29 and all(len(row) == len(matrix) for row in matrix)
    assert any(any(row) for row in matrix)
    assert client.post(BASE + "/resolve", headers=a, json={"payment_id": target}).status_code == 200
    first = send(client, a, target)
    assert first.status_code == 200, first.text
    assert first.json()["simulated"] is True
    assert send(client, a, target).json() == first.json()
    assert send(client, a, target, amount=100).status_code == 409
    assert balances(client, a)["checking"] == STARTING_MINOR-50000
    assert balances(client, b)["checking"] == STARTING_MINOR+50000
    path = BASE + "/" + first.json()["id"]
    assert client.get(path, headers=b).json() == first.json()
    outsider = login(client, "third@example.com")
    assert client.get(path, headers=outsider).status_code == 404
    assert client.get(path).status_code == 401
    assert_reconciled()

def test_payment_validation(client):
    a, b = headers(client), login(client)
    init(client, a)
    init(client, b)
    target = receive(client, b)["payment_id"]
    assert send(client, a, receive(client, a)["payment_id"]).status_code == 400
    assert send(client, a, target, amount=STARTING_MINOR+1).status_code == 409
    assert send(client, a, target, amount=1.5).status_code == 422
    assert send(client, a, "arth-demo:00000000-0000-0000-0000-000000000000").status_code == 404
    assert send(client, a, "upi://pay?pa=someone@example").status_code in (400, 422)
    assert send(client, {}, target).status_code == 401
    assert balances(client, a)["checking"] == STARTING_MINOR
    assert_reconciled()

def test_concurrent_peer_payments(client):
    a, b = headers(client), login(client)
    init(client, a)
    init(client, b)
    target = receive(client, b)["payment_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda k: send(client, a, target, amount=600000, key=k),
                                ["race-pay-1", "race-pay-2"]))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert balances(client, a)["checking"] == STARTING_MINOR-600000
    assert balances(client, b)["checking"] == STARTING_MINOR+600000
    assert_reconciled()

def test_concurrent_opposite_payments(client):
    a, b = headers(client), login(client)
    init(client, a)
    init(client, b)
    one, two = receive(client, a)["payment_id"], receive(client, b)["payment_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(send, client, a, two)
        f2 = pool.submit(send, client, b, one)
        assert f1.result().status_code == f2.result().status_code == 200
    assert balances(client, a)["checking"] == balances(client, b)["checking"] == STARTING_MINOR
    assert_reconciled()
