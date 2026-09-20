"""PostgreSQL and profile-service adapters."""

from __future__ import annotations

import time
from typing import Any

import httpx
from psycopg_pool import ConnectionPool
from pydantic import ValidationError

from .config import Settings
from .models import ProfileResponse, Tariff
from .observability import Metrics


class DependencyUnavailable(RuntimeError):
    """A required downstream dependency is unavailable or invalid."""


def read_bounded_response(response: httpx.Response, maximum_bytes: int) -> bytes:
    """Consume a streamed response without buffering beyond the configured cap."""

    content_encoding = response.headers.get("content-encoding", "").strip().lower()
    if content_encoding not in {"", "identity"}:
        raise DependencyUnavailable("encoded profile responses are not accepted")
    content_length = response.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as error:
            raise DependencyUnavailable("invalid response length") from error
        if declared_length < 0 or declared_length > maximum_bytes:
            raise DependencyUnavailable("profile response too large")

    body = bytearray()
    chunk_size = min(8_192, maximum_bytes + 1)
    for chunk in response.iter_raw(chunk_size=chunk_size):
        if len(body) + len(chunk) > maximum_bytes:
            raise DependencyUnavailable("profile response too large")
        body.extend(chunk)
    return bytes(body)


class TariffRepository:
    _QUERY = """
        SELECT annual_rate, fixed_fee, version
        FROM partner_rates
        WHERE partner_id = %s
    """

    def __init__(self, settings: Settings, metrics: Metrics) -> None:
        self._pool = ConnectionPool(
            conninfo=settings.database_url.get_secret_value(),
            min_size=settings.db_pool_min,
            max_size=settings.db_pool_max,
            timeout=settings.db_pool_timeout_seconds,
            open=True,
            kwargs={"autocommit": True},
        )
        self._timeout = settings.db_pool_timeout_seconds
        self._metrics = metrics

    def get_tariff(self, partner_ref: str) -> Tariff:
        started = time.perf_counter()
        outcome = "success"
        try:
            with self._pool.connection(timeout=self._timeout) as connection:
                row = connection.execute(self._QUERY, (partner_ref,)).fetchone()
            if row is None:
                raise DependencyUnavailable("tariff not configured")
            return Tariff(annual_rate=row[0], fixed_fee=row[1], version=row[2])
        except DependencyUnavailable:
            outcome = "not_found"
            raise
        except Exception as error:
            outcome = "error"
            raise DependencyUnavailable("database unavailable") from error
        finally:
            self._metrics.dependency_latency.labels("postgresql", outcome).observe(
                time.perf_counter() - started
            )

    def ping(self) -> bool:
        try:
            with self._pool.connection(timeout=self._timeout) as connection:
                return bool(connection.execute("SELECT 1").fetchone())
        except Exception:
            return False

    def close(self) -> None:
        self._pool.close()


class ProfileClient:
    _SCORE_PATH = "/internal/v1/profiles/score"
    _READY_PATH = "/health/ready"
    _MAX_RESPONSE_BYTES = 16_384

    def __init__(self, settings: Settings, metrics: Metrics) -> None:
        timeout = httpx.Timeout(
            connect=settings.http_connect_timeout_seconds,
            read=settings.http_read_timeout_seconds,
            write=settings.http_read_timeout_seconds,
            pool=settings.http_connect_timeout_seconds,
        )
        limits = httpx.Limits(
            max_connections=settings.http_pool_max_connections,
            max_keepalive_connections=settings.http_pool_max_keepalive,
        )
        self._client = httpx.Client(
            base_url=settings.profile_service_url,
            timeout=timeout,
            limits=limits,
            follow_redirects=False,
            trust_env=False,
        )
        self._metrics = metrics

    def get_score(self, *, partner_ref: str, profile_ref: str) -> ProfileResponse:
        started = time.perf_counter()
        outcome = "success"
        try:
            with self._client.stream(
                "POST",
                self._SCORE_PATH,
                json={"partner_ref": partner_ref, "profile_ref": profile_ref},
                headers={"Accept-Encoding": "identity"},
            ) as response:
                if response.status_code != 200:
                    outcome = "upstream_error"
                    raise DependencyUnavailable("profile service unavailable")
                try:
                    content = read_bounded_response(response, self._MAX_RESPONSE_BYTES)
                    return ProfileResponse.model_validate_json(content)
                except (DependencyUnavailable, ValidationError) as error:
                    outcome = "invalid_response"
                    raise DependencyUnavailable("invalid profile response") from error
        except DependencyUnavailable:
            raise
        except httpx.HTTPError as error:
            outcome = "network_error"
            raise DependencyUnavailable("profile service unavailable") from error
        finally:
            self._metrics.dependency_latency.labels("profile", outcome).observe(
                time.perf_counter() - started
            )

    def ping(self) -> bool:
        try:
            with self._client.stream("GET", self._READY_PATH) as response:
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    def close(self) -> None:
        self._client.close()


def close_dependency(dependency: Any) -> None:
    close = getattr(dependency, "close", None)
    if callable(close):
        close()
