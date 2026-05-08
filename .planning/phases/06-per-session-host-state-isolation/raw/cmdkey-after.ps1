$out = '.planning/phases/06-per-session-host-state-isolation/raw/keyring-after.txt'
"=== Windows Credential Manager (cmdkey /list) at $((Get-Date).ToString('o')) ===" | Out-File -FilePath $out -Encoding utf8
"NOTE: filtered to lines mentioning 'homelab' or 'mcp'" | Out-File -FilePath $out -Encoding utf8 -Append
cmdkey /list | Select-String -Pattern 'homelab|mcp' | ForEach-Object { $_.Line } | Out-File -FilePath $out -Encoding utf8 -Append
Write-Host "Wrote $out"
Get-Content $out | Select-Object -First 30

Write-Host ""
Write-Host "=== Diff (Compare-Object) ==="
$before = Get-Content '.planning/phases/06-per-session-host-state-isolation/raw/keyring-before.txt' | Where-Object { $_ -match '(Target|User):' }
$after = Get-Content $out | Where-Object { $_ -match '(Target|User):' }
$diff = Compare-Object -ReferenceObject $before -DifferenceObject $after
if ($null -eq $diff -or $diff.Count -eq 0) {
    "(empty diff -- before and after are identical for filtered Target/User lines)" | Out-File -FilePath '.planning/phases/06-per-session-host-state-isolation/raw/keyring-diff.txt' -Encoding utf8
    Write-Host "EMPTY DIFF (no changes)"
} else {
    $diff | Format-Table -AutoSize | Out-File -FilePath '.planning/phases/06-per-session-host-state-isolation/raw/keyring-diff.txt' -Encoding utf8
    Write-Host "DIFF FOUND:"
    $diff | Format-Table -AutoSize
}
