# ─── Stage 1: Build CSS ───
FROM node:20-alpine AS css-builder

WORKDIR /app

RUN npm install -g npm@11.7.0

COPY package*.json ./
RUN npm ci

COPY tailwind.config.js postcss.config.js ./
COPY static/css/input.css ./static/css/
COPY templates ./templates
COPY static/js ./static/js

RUN npm run build:css

# ─── Stage 2: Python App ───
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    WATCHFILES_FORCE_POLLING=true

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash git build-essential ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml /app/
COPY README.md /app/
COPY src /app/src
COPY alembic.ini .
COPY alembic/ ./alembic/
COPY templates/ ./templates/
COPY translations/ ./translations/

# ✅ FIX: Copy static files BEFORE CSS to preserve directory structure
COPY static/ ./static/

# ✅ FIX: Copy compiled CSS WITHOUT overwriting entire directory
COPY --from=css-builder /app/static/css/main.css /app/static/css/main.css

RUN pip install -U pip setuptools wheel
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir .[dev]

RUN pybabel compile -d translations

CMD sh -c "alembic upgrade head && uvicorn cashpilot.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'"