FROM python:3.13-slim

ENV UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock /app/

RUN uv sync --frozen --no-dev

COPY conf/ /app/conf/
COPY app.py logging.ini /app/

RUN useradd -m -u 1001 presidio && chown -R presidio:presidio /app
USER 1001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=5 \
    CMD curl -f "http://localhost:8000/health" || exit 1

ENTRYPOINT ["uv", "run", "gunicorn", "app:create_app()"]
