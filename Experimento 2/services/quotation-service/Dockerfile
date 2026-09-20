FROM python:3.11.16-slim-bookworm@sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

RUN apt-get update \
    && apt-get install --no-install-recommends --yes ca-certificates curl \
    && curl --proto '=https' --tlsv1.2 --fail --show-error --silent --location \
        --output /tmp/aws-rds-global-bundle.pem \
        https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
    && echo "e5bb2084ccf45087bda1c9bffdea0eb15ee67f0b91646106e466714f9de3c7e3  /tmp/aws-rds-global-bundle.pem" \
        | sha256sum --check --strict \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv "$VIRTUAL_ENV"
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
COPY --from=builder /tmp/aws-rds-global-bundle.pem /etc/ssl/certs/aws-rds-global-bundle.pem
COPY --chown=10001:10001 app ./app
COPY --chown=10001:10001 gunicorn.conf.py ./gunicorn.conf.py

USER 10001:10001
EXPOSE 8080
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app.wsgi:app"]
