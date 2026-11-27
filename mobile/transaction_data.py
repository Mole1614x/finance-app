"""Presentation of synthetic ledger receipts, independent of Kivy."""
from datetime import datetime, timezone
try:
    from .dashboard_data import inr
except ImportError:
    from dashboard_data import inr

NAMES = {"opening": "Opening funds", "internal": "Account transfer",
         "sent": "Money sent", "received": "Money received"}

def time_label(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%d %b %Y, %H:%M UTC")

def row_label(data):
    return NAMES.get(data["kind"], "Transaction") + " | " + inr(data["amount_minor"]) + "\n" + time_label(data["created_at"])

def receipt_text(data):
    return "\n".join([
        "ARTH — SIMULATED RECEIPT (no real money)",
        NAMES.get(data["kind"], "Transaction"),
        inr(data["amount_minor"]),
        "Status: " + data["status"],
        "Date: " + time_label(data["created_at"]),
        "From: " + data["source"],
        "To: " + data["destination"],
        "Ledger reference: " + data["id"],
        "Payment reference: " + (data.get("payment_reference") or "Not applicable"),
    ])
