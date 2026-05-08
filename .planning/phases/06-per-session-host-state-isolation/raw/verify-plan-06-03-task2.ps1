$ErrorActionPreference = 'Stop'
$f = '.planning/phases/06-per-session-host-state-isolation/06-03-SUMMARY.md'
if (-not (Test-Path $f)) { Write-Host "MISSING SUMMARY"; exit 1 }
$c = Get-Content $f -Raw
if ($c -notmatch '## ROADMAP success criteria' -or $c -notmatch 'CD-02' -or $c -notmatch 'isol-03-run.txt') {
    Write-Host "STRUCTURE FAIL (sections)"
    exit 1
}
uv run pytest tests/test_isolation.py --collect-only -q
if ($LASTEXITCODE -ne 0) { Write-Host "PYTEST COLLECT FAIL"; exit 1 }
Write-Host "TASK 2 VERIFY GATE: PASS"
exit 0
