FROM python:3.11.16-slim-bookworm@sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-compile -r /tmp/requirements.txt

FROM python:3.11.16-slim-bookworm@sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

RUN groupadd --gid 10001 solventa \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin solventa

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=10001:10001 app ./app
COPY --chown=10001:10001 gunicorn.conf.py ./gunicorn.conf.py

USER 10001:10001
EXPOSE 8080
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app.wsgi:app"]
