"""PostgreSQL repository implementing the Inbox and Transactional Outbox patterns.

The connection pool is injectable so the idempotency decision logic (the
actual point of this module) can be unit-tested with a fake connection that
mimics the small slice of the psycopg API this module relies on
(``pool.connection()`` / ``connection.transaction()`` / ``connection.execute()``
/ ``cursor.fetchone()``/``fetchall()``), without a live PostgreSQL instance.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from psycopg_pool import ConnectionPool

from .computation import evaluate_and_settle
from .config import Settings
from .models import ParametricEventPayload, ProcessingResult
from .observability import Metrics

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS reclamos_inbox (
        external_event_id TEXT PRIMARY KEY,
        siniestro_id TEXT NOT NULL,
        monto_liquidado NUMERIC NOT NULL,
        estado TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS siniestros (
        siniestro_id TEXT PRIMARY KEY,
        external_event_id TEXT NOT NULL,
        tipo_evento_parametrico TEXT NOT NULL,
        magnitud NUMERIC NOT NULL,
        monto_liquidado NUMERIC NOT NULL,
        estado TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS outbox_ordenes_pagos (
        id BIGSERIAL PRIMARY KEY,
        operation_id TEXT NOT NULL UNIQUE,
        siniestro_id TEXT NOT NULL,
        monto NUMERIC NOT NULL,
        partition_key TEXT NOT NULL,
        published BOOLEAN NOT NULL DEFAULT false,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS outbox_ordenes_pagos_pending "
    "ON outbox_ordenes_pagos (id) WHERE NOT published",
)


class SupportsCursor(Protocol):
    def fetchone(self) -> tuple[Any, ...] | None: ...
    def fetchall(self) -> list[tuple[Any, ...]]: ...


class SupportsConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> SupportsCursor: ...

    def transaction(self) -> Any: ...


@dataclass(frozen=True)
class OutboxRow:
    id: int
    operation_id: str
    siniestro_id: str
    monto: Decimal
    partition_key: str


class ReclamosRepository:
    def __init__(
        self,
        settings: Settings,
        metrics: Metrics,
        *,
        pool: Any | None = None,
    ) -> None:
        self._pool = pool or ConnectionPool(
            conninfo=settings.database_url.get_secret_value(),
            min_size=settings.db_pool_min,
            max_size=settings.db_pool_max,
            timeout=settings.db_pool_timeout_seconds,
            open=True,
            kwargs={"autocommit": False},
        )
        self._timeout = settings.db_pool_timeout_seconds
        self._metrics = metrics
        self._owns_pool = pool is None
        # Schema creation is exclusively app/seed.py's job, run once with
        # admin credentials by the Helm pre-install hook. This repository
        # only ever connects with the least-privilege runtime role (see
        # configure_runtime_role in seed.py), which deliberately has no
        # CREATE privilege on the schema — calling _SCHEMA_STATEMENTS here
        # would fail with InsufficientPrivilege on every pod startup.

    def process_event(
        self,
        *,
        external_event_id: str,
        partition_key: str,
        payload: ParametricEventPayload,
    ) -> ProcessingResult:
        """Idempotently record an event and, on first sight, settle it.

        The unique constraint on ``external_event_id`` is the actual
        idempotency mechanism: ``INSERT ... ON CONFLICT DO NOTHING`` either
        wins (new event) or loses (duplicate/redelivery), inside one
        transaction, so no race between concurrent redeliveries of the same
        event can create two settlements.
        """

        started = time.perf_counter()
        siniestro_id = str(uuid.uuid4())
        operation_id = str(uuid.uuid4())
        monto = evaluate_and_settle(payload)
        estado = "aprobado" if monto > 0 else "rechazado_umbral"

        try:
            with self._pool.connection(timeout=self._timeout) as connection:
                with connection.transaction():
                    inserted = connection.execute(
                        """
                        INSERT INTO reclamos_inbox
                            (external_event_id, siniestro_id, monto_liquidado, estado)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (external_event_id) DO NOTHING
                        RETURNING external_event_id
                        """,
                        (external_event_id, siniestro_id, str(monto), estado),
                    ).fetchone()

                    if inserted is None:
                        existing = connection.execute(
                            """
                            SELECT siniestro_id, monto_liquidado, estado
                            FROM reclamos_inbox
                            WHERE external_event_id = %s
                            """,
                            (external_event_id,),
                        ).fetchone()
                        if existing is None:
                            raise RuntimeError(
                                "inbox conflict without a matching row"
                            )
                        return ProcessingResult(
                            is_duplicate=True,
                            siniestro_id=existing[0],
                            monto_liquidado=Decimal(str(existing[1])),
                            estado=existing[2],
                            operation_id=None,
                        )

                    connection.execute(
                        """
                        INSERT INTO siniestros
                            (siniestro_id, external_event_id, tipo_evento_parametrico,
                             magnitud, monto_liquidado, estado)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            siniestro_id,
                            external_event_id,
                            payload.tipo_evento_parametrico,
                            str(payload.magnitud),
                            str(monto),
                            estado,
                        ),
                    )

                    if estado == "aprobado":
                        connection.execute(
                            """
                            INSERT INTO outbox_ordenes_pagos
                                (operation_id, siniestro_id, monto, partition_key, published)
                            VALUES (%s, %s, %s, %s, false)
                            """,
                            (operation_id, siniestro_id, str(monto), partition_key),
                        )

                    return ProcessingResult(
                        is_duplicate=False,
                        siniestro_id=siniestro_id,
                        monto_liquidado=monto,
                        estado=estado,
                        operation_id=operation_id if estado == "aprobado" else None,
                    )
        finally:
            self._metrics.dependency_latency.labels("postgresql", "process_event").observe(
                time.perf_counter() - started
            )

    def fetch_unpublished_outbox_rows(self, *, limit: int) -> list[OutboxRow]:
        with self._pool.connection(timeout=self._timeout) as connection:
            rows = connection.execute(
                """
                SELECT id, operation_id, siniestro_id, monto, partition_key
                FROM outbox_ordenes_pagos
                WHERE NOT published
                ORDER BY id
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [
            OutboxRow(
                id=row[0],
                operation_id=row[1],
                siniestro_id=row[2],
                monto=Decimal(str(row[3])),
                partition_key=row[4],
            )
            for row in rows
        ]

    def mark_outbox_published(self, row_id: int) -> None:
        with self._pool.connection(timeout=self._timeout) as connection:
            connection.execute(
                "UPDATE outbox_ordenes_pagos SET published = true WHERE id = %s",
                (row_id,),
            )
            connection.commit()

    def ping(self) -> bool:
        try:
            with self._pool.connection(timeout=self._timeout) as connection:
                return bool(connection.execute("SELECT 1").fetchone())
        except Exception:
            return False

    def close(self) -> None:
        if self._owns_pool:
            self._pool.close()
