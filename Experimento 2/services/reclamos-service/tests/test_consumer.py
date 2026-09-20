import json
import logging
from decimal import Decimal

from app.config import Settings
from app.consumer import ConsumerLoop
from app.models import ProcessingResult
from app.observability import Metrics


class FakeSqsClient:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_message(self, *, QueueUrl: str, ReceiptHandle: str) -> None:
        del QueueUrl
        self.deleted.append(ReceiptHandle)


class FakeRepository:
    def __init__(self, result: ProcessingResult | None = None, *, raise_error: bool = False) -> None:
        self._result = result
        self._raise_error = raise_error
        self.calls: list[dict[str, object]] = []

    def process_event(self, **kwargs: object) -> ProcessingResult:
        self.calls.append(kwargs)
        if self._raise_error:
            raise RuntimeError("synthetic database outage")
        assert self._result is not None
        return self._result


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


def valid_message_body() -> str:
    return json.dumps(
        {
            "external_event_id": "evt-1",
            "timestamp": 1_700_000_000,
            "partition_key": "riesgo-01",
            "signature": "0" * 64,
            "payload": {
                "tipo_evento_parametrico": "sismo",
                "magnitud": "7.0",
                "umbral_activacion": "6.0",
                "suma_asegurada": "100000",
            },
        }
    )


def business_invalid_message_body() -> str:
    body = json.loads(valid_message_body())
    body["payload"]["tipo_evento_parametrico"] = "granizo_extremo"
    return json.dumps(body)


def _make_consumer(repository: FakeRepository, client: FakeSqsClient) -> ConsumerLoop:
    return ConsumerLoop(
        settings(), repository, Metrics(), logging.getLogger("test"), sqs_client=client
    )


def test_valid_new_event_is_processed_and_deleted() -> None:
    result = ProcessingResult(
        is_duplicate=False,
        siniestro_id="sin-1",
        monto_liquidado=Decimal("50000.00"),
        estado="aprobado",
        operation_id="op-1",
    )
    repository = FakeRepository(result)
    client = FakeSqsClient()
    consumer = _make_consumer(repository, client)

    consumer._handle_message({"Body": valid_message_body(), "ReceiptHandle": "rh-1"})

    assert len(repository.calls) == 1
    assert client.deleted == ["rh-1"]


def test_business_invalid_payload_is_left_for_redrive_without_calling_repository() -> None:
    repository = FakeRepository()
    client = FakeSqsClient()
    consumer = _make_consumer(repository, client)

    consumer._handle_message({"Body": business_invalid_message_body(), "ReceiptHandle": "rh-2"})

    assert repository.calls == []
    assert client.deleted == []


def test_repository_failure_leaves_the_message_for_retry() -> None:
    repository = FakeRepository(raise_error=True)
    client = FakeSqsClient()
    consumer = _make_consumer(repository, client)

    consumer._handle_message({"Body": valid_message_body(), "ReceiptHandle": "rh-3"})

    assert len(repository.calls) == 1
    assert client.deleted == []


def test_duplicate_result_is_still_deleted() -> None:
    result = ProcessingResult(
        is_duplicate=True,
        siniestro_id="sin-1",
        monto_liquidado=Decimal("50000.00"),
        estado="aprobado",
        operation_id=None,
    )
    repository = FakeRepository(result)
    client = FakeSqsClient()
    consumer = _make_consumer(repository, client)

    consumer._handle_message({"Body": valid_message_body(), "ReceiptHandle": "rh-4"})

    assert client.deleted == ["rh-4"]
