from typing import Any

import pytest
from pydantic import SecretStr, ValidationError

from app.seed import (
    RUNTIME_ROLE,
    UPSERT_PROFILES,
    SeedSettings,
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
    def __init__(self, *, role_exists: bool = False) -> None:
        self.role_exists = role_exists
        self.executions: list[tuple[Any, tuple[Any, ...] | None]] = []
        self.pgconn = FakePgConnection()

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(self, query: Any, params: tuple[Any, ...] | None = None) -> FakeResult:
        self.executions.append((query, params))
        if query == "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = %s":
            return FakeResult((1,) if self.role_exists else None)
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
    assert captured.err == '{"event":"database_seed_failed"}\n'
    assert secret_url not in captured.err
