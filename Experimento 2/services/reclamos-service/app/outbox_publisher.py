"""Transactional Outbox publisher: drains outbox_ordenes_pagos into SQS.

Rows are written to ``outbox_ordenes_pagos`` inside the same database
transaction as the siniestro they describe (see ``repository.process_event``),
so a settlement is never lost even if the process crashes before publishing.
This loop only ever reads already-committed rows and publishes them; it never
publishes before the write, avoiding the classic dual-write inconsistency.
"""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import boto3
from botocore.config import Config

from .config import Settings
from .observability import Metrics
from .repository import OutboxRow, ReclamosRepository


class OutboxPublisher(threading.Thread):
    def __init__(
        self,
        settings: Settings,
        repository: ReclamosRepository,
        metrics: Metrics,
        logger: logging.Logger,
        *,
        sqs_client: Any | None = None,
    ) -> None:
        super().__init__(daemon=True, name="reclamos-outbox-publisher")
        self._settings = settings
        self._repository = repository
        self._metrics = metrics
        self._logger = logger
        self._client = sqs_client or boto3.client(
            "sqs", region_name=settings.aws_region, config=Config(max_pool_connections=20)
        )
        self._queue_url = settings.sqs_ordenes_pagos_url
        self._stop_event = threading.Event()
        self._publish_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="outbox-batch")

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            self.publish_pending()
            self._stop_event.wait(self._settings.outbox_poll_interval_seconds)

    def publish_pending(self) -> int:
        rows = self._repository.fetch_unpublished_outbox_rows(
            limit=self._settings.outbox_batch_size
        )
        futures = [self._publish_pool.submit(self._publish_one, row) for row in rows]
        for future in futures:
            future.result()
        return len(rows)

    def _publish_one(self, row: OutboxRow) -> None:
        self._client.send_message(
            QueueUrl=self._queue_url,
            MessageBody=(
                '{"operation_id":"%s","siniestro_id":"%s","monto":"%s"}'
                % (row.operation_id, row.siniestro_id, row.monto)
            ),
            MessageGroupId=row.partition_key,
            MessageDeduplicationId=str(uuid.uuid4()),
        )
        self._repository.mark_outbox_published(row.id)
        self._metrics.outbox_published.inc()
        self._logger.info(
            "outbox_row_published",
            extra={"event": "outbox_row_published", "operation_id": row.operation_id},
        )
