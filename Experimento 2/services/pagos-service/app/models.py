"""Strict models for the payment order consumed from ordenes-pagos."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_TOKEN_PATTERN = r"^[A-Za-z0-9._:-]+$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReceivedPaymentOrder(StrictModel):
    """The SiniestroAprobado order as published by reclamos-service's outbox."""

    operation_id: str = Field(min_length=1, max_length=100, pattern=_TOKEN_PATTERN)
    siniestro_id: str = Field(min_length=1, max_length=100, pattern=_TOKEN_PATTERN)
    monto: Decimal = Field(gt=Decimal("0"), le=Decimal("1000000000"))


class PaymentResult(StrictModel):
    is_duplicate: bool
    orden_id: str
    monto: Decimal
    estado: Literal["confirmado"]
