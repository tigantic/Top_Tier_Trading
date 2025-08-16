Param()

if (-not $env:STATE_STORE_URI) {
    Write-Host "STATE_STORE_URI is not set; skipping migrations"
    exit 0
}
Write-Host "Running database migrations via Alembic..."
$scriptDir = Split-Path -Path $MyInvocation.MyCommand.Path
python (Join-Path $scriptDir 'migrate_db.py')
