FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Pillow + OpenCV + torch native deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
        libwebp7 \
        libtiff6 \
        libfreetype6 \
        libpng16-16 \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
ARG TORCH_WHEEL_INDEX=https://download.pytorch.org/whl/cpu
# API uses CPU torch by default; the worker image overrides this with a CUDA wheel index.
RUN pip install --index-url ${TORCH_WHEEL_INDEX} "torch>=2.2" \
    && pip install -r requirements.txt

COPY api ./api
COPY models ./models
COPY services ./services
COPY worker ./worker
COPY alembic ./alembic
COPY alembic.ini ./

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
