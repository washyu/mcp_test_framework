$out = '.planning/phases/06-per-session-host-state-isolation/raw/keyring-before.txt'
"=== Windows Credential Manager (cmdkey /list) at $((Get-Date).ToString('o')) ===" | Out-File -FilePath $out -Encoding utf8
"NOTE: filtered to lines mentioning 'homelab' or 'mcp'" | Out-File -FilePath $out -Encoding utf8 -Append
cmdkey /list | Select-String -Pattern 'homelab|mcp' | ForEach-Object { $_.Line } | Out-File -FilePath $out -Encoding utf8 -Append
Write-Host "Wrote $out"
Get-Content $out | Select-Object -First 30
