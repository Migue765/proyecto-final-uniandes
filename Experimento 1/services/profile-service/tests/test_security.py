import pytest
from pydantic import ValidationError

from app.config import Settings
from app.models import ProfileScoreRequest


def base_settings(**overrides: str) -> dict[str, str]:
    values = {
        "database_url": "postgresql://runtime:test-password@placeholder.invalid/solventa",
        "redis_url": "redis://:test-password@placeholder.invalid:6379/0",
        "wiremock_url": "http://wiremock:8080",
    }
    values.update(overrides)
    return values


def test_rejects_metadata_wiremock_destination() -> None:
    with pytest.raises(ValidationError):
        Settings(**base_settings(wiremock_url="http://169.254.169.254"))


def test_rejects_resource_injection_in_profile_reference() -> None:
    with pytest.raises(ValidationError):
        ProfileScoreRequest(
            partner_ref="partner-01",
            profile_ref=("profile-00000000-0000-4000-8000-000000000101?admin=true"),
        )


def test_rejects_non_redis_cache_scheme() -> None:
    with pytest.raises(ValidationError):
        Settings(**base_settings(redis_url="http://redis:6379/0"))


def test_requires_tls_and_auth_for_elasticache() -> None:
    with pytest.raises(ValidationError):
        Settings(
            **base_settings(
                redis_url="redis://:test-password@cache.cache.amazonaws.com:6379/0"
            )
        )


def test_accepts_authenticated_tls_elasticache_database_zero() -> None:
    settings = Settings(
        **base_settings(
            redis_url="rediss://:test-password@cache.cache.amazonaws.com:6379/0"
        )
    )

    assert settings.redis_url.get_secret_value().startswith("rediss://")


def test_requires_verified_tls_for_rds() -> None:
    with pytest.raises(ValidationError):
        Settings(
            **base_settings(
                database_url=(
                    "postgresql://runtime:test-password@"
                    "database.cluster.us-east-1.rds.amazonaws.com/solventa"
                )
            )
        )


def test_accepts_rds_with_pinned_bundle_path() -> None:
    settings = Settings(
        **base_settings(
            database_url=(
                "postgresql://runtime:test-password@"
                "database.cluster.us-east-1.rds.amazonaws.com/solventa"
                "?sslmode=verify-full&"
                "sslrootcert=/etc/ssl/certs/aws-rds-global-bundle.pem"
            )
        )
    )

    assert settings.database_url.get_secret_value().startswith("postgresql://")


def test_rejects_profile_outside_partner_partition() -> None:
    with pytest.raises(ValidationError):
        ProfileScoreRequest(
            partner_ref="partner-02",
            profile_ref="profile-00000000-0000-4000-8000-000000000101",
        )


def test_rejects_arbitrary_uuid_even_when_shape_is_valid() -> None:
    with pytest.raises(ValidationError):
        ProfileScoreRequest(
            partner_ref="partner-01",
            profile_ref="profile-12345678-1234-4123-8123-000000000101",
        )
