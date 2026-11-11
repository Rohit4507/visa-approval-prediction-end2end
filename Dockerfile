# syntax=docker/dockerfile:1

###############################################################################
# Builder — resolve dependencies from uv.lock, then install the project
###############################################################################
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN pip install --no-cache-dir uv

# Dependencies are installed before the source is copied so that code-only
# changes reuse this layer instead of reinstalling 158 packages.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY us_visa ./us_visa
COPY app.py ./

# Install the project as a regular package (not editable) so the runtime stage
# needs nothing but the virtualenv.
RUN uv sync --frozen --no-dev --no-editable

###############################################################################
# Runtime — virtualenv + app assets only: no compilers, no package indexes,
# no root user.
###############################################################################
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    US_VISA_LOG_DIR=/app/logs

RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder --chown=10001:10001 /app/.venv /app/.venv
COPY --chown=10001:10001 app.py ./
COPY --chown=10001:10001 config ./config
COPY --chown=10001:10001 static ./static
COPY --chown=10001:10001 templates ./templates

RUN mkdir -p /app/logs /app/artifact \
    && chown -R 10001:10001 /app/logs /app/artifact

USER 10001:10001

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/', timeout=3).status == 200 else 1)"

CMD ["python", "app.py"]
