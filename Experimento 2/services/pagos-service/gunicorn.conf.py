"""Gunicorn settings.

``workers`` is hard-pinned to 1 for the same reason as reclamos-service: the
consumer background thread is started once per process in ``create_app()``,
and replica count (via KEDA) is how this service scales, not in-pod worker
count.
"""

import os


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = int(os.environ.get(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


bind = f"0.0.0.0:{_bounded_int('PORT', 8080, 1, 65535)}"
workers = 1
worker_class = "gthread"
threads = _bounded_int("GUNICORN_THREADS", 8, 1, 64)
timeout = _bounded_int("GUNICORN_TIMEOUT_SECONDS", 30, 1, 300)
graceful_timeout = _bounded_int("GUNICORN_GRACEFUL_TIMEOUT_SECONDS", 30, 1, 300)
keepalive = _bounded_int("GUNICORN_KEEPALIVE_SECONDS", 5, 1, 75)
accesslog = None
errorlog = "-"
capture_output = True
preload_app = False
