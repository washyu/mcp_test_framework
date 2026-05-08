try {
    $r = Invoke-WebRequest -Uri 'https://pypi.org/pypi/homelab-mcp/json' -UseBasicParsing -TimeoutSec 30
    $j = $r.Content | ConvertFrom-Json
    Write-Host '=== Name ==='
    Write-Host $j.info.name
    Write-Host '=== Version ==='
    Write-Host $j.info.version
    Write-Host '=== Summary ==='
    Write-Host $j.info.summary
    Write-Host '=== Description (full) ==='
    Write-Host $j.info.description
    # Save full description to file for grepping
    $j.info.description | Out-File -FilePath '.planning/phases/06-per-session-host-state-isolation/raw/pypi-readme.txt' -Encoding utf8
    Write-Host ''
    Write-Host '=== Saved full README to raw/pypi-readme.txt ==='
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
    exit 1
}
