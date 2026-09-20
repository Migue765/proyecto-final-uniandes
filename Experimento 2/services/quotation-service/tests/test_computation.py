from decimal import Decimal

from app.computation import calculate_monthly_premium
from app.models import QuoteRequest, Tariff


def test_actuarial_calculation_uses_quote_tariff_risk_term_and_fee() -> None:
    arguments = {
        "quote": QuoteRequest(term_months=24),
        "tariff": Tariff(
            annual_rate=Decimal("0.02"),
            fixed_fee=Decimal("1500"),
            version="synthetic-v1",
        ),
        "risk_score": 440,
    }

    assert calculate_monthly_premium(**arguments) == Decimal("19690.00")
