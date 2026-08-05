FROM python:3.12-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.lock /tmp/requirements.lock
RUN pip install --require-hashes -r /tmp/requirements.lock

FROM builder AS test

COPY backend/requirements-dev.lock /tmp/requirements-dev.lock
RUN pip install --require-hashes -r /tmp/requirements-dev.lock

WORKDIR /app
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/tests ./tests
COPY backend/blackbox_tests ./blackbox_tests
COPY evals ./evals

ENTRYPOINT []
CMD ["pytest", "-q"]

FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system journey && useradd --system --gid journey --home /app journey

COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=journey:journey backend/alembic.ini ./alembic.ini
COPY --chown=journey:journey backend/alembic ./alembic
COPY --chown=journey:journey backend/app ./app
COPY --chown=journey:journey infra/docker/api-entrypoint.sh /usr/local/bin/api-entrypoint

RUN chmod 0555 /usr/local/bin/api-entrypoint
USER journey
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/health/live', timeout=2)"]

ENTRYPOINT ["api-entrypoint"]
