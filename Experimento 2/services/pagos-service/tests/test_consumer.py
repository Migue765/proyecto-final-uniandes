import json
import logging
from decimal import Decimal

from app.config import Settings
from app.consumer import ConsumerLoop
from app.models import PaymentResult
from app.observability import Metrics


class FakeSqsClient:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_message(self, *, QueueUrl: str, ReceiptHandle: str) -> None:
        del QueueUrl
        self.deleted.append(ReceiptHandle)


class FakeRepository:
    def __init__(self, result: PaymentResult | None = None, *, raise_error: bool = False) -> None:
        self._result = result
        self._raise_error = raise_error
        self.calls: list[dict[str, object]] = []

    def process_order(self, **kwargs: object) -> PaymentResult:
        self.calls.append(kwargs)
        if self._raise_error:
            raise RuntimeError("synthetic database outage")
        assert self._result is not None
        return self._result


def settings() -> Settings:
    return Settings(
        database_url="postgresql://runtime:test-password@placeholder.invalid/pagos",
        sqs_ordenes_pagos_url=(
            "https://sqs.us-east-1.amazonaws.com/969325258550/solventa-exp2-ordenes-pagos.fifo"
        ),
    )


def valid_message_body() -> str:
    return json.dumps({"operation_id": "op-1", "siniestro_id": "sin-1", "monto": "50000.00"})


def invalid_message_body() -> str:
    return json.dumps({"operation_id": "op-1", "siniestro_id": "sin-1", "monto": "-1"})


def _make_consumer(repository: FakeRepository, client: FakeSqsClient) -> ConsumerLoop:
    return ConsumerLoop(
        settings(), repository, Metrics(), logging.getLogger("test"), sqs_client=client
    )


def test_valid_order_is_processed_and_deleted() -> None:
    result = PaymentResult(is_duplicate=False, orden_id="ord-1", monto=Decimal("50000.00"), estado="confirmado")
    repository = FakeRepository(result)
    client = FakeSqsClient()
    consumer = _make_consumer(repository, client)

    consumer._handle_message({"Body": valid_message_body(), "ReceiptHandle": "rh-1"})

    assert len(repository.calls) == 1
    assert client.deleted == ["rh-1"]


def test_invalid_order_is_left_for_redrive() -> None:
    repository = FakeRepository()
    client = FakeSqsClient()
    consumer = _make_consumer(repository, client)

    consumer._handle_message({"Body": invalid_message_body(), "ReceiptHandle": "rh-2"})

    assert repository.calls == []
    assert client.deleted == []


def test_repository_failure_leaves_the_message_for_retry() -> None:
    repository = FakeRepository(raise_error=True)
    client = FakeSqsClient()
    consumer = _make_consumer(repository, client)

    consumer._handle_message({"Body": valid_message_body(), "ReceiptHandle": "rh-3"})

    assert client.deleted == []
