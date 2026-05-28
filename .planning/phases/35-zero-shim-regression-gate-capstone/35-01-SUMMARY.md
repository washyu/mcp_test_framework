---
phase: 35-zero-shim-regression-gate-capstone
plan: "01"
subsystem: testing/regression-gate
tags: [shim-retirement, regression-gate, static-analysis, ast, behavioral-probe, v1.5-capstone]
dependency_graph:
  requires: [phases/31-config-surface-cleanup, phases/32-surface-shim-removals-cli-package-fixtures-discovery]
  provides: [SHIM-09 cross-surface zero-shim regression gate]
  affects: [tests/framework/]
tech_stack:
  added: []
  patterns: [ast.walk behavioral probe, typer.testing.CliRunner in-process, tomllib pyproject parse, importlib.import_module + sys.modules.pop]
key_files:
  created:
    - tests/framework/test_zero_shim_regression_gate.py
  modified:
    - tests/framework/test_sdet_rename_leak_gate.py
decisions:
  - "D-01: Behavioral-first probes — import raises, CLI exits 2, SystemExit 2, AST node absence, fixture pytest.fail bodies present; 'zero shims' = 'zero FUNCTIONAL shims'"
  - "D-02/D-07: No operator-tone message-text re-pinned; Phase 31/32 per-surface tests own those"
  - "D-03: AST backstop on config.py ONLY for MCPTF_CONFIG_FILE literal and alias='sdet' keyword checks (not _plugin.py)"
  - "D-08: No subprocess, no network, no shared fixtures; runtime 0.10s"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-28"
  tasks: 2
  files: 2
---

# Phase 35 Plan 01: Zero-Shim Regression Gate (SHIM-09) Summary

**One-liner:** Five-surface behavioral gate that pins zero FUNCTIONAL shims across import / CLI+console-script / config-AST / fixture-AST / discovery surfaces and fails loudly on reintroduction.

## What Was Built

### Task 1: Five-surface zero-shim regression gate (SHIM-09)

Created `tests/framework/test_zero_shim_regression_gate.py` with exactly five named test functions, no shared fixtures, no subprocess, no network. Runs in 0.10s.

**test_import_surface_shim_absent** (SHIM-01): `importlib.import_module("mcp_test_framework.sdet")` under `pytest.raises((ModuleNotFoundError, ImportError))`. Flips red if `sdet/__init__.py` re-exports symbols instead of raising.

**test_cli_surface_shims_reject** (SHIM-02/03/08): `CliRunner().invoke(app, ["run", "--sdet"])` asserts exit 2; `invoke(app, ["gen-sdet-classes"])` asserts exit 2; `_deprecated_script.main()` under `pytest.raises(SystemExit)` asserts code 2; `tomllib` parse of pyproject.toml asserts `mcp-test-framework` entry wires to `_deprecated_script`.

**test_config_surface_shims_absent** (SHIM-04/05): AST walk of `config.py` ONLY (not `_plugin.py`). Asserts no `Field(alias/validation_alias=..., "sdet")` keyword and no `"MCPTF_CONFIG_FILE"` string constant.

**test_fixture_surface_stubs_present** (SHIM-07): AST walk of `_plugin.py`. Asserts all six expected names (`config`, `judge`, `target_tool`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`) are `@pytest.fixture`-decorated functions whose bodies call `pytest.fail`. `client` is NOT in the set.

**test_discovery_surface_not_auto_collected** (SHIM-06): Glob asserts no `test_*.py` files in `tests/sdet/`; substring check asserts the warn-detector string `"tests/sdet/ is no longer auto-discovered as of v1.5"` survives in `_plugin.py` source.

### Task 2: Docstring fix in RENAME-06 gate (D-06)

Replaced stale line 4 of `tests/framework/test_sdet_rename_leak_gate.py` docstring from:
```
Removed in v1.5 when the deprecation shims drop and the gate becomes a no-op.
```
to:
```
Survives v1.5 — the grandfathered hard-reject intercepts keep the # noqa: sdet-rename-shim exclusions live until the v1.6 clean-delete.
```
No behavior change. RENAME-06 gate still passes (4/4).

## Verification Results

- `uv run pytest tests/framework/test_zero_shim_regression_gate.py -q` — **5 passed in 0.10s**
- `uv run pytest tests/framework/test_sdet_rename_leak_gate.py -q` — **4 passed in 0.36s**
- `uv run pytest tests/framework/ -q` — **793 passed, 2 skipped, 18 deselected, 1 xfailed in 99.60s**

## Interface Verification (pre-write checks)

All interfaces matched the plan's `<interfaces>` block verbatim:
- `config.py` line 61: `test_code: TestCodeConfig = Field(...)` — no alias keyword, no `os` import, no `MCPTF_CONFIG_FILE` constant
- `_plugin.py` lines 549–648: six `@pytest.fixture(scope="session")` stubs, each body calling `pytest.fail(..., pytrace=False)`
- `_plugin.py` line 340: `"tests/sdet/ is no longer auto-discovered as of v1.5"` substring present
- `_deprecated_script.py` line 28: `sys.exit(2)` confirmed
- `cli.py`: `--sdet` hidden Option with `_sdet_flag_removed` callback; `gen-sdet-classes` hidden command; both exit 2 under CliRunner
- `pyproject.toml`: `mcp-test-framework = "mcp_test_framework._deprecated_script:main"` confirmed
- `tests/sdet/`: directory exists but contains only `__pycache__/` and `_generated/` — no `test_*.py` files

## Acceptance Criteria Verification

- `grep -c "^def test_.*surface" ...` == 5 — PASS
- `grep -c "import subprocess\|subprocess\."` == 0 (comment mentions only) — PASS
- `grep -c "httpx|requests|urllib|socket"` == 0 — PASS
- `grep -c "@pytest.fixture\|@pytest_asyncio.fixture"` in actual code == 0 (only in docstrings) — PASS
- Config probe walks config.py ONLY; MCPTF check runs against `tree` (config.py), not `ptree` (_plugin.py) — PASS
- `grep -c "exit_code == 2|\.code == 2"` == 3 — PASS
- `grep -c "rubric_parameters"` == 1; EXPECTED frozenset has 6 members, no `"client"` — PASS
- Each function has assertion messages with SHIM-0x id and "v1.6" — PASS
- `grep -c "becomes a no-op"` in RENAME-06 gate == 0 — PASS
- `grep -c "until the v1.6 clean-delete"` in RENAME-06 gate == 1 — PASS

## Deviations from Plan

None — plan executed exactly as written. The five `<action>` code blocks were followed verbatim. The decorator `is_fixture` check included all three branches (bare-attr, bare-name, Call) as specified. The `tomllib.loads(...read_bytes().decode())` pattern was used as specified. The REPO_ROOT derivation `Path(__file__).resolve().parents[2]` matches the structural analog.

## Known Stubs

None — no stubs, placeholders, or hardcoded values in the new gate file.

## Threat Flags

None — this plan adds a static / in-process test file and a docstring edit. No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 537da41 | feat(35-01): add SHIM-09 five-surface zero-shim regression gate |
| Task 2 | 96d9e8e | docs(35-01): correct stale v1.5-removal docstring in RENAME-06 gate (D-06) |

## Self-Check: PASSED

- `tests/framework/test_zero_shim_regression_gate.py` exists: FOUND
- `tests/framework/test_sdet_rename_leak_gate.py` modified: FOUND
- Commit 537da41 exists: FOUND
- Commit 96d9e8e exists: FOUND
- 5 surface functions confirmed: FOUND
- Full framework suite green (793 passed): CONFIRMED
