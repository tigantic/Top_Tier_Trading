#!/usr/bin/env bash
set -euo pipefail

#!/usr/bin/env bash
set -euo pipefail

# Run Alembic migrations up to the latest head revision.  The
# STATE_STORE_URI environment variable must be set to a valid
# SQLAlchemy URL (e.g. postgresql+asyncpg://user:pass@host:5432/db).

if [[ -z "${STATE_STORE_URI:-}" ]]; then
  echo "STATE_STORE_URI is not set; skipping migrations" >&2
  exit 0
fi

echo "Running database migrations via Alembic..."
python "$(dirname "$0")/migrate_db.py"
