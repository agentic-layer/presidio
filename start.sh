#!/bin/sh
set -e

# Start anonymizer in background on port 5002
cd /app/anonymizer && gunicorn -w "${WORKERS:-1}" -b "0.0.0.0:${ANONYMIZER_PORT:-5002}" "app:create_app()" &

# Start analyzer in foreground on port 5001
cd /app/analyzer && exec gunicorn -w "${WORKERS:-1}" -b "0.0.0.0:${ANALYZER_PORT:-5001}" "app:create_app()"
