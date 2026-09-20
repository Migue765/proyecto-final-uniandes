"""A tiny in-memory stand-in for the psycopg surface ``ReclamosRepository`` uses.

It pattern-matches on the small, fixed set of SQL statements the repository
actually issues rather than implementing a real SQL engine — enough to
exercise the idempotency decision logic (the point of these tests) without a
live PostgreSQL instance.
"""

from __future__ import annotations

from typing import Any


class FakeCursor:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._rows)


class FakeTransaction:
    def __enter__(self) -> "FakeTransaction":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


class FakeConnection:
    def __init__(self, state: dict[str, Any]) -> None:
        self._state = state

    def commit(self) -> None:
        pass

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> FakeCursor:
        normalized = " ".join(sql.split())

        if normalized.startswith("CREATE TABLE") or normalized.startswith("CREATE INDEX"):
            return FakeCursor([])

        if normalized.startswith("SELECT 1"):
            return FakeCursor([(1,)])

        if normalized.startswith("INSERT INTO reclamos_inbox"):
            external_event_id, siniestro_id, monto, estado = params
            if external_event_id in self._state["inbox"]:
                return FakeCursor([])
            self._state["inbox"][external_event_id] = {
                "siniestro_id": siniestro_id,
                "monto_liquidado": monto,
                "estado": estado,
            }
            return FakeCursor([(external_event_id,)])

        if normalized.startswith("SELECT siniestro_id, monto_liquidado, estado"):
            (external_event_id,) = params
            row = self._state["inbox"].get(external_event_id)
            if row is None:
                return FakeCursor([])
            return FakeCursor([(row["siniestro_id"], row["monto_liquidado"], row["estado"])])

        if normalized.startswith("INSERT INTO siniestros"):
            siniestro_id, external_event_id, tipo, magnitud, monto, estado = params
            self._state["siniestros"][siniestro_id] = {
                "external_event_id": external_event_id,
                "tipo_evento_parametrico": tipo,
                "magnitud": magnitud,
                "monto_liquidado": monto,
                "estado": estado,
            }
            return FakeCursor([])

        if normalized.startswith("INSERT INTO outbox_ordenes_pagos"):
            operation_id, siniestro_id, monto, partition_key = params
            row_id = self._state["next_outbox_id"]
            self._state["next_outbox_id"] += 1
            self._state["outbox"][row_id] = {
                "operation_id": operation_id,
                "siniestro_id": siniestro_id,
                "monto": monto,
                "partition_key": partition_key,
                "published": False,
            }
            return FakeCursor([])

        if normalized.startswith("SELECT id, operation_id, siniestro_id, monto, partition_key"):
            (limit,) = params
            pending = [
                (row_id, row["operation_id"], row["siniestro_id"], row["monto"], row["partition_key"])
                for row_id, row in sorted(self._state["outbox"].items())
                if not row["published"]
            ]
            return FakeCursor(pending[:limit])

        if normalized.startswith("UPDATE outbox_ordenes_pagos SET published"):
            (row_id,) = params
            self._state["outbox"][row_id]["published"] = True
            return FakeCursor([])

        raise AssertionError(f"unexpected SQL in FakeConnection: {sql!r}")


class _ConnectionContext:
    def __init__(self, state: dict[str, Any]) -> None:
        self._state = state

    def __enter__(self) -> FakeConnection:
        return FakeConnection(self._state)

    def __exit__(self, *exc_info: object) -> bool:
        return False


class FakePool:
    def __init__(self) -> None:
        self.state: dict[str, Any] = {
            "inbox": {},
            "siniestros": {},
            "outbox": {},
            "next_outbox_id": 1,
        }

    def connection(self, timeout: float | None = None) -> _ConnectionContext:
        del timeout
        return _ConnectionContext(self.state)

    def close(self) -> None:
        pass
