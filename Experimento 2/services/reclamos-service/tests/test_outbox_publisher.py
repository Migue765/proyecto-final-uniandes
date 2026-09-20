import logging
from decimal import Decimal

from app.config import Settings
from app.observability import Metrics
from app.outbox_publisher import OutboxPublisher
from app.repository import OutboxRow


class FakeSqsClient:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    def send_message(self, **kwargs: object) -> None:
        self.sent.append(kwargs)


class RecordingRepository:
    def __init__(self, rows: list[OutboxRow]) -> None:
        self._rows = rows
        self.marked_published: list[int] = []
        self.calls_order: list[str] = []

    def fetch_unpublished_outbox_rows(self, *, limit: int) -> list[OutboxRow]:
        del limit
        self.calls_order.append("fetch")
        return self._rows

    def mark_outbox_published(self, row_id: int) -> None:
        self.calls_order.append(f"mark:{row_id}")
        self.marked_published.append(row_id)


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


def test_pending_rows_are_published_then_marked_in_order() -> None:
    rows = [
        OutboxRow(
            id=1,
            operation_id="op-1",
            siniestro_id="sin-1",
            monto=Decimal("50000.00"),
            partition_key="riesgo-01",
        )
    ]
    repository = RecordingRepository(rows)
    client = FakeSqsClient()
    publisher = OutboxPublisher(
        settings(), repository, Metrics(), logging.getLogger("test"), sqs_client=client
    )

    published_count = publisher.publish_pending()

    assert published_count == 1
    assert len(client.sent) == 1
    assert client.sent[0]["MessageGroupId"] == "riesgo-01"
    assert "op-1" in client.sent[0]["MessageBody"]
    # Publish must happen before marking published (never the reverse).
    assert repository.calls_order == ["fetch", "mark:1"]


def test_no_pending_rows_sends_nothing() -> None:
    repository = RecordingRepository([])
    client = FakeSqsClient()
    publisher = OutboxPublisher(
        settings(), repository, Metrics(), logging.getLogger("test"), sqs_client=client
    )

    assert publisher.publish_pending() == 0
    assert client.sent == []


def test_each_publish_uses_a_distinct_deduplication_id() -> None:
    rows = [
        OutboxRow(
            id=index,
            operation_id=f"op-{index}",
            siniestro_id=f"sin-{index}",
            monto=Decimal("1.00"),
            partition_key="riesgo-01",
        )
        for index in (1, 2)
    ]
    repository = RecordingRepository(rows)
    client = FakeSqsClient()
    publisher = OutboxPublisher(
        settings(), repository, Metrics(), logging.getLogger("test"), sqs_client=client
    )

    publisher.publish_pending()

    dedup_ids = [message["MessageDeduplicationId"] for message in client.sent]
    assert len(set(dedup_ids)) == 2
