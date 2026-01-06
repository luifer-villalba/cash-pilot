# ─── Stage 1: Build CSS ───
FROM node:20-alpine AS css-builder

WORKDIR /app

# Pin npm to a specific version for reproducible builds and to stay
# consistent with the existing Node.js build tooling in this project.
RUN npm install -g npm@11.7.0

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy config and source files
# Note: In this project, Tailwind v4 requires tailwind.config.js
# to define explicit content paths and safelist patterns
# so that class generation is reliable, including for dynamic content.
COPY tailwind.config.js postcss.config.js ./
COPY static/css/input.css ./static/css/
COPY templates ./templates
COPY static/js ./static/js

# Build CSS
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

# Copy static files BEFORE CSS to preserve directory structure
COPY static/ ./static/

# Copy compiled CSS WITHOUT overwriting entire directory
COPY --from=css-builder /app/static/css/main.css /app/static/css/main.css

# VERIFY: Ensure all static files exist at build time
RUN echo "=== Static Files Verification ===" && \
    ls -la /app/static/ && \
    echo "" && \
    echo "JS files:" && \
    ls -la /app/static/js/ && \
    echo "" && \
    echo "CSS files:" && \
    ls -la /app/static/css/ && \
    echo "" && \
    test -f /app/static/js/theme-toggle.js || (echo "❌ theme-toggle.js missing" && exit 1) && \
    test -f /app/static/js/form-navigation.js || (echo "❌ form-navigation.js missing" && exit 1) && \
    test -f /app/static/js/currency-formatter.js || (echo "❌ currency-formatter.js missing" && exit 1) && \
    test -f /app/static/css/main.css || (echo "❌ main.css missing" && exit 1) && \
    echo "✅ All static files verified successfully"

RUN pip install -U pip setuptools wheel
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir .[dev]

# Compile translations for production
RUN pybabel compile -d translations

CMD sh -c "alembic upgrade head && uvicorn cashpilot.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'"