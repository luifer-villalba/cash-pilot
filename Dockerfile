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

RUN pip install -U pip setuptools wheel
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir .[dev]

CMD ["bash"]
