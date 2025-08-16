#!/usr/bin/env bash
set -euo pipefail

# Tail logs from all services
docker compose logs -f --tail=100
