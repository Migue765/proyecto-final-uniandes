"""Flask application factory for the Pagos service."""

from __future__ import annotations

import atexit
import logging
import time
import uuid
from typing import Any

from flask import Flask, Response, g, jsonify, request
from werkzeug.exceptions import HTTPException

from .config import Settings
from .consumer import ConsumerLoop
from .observability import Metrics, configure_logging
from .repository import PagosRepository


def create_app(
    settings: Settings | None = None,
    *,
    repository: Any | None = None,
    consumer: Any | None = None,
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

    pagos_repository = repository or PagosRepository(runtime, service_metrics)

    consumer_loop = consumer
    if consumer_loop is None and runtime.enable_consumer_thread:
        consumer_loop = ConsumerLoop(runtime, pagos_repository, service_metrics, logger)
    if consumer_loop is not None and not getattr(consumer_loop, "is_alive", lambda: True)():
        consumer_loop.start()

    app.extensions["settings"] = runtime
    app.extensions["metrics"] = service_metrics
    app.extensions["repository"] = pagos_repository
    app.extensions["consumer"] = consumer_loop

    if repository is None:
        atexit.register(pagos_repository.close)
    stop = getattr(consumer_loop, "stop", None)
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
        db_ok = bool(pagos_repository.ping())
        status = 200 if db_ok else 503
        return (
            jsonify({"status": "ready" if db_ok else "not_ready", "checks": {"postgresql": db_ok}}),
            status,
        )

    @app.get("/metrics")
    def prometheus_metrics() -> Response:
        return Response(service_metrics.render(), mimetype="text/plain; version=0.0.4")

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
