#!/usr/bin/env bash
set -euo pipefail

# Build all Docker images
docker compose build --pull
