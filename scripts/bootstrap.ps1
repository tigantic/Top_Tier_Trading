Param()

if (-Not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    Write-Host "Please review the .env file and populate your API keys and secrets."
} else {
    Write-Host ".env already exists.  Skipping bootstrap."
}
