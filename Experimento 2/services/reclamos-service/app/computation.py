"""Deterministic, self-contained parametric evaluation and settlement.

This computes a synthetic payout purely from fields already present in the
event payload. It deliberately performs no external or reference-data
lookups: the experiment's purpose is to validate ingestion integrity,
idempotency and backpressure (ASR-EVT-01), not underwriting realism, so no
mock/reference dataset needs to be pre-populated before a run.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from .models import ParametricEventPayload

_MIN_PAYOUT_FACTOR = Decimal("0.5")
_MAX_PAYOUT_FACTOR = Decimal("1")


def evaluate_and_settle(payload: ParametricEventPayload) -> Decimal:
    """Return the settlement amount, or ``0.00`` when the trigger is not met."""

    if payload.magnitud < payload.umbral_activacion:
        return Decimal("0.00")

    excess = min(payload.magnitud - payload.umbral_activacion, payload.umbral_activacion)
    payout_factor = min(
        _MIN_PAYOUT_FACTOR + (excess / payload.umbral_activacion) / Decimal("2"),
        _MAX_PAYOUT_FACTOR,
    )
    return (payload.suma_asegurada * payout_factor).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
