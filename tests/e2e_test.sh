#!/bin/bash
set -euo pipefail

IMG="${1:-ghcr.io/agentic-layer/presidio:test}"
ANALYZER_PORT=5001
ANONYMIZER_PORT=5002

echo "==> Starting container from image: $IMG"
CONTAINER_ID=$(docker run -d \
    -p "${ANALYZER_PORT}:${ANALYZER_PORT}" \
    -p "${ANONYMIZER_PORT}:${ANONYMIZER_PORT}" \
    "$IMG")

cleanup() {
    echo "==> Stopping container $CONTAINER_ID"
    docker stop "$CONTAINER_ID" > /dev/null 2>&1 || true
    docker rm "$CONTAINER_ID" > /dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> Waiting for analyzer to be ready on port $ANALYZER_PORT..."
for i in $(seq 1 60); do
    if curl -sf "http://localhost:${ANALYZER_PORT}/health" > /dev/null 2>&1; then
        echo "    Analyzer is up!"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "ERROR: Analyzer did not start in time"
        docker logs "$CONTAINER_ID"
        exit 1
    fi
    sleep 3
done

echo "==> Waiting for anonymizer to be ready on port $ANONYMIZER_PORT..."
for i in $(seq 1 60); do
    if curl -sf "http://localhost:${ANONYMIZER_PORT}/health" > /dev/null 2>&1; then
        echo "    Anonymizer is up!"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "ERROR: Anonymizer did not start in time"
        docker logs "$CONTAINER_ID"
        exit 1
    fi
    sleep 3
done

echo "==> Testing analyzer with English text..."
ANALYZE_EN=$(curl -sf -X POST "http://localhost:${ANALYZER_PORT}/analyze" \
    -H "Content-Type: application/json" \
    -d '{"text": "My name is John Smith and my email is john@example.com", "language": "en"}')
echo "    Result: $ANALYZE_EN"
if [ "$ANALYZE_EN" = "[]" ]; then
    echo "ERROR: Expected entities to be found in English text"
    exit 1
fi

echo "==> Testing analyzer with German text..."
ANALYZE_DE=$(curl -sf -X POST "http://localhost:${ANALYZER_PORT}/analyze" \
    -H "Content-Type: application/json" \
    -d '{"text": "Meine E-Mail ist hans@beispiel.de", "language": "de"}')
echo "    Result: $ANALYZE_DE"
if [ "$ANALYZE_DE" = "[]" ]; then
    echo "ERROR: Expected entities to be found in German text"
    exit 1
fi

echo "==> Testing anonymizer..."
ANONYMIZE_RESULT=$(curl -sf -X POST "http://localhost:${ANONYMIZER_PORT}/anonymize" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"My name is John Smith and my email is john@example.com\", \"analyzer_results\": ${ANALYZE_EN}}")
echo "    Result: $ANONYMIZE_RESULT"
if echo "$ANONYMIZE_RESULT" | grep -q "error"; then
    echo "ERROR: Anonymizer returned an error"
    exit 1
fi

echo "==> Testing supported entities for German..."
ENTITIES_DE=$(curl -sf "http://localhost:${ANALYZER_PORT}/supportedentities?language=de")
echo "    Supported entities (de): $ENTITIES_DE"

echo ""
echo "==> All tests passed!"
