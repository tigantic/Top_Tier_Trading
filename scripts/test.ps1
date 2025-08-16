Param()

# Run API tests
try {
    Push-Location api
    npm test
    Pop-Location
} catch {
    Write-Host "API tests failed or not configured" -ForegroundColor Yellow
}

# Run Python tests with pytest if available
if (Get-Command pytest -ErrorAction SilentlyContinue) {
    pytest
} else {
    Write-Host "pytest is not installed; skipping Python tests"
}
