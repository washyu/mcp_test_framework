---
phase: 27-register-api-contracts-sub-package-test-extraction-lib
plan: 01
subsystem: library-mode-foundations
tags: [pytest-plugin, wave-0-spike, file-relocation, contract-tests, black-box-guard]
requires:
  - mcp_test_framework.fixtures (mcp_target_tool, mcp_judge, mcp_client, mcp_rubric_*, tool_config)
  - _pytest.python.Module (pytest-internal stable surface)
  - pytest-asyncio strict mode + loop_scope="session"
provides:
  - src/mcp_test_framework/contracts/_tests.py (extracted contract test bodies; consumed by 27-02/03 plugin)
  - src/mcp_test_framework/_black_box_guard.py (relocated runtime guard; consumed by 27-02 plugin wiring)
  - tests/framework/test_phase27_spike_synthetic_module.py (Wave 0 gate evidence)
affects:
  - Plans 27-02 (plugin pytest_collection hook) and 27-03 (parametrize site) are now LOCKED to hybrid Approach A
tech-stack:
  added: []
  patterns:
    - "_PytestModule subclass + property nodeid override + Module.from_parent(path=real_file)"
    - "subprocess-isolated embedded pytest for plugin/state-isolated test fixtures"
key-files:
  created:
    - src/mcp_test_framework/_black_box_guard.py
    - src/mcp_test_framework/contracts/_tests.py
    - tests/framework/test_phase27_spike_synthetic_module.py
  modified: []
decisions:
  - "Hybrid Approach A (RESEARCH.md Pattern 3/4) is GO for Plans 27-02/27-03 -- the spike PASSED all four sub-checks under pytest-asyncio strict mode."
  - "Operator-facing -k selection against the synthetic label uses substring 'mcp', not the literal 'mcp-contracts' -- pytest's -k keyword-expression parser treats dashes as binary operators."
  - "Planning-ID-leak gate in src/ took precedence over the plan's verbatim docstring instruction -- scrubbed TEST-NN, D-NN, LIB-NN tokens from the relocated files."
metrics:
  duration_minutes: ~45
  tasks_completed: 3
  files_created: 3
  files_modified: 0
  commits: 4
  spike_outcome: PASS
  completed_date: 2026-05-16
---

# Phase 27 Plan 01: Wave 0 Spike + Black-Box Guard Relocation + Contract-Test Extraction -- Summary

## One-Liner

Wave 0 spike PASSED: hybrid `_ContractsModule(_PytestModule)` injection with synthetic
`<mcp-contracts>` nodeid works end-to-end under pytest-asyncio strict mode with
`loop_scope="session"` -- Plans 27-02 and 27-03 are GO for Approach A. Black-box guard
and 10 contract test bodies relocated into the installed-wheel surface.

## Wave 0 Spike Outcome -- HARD GATE

**Result: PASS (all four sub-checks GREEN).**

The spike test at `tests/framework/test_phase27_spike_synthetic_module.py` exits 0 with
1 passing test. Plans 27-02 and 27-03 may proceed against the hybrid Approach A pattern
as described in their `<action>` blocks. No fallback to the thin-re-export pattern is
required.

Sub-check outcomes:

| Sub-check | Description | Result |
|-----------|-------------|--------|
| A | `--collect-only` renders the synthetic nodeid `<mcp-contracts>` and does not leak `_tests.py::test_spike_alpha` | PASS |
| B | `-k spike_alpha` collects+runs the test; `-k mcp` (substring matched against the synthetic nodeid label) also selects | PASS |
| C | `-m mcp_contract` runs the marker-tagged synth test; `-m "not mcp_contract"` exits 5 (no tests collected) | PASS |
| D | pytest-asyncio strict-mode loop wiring fires without any RuntimeError / cancel-scope / "event loop is closed" diagnostics in output | PASS |

## Tasks Completed

| Task | Name | Status | Files |
|------|------|--------|-------|
| 1 | Relocate black-box `sys.modules` guard to wheel | DONE | `src/mcp_test_framework/_black_box_guard.py` |
| 2 | Extract 10 contract test bodies with `mcp_*` fixture rename | DONE | `src/mcp_test_framework/contracts/_tests.py` |
| 3 | Wave 0 spike validating `_ContractsModule` synthesis pattern | DONE (PASS) | `tests/framework/test_phase27_spike_synthetic_module.py` |

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `c417252` | feat(27-01) | Relocate black-box sys.modules guard to wheel |
| `0829d98` | feat(27-01) | Extract contract test bodies to contracts/_tests.py with mcp_* renames |
| `3e5a470` | fix(27-01) | Scrub planning-IDs from relocated src/ files (auto-fix per project policy) |
| `67abcef` | test(27-01) | Wave 0 spike validates hybrid _ContractsModule injection PASS |

## Verbatim Move -- Line-Count Confirmation

| File | Lines | Analog | Delta |
|------|-------|--------|-------|
| `src/mcp_test_framework/contracts/_tests.py` | 282 | `tests/contract/test_mcp_tool_contract.py` (280) | +2 (+0.7%) |

Within the ±10% target. The +2-line delta is from the expanded module docstring (the
new docstring lists the 10-test surface explicitly to support Plan 27-05's wheel-
introspection scan after the planning-ID scrub removed the original `TEST-NN` markers).

## Pytest-Internal API Surprises

**None observed.** `from _pytest.python import Module` resolves cleanly on:

- pytest 9.0.3
- pytest-asyncio 1.3.0
- Python 3.14.3
- Windows 11 (winpty subprocess timing was the only platform-specific consideration -- spike sets `timeout=60s` per embedded pytest invocation, none hit it)

The spike imports `Module` at module-level under `noqa: F401` so any future pytest
internal-API drift fails the framework's own collection LOUDLY (clear `ImportError`
naming `_pytest.python.Module`) rather than the spike failing inside the subprocess
with an opaque traceback.

## Findings for Plans 27-02 / 27-03

### 1. Dash in `<mcp-contracts>` blocks operator-facing `-k mcp-contracts` selection

Pytest's `-k` keyword-expression grammar parses `-` as a binary operator. Calling
`pytest -k mcp-contracts` is interpreted as `mcp - contracts` and matches nothing
(exit 5 with "1 deselected"). Three options for Plan 27-02 / 27-03 to consider:

- **Option A (status quo):** Keep `<mcp-contracts>` as the synthetic label and surface
  the substring idiom (`pytest -k mcp`) in operator-facing docs. Substring works
  because `mcp` is unique within the synthesized item's keywords.
- **Option B:** Use `<mcp_contracts>` (underscore) for the synthetic label so
  `pytest -k mcp_contracts` works literally. The plan text specified the dash form;
  this is a planner-level decision to revisit.
- **Option C:** Use `[mcp-contracts]` or another bracket syntax that does not collide
  with `-k` expression operators. Untested -- would need a follow-up spike.

The spike currently uses Option A and the substring `mcp` for its sub-check B
assertion. No spike-level failure -- the keyword matcher DOES reach the synthetic
nodeid; the failure mode is purely operator-ergonomic.

### 2. Synthesized collector attachment ritual

The synth `_ContractsModule.from_parent(parent=session, path=<real>)` constructor
returns a Module collector, but pytest's default `Session.collect()` walk does NOT
descend into out-of-band-attached collectors. The spike's payload conftest works
around this by:

1. Stashing the synth collector on `session._mcp_synthetic_collectors` from
   `pytest_collection(session)`.
2. In `pytest_collection_modifyitems(session, config, items)`, iterating each stashed
   collector, calling `collector.collect()`, and appending items to the `items` list
   directly. The `mcp_contract` marker is re-applied to each item explicitly because
   the module-level `add_marker(pytest.mark.mcp_contract)` does NOT auto-propagate to
   `Function` children in this construction path (validated by sub-check C with
   `-m "not mcp_contract"` exiting 5).

Plan 27-02 should adopt the same two-hook attachment ritual. Plan 27-03's
`pytest_generate_tests` hook will see `mcp_target_tool` in `metafunc.fixturenames`
naturally (the fixture is requested by the test functions in `_tests.py`); no extra
gating sentinel is needed beyond the synthetic-module check the plan already calls
out.

### 3. `PytestAssertRewriteWarning: Module already imported so cannot be rewritten; mcp_test_framework.fixtures`

This warning fires on every test session in the repo (pre-existing, unrelated to this
plan -- the framework's `tests/conftest.py:18` declares
`pytest_plugins = ["mcp_test_framework.fixtures"]` which triggers a second-import
attempt after `_plugin.py` already imported the module). Not a Plan 27-01 regression.
Plan 27-04 or 27-05 (when `tests/conftest.py` is cleaned up) should make it go away.

### 4. Subprocess-isolated spike isolation hardening

The spike passes `-p no:mcp_test_framework` to the embedded pytest invocation so the
outer framework's auto-loaded entry-point plugin does not leak into the subprocess.
This is important because the half-built Phase 27 plugin (filled by Plans 27-02/03)
would otherwise attempt to read `mcp_config_file` from the embedded mini-project's
`pyproject.toml` -- which doesn't have it set, but would trigger the plugin's silent
no-op path. Keeping the spike pure-pytest+pytest-asyncio isolates the validation to
exactly the pattern under test.

## Deviations from Plan

### Auto-fixed Issues (Rule 1 + Rule 2)

**1. [Rule 1 - Bug] Spike sub-check B keyword expression**

- **Found during:** Task 3 first run (`-k mcp-contracts` returned exit 5)
- **Issue:** The plan-specified assertion `pytest -k mcp-contracts` cannot match
  because pytest's `-k` parser treats `-` as a binary operator. The spike test
  failed on the second assertion in sub-check B.
- **Fix:** Switched to `-k mcp` (substring match against the synthetic label,
  unique within the synth item's keywords because the real on-disk filename
  contains no `mcp`). Added explanatory comments + a Plan-27-02/03 finding note
  inline.
- **Files modified:** `tests/framework/test_phase27_spike_synthetic_module.py`
  (sub-check B assertion + 19 lines of explanatory comment)
- **Commit:** included in `67abcef`

**2. [Rule 2 - Missing critical correctness: project gate] Planning-ID scrub in src/**

- **Found during:** Post-Task-2 framework regression run
  (`uv run pytest tests/framework/` exited 1)
- **Issue:** The framework's own `tests/framework/unit/test_no_planning_ids_in_src.py`
  and `tests/framework/test_sdet_rename_leak_gate.py` enforce a hard-zero
  planning-ID-leak policy in `src/mcp_test_framework/`. The plan's literal
  docstrings for `_black_box_guard.py` (`Phase 27 D-18 / LIB-08`) and `_tests.py`
  (`TEST-01..TEST-10`, `D-04`, `D-08..D-19`) violate the locked regex
  `(CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB|RELOC)-\d+|\bD-\d+\b`.
- **Fix:** Scrubbed all matching IDs from docstrings + comments. Test function
  names, fixture parameter names, assertion logic, pytest.skip() reasons, the
  `pytestmark` line, and all imports are UNCHANGED -- only narrative text was
  rewritten. The wheel-introspection scan in Plan 27-05 was specified to find
  "an unambiguous, single-purpose module"; the scrubbed docstring still satisfies
  that intent (the module name, function name, and the "Black-box rule" marker
  string in the error message are all preserved).
- **Files modified:** `src/mcp_test_framework/_black_box_guard.py`,
  `src/mcp_test_framework/contracts/_tests.py`
- **Commit:** `3e5a470`

### Spec-vs-Reality Note

- Plan 27-01 Task 1 acceptance criterion says
  `grep -n "homelab_mcp" src/mcp_test_framework/_black_box_guard.py` should return
  three matches. After implementing the literal docstring block specified in the
  plan, grep returns 4 matches (docstring mention, two literals in the
  comprehension, one mention in the error message). The file content matches
  the plan's literal source verbatim (minus the planning-ID scrub); the
  acceptance-criterion count was off-by-one. No remediation needed.

## Files Created (Summary)

```
src/mcp_test_framework/
  _black_box_guard.py     # NEW -- relocated runtime guard, 36 lines
  contracts/
    _tests.py             # NEW -- 10 contract test bodies, 282 lines

tests/framework/
  test_phase27_spike_synthetic_module.py    # NEW -- Wave 0 spike, 334 lines
```

## Files NOT Modified (per Plan)

| File | Reason | Handled By |
|------|--------|------------|
| `tests/contract/test_mcp_tool_contract.py` | Original analog kept for Plan 27-05 deletion | Plan 27-05 |
| `tests/conftest.py` | Original black-box guard + `pytest_generate_tests` kept until plugin wiring lands | Plans 27-02 / 27-05 |
| `src/mcp_test_framework/_plugin.py` | Plugin hook bodies filled by Plans 27-02 + 27-03 | Plans 27-02, 27-03 |

## Verification Gates -- All GREEN

| Gate | Command | Result |
|------|---------|--------|
| Task 1 smoke (clean path) | `uv run python -c "from mcp_test_framework._black_box_guard import check_black_box; check_black_box(); print('OK')"` | `OK` |
| Task 1 smoke (leak-injected) | `... sys.modules['homelab_mcp'] = object(); check_black_box()` | `RuntimeError: Black-box rule violated...` |
| Task 2 function count | `uv run python -c "import inspect; from mcp_test_framework.contracts import _tests; ..."` | 10 async test functions |
| Task 3 spike | `uv run pytest tests/framework/test_phase27_spike_synthetic_module.py -x -v` | 1 passed in ~5s |
| Phase verification | `uv run pytest tests/framework/ -x` | 598 passed, 1 skipped, 17 deselected, 2 xfailed |
| Planning-ID gate | `uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py` | PASSED |
| SDET / planning-ID leak gate | `uv run pytest tests/framework/test_sdet_rename_leak_gate.py` | 4 passed |

## Self-Check: PASSED

Verified all created files exist:

- `src/mcp_test_framework/_black_box_guard.py` -- FOUND
- `src/mcp_test_framework/contracts/_tests.py` -- FOUND
- `tests/framework/test_phase27_spike_synthetic_module.py` -- FOUND

Verified all commits exist on `main`:

- `c417252` -- FOUND
- `0829d98` -- FOUND
- `3e5a470` -- FOUND
- `67abcef` -- FOUND

## GO/NO-GO Signal for Plans 27-02 + 27-03

**GO -- Approach A is validated.** Plans 27-02 and 27-03 may proceed against the
hybrid `_ContractsModule(_PytestModule)` synthesis pattern as their `<action>` blocks
describe. The two-hook attachment ritual (stash collector in `pytest_collection`,
explicit `collect()` + marker re-application in `pytest_collection_modifyitems`) is
the recommended attachment pattern based on spike findings.
