Param(
    [string]$Strategy = "ma_crossover",
    [string]$StartDate = "2023-01-01T00:00:00Z",
    [string]$EndDate = "2023-12-31T23:59:59Z"
)

Write-Host "Running backtest for strategy $Strategy from $StartDate to $EndDate..."
docker compose run --rm backtester python -m backtester.backtester_main $Strategy $StartDate $EndDate
