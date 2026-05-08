$f = '.planning/phases/06-per-session-host-state-isolation/06-keyring-recon.md'
$c = Get-Content $f -Raw
if ($c -notmatch '## 2\. cmdkey before/after diff') { Write-Host 'FAIL: section 2 missing'; exit 1 }
if ($c -notmatch 'Procedure') { Write-Host 'FAIL: Procedure missing'; exit 1 }
if ($c -notmatch 'cmdkey /list') { Write-Host 'FAIL: cmdkey /list missing'; exit 1 }
if ($c -notmatch 'Diff result') { Write-Host 'FAIL: Diff result missing'; exit 1 }
if ($c -notmatch 'Caveats') { Write-Host 'FAIL: Caveats missing'; exit 1 }
$d = '.planning/phases/06-per-session-host-state-isolation/raw/keyring-diff.txt'
if (-not (Test-Path $d)) { Write-Host 'FAIL: keyring-diff.txt missing'; exit 1 }
# Confirm no new pytest test file created (D-03 enforcement)
$keyringTests = Get-ChildItem -Path tests -Filter 'test_keyring*.py' -ErrorAction SilentlyContinue
if ($keyringTests) { Write-Host "FAIL: D-03 violated -- new test file found: $keyringTests"; exit 1 }
Write-Host 'PASS'
exit 0
