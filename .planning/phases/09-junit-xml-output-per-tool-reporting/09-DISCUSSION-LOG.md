# Phase 09 Discussion Log

**Date:** 2026-05-07
**Mode:** discuss (default; non-power)
**Areas presented:** 8 candidate gray areas
**Areas selected for interactive discussion:** 1, 2, 3, 4, 5
**Areas resolved as Claude's Discretion:** 6, 7, 8

## Areas selected — user-locked decisions

### 1. `--junit-xml` flag surface → D-01

**Question:** Explicit Typer flag, naked passthrough, or both?
**User answer:** Explicit flag + keep passthrough (Recommended)
**Locked:** D-01, D-01a, D-01b — explicit `--junit-xml=PATH` Typer option translates to pytest's `--junitxml=PATH`; extras passthrough preserved; passthrough wins on conflict (last-occurrence pytest argparse rule).

### 2. Per-tool summary mechanism → D-02

**Question:** pytest plugin / hook vs. post-run XML re-parse vs. both?
**User answer:** pytest plugin via `pytest_terminal_summary` hook (Recommended)
**Locked:** D-02, D-02a, D-02b, D-02c — `src/mcp_test_framework/_reporter.py`, registered via the existing `pytest_plugins` chain, `pytest_runtest_logreport` accumulator + `pytest_terminal_summary` emission, parses tool name from `[<tool_name>]` parametrize suffix, emits via `terminalreporter` (not raw stdout).

### 3. Per-tool aggregate verdict rule → D-03

**Question:** Strict any-fail-wins, MIXED bucket, or counts-always?
**User answer:** Strict any-fail-wins (Recommended)
**Locked:** D-03, D-03a, D-03b — FAIL/error → FAIL; else any pass → PASS; else SKIP. Errors collapse into FAIL for terminal; XML preserves the `<error>` vs `<failure>` distinction. No reason text on PASS/FAIL rows; reason text only on SKIP rows.

### 4. Summary on/off → D-04

**Question:** Always-on, opt-in, or opt-out?
**User answer:** Always-on for `run` (Recommended)
**Locked:** D-04, D-04a, D-04b — always-on for the framework CLI; appears after pytest's standard sections; suppressed under `-q`.

### 5. Skip-reason rendering → D-05

**Question:** First-seen reason, list distinct, or aggregate count + canonical?
**User answer:** List distinct reasons when they differ
**Locked:** D-05, D-05a — first-seen by default for single-reason tools; `;`-separated list when distinct reasons exist (truncate to first 3 + "(N more)" if >3 distinct); reason text rendered verbatim.

## Areas not selected — Claude's Discretion

### 6. JUnit XML defaults vs customization → CD-01

Accept pytest's defaults for `<skipped>`, `<failure>`, `<error>`, `classname`, `name`. No `<properties>` extensions, no custom reordering. Verifier confirms a sample emitted XML is well-formed against GitHub Actions's expected JUnit XSD.

### 7. Error vs Fail bucketing → CD-02

Terminal summary collapses `error` outcomes into `FAIL` (matches ROADMAP's PASS|FAIL|SKIP literal). JUnit XML preserves the granular distinction.

### 8. Output ordering → CD-03

Group by status: FAIL alphabetical → SKIP alphabetical → PASS alphabetical. Header line above the table notes the grouping.

## Wrap-up

User selected "I'm ready for context" after 5 decisions + 3 discretion items. CONTEXT.md written with full inheritance chain (L-01..L-06 from prior phases) and 6 additional Claude's Discretion items (CD-04..CD-06) covering plan-cut, naming, and translation seam — left for the planner to choose during `/gsd-plan-phase 09`.

No scope creep raised; no canonical refs added beyond the standard set; no spike/sketch findings to fold; one matched todo (`2026-05-07-v1-1-isolate-test-runs-from-user-state.md`) was reviewed and rejected as out-of-scope (it's a Phase 06 source artifact that should be archived independently — flagged in the deferred section).
