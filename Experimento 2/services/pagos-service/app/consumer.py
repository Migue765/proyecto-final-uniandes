"""Long-poll consumer for ordenes-pagos.fifo.

Pagos is the terminal service in the pipeline: it has no further queue to
publish to, so a successfully processed message (new or duplicate) is simply
deleted. A malformed message (fails ``ReceivedPaymentOrder`` validation) is
left un-deleted so SQS's own redrive handles it, same policy as
reclamos-service's consumer for business-invalid events.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import boto3
from botocore.config import Config
from pydantic import ValidationError

from .config import Settings
from .models import ReceivedPaymentOrder
from .observability import Metrics
from .repository import PagosRepository


class ConsumerLoop(threading.Thread):
    def __init__(
        self,
        settings: Settings,
        repository: PagosRepository,
        metrics: Metrics,
        logger: logging.Logger,
        *,
        sqs_client: Any | None = None,
    ) -> None:
        super().__init__(daemon=True, name="pagos-consumer")
        self._settings = settings
        self._repository = repository
        self._metrics = metrics
        self._logger = logger
        self._client = sqs_client or boto3.client(
            "sqs", region_name=settings.aws_region, config=Config(max_pool_connections=20)
        )
        self._queue_url = settings.sqs_ordenes_pagos_url
        self._stop_event = threading.Event()
        self._batch_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="pagos-batch")

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            self.poll_once()

    def poll_once(self) -> int:
        response = self._client.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=self._settings.sqs_wait_time_seconds,
            VisibilityTimeout=self._settings.sqs_visibility_timeout_seconds,
        )
        messages = response.get("Messages", [])
        futures = [self._batch_pool.submit(self._handle_message, message) for message in messages]
        for future in futures:
            future.result()
        return len(messages)

    def _handle_message(self, message: dict[str, Any]) -> None:
        receipt_handle = message["ReceiptHandle"]
        try:
            order = ReceivedPaymentOrder.model_validate_json(message["Body"])
        except ValidationError:
            self._metrics.orders.labels("business_invalid").inc()
            self._logger.warning(
                "order_business_invalid", extra={"event": "order_business_invalid"}
            )
            return

        try:
            result = self._repository.process_order(
                operation_id=order.operation_id,
                siniestro_id=order.siniestro_id,
                monto=order.monto,
            )
        except Exception:
            self._metrics.failures.labels("repository").inc()
            self._logger.error(
                "order_processing_failed",
                extra={"event": "order_processing_failed", "operation_id": order.operation_id},
            )
            return

        outcome = "duplicate" if result.is_duplicate else "accepted"
        self._metrics.orders.labels(outcome).inc()
        self._logger.info(
            outcome,
            extra={"event": outcome, "operation_id": order.operation_id},
        )
        self._client.delete_message(QueueUrl=self._queue_url, ReceiptHandle=receipt_handle)
