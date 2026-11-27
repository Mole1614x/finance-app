import pytest
from mobile.payment_data import parse_amount, parse_identifier

def test_amount():
    assert parse_amount("500.01") == 50001
    assert parse_amount("0.01") == 1
    for value in ("0", "-1", "1.001", "1e2", "NaN", "1000000.01"):
        with pytest.raises(ValueError):
            parse_amount(value)

def test_identifier():
    assert parse_identifier("arth-demo:00000000-0000-0000-0000-000000000000").startswith("arth-demo:")
    for value in ("upi://pay", "https://example.com", "test@upi"):
        with pytest.raises(ValueError):
            parse_identifier(value)
