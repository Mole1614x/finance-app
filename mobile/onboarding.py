"""UI-only demo onboarding. No real identity, OTP delivery or authentication."""
import re

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo-only"
DEMO_PHONE = "9000000000"
DEMO_CODE = "7358"

def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value.strip()))

def demo_credentials(email: str, password: str) -> bool:
    return valid_email(email) and email.strip().lower() == DEMO_EMAIL and password == DEMO_PASSWORD

def demo_phone(value: str) -> bool:
    return value.strip() == DEMO_PHONE

def demo_code(value: str) -> bool:
    return value.strip() == DEMO_CODE
