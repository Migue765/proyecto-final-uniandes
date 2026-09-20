"""Strict request envelope for the parametric event ingress."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_TOKEN_PATTERN = r"^[A-Za-z0-9._:-]+$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ParametricEventEnvelope(StrictModel):
    """The signed envelope produced by the parametric event generator.

    ``signature`` authenticates ``external_event_id`` + ``timestamp`` +
    ``payload`` (see ``app.security.compute_signature`` for the exact
    canonical string). It intentionally does not gate on uniqueness: the
    generator sends deliberate exact duplicates and late redeliveries of the
    same ``external_event_id`` to exercise the Inbox pattern downstream, and a
    valid signature must accept all of them. Real idempotency is enforced only
    by Reclamos and Pagos, never here.
    """

    external_event_id: str = Field(min_length=1, max_length=100, pattern=_TOKEN_PATTERN)
    timestamp: int = Field(gt=0, description="Unix epoch seconds, set by the sender.")
    partition_key: str = Field(min_length=1, max_length=100, pattern=_TOKEN_PATTERN)
    signature: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    payload: dict[str, Any]
