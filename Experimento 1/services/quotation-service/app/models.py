"""Strict request, dependency-response and domain models."""

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


class QuoteRequest(StrictModel):
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
    requested_amount: Decimal = Field(
        default=Decimal("10000000"), ge=Decimal("100000"), le=Decimal("1000000000")
    )
    term_months: int = Field(default=12, ge=1, le=60)

    @model_validator(mode="after")
    def validate_reference_partition(self) -> "QuoteRequest":
        validate_synthetic_pair(self.partner_ref, self.profile_ref)
        return self


class Tariff(StrictModel):
    annual_rate: Decimal = Field(gt=Decimal("0"), le=Decimal("1"))
    fixed_fee: Decimal = Field(ge=Decimal("0"), le=Decimal("1000000"))
    version: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")


class ProfileResponse(StrictModel):
    partner_ref: str = Field(pattern=PARTNER_PATTERN)
    profile_ref: str = Field(pattern=PROFILE_PATTERN)
    risk_score: int = Field(ge=0, le=1000)
    risk_band: Literal["LOW", "MEDIUM", "HIGH"]
    cache_status: Literal["hit", "miss"]
    profile_version: str = Field(pattern=r"^[A-Za-z0-9._-]{1,32}$")

    @model_validator(mode="after")
    def validate_reference_partition(self) -> "ProfileResponse":
        validate_synthetic_pair(self.partner_ref, self.profile_ref)
        return self


class QuoteResult(StrictModel):
    quotation_id: str = Field(
        pattern=(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
            r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        )
    )
    request_id: str = Field(
        pattern=(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
            r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        )
    )
    partner_ref: str = Field(pattern=PARTNER_PATTERN)
    profile_ref: str = Field(pattern=PROFILE_PATTERN)
    currency: Literal["COP"] = "COP"
    monthly_premium: str = Field(pattern=r"^(?:0|[1-9][0-9]{0,15})\.[0-9]{2}$")
    risk_score: int = Field(ge=0, le=1_000)
    tariff_version: str = Field(pattern=r"^[A-Za-z0-9._-]{1,32}$")
    calculation_checksum: str = Field(pattern=r"^[0-9a-f]{16}$")

    @model_validator(mode="after")
    def validate_reference_partition(self) -> "QuoteResult":
        validate_synthetic_pair(self.partner_ref, self.profile_ref)
        return self
