import time

from app.models import ParametricEventEnvelope
from app.security import compute_signature, verify_signature, within_signature_skew


def _envelope(signature: str) -> ParametricEventEnvelope:
    return ParametricEventEnvelope(
        external_event_id="evt-000000000001",
        timestamp=1_700_000_000,
        partition_key="riesgo-01",
        signature=signature,
        payload={"tipo_evento_parametrico": "sismo", "magnitud": "6.1"},
    )


def test_valid_signature_is_accepted() -> None:
    secret = b"shared-secret"
    signature = compute_signature(
        secret,
        external_event_id="evt-000000000001",
        timestamp=1_700_000_000,
        payload={"tipo_evento_parametrico": "sismo", "magnitud": "6.1"},
    )

    assert verify_signature(secret, _envelope(signature)) is True


def test_tampered_payload_is_rejected() -> None:
    secret = b"shared-secret"
    signature = compute_signature(
        secret,
        external_event_id="evt-000000000001",
        timestamp=1_700_000_000,
        payload={"tipo_evento_parametrico": "sismo", "magnitud": "9.9"},
    )

    assert verify_signature(secret, _envelope(signature)) is False


def test_wrong_secret_is_rejected() -> None:
    signature = compute_signature(
        b"shared-secret",
        external_event_id="evt-000000000001",
        timestamp=1_700_000_000,
        payload={"tipo_evento_parametrico": "sismo", "magnitud": "6.1"},
    )

    assert verify_signature(b"different-secret", _envelope(signature)) is False


def test_signature_is_order_independent_over_payload_keys() -> None:
    secret = b"shared-secret"
    payload_a = {"a": 1, "b": 2}
    payload_b = {"b": 2, "a": 1}

    assert compute_signature(
        secret, external_event_id="evt-1", timestamp=1, payload=payload_a
    ) == compute_signature(secret, external_event_id="evt-1", timestamp=1, payload=payload_b)


def test_within_signature_skew_accepts_recent_timestamp() -> None:
    now = time.time()
    assert within_signature_skew(int(now) - 30, max_skew_seconds=600, now=now) is True


def test_within_signature_skew_rejects_stale_timestamp() -> None:
    now = time.time()
    assert within_signature_skew(int(now) - 3_600, max_skew_seconds=600, now=now) is False


def test_duplicate_external_event_id_is_not_a_signature_concern() -> None:
    """Two envelopes reusing the same external_event_id both verify fine.

    Rejecting a repeated external_event_id is explicitly NOT this module's
    job; that would break the experiment's intentional duplicate/redelivery
    test cases. Idempotency is enforced downstream, in the Inbox.
    """

    secret = b"shared-secret"
    payload = {"tipo_evento_parametrico": "sismo", "magnitud": "6.1"}
    signature = compute_signature(
        secret, external_event_id="evt-000000000001", timestamp=1_700_000_000, payload=payload
    )

    first = _envelope(signature)
    second = _envelope(signature)

    assert verify_signature(secret, first) is True
    assert verify_signature(secret, second) is True
