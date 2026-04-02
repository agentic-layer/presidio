#!/bin/bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"

echo "==> Testing analyzer with English text..."
if ! ANALYZE_EN=$(curl -sS -f -X POST "${BASE_URL}/analyze" \
    -H "Content-Type: application/json" \
    -d '{"text": "My name is John Smith and my email is john@example.com", "language": "en"}' 2>&1); then
    echo "ERROR: Analyzer request failed for English text:"
    echo "    $ANALYZE_EN"
    exit 1
fi
echo "    Result: $ANALYZE_EN"
if [ "$ANALYZE_EN" = "[]" ]; then
    echo "ERROR: Expected entities to be found in English text"
    exit 1
fi

echo "==> Testing analyzer with German text..."
if ! ANALYZE_DE=$(curl -sS -f -X POST "${BASE_URL}/analyze" \
    -H "Content-Type: application/json" \
    -d '{"text": "Meine E-Mail ist hans@beispiel.de", "language": "de"}' 2>&1); then
    echo "ERROR: Analyzer request failed for German text:"
    echo "    $ANALYZE_DE"
    exit 1
fi
echo "    Result: $ANALYZE_DE"
if [ "$ANALYZE_DE" = "[]" ]; then
    echo "ERROR: Expected entities to be found in German text"
    exit 1
fi

echo "==> Testing anonymizer..."
if ! ANONYMIZE_RESULT=$(curl -sS -f -X POST "${BASE_URL}/anonymize" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"My name is John Smith and my email is john@example.com\", \"analyzer_results\": ${ANALYZE_EN}}" 2>&1); then
    echo "ERROR: Anonymizer request failed:"
    echo "    $ANONYMIZE_RESULT"
    exit 1
fi
echo "    Result: $ANONYMIZE_RESULT"
if echo "$ANONYMIZE_RESULT" | grep -q "error"; then
    echo "ERROR: Anonymizer returned an error"
    exit 1
fi

echo "==> Testing supported entities for German..."
if ! ENTITIES_DE=$(curl -sS -f "${BASE_URL}/supportedentities?language=de" 2>&1); then
    echo "ERROR: Supported entities request failed:"
    echo "    $ENTITIES_DE"
    exit 1
fi
echo "    Supported entities (de): $ENTITIES_DE"

echo ""
echo "==> All tests passed!"
