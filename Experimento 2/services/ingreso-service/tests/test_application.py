import time

from app.application import create_app
from app.config import Settings
from app.security import compute_signature

SECRET = b"shared-secret"


class FakePublisher:
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = ready
        self.published: list[object] = []

    def publish(self, envelope: object) -> None:
        self.published.append(envelope)

    def ping(self) -> bool:
        return self.ready


class FakeSecretProvider:
    def __init__(self, *, ready: bool = True, secret: bytes = SECRET) -> None:
        self.ready = ready
        self._secret = secret

    def get_secret(self) -> bytes:
        return self._secret

    def ping(self) -> bool:
        return self.ready


def settings() -> Settings:
    return Settings(
        sqs_entrada_parametrica_url=(
            "https://sqs.us-east-1.amazonaws.com/969325258550/"
            "solventa-exp2-entrada-parametrica.fifo"
        ),
        hmac_secret_arn="arn:aws:secretsmanager:us-east-1:969325258550:secret:exp2-hmac",
    )


def signed_body(*, external_event_id: str = "evt-000000000001", timestamp: int | None = None) -> dict:
    # A fixed epoch here would drift out of signature_max_skew_seconds as real
    # time passes; compute "now" at call time so these tests never go stale.
    if timestamp is None:
        timestamp = int(time.time())
    payload = {"tipo_evento_parametrico": "sismo", "magnitud": "6.1"}
    signature = compute_signature(
        SECRET, external_event_id=external_event_id, timestamp=timestamp, payload=payload
    )
    return {
        "external_event_id": external_event_id,
        "timestamp": timestamp,
        "partition_key": "riesgo-01",
        "signature": signature,
        "payload": payload,
    }


def test_valid_signed_event_is_accepted_and_published() -> None:
    publisher = FakePublisher()
    app = create_app(settings(), publisher=publisher, secret_provider=FakeSecretProvider())

    response = app.test_client().post("/parametricos/v1/eventos", json=signed_body())

    assert response.status_code == 202
    assert response.get_json() == {"external_event_id": "evt-000000000001", "status": "accepted"}
    assert len(publisher.published) == 1


def test_invalid_signature_is_rejected_without_publishing() -> None:
    publisher = FakePublisher()
    app = create_app(settings(), publisher=publisher, secret_provider=FakeSecretProvider())

    body = signed_body()
    body["signature"] = "0" * 64

    response = app.test_client().post("/parametricos/v1/eventos", json=body)

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_signature"}
    assert publisher.published == []


def test_extra_field_is_rejected_as_invalid_request() -> None:
    app = create_app(
        settings(), publisher=FakePublisher(), secret_provider=FakeSecretProvider()
    )

    body = signed_body()
    body["unexpected"] = True

    response = app.test_client().post("/parametricos/v1/eventos", json=body)

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_request"}


def test_duplicate_external_event_id_is_accepted_twice_by_the_edge() -> None:
    """The edge never rejects a repeated external_event_id — see security.py."""

    publisher = FakePublisher()
    app = create_app(settings(), publisher=publisher, secret_provider=FakeSecretProvider())
    client = app.test_client()

    first = client.post("/parametricos/v1/eventos", json=signed_body())
    second = client.post("/parametricos/v1/eventos", json=signed_body())

    assert first.status_code == 202
    assert second.status_code == 202
    assert len(publisher.published) == 2


def test_stale_timestamp_is_rejected() -> None:
    app = create_app(
        settings(), publisher=FakePublisher(), secret_provider=FakeSecretProvider()
    )

    response = app.test_client().post(
        "/parametricos/v1/eventos", json=signed_body(timestamp=1)
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "stale_timestamp"}


def test_readiness_reflects_dependencies() -> None:
    app = create_app(
        settings(),
        publisher=FakePublisher(ready=False),
        secret_provider=FakeSecretProvider(ready=True),
    )

    response = app.test_client().get("/health/ready")

    assert response.status_code == 503
    assert response.get_json()["checks"] == {"sqs": False, "hmac_secret": True}


def test_metrics_expose_event_outcomes() -> None:
    app = create_app(
        settings(), publisher=FakePublisher(), secret_provider=FakeSecretProvider()
    )
    client = app.test_client()
    client.post("/parametricos/v1/eventos", json=signed_body())

    metrics = client.get("/metrics").get_data(as_text=True)

    assert 'solventa_ingreso_events_total{outcome="accepted"}' in metrics
