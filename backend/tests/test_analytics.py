from datetime import datetime, timezone
from backend.tests.test_auth import client
from backend.tests.test_ledger import headers, login, init, move, assert_reconciled
from backend.tests.test_services import purchase, catalog
from backend.tests.test_payments import receive, send
from backend.app.analytics import anomaly_flags, month_bounds, summary_for
from backend.app.auth import engine
from sqlalchemy.orm import Session
from backend.app.auth import User
from sqlalchemy import select

BASE = "/api/v1/analytics"

def test_spending_and_budget(client):
    a, b = headers(client), login(client)
    assert client.get(BASE+"/summary").status_code == 401
    init(client, a)
    init(client, b)
    month = catalog(client, a)["electricity"]["bill_cycle"]
    assert purchase(client, a, cycle=month).status_code == 200
    assert send(client, a, receive(client, b)["payment_id"]).status_code == 200
    assert move(client, a).status_code == 200
    assert client.put(BASE+"/budget", headers=a, json={"month": month, "limit_minor": 200000}).status_code == 200
    summary = client.get(BASE+"/summary", headers=a).json()
    assert summary["spent_minor"] == 175000
    assert summary["cashback_minor"] == 2000
    assert summary["opening_funds_minor"] == 850000
    assert summary["received_minor"] == 0
    assert summary["budget_remaining_minor"] == 25000
    assert sum(summary["daily_net_minor"]) == summary["net_change_minor"] == 677000
    assert {x["category"]: x["amount_minor"] for x in summary["categories"]} == {"Electricity": 125000, "Peer payments": 50000}
    other = client.get(BASE+"/summary", headers=b).json()
    assert other["received_minor"] == 50000 and other["spent_minor"] == 0
    assert other["budget_limit_minor"] is None
    dashboard = client.get("/api/v1/dashboard", headers=a).json()
    assert dashboard["cashflow_minor"] == summary["daily_net_minor"]
    assert client.get(BASE+"/summary", headers=a, params={"month":"2026-13"}).status_code == 400
    assert client.put(BASE+"/budget", headers=a, json={"month":month,"limit_minor":0}).status_code == 422
    assert_reconciled()

def test_goal_and_assistant(client):
    a, b = headers(client), login(client)
    init(client, a)
    init(client, b)
    assert client.put(BASE+"/goal", headers=a, json={"title":"Demo trip","target_minor":100000}).status_code == 200
    assert move(client, a, amount=50000).status_code == 200
    goal = client.get(BASE+"/goal", headers=a).json()
    assert goal["saved_minor"] == 50000 and goal["remaining_minor"] == 50000
    assert goal["achieved"] is False
    assert move(client, a, key="goal-next", amount=50000).status_code == 200
    assert client.get(BASE+"/goal", headers=a).json()["achieved"] is True
    assert client.get(BASE+"/goal", headers=b).json()["title"] is None
    answer = client.post(BASE+"/assistant", headers=a, json={"topic":"savings"}).json()
    assert answer["engine"] == "deterministic rules" and answer["answer"]["achieved"]
    assert client.post(BASE+"/assistant", headers=a, json={"topic":"unsupported"}).status_code == 422
    assert_reconciled()

def test_anomaly_and_month_bounds():
    rows = [{"id":str(i),"amount_minor":a} for i,a in enumerate([10000,12000,9000,11000,150000])]
    flags = anomaly_flags(rows)
    assert len(flags) == 1 and flags[0]["transaction_id"] == "4"
    assert flags[0]["fraud_confirmed"] is False
    assert anomaly_flags(rows[:4]) == []
    start, end, days = month_bounds("2024-02")
    assert days == 29 and end-start == 29*86400

def test_forecast_uses_completed_days(client):
    a = headers(client)
    init(client, a)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    assert purchase(client, a, sku="mobile-199").status_code == 200
    # Freeze the reporting time after seven days and relocate demo journal rows to day 1.
    from backend.app.ledger import Journal
    from backend.app.services import ServiceOrder
    from sqlalchemy import update
    start, _, days = month_bounds(month)
    year, number = map(int, month.split("-"))
    with Session(engine()) as db:
        db.execute(update(Journal).values(created_at=start+60))
        db.execute(update(ServiceOrder).values(created_at=start+60))
        db.commit()
        owner = db.scalar(select(User.id))
        early = summary_for(db, owner, month, current=datetime(year,number,3,tzinfo=timezone.utc))
        later = summary_for(db, owner, month, current=datetime(year,number,8,tzinfo=timezone.utc))
        assert early["forecast_spending_minor"] is None
        assert later["forecast_spending_minor"] == 19900*days//7
