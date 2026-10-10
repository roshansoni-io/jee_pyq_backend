# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies before copying source so code-only changes keep the
# dependency layer cached.
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home app

COPY --chown=app:app app ./app
COPY --chown=app:app scripts/download_sqlite.py ./scripts/download_sqlite.py

USER 10001:10001

# Bind host, port and worker count come from PYQ_HOST / PYQ_PORT /
# PYQ_WORKERS (see app/config.py, fed by the container env or .env).
CMD ["python", "-m", "app"]
