$f = '.planning/phases/06-per-session-host-state-isolation/06-keyring-recon.md'
if (-not (Test-Path $f)) { Write-Host 'FAIL: file missing'; exit 1 }
$c = Get-Content $f -Raw
if ($c -notmatch '## 1\. PyPI README evidence') { Write-Host 'FAIL: section 1 missing'; exit 1 }
if ($c -notmatch 'No homelab-mcp source files were read') { Write-Host 'FAIL: black-box sentence missing'; exit 1 }
if ($c -notmatch '\*\*Date:\*\* 2026-05-07') { Write-Host 'FAIL: date missing'; exit 1 }
if ($c -notmatch '\*\*Method:\*\*') { Write-Host 'FAIL: method missing'; exit 1 }
Write-Host 'PASS'
exit 0
