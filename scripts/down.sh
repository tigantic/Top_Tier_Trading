#!/usr/bin/env bash
set -euo pipefail

# Stop and remove containers
docker compose down --remove-orphans
