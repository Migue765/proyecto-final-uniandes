"""Flask application factory for the Reclamos service."""

from __future__ import annotations

import atexit
import logging
import time
import uuid
from dataclasses import asdict
from typing import Any

import boto3
from flask import Flask, Response, g, jsonify, request
from werkzeug.exceptions import HTTPException

from .config import Settings
from .consumer import ConsumerLoop
from .dlq_inspector import dlq_status, peek_messages
from .observability import Metrics, configure_logging
from .outbox_publisher import OutboxPublisher
from .repository import ReclamosRepository

_QUEUE_ALIASES = {"entrada", "pagos"}


def create_app(
    settings: Settings | None = None,
    *,
    repository: Any | None = None,
    consumer: Any | None = None,
    outbox_publisher: Any | None = None,
    dlq_client: Any | None = None,
    metrics: Metrics | None = None,
) -> Flask:
    runtime = settings or Settings.from_env()
    service_metrics = metrics or Metrics()
    logger = configure_logging(runtime.service_name, runtime.log_level)

    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=runtime.max_request_bytes,
        PROPAGATE_EXCEPTIONS=False,
        JSON_SORT_KEYS=False,
    )

    reclamos_repository = repository or ReclamosRepository(runtime, service_metrics)
    dlq_inspection_client = dlq_client or boto3.client("sqs", region_name=runtime.aws_region)

    consumer_loop = consumer
    if consumer_loop is None and runtime.enable_consumer_thread:
        consumer_loop = ConsumerLoop(runtime, reclamos_repository, service_metrics, logger)
    if consumer_loop is not None and not getattr(consumer_loop, "is_alive", lambda: True)():
        consumer_loop.start()

    publisher_loop = outbox_publisher
    if publisher_loop is None and runtime.enable_outbox_publisher_thread:
        publisher_loop = OutboxPublisher(runtime, reclamos_repository, service_metrics, logger)
    if publisher_loop is not None and not getattr(publisher_loop, "is_alive", lambda: True)():
        publisher_loop.start()

    app.extensions["settings"] = runtime
    app.extensions["metrics"] = service_metrics
    app.extensions["repository"] = reclamos_repository
    app.extensions["consumer"] = consumer_loop
    app.extensions["outbox_publisher"] = publisher_loop

    if repository is None:
        atexit.register(reclamos_repository.close)
    for background in (consumer_loop, publisher_loop):
        stop = getattr(background, "stop", None)
        if callable(stop):
            atexit.register(stop)

    @app.before_request
    def begin_request() -> None:
        g.request_started = time.perf_counter()
        g.metric_route = request.url_rule.rule if request.url_rule else "unmatched"

    @app.after_request
    def record_request(response: Response) -> Response:
        duration = time.perf_counter() - g.get("request_started", time.perf_counter())
        route = g.get("metric_route", "unmatched")
        service_metrics.requests.labels(route, request.method, str(response.status_code)).inc()
        service_metrics.request_latency.labels(route, request.method).observe(duration)
        return response

    @app.get("/health/live")
    def health_live() -> tuple[Response, int]:
        return jsonify({"status": "alive"}), 200

    @app.get("/health/ready")
    def health_ready() -> tuple[Response, int]:
        db_ok = bool(reclamos_repository.ping())
        ready = db_ok
        status = 200 if ready else 503
        return (
            jsonify({"status": "ready" if ready else "not_ready", "checks": {"postgresql": db_ok}}),
            status,
        )

    @app.get("/metrics")
    def prometheus_metrics() -> Response:
        return Response(service_metrics.render(), mimetype="text/plain; version=0.0.4")

    @app.get("/internal/v1/dlq/status")
    def dlq_status_endpoint() -> tuple[Response, int]:
        counts = dlq_status(
            dlq_inspection_client,
            entrada_dlq_url=runtime.sqs_entrada_parametrica_dlq_url,
            pagos_dlq_url=runtime.sqs_ordenes_pagos_dlq_url,
        )
        return jsonify(counts), 200

    @app.get("/internal/v1/dlq/messages")
    def dlq_messages_endpoint() -> tuple[Response, int]:
        queue = request.args.get("queue", "")
        if queue not in _QUEUE_ALIASES:
            return jsonify({"error": "invalid_queue", "allowed": sorted(_QUEUE_ALIASES)}), 400

        queue_url = (
            runtime.sqs_entrada_parametrica_dlq_url
            if queue == "entrada"
            else runtime.sqs_ordenes_pagos_dlq_url
        )
        try:
            limit = int(request.args.get("limit", "10"))
        except ValueError:
            return jsonify({"error": "invalid_limit"}), 400
        bounded_limit = max(1, min(limit, runtime.dlq_peek_max_messages))

        messages = peek_messages(dlq_inspection_client, queue_url, limit=bounded_limit)
        return jsonify({"queue": queue, "messages": [asdict(message) for message in messages]}), 200

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception) -> tuple[Response, int]:
        if isinstance(error, HTTPException):
            return jsonify({"error": "http_error"}), error.code or 500
        service_metrics.failures.labels("unexpected").inc()
        error_id = str(uuid.uuid4())
        logger.error(
            "unexpected_error",
            extra={"event": "unexpected_error", "error_id": error_id},
        )
        return jsonify({"error": "internal_error", "error_id": error_id}), 500

    logging.getLogger("werkzeug").disabled = True
    return app
