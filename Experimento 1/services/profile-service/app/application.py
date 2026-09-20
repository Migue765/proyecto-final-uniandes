"""Flask application factory for cache-aside profile scoring."""

from __future__ import annotations

import atexit
import logging
import time
import uuid
from typing import Any

from flask import Flask, Response, g, jsonify, request
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from .computation import calculate_risk_score
from .config import Settings
from .dependencies import (
    DependencyUnavailable,
    ProfileCache,
    ProfileRepository,
    WireMockClient,
    close_dependency,
)
from .models import ProfileInputs, ProfileResult, ProfileScoreRequest
from .observability import Metrics, configure_logging


def _parse_request() -> ProfileScoreRequest:
    if not request.is_json:
        raise ValueError("JSON body required")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return ProfileScoreRequest.model_validate(payload)


def create_app(
    settings: Settings | None = None,
    *,
    repository: Any | None = None,
    cache: Any | None = None,
    wiremock_client: Any | None = None,
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
    profile_repository = repository or ProfileRepository(runtime, service_metrics)
    profile_cache = cache or ProfileCache(runtime, service_metrics)
    open_finance = wiremock_client or WireMockClient(runtime, service_metrics)
    app.extensions["settings"] = runtime
    app.extensions["metrics"] = service_metrics
    app.extensions["profile_repository"] = profile_repository
    app.extensions["profile_cache"] = profile_cache
    app.extensions["wiremock_client"] = open_finance

    if repository is None:
        atexit.register(close_dependency, profile_repository)
    if cache is None:
        atexit.register(close_dependency, profile_cache)
    if wiremock_client is None:
        atexit.register(close_dependency, open_finance)

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

    @app.post("/internal/v1/profiles/score")
    def score_profile() -> tuple[Response, int]:
        request_id = str(uuid.uuid4())
        try:
            score_request = _parse_request()
        except (ValidationError, ValueError):
            g.partner_metric = "invalid"
            service_metrics.failures.labels("validation").inc()
            return jsonify({"error": "invalid_request"}), 400

        g.partner_metric = score_request.partner_ref
        cached = profile_cache.get(score_request.partner_ref, score_request.profile_ref)
        if cached is None:
            cache_status = "miss"
            stored = profile_repository.get_profile(
                score_request.partner_ref, score_request.profile_ref
            )
            finance = open_finance.fetch(
                score_request.partner_ref, score_request.profile_ref
            )
            inputs = ProfileInputs(
                age=stored.age,
                monthly_income=stored.monthly_income,
                debt_ratio=stored.debt_ratio,
                claims_count=stored.claims_count,
                account_age_months=finance.account_age_months,
                inflow_stability=finance.inflow_stability,
                delinquency_count=finance.delinquency_count,
            )
            profile_cache.put(
                score_request.partner_ref, score_request.profile_ref, inputs
            )
        else:
            cache_status = "hit"
            inputs = cached

        service_metrics.cache_operations.labels(
            score_request.partner_ref, cache_status
        ).inc()
        risk_score, risk_band = calculate_risk_score(
            profile=inputs,
            partner_ref=score_request.partner_ref,
            profile_ref=score_request.profile_ref,
            iterations=runtime.profile_cpu_iterations,
        )
        result = ProfileResult(
            partner_ref=score_request.partner_ref,
            profile_ref=score_request.profile_ref,
            risk_score=risk_score,
            risk_band=risk_band,
            cache_status=cache_status,
            profile_version="synthetic-v1",
        )
        logger.info(
            "profile_scored",
            extra={
                "event": "profile_scored",
                "request_id": request_id,
                "partner_ref": score_request.partner_ref,
                "cache_status": cache_status,
            },
        )
        return jsonify(result.model_dump()), 200

    @app.get("/health/live")
    def health_live() -> tuple[Response, int]:
        return jsonify({"status": "alive"}), 200

    @app.get("/health/ready")
    def health_ready() -> tuple[Response, int]:
        postgres_ok = bool(profile_repository.ping())
        redis_ok = bool(profile_cache.ping())
        ready = postgres_ok and redis_ok
        status = 200 if ready else 503
        return (
            jsonify(
                {
                    "status": "ready" if ready else "not_ready",
                    "checks": {"postgresql": postgres_ok, "redis": redis_ok},
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
