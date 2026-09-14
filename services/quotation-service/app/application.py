"""Flask application factory for the quotation path."""

from __future__ import annotations

import atexit
import logging
import time
import uuid
from typing import Any

from flask import Flask, Response, g, jsonify, request
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from .computation import calculate_monthly_premium
from .config import Settings
from .dependencies import (
    DependencyUnavailable,
    ProfileClient,
    TariffRepository,
    close_dependency,
)
from .models import QuoteRequest, QuoteResult
from .observability import Metrics, configure_logging


def _parse_quote_request() -> QuoteRequest:
    raw_body = request.get_data(cache=True, parse_form_data=False)
    if not raw_body:
        return QuoteRequest()
    if not request.is_json:
        raise ValueError("unsupported media type")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return QuoteRequest.model_validate(payload)


def create_app(
    settings: Settings | None = None,
    *,
    repository: Any | None = None,
    profile_client: Any | None = None,
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
    tariff_repository = repository or TariffRepository(runtime, service_metrics)
    downstream = profile_client or ProfileClient(runtime, service_metrics)
    app.extensions["settings"] = runtime
    app.extensions["metrics"] = service_metrics
    app.extensions["tariff_repository"] = tariff_repository
    app.extensions["profile_client"] = downstream

    if repository is None:
        atexit.register(close_dependency, tariff_repository)
    if profile_client is None:
        atexit.register(close_dependency, downstream)

    @app.before_request
    def begin_request() -> None:
        g.request_started = time.perf_counter()
        g.partner_metric = "unattributed"
        g.metric_route = request.url_rule.rule if request.url_rule else "unmatched"

    @app.after_request
    def record_request(response: Response) -> Response:
        duration = time.perf_counter() - g.get("request_started", time.perf_counter())
        partner = g.get("partner_metric", "unattributed")
        route = g.get("metric_route", "unmatched")
        service_metrics.requests.labels(
            route, request.method, str(response.status_code), partner
        ).inc()
        service_metrics.request_latency.labels(route, request.method, partner).observe(
            duration
        )
        return response

    @app.post("/api/v1/cotizaciones")
    def create_quotation() -> tuple[Response, int]:
        request_id = str(uuid.uuid4())
        try:
            quote_request = _parse_quote_request()
        except (ValidationError, ValueError):
            g.partner_metric = "invalid"
            service_metrics.failures.labels("validation").inc()
            return jsonify({"error": "invalid_request"}), 400

        g.partner_metric = quote_request.partner_ref
        profile = downstream.get_score(
            partner_ref=quote_request.partner_ref,
            profile_ref=quote_request.profile_ref,
        )
        if (
            profile.partner_ref != quote_request.partner_ref
            or profile.profile_ref != quote_request.profile_ref
        ):
            raise DependencyUnavailable("profile identity mismatch")

        tariff = tariff_repository.get_tariff(quote_request.partner_ref)
        premium, checksum = calculate_monthly_premium(
            quote=quote_request,
            tariff=tariff,
            risk_score=profile.risk_score,
            partner_ref=quote_request.partner_ref,
            profile_ref=quote_request.profile_ref,
            iterations=runtime.quote_cpu_iterations,
        )
        result = QuoteResult(
            quotation_id=str(uuid.uuid4()),
            request_id=request_id,
            partner_ref=quote_request.partner_ref,
            profile_ref=quote_request.profile_ref,
            monthly_premium=format(premium, "f"),
            risk_score=profile.risk_score,
            tariff_version=tariff.version,
            calculation_checksum=checksum,
        )
        logger.info(
            "quotation_completed",
            extra={
                "event": "quotation_completed",
                "request_id": request_id,
                "partner_ref": quote_request.partner_ref,
            },
        )
        return jsonify(result.model_dump()), 200

    @app.get("/health/live")
    def health_live() -> tuple[Response, int]:
        return jsonify({"status": "alive"}), 200

    @app.get("/health/ready")
    def health_ready() -> tuple[Response, int]:
        postgres_ok = bool(tariff_repository.ping())
        profile_ok = bool(downstream.ping())
        ready = postgres_ok and profile_ok
        status = 200 if ready else 503
        return (
            jsonify(
                {
                    "status": "ready" if ready else "not_ready",
                    "checks": {"postgresql": postgres_ok, "profile": profile_ok},
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

    # Avoid Flask's default request log formatting; application logs are JSON only.
    logging.getLogger("werkzeug").disabled = True
    return app
