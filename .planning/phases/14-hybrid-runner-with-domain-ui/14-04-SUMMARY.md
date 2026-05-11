---
phase: 14-hybrid-runner-with-domain-ui
plan: 04
subsystem: cli
tags: [verbosity, quiet, debug, typer, flags, render-appendix, rung-layering]

# Dependency graph
requires:
  - phase: 14-01-subprocess-spine
    provides: "src/mcp_test_framework/_runner.py module + subprocess.run + tempfile JUnit XML + captured_stdout/captured_stderr surfaces"
  - phase: 14-02-junit-xml-parser
    provides: "ParsedRun + ToolVerdict.failure_body (consumed by render_debug_appendix for traceback rendering)"
  - phase: 14-03-domain-ui-renderer
    provides: "render_domain_ui + RenderContext + _render_summary_line + _compose_unparametrized_skips_from_config (all reused by Plan 04 helpers)"
provides:
  - "render_summary_only(parsed, ctx, file=None): D-12 quiet-mode renderer; emits ONLY the summary line; includes state-(a)/(c) SKIP count via _compose_unparametrized_skips_from_config so quiet summary matches default summary"
  - "render_debug_appendix(captured_stdout, captured_stderr, parsed, file=None): D-13 debug appendix; printed AFTER whichever rung above ran; sections: raw stdout -> stderr (if any) -> failure tracebacks (if any tool has failure_body)"
  - "cli.py:run -q/--quiet flag (Typer-level): swaps render_domain_ui -> render_summary_only"
  - "cli.py:run --debug flag (Typer-level): appends render_debug_appendix after whichever rung ran"
  - "Verbosity ladder COMPLETE: quiet -> default -> debug. RUNNER-04 invariant pinned in tests: each rung adds info; none re-shapes the layer below"
  - "Explicit absence of --explain in run --help (D-14: Phase 16 owns it); test_run_help_does_not_list_explain pins this contract"
affects: [14-05-reporter-cleanup, phase-16-pre-run-digest]

# Tech tracking
tech-stack:
  added: []  # no new deps -- stdlib print + dataclass field iteration only
  patterns:
    - "Verbosity ladder via additive composition: --debug appends render_debug_appendix AFTER render_domain_ui OR render_summary_only (the rung below decides shape; --debug only adds info). RUNNER-04 invariant + D-13 layering."
    - "Quiet mode does NOT forward -q to pytest (D-12) -- pytest runs at default verbosity internally so the JUnit XML stays complete. quiet is a Typer-level shape switch, not a pytest passthrough."
    - "Grep-pinned separator strings: '--- raw pytest output ---', '--- captured stderr ---', '--- failure tracebacks ---'. Tests assert their presence in at least 3 places per acceptance criteria so future drift is caught."
    - "Forward-reference test pattern (test_run_help_does_not_list_explain): pin the ABSENCE of a future flag so phases that ship out of order are caught. D-14 owns this."
    - "TDD RED->GREEN split commits: test commit precedes the implementation commit so each gate is independently grep-able in `git log --oneline`."

key-files:
  created:
    - "tests/test_runner_verbosity.py -- 13 tests pinning Phase 14 D-12/D-13/D-14: render_summary_only output shape (no header / no rows), render_debug_appendix separators + failure body inclusion, CLI --help surface (lists -q/--quiet/--debug, NOT --explain), CLI end-to-end with mocked subprocess (--debug ordering invariant, -q+--debug ordering invariant, --raw bypasses all flags)"
  modified:
    - "src/mcp_test_framework/_runner.py -- appended 91 lines: render_summary_only + render_debug_appendix; both use file=None / call-time sys.stdout resolution for capsys compatibility; render_debug_appendix iterates parsed.per_tool failure_body fields surfaced by Plan 02"
    - "src/mcp_test_framework/cli.py -- added two Typer options (debug + quiet) to run(); default-mode branch now conditional-renders render_summary_only vs render_domain_ui, then optionally appends render_debug_appendix; --raw branch unchanged (raw mode bypasses all renderers)"
    - "tests/test_runner_subprocess.py -- flipped test_run_help_does_not_list_debug -> test_run_help_lists_debug (Plan 01 had pinned the absence as forward-reference; Plan 04 ships the flag so the invariant inverts). Rule 1 deviation."

key-decisions:
  - "render_summary_only and render_debug_appendix BOTH use file=None / call-time sys.stdout resolution. Matches the existing renderer pattern from Plan 03 (file=sys.stdout default would bind to pre-test stdout at function definition time, bypassing pytest's capsys fixture). The plan's action block had `file=sys.stdout` defaults; I switched to file=None to preserve capsys compatibility across the whole renderer module. Tracked as deviation Rule 1 below."
  - "--raw branch left UNTOUCHED: -q and --debug do not apply in raw mode. Raw passes everything to pytest verbatim; the operator chose to bypass the wrapper, so quiet/debug semantics belong to pytest's own flags inside that subprocess. test_run_raw_ignores_quiet_and_debug pins this."
  - "Test failure on Plan 01's test_run_help_does_not_list_debug treated as Rule 1 deviation (outdated forward-reference invariant), not a regression. Test renamed to enforce the new contract."

patterns-established:
  - "Additive verbosity ladder: lower-rung renderer emits its shape; upper-rung flag (e.g. --debug) appends MORE content after, never modifies the lower rung's output. Future flags (Phase 16's --explain) inherit this pattern."
  - "Forward-reference absence tests (pin that a NOT-YET-SHIPPED flag does not appear in --help). D-14's --explain absence is the canonical example; Phase 16 will flip this test to enforce presence when it ships --explain."

requirements-completed: [RUNNER-04]  # RUNNER-04 (verbosity ladder: quiet/default/debug) is now complete after Plan 03 shipped the default rung

# Metrics
duration: ~20min
completed: 2026-05-11
---

# Phase 14 Plan 04: Verbosity Ladder Summary

**Shipped the verbosity ladder for `mcp-test-framework run`: two new Typer-level flags (`-q`/`--quiet` and `--debug`) plus two new render helpers (`render_summary_only`, `render_debug_appendix`). Quiet mode prints only the summary line; debug mode appends raw pytest output and failure tracebacks AFTER whichever default/quiet rung produced. Both flags are orthogonal -- `-q --debug` is allowed and renders "summary, then appendix." Default-mode output is unchanged whether `--debug` is passed or not (D-13 invariant: each rung adds info; none re-shapes the layer below). `--explain` is NOT registered (D-14: Phase 16 owns it). RUNNER-04 is complete.**

## What Shipped

### `render_summary_only` (`_runner.py`)
- New helper that prints ONLY the SEED-011 §2 summary line (`Result: N PASS / M FAIL / S SKIP in T.Ts`).
- Reuses `_compose_unparametrized_skips_from_config` so state-(a)/(c) SKIPs count in the summary even when no header/rows are emitted (the quiet summary always agrees with the default summary).
- `file=None` default with call-time `sys.stdout` resolution: capsys-friendly, matching the rest of the renderer module.

### `render_debug_appendix` (`_runner.py`)
- New helper that emits the debug appendix in three sections, each omitted when empty:
  1. `--- raw pytest output ---` + captured_stdout verbatim (or `(no stdout captured)` if empty).
  2. `--- captured stderr ---` + captured_stderr verbatim (only when non-empty).
  3. `--- failure tracebacks ---` + per-tool failure bodies indented 2 spaces (only when at least one tool has a non-empty `failure_body`).
- Sorted alphabetically by tool name in the failure section for stable output.
- Surface-level separators are grep-pinned (regression tests assert `--- raw pytest output ---` appears in at least 3 test sites).

### `cli.py:run` flags
- `-q` / `--quiet` Typer option (D-12): swaps `render_domain_ui` -> `render_summary_only`. Not forwarded to pytest -- pytest runs at default verbosity internally so the JUnit XML stays complete.
- `--debug` Typer option (D-13): appends `render_debug_appendix(captured_stdout, captured_stderr, parsed)` AFTER whichever rung above ran. Default UI unchanged regardless of `--debug` (D-13 invariant).
- `--raw` branch unchanged: `-q` and `--debug` are no-ops in raw mode (raw bypasses all renderers).
- `--explain` is intentionally NOT registered in cli.py (D-14: Phase 16 owns it). Verified via `grep -n -- "--explain" cli.py` returning zero matches.

### Tests (`tests/test_runner_verbosity.py`)
- 13 tests total covering: render_summary_only output shape (no header / no rows), state-(a)/(c) skip count in quiet summary, render_debug_appendix separators + content, render_debug_appendix sections-omitted-when-empty invariant, CLI --help lists `-q`/`--quiet`/`--debug`, CLI --help does NOT list `--explain`, end-to-end CLI mocked-subprocess: quiet -> summary-only, default -> full UI, --debug -> UI + appendix in order, -q --debug -> summary + appendix in order, --raw -> bypasses all flags.
- All 13 pass. Plan 01/02/03 regression tests still pass (71 total runner tests).

## Deviations from Plan

### Rule 1 - Forward-reference test invalidated by this plan

**1. Flipped `test_run_help_does_not_list_debug` -> `test_run_help_lists_debug`**
- **Found during:** Task 3 verification (Plan 01..03 regression check).
- **Issue:** Plan 01's `tests/test_runner_subprocess.py::test_run_help_does_not_list_debug` pinned the ABSENCE of `--debug` in `run --help` with the docstring "Plan 04 adds --debug; Plan 01 must not expose it." Plan 04 now ships `--debug`, so the test's expectation became outdated by design.
- **Fix:** Renamed the test to `test_run_help_lists_debug` and inverted the assertion to require `--debug in result.output`. Updated docstring to cite Plan 04 / D-13.
- **Files modified:** `tests/test_runner_subprocess.py`
- **Commit:** 866ce25

### Rule 1 - Capsys-friendly file= default

**2. `file=None` instead of `file=sys.stdout` defaults**
- **Found during:** Task 1 implementation.
- **Issue:** The plan's action block specified `file=sys.stdout` defaults for both new helpers, but Plan 03's existing renderer functions (`_render_header`, `_render_per_tool_rows`, `_render_summary_line`, `render_domain_ui`) all use the `file=None` / call-time `sys.stdout` resolution pattern. Using `file=sys.stdout` defaults breaks pytest's `capsys` capture (the default binds to function-definition-time stdout, bypassing per-test stdout replacement).
- **Fix:** Both new helpers use `file=None` -> `if file is None: file = sys.stdout` at the top of the function body. Functionally identical for non-test callers; capsys-friendly inside the test suite.
- **Files modified:** `src/mcp_test_framework/_runner.py`
- **Commit:** a187fb2

## Auth Gates

None.

## Deferred Issues

The full `tests/` sweep surfaced 6 pre-existing failures in `tests/test_tool_config.py` and `tests/test_reporter.py` related to `target.tool_name` and schema-version mismatch when `MCPTF_CONFIG_FILE` overlays `version: 2` worktree config onto tests that construct bare `Config()` expecting v1 defaults. These failures reproduce against base `7d7780f8` (i.e., they are NOT caused by Plan 14-04). Out of scope per the SCOPE BOUNDARY rule. Plan 14-05 or a follow-up plan should triage them.

## TDD Gate Compliance

- **RED:** `test(14-04): add failing tests for verbosity ladder (-q / --debug)` (3ef4d23). Tests asserted; verified failing via stash-and-rerun.
- **GREEN (Task 1):** `feat(14-04): add render_summary_only + render_debug_appendix helpers` (a187fb2). 6 render-helper tests pass.
- **GREEN (Task 2):** `feat(14-04): wire -q/--quiet and --debug flags into cli.py:run` (9cc55c4). All 13 verbosity tests pass.

## Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| `grep -n "def render_summary_only" src/mcp_test_framework/_runner.py` -> exactly 1 match | PASS (1) |
| `grep -n "def render_debug_appendix" src/mcp_test_framework/_runner.py` -> exactly 1 match | PASS (1) |
| `--- raw pytest output ---` appears in _runner.py | PASS |
| `--- failure tracebacks ---` appears in _runner.py | PASS |
| `grep -n 'quiet: bool = typer.Option' cli.py` -> exactly 1 match | PASS (1) |
| `grep -n 'debug: bool = typer.Option' cli.py` -> exactly 1 match | PASS (1) |
| `grep -n -- "--explain" cli.py` -> ZERO matches (D-14) | PASS (0) |
| `run --help` lists `-q`, `--quiet`, `--debug` | PASS |
| `run --help` does NOT list `--explain` (D-14) | PASS |
| `run --help` still lists `--raw` (preserved) | PASS |
| `grep -c "^def test_" tests/test_runner_verbosity.py` >= 11 | PASS (13) |
| `grep -c -- "--- raw pytest output ---" tests/test_runner_verbosity.py` >= 3 | PASS (7) |
| All Plan 04 tests pass | PASS (13/13) |
| Plan 01/02/03 runner regression tests pass | PASS (71/71 after Rule 1 test rename) |

## Self-Check: PASSED

Verified:
- `src/mcp_test_framework/_runner.py` contains `render_summary_only` and `render_debug_appendix` definitions (1 each).
- `src/mcp_test_framework/cli.py` contains `quiet: bool = typer.Option` and `debug: bool = typer.Option` (1 each); zero `--explain` matches.
- `tests/test_runner_verbosity.py` exists with 13 test functions.
- All four task commits present in `git log --oneline`: 3ef4d23, a187fb2, 9cc55c4, 866ce25.
