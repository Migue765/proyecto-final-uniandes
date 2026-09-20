"""Environment-backed configuration for the Reclamos service."""

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


def validate_queue_url(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".amazonaws.com")
    ):
        raise ValueError("queue URL must be an https *.amazonaws.com endpoint")
    return value


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    service_name: str = "reclamos-service"
    aws_region: str = Field(default="us-east-1", min_length=1, max_length=32)
    database_url: SecretStr = Field(min_length=1)
    sqs_entrada_parametrica_url: str = Field(min_length=1, max_length=2048)
    sqs_entrada_parametrica_dlq_url: str = Field(min_length=1, max_length=2048)
    sqs_ordenes_pagos_url: str = Field(min_length=1, max_length=2048)
    sqs_ordenes_pagos_dlq_url: str = Field(min_length=1, max_length=2048)
    db_pool_min: int = Field(default=1, ge=1, le=50)
    db_pool_max: int = Field(default=10, ge=1, le=200)
    db_pool_timeout_seconds: float = Field(default=1.0, gt=0, le=30)
    sqs_wait_time_seconds: int = Field(default=20, ge=0, le=20)
    sqs_visibility_timeout_seconds: int = Field(default=30, ge=1, le=43_200)
    outbox_poll_interval_seconds: float = Field(default=2.0, gt=0, le=60)
    outbox_batch_size: int = Field(default=25, ge=1, le=100)
    dlq_peek_max_messages: int = Field(default=50, ge=1, le=50)
    enable_consumer_thread: bool = True
    enable_outbox_publisher_thread: bool = True
    max_request_bytes: int = Field(default=4_096, ge=128, le=65_536)
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def validate_database_connection(cls, value: SecretStr) -> SecretStr:
        return validate_database_url(value)

    @field_validator(
        "sqs_entrada_parametrica_url",
        "sqs_entrada_parametrica_dlq_url",
        "sqs_ordenes_pagos_url",
        "sqs_ordenes_pagos_dlq_url",
    )
    @classmethod
    def validate_queue_urls(cls, value: str) -> str:
        return validate_queue_url(value)

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
                aws_region=os.environ.get("AWS_REGION", "us-east-1"),
                database_url=os.environ.get("DATABASE_URL", ""),
                sqs_entrada_parametrica_url=os.environ.get(
                    "SQS_ENTRADA_PARAMETRICA_URL", ""
                ),
                sqs_entrada_parametrica_dlq_url=os.environ.get(
                    "SQS_ENTRADA_PARAMETRICA_DLQ_URL", ""
                ),
                sqs_ordenes_pagos_url=os.environ.get("SQS_ORDENES_PAGOS_URL", ""),
                sqs_ordenes_pagos_dlq_url=os.environ.get(
                    "SQS_ORDENES_PAGOS_DLQ_URL", ""
                ),
                db_pool_min=os.environ.get("DB_POOL_MIN", "1"),
                db_pool_max=os.environ.get("DB_POOL_MAX", "10"),
                db_pool_timeout_seconds=os.environ.get(
                    "DB_POOL_TIMEOUT_SECONDS", "1.0"
                ),
                sqs_wait_time_seconds=os.environ.get("SQS_WAIT_TIME_SECONDS", "20"),
                sqs_visibility_timeout_seconds=os.environ.get(
                    "SQS_VISIBILITY_TIMEOUT_SECONDS", "30"
                ),
                outbox_poll_interval_seconds=os.environ.get(
                    "OUTBOX_POLL_INTERVAL_SECONDS", "2.0"
                ),
                outbox_batch_size=os.environ.get("OUTBOX_BATCH_SIZE", "25"),
                dlq_peek_max_messages=os.environ.get("DLQ_PEEK_MAX_MESSAGES", "50"),
                enable_consumer_thread=os.environ.get(
                    "ENABLE_CONSUMER_THREAD", "true"
                ).lower()
                not in {"0", "false", "no"},
                enable_outbox_publisher_thread=os.environ.get(
                    "ENABLE_OUTBOX_PUBLISHER_THREAD", "true"
                ).lower()
                not in {"0", "false", "no"},
                max_request_bytes=os.environ.get("MAX_REQUEST_BYTES", "4096"),
                log_level=os.environ.get("LOG_LEVEL", "INFO"),
            )
        except ValidationError:
            raise RuntimeError("invalid reclamos service configuration") from None
