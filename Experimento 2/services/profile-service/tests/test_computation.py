from decimal import Decimal

from app.computation import calculate_risk_score
from app.models import ProfileInputs


def test_profile_score_uses_financial_and_history_factors() -> None:
    profile = ProfileInputs(
        age=35,
        monthly_income=Decimal("5000000"),
        debt_ratio=Decimal("0.25"),
        claims_count=1,
        account_age_months=36,
        inflow_stability=Decimal("0.82"),
        delinquency_count=0,
    )
    assert calculate_risk_score(profile=profile) == (373, "MEDIUM")


def test_profile_score_includes_delinquency_and_maps_high_risk_band() -> None:
    profile = ProfileInputs(
        age=35,
        monthly_income=Decimal("3000000"),
        debt_ratio=Decimal("0.40"),
        claims_count=2,
        account_age_months=12,
        inflow_stability=Decimal("0.50"),
        delinquency_count=2,
    )

    assert calculate_risk_score(profile=profile) == (758, "HIGH")


def test_profile_score_remains_bounded_and_maps_low_risk_band() -> None:
    healthy_profile = ProfileInputs(
        age=35,
        monthly_income=Decimal("12000000"),
        debt_ratio=Decimal("0"),
        claims_count=0,
        account_age_months=120,
        inflow_stability=Decimal("1"),
        delinquency_count=0,
    )
    high_risk_profile = ProfileInputs(
        age=35,
        monthly_income=Decimal("0"),
        debt_ratio=Decimal("1"),
        claims_count=100,
        account_age_months=0,
        inflow_stability=Decimal("0"),
        delinquency_count=100,
    )

    assert calculate_risk_score(profile=healthy_profile) == (10, "LOW")
    assert calculate_risk_score(profile=high_risk_profile) == (1_000, "HIGH")
