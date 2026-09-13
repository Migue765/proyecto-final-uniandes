"""Idempotent PostgreSQL schema and synthetic-data bootstrap.

Run non-interactively from this image with ``python -m app.seed``.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Literal

import psycopg
from psycopg import sql
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
)

from .config import validate_database_url


RUNTIME_ROLE = "solventa_runtime"
_SEED_LOCK_ID = 2_026_091_200


class SeedSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    database_admin_url: SecretStr = Field(min_length=1)
    runtime_db_user: Literal["solventa_runtime"] = RUNTIME_ROLE
    runtime_db_password: SecretStr = Field(min_length=24, max_length=256)
    profiles_per_partner: int = Field(default=100, ge=100, le=100)
    connect_timeout_seconds: int = Field(default=10, ge=1, le=60)

    @field_validator("database_admin_url")
    @classmethod
    def validate_admin_database_connection(cls, value: SecretStr) -> SecretStr:
        return validate_database_url(value)

    @classmethod
    def from_env(cls) -> "SeedSettings":
        try:
            return cls(
                database_admin_url=os.environ.get("DATABASE_ADMIN_URL", ""),
                runtime_db_user=os.environ.get("RUNTIME_DB_USER", RUNTIME_ROLE),
                runtime_db_password=os.environ.get("RUNTIME_DB_PASSWORD", ""),
                profiles_per_partner=os.environ.get("SEED_PROFILES_PER_PARTNER", "100"),
                connect_timeout_seconds=os.environ.get(
                    "DB_CONNECT_TIMEOUT_SECONDS", "10"
                ),
            )
        except ValidationError:
            raise RuntimeError("invalid database seed configuration") from None


CREATE_RATES = """
    CREATE TABLE IF NOT EXISTS partner_rates (
        partner_id VARCHAR(32) PRIMARY KEY,
        annual_rate NUMERIC(8, 6) NOT NULL CHECK (annual_rate > 0 AND annual_rate <= 1),
        fixed_fee NUMERIC(14, 2) NOT NULL CHECK (fixed_fee >= 0),
        version VARCHAR(32) NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
"""

CREATE_PROFILES = """
    CREATE TABLE IF NOT EXISTS synthetic_profiles (
        partner_id VARCHAR(32) NOT NULL,
        profile_id VARCHAR(64) NOT NULL,
        age SMALLINT NOT NULL CHECK (age BETWEEN 18 AND 100),
        monthly_income NUMERIC(14, 2) NOT NULL CHECK (monthly_income >= 0),
        debt_ratio NUMERIC(5, 4) NOT NULL CHECK (debt_ratio BETWEEN 0 AND 1),
        claims_count SMALLINT NOT NULL CHECK (claims_count BETWEEN 0 AND 100),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (partner_id, profile_id)
    )
"""

UPSERT_RATES = """
    INSERT INTO partner_rates (partner_id, annual_rate, fixed_fee, version)
    SELECT
        'partner-' || to_char(partner_number, 'FM00'),
        0.018000 + (partner_number * 0.000050),
        1500.00 + (partner_number * 10.00),
        'synthetic-v1'
    FROM generate_series(1, 50) AS partner_number
    ON CONFLICT (partner_id) DO UPDATE SET
        annual_rate = EXCLUDED.annual_rate,
        fixed_fee = EXCLUDED.fixed_fee,
        version = EXCLUDED.version,
        updated_at = CURRENT_TIMESTAMP
"""

UPSERT_PROFILES = """
    INSERT INTO synthetic_profiles (
        partner_id, profile_id, age, monthly_income, debt_ratio, claims_count
    )
    SELECT
        'partner-' || to_char(partner_number, 'FM00'),
        'profile-00000000-0000-4000-8000-' ||
            lpad((partner_number * 100 + profile_number)::text, 12, '0'),
        18 + ((partner_number * 7 + profile_number * 3) % 63),
        1800000.00 + ((partner_number * 110003 + profile_number * 7919) % 18200000),
        (((partner_number * 13 + profile_number * 17) % 8500)::numeric / 10000),
        ((partner_number + profile_number) % 6)
    FROM generate_series(1, 50) AS partner_number
    CROSS JOIN generate_series(1, %s) AS profile_number
    ON CONFLICT (partner_id, profile_id) DO UPDATE SET
        age = EXCLUDED.age,
        monthly_income = EXCLUDED.monthly_income,
        debt_ratio = EXCLUDED.debt_ratio,
        claims_count = EXCLUDED.claims_count,
        updated_at = CURRENT_TIMESTAMP
"""


def configure_runtime_role(
    connection: psycopg.Connection,
    runtime_db_user: str,
    runtime_db_password: SecretStr,
) -> None:
    """Create or rotate the fixed read-only role without logging its password."""

    if runtime_db_user != RUNTIME_ROLE:
        raise ValueError("unsupported runtime database role")

    connection.execute("SELECT pg_advisory_xact_lock(%s)", (_SEED_LOCK_ID,))
    role_exists = connection.execute(
        "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = %s",
        (runtime_db_user,),
    ).fetchone()
    role = sql.Identifier(runtime_db_user)
    if role_exists is None:
        connection.execute(sql.SQL("CREATE ROLE {} LOGIN").format(role))

    password_buffer = bytearray(runtime_db_password.get_secret_value().encode("utf-8"))
    encrypted_password: bytes | None = None
    try:
        encrypted_password = connection.pgconn.encrypt_password(
            bytes(password_buffer),
            runtime_db_user.encode("ascii"),
            algorithm=b"scram-sha-256",
        )
        connection.execute(
            sql.SQL(
                "ALTER ROLE {} WITH LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                "NOCREATEROLE NOINHERIT NOREPLICATION"
            ).format(role, sql.Literal(encrypted_password.decode("ascii")))
        )
    finally:
        password_buffer[:] = b"\x00" * len(password_buffer)
        del encrypted_password
    connection.execute(
        sql.SQL("ALTER ROLE {} SET default_transaction_read_only TO on").format(role)
    )

    database_row = connection.execute("SELECT current_database()").fetchone()
    if database_row is None:
        raise RuntimeError("database name unavailable")
    database = sql.Identifier(database_row[0])
    connection.execute(
        sql.SQL("REVOKE CONNECT, TEMPORARY ON DATABASE {} FROM PUBLIC").format(database)
    )
    connection.execute(sql.SQL("REVOKE ALL PRIVILEGES ON SCHEMA public FROM PUBLIC"))
    connection.execute(
        sql.SQL(
            "REVOKE ALL PRIVILEGES ON TABLE partner_rates, synthetic_profiles "
            "FROM PUBLIC"
        )
    )
    connection.execute(
        sql.SQL("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC")
    )
    connection.execute(
        sql.SQL("REVOKE CREATE, TEMPORARY ON DATABASE {} FROM {}").format(
            database, role
        )
    )
    connection.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(database, role)
    )
    connection.execute(
        sql.SQL("REVOKE ALL PRIVILEGES ON SCHEMA public FROM {}").format(role)
    )
    connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
    connection.execute(
        sql.SQL(
            "REVOKE ALL PRIVILEGES ON TABLE partner_rates, synthetic_profiles FROM {}"
        ).format(role)
    )
    connection.execute(
        sql.SQL("GRANT SELECT ON TABLE partner_rates, synthetic_profiles TO {}").format(
            role
        )
    )
    connection.execute(
        sql.SQL(
            "REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM {}"
        ).format(role)
    )


def seed_database(
    connection: psycopg.Connection,
    profiles_per_partner: int,
    runtime_db_user: str,
    runtime_db_password: SecretStr,
) -> None:
    with connection.transaction():
        connection.execute(CREATE_RATES)
        connection.execute(CREATE_PROFILES)
        connection.execute(UPSERT_RATES)
        connection.execute(UPSERT_PROFILES, (profiles_per_partner,))
        configure_runtime_role(connection, runtime_db_user, runtime_db_password)


def main() -> int:
    try:
        settings = SeedSettings.from_env()
        with psycopg.connect(
            settings.database_admin_url.get_secret_value(),
            connect_timeout=settings.connect_timeout_seconds,
        ) as connection:
            seed_database(
                connection,
                settings.profiles_per_partner,
                settings.runtime_db_user,
                settings.runtime_db_password,
            )
        sys.stdout.write(
            json.dumps(
                {
                    "event": "database_seed_completed",
                    "partners": 50,
                    "profiles": 50 * settings.profiles_per_partner,
                },
                separators=(",", ":"),
            )
            + "\n"
        )
        return 0
    except Exception:
        sys.stderr.write('{"event":"database_seed_failed"}\n')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
