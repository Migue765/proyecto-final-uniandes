"""Flask application factory for the Adaptador de Ingreso."""

from __future__ import annotations

import atexit
import logging
import time
import uuid
from typing import Any

from flask import Flask, Response, g, jsonify, request
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from .config import Settings
from .dependencies import DependencyUnavailable, SqsPublisher, close_dependency
from .models import ParametricEventEnvelope
from .observability import Metrics, configure_logging
from .security import SecretProvider, SecretUnavailable, verify_signature, within_signature_skew


def _parse_envelope() -> ParametricEventEnvelope:
    if not request.is_json:
        raise ValueError("unsupported media type")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return ParametricEventEnvelope.model_validate(payload)


def create_app(
    settings: Settings | None = None,
    *,
    publisher: Any | None = None,
    secret_provider: Any | None = None,
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
    sqs_publisher = publisher or SqsPublisher(runtime, service_metrics)
    secrets = secret_provider or SecretProvider(runtime)
    app.extensions["settings"] = runtime
    app.extensions["metrics"] = service_metrics
    app.extensions["sqs_publisher"] = sqs_publisher
    app.extensions["secret_provider"] = secrets

    if publisher is None:
        atexit.register(close_dependency, sqs_publisher)
    if secret_provider is None:
        atexit.register(close_dependency, secrets)

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

    @app.post("/parametricos/v1/eventos")
    def receive_event() -> tuple[Response, int]:
        request_id = str(uuid.uuid4())
        try:
            envelope = _parse_envelope()
        except (ValidationError, ValueError):
            service_metrics.failures.labels("validation").inc()
            service_metrics.events.labels("invalid_schema").inc()
            return jsonify({"error": "invalid_request"}), 400

        try:
            secret = secrets.get_secret()
        except SecretUnavailable as error:
            raise DependencyUnavailable("hmac secret unavailable") from error

        if not verify_signature(secret, envelope):
            service_metrics.failures.labels("signature").inc()
            service_metrics.events.labels("invalid_signature").inc()
            logger.warning(
                "signature_rejected",
                extra={"event": "signature_rejected", "request_id": request_id},
            )
            return jsonify({"error": "invalid_signature"}), 400

        if not within_signature_skew(envelope.timestamp, runtime.signature_max_skew_seconds):
            service_metrics.failures.labels("stale_timestamp").inc()
            service_metrics.events.labels("stale_timestamp").inc()
            return jsonify({"error": "stale_timestamp"}), 400

        sqs_publisher.publish(envelope)
        service_metrics.events.labels("accepted").inc()
        logger.info(
            "event_accepted",
            extra={
                "event": "event_accepted",
                "request_id": request_id,
                "external_event_id": envelope.external_event_id,
            },
        )
        return jsonify({"external_event_id": envelope.external_event_id, "status": "accepted"}), 202

    @app.get("/health/live")
    def health_live() -> tuple[Response, int]:
        return jsonify({"status": "alive"}), 200

    @app.get("/health/ready")
    def health_ready() -> tuple[Response, int]:
        sqs_ok = bool(sqs_publisher.ping())
        secret_ok = bool(secrets.ping())
        ready = sqs_ok and secret_ok
        status = 200 if ready else 503
        return (
            jsonify(
                {
                    "status": "ready" if ready else "not_ready",
                    "checks": {"sqs": sqs_ok, "hmac_secret": secret_ok},
                }
            ),
            status,
        )

    @app.get("/metrics")
    def prometheus_metrics() -> Response:
        return Response(service_metrics.render(), mimetype="text/plain; version=0.0.4")

    @app.errorhandler(DependencyUnavailable)
    def handle_dependency_error(error: DependencyUnavailable) -> tuple[Response, int]:
        del error
        service_metrics.failures.labels("dependency").inc()
        error_id = str(uuid.uuid4())
        logger.warning(
            "dependency_unavailable",
            extra={"event": "dependency_unavailable", "error_id": error_id},
        )
        return jsonify({"error": "service_unavailable", "error_id": error_id}), 503

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(error: RequestEntityTooLarge) -> tuple[Response, int]:
        del error
        service_metrics.failures.labels("validation").inc()
        return jsonify({"error": "request_too_large"}), 413

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
