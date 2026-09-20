"""Redis, PostgreSQL and fixed-destination WireMock adapters."""

from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx
import redis
from psycopg_pool import ConnectionPool
from pydantic import ValidationError

from .config import Settings
from .models import OpenFinanceData, ProfileInputs, StoredProfile
from .observability import Metrics


class DependencyUnavailable(RuntimeError):
    """A required downstream dependency is unavailable or invalid."""


def read_bounded_response(response: httpx.Response, maximum_bytes: int) -> bytes:
    """Consume a streamed response without buffering beyond the configured cap."""

    content_encoding = response.headers.get("content-encoding", "").strip().lower()
    if content_encoding not in {"", "identity"}:
        raise DependencyUnavailable("encoded Open Finance responses are not accepted")
    content_length = response.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as error:
            raise DependencyUnavailable("invalid response length") from error
        if declared_length < 0 or declared_length > maximum_bytes:
            raise DependencyUnavailable("Open Finance response too large")

    body = bytearray()
    chunk_size = min(8_192, maximum_bytes + 1)
    for chunk in response.iter_raw(chunk_size=chunk_size):
        if len(body) + len(chunk) > maximum_bytes:
            raise DependencyUnavailable("Open Finance response too large")
        body.extend(chunk)
    return bytes(body)


class ProfileRepository:
    _QUERY = """
        SELECT age, monthly_income, debt_ratio, claims_count
        FROM synthetic_profiles
        WHERE partner_id = %s AND profile_id = %s
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

    def get_profile(self, partner_ref: str, profile_ref: str) -> StoredProfile:
        started = time.perf_counter()
        outcome = "success"
        try:
            parameters = (partner_ref, profile_ref)
            with self._pool.connection(timeout=self._timeout) as connection:
                row = connection.execute(self._QUERY, parameters).fetchone()
            if row is None:
                outcome = "not_found"
                raise DependencyUnavailable("profile seed data unavailable")
            return StoredProfile(
                age=row[0],
                monthly_income=row[1],
                debt_ratio=row[2],
                claims_count=row[3],
            )
        except DependencyUnavailable:
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


class ProfileCache:
    _PREFIX = "profile:v1:"

    def __init__(self, settings: Settings, metrics: Metrics) -> None:
        pool = redis.ConnectionPool.from_url(
            settings.redis_url.get_secret_value(),
            max_connections=settings.redis_pool_max,
            socket_connect_timeout=settings.redis_connect_timeout_seconds,
            socket_timeout=settings.redis_read_timeout_seconds,
            decode_responses=True,
        )
        self._client = redis.Redis(connection_pool=pool)
        self._ttl = settings.cache_ttl_seconds
        self._jitter = settings.cache_ttl_jitter_seconds
        self._metrics = metrics

    @classmethod
    def cache_key(cls, partner_ref: str, profile_ref: str) -> str:
        digest = hashlib.sha256(
            f"{partner_ref}\x00{profile_ref}".encode("ascii")
        ).hexdigest()
        return cls._PREFIX + digest

    def get(self, partner_ref: str, profile_ref: str) -> ProfileInputs | None:
        started = time.perf_counter()
        outcome = "success"
        try:
            cached = self._client.get(self.cache_key(partner_ref, profile_ref))
            if cached is None:
                outcome = "miss"
                return None
            try:
                return ProfileInputs.model_validate_json(cached)
            except ValidationError as error:
                outcome = "invalid"
                raise DependencyUnavailable("invalid cache value") from error
        except DependencyUnavailable:
            raise
        except redis.RedisError as error:
            outcome = "error"
            raise DependencyUnavailable("cache unavailable") from error
        finally:
            self._metrics.dependency_latency.labels("redis_get", outcome).observe(
                time.perf_counter() - started
            )

    def put(
        self,
        partner_ref: str,
        profile_ref: str,
        profile: ProfileInputs,
    ) -> int:
        key = self.cache_key(partner_ref, profile_ref)
        if self._jitter:
            jitter = int(hashlib.sha256(key.encode("ascii")).hexdigest()[:8], 16) % (
                self._jitter + 1
            )
        else:
            jitter = 0
        ttl = self._ttl + jitter
        started = time.perf_counter()
        outcome = "success"
        try:
            self._client.setex(key, ttl, profile.model_dump_json())
            return ttl
        except redis.RedisError as error:
            outcome = "error"
            raise DependencyUnavailable("cache unavailable") from error
        finally:
            self._metrics.dependency_latency.labels("redis_set", outcome).observe(
                time.perf_counter() - started
            )

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except redis.RedisError:
            return False

    def close(self) -> None:
        self._client.close()


class WireMockClient:
    _PROFILE_PATH = "/open-finance/v1/profiles"
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
            base_url=settings.wiremock_url,
            timeout=timeout,
            limits=limits,
            follow_redirects=False,
            trust_env=False,
        )
        self._metrics = metrics

    def fetch(self, partner_ref: str, profile_ref: str) -> OpenFinanceData:
        started = time.perf_counter()
        outcome = "success"
        try:
            with self._client.stream(
                "POST",
                self._PROFILE_PATH,
                json={"partner_ref": partner_ref, "profile_ref": profile_ref},
                headers={"Accept-Encoding": "identity"},
            ) as response:
                if response.status_code != 200:
                    outcome = "upstream_error"
                    raise DependencyUnavailable("Open Finance mock unavailable")
                try:
                    content = read_bounded_response(response, self._MAX_RESPONSE_BYTES)
                    return OpenFinanceData.model_validate_json(content)
                except (DependencyUnavailable, ValidationError) as error:
                    outcome = "invalid_response"
                    raise DependencyUnavailable(
                        "invalid Open Finance response"
                    ) from error
        except DependencyUnavailable:
            raise
        except httpx.HTTPError as error:
            outcome = "network_error"
            raise DependencyUnavailable("Open Finance mock unavailable") from error
        finally:
            self._metrics.dependency_latency.labels("wiremock", outcome).observe(
                time.perf_counter() - started
            )

    def close(self) -> None:
        self._client.close()


def close_dependency(dependency: Any) -> None:
    close = getattr(dependency, "close", None)
    if callable(close):
        close()
