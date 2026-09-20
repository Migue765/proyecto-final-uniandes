from decimal import Decimal

import pytest
from app.config import Settings
from app.models import ParametricEventPayload
from app.observability import Metrics
from app.repository import ReclamosRepository
from fakes import FakePool


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql://runtime:test-password@placeholder.invalid/reclamos",
        sqs_entrada_parametrica_url=(
            "https://sqs.us-east-1.amazonaws.com/969325258550/"
            "solventa-exp2-entrada-parametrica.fifo"
        ),
        sqs_entrada_parametrica_dlq_url=(
            "https://sqs.us-east-1.amazonaws.com/969325258550/"
            "solventa-exp2-entrada-parametrica-dlq.fifo"
        ),
        sqs_ordenes_pagos_url=(
            "https://sqs.us-east-1.amazonaws.com/969325258550/solventa-exp2-ordenes-pagos.fifo"
        ),
        sqs_ordenes_pagos_dlq_url=(
            "https://sqs.us-east-1.amazonaws.com/969325258550/"
            "solventa-exp2-ordenes-pagos-dlq.fifo"
        ),
    )


def triggered_payload() -> ParametricEventPayload:
    return ParametricEventPayload(
        tipo_evento_parametrico="sismo",
        magnitud=Decimal("7.0"),
        umbral_activacion=Decimal("6.0"),
        suma_asegurada=Decimal(100000),
    )


def below_threshold_payload() -> ParametricEventPayload:
    return ParametricEventPayload(
        tipo_evento_parametrico="sismo",
        magnitud=Decimal("4.0"),
        umbral_activacion=Decimal("6.0"),
        suma_asegurada=Decimal(100000),
    )


def test_new_event_is_settled_and_queued_for_payment(settings: Settings) -> None:
    repository = ReclamosRepository(settings, Metrics(), pool=FakePool())

    result = repository.process_event(
        external_event_id="evt-1", partition_key="riesgo-01", payload=triggered_payload()
    )

    assert result.is_duplicate is False
    assert result.estado == "aprobado"
    assert result.monto_liquidado > 0
    assert result.operation_id is not None

    pending = repository.fetch_unpublished_outbox_rows(limit=10)
    assert len(pending) == 1
    assert pending[0].operation_id == result.operation_id


def test_duplicate_external_event_id_returns_the_original_result_without_a_second_effect(
    settings: Settings,
) -> None:
    repository = ReclamosRepository(settings, Metrics(), pool=FakePool())

    first = repository.process_event(
        external_event_id="evt-1", partition_key="riesgo-01", payload=triggered_payload()
    )
    second = repository.process_event(
        external_event_id="evt-1", partition_key="riesgo-01", payload=triggered_payload()
    )

    assert second.is_duplicate is True
    assert second.siniestro_id == first.siniestro_id
    assert second.monto_liquidado == first.monto_liquidado
    assert second.operation_id is None

    # Only one outbox row exists — the duplicate never created a second one.
    pending = repository.fetch_unpublished_outbox_rows(limit=10)
    assert len(pending) == 1


def test_late_redelivery_after_publish_is_still_recognized_as_duplicate(
    settings: Settings,
) -> None:
    repository = ReclamosRepository(settings, Metrics(), pool=FakePool())

    first = repository.process_event(
        external_event_id="evt-1", partition_key="riesgo-01", payload=triggered_payload()
    )
    for row in repository.fetch_unpublished_outbox_rows(limit=10):
        repository.mark_outbox_published(row.id)

    redelivered = repository.process_event(
        external_event_id="evt-1", partition_key="riesgo-01", payload=triggered_payload()
    )

    assert redelivered.is_duplicate is True
    assert redelivered.siniestro_id == first.siniestro_id
    assert repository.fetch_unpublished_outbox_rows(limit=10) == []


def test_below_threshold_event_is_rejected_without_a_payment_order(settings: Settings) -> None:
    repository = ReclamosRepository(settings, Metrics(), pool=FakePool())

    result = repository.process_event(
        external_event_id="evt-2", partition_key="riesgo-01", payload=below_threshold_payload()
    )

    assert result.estado == "rechazado_umbral"
    assert result.monto_liquidado == Decimal("0.00")
    assert result.operation_id is None
    assert repository.fetch_unpublished_outbox_rows(limit=10) == []


def test_ping_reflects_pool_health(settings: Settings) -> None:
    repository = ReclamosRepository(settings, Metrics(), pool=FakePool())

    assert repository.ping() is True


def test_injected_pool_is_not_closed_by_the_repository(settings: Settings) -> None:
    pool = FakePool()
    repository = ReclamosRepository(settings, Metrics(), pool=pool)

    repository.close()

    # An injected pool is owned by the caller (e.g. shared across tests or
    # closed explicitly by the app factory); the repository must not close a
    # pool it did not create itself.
    assert repository.ping() is True
