from decimal import Decimal

from app.computation import calculate_risk_score
from app.models import ProfileInputs


def test_profile_score_is_deterministic_and_bounded() -> None:
    profile = ProfileInputs(
        age=35,
        monthly_income=Decimal("5000000"),
        debt_ratio=Decimal("0.25"),
        claims_count=1,
        account_age_months=36,
        inflow_stability=Decimal("0.82"),
        delinquency_count=0,
    )
    arguments = {
        "profile": profile,
        "partner_ref": "partner-01",
        "profile_ref": "profile-00000000-0000-4000-8000-000000000101",
        "iterations": 25,
    }

    first = calculate_risk_score(**arguments)
    second = calculate_risk_score(**arguments)

    assert first == second
    assert 0 <= first[0] <= 1_000
    assert first[1] in {"LOW", "MEDIUM", "HIGH"}
