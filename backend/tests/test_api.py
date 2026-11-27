from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health():
    assert client.get("/health").json() == {"status": "ok", "mode": "demo"}

def test_dashboard_is_demo_only():
    response = client.get("/api/v1/demo/dashboard")
    assert response.status_code == 200
    assert response.json() == {"mode": "demo", "currency": "INR",
                              "balance_minor": 850000, "payments_enabled": False}
