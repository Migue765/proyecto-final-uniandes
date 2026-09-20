import json
from typing import Any

import pytest
from pydantic import SecretStr, ValidationError

from app.seed import (
    RUNTIME_ROLE,
    UPSERT_PROFILES,
    SeedSettings,
    SeedStageError,
    _failure_event,
    configure_runtime_role,
    main,
    seed_database,
)


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
        'permission denied for role "solventa_runtime"; password=hunter2; '
        "postgresql://admin:do-not-log@example.invalid/solventa " + ("x" * 300)
    )


class FakeDatabaseError(Exception):
    sqlstate = "42501"
    diag = FakeDiagnostic()


class FakePgConnection:
    def __init__(self) -> None:
        self.encrypt_calls = 0

    def encrypt_password(self, password: bytes, user: bytes, algorithm: bytes) -> bytes:
        assert password
        assert user == b"solventa_runtime"
        assert algorithm == b"scram-sha-256"
        self.encrypt_calls += 1
        return b"SCRAM-SHA-256$4096:synthetic$safe-verifier"


class FakeConnection:
    def __init__(
        self,
        *,
        role_exists: bool = False,
        privileged_role: bool = False,
    ) -> None:
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
            return FakeResult(("solventa",))
        return FakeResult()


def rendered_statements(connection: FakeConnection) -> list[str]:
    return [str(query) for query, _ in connection.executions]


def test_seed_is_idempotent_and_configures_read_only_runtime_role() -> None:
    connection = FakeConnection()
    plaintext_password = "a-runtime-password-with-24-chars"

    seed_database(
        connection,
        profiles_per_partner=100,
        runtime_db_user=RUNTIME_ROLE,
        runtime_db_password=SecretStr(plaintext_password),
    )

    assert connection.executions[3] == (UPSERT_PROFILES, (100,))
    assert "ON CONFLICT" in connection.executions[2][0]
    assert "ON CONFLICT" in connection.executions[3][0]
    assert "partner_number * 100 + profile_number" in UPSERT_PROFILES
    assert UPSERT_PROFILES.count("MOD(") == 4
    assert "%" not in UPSERT_PROFILES.replace("%s", "")
    statements = rendered_statements(connection)
    assert any("CREATE ROLE" in statement for statement in statements)
    assert any(
        "REVOKE CONNECT, TEMPORARY ON DATABASE" in statement and "PUBLIC" in statement
        for statement in statements
    )
    assert any(
        "REVOKE ALL PRIVILEGES ON SCHEMA public FROM PUBLIC" in statement
        for statement in statements
    )
    assert any("GRANT SELECT ON TABLE" in statement for statement in statements)
    assert any("default_transaction_read_only" in statement for statement in statements)
    assert not any("GRANT INSERT" in statement for statement in statements)
    assert not any("GRANT UPDATE" in statement for statement in statements)
    assert connection.pgconn.encrypt_calls == 1
    assert not any(plaintext_password in statement for statement in statements)
    assert any("SCRAM-SHA-256" in statement for statement in statements)


def test_existing_runtime_role_is_rotated_without_recreation() -> None:
    connection = FakeConnection(role_exists=True)

    configure_runtime_role(
        connection,
        RUNTIME_ROLE,
        SecretStr("another-runtime-password-24"),
    )

    statements = rendered_statements(connection)
    assert not any("CREATE ROLE" in statement for statement in statements)
    assert any("ALTER ROLE" in statement for statement in statements)
    assert not any("NOSUPERUSER" in statement for statement in statements)
    assert not any("NOREPLICATION" in statement for statement in statements)


def test_existing_privileged_or_owner_runtime_role_is_rejected() -> None:
    connection = FakeConnection(role_exists=True, privileged_role=True)

    with pytest.raises(RuntimeError, match="forbidden privileges"):
        configure_runtime_role(
            connection,
            RUNTIME_ROLE,
            SecretStr("another-runtime-password-24"),
        )

    assert not any("ALTER ROLE" in statement for statement in rendered_statements(connection))


def test_failure_event_reports_stage_and_sqlstate_without_sensitive_data() -> None:
    event = _failure_event(
        "seed_transaction",
        SeedStageError("configure_runtime_role", FakeDatabaseError("unsafe fallback")),
    )

    serialized = json.dumps(event)
    assert event["event"] == "database_seed_failed"
    assert event["stage"] == "configure_runtime_role"
    assert event["error_type"] == "FakeDatabaseError"
    assert event["sqlstate"] == "42501"
    assert len(event["message_primary"]) <= 160
    assert "solventa_runtime" not in serialized
    assert "hunter2" not in serialized
    assert "do-not-log" not in serialized
    assert "unsafe fallback" not in serialized


def test_seed_rejects_any_runtime_role_name_other_than_fixed_role() -> None:
    with pytest.raises(ValueError):
        configure_runtime_role(
            FakeConnection(),
            "attacker_controlled_role",
            SecretStr("another-runtime-password-24"),
        )


def test_seed_settings_fix_profile_universe_to_one_hundred() -> None:
    with pytest.raises(ValidationError):
        SeedSettings(
            database_admin_url=(
                "postgresql://admin:test-password@postgres:5432/solventa"
            ),
            runtime_db_password="another-runtime-password-24",
            profiles_per_partner=101,
        )


def test_seed_failure_does_not_print_connection_details(monkeypatch, capsys) -> None:
    secret_url = "postgresql://admin:do-not-print-this@postgres:5432/solventa"
    monkeypatch.setenv("DATABASE_ADMIN_URL", secret_url)
    monkeypatch.delenv("RUNTIME_DB_PASSWORD", raising=False)

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "event": "database_seed_failed",
        "stage": "configuration",
        "error_type": "RuntimeError",
        "sqlstate": "none",
        "message_primary": "unavailable",
    }
    assert secret_url not in captured.err
