"""Integrated demo journey, including durable recovery and ledger reconciliation."""
from datetime import datetime, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
from backend.app.main import app
from backend.app.auth import engine
from backend.app.ledger import Journal, STARTING_MINOR
from backend.app.analytics import month_bounds
from backend.app.services import ServiceOrder
from backend.tests.test_auth import client
from backend.tests.test_ledger import headers, login, init, move, balances, assert_reconciled
from backend.tests.test_payments import receive, send
from backend.tests.test_services import catalog, purchase
from backend.tests.test_payment_recovery import action
from mobile.pending_payment import PendingStore

def ok(response):
    assert response.status_code == 200, response.text
    return response.json()

def test_complete_demo_journey(client, tmp_path, monkeypatch):
    monkeypatch.setenv("ARTH_AI_ENABLED", "0")
    a, b = headers(client), login(client)
    init(client, a)
    init(client, b)
    target = receive(client, b)["payment_id"]
    owner = ok(client.get("/api/v1/auth/me", headers=a))["id"]
    key = str(uuid4())
    PendingStore(tmp_path).reserve("local-demo", owner, key, target, 50000)
    receipt = ok(send(client, a, target, key=key))
    # Simulate loss of the response and restart of local recovery storage.
    pending = PendingStore(tmp_path)
    record = pending.get("local-demo", owner)
    assert record["request_key"] == key
    assert action(client, a, key).json()["receipt"] == receipt
    assert ok(send(client, a, target, key=key)) == receipt
    pending.clear("local-demo", owner, key)
    assert pending.get("local-demo", owner) is None
    cancelled = str(uuid4())
    assert action(client, a, cancelled, "cancel").json()["status"] == "cancelled"
    assert send(client, a, target, key=cancelled).status_code == 409
    month = catalog(client, a)["electricity"]["bill_cycle"]
    order = ok(purchase(client, a, cycle=month))
    assert order["cashback_minor"] == 2000
    assert ok(purchase(client, a, cycle=month)) == order
    for i in range(3):
        assert purchase(client, a, sku="mobile-199", key=f"accept-recharge-{i}").status_code == 200
    base = "/api/v1/analytics"
    ok(client.put(base+"/goal", headers=a, json={"title":"Demo goal","target_minor":50000}))
    ok(move(client, a, amount=50000))
    ok(client.put(base+"/budget", headers=a, json={"month":month,"limit_minor":300000}))
    # Order outgoing entries strictly in the chosen month for the ML baseline.
    start, _, _ = month_bounds(month)
    with Session(engine()) as db:
        rows = db.scalars(select(Journal).where(Journal.owner_id==owner).order_by(Journal.created_at,Journal.id)).all()
        for i,row in enumerate(rows):
            row.created_at = start + 60*(i+1)
        for row in db.scalars(select(ServiceOrder).where(ServiceOrder.owner_id==owner)):
            row.created_at = start+60
        db.commit()
    info = ok(client.get(base+"/summary", headers=a, params={"month":month}))
    spent = 50000+125000+3*19900
    cashback = 2000+3*398
    assert info["spent_minor"] == spent
    assert info["cashback_minor"] == cashback
    assert info["budget_remaining_minor"] == 300000-spent
    assert balances(client,a) == {"checking":STARTING_MINOR-spent+cashback-50000,"savings":50000}
    assert balances(client,b)["checking"] == STARTING_MINOR+50000
    assert ok(client.get(base+"/goal",headers=a))["achieved"]
    risk = ok(client.get(base+"/risk",headers=a,params={"month":month}))
    assert risk["evaluated_count"] == 1
    assert all(not f["fraud_confirmed"] for f in risk["flags"])
    answer = ok(client.post(base+"/assistant",headers=a,json={"topic":"risk"}))
    assert answer["engine"] == "deterministic rules"
    assert answer["answer"]["ml_review"]["evaluated_count"] == 1
    rows = ok(client.get("/api/v1/transactions",headers=a,params={"kind":"sent"}))["items"]
    assert len(rows)==1 and rows[0]["payment_reference"]==receipt["id"]
    assert ok(client.get("/api/v1/payments/"+receipt["id"],headers=b)) == receipt
    assert ok(client.get("/api/v1/services/rewards",headers=a))["earned_minor"] == cashback
    assert ok(client.get("/api/v1/services/rewards",headers=b))["earned_minor"] == 0
    assert_reconciled()
    ok(client.post("/api/v1/auth/logout",headers=a))
    assert client.get(base+"/summary",headers=a).status_code==401

def test_upgrade_preserves_data_and_restart(tmp_path, monkeypatch):
    # Isolated SQLite database; never operate on the user's existing database.
    engine.cache_clear()
    monkeypatch.setenv("DATABASE_URL","sqlite:///"+str(tmp_path/"upgrade.db"))
    monkeypatch.setenv("ARTH_MANAGED_SCHEMA","1")
    from backend.app import security
    monkeypatch.setattr(security,"limiter",security.RateLimiter())
    config = Config("alembic.ini")
    try:
        command.upgrade(config,"0001_demo_baseline")
        with TestClient(app) as c:
            a,b = headers(c),login(c)
            init(c,a)
            init(c,b)
            target = receive(c,b)["payment_id"]
            assert balances(c,a)["checking"] == STARTING_MINOR
        engine().dispose()
        engine.cache_clear()
        command.upgrade(config,"head")
        command.check(config)
        with TestClient(app) as c:
            assert balances(c,a)["checking"] == STARTING_MINOR
            receipt = ok(send(c,a,target,key="upgrade-payment"))
            assert action(c,a,"upgrade-cancel","cancel").json()["status"]=="cancelled"
        engine().dispose()
        engine.cache_clear()
        with TestClient(app) as c:
            assert action(c,a,"upgrade-payment").json()["receipt"] == receipt
            assert send(c,a,target,key="upgrade-cancel").status_code == 409
            assert balances(c,a)["checking"] == STARTING_MINOR-50000
            assert_reconciled()
    finally:
        engine().dispose()
        engine.cache_clear()
