---
phase: 30-cli-demotion-carry-forward-uat-closure-docs-rewrite
plan: "01"
subsystem: framework-self-tests
tags: [parity, pytest, junit-xml, subprocess, marker-registration, close-02]
dependency_graph:
  requires: [phase-27-dogfood-loop, pyproject-mcp-config-file-ini]
  provides: [cli-library-parity-gate, parity-marker-registration]
  affects: [tests/framework/parity/, tests/framework/conftest.py]
tech_stack:
  added: []
  patterns: [subprocess-two-route-parity, junit-xml-parse-nodeid-outcome, pytest-marker-registration-in-conftest]
key_files:
  created:
    - tests/framework/parity/test_cli_vs_pytest_route.py
  modified:
    - tests/framework/conftest.py
decisions:
  - "Used config parameter name (not pytestconfig) in pytest_configure hook — pluggy validates parameter names against pytest hookspec"
  - "Local ET.parse walker for _parse_outcomes — not reusing _runner.parse_junit_xml (returns ParsedRun per-tool, not per-nodeid as D-01 requires)"
  - "No tests/framework/parity/__init__.py — pytest collects without it per existing smoke/ pattern"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-20T00:24:18Z"
  tasks: 2
  files: 2
---

# Phase 30 Plan 01: CLI vs pytest-route parity test (CLOSE-02) Summary

CLI/library parity gate using two-subprocess JUnit XML round-trip: drives both `mcp-contracts run` and raw `pytest -o mcp_config_file=...` against `config.test.yaml` and asserts identical `{nodeid: outcome}` dicts.

## What Was Created

### New File: `tests/framework/parity/test_cli_vs_pytest_route.py`

The only new production-shape test in Phase 30. Implements all four locked design decisions:

- **D-01:** Dict equality on `{nodeid: outcome}` parsed from JUnit XML via `_parse_outcomes()`. Outcome enum: `passed | failed | skipped | error`. Any-fail-wins priority per testcase children (failure > error > skipped > passed).
- **D-02:** Config substrate is `./config.test.yaml` — same config Phase 27 D-06 dogfood uses. Zero new fixture infrastructure.
- **D-02a:** Defensive `assert outcomes_a, (...)` fires before dict-equality assert when `config.test.yaml` has `tools: {}` (Phase 27 D-13/D-16 intentional empty allowlist). Catches vacuous PASS and directs operator to populate `tools:` before running the gate locally.
- **D-03:** Two subprocesses + `@pytest.mark.parity` recursion guard. Route A uses `sys.executable -m mcp_test_framework.cli run --config config.test.yaml --junit-xml=<tmp>/a.xml -- -m "not parity"`. Route B uses `sys.executable -m pytest -o mcp_config_file=./config.test.yaml --junitxml=<tmp>/b.xml -m "not parity" tests/`.

Key implementation details:
- `repo_root = Path(__file__).resolve().parents[3]` (parity → framework → tests → repo_root)
- `check=False` so returncode surfaces in assertion messages
- `f"--junit-xml={xml_a}"` single f-string element (no manual quoting)
- `pytestmark = [pytest.mark.parity, pytest.mark.live_homelab, pytest.mark.live_ollama]`

### Modified File: `tests/framework/conftest.py`

Appended `pytest_configure` hook that registers the `parity` marker via `config.addinivalue_line(...)`. Hook is framework-internal (not in `pyproject.toml` markers list) so it is NOT surfaced on operator-facing `pytest --markers` output.

Existing Phase 23 D-02 content preserved verbatim (module docstring, imports, `_TEST_CODE_STUB` constant, `config` fixture).

## Verification Commands That Passed

```
uv run pytest tests/framework/parity/ --collect-only
# collected 1 item / 1 deselected / 0 selected (default addopts deselects live markers)

uv run pytest tests/framework/parity/ --collect-only -m "not live_homelab and not live_ollama"
# no tests collected (1 deselected) — default deselect works

uv run pytest tests/framework/parity/ --collect-only -m "parity"
# 1 test collected — opt-in selection works

grep '"parity:' pyproject.toml
# (no output) — marker NOT in operator-facing pyproject markers

grep '"parity:' tests/framework/conftest.py
# 1 match — marker registered in framework conftest

grep "_TEST_CODE_STUB" tests/framework/conftest.py
# 2 matches — Phase 23 D-02 fixture unchanged
```

## Test Default-Skip Confirmation

The parity test carries both `pytest.mark.live_homelab` and `pytest.mark.live_ollama`. The pyproject `addopts = "-m 'not live_homelab and not live_ollama'"` deselects it by default. Verified via `--collect-only` showing zero collected items under default selector.

To run the parity gate: `pytest -m "parity and live_homelab and live_ollama" tests/framework/parity/`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pytest_configure hook parameter name must be `config` per hookspec**

- **Found during:** Task 2 verification (collection threw `PluginValidationError`)
- **Issue:** Plan specified `pytestconfig` as the hook parameter name (to avoid reader confusion with the `config` fixture). Pluggy validates hook parameter names against the pytest hookspec at registration time. The `pytest_configure` hookspec declares the parameter as `config`, so `pytestconfig` caused `PluginValidationError: Argument(s) {'pytestconfig'} are declared in the hookimpl but can not be found in the hookspec`.
- **Fix:** Renamed parameter from `pytestconfig` to `config` and updated docstring to explain the naming constraint (noting that the session-scoped `config` fixture does not conflict at hook scope). Also added `# noqa: D401` per the pattern in PATTERNS.md.
- **Files modified:** `tests/framework/conftest.py`
- **Commit:** 8c12d76

## Known Stubs

None. The parity test is intentionally skipped by default (live stack markers). No stubs exist — the test body is complete and functional.

## Threat Flags

None. This plan adds only framework self-test files. No new network endpoints, auth paths, or operator-facing surfaces introduced.

## Self-Check: PASSED

- `tests/framework/parity/test_cli_vs_pytest_route.py` exists: FOUND
- `tests/framework/conftest.py` modified (44 lines): FOUND
- Commit e3cc97b: FOUND (feat: register parity marker)
- Commit 8c12d76: FOUND (fix: use config parameter name)
- Commit 456bfaa: FOUND (feat: add CLI vs pytest-route parity test)
