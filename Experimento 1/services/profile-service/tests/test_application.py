from decimal import Decimal

import pytest

from app.application import create_app
from app.config import Settings
from app.models import OpenFinanceData, ProfileInputs, StoredProfile


PROFILE_REF = "profile-00000000-0000-4000-8000-000000000101"


class FakeRepository:
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = ready
        self.calls = 0

    def get_profile(self, partner_ref: str, profile_ref: str) -> StoredProfile:
        self.calls += 1
        return StoredProfile(
            age=35,
            monthly_income=Decimal("5000000"),
            debt_ratio=Decimal("0.25"),
            claims_count=1,
        )

    def ping(self) -> bool:
        return self.ready


class FakeCache:
    def __init__(
        self, value: ProfileInputs | None = None, *, ready: bool = True
    ) -> None:
        self.value = value
        self.ready = ready
        self.puts: list[tuple[str, str, ProfileInputs]] = []

    def get(self, partner_ref: str, profile_ref: str) -> ProfileInputs | None:
        return self.value

    def put(self, partner_ref: str, profile_ref: str, profile: ProfileInputs) -> int:
        self.puts.append((partner_ref, profile_ref, profile))
        self.value = profile
        return 930

    def ping(self) -> bool:
        return self.ready


class FakeWireMock:
    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, partner_ref: str, profile_ref: str) -> OpenFinanceData:
        self.calls += 1
        return OpenFinanceData()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql://runtime:test-password@placeholder.invalid/solventa",
        redis_url="redis://:test-password@placeholder.invalid:6379/0",
        wiremock_url="http://wiremock:8080",
        profile_cpu_iterations=5,
    )


def payload() -> dict[str, str]:
    return {"partner_ref": "partner-01", "profile_ref": PROFILE_REF}


def cached_inputs() -> ProfileInputs:
    return ProfileInputs(
        age=35,
        monthly_income=Decimal("5000000"),
        debt_ratio=Decimal("0.25"),
        claims_count=1,
        account_age_months=36,
        inflow_stability=Decimal("0.82"),
        delinquency_count=0,
    )


def test_cache_miss_queries_postgres_and_wiremock(settings: Settings) -> None:
    repository = FakeRepository()
    cache = FakeCache()
    wiremock = FakeWireMock()
    app = create_app(
        settings, repository=repository, cache=cache, wiremock_client=wiremock
    )

    response = app.test_client().post("/internal/v1/profiles/score", json=payload())

    assert response.status_code == 200
    assert response.get_json()["cache_status"] == "miss"
    assert repository.calls == 1
    assert wiremock.calls == 1
    assert len(cache.puts) == 1


def test_cache_hit_skips_postgres_and_wiremock_but_scores(settings: Settings) -> None:
    repository = FakeRepository()
    cache = FakeCache(cached_inputs())
    wiremock = FakeWireMock()
    app = create_app(
        settings, repository=repository, cache=cache, wiremock_client=wiremock
    )

    response = app.test_client().post("/internal/v1/profiles/score", json=payload())

    assert response.status_code == 200
    assert response.get_json()["risk_score"] >= 0
    assert response.get_json()["cache_status"] == "hit"
    assert repository.calls == 0
    assert wiremock.calls == 0


def test_invalid_input_is_rejected_before_dependencies(settings: Settings) -> None:
    repository = FakeRepository()
    cache = FakeCache()
    wiremock = FakeWireMock()
    app = create_app(
        settings, repository=repository, cache=cache, wiremock_client=wiremock
    )

    response = app.test_client().post(
        "/internal/v1/profiles/score",
        json={"partner_ref": "partner-02", "profile_ref": PROFILE_REF},
    )

    assert response.status_code == 400
    assert repository.calls == 0
    assert wiremock.calls == 0


def test_readiness_checks_postgres_and_redis(settings: Settings) -> None:
    app = create_app(
        settings,
        repository=FakeRepository(ready=True),
        cache=FakeCache(ready=False),
        wiremock_client=FakeWireMock(),
    )

    response = app.test_client().get("/health/ready")

    assert response.status_code == 503
    assert response.get_json()["checks"] == {
        "postgresql": True,
        "redis": False,
    }


def test_metrics_include_partner_and_cache_result(settings: Settings) -> None:
    app = create_app(
        settings,
        repository=FakeRepository(),
        cache=FakeCache(cached_inputs()),
        wiremock_client=FakeWireMock(),
    )
    client = app.test_client()
    client.post("/internal/v1/profiles/score", json=payload())

    metrics = client.get("/metrics").get_data(as_text=True)

    assert 'partner="partner-01"' in metrics
    assert 'outcome="hit"' in metrics
