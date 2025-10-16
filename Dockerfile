FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Herramientas básicas de build (sin binarios pesados)
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash git build-essential ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiamos metadata y fuentes ANTES de instalar
COPY pyproject.toml /app/
COPY README.md /app/

# Prepara pip y wheel; instala el paquete en editable
RUN pip install -U pip setuptools wheel

# 1) Instalar el paquete en editable (runtime deps)
RUN pip install --no-cache-dir -e .

# 2) Instalar extras de desarrollo aparte
RUN pip install --no-cache-dir .[dev]

CMD ["bash"]
