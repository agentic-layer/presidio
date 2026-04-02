# presidio

Docker images for presidio services, including German language modules

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
