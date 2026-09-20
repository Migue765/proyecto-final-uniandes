"""Environment-backed configuration for the quotation service."""

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


def validate_database_url(value: SecretStr) -> SecretStr:
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


class Settings(BaseModel):
    """Validated runtime settings.

    Service URLs are trusted deployment configuration and never come from an
    HTTP request. Credentials stay wrapped in ``SecretStr`` so accidental
    serialization cannot disclose them.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    service_name: str = "quotation-service"
    database_url: SecretStr = Field(min_length=1)
    profile_service_url: str = Field(min_length=1, max_length=512)
    db_pool_min: int = Field(default=1, ge=1, le=50)
    db_pool_max: int = Field(default=10, ge=1, le=200)
    db_pool_timeout_seconds: float = Field(default=1.0, gt=0, le=30)
    http_connect_timeout_seconds: float = Field(default=0.25, gt=0, le=10)
    http_read_timeout_seconds: float = Field(default=0.75, gt=0, le=30)
    http_pool_max_connections: int = Field(default=100, ge=1, le=1000)
    http_pool_max_keepalive: int = Field(default=50, ge=1, le=1000)
    quote_cpu_iterations: int = Field(default=1_200, ge=1, le=1_000_000)
    max_request_bytes: int = Field(default=4_096, ge=128, le=65_536)
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def validate_database_connection(cls, value: SecretStr) -> SecretStr:
        return validate_database_url(value)

    @field_validator("profile_service_url")
    @classmethod
    def validate_profile_service_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("profile service URL must use http or https")
        if not parsed.hostname or parsed.hostname.lower() in _BLOCKED_METADATA_HOSTS:
            raise ValueError("profile service URL host is not allowed")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("profile service URL must be a credential-free base URL")
        if parsed.path not in {"", "/"}:
            raise ValueError("profile service URL must not include a path")
        return value.rstrip("/")

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

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            return cls(
                database_url=os.environ.get("DATABASE_URL", ""),
                profile_service_url=os.environ.get("PROFILE_SERVICE_URL", ""),
                db_pool_min=os.environ.get("DB_POOL_MIN", "1"),
                db_pool_max=os.environ.get("DB_POOL_MAX", "10"),
                db_pool_timeout_seconds=os.environ.get(
                    "DB_POOL_TIMEOUT_SECONDS", "1.0"
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
                quote_cpu_iterations=os.environ.get("QUOTE_CPU_ITERATIONS", "1200"),
                max_request_bytes=os.environ.get("MAX_REQUEST_BYTES", "4096"),
                log_level=os.environ.get("LOG_LEVEL", "INFO"),
            )
        except ValidationError:
            raise RuntimeError("invalid quotation service configuration") from None
