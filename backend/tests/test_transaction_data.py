from mobile.transaction_data import row_label, receipt_text

def test_receipt():
    data = {"kind": "sent", "amount_minor": 50001, "created_at": 0,
            "status": "completed", "source": "checking", "destination": "another demo account",
            "id": "ledger-ref", "payment_reference": "payment-ref"}
    assert "INR 500.01" in row_label(data)
    text = receipt_text(data)
    assert "SIMULATED" in text
    assert "ledger-ref" in text and "payment-ref" in text
    assert "01 Jan 1970, 00:00 UTC" in text
