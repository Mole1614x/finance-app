from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.auth import engine
from backend.app.ledger import Account, Journal, STARTING_MINOR
from backend.tests.test_auth import client, session

BASE = "/api/v1/accounts"

def login(client, email="other@example.com"):
    auth = "/api/v1/auth"
    ticket = client.post(auth + "/register", json={"email": email, "password": "demo-password"}).json()
    data = {"challenge_id": ticket["challenge_id"]}
    code = client.post(auth + "/otp/request", json=data).json()["demo_code"]
    tokens = client.post(auth + "/otp/verify", json={**data, "code": code}).json()
    return {"Authorization": "Bearer " + tokens["access_token"]}

def headers(client):
    return {"Authorization": "Bearer " + session(client)["access_token"]}

def init(client, h):
    r = client.post(BASE + "/initialize", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["accounts"]

def balances(client, h):
    return {a["kind"]: a["balance_minor"] for a in client.get(BASE, headers=h).json()["accounts"]}

def move(client, h, key="test-key-1", amount=50000, source="checking", destination="savings"):
    return client.post(BASE + "/move", headers={**h, "Idempotency-Key": key},
                       json={"source": source, "destination": destination, "amount_minor": amount})

def assert_reconciled():
    with Session(engine()) as db:
        accounts = db.scalars(select(Account)).all()
        journal = db.scalars(select(Journal)).all()
        calculated = {a.id: 0 for a in accounts}
        for entry in journal:
            calculated[entry.debit_account_id] -= entry.amount_minor
            calculated[entry.credit_account_id] += entry.amount_minor
        assert calculated == {a.id: a.balance_minor for a in accounts}
        assert sum(calculated.values()) == 0

def test_initialization_and_dashboard(client):
    h = headers(client)
    assert client.get(BASE).status_code == 401
    assert client.get(BASE, headers=h).json()["accounts"] == []
    assert init(client, h) == init(client, h)
    assert balances(client, h) == {"checking": STARTING_MINOR, "savings": 0}
    dashboard = client.get("/api/v1/dashboard", headers=h).json()
    assert dashboard["balance_minor"] == STARTING_MINOR
    assert dashboard["sample_balance"] is False
    assert dashboard["payments_enabled"] is False
    with Session(engine()) as db:
        assert len(db.scalars(select(Journal)).all()) == 1
    assert_reconciled()

def test_move_retry_conflict_and_insufficient_funds(client):
    h = headers(client)
    assert move(client, h).status_code == 409
    init(client, h)
    first = move(client, h)
    assert first.status_code == 200, first.text
    assert move(client, h).json() == first.json()
    assert move(client, h, amount=10).status_code == 409
    assert move(client, h, key="too-much", amount=STARTING_MINOR).status_code == 409
    assert move(client, h, key="same-acct", destination="checking").status_code == 400
    assert move(client, h, key="negative", amount=-1).status_code == 422
    assert move(client, h, key="fraction", amount=1.5).status_code == 422
    assert balances(client, h) == {"checking": STARTING_MINOR-50000, "savings": 50000}
    assert_reconciled()

def test_owner_isolation(client):
    h1 = headers(client)
    h2 = login(client)
    a1 = init(client, h1)
    a2 = init(client, h2)
    assert {a["id"] for a in a1}.isdisjoint(a["id"] for a in a2)
    assert move(client, h1).status_code == 200
    assert balances(client, h2) == {"checking": STARTING_MINOR, "savings": 0}
    assert move(client, h2).status_code == 200
    assert_reconciled()

def test_concurrent_moves_cannot_overspend(client):
    h = headers(client)
    init(client, h)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda key: move(client, h, key=key, amount=600000), ["race-key-1", "race-key-2"]))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert balances(client, h) == {"checking": STARTING_MINOR-600000, "savings": 600000}
    assert_reconciled()

def test_concurrent_initialization_and_replay(client):
    h = headers(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: init(client, h), range(2)))
    assert results[0] == results[1]
    with ThreadPoolExecutor(max_workers=2) as pool:
        moves = list(pool.map(lambda _: move(client, h), range(2)))
    assert all(r.status_code == 200 for r in moves)
    assert moves[0].json() == moves[1].json()
    assert balances(client, h) == {"checking": STARTING_MINOR-50000, "savings": 50000}
    assert_reconciled()
