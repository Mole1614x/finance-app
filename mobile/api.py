"""Small standard-library client for the local demo backend."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

class APIError(Exception):
    pass

class AuthClient:
    def __init__(self):
        self.base = os.getenv("ARTH_API_URL", "http://127.0.0.1:8000").rstrip("/")
        parsed = urlparse(self.base)
        if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "10.0.2.2"}):
            raise ValueError("Use HTTPS or a local development address.")
        self.challenge = None
        self.access = None
        self.refresh = None

    def call(self, path, data=None, method="POST", namespace="/api/v1/auth", extra_headers=None):
        headers = {"Content-Type": "application/json"}
        headers.update(extra_headers or {})
        if self.access:
            headers["Authorization"] = "Bearer " + self.access
        req = Request(self.base + namespace + path,
                      data=json.dumps(data).encode() if data is not None else None,
                      headers=headers, method=method)
        try:
            with urlopen(req, timeout=8) as response:
                return json.load(response)
        except HTTPError as exc:
            try:
                detail = json.load(exc).get("detail")
            except (ValueError, OSError):
                detail = None
            raise APIError(detail if isinstance(detail, str) else "Check the demo input.") from None
        except (URLError, TimeoutError, OSError):
            raise APIError("Cannot reach the local ARTH backend.") from None

    def credentials(self, mode, email, password):
        self.challenge = self.call("/register" if mode == "signup" else "/login",
                                   {"email": email, "password": password})["challenge_id"]

    def request_code(self):
        return self.call("/otp/request", {"challenge_id": self.challenge})["demo_code"]

    def verify(self, code):
        tokens = self.call("/otp/verify", {"challenge_id": self.challenge, "code": code})
        self.access, self.refresh = tokens["access_token"], tokens["refresh_token"]
        self.challenge = None

    def dashboard(self):
        return self.call('', method='GET', namespace='/api/v1/dashboard')

    def accounts(self):
        return self.call("", method="GET", namespace="/api/v1/accounts")

    def initialize_accounts(self):
        return self.call("/initialize", namespace="/api/v1/accounts")

    def move(self, source, destination, amount_minor, key):
        return self.call("/move", {"source": source, "destination": destination, "amount_minor": amount_minor}, namespace="/api/v1/accounts", extra_headers={"Idempotency-Key": key})

    def receive_payment(self):
        return self.call("/receive", method="GET", namespace="/api/v1/payments")

    def resolve_payment(self, identifier):
        return self.call("/resolve", {"payment_id": identifier}, namespace="/api/v1/payments")

    def send_payment(self, identifier, amount_minor, key):
        return self.call("/send", {"payment_id": identifier, "amount_minor": amount_minor},
                         namespace="/api/v1/payments", extra_headers={"Idempotency-Key": key})

    def transactions(self, kind="all", offset=0):
        from urllib.parse import urlencode
        query = urlencode({"kind": kind, "offset": offset, "limit": 20})
        return self.call("?" + query, method="GET", namespace="/api/v1/transactions")

    def transaction(self, reference):
        from urllib.parse import quote
        return self.call("/" + quote(reference, safe=""), method="GET", namespace="/api/v1/transactions")

    def lookup_payment(self, key):
        return self.call("/payment-lookup", {"idempotency_key": key}, namespace="/api/v1/transactions")

    def service_catalog(self):
        return self.call("/catalog", method="GET", namespace="/api/v1/services")

    def purchase_service(self, sku, cycle, key):
        return self.call("/purchase", {"sku": sku, "bill_cycle": cycle},
                         namespace="/api/v1/services", extra_headers={"Idempotency-Key": key})

    def service_orders(self):
        return self.call("/orders", method="GET", namespace="/api/v1/services")

    def rewards(self):
        return self.call("/rewards", method="GET", namespace="/api/v1/services")

    def insights(self, month=None):
        from urllib.parse import urlencode
        query = "?" + urlencode({"month": month}) if month else ""
        return self.call("/summary" + query, method="GET", namespace="/api/v1/analytics")

    def set_budget(self, month, limit_minor):
        return self.call("/budget", {"month": month, "limit_minor": limit_minor}, method="PUT", namespace="/api/v1/analytics")

    def goal(self):
        return self.call("/goal", method="GET", namespace="/api/v1/analytics")

    def set_goal(self, title, target_minor):
        return self.call("/goal", {"title": title, "target_minor": target_minor}, method="PUT", namespace="/api/v1/analytics")

    def assistant(self, topic):
        return self.call("/assistant", {"topic": topic}, namespace="/api/v1/analytics")

    def profile(self):
        return self.call('/me', method='GET')

    def update_profile(self, name):
        return self.call('/me', {'display_name': name}, method='PATCH')

    def logout(self):
        try:
            if self.access:
                self.call("/logout")
        finally:
            self.access = self.refresh = self.challenge = None
