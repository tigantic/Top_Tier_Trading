Param()

# Lint TypeScript code
try {
    Push-Location api
    npm run lint
    Pop-Location
} catch {
    Write-Host "TypeScript lint failed" -ForegroundColor Yellow
}

# Lint Python code with flake8 if available
if (Get-Command flake8 -ErrorAction SilentlyContinue) {
    flake8 workers/src, backtester/src
} else {
    Write-Host "flake8 is not installed; skipping Python linting"
}
