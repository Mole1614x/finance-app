"""Pure helpers for safe demo payment amount and QR parsing."""
import re
from decimal import Decimal

PATTERN = re.compile(r"arth-demo:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

def parse_identifier(value):
    value = value.strip()
    if not PATTERN.fullmatch(value):
        raise ValueError("Enter an ARTH demo identifier, not a UPI ID or URL.")
    return value

def parse_amount(value):
    value = value.strip()
    if not re.fullmatch(r"[0-9]{1,7}(?:\.[0-9]{1,2})?", value):
        raise ValueError("Enter rupees with up to two decimal places.")
    result = int(Decimal(value) * 100)
    if not 0 < result <= 100000000:
        raise ValueError("Amount must be between INR 0.01 and INR 10,00,000.")
    return result
