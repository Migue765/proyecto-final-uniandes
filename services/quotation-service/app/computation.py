"""Deterministic, CPU-consuming actuarial calculation used by the experiment."""

from __future__ import annotations

import hashlib
from decimal import Decimal, ROUND_HALF_UP

from .models import QuoteRequest, Tariff


def calculate_monthly_premium(
    *,
    quote: QuoteRequest,
    tariff: Tariff,
    risk_score: int,
    partner_ref: str,
    profile_ref: str,
    iterations: int,
) -> tuple[Decimal, str]:
    """Return a stable premium and checksum while consuming measurable CPU.

    Hashing is intentionally iterative: this is real CPU work, contains no
    sleeps, and can be calibrated through ``QUOTE_CPU_ITERATIONS``.
    """

    canonical = "|".join(
        (
            partner_ref,
            profile_ref,
            format(quote.requested_amount, "f"),
            str(quote.term_months),
            format(tariff.annual_rate, "f"),
            str(risk_score),
        )
    ).encode("ascii")
    digest = hashlib.sha256(canonical).digest()
    accumulator = 0
    for index in range(iterations):
        digest = hashlib.sha256(digest + index.to_bytes(4, "big")).digest()
        accumulator ^= int.from_bytes(digest[:8], "big")

    risk_multiplier = Decimal("0.85") + (Decimal(risk_score) / Decimal("2000"))
    term_multiplier = Decimal("1") + (
        Decimal(max(quote.term_months - 12, 0)) / Decimal("600")
    )
    deterministic_adjustment = Decimal(accumulator % 1_000) / Decimal("100")
    premium = (
        quote.requested_amount
        * tariff.annual_rate
        / Decimal("12")
        * risk_multiplier
        * term_multiplier
        + tariff.fixed_fee
        + deterministic_adjustment
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return premium, digest.hex()[:16]
