from mobile.onboarding import valid_email, demo_credentials, demo_phone, demo_code

def test_email_validation():
    assert valid_email("demo@example.com")
    assert not valid_email("demo@example")
    assert not valid_email("a b@example.com")

def test_only_demo_identity():
    assert demo_credentials("demo@example.com", "demo-only")
    assert not demo_credentials("demo@example.com", "wrong")
    assert not demo_credentials("real@example.com", "demo-only")
    assert demo_phone("9000000000")
    assert not demo_phone("1234567890")

def test_demo_otp():
    assert demo_code("7358")
    assert not demo_code("7359")
    assert not demo_code("73580")
