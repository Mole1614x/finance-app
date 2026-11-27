from concurrent.futures import ThreadPoolExecutor
from backend.tests.test_auth import client
from backend.tests.test_ledger import headers, login, init, balances, assert_reconciled
from backend.app.ledger import STARTING_MINOR

BASE = "/api/v1/services"

def catalog(client, h):
    r = client.get(BASE + "/catalog", headers=h)
    assert r.status_code == 200, r.text
    return {item["sku"]: item for item in r.json()["items"]}

def purchase(client, h, sku="electricity", cycle=None, key="demo-order-1"):
    return client.post(BASE + "/purchase", headers={**h, "Idempotency-Key": key},
                       json={"sku": sku, "bill_cycle": cycle})

def test_bill_and_rewards(client):
    h = headers(client)
    assert client.get(BASE + "/catalog").status_code == 401
    product = catalog(client, h)["electricity"]
    cycle = product["bill_cycle"]
    assert purchase(client, h, cycle=cycle).status_code == 409
    init(client, h)
    first = purchase(client, h, cycle=cycle)
    assert first.status_code == 200, first.text
    order = first.json()
    assert order["cashback_minor"] == 2000
    assert purchase(client, h, cycle=cycle).json() == order
    assert purchase(client, h, cycle=cycle, key="demo-order-2").status_code == 409
    assert purchase(client, h, sku="water", cycle=cycle).status_code == 409
    assert balances(client, h)["checking"] == STARTING_MINOR - 125000 + 2000
    assert catalog(client, h)["electricity"]["paid"]
    assert client.get(BASE + "/rewards", headers=h).json()["earned_minor"] == 2000
    assert client.get(BASE + "/orders", headers=h).json()["items"] == [order]
    for kind, change in (("service", -125000), ("reward", 2000)):
        rows = client.get("/api/v1/transactions", headers=h, params={"kind": kind}).json()["items"]
        assert len(rows) == 1 and rows[0]["balance_change_minor"] == change
    assert client.get("/api/v1/transactions", headers=h, params={"kind": "internal"}).json()["items"] == []
    assert_reconciled()

def test_recharge_and_isolation(client):
    a, b = headers(client), login(client)
    init(client, a)
    init(client, b)
    for key in ("recharge-1", "recharge-2"):
        assert purchase(client, a, sku="mobile-199", key=key).status_code == 200
    assert balances(client, a)["checking"] == STARTING_MINOR - 2*(19900-398)
    assert balances(client, b)["checking"] == STARTING_MINOR
    assert client.get(BASE + "/rewards", headers=b).json()["earned_minor"] == 0
    assert client.get(BASE + "/orders", headers=b).json()["items"] == []
    assert purchase(client, a, sku="unknown", key="bad-sku-1").status_code == 404
    assert purchase(client, a, sku="electricity", cycle="2000-01", key="old-bill-1").status_code == 409
    assert_reconciled()

def test_concurrent_bill_and_insufficient_funds(client):
    h = headers(client)
    init(client, h)
    cycle = catalog(client, h)["electricity"]["bill_cycle"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda key: purchase(client, h, cycle=cycle, key=key), ["bill-race-1", "bill-race-2"]))
    assert sorted(r.status_code for r in results) == [200, 409]
    from backend.tests.test_ledger import move
    remaining = balances(client, h)["checking"]
    assert move(client, h, amount=remaining).status_code == 200
    assert purchase(client, h, sku="mobile-199", key="no-funds-1").status_code == 409
    assert client.get(BASE + "/rewards", headers=h).json()["earned_minor"] == 2000
    assert_reconciled()
