"""Arithmetic risk scoring for a validated customer profile."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from .models import ProfileInputs


def calculate_risk_score(
    *,
    profile: ProfileInputs,
) -> tuple[int, Literal["LOW", "MEDIUM", "HIGH"]]:
    income_relief = min(profile.monthly_income / Decimal("100000"), Decimal("120"))
    account_relief = min(Decimal(profile.account_age_months), Decimal("120"))
    score_value = (
        profile.debt_ratio * Decimal("500")
        + Decimal(profile.claims_count * 45)
        + Decimal(profile.delinquency_count * 75)
        + (Decimal("1") - profile.inflow_stability) * Decimal("220")
        - income_relief
        - account_relief
        + Decimal("250")
    )
    score = max(0, min(1_000, int(score_value)))
    if score < 350:
        band: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    elif score < 650:
        band = "MEDIUM"
    else:
        band = "HIGH"
    return score, band
