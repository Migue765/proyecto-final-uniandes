from app.application import create_app
from app.config import Settings


class FakeRepository:
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = ready

    def ping(self) -> bool:
        return self.ready

    def close(self) -> None:
        pass


class FakeConsumer:
    def is_alive(self) -> bool:
        return True

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


def settings() -> Settings:
    return Settings(
        database_url="postgresql://runtime:test-password@placeholder.invalid/pagos",
        sqs_ordenes_pagos_url=(
            "https://sqs.us-east-1.amazonaws.com/969325258550/solventa-exp2-ordenes-pagos.fifo"
        ),
    )


def test_readiness_reflects_database_health() -> None:
    app = create_app(settings(), repository=FakeRepository(ready=False), consumer=FakeConsumer())

    response = app.test_client().get("/health/ready")

    assert response.status_code == 503
    assert response.get_json()["checks"] == {"postgresql": False}


def test_unknown_route_returns_404_not_internal_error() -> None:
    app = create_app(settings(), repository=FakeRepository(), consumer=FakeConsumer())

    response = app.test_client().get("/does-not-exist")

    assert response.status_code == 404


def test_metrics_endpoint_is_exposed() -> None:
    app = create_app(settings(), repository=FakeRepository(), consumer=FakeConsumer())

    response = app.test_client().get("/metrics")

    assert response.status_code == 200
