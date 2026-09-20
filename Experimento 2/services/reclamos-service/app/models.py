"""Strict models for the parametric event consumed from entrada-parametrica."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_TOKEN_PATTERN = r"^[A-Za-z0-9._:-]+$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ParametricEventPayload(StrictModel):
    """Business content of a parametric event.

    This is the *business* validation gate: an envelope that passed the
    Adaptador de Ingreso's signature/schema check can still fail here (e.g.
    an unsupported ``tipo_evento_parametrico`` or an out-of-range value).
    That failure is deliberate for a fraction of the experiment's corpus —
    see ``experimento-2/PLAN.md`` section 8 — and is what drives those
    messages to the DLQ after SQS exhausts its redelivery attempts.
    """

    tipo_evento_parametrico: Literal["sismo", "huracan", "vuelo_retrasado", "inundacion"]
    magnitud: Decimal = Field(gt=Decimal("0"), le=Decimal("10"))
    umbral_activacion: Decimal = Field(gt=Decimal("0"), le=Decimal("10"))
    suma_asegurada: Decimal = Field(gt=Decimal("0"), le=Decimal("1000000000"))


class ReceivedParametricEvent(StrictModel):
    """The envelope as published by the Adaptador de Ingreso."""

    external_event_id: str = Field(min_length=1, max_length=100, pattern=_TOKEN_PATTERN)
    timestamp: int = Field(gt=0)
    partition_key: str = Field(min_length=1, max_length=100, pattern=_TOKEN_PATTERN)
    signature: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    payload: ParametricEventPayload


class ProcessingResult(StrictModel):
    is_duplicate: bool
    siniestro_id: str
    monto_liquidado: Decimal
    estado: Literal["aprobado", "rechazado_umbral"]
    operation_id: str | None
