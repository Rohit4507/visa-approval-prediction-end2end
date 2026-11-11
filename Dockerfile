# Image for the FastAPI prediction service.
# PR 2 replaces this single-stage build with a multi-stage, non-root image.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY us_visa ./us_visa
COPY app.py template.py ./
COPY config ./config
COPY static ./static
COPY templates ./templates

RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

CMD ["uv", "run", "--frozen", "--no-dev", "python", "app.py"]
