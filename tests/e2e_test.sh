#!/bin/bash
set -euo pipefail

export IMG="${1:-ghcr.io/agentic-layer/presidio:test}"
PORT=3000
COMPOSE_FILE="$(dirname "$0")/compose.yml"

echo "==> Starting service from image: $IMG"
docker compose -f "$COMPOSE_FILE" up -d

cleanup() {
    echo "==> Stopping service"
    docker compose -f "$COMPOSE_FILE" down
}
trap cleanup EXIT

echo "==> Waiting for service to be healthy..."
docker compose -f "$COMPOSE_FILE" wait presidio

echo "==> Testing analyzer with English text..."
ANALYZE_EN=$(curl -sf -X POST "http://localhost:${PORT}/analyze" \
    -H "Content-Type: application/json" \
    -d '{"text": "My name is John Smith and my email is john@example.com", "language": "en"}')
echo "    Result: $ANALYZE_EN"
if [ "$ANALYZE_EN" = "[]" ]; then
    echo "ERROR: Expected entities to be found in English text"
    exit 1
fi

echo "==> Testing analyzer with German text..."
ANALYZE_DE=$(curl -sf -X POST "http://localhost:${PORT}/analyze" \
    -H "Content-Type: application/json" \
    -d '{"text": "Meine E-Mail ist hans@beispiel.de", "language": "de"}')
echo "    Result: $ANALYZE_DE"
if [ "$ANALYZE_DE" = "[]" ]; then
    echo "ERROR: Expected entities to be found in German text"
    exit 1
fi

echo "==> Testing anonymizer..."
ANONYMIZE_RESULT=$(curl -sf -X POST "http://localhost:${PORT}/anonymize" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"My name is John Smith and my email is john@example.com\", \"analyzer_results\": ${ANALYZE_EN}}")
echo "    Result: $ANONYMIZE_RESULT"
if echo "$ANONYMIZE_RESULT" | grep -q "error"; then
    echo "ERROR: Anonymizer returned an error"
    exit 1
fi

echo "==> Testing supported entities for German..."
ENTITIES_DE=$(curl -sf "http://localhost:${PORT}/supportedentities?language=de")
echo "    Supported entities (de): $ENTITIES_DE"

echo ""
echo "==> All tests passed!"

