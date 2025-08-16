#!/usr/bin/env bash
set -euo pipefail

# Create a new .env file from the provided template if it does not exist
if [ ! -f ".env" ]; then
  echo "Creating .env from .env.example..."
  cp .env.example .env
  echo "Please review the .env file and populate your API keys and secrets."
else
  echo ".env already exists.  Skipping bootstrap."
fi
