from backend.app.anomaly_model import evaluate, feature_rows, review, trained_model, vector
from backend.tests.test_auth import client
from backend.tests.test_ledger import headers, login, init, assert_reconciled
from backend.tests.test_services import purchase
from backend.tests.test_payments import receive, send
from backend.app.auth import engine
from backend.app.ledger import Journal
from backend.app.analytics import month_bounds
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

def test_reproducible_synthetic_evaluation():
    first = evaluate()
    trained_model.cache_clear()
    second = evaluate()
    assert first == second
    assert first["synthetic_only"]
    assert sum(first["confusion_matrix"].values()) == 1050
    # Modest smoke thresholds on injected scenarios, not production quality claims.
    assert first["roc_auc"] > .75
    assert first["recall"] > .4

def test_prior_history_only_and_ties():
    rows = [{"id":str(i), "created_at":i*60, "amount_minor":10000} for i in range(4)]
    rows.extend([{"id":"a","created_at":240,"amount_minor":100000},
                 {"id":"b","created_at":240,"amount_minor":200000},
                 {"id":"later","created_at":4000,"amount_minor":10000}])
    result = list(feature_rows(rows))
    assert [x[0]["id"] for x in result] == ["a", "b", "later"]
    assert result[0][2:] == (10,4)
    assert result[1][2:] == (20,4)
    assert result[2][3] == 0
    assert review(rows[:4])["status"] == "insufficient_history"
    assert review(rows)["evaluated_count"] == 3
    assert all(not r["fraud_confirmed"] for r in review(rows)["flags"])

def test_risk_endpoint_isolated_read_only(client):
    a, b = headers(client), login(client)
    path = "/api/v1/analytics/risk"
    assert client.get(path).status_code == 401
    init(client, a)
    init(client, b)
    assert client.get(path, headers=a).json()["status"] == "insufficient_history"
    # Recharges are outgoing expenses, while their rewards are excluded.
    for i in range(4):
        assert purchase(client, a, sku="mobile-199", key=f"risk-demo-{i}").status_code == 200
    assert send(client, a, receive(client,b)["payment_id"], amount=400000).status_code == 200
    # Give the expense entries distinct timestamps without depending on test speed.
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    start, _, _ = month_bounds(month)
    with Session(engine()) as db:
        rows = db.scalars(select(Journal).where(Journal.idempotency_key.startswith("svc:"))
                          .order_by(Journal.id)).all()
        for i, row in enumerate(rows):
            row.created_at = start+i*120+10
        for row in db.scalars(select(Journal).where(Journal.idempotency_key.startswith("pay:"))):
            row.created_at = start+600
        db.commit()
    one = client.get(path, headers=a).json()
    assert one["status"] == "evaluated"
    assert one["evaluated_count"] == 1
    assert one["training_data"] == "synthetic"
    assert client.get(path, headers=b).json()["evaluated_count"] == 0
    assert client.get(path, headers=a, params={"month":"2026-13"}).status_code == 400
    assert client.get(path, headers=a).json() == one
    answer = client.post("/api/v1/analytics/assistant", headers=a, json={"topic":"risk"}).json()
    assert answer["answer"]["ml_review"] == {k: one[k] for k in answer["answer"]["ml_review"]}
    assert_reconciled()
