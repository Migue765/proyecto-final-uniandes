"""Gunicorn entry point."""

from .application import create_app

app = create_app()
