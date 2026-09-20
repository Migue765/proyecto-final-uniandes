"""Idempotent database creation, schema bootstrap and runtime-role setup.

Run non-interactively from this image with ``python -m app.seed``. Unlike
``quotation-service/app/seed.py`` (whose ``solventa`` database already
existed when the RDS instance was provisioned), the ``reclamos`` database
does not exist yet on the shared RDS instance the first time this runs, so
this module also issues the ``CREATE DATABASE`` statement itself, against the
instance's default ``postgres`` maintenance database, before touching
anything inside ``reclamos``.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

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
from .repository import _SCHEMA_STATEMENTS

RUNTIME_ROLE = "reclamos_runtime"
_TARGET_DATABASE = "reclamos"
_SEED_LOCK_ID = 2_026_091_201
_MAX_PRIMARY_MESSAGE_LENGTH = 160
_SQLSTATE_PATTERN = re.compile(r"^[0-9A-Z]{5}$")
_DUPLICATE_DATABASE_SQLSTATE = "42P04"
_URI_PATTERN = re.compile(r"(?i)\b(?:https?|postgres(?:ql)?|redis(?:s)?)://\S+")
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(?:password|passwd|secret|token)\s*[:=]\s*[^\s,;]+"
)
_IDENTITY_PATTERN = re.compile(r"(?i)\b(user|role)\s+(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)")

_RUNTIME_TABLES = ("reclamos_inbox", "siniestros", "outbox_ordenes_pagos")


class SeedStageError(RuntimeError):
    """Preserve a fixed seed stage without copying database error text."""

    def __init__(self, stage: str, cause: Exception) -> None:
        super().__init__("database seed stage failed")
        self.stage = stage
        self.cause = cause


def _sanitized_primary_message(error: Exception) -> str:
    diagnostic = getattr(error, "diag", None)
    message = getattr(diagnostic, "message_primary", None)
    if not isinstance(message, str) or not message.strip():
        return "unavailable"

    normalized = " ".join(
        "".join(character if character.isprintable() else " " for character in message).split()
    )
    normalized = _URI_PATTERN.sub("[redacted-url]", normalized)
    normalized = _SECRET_ASSIGNMENT_PATTERN.sub("credential=[redacted]", normalized)
    normalized = _IDENTITY_PATTERN.sub(r"\1 [redacted]", normalized)
    return normalized[:_MAX_PRIMARY_MESSAGE_LENGTH] or "unavailable"


def _failure_event(default_stage: str, error: Exception) -> dict[str, str]:
    stage = default_stage
    cause = error
    if isinstance(error, SeedStageError):
        stage = error.stage
        cause = error.cause

    sqlstate = getattr(cause, "sqlstate", None)
    if not isinstance(sqlstate, str) or not _SQLSTATE_PATTERN.fullmatch(sqlstate):
        sqlstate = "none"

    return {
        "event": "database_seed_failed",
        "stage": stage,
        "error_type": type(cause).__name__[:64] or "Exception",
        "sqlstate": sqlstate,
        "message_primary": _sanitized_primary_message(cause),
    }


def _with_database(url: str, database: str) -> str:
    """Return ``url`` pointed at a different database name, same credentials/host."""

    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{database}"))


class SeedSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    database_admin_url: SecretStr = Field(min_length=1)
    runtime_db_user: Literal["reclamos_runtime"] = RUNTIME_ROLE
    runtime_db_password: SecretStr = Field(min_length=24, max_length=256)
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
                connect_timeout_seconds=os.environ.get("DB_CONNECT_TIMEOUT_SECONDS", "10"),
            )
        except ValidationError:
            raise RuntimeError("invalid reclamos database seed configuration") from None


def create_database_if_missing(maintenance_url: str, connect_timeout: int) -> None:
    """Issue CREATE DATABASE outside a transaction; tolerate it already existing."""

    try:
        with psycopg.connect(
            maintenance_url, autocommit=True, connect_timeout=connect_timeout
        ) as connection:
            connection.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(_TARGET_DATABASE))
            )
    except psycopg.Error as error:
        if getattr(error, "sqlstate", None) != _DUPLICATE_DATABASE_SQLSTATE:
            raise


def configure_runtime_role(
    connection: psycopg.Connection,
    runtime_db_user: str,
    runtime_db_password: SecretStr,
) -> None:
    """Create or rotate a read-write role scoped to exactly this service's tables."""

    if runtime_db_user != RUNTIME_ROLE:
        raise ValueError("unsupported runtime database role")

    connection.execute("SELECT pg_advisory_xact_lock(%s)", (_SEED_LOCK_ID,))
    role_attributes = connection.execute(
        "SELECT "
        "role.rolsuper, "
        "role.rolreplication, "
        "role.rolbypassrls, "
        "EXISTS ("
        "SELECT 1 FROM pg_catalog.pg_auth_members membership "
        "WHERE membership.member = role.oid"
        "), "
        "EXISTS ("
        "SELECT 1 FROM pg_catalog.pg_database database "
        "WHERE database.datname = current_database() AND database.datdba = role.oid"
        "), "
        "EXISTS ("
        "SELECT 1 FROM pg_catalog.pg_namespace namespace "
        "WHERE namespace.nspowner = role.oid"
        "), "
        "EXISTS ("
        "SELECT 1 FROM pg_catalog.pg_class relation "
        "WHERE relation.relowner = role.oid"
        ") "
        "FROM pg_catalog.pg_roles role WHERE role.rolname = %s",
        (runtime_db_user,),
    ).fetchone()
    role = sql.Identifier(runtime_db_user)
    if role_attributes is None:
        connection.execute(sql.SQL("CREATE ROLE {} LOGIN").format(role))
    elif any(role_attributes):
        raise RuntimeError("runtime database role has forbidden privileges")

    password_buffer = bytearray(runtime_db_password.get_secret_value().encode("utf-8"))
    encrypted_password: bytes | None = None
    try:
        encrypted_password = connection.pgconn.encrypt_password(
            bytes(password_buffer), runtime_db_user.encode("ascii"), algorithm=b"scram-sha-256"
        )
        connection.execute(
            sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {} NOCREATEDB NOCREATEROLE NOINHERIT").format(
                role, sql.Literal(encrypted_password.decode("ascii"))
            )
        )
    finally:
        password_buffer[:] = b"\x00" * len(password_buffer)
        del encrypted_password

    database_row = connection.execute("SELECT current_database()").fetchone()
    if database_row is None:
        raise RuntimeError("database name unavailable")
    database = sql.Identifier(database_row[0])
    table_list = sql.SQL(", ").join(sql.Identifier(name) for name in _RUNTIME_TABLES)

    connection.execute(sql.SQL("REVOKE CONNECT, TEMPORARY ON DATABASE {} FROM PUBLIC").format(database))
    connection.execute(sql.SQL("REVOKE ALL PRIVILEGES ON SCHEMA public FROM PUBLIC"))
    connection.execute(sql.SQL("REVOKE ALL PRIVILEGES ON TABLE {} FROM PUBLIC").format(table_list))
    connection.execute(sql.SQL("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC"))
    connection.execute(sql.SQL("REVOKE CREATE, TEMPORARY ON DATABASE {} FROM {}").format(database, role))

    connection.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(database, role))
    connection.execute(sql.SQL("REVOKE ALL PRIVILEGES ON SCHEMA public FROM {}").format(role))
    connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
    connection.execute(sql.SQL("REVOKE ALL PRIVILEGES ON TABLE {} FROM {}").format(table_list, role))
    connection.execute(
        sql.SQL("GRANT SELECT, INSERT, UPDATE ON TABLE {} TO {}").format(table_list, role)
    )
    connection.execute(
        sql.SQL("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM {}").format(role)
    )
    connection.execute(
        sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(role)
    )


def seed_database(
    connection: psycopg.Connection,
    runtime_db_user: str,
    runtime_db_password: SecretStr,
) -> None:
    try:
        with connection.transaction():
            for index, statement in enumerate(_SCHEMA_STATEMENTS):
                try:
                    connection.execute(statement)
                except Exception as error:
                    raise SeedStageError(f"create_schema_{index}", error) from error
            try:
                configure_runtime_role(connection, runtime_db_user, runtime_db_password)
            except Exception as error:
                raise SeedStageError("configure_runtime_role", error) from error
    except SeedStageError:
        raise
    except Exception as error:
        raise SeedStageError("seed_transaction", error) from error


def main() -> int:
    stage = "configuration"
    try:
        settings = SeedSettings.from_env()
        stage = "create_database"
        create_database_if_missing(
            settings.database_admin_url.get_secret_value(), settings.connect_timeout_seconds
        )
        stage = "database_connection"
        target_admin_url = _with_database(
            settings.database_admin_url.get_secret_value(), _TARGET_DATABASE
        )
        with psycopg.connect(
            target_admin_url, connect_timeout=settings.connect_timeout_seconds
        ) as connection:
            stage = "seed_transaction"
            seed_database(connection, settings.runtime_db_user, settings.runtime_db_password)
        sys.stdout.write(
            json.dumps({"event": "database_seed_completed", "database": _TARGET_DATABASE}, separators=(",", ":"))
            + "\n"
        )
        return 0
    except Exception as error:
        sys.stderr.write(
            json.dumps(_failure_event(stage, error), separators=(",", ":"), ensure_ascii=True) + "\n"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
