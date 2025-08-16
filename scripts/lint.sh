#!/usr/bin/env bash
set -euo pipefail

# Lint TypeScript code
(cd api && npm run lint || true)

# Lint Python code using flake8 if installed
if command -v flake8 >/dev/null 2>&1; then
  flake8 workers/src backtester/src || true
else
  echo "flake8 is not installed; skipping Python linting"
fi
