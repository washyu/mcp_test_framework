---
phase: 19-stateful-primitives-domain-ui-integration
plan: "03"
subsystem: runner
tags: [runner, renderer, junit-xml, sdet, scenario, ui-01, tdd]
dependency_graph:
  requires:
    - "18-06: _render_per_tool_rows em-dash + FAIL row surface (D-09/D-10 property extraction)"
    - "18-07: tests/sdet/conftest.py pytest_exception_interact hook"
    - "16-xx: ParsedRun/ToolVerdict dataclasses, _extract_tool_name, _format_skip_reasons"
  provides:
    - "parse_junit_xml SDET classname fall-through: synthetic per_tool keys for tests.sdet.test_* testcases"
    - "_render_per_tool_rows scenario block: bare group header + indented per-test rows (UI-01 shape)"
  affects:
    - "19-04: dogfood scenario (test_proxmox_vm_lifecycle.py) exercises this renderer end-to-end"
tech_stack:
  added: []
  patterns:
    - "Strategy beta: synthetic per_tool keys (<group>::<row_label>) instead of ToolVerdict extension -- mirrors Phase 18 Plan 06 Strategy 1"
    - "TDD RED/GREEN: test file written first, parser/renderer extended after; all 17 tests RED before implementation"
key_files:
  created:
    - tests/framework/unit/test_runner_sdet_rows.py
  modified:
    - src/mcp_test_framework/_runner.py
decisions:
  - "Strategy beta (synthetic keys) chosen over Strategy alpha (ToolVerdict extension): zero dataclass churn, mirrors Plan 18-06 Strategy 1 lock, keeps parser->renderer surface frozen"
  - "SDET testcase bracket-extraction precedence preserved: _extract_tool_name(name) wins when it returns non-None, classname fall-through only fires on None"
  - "Contract block byte-identical when no scenarios present: contract_per_tool filter ensures legacy path unchanged"
  - "Requirement-ID tokens: zero new tokens in src/ (delta 0 vs baseline of 1 pre-existing PREFLIGHT-01 in docstring)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-13"
  tasks_completed: 2
  files_changed: 2
---

# Phase 19 Plan 03: SDET classname parser branch + scenario renderer (UI-01) Summary

SDET-classname fall-through in `parse_junit_xml` plus scenario-block rendering in `_render_per_tool_rows`, enabling `tests/sdet/test_*` testcases to flow from JUnit XML into the operator output as grouped per-scenario rows under bare group headers.

## What Was Built

### Task 1: parse_junit_xml SDET classname fall-through

`parse_junit_xml` now handles testcases under `tests/sdet/` that lack a `[<tool>]` parametrize bracket suffix. When `_extract_tool_name(name)` returns `None` AND `classname.startswith("tests.sdet.test_")`, the parser derives:

- `group = classname.rsplit(".", 1)[-1].removeprefix("test_")` — strips `tests.sdet.test_` prefix to get the scenario module stem (e.g. `proxmox_vm_lifecycle`)
- `row_label = name.removeprefix("test_")` — strips `test_` prefix from the test function name (e.g. `create_returns_pending_vm`)
- `tool = f"{group}::{row_label}"` — synthetic per_tool key (e.g. `proxmox_vm_lifecycle::create_returns_pending_vm`)

All downstream PASS/FAIL/SKIP rules and Phase 18 D-09 `mcptf_error_*` property extraction reuse the same code path verbatim. No new ToolVerdict fields.

**Strategy choice (beta):** Synthetic keys instead of ToolVerdict extension. Keeps the parser→renderer dataclass surface frozen, matching Phase 18 Plan 06 "Strategy 1 — no dataclass churn" lock.

### Task 2: _render_per_tool_rows scenario blocks

`_render_per_tool_rows` now splits `parsed.per_tool` into two buckets:
- `contract_per_tool` — keys without `::` (legacy contract tools, ljust-aligned)
- `scenario_entries` — keys with `::`, grouped by the prefix before `::` (scenario module stems)

Contract block output is **byte-identical** when no scenario keys are present. Scenario blocks render after the contract block: bare group header (no trailing colon) followed by indented per-test rows with glyph + row_label but **no "PASS"/"FAIL"/"SKIP" word**.

**Matches CONTEXT.md UI-01 expected output exactly:**
```
proxmox_vm_lifecycle
  ✓ create_returns_pending_vm
  ✓ modify_accepts_cpu_increase
  ✓ delete_returns_ok
```

Glyph vocabulary: `✓` (PASS), `✗` (FAIL), `–` (SKIP, en-dash U+2013). FAIL and SKIP rows with detail append em-dash U+2014 + message/reasons.

## Test Counts

| Suite | Before | After | Delta |
|-------|--------|-------|-------|
| test_runner_sdet_rows.py | 0 | 17 | +17 |
| test_runner_parser.py | 30 | 30 | 0 (regression) |
| test_runner_pre_run_digest.py | - | pass | 0 (regression) |
| test_runner_sdet_digest.py | - | pass | 0 (regression) |
| test_runner_debug_appendix_d11.py | - | pass | 0 (regression) |
| test_runner_verbosity.py | - | pass | 0 (regression) |
| **Total regression** | 88 | 88 | 0 regression |

## Strategy Choice Rationale

Strategy beta (synthetic keys `<group>::<row_label>`) was chosen over Strategy alpha (extend ToolVerdict with `per_case: list[...]`):

- Zero dataclass churn: 30 existing parser regression tests continue to pass without modification
- Direct analog: Phase 18 Plan 06 Strategy 1 ("second-pass over data rather than dataclass extension") set the precedent
- Renderer split is minimal: a 3-line dict comprehension separates contracts from scenarios
- Future extensibility: if per-row metadata (e.g. duration) is needed later, the key shape is already established

## Sample Rendered Output (Mixed Scope ParsedRun)

Given a `ParsedRun` with both contract and scenario keys:
```
passing:
  list_tools  ✓ PASS

proxmox_vm_lifecycle
  ✓ create_returns_pending_vm
  ✓ modify_accepts_cpu_increase
  ✓ delete_returns_ok
```

FAIL scenario row with Phase 18 D-10 error code:
```
proxmox_vm_lifecycle
  ✗ create_returns_pending_vm — [E_SUBTREE] vmid not found
  – modify_accepts_cpu_increase — fixture proxmox_vm_lifecycle failed
  – delete_returns_ok — fixture proxmox_vm_lifecycle failed
```

## Pyright Notes

Pre-Phase-19 baseline: 2 known pre-existing errors at `elem` Optional access lines (the parser's `failure = tc.find(...)` / `error = tc.find(...)` branches where `elem` is typed `Element | None` but then used without re-checking). These are pre-existing. The Phase 19 additions introduce no new type errors; the synthetic key derivation uses only `str` operations and `dict.setdefault` (same shape as the existing contract-tool path).

## Requirement-ID Token Count

- Pre-edit baseline in `src/mcp_test_framework/_runner.py`: 1 (pre-existing `PREFLIGHT-01..02` in `_render_scenario_pre_run_digest` docstring, line 923)
- Post-edit count: 1 (no new tokens added)
- Delta: 0 (acceptance criterion satisfied)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed wrong field name in renderer tests**
- **Found during:** Task 2 GREEN phase
- **Issue:** Tests constructed `ParsedRun(total_tests=...)` but the dataclass field is `total_cases`. Caused `TypeError` on 8 of the 9 renderer tests.
- **Fix:** Changed all `total_tests=` kwargs to `total_cases=` in the 8 direct-construction renderer tests (parser tests use `parse_junit_xml` so they never hit this).
- **Files modified:** `tests/framework/unit/test_runner_sdet_rows.py`
- **Commit:** 3a8f3eb (included in the GREEN commit)

**2. [Rule - Proactive] Removed UI-01 requirement-ID token from renderer comment**
- **Found during:** Task 2 GREEN acceptance check
- **Issue:** A comment in the new `_render_per_tool_rows` scenario block read `# -- Scenario blocks (Phase 19 UI-01) --` which introduced a requirement-ID token (delta +1 vs baseline).
- **Fix:** Changed to `# -- Scenario blocks (Phase 19) --` (ID removed from src/).
- **Files modified:** `src/mcp_test_framework/_runner.py`
- **Commit:** 3a8f3eb (included in the GREEN commit)

## Plan 04 Integration Note

Plan 04 (dogfood: `tests/sdet/test_proxmox_vm_lifecycle.py`) will exercise this parser+renderer end-to-end against live Proxmox JUnit XML. When Proxmox is reachable and all three tests pass, the operator will see the exact UI-01 output block from CONTEXT.md lines 178-183. When Proxmox is unreachable (D-01 fail-loud), the cascade pattern (one FAIL + N SKIP rows under the group header) pinned by `test_render_scenario_block_fixture_error_cascade` will be the actual output.

## Known Stubs

None. The parser and renderer are fully wired and produce correct output for all covered scenarios.

## Self-Check: PASSED

- [x] `tests/framework/unit/test_runner_sdet_rows.py` exists
- [x] `src/mcp_test_framework/_runner.py` modified with parser + renderer extensions
- [x] commit `6c282ff` — test(19-03): RED -- SDET parser branch (8 tests)
- [x] commit `96f962b` — feat(19-03): GREEN -- parse_junit_xml SDET classname fall-through
- [x] commit `3a8f3eb` — feat(19-03): GREEN -- _render_per_tool_rows scenario blocks
- [x] 17/17 new tests pass, 88/88 regression tests pass
- [x] Zero new requirement-ID tokens in src/
