import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth import engine, User
from sqlalchemy import select
from sqlalchemy.orm import Session

@pytest.fixture
def client(tmp_path, monkeypatch):
    engine.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "test.db"))
    with TestClient(app) as c:
        yield c
    engine().dispose()
    engine.cache_clear()

PREFIX = "/api/v1/auth"
CREDS = {"email": "demo@example.com", "password": "demo-password"}

def post(client, path, data):
    return client.post(PREFIX + path, json=data)

def challenge(client, path="/register"):
    response = post(client, path, CREDS)
    assert response.status_code in (200, 201), response.text
    return {"challenge_id": response.json()["challenge_id"]}

def session(client):
    ticket = challenge(client)
    otp = post(client, "/otp/request", ticket).json()
    assert otp["sms_sent"] is False
    code = {**ticket, "code": otp["demo_code"]}
    response = post(client, "/otp/verify", code)
    assert response.status_code == 200, response.text
    assert post(client, "/otp/verify", code).status_code == 401
    return response.json()

def test_register_login_and_password_hash(client):
    challenge(client)
    with Session(engine()) as db:
        user = db.scalar(select(User))
        assert user.password_hash.startswith("$argon2id$")
        assert user.password_hash != CREDS["password"]
    assert post(client, "/register", CREDS).status_code == 409
    assert post(client, "/login", {**CREDS, "password": "wrong-password"}).status_code == 401
    challenge(client, "/login")
    assert post(client, "/register", {**CREDS, "email": "person@real.com"}).status_code == 400

def test_session_profile_refresh_logout(client):
    tokens = session(client)
    headers = {"Authorization": "Bearer " + tokens["access_token"]}
    assert client.get(PREFIX + "/me").status_code == 401
    assert client.get(PREFIX + "/me", headers=headers).json()["email"] == CREDS["email"]
    assert client.patch(PREFIX + "/me", headers=headers, json={"display_name": "Demo Name"}).json()["display_name"] == "Demo Name"
    assert client.get(PREFIX + "/me", headers=headers).json()["display_name"] == "Demo Name"
    rotated = post(client, "/refresh", {"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    assert post(client, "/refresh", {"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.post(PREFIX + "/logout", headers=headers).status_code == 200
    assert client.get(PREFIX + "/me", headers=headers).status_code == 401
    assert post(client, "/refresh", {"refresh_token": rotated.json()["refresh_token"]}).status_code == 401

def test_otp_attempt_limit(client):
    ticket = challenge(client)
    code = post(client, "/otp/request", ticket).json()["demo_code"]
    wrong = "0000" if code != "0000" else "0001"
    assert post(client, "/otp/request", ticket).status_code == 409
    for _ in range(5):
        assert post(client, "/otp/verify", {**ticket, "code": wrong}).status_code == 401
    assert post(client, "/otp/verify", {**ticket, "code": code}).status_code == 401

def test_authenticated_dashboard(client):
    assert client.get("/api/v1/dashboard").status_code == 401
    tokens = session(client)
    headers = {"Authorization": "Bearer " + tokens["access_token"]}
    client.patch(PREFIX + "/me", headers=headers, json={"display_name": "Dashboard Demo"})
    result = client.get("/api/v1/dashboard", headers=headers)
    assert result.status_code == 200
    data = result.json()
    assert data["display_name"] == "Dashboard Demo"
    assert data["balance_minor"] == 850000
    assert data["sample_balance"] is True
    assert data["payments_enabled"] is False
    assert data["accounts"] == data["recent_transactions"] == []
