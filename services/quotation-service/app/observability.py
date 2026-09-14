"""Bounded-cardinality Prometheus metrics and JSON logging."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest


class JsonFormatter(logging.Formatter):
    _optional_fields = (
        "event",
        "request_id",
        "partner_ref",
        "status_code",
        "duration_ms",
        "dependency",
        "error_id",
    )

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self._service_name,
            "message": record.getMessage(),
        }
        for field in self._optional_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def configure_logging(service_name: str, level: str) -> logging.Logger:
    logger = logging.getLogger(service_name)
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service_name))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


class Metrics:
    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self.registry = registry or CollectorRegistry()
        self.requests = Counter(
            "solventa_http_requests_total",
            "HTTP requests handled by the quotation service.",
            ("route", "method", "status", "partner"),
            registry=self.registry,
        )
        self.request_latency = Histogram(
            "solventa_http_request_duration_seconds",
            "HTTP request latency by synthetic partner.",
            ("route", "method", "partner"),
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2),
            registry=self.registry,
        )
        self.dependency_latency = Histogram(
            "solventa_dependency_duration_seconds",
            "Dependency latency from the quotation service.",
            ("dependency", "outcome"),
            buckets=(0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1),
            registry=self.registry,
        )
        self.failures = Counter(
            "solventa_failures_total",
            "Quotation service failures by dependency or processing stage.",
            ("stage",),
            registry=self.registry,
        )

    def render(self) -> bytes:
        return generate_latest(self.registry)
