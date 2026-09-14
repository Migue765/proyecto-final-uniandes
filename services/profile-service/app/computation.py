"""Deterministic synthetic profile scoring with configurable CPU cost."""

from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Literal

from .models import ProfileInputs


def calculate_risk_score(
    *,
    profile: ProfileInputs,
    partner_ref: str,
    profile_ref: str,
    iterations: int,
) -> tuple[int, Literal["LOW", "MEDIUM", "HIGH"]]:
    canonical = "|".join(
        (
            partner_ref,
            profile_ref,
            str(profile.age),
            format(profile.monthly_income, "f"),
            format(profile.debt_ratio, "f"),
            str(profile.claims_count),
            str(profile.account_age_months),
            format(profile.inflow_stability, "f"),
            str(profile.delinquency_count),
        )
    ).encode("ascii")
    digest = hashlib.sha256(canonical).digest()
    accumulator = 0
    for index in range(iterations):
        digest = hashlib.sha256(digest + index.to_bytes(4, "big")).digest()
        accumulator ^= int.from_bytes(digest[:8], "big")

    income_relief = min(profile.monthly_income / Decimal("100000"), Decimal("120"))
    account_relief = min(Decimal(profile.account_age_months), Decimal("120"))
    score_value = (
        profile.debt_ratio * Decimal("500")
        + Decimal(profile.claims_count * 45)
        + Decimal(profile.delinquency_count * 75)
        + (Decimal("1") - profile.inflow_stability) * Decimal("220")
        - income_relief
        - account_relief
        + Decimal(accumulator % 101)
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
