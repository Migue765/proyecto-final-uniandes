from app.application import create_app
from app.config import Settings


class FakeRepository:
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = ready

    def ping(self) -> bool:
        return self.ready

    def close(self) -> None:
        pass


class FakeBackgroundThread:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def is_alive(self) -> bool:
        return self.started

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


class FakeDlqClient:
    def __init__(self) -> None:
        self._attributes = {
            "https://sqs.us-east-1.amazonaws.com/969325258550/solventa-exp2-entrada-parametrica-dlq.fifo": {
                "ApproximateNumberOfMessages": "5"
            },
            "https://sqs.us-east-1.amazonaws.com/969325258550/solventa-exp2-ordenes-pagos-dlq.fifo": {
                "ApproximateNumberOfMessages": "0"
            },
        }

    def get_queue_attributes(self, *, QueueUrl: str, AttributeNames: list[str]) -> dict:
        del AttributeNames
        return {"Attributes": self._attributes[QueueUrl]}

    def receive_message(self, **kwargs: object) -> dict:
        del kwargs
        return {"Messages": [{"MessageId": "m1", "Body": '{"external_event_id":"evt-x"}'}]}


def settings() -> Settings:
    return Settings(
        database_url="postgresql://runtime:test-password@placeholder.invalid/reclamos",
        sqs_entrada_parametrica_url=(
            "https://sqs.us-east-1.amazonaws.com/969325258550/"
            "solventa-exp2-entrada-parametrica.fifo"
        ),
        sqs_entrada_parametrica_dlq_url=(
            "https://sqs.us-east-1.amazonaws.com/969325258550/"
            "solventa-exp2-entrada-parametrica-dlq.fifo"
        ),
        sqs_ordenes_pagos_url=(
            "https://sqs.us-east-1.amazonaws.com/969325258550/solventa-exp2-ordenes-pagos.fifo"
        ),
        sqs_ordenes_pagos_dlq_url=(
            "https://sqs.us-east-1.amazonaws.com/969325258550/"
            "solventa-exp2-ordenes-pagos-dlq.fifo"
        ),
    )


def build_app(**overrides: object):
    defaults = dict(
        repository=FakeRepository(),
        consumer=FakeBackgroundThread(),
        outbox_publisher=FakeBackgroundThread(),
        dlq_client=FakeDlqClient(),
    )
    defaults.update(overrides)
    return create_app(settings(), **defaults)


def test_readiness_reflects_database_health() -> None:
    app = build_app(repository=FakeRepository(ready=False))

    response = app.test_client().get("/health/ready")

    assert response.status_code == 503
    assert response.get_json()["checks"] == {"postgresql": False}


def test_dlq_status_endpoint_reports_both_queues() -> None:
    app = build_app()

    response = app.test_client().get("/internal/v1/dlq/status")

    assert response.status_code == 200
    assert response.get_json() == {"entrada_parametrica_dlq": 5, "ordenes_pagos_dlq": 0}


def test_dlq_messages_endpoint_requires_a_known_queue_alias() -> None:
    app = build_app()

    response = app.test_client().get("/internal/v1/dlq/messages?queue=unknown")

    assert response.status_code == 400


def test_dlq_messages_endpoint_returns_peeked_messages() -> None:
    app = build_app()

    response = app.test_client().get("/internal/v1/dlq/messages?queue=entrada&limit=1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["queue"] == "entrada"
    assert payload["messages"] == [{"message_id": "m1", "body": '{"external_event_id":"evt-x"}'}]


def test_dlq_messages_endpoint_caps_limit_at_configured_maximum() -> None:
    app = build_app()

    response = app.test_client().get("/internal/v1/dlq/messages?queue=entrada&limit=999999")

    assert response.status_code == 200


def test_unknown_route_returns_404_not_internal_error() -> None:
    app = build_app()

    response = app.test_client().get("/does-not-exist")

    assert response.status_code == 404
