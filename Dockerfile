FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1
ENV WORKERS=1
ENV ANALYZER_PORT=5001
ENV ANONYMIZER_PORT=5002
ENV NLP_CONF_FILE=/app/conf/nlp.yaml
ENV ANALYZER_CONF_FILE=/app/conf/analyzer.yaml

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

RUN pip install \
    "presidio-analyzer[server]==2.2.362" \
    "presidio-anonymizer[server]==2.2.362"

RUN python -m spacy download en_core_web_lg \
    && python -m spacy download de_core_news_lg

COPY conf/ /app/conf/
COPY analyzer/ /app/analyzer/
COPY anonymizer/ /app/anonymizer/
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

RUN useradd -m -u 1001 presidio && chown -R presidio:presidio /app
USER 1001

EXPOSE ${ANALYZER_PORT}
EXPOSE ${ANONYMIZER_PORT}

HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
    CMD curl -f "http://localhost:${ANALYZER_PORT}/health" || exit 1

CMD ["/app/start.sh"]
