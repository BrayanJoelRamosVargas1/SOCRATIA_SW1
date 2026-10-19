FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements-local-voice.txt ./
ARG INSTALL_LOCAL_VOICE=false
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$INSTALL_LOCAL_VOICE" = "true" ]; then pip install --no-cache-dir -r requirements-local-voice.txt; fi

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY scripts ./scripts

# -------- Normal Backend Stage --------
FROM base AS backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# -------- ML Backend Stage --------
FROM base AS backend-ml

COPY requirements-local-embeddings.txt ./
RUN pip install --no-cache-dir -r requirements-local-embeddings.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Precache model (optional during build)
ARG PRELOAD_MODEL=false
ENV E5_MODEL_NAME=intfloat/multilingual-e5-base
ENV E5_MODEL_REVISION=d128750597153bb5987e10b1c3493a34e5a4502a
RUN if [ "$PRELOAD_MODEL" = "true" ]; then python -m app.cli.preload_embedding_model; else echo "Skipping preload"; fi

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
