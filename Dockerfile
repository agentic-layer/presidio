FROM python:3.13-slim

ENV WORKERS=1
ENV PORT=3000
ENV NLP_CONF_FILE=/app/conf/nlp.yaml
ENV ANALYZER_CONF_FILE=/app/conf/analyzer.yaml

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock /app/

RUN uv sync --frozen --no-dev

RUN uv run python -m spacy download en_core_web_lg \
    && uv run python -m spacy download de_core_news_lg

COPY conf/ /app/conf/
COPY app.py logging.ini /app/

RUN useradd -m -u 1001 presidio && chown -R presidio:presidio /app
USER 1001

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
    CMD curl -f "http://localhost:${PORT}/health" || exit 1

ENTRYPOINT ["sh", "-c", "uv run gunicorn -w ${WORKERS} -b 0.0.0.0:${PORT} 'app:create_app()'"]

