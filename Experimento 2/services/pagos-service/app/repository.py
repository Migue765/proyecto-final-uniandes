"""PostgreSQL repository implementing the Inbox pattern for payment orders.

Same injectable-pool design as ``reclamos-service/app/repository.py``: the
idempotency decision logic is the point of the unit tests, so the connection
pool can be swapped for a fake without a live PostgreSQL instance.
"""

from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import Any

from psycopg_pool import ConnectionPool

from .config import Settings
from .models import PaymentResult
from .observability import Metrics

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS pagos_inbox (
        operation_id TEXT PRIMARY KEY,
        orden_id TEXT NOT NULL,
        monto NUMERIC NOT NULL,
        estado TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ordenes_pago (
        orden_id TEXT PRIMARY KEY,
        operation_id TEXT NOT NULL,
        siniestro_id TEXT NOT NULL,
        monto NUMERIC NOT NULL,
        estado TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ledger_simulado (
        orden_id TEXT PRIMARY KEY,
        operation_id TEXT NOT NULL UNIQUE,
        monto NUMERIC NOT NULL,
        referencia TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
)


class PagosRepository:
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

    def process_order(self, *, operation_id: str, siniestro_id: str, monto: Decimal) -> PaymentResult:
        """Idempotently record a payment order and register its single ledger effect.

        The unique constraint on ``operation_id`` is the idempotency
        mechanism: a redelivered order (same ``operation_id``) always
        recovers the *same* ``orden_id``/``monto`` and never creates a second
        ledger row.
        """

        started = time.perf_counter()
        orden_id = str(uuid.uuid4())
        estado = "confirmado"

        try:
            with self._pool.connection(timeout=self._timeout) as connection:
                with connection.transaction():
                    inserted = connection.execute(
                        """
                        INSERT INTO pagos_inbox (operation_id, orden_id, monto, estado)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (operation_id) DO NOTHING
                        RETURNING operation_id
                        """,
                        (operation_id, orden_id, str(monto), estado),
                    ).fetchone()

                    if inserted is None:
                        existing = connection.execute(
                            "SELECT orden_id, monto, estado FROM pagos_inbox WHERE operation_id = %s",
                            (operation_id,),
                        ).fetchone()
                        if existing is None:
                            raise RuntimeError("inbox conflict without a matching row")
                        return PaymentResult(
                            is_duplicate=True,
                            orden_id=existing[0],
                            monto=Decimal(str(existing[1])),
                            estado=existing[2],
                        )

                    connection.execute(
                        """
                        INSERT INTO ordenes_pago
                            (orden_id, operation_id, siniestro_id, monto, estado)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (orden_id, operation_id, siniestro_id, str(monto), estado),
                    )
                    connection.execute(
                        """
                        INSERT INTO ledger_simulado (orden_id, operation_id, monto, referencia)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (orden_id, operation_id, str(monto), f"ledger-{orden_id}"),
                    )
                    return PaymentResult(
                        is_duplicate=False, orden_id=orden_id, monto=monto, estado=estado
                    )
        finally:
            self._metrics.dependency_latency.labels("postgresql", "process_order").observe(
                time.perf_counter() - started
            )

    def ping(self) -> bool:
        try:
            with self._pool.connection(timeout=self._timeout) as connection:
                return bool(connection.execute("SELECT 1").fetchone())
        except Exception:
            return False

    def close(self) -> None:
        if self._owns_pool:
            self._pool.close()
