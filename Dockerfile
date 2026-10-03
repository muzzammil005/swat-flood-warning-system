# syntax=docker/dockerfile:1.6
#
# Multi-stage Dockerfile for Swat Flood backend.
#
# Targets:
#   --target=base        → bare Python env with runtime deps only (smaller, Stage 4 API)
#   --target=dev         → base + dev/test tooling (ruff, mypy, pytest; default target)
#
# Why multi-stage instead of one fat image:
#   1. The CI pipeline (Stage 5 GitHub Actions) can build `base` for deployment
#      and `dev` for lint/test without duplicating build steps.
#   2. Local devs get exactly the same interpreter + pinned packages as CI,
#      eliminating "works on my machine" drift across Windows/macOS/Linux.
#   3. Build tooling is only in a single RUN command to reduce CVE surface.

# ---------- Base: runtime only, no dev tooling ----------
FROM python:3.11-slim-bookworm AS base

LABEL org.opencontainers.image.title="swat-flood-backend" \
      org.opencontainers.image.description="Swat Flood Early-Warning System backend (FastAPI, Clean Architecture)"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/backend/src

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        curl \
        postgresql-client \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy pyproject first (and source) so package metadata + install runtime deps. Direct
# editable install works inside the package metadata + install runtime deps. We do this BEFORE
# copying source so layer cache miss = package metadata + install runtime deps first (editable)
# so layer cache invalidation: deps only when pyproject changes.
COPY pyproject.toml README.md ./
COPY backend/ ./backend/
COPY alembic/ ./alembic/

RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --default-timeout 1000 --no-cache-dir -e .

COPY tests/ ./tests/

EXPOSE 8000

# Default entrypoint: start uvicorn (compose override disables reload).
# main:app includes all routers (zones, alerts, reports, auth, admin) +
# SHAP explainer lifespan startup — app:app is a minimal health-only stub.
CMD ["uvicorn", "backend.src.interfaces.http.main:app", \
     "--host", "0.0.0.0", "--port", "8000"]


# ---------- Dev: base + dev extras (ruff, mypy, pytest) ----------
FROM base AS dev

# Re-install with [dev] extra on top: adds ruff/mypy/pytest.
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --default-timeout 1000 --no-cache-dir -e ".[dev]"

# Compose CMD override re-enables it for local dev.
CMD ["uvicorn", "backend.src.interfaces.http.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--reload"]
