"""Actuarial premium calculation used by the quotation flow."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .models import QuoteRequest, Tariff


def calculate_monthly_premium(
    *,
    quote: QuoteRequest,
    tariff: Tariff,
    risk_score: int,
) -> Decimal:
    """Return the monthly premium from the validated quote and tariff."""

    risk_multiplier = Decimal("0.85") + (Decimal(risk_score) / Decimal("2000"))
    term_multiplier = Decimal("1") + (
        Decimal(max(quote.term_months - 12, 0)) / Decimal("600")
    )
    return (
        quote.requested_amount
        * tariff.annual_rate
        / Decimal("12")
        * risk_multiplier
        * term_multiplier
        + tariff.fixed_fee
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
