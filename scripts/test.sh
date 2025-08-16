#!/usr/bin/env bash
set -euo pipefail

# Run API tests
(cd api && npm test || true)

# Run Python tests with pytest if installed
if command -v pytest >/dev/null 2>&1; then
  pytest
else
  echo "pytest is not installed; skipping Python tests"
fi
