from decimal import Decimal

import pytest

from app.application import create_app
from app.config import Settings
from app.dependencies import DependencyUnavailable
from app.models import ProfileResponse, Tariff


class FakeRepository:
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = ready
        self.partner_refs: list[str] = []

    def get_tariff(self, partner_ref: str) -> Tariff:
        self.partner_refs.append(partner_ref)
        return Tariff(
            annual_rate=Decimal("0.02"),
            fixed_fee=Decimal("1500"),
            version="synthetic-v1",
        )

    def ping(self) -> bool:
        return self.ready


class FakeProfileClient:
    def __init__(self, *, ready: bool = True, fail: bool = False) -> None:
        self.ready = ready
        self.fail = fail
        self.calls: list[dict[str, str]] = []

    def get_score(self, **kwargs: str) -> ProfileResponse:
        self.calls.append(kwargs)
        if self.fail:
            raise DependencyUnavailable("synthetic failure")
        return ProfileResponse(
            partner_ref=kwargs["partner_ref"],
            profile_ref=kwargs["profile_ref"],
            risk_score=420,
            risk_band="MEDIUM",
            cache_status="hit",
            profile_version="synthetic-v1",
        )

    def ping(self) -> bool:
        return self.ready


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql://runtime:test-password@placeholder.invalid/solventa",
        profile_service_url="http://profile-service:8080",
        quote_cpu_iterations=5,
    )


def request_payload() -> dict[str, str]:
    return {
        "partner_ref": "partner-01",
        "profile_ref": "profile-00000000-0000-4000-8000-000000000101",
    }


def test_empty_body_executes_full_quotation_path(settings: Settings) -> None:
    repository = FakeRepository()
    profile = FakeProfileClient()
    app = create_app(settings, repository=repository, profile_client=profile)

    response = app.test_client().post("/api/v1/cotizaciones", data=b"")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["currency"] == "COP"
    assert payload["partner_ref"] == "partner-01"
    assert payload["monthly_premium"]
    assert repository.partner_refs == ["partner-01"]
    assert profile.calls[0]["profile_ref"].startswith("profile-")


def test_rejects_unknown_body_fields_and_invalid_partner(settings: Settings) -> None:
    app = create_app(
        settings, repository=FakeRepository(), profile_client=FakeProfileClient()
    )
    response = app.test_client().post(
        "/api/v1/cotizaciones",
        json={**request_payload(), "partner_ref": "partner-99", "unexpected": True},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_request"}


def test_rejects_nonempty_form_body_instead_of_treating_it_as_empty(
    settings: Settings,
) -> None:
    repository = FakeRepository()
    profile = FakeProfileClient()
    app = create_app(settings, repository=repository, profile_client=profile)

    response = app.test_client().post(
        "/api/v1/cotizaciones",
        data={"partner_ref": "partner-01"},
        content_type="application/x-www-form-urlencoded",
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_request"}
    assert repository.partner_refs == []
    assert profile.calls == []


def test_rejects_profile_outside_partner_partition_before_dependencies(
    settings: Settings,
) -> None:
    repository = FakeRepository()
    profile = FakeProfileClient()
    app = create_app(settings, repository=repository, profile_client=profile)

    response = app.test_client().post(
        "/api/v1/cotizaciones",
        json={
            "partner_ref": "partner-02",
            "profile_ref": "profile-00000000-0000-4000-8000-000000000101",
        },
    )

    assert response.status_code == 400
    assert repository.partner_refs == []
    assert profile.calls == []


def test_dependency_failure_is_generic(settings: Settings) -> None:
    app = create_app(
        settings,
        repository=FakeRepository(),
        profile_client=FakeProfileClient(fail=True),
    )

    response = app.test_client().post("/api/v1/cotizaciones", json=request_payload())

    assert response.status_code == 503
    assert response.get_json()["error"] == "service_unavailable"
    assert "synthetic failure" not in response.get_data(as_text=True)


def test_readiness_reflects_dependencies(settings: Settings) -> None:
    app = create_app(
        settings,
        repository=FakeRepository(ready=True),
        profile_client=FakeProfileClient(ready=False),
    )

    response = app.test_client().get("/health/ready")

    assert response.status_code == 503
    assert response.get_json()["checks"] == {
        "postgresql": True,
        "profile": False,
    }


def test_metrics_are_partitioned_by_synthetic_partner(settings: Settings) -> None:
    app = create_app(
        settings, repository=FakeRepository(), profile_client=FakeProfileClient()
    )
    client = app.test_client()
    client.post("/api/v1/cotizaciones", json=request_payload())

    metrics = client.get("/metrics").get_data(as_text=True)

    assert 'partner="partner-01"' in metrics
    assert 'route="/api/v1/cotizaciones"' in metrics
