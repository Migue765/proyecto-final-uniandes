"""Environment-backed configuration for the profile service."""

from __future__ import annotations

import os
from urllib.parse import parse_qs, urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
)


_BLOCKED_METADATA_HOSTS = {
    "169.254.169.254",
    "fd00:ec2::254",
    "metadata.google.internal",
}
_RDS_CA_PATH = "/etc/ssl/certs/aws-rds-global-bundle.pem"


def _validate_database_url(value: SecretStr) -> SecretStr:
    parsed = urlparse(value.get_secret_value())
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("database URL must use PostgreSQL")
    if not parsed.hostname or parsed.hostname.lower() in _BLOCKED_METADATA_HOSTS:
        raise ValueError("database URL host is not allowed")
    if not parsed.username or parsed.password is None or parsed.fragment:
        raise ValueError("database URL must contain credentials and no fragment")
    if not parsed.path or parsed.path == "/":
        raise ValueError("database URL must name a database")

    try:
        parameters = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as error:
        raise ValueError("database URL query is invalid") from error
    if parsed.hostname.lower().endswith(".rds.amazonaws.com"):
        if parameters.get("sslmode") != ["verify-full"]:
            raise ValueError("Amazon RDS requires sslmode=verify-full")
        if parameters.get("sslrootcert") != [_RDS_CA_PATH]:
            raise ValueError("Amazon RDS requires the bundled root certificate")
    return value


def _validate_base_url(value: str, label: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"{label} must use http or https")
    if not parsed.hostname or parsed.hostname.lower() in _BLOCKED_METADATA_HOSTS:
        raise ValueError(f"{label} host is not allowed")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"{label} must be a credential-free base URL")
    if parsed.path not in {"", "/"}:
        raise ValueError(f"{label} must not include a path")
    return value.rstrip("/")


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    service_name: str = "profile-service"
    database_url: SecretStr = Field(min_length=1)
    redis_url: SecretStr = Field(min_length=1)
    wiremock_url: str = Field(min_length=1, max_length=512)
    db_pool_min: int = Field(default=1, ge=1, le=50)
    db_pool_max: int = Field(default=10, ge=1, le=200)
    db_pool_timeout_seconds: float = Field(default=1.0, gt=0, le=30)
    redis_pool_max: int = Field(default=100, ge=1, le=2_000)
    redis_connect_timeout_seconds: float = Field(default=0.2, gt=0, le=10)
    redis_read_timeout_seconds: float = Field(default=0.5, gt=0, le=30)
    cache_ttl_seconds: int = Field(default=900, ge=60, le=86_400)
    cache_ttl_jitter_seconds: int = Field(default=60, ge=0, le=3_600)
    http_connect_timeout_seconds: float = Field(default=0.25, gt=0, le=10)
    http_read_timeout_seconds: float = Field(default=0.75, gt=0, le=30)
    http_pool_max_connections: int = Field(default=100, ge=1, le=1_000)
    http_pool_max_keepalive: int = Field(default=50, ge=1, le=1_000)
    profile_cpu_iterations: int = Field(default=800, ge=1, le=1_000_000)
    max_request_bytes: int = Field(default=4_096, ge=128, le=65_536)
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def validate_database_connection(cls, value: SecretStr) -> SecretStr:
        return _validate_database_url(value)

    @field_validator("wiremock_url")
    @classmethod
    def validate_wiremock_url(cls, value: str) -> str:
        return _validate_base_url(value, "WireMock URL")

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: SecretStr) -> SecretStr:
        parsed = urlparse(value.get_secret_value())
        if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
            raise ValueError("Redis URL must use redis or rediss and include a host")
        if parsed.hostname.lower() in _BLOCKED_METADATA_HOSTS:
            raise ValueError("Redis URL host is not allowed")
        if parsed.password in {None, ""}:
            raise ValueError("Redis URL must contain a password")
        if parsed.query or parsed.fragment:
            raise ValueError("Redis URL must not contain query or fragment data")
        if parsed.hostname.lower().endswith(".cache.amazonaws.com"):
            if parsed.scheme != "rediss":
                raise ValueError("Amazon ElastiCache requires TLS")
            if parsed.path != "/0":
                raise ValueError("Amazon ElastiCache URL must select database 0")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("unsupported log level")
        return normalized

    @field_validator("db_pool_max")
    @classmethod
    def validate_pool_bounds(cls, value: int, info) -> int:
        minimum = info.data.get("db_pool_min", 1)
        if value < minimum:
            raise ValueError("db_pool_max must be greater than or equal to db_pool_min")
        return value

    @field_validator("http_pool_max_keepalive")
    @classmethod
    def validate_http_pool_bounds(cls, value: int, info) -> int:
        maximum = info.data.get("http_pool_max_connections", 100)
        if value > maximum:
            raise ValueError(
                "HTTP keepalive connections cannot exceed total connections"
            )
        return value

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            return cls(
                database_url=os.environ.get("DATABASE_URL", ""),
                redis_url=os.environ.get("REDIS_URL", ""),
                wiremock_url=os.environ.get("WIREMOCK_URL", ""),
                db_pool_min=os.environ.get("DB_POOL_MIN", "1"),
                db_pool_max=os.environ.get("DB_POOL_MAX", "10"),
                db_pool_timeout_seconds=os.environ.get(
                    "DB_POOL_TIMEOUT_SECONDS", "1.0"
                ),
                redis_pool_max=os.environ.get("REDIS_POOL_MAX", "100"),
                redis_connect_timeout_seconds=os.environ.get(
                    "REDIS_CONNECT_TIMEOUT_SECONDS", "0.2"
                ),
                redis_read_timeout_seconds=os.environ.get(
                    "REDIS_READ_TIMEOUT_SECONDS", "0.5"
                ),
                cache_ttl_seconds=os.environ.get("CACHE_TTL_SECONDS", "900"),
                cache_ttl_jitter_seconds=os.environ.get(
                    "CACHE_TTL_JITTER_SECONDS", "60"
                ),
                http_connect_timeout_seconds=os.environ.get(
                    "HTTP_CONNECT_TIMEOUT_SECONDS", "0.25"
                ),
                http_read_timeout_seconds=os.environ.get(
                    "HTTP_READ_TIMEOUT_SECONDS", "0.75"
                ),
                http_pool_max_connections=os.environ.get(
                    "HTTP_POOL_MAX_CONNECTIONS", "100"
                ),
                http_pool_max_keepalive=os.environ.get("HTTP_POOL_MAX_KEEPALIVE", "50"),
                profile_cpu_iterations=os.environ.get("PROFILE_CPU_ITERATIONS", "800"),
                max_request_bytes=os.environ.get("MAX_REQUEST_BYTES", "4096"),
                log_level=os.environ.get("LOG_LEVEL", "INFO"),
            )
        except ValidationError:
            raise RuntimeError("invalid profile service configuration") from None
