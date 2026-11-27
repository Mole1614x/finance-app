from types import SimpleNamespace
from backend.tests.test_auth import client
from backend.tests.test_ledger import headers, login, init, move
from backend.app import ai_assistant as ai

BASE = "/api/v1/analytics"

def enable(monkeypatch):
    monkeypatch.setenv("ARTH_AI_ENABLED", "1")
    monkeypatch.setenv("ARTH_GEMINI_API_KEY", "fictional-test-key")
    monkeypatch.setenv("ARTH_GEMINI_MODEL", "mock-model")

def test_opt_in_and_minimized_payload(client, monkeypatch):
    enable(monkeypatch)
    a, b = headers(client), login(client)
    init(client, a)
    init(client, b)
    assert client.put(BASE+"/goal", headers=a, json={"title":"Private demo title", "target_minor":100000}).status_code == 200
    assert move(client, a, amount=50000).status_code == 200
    calls = []
    def fake(topic, facts):
        calls.append((topic, facts))
        return "Review the savings target regularly."
    monkeypatch.setattr(ai, "generate", fake)
    path = BASE+"/assistant"
    assert client.post(path, headers=a, json={"topic":"savings"}).json()["engine"] == "deterministic rules"
    assert calls == []
    assert client.post(path, json={"topic":"savings","allow_external_ai":True}).status_code == 401
    result = client.post(path, headers=a, json={"topic":"savings","allow_external_ai":True})
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["engine"] == "gemini" and data["explanation"]
    assert calls == [("savings", {"target_minor":100000,"saved_minor":50000,"remaining_minor":50000})]
    assert data["answer"]["title"] == "Private demo title"  # local facts, not provider input
    other = client.post(path, headers=b, json={"topic":"savings","allow_external_ai":True}).json()
    assert other["answer"]["target_minor"] is None
    assert calls[-1][1]["saved_minor"] == 0

def test_provider_failure_and_disabled(client, monkeypatch):
    a = headers(client)
    init(client, a)
    enable(monkeypatch)
    def failure(*args):
        raise RuntimeError("secret internal provider error")
    monkeypatch.setattr(ai, "generate", failure)
    path = BASE+"/assistant"
    request = {"topic":"budget", "allow_external_ai":True}
    result = client.post(path, headers=a, json=request).json()
    assert result["engine"] == "deterministic rules"
    assert result["fallback_reason"] == "provider_unavailable"
    assert "secret" not in str(result)
    monkeypatch.setenv("ARTH_AI_ENABLED", "0")
    assert client.post(path, headers=a, json=request).json()["fallback_reason"] == "provider_unconfigured"
    assert client.post(path, headers=a, json={**request,"allow_external_ai":"true"}).status_code == 422

def test_risk_and_category_allowlist():
    assert ai.aggregate("risk", {"flags":[{"transaction_id":"private-id","amount_minor":999}]}) == {
        "review_flag_count":1, "fraud_confirmed":False}
    assert ai.aggregate("spending", {"spent_minor":100,"categories":[
        {"category":"Electricity","amount_minor":50},{"category":"Private user text","amount_minor":50}
    ]}) == {"spent_minor":100,"categories":[{"category":"Electricity","amount_minor":50}]}

def test_sdk_adapter(monkeypatch):
    enable(monkeypatch)
    captured = {}
    class MockClient:
        def __init__(self, **kw):
            captured.update(kw)
            self.models = SimpleNamespace(generate_content=self.call)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def call(self, **kw):
            captured.update(kw)
            return SimpleNamespace(text="Demo explanation.")
    monkeypatch.setattr(ai.genai, "Client", MockClient)
    result = ai.explain("budget", {"limit_minor":100,"remaining_minor":50}, True)
    assert result["engine"] == "gemini"
    assert captured["api_key"] == "fictional-test-key"
    assert captured["model"] == "mock-model"
    assert captured["http_options"].timeout == 5000
    assert "remaining_minor" in captured["contents"]
    assert "fictional-test-key" not in captured["contents"]
