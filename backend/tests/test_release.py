import os
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from backend.app.auth import Base
from backend.app.security import RateLimiter
from backend.tests.test_auth import client

def test_migration_schema(tmp_path, monkeypatch):
    url = "sqlite:///" + str(tmp_path / "migration.db")
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.check(config)
    db = create_engine(url)
    assert set(Base.metadata.tables) <= set(inspect(db).get_table_names())
    command.downgrade(config, "base")
    assert not set(Base.metadata.tables) & set(inspect(db).get_table_names())
    db.dispose()

def test_rate_limit_window():
    limiter = RateLimiter(max_keys=2)
    assert limiter.allow("test", 2, 120)
    assert limiter.allow("test", 2, 120)
    assert not limiter.allow("test", 2, 120)
    assert limiter.allow("test", 2, 180)
    assert limiter.allow("other", 1, 180)
    assert not limiter.allow("third", 1, 180)

def test_security_headers_and_throttle(client, monkeypatch):
    monkeypatch.setenv("ARTH_AUTH_RATE_LIMIT", "2")
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    for _ in range(2):
        response = client.post("/api/v1/auth/login", json={"email":"demo@example.com","password":"demo-password"})
        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"
    response = client.post("/api/v1/auth/login", json={})
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"

def test_redis_rate_limit():
    url = os.getenv("ARTH_TEST_REDIS_URL")
    if not url:
        pytest.skip("Disposable Redis integration service not configured")
    limiter = RateLimiter(url)
    identity = str(uuid4())
    assert limiter.allow(identity, 1)
    assert not limiter.allow(identity, 1)
