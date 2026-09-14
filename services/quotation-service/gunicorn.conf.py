"""Gunicorn settings optimized for one worker per horizontally scaled pod."""

import os


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = int(os.environ.get(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


bind = f"0.0.0.0:{_bounded_int('PORT', 8080, 1, 65535)}"
workers = _bounded_int("WEB_CONCURRENCY", 1, 1, 32)
worker_class = "gthread"
threads = _bounded_int("GUNICORN_THREADS", 8, 1, 64)
timeout = _bounded_int("GUNICORN_TIMEOUT_SECONDS", 30, 1, 300)
graceful_timeout = _bounded_int("GUNICORN_GRACEFUL_TIMEOUT_SECONDS", 30, 1, 300)
keepalive = _bounded_int("GUNICORN_KEEPALIVE_SECONDS", 5, 1, 75)
accesslog = None
errorlog = "-"
capture_output = True
preload_app = False
