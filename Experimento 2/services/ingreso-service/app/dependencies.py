"""SQS publisher for the entrada-parametrica queue."""

from __future__ import annotations

import time
import uuid
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from .config import Settings
from .models import ParametricEventEnvelope
from .observability import Metrics


class DependencyUnavailable(RuntimeError):
    """A required downstream dependency is unavailable or invalid."""


class SqsPublisher:
    """Publishes accepted envelopes to the entrada-parametrica FIFO queue.

    The queue has ``content_based_deduplication`` disabled on purpose (see
    ``infra/terraform/exp2/sqs.tf``), so every publish sets an explicit,
    random ``MessageDeduplicationId`` — never derived from
    ``external_event_id`` — so SQS never collapses the intentional test
    duplicates before they reach Reclamos.
    """

    def __init__(self, settings: Settings, metrics: Metrics) -> None:
        self._client = boto3.client(
            "sqs", region_name=settings.aws_region, config=Config(max_pool_connections=64)
        )
        self._queue_url = settings.sqs_entrada_parametrica_url
        self._metrics = metrics

    def publish(self, envelope: ParametricEventEnvelope) -> None:
        started = time.perf_counter()
        outcome = "success"
        try:
            self._client.send_message(
                QueueUrl=self._queue_url,
                MessageBody=envelope.model_dump_json(),
                MessageGroupId=envelope.partition_key,
                MessageDeduplicationId=str(uuid.uuid4()),
            )
        except (BotoCoreError, ClientError) as error:
            outcome = "error"
            raise DependencyUnavailable("entrada parametrica queue unavailable") from error
        finally:
            self._metrics.dependency_latency.labels(
                "sqs_entrada_parametrica", outcome
            ).observe(time.perf_counter() - started)

    def ping(self) -> bool:
        try:
            self._client.get_queue_attributes(
                QueueUrl=self._queue_url, AttributeNames=["QueueArn"]
            )
            return True
        except (BotoCoreError, ClientError):
            return False

    def close(self) -> None:
        self._client.close()


def close_dependency(dependency: Any) -> None:
    close = getattr(dependency, "close", None)
    if callable(close):
        close()
