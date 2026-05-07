$ErrorActionPreference = 'Stop'
$f = 'tests/test_isolation.py'
if (-not (Test-Path $f)) { Write-Host "MISSING FILE"; exit 1 }
$c = Get-Content $f -Raw
$structure_checks = @(
    'from __future__ import annotations',
    'import hashlib',
    [regex]::Escape('pytestmark = [pytest.mark.asyncio(loop_scope="session")]'),
    'def _sha256_of',
    'async def test_real_state_unchanged',
    'pytest.skip',
    [regex]::Escape('(_isolated_home / ".homelab_mcp").exists()')
)
foreach ($pat in $structure_checks) {
    if ($c -notmatch $pat) {
        Write-Host "STRUCTURE FAIL: missing $pat"
        exit 1
    }
}
if ($c -match 'import\s+homelab_mcp' -or $c -match 'from\s+homelab_mcp') {
    Write-Host 'BLACK BOX VIOLATION'
    exit 1
}
if ($c -match 'import\s+subprocess' -or $c -match 'subprocess\.run' -or $c -match 'subprocess\.Popen') {
    Write-Host 'D-10 VIOLATION'
    exit 1
}
if ($c -match 'st_mtime' -or $c -match 'getmtime') {
    Write-Host 'D-09 VIOLATION'
    exit 1
}
uv run ruff check tests/test_isolation.py
if ($LASTEXITCODE -ne 0) { Write-Host "RUFF FAIL"; exit 1 }
uv run python -c "import ast; ast.parse(open('tests/test_isolation.py').read())"
if ($LASTEXITCODE -ne 0) { Write-Host "AST FAIL"; exit 1 }
Write-Host "PLAN VERIFY GATE: PASS"
exit 0
