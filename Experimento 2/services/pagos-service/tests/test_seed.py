import json
from typing import Any

import psycopg
import pytest
from app.seed import (
    RUNTIME_ROLE,
    SeedSettings,
    SeedStageError,
    _failure_event,
    _with_database,
    configure_runtime_role,
    create_database_if_missing,
    main,
    seed_database,
)
from pydantic import SecretStr, ValidationError


class FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeResult:
    def __init__(self, row: tuple[Any, ...] | None = None) -> None:
        self._row = row

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row


class FakeDiagnostic:
    message_primary = (
        'permission denied for role "pagos_runtime"; password=hunter2; '
        "postgresql://admin:do-not-log@example.invalid/pagos " + ("x" * 300)
    )


class FakeDatabaseError(Exception):
    sqlstate = "42501"
    diag = FakeDiagnostic()


class FakePgConnection:
    def __init__(self) -> None:
        self.encrypt_calls = 0

    def encrypt_password(self, password: bytes, user: bytes, algorithm: bytes) -> bytes:
        assert password
        assert user == b"pagos_runtime"
        assert algorithm == b"scram-sha-256"
        self.encrypt_calls += 1
        return b"SCRAM-SHA-256$4096:synthetic$safe-verifier"


class FakeConnection:
    def __init__(self, *, role_exists: bool = False, privileged_role: bool = False) -> None:
        self.role_exists = role_exists
        self.privileged_role = privileged_role
        self.executions: list[tuple[Any, tuple[Any, ...] | None]] = []
        self.pgconn = FakePgConnection()

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(self, query: Any, params: tuple[Any, ...] | None = None) -> FakeResult:
        self.executions.append((query, params))
        if isinstance(query, str) and "FROM pg_catalog.pg_roles role" in query:
            if not self.role_exists:
                return FakeResult()
            return FakeResult(
                (
                    self.privileged_role,
                    self.privileged_role,
                    self.privileged_role,
                    self.privileged_role,
                    self.privileged_role,
                    self.privileged_role,
                    self.privileged_role,
                )
            )
        if query == "SELECT current_database()":
            return FakeResult(("pagos",))
        return FakeResult()


def rendered_statements(connection: FakeConnection) -> list[str]:
    return [str(query) for query, _ in connection.executions]


def test_seed_creates_schema_and_read_write_runtime_role() -> None:
    connection = FakeConnection()

    seed_database(connection, RUNTIME_ROLE, SecretStr("a-runtime-password-with-24-chars"))

    statements = rendered_statements(connection)
    assert any("CREATE TABLE IF NOT EXISTS pagos_inbox" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS ordenes_pago" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS ledger_simulado" in statement for statement in statements)
    assert any("CREATE ROLE" in statement for statement in statements)
    assert any("GRANT SELECT, INSERT, UPDATE ON TABLE" in statement for statement in statements)
    assert not any("DELETE" in statement for statement in statements)
    assert connection.pgconn.encrypt_calls == 1
    assert any("SCRAM-SHA-256" in statement for statement in statements)


def test_existing_privileged_runtime_role_is_rejected() -> None:
    connection = FakeConnection(role_exists=True, privileged_role=True)

    with pytest.raises(RuntimeError, match="forbidden privileges"):
        configure_runtime_role(connection, RUNTIME_ROLE, SecretStr("another-runtime-password-24"))


def test_seed_rejects_any_runtime_role_name_other_than_fixed_role() -> None:
    with pytest.raises(ValueError):
        configure_runtime_role(
            FakeConnection(), "attacker_controlled_role", SecretStr("another-runtime-password-24")
        )


def test_with_database_swaps_path_keeps_credentials_and_query() -> None:
    admin_url = (
        "postgresql://solventa_admin:s3cr3t@"
        "solventa-exp1-postgres.example.rds.amazonaws.com:5432/postgres"
        "?sslmode=verify-full&sslrootcert=%2Fetc%2Fssl%2Fcerts%2Faws-rds-global-bundle.pem"
    )

    result = _with_database(admin_url, "pagos")

    assert result.startswith(
        "postgresql://solventa_admin:s3cr3t@solventa-exp1-postgres.example.rds.amazonaws.com:5432/pagos"
    )
    assert "sslmode=verify-full" in result


def test_create_database_if_missing_tolerates_duplicate_database(monkeypatch) -> None:
    class FakeDuplicateDatabaseError(psycopg.Error):
        sqlstate = "42P04"

    class FakeAdminConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, *_args, **_kwargs):
            raise FakeDuplicateDatabaseError("database already exists")

    monkeypatch.setattr(psycopg, "connect", lambda *args, **kwargs: FakeAdminConnection())

    create_database_if_missing("postgresql://a:b@host/postgres", 10)


def test_create_database_if_missing_reraises_other_errors(monkeypatch) -> None:
    class FakeOtherError(psycopg.Error):
        sqlstate = "08006"

    class FakeAdminConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, *_args, **_kwargs):
            raise FakeOtherError("connection failure")

    monkeypatch.setattr(psycopg, "connect", lambda *args, **kwargs: FakeAdminConnection())

    with pytest.raises(psycopg.Error):
        create_database_if_missing("postgresql://a:b@host/postgres", 10)


def test_failure_event_reports_stage_and_sqlstate_without_sensitive_data() -> None:
    event = _failure_event(
        "seed_transaction", SeedStageError("configure_runtime_role", FakeDatabaseError("unsafe fallback"))
    )

    serialized = json.dumps(event)
    assert event["event"] == "database_seed_failed"
    assert event["stage"] == "configure_runtime_role"
    assert event["sqlstate"] == "42501"
    assert "pagos_runtime" not in serialized
    assert "hunter2" not in serialized
    assert "unsafe fallback" not in serialized


def test_seed_settings_requires_strong_runtime_password() -> None:
    with pytest.raises(ValidationError):
        SeedSettings(
            database_admin_url="postgresql://admin:test-password@postgres:5432/postgres",
            runtime_db_password="too-short",
        )


def test_seed_failure_does_not_print_connection_details(monkeypatch, capsys) -> None:
    secret_url = "postgresql://admin:do-not-print-this@postgres:5432/postgres"
    monkeypatch.setenv("DATABASE_ADMIN_URL", secret_url)
    monkeypatch.delenv("RUNTIME_DB_PASSWORD", raising=False)

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert json.loads(captured.err)["event"] == "database_seed_failed"
    assert secret_url not in captured.err
