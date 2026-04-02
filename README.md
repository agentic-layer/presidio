# presidio

Docker images for presidio services, including German language modules

## Docker Image

The pre-built image is available on GitHub Container Registry:

```bash
docker pull ghcr.io/agentic-layer/presidio:latest
```

Available versions can be found at the [container registry](https://github.com/agentic-layer/presidio/pkgs/container/presidio).

### Running

```bash
docker run -p 8000:8000 ghcr.io/agentic-layer/presidio:latest
```

The server starts on `http://localhost:8000`.

### Custom Configuration

Mount your own config files to override the defaults:

```bash
docker run -p 8000:8000 \
  -v ./my-conf:/app/conf \
  ghcr.io/agentic-layer/presidio:latest
```

Or use environment variables to point to individual config files:

```bash
docker run -p 8000:8000 \
  -e ANALYZER_CONF_FILE=/app/conf/analyzer.yaml \
  -e NLP_CONF_FILE=/app/conf/nlp.yaml \
  -e RECOGNIZER_REGISTRY_CONF_FILE=/app/conf/recognizers.yaml \
  ghcr.io/agentic-layer/presidio:latest
```

### Health Check

The container includes a built-in health check on `http://localhost:8000/health`.

## Local Development

### Prerequisites

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

2. Install dependencies:
   ```bash
   uv sync
   ```

### Running

```bash
uv run app.py
```

The server starts on `http://localhost:8000`

### Configuration

The app uses config files from the `conf/` directory by default:

- `conf/analyzer.yaml` - supported languages and score threshold
- `conf/nlp.yaml` - spaCy model configuration and NER entity mapping
- `conf/recognizers.yaml` - recognizer registry configuration, including custom recognizers

Override with environment variables:

- `ANALYZER_CONF_FILE` - path to analyzer config
- `NLP_CONF_FILE` - path to NLP engine config
- `RECOGNIZER_REGISTRY_CONF_FILE` - path to recognizer registry config

### E2E Tests

With the server running locally, execute the end-to-end tests:

```bash
bash tests/e2e_test.sh
```

To run against a different host:

```bash
bash tests/e2e_test.sh http://localhost:8000
```
