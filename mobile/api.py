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
