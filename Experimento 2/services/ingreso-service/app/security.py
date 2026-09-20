"""HMAC signature verification and shared-secret retrieval.

Signature verification is purely an authenticity check ("was this envelope
produced by a holder of the shared secret?"). It is deliberately NOT a
replay/nonce/idempotency gate: the timestamp skew check only rejects
obviously stale or clock-skewed requests, not requests reusing an
``external_event_id`` that was already seen. Rejecting on repetition here
would silently break the experiment's intentional duplicate and
late-redelivery test cases. Business idempotency is enforced downstream, in
each consumer's Inbox (a unique database constraint), never at this edge.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .config import Settings
from .models import ParametricEventEnvelope


class SecretUnavailable(RuntimeError):
    """The HMAC shared secret could not be retrieved."""


def _canonical_message(external_event_id: str, timestamp: int, payload: dict[str, Any]) -> bytes:
    compact_payload = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return f"{external_event_id}|{timestamp}|{compact_payload}".encode("utf-8")


def compute_signature(secret: bytes, *, external_event_id: str, timestamp: int, payload: dict[str, Any]) -> str:
    """Return the hex-encoded HMAC-SHA256 signature for an envelope's contents."""

    message = _canonical_message(external_event_id, timestamp, payload)
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_signature(secret: bytes, envelope: ParametricEventEnvelope) -> bool:
    expected = compute_signature(
        secret,
        external_event_id=envelope.external_event_id,
        timestamp=envelope.timestamp,
        payload=envelope.payload,
    )
    return hmac.compare_digest(expected, envelope.signature)


def within_signature_skew(timestamp: int, max_skew_seconds: float, *, now: float | None = None) -> bool:
    reference = now if now is not None else time.time()
    return abs(reference - timestamp) <= max_skew_seconds


class SecretProvider:
    """Fetches and caches the HMAC shared secret from AWS Secrets Manager."""

    def __init__(self, settings: Settings) -> None:
        self._client = boto3.client("secretsmanager", region_name=settings.aws_region)
        self._secret_arn = settings.hmac_secret_arn
        self._cached: bytes | None = None

    def get_secret(self) -> bytes:
        if self._cached is None:
            try:
                response = self._client.get_secret_value(SecretId=self._secret_arn)
            except (BotoCoreError, ClientError) as error:
                raise SecretUnavailable("hmac shared secret unavailable") from error
            secret_string = response.get("SecretString")
            if not secret_string:
                raise SecretUnavailable("hmac shared secret is not a string secret")
            self._cached = secret_string.encode("utf-8")
        return self._cached

    def ping(self) -> bool:
        try:
            self.get_secret()
            return True
        except SecretUnavailable:
            return False

    def close(self) -> None:
        self._client.close()
