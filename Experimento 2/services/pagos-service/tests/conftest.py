"""Test-only stand-ins for boto3/botocore/psycopg_pool (no network in this sandbox)."""

from __future__ import annotations

import sys
import types


def _install_stub(name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


boto3_stub = _install_stub("boto3")
if not hasattr(boto3_stub, "client"):
    def _unused_client(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("boto3.client must not be called directly in tests")

    boto3_stub.client = _unused_client  # type: ignore[attr-defined]

botocore_stub = _install_stub("botocore")
botocore_exceptions_stub = _install_stub("botocore.exceptions")
if not hasattr(botocore_exceptions_stub, "BotoCoreError"):

    class BotoCoreError(Exception):
        pass

    class ClientError(Exception):
        pass

    botocore_exceptions_stub.BotoCoreError = BotoCoreError  # type: ignore[attr-defined]
    botocore_exceptions_stub.ClientError = ClientError  # type: ignore[attr-defined]
botocore_stub.exceptions = botocore_exceptions_stub  # type: ignore[attr-defined]

botocore_config_stub = _install_stub("botocore.config")
if not hasattr(botocore_config_stub, "Config"):

    class Config:  # pragma: no cover - never inspected in tests
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

    botocore_config_stub.Config = Config  # type: ignore[attr-defined]
botocore_stub.config = botocore_config_stub  # type: ignore[attr-defined]

psycopg_pool_stub = _install_stub("psycopg_pool")
if not hasattr(psycopg_pool_stub, "ConnectionPool"):

    class ConnectionPool:  # pragma: no cover - never instantiated in tests
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError(
                "ConnectionPool must not be constructed directly in tests; "
                "inject a fake pool instead"
            )

    psycopg_pool_stub.ConnectionPool = ConnectionPool  # type: ignore[attr-defined]
