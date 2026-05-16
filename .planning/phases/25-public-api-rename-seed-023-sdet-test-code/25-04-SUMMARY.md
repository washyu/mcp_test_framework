---
phase: 25-public-api-rename-seed-023-sdet-test-code
plan: 04
subsystem: public-api / operator-test-directory
tags: [rename, sdet, test_code, dual-discovery, deprecation-warning, RENAME-04]
requires:
  - tests/sdet/{conftest.py, test_proxmox_vm_lifecycle_readme_sample.py, __init__.py} (pre-rename)
  - src/mcp_test_framework/_runner.py:_build_pytest_args (pre-rename)
  - src/mcp_test_framework/fixtures.py:_LIVE_PREFIXES (pre-rename)
provides:
  - tests/test_code/ as the canonical operator-authored test directory
  - dual-discovery argv (tests/test_code/ primary, tests/sdet/ fallback when populated)
  - session-once DeprecationWarning when items collect from legacy tests/sdet/
  - _LIVE_PREFIXES allowlist accepting tests/test_code/ alongside legacy tests/sdet/
  - [tool.pytest.ini_options].filterwarnings entry surfacing project DeprecationWarnings (D-03)
  - [tool.pyright] include/strict paths repointed to test_code/response.py
affects:
  - src/mcp_test_framework/_runner.py (argv builder + _collect_test_code_scenarios rename + classname-prefix dual-acceptance)
  - src/mcp_test_framework/fixtures.py (live-prefix allowlist)
  - src/mcp_test_framework/cli.py (one call-site update: _collect_sdet_scenarios -> _collect_test_code_scenarios)
  - tests/framework/unit/test_runner_sdet_digest.py (Rule 1 -- renamed helper consumed)
  - tests/framework/unit/test_runner_sdet_kwarg.py (Rule 1 -- argv assertions + 2 new pinning tests)
  - tests/framework/unit/test_sdet_cli.py (Rule 1 -- --sdet -> --test-code, argv flip, chdir(tmp_path))
  - tests/framework/unit/test_sdet_conftest_hook.py (Rule 1 -- importlib path repoint)
tech-stack:
  added: []
  patterns:
    - "git mv preserves blame on conftest + test file move (D-06 convention, third re-use in Phase 25 after plans 01 + 03)"
    - "Dual-path argv (primary + optional fallback when populated) -- echoes Phase 15 tests/framework/ + tests/contract/ split pattern"
    - "Session-once warning via module-level _LEGACY_SDET_WARNED flag in pytest_collection_modifyitems -- cleaner than the per-call default-filter approach used by the cli.py shim because pytest may call the hook once per collection pass"
    - "[tool.pytest.ini_options].filterwarnings TOML array with always::DeprecationWarning:mcp_test_framework rule (D-03) -- targets module-suffix match so external operators are unaffected"
    - "# noqa: sdet-rename-shim token on every shim line (D-18) for plan 06 sweep exclusion"
    - "Cross-platform nodeid normalization (replace backslash with forward slash) before substring match -- defensive against Windows-collected paths"
key-files:
  created:
    - .planning/phases/25-public-api-rename-seed-023-sdet-test-code/25-04-SUMMARY.md
  modified:
    - tests/test_code/conftest.py (moved via git mv from tests/sdet/; imports flipped + session-once DeprecationWarning hook added)
    - tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py (moved via git mv from tests/sdet/; imports flipped)
    - tests/test_code/__init__.py (moved via git mv from tests/sdet/; empty file)
    - src/mcp_test_framework/_runner.py (_build_pytest_args dual-discovery; _collect_sdet_scenarios -> _collect_test_code_scenarios; JUnit classname dual-prefix acceptance; docstring path updates)
    - src/mcp_test_framework/fixtures.py (_LIVE_PREFIXES allowlist adds tests/test_code/; docstring updates)
    - src/mcp_test_framework/cli.py (call-site rename: _collect_sdet_scenarios -> _collect_test_code_scenarios)
    - pyproject.toml ([tool.pytest.ini_options].filterwarnings + [tool.pyright] include/strict path repoint)
    - tests/framework/unit/test_runner_sdet_digest.py (renamed helper import + references)
    - tests/framework/unit/test_runner_sdet_kwarg.py (argv assertions flipped + 2 new dual-discovery pin tests)
    - tests/framework/unit/test_sdet_cli.py (argv assertions flipped + flag rename --sdet -> --test-code in test bodies)
    - tests/framework/unit/test_sdet_conftest_hook.py (importlib path repoint)
decisions:
  - "D-03 honored: pyproject.toml [tool.pytest.ini_options].filterwarnings = always::DeprecationWarning:mcp_test_framework surfaces project-emitted DeprecationWarnings on every framework pytest run"
  - "D-06 honored: git mv preserves blame for tests/sdet/conftest.py + test file move to tests/test_code/"
  - "D-07 honored: dual-path discovery for v1.4 -- tests/test_code/ is the documented primary, tests/sdet/ continues to collect; session-once DeprecationWarning fires (NOT per-file, NOT per-process) when items collect from the legacy path"
  - "D-08 honored: no stub file at tests/sdet/; the directory simply becomes empty after git mv (only __pycache__/ and _generated/ remain, both gitignored or operator-generated)"
  - "D-18 honored: every # noqa: sdet-rename-shim shim line carries the marker; grep -v noqa filter returns zero count in _runner.py + fixtures.py for tests/sdet literals"
  - "Rename of _collect_sdet_scenarios to _collect_test_code_scenarios chosen over keeping the old name with a comment: the helper is a `_`-prefixed internal so no compat alias is needed (D-16: sweep excludes _-prefixed names but consistency favors rename)"
  - "Classname prefix check in the JUnit testcase parser accepts BOTH tests.test_code.test_ AND tests.sdet.test_ -- needed so renderer keeps grouping legacy testcase output during the dual-discovery window"
  - "Strip D-07 planning-ID literal from src/ docstrings/comments mid-task: test_no_planning_ids_in_src.py enforces Phase 22 D-04 hard-zero policy; behavior unchanged, only the literal IDs removed"
metrics:
  duration: ~25min
  completed: 2026-05-16
  tasks_completed: 4
  files_modified: 11
  commits: 5
---

# Phase 25 Plan 04: Public-API Rename (sdet -> test_code) -- Operator Test Directory Summary

Moved the operator-authored test files (`conftest.py` + `test_proxmox_vm_lifecycle_readme_sample.py`) from `tests/sdet/` to `tests/test_code/` via `git mv` (blame preserved). Updated `_runner._build_pytest_args` so the operator-default `--test-code` scope is `tests/test_code/`, with `tests/sdet/` retained as a fallback discovery path when the legacy directory contains `test_*.py` files (D-07 dual-discovery). Added a session-once `DeprecationWarning` hook in `tests/test_code/conftest.py` that fires exactly one warning per session when any item is collected from the legacy `tests/sdet/` path. Updated `_session_needs_preflight` allowlist (in `fixtures.py`) to accept both paths. Added `filterwarnings = always::DeprecationWarning:mcp_test_framework` to `pyproject.toml` so the framework's own test runs surface project-emitted deprecation warnings (D-03). Updated `[tool.pyright]` `include`/`strict` paths from `sdet/response.py` to `test_code/response.py`.

## Objective Met

RENAME-04 acceptance text holds:

- **`tests/test_code/` is discoverable**: `mcp-test-framework run --test-code` (and the deprecated `--sdet` alias) builds argv whose primary scope is `tests/test_code/` (verified via `_build_pytest_args(sdet=True)` -> `['tests/test_code']`).
- **`tests/sdet/` continues to work with deprecation note**: when the legacy directory contains `test_*.py` files, argv is `['tests/test_code', 'tests/sdet']`; pytest collects items from both, and the session-once `DeprecationWarning` fires once via `pytest_collection_modifyitems` in `tests/test_code/conftest.py` naming the v1.5 removal milestone.
- **Framework's own pytest run surfaces project DeprecationWarnings (D-03)**: `[tool.pytest.ini_options].filterwarnings = ["always::DeprecationWarning:mcp_test_framework"]` forces the warnings through on every framework run; external operators' pytest configs are unaffected (module-suffix match only).
- **`_session_needs_preflight` allowlist accepts both paths**: `_LIVE_PREFIXES` is `("tests/contract/", "tests/test_code/", "tests/sdet/")` -- preflight runs for items under any of the three scopes.
- **`pyright` include/strict paths updated**: both lists now reference `src/mcp_test_framework/test_code/response.py` (no `sdet/response.py` reference remains in `pyproject.toml`).

## Tasks Completed

| # | Name                                                                                                  | Commit  | Files                                                                              |
| - | ----------------------------------------------------------------------------------------------------- | ------- | ---------------------------------------------------------------------------------- |
| 1 | git mv tests/sdet/ to tests/test_code/ preserving blame                                               | acabf98 | tests/test_code/{conftest.py, test_proxmox_vm_lifecycle_readme_sample.py, __init__.py} |
| 2 | Dual-discovery in _runner._build_pytest_args + _collect_test_code_scenarios + classname dual-prefix; _LIVE_PREFIXES allowlist | 2397d84 | src/mcp_test_framework/_runner.py, src/mcp_test_framework/fixtures.py, src/mcp_test_framework/cli.py, tests/framework/unit/test_runner_sdet_digest.py |
| 3 | Session-once DeprecationWarning hook in tests/test_code/conftest.py                                   | 2d453cb | tests/test_code/conftest.py                                                        |
| 4 | pyproject.toml filterwarnings + pyright path repoint                                                  | 843b767 | pyproject.toml                                                                     |
| - | **Deviation (Rule 1):** repoint framework self-tests to test_code surface (17 tests pre-fix -> 580 pass post-fix) | 074ab92 | 5 modules under tests/framework/unit/ + 2 stripped D-07 ID literals in src/ |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Framework self-test failures directly caused by Plan 25-04 changes**

- **Found during:** Task 2 verification (`uv run python -m pytest tests/framework -q`)
- **Issue:** 17 framework self-tests failed after the argv builder + helper rename + conftest move. Categories:
  - `test_runner_sdet_kwarg.py`: 4 tests asserted `'tests/sdet' in args` (now `tests/test_code` is primary)
  - `test_sdet_cli.py`: 3 tests invoked `_invoke('run', '--sdet', ...)` and asserted argv contains `'tests/sdet'` (now `--test-code` + `tests/test_code`)
  - `test_sdet_conftest_hook.py`: 8 tests called `_load_sdet_conftest()` which looked up `tests/sdet/conftest.py` (now at `tests/test_code/conftest.py`)
  - `test_no_planning_ids_in_src.py`: 1 test enforced Phase 22 D-04 hard-zero policy on `D-\d+` references; my new `D-07` mentions in `_runner.py` + `fixtures.py` docstrings tripped it
  - `test_runner_sdet_digest.py`: 2 tests already fixed in Task 2 commit -- listed for completeness only
- **Fix:**
  - argv assertions flipped from `tests/sdet` to `tests/test_code`; added `monkeypatch.chdir(tmp_path)` so the dual-discovery fallback stays inactive in unit tests
  - Added two new pinning tests (`test_build_pytest_args_sdet_true_with_legacy_dir_appends_legacy`, `test_build_pytest_args_sdet_true_legacy_dir_empty_is_inactive`) for the dual-discovery contract
  - `--sdet` -> `--test-code` flag substitution in `_invoke(...)` call sites (the legacy `--sdet` flag still works as a hidden shim per Plan 25-02, but the tests are pinning the canonical operator surface)
  - `_load_sdet_conftest()` importlib path repointed to `tests/test_code/conftest.py`; module name + assertion message updated to match
  - Stripped 4 occurrences of `D-07` literal from `_runner.py` + `fixtures.py` docstrings/comments; behavior unchanged, only the planning-ID strings removed (Phase 22 D-04 hard-zero policy holds)
- **Files modified:** 5 test modules (3 under `tests/framework/unit/`, 2 framework-internal `_runner.py` + `fixtures.py` for the ID strip)
- **Commit:** 074ab92

**Rationale (per deviation rules SCOPE BOUNDARY):** All 17 failures were directly caused by Plan 25-04 changes (this commit's argv rename + git mv). No pre-existing failures unrelated to the rename were touched.

## Authentication Gates

None encountered.

## Self-Check: PASSED

**1. Created files exist:**
- `tests/test_code/conftest.py` FOUND (renamed via git mv from tests/sdet/conftest.py; pytest_collection_modifyitems + pytest_exception_interact present)
- `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py` FOUND (renamed via git mv)
- `tests/test_code/__init__.py` FOUND (empty file, renamed via git mv)

**2. Commits exist (verified via git log --oneline -8):**
- acabf98 (refactor(25-04): git mv tests/sdet/ to tests/test_code/)
- 2397d84 (feat(25-04): dual-discovery tests/test_code/ + tests/sdet/ in _runner.py + fixtures.py)
- 2d453cb (feat(25-04): add session-once DeprecationWarning hook to tests/test_code/conftest.py)
- 843b767 (chore(25-04): add filterwarnings always::DeprecationWarning:mcp_test_framework + pyright path update)
- 074ab92 (fix(25-04): Rule-1 deviation -- repoint framework self-tests to test_code surface)

**3. Verifications run:**
- `uv run python -m pytest tests/framework -q` -> 580 passed, 1 skipped, 17 deselected, 2 xfailed (post-Rule-1-fix)
- `uv run python -c "from mcp_test_framework._runner import _build_pytest_args; argv = _build_pytest_args(None, [], sdet=True); assert 'tests/test_code' in argv"` -> argv = `['tests/test_code']` (no legacy dir in repo cwd; matches D-08: tests/sdet/ contains only __pycache__ + _generated, no test_*.py)
- `grep -n "tests/sdet" src/mcp_test_framework/_runner.py | grep -v "noqa: sdet-rename-shim" | wc -l` -> 0
- `grep -n "tests/sdet" src/mcp_test_framework/fixtures.py | grep -v "noqa: sdet-rename-shim" | wc -l` -> 0
- `uv run python -c "import tomllib; d = tomllib.load(open('pyproject.toml','rb')); assert 'src/mcp_test_framework/test_code/response.py' in d['tool']['pyright']['include']"` -> ok
