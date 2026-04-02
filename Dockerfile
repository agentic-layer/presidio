FROM python:3.13-slim

ENV UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /usr/local/bin/uv

RUN useradd -m -u 1001 presidio \
  && chown 1001:1001 /app

USER 1001

COPY --chown=1001:1001 pyproject.toml uv.lock /app/

RUN uv sync --frozen --no-dev --no-cache

COPY --chown=1001:1001 conf/ /app/conf/
COPY --chown=1001:1001 app.py logging.ini /app/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

ENTRYPOINT [".venv/bin/gunicorn", "-b", "0.0.0.0:8000", "app:create_app()"]
