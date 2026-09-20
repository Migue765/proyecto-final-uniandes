"""Long-poll consumer for entrada-parametrica.fifo.

Business-invalid messages (valid signature, invalid business payload) are
deliberately left un-deleted so SQS's own visibility-timeout redelivery
handles them: after ``maxReceiveCount`` attempts (configured in
``infra/terraform/exp2/sqs.tf``), SQS moves the message to the DLQ on its
own. This module must never delete a message on that path and must never
retry it in a tight loop itself.
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
from .models import ReceivedParametricEvent
from .observability import Metrics
from .repository import ReclamosRepository


class ConsumerLoop(threading.Thread):
    def __init__(
        self,
        settings: Settings,
        repository: ReclamosRepository,
        metrics: Metrics,
        logger: logging.Logger,
        *,
        sqs_client: Any | None = None,
    ) -> None:
        super().__init__(daemon=True, name="reclamos-consumer")
        self._settings = settings
        self._repository = repository
        self._metrics = metrics
        self._logger = logger
        self._client = sqs_client or boto3.client(
            "sqs", region_name=settings.aws_region, config=Config(max_pool_connections=20)
        )
        self._queue_url = settings.sqs_entrada_parametrica_url
        self._stop_event = threading.Event()
        self._batch_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="reclamos-batch")

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            self.poll_once()

    def poll_once(self) -> int:
        """Receive and process one batch; returns the number of messages seen."""

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
            envelope = ReceivedParametricEvent.model_validate_json(message["Body"])
        except ValidationError:
            self._metrics.events.labels("business_invalid").inc()
            self._logger.warning(
                "event_business_invalid",
                extra={"event": "event_business_invalid"},
            )
            return

        try:
            result = self._repository.process_event(
                external_event_id=envelope.external_event_id,
                partition_key=envelope.partition_key,
                payload=envelope.payload,
            )
        except Exception:
            self._metrics.failures.labels("repository").inc()
            self._logger.error(
                "event_processing_failed",
                extra={
                    "event": "event_processing_failed",
                    "external_event_id": envelope.external_event_id,
                },
            )
            return

        outcome = "duplicate" if result.is_duplicate else "accepted"
        self._metrics.events.labels(outcome).inc()
        self._logger.info(
            outcome,
            extra={
                "event": outcome,
                "external_event_id": envelope.external_event_id,
                "operation_id": result.operation_id,
            },
        )
        self._client.delete_message(QueueUrl=self._queue_url, ReceiptHandle=receipt_handle)
