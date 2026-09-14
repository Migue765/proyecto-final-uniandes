from decimal import Decimal

from app.computation import calculate_monthly_premium
from app.models import QuoteRequest, Tariff


def test_actuarial_calculation_is_deterministic() -> None:
    arguments = {
        "quote": QuoteRequest(),
        "tariff": Tariff(
            annual_rate=Decimal("0.02"),
            fixed_fee=Decimal("1500"),
            version="synthetic-v1",
        ),
        "risk_score": 440,
        "partner_ref": "partner-01",
        "profile_ref": "profile-00000000-0000-4000-8000-000000000101",
        "iterations": 25,
    }

    first = calculate_monthly_premium(**arguments)
    second = calculate_monthly_premium(**arguments)

    assert first == second
    assert first[0] > Decimal("0")
    assert len(first[1]) == 16
