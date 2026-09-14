import pytest
from pydantic import ValidationError

from app.config import Settings
from app.models import QuoteRequest


def test_rejects_metadata_service_destination() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://runtime:test-password@placeholder.invalid/solventa",
            profile_service_url="http://169.254.169.254",
        )


def test_rejects_resource_injection_in_partner_reference() -> None:
    with pytest.raises(ValidationError):
        QuoteRequest(partner_ref="partner-01?admin=true")


def test_rejects_credentials_or_paths_in_service_base_url() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://runtime:test-password@placeholder.invalid/solventa",
            profile_service_url="https://user:password@profile.invalid/admin",
        )


def test_requires_verified_tls_for_rds() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url=(
                "postgresql://runtime:test-password@"
                "database.cluster.us-east-1.rds.amazonaws.com/solventa"
            ),
            profile_service_url="http://profile-service:8080",
        )


def test_accepts_rds_with_pinned_bundle_path() -> None:
    settings = Settings(
        database_url=(
            "postgresql://runtime:test-password@"
            "database.cluster.us-east-1.rds.amazonaws.com/solventa"
            "?sslmode=verify-full&"
            "sslrootcert=/etc/ssl/certs/aws-rds-global-bundle.pem"
        ),
        profile_service_url="http://profile-service:8080",
    )

    assert settings.database_url.get_secret_value().startswith("postgresql://")


def test_rejects_profile_outside_partner_partition() -> None:
    with pytest.raises(ValidationError):
        QuoteRequest(
            partner_ref="partner-02",
            profile_ref="profile-00000000-0000-4000-8000-000000000101",
        )


def test_rejects_arbitrary_uuid_even_when_shape_is_valid() -> None:
    with pytest.raises(ValidationError):
        QuoteRequest(
            partner_ref="partner-01",
            profile_ref="profile-12345678-1234-4123-8123-000000000101",
        )
