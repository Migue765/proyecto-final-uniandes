from decimal import Decimal

import pytest
from app.config import Settings
from app.observability import Metrics
from app.repository import PagosRepository
from fakes import FakePool


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql://runtime:test-password@placeholder.invalid/pagos",
        sqs_ordenes_pagos_url=(
            "https://sqs.us-east-1.amazonaws.com/969325258550/solventa-exp2-ordenes-pagos.fifo"
        ),
    )


def test_new_order_is_settled_with_a_single_ledger_effect(settings: Settings) -> None:
    repository = PagosRepository(settings, Metrics(), pool=FakePool())
    pool = repository._pool

    result = repository.process_order(
        operation_id="op-1", siniestro_id="sin-1", monto=Decimal("50000.00")
    )

    assert result.is_duplicate is False
    assert result.estado == "confirmado"
    assert len(pool.state["ledger"]) == 1


def test_duplicate_operation_id_returns_original_result_without_a_second_ledger_effect(
    settings: Settings,
) -> None:
    repository = PagosRepository(settings, Metrics(), pool=FakePool())
    pool = repository._pool

    first = repository.process_order(
        operation_id="op-1", siniestro_id="sin-1", monto=Decimal("50000.00")
    )
    second = repository.process_order(
        operation_id="op-1", siniestro_id="sin-1", monto=Decimal("50000.00")
    )

    assert second.is_duplicate is True
    assert second.orden_id == first.orden_id
    assert second.monto == first.monto
    assert len(pool.state["ledger"]) == 1


def test_ping_reflects_pool_health(settings: Settings) -> None:
    repository = PagosRepository(settings, Metrics(), pool=FakePool())

    assert repository.ping() is True
