"""Validated synthetic contracts used by profile scoring."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PARTNER_PATTERN = r"^partner-(?:0[1-9]|[1-4][0-9]|50)$"
PROFILE_PATTERN = r"^profile-00000000-0000-4000-8000-[0-9]{12}$"
DEFAULT_PARTNER_REF = "partner-01"
DEFAULT_PROFILE_REF = "profile-00000000-0000-4000-8000-000000000101"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def validate_synthetic_pair(partner_ref: str, profile_ref: str) -> None:
    """Require a profile from the fixed 100-profile partition of its partner."""

    partner_number = int(partner_ref.removeprefix("partner-"))
    profile_number = int(profile_ref[-12:])
    first_profile = partner_number * 100 + 1
    if not first_profile <= profile_number <= first_profile + 99:
        raise ValueError("profile_ref does not belong to partner_ref")


class ProfileScoreRequest(StrictModel):
    partner_ref: str = Field(
        default=DEFAULT_PARTNER_REF,
        min_length=10,
        max_length=10,
        pattern=PARTNER_PATTERN,
    )
    profile_ref: str = Field(
        default=DEFAULT_PROFILE_REF,
        min_length=44,
        max_length=44,
        pattern=PROFILE_PATTERN,
    )

    @model_validator(mode="after")
    def validate_reference_partition(self) -> "ProfileScoreRequest":
        validate_synthetic_pair(self.partner_ref, self.profile_ref)
        return self


class StoredProfile(StrictModel):
    age: int = Field(ge=18, le=100)
    monthly_income: Decimal = Field(ge=Decimal("0"), le=Decimal("1000000000"))
    debt_ratio: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    claims_count: int = Field(ge=0, le=100)


class OpenFinanceData(StrictModel):
    account_age_months: int = Field(default=36, ge=0, le=1_200)
    inflow_stability: Decimal = Field(
        default=Decimal("0.82"), ge=Decimal("0"), le=Decimal("1")
    )
    delinquency_count: int = Field(default=0, ge=0, le=100)


class ProfileInputs(StrictModel):
    age: int = Field(ge=18, le=100)
    monthly_income: Decimal = Field(ge=Decimal("0"), le=Decimal("1000000000"))
    debt_ratio: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    claims_count: int = Field(ge=0, le=100)
    account_age_months: int = Field(ge=0, le=1_200)
    inflow_stability: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    delinquency_count: int = Field(ge=0, le=100)


class ProfileResult(StrictModel):
    partner_ref: str = Field(pattern=PARTNER_PATTERN)
    profile_ref: str = Field(pattern=PROFILE_PATTERN)
    risk_score: int = Field(ge=0, le=1_000)
    risk_band: Literal["LOW", "MEDIUM", "HIGH"]
    cache_status: Literal["hit", "miss"]
    profile_version: str = Field(pattern=r"^[A-Za-z0-9._-]{1,32}$")

    @model_validator(mode="after")
    def validate_reference_partition(self) -> "ProfileResult":
        validate_synthetic_pair(self.partner_ref, self.profile_ref)
        return self
