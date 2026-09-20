"""Environment-backed configuration for the Adaptador de Ingreso."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class Settings(BaseModel):
    """Validated runtime settings.

    The SQS queue URL and the Secrets Manager ARN are trusted deployment
    configuration and never come from an HTTP request.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    service_name: str = "ingreso-service"
    aws_region: str = Field(default="us-east-1", min_length=1, max_length=32)
    sqs_entrada_parametrica_url: str = Field(min_length=1, max_length=2048)
    hmac_secret_arn: str = Field(min_length=1, max_length=2048)
    signature_max_skew_seconds: float = Field(default=600, gt=0, le=3600)
    max_request_bytes: int = Field(default=8_192, ge=128, le=65_536)
    log_level: str = "INFO"

    @field_validator("sqs_entrada_parametrica_url")
    @classmethod
    def validate_queue_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or not parsed.hostname.endswith(".amazonaws.com")
        ):
            raise ValueError("queue URL must be an https *.amazonaws.com endpoint")
        return value

    @field_validator("hmac_secret_arn")
    @classmethod
    def validate_secret_arn(cls, value: str) -> str:
        if not value.startswith("arn:aws:secretsmanager:"):
            raise ValueError("hmac secret arn must be a Secrets Manager ARN")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("unsupported log level")
        return normalized

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            return cls(
                aws_region=os.environ.get("AWS_REGION", "us-east-1"),
                sqs_entrada_parametrica_url=os.environ.get(
                    "SQS_ENTRADA_PARAMETRICA_URL", ""
                ),
                hmac_secret_arn=os.environ.get("HMAC_SHARED_SECRET_ARN", ""),
                signature_max_skew_seconds=os.environ.get(
                    "SIGNATURE_MAX_SKEW_SECONDS", "600"
                ),
                max_request_bytes=os.environ.get("MAX_REQUEST_BYTES", "8192"),
                log_level=os.environ.get("LOG_LEVEL", "INFO"),
            )
        except ValidationError:
            raise RuntimeError("invalid ingreso service configuration") from None
