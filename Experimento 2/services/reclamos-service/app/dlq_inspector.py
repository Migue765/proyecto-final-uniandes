"""Read-only, non-destructive inspection of both experiment 2 DLQs.

These helpers back ``GET /internal/v1/dlq/status`` and
``GET /internal/v1/dlq/messages`` in ``application.py``. Reclamos owns this
inspection surface for both DLQs (its IAM policy statement already covers
read access to both), so nobody needs a separate observability service for
this lab. Messages are peeked with ``VisibilityTimeout=0`` and are never
deleted, so inspection never affects the redrive/DLQ bookkeeping or the
reconciliation counts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_RECEIVE_BATCH_SIZE = 10


@dataclass(frozen=True)
class DlqMessage:
    message_id: str
    body: str


def approximate_count(client: Any, queue_url: str) -> int:
    response = client.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessages"]
    )
    return int(response["Attributes"]["ApproximateNumberOfMessages"])


def dlq_status(client: Any, *, entrada_dlq_url: str, pagos_dlq_url: str) -> dict[str, int]:
    return {
        "entrada_parametrica_dlq": approximate_count(client, entrada_dlq_url),
        "ordenes_pagos_dlq": approximate_count(client, pagos_dlq_url),
    }


def peek_messages(client: Any, queue_url: str, *, limit: int) -> list[DlqMessage]:
    """Non-destructively fetch up to ``limit`` messages (best-effort, not exhaustive)."""

    collected: list[DlqMessage] = []
    remaining = limit
    while remaining > 0:
        batch_size = min(_RECEIVE_BATCH_SIZE, remaining)
        response = client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=batch_size,
            VisibilityTimeout=0,
        )
        messages = response.get("Messages", [])[:remaining]
        if not messages:
            break
        collected.extend(
            DlqMessage(message_id=message["MessageId"], body=message["Body"])
            for message in messages
        )
        remaining -= len(messages)
    return collected
