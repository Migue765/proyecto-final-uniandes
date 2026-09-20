"""A tiny in-memory stand-in for the psycopg surface ``PagosRepository`` uses."""

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

        if normalized.startswith("CREATE TABLE"):
            return FakeCursor([])

        if normalized.startswith("SELECT 1"):
            return FakeCursor([(1,)])

        if normalized.startswith("INSERT INTO pagos_inbox"):
            operation_id, orden_id, monto, estado = params
            if operation_id in self._state["inbox"]:
                return FakeCursor([])
            self._state["inbox"][operation_id] = {
                "orden_id": orden_id,
                "monto": monto,
                "estado": estado,
            }
            return FakeCursor([(operation_id,)])

        if normalized.startswith("SELECT orden_id, monto, estado"):
            (operation_id,) = params
            row = self._state["inbox"].get(operation_id)
            if row is None:
                return FakeCursor([])
            return FakeCursor([(row["orden_id"], row["monto"], row["estado"])])

        if normalized.startswith("INSERT INTO ordenes_pago"):
            orden_id, operation_id, siniestro_id, monto, estado = params
            self._state["ordenes_pago"][orden_id] = {
                "operation_id": operation_id,
                "siniestro_id": siniestro_id,
                "monto": monto,
                "estado": estado,
            }
            return FakeCursor([])

        if normalized.startswith("INSERT INTO ledger_simulado"):
            orden_id, operation_id, monto, referencia = params
            self._state["ledger"][orden_id] = {
                "operation_id": operation_id,
                "monto": monto,
                "referencia": referencia,
            }
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
        self.state: dict[str, Any] = {"inbox": {}, "ordenes_pago": {}, "ledger": {}}

    def connection(self, timeout: float | None = None) -> _ConnectionContext:
        del timeout
        return _ConnectionContext(self.state)

    def close(self) -> None:
        pass
