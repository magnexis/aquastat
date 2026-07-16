#!/usr/bin/env bash
set -euo pipefail

curl -sS "${AQUASTAT_BASE_URL:-http://localhost:8080}/api/v1/estimate?provider=aws&region=us-east-1&load_mw=2.5" \
  -H "X-API-Key: ${AQUASTAT_API_KEY:?AQUASTAT_API_KEY is required}"
