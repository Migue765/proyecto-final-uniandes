"""Solventa synthetic profile and scoring service."""

from __future__ import annotations

from typing import Any


def create_app(*args: Any, **kwargs: Any):
    """Import the Flask factory lazily to keep package imports side-effect free."""

    from .application import create_app as factory

    return factory(*args, **kwargs)


__all__ = ["create_app"]
