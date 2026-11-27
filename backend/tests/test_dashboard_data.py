import pytest
from mobile.dashboard_data import inr, chart_fractions

def test_inr():
    assert inr(850000) == "INR 8,500.00"
    assert inr(-123456789) == "-INR 12,34,567.89"
    assert inr(0) == "INR 0.00"
    with pytest.raises(ValueError):
        inr(12.5)

def test_chart():
    assert chart_fractions([10, -5, 0]) == [1, -.5, 0]
    assert chart_fractions([]) == []
    assert chart_fractions([0]) == [0]
