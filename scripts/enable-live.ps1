Param()

Write-Host "WARNING: You are about to enable live trading. This will allow the platform to place real orders on Coinbase."
$confirm = Read-Host "Type YES to confirm"

if ($confirm -ne "YES") {
    Write-Host "Live trading not enabled."
    exit 1
}

if (Test-Path ".env") {
    $content = Get-Content .env
    $updated = $false
    $newContent = @()
    foreach ($line in $content) {
        if ($line -match '^LIVE_TRADING_DEFAULT=') {
            $newContent += 'LIVE_TRADING_DEFAULT=true'
            $updated = $true
        } else {
            $newContent += $line
        }
    }
    if (-not $updated) {
        $newContent += 'LIVE_TRADING_DEFAULT=true'
    }
    $newContent | Set-Content .env
    Write-Host "LIVE_TRADING_DEFAULT set to true in .env."
} else {
    'LIVE_TRADING_DEFAULT=true' | Set-Content .env
    Write-Host "Created .env and set LIVE_TRADING_DEFAULT=true."
}

Write-Host "Live trading has been enabled. Make sure you understand the risks before proceeding."
