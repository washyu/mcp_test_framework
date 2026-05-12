---
phase: 16-reporter-ux-overhaul
plan: 01
subsystem: renderer
tags:
  - reporter
  - ux
  - renderer
  - pre-run-digest
  - explain
requires:
  - Phase 14 (_render_header, _compose_unparametrized_skips_from_config, RenderContext)
  - Phase 13 (_REASON_NOT_SELECTED, _REASON_EXPLICIT_DEFAULT locked constants)
provides:
  - CASES_PER_CONTRACT_TOOL module constant
  - _compose_pre_run_skip_reasons wrapper
  - _render_pre_run_digest pre-run renderer (banner + 5 label rows)
  - _render_skipped_tools_explain --explain renderer
  - render_domain_ui shrunk to per-tool rows + summary line only
affects:
  - tests/framework/test_runner_renderer.py (test_render_domain_ui_full_flow inverted)
  - tests/framework/test_runner_verbosity.py (two CLI e2e tests inverted for Plan 16-01 interim state)
tech-stack:
  added: []
  patterns:
    - file=None -> sys.stdout at call-time (capsys-friendly)
    - U+2014 em-dash literal separator
    - ljust(name_width) column-aligned tool names
    - sorted alphabetical iteration over grouped tools
key-files:
  created: []
  modified:
    - src/mcp_test_framework/_runner.py
    - tests/framework/test_runner_renderer.py
    - tests/framework/test_runner_verbosity.py
decisions:
  - "Filter state-b out of _compose_pre_run_skip_reasons by computing running set and passing as ran_tools (Rule 1 deviation from plan's literal 'thin wrapper with ran_tools=set()' spec — see Deviations)"
  - "Update two CLI e2e tests in verbosity suite to assert banner ABSENCE during Plan 16-01 interim state (Plan 16-02 will re-wire pre-run digest in cli.py and the assertions will need to flip back)"
metrics:
  duration_minutes: ~25
  completed_date: 2026-05-11
---

# Phase 16 Plan 01: Pre-run digest renderer Summary

Landed the four new module-level renderer symbols (one constant + three functions) inside `_runner.py` and removed the `_render_header` call site from `render_domain_ui`, shrinking post-run output to per-tool rows + summary line only. All four symbols are pure transforms over `RenderContext` — no new trust boundaries, no new I/O.

## What Changed

### New module-level symbols in `src/mcp_test_framework/_runner.py`

1. **`CASES_PER_CONTRACT_TOOL: int = 10`** (D-03) — module-level constant capturing the parametrized-cases-per-tool count (5 schema + 4 judge + 1 output conformance) used by the pre-run "Test plan" line.
2. **`_compose_pre_run_skip_reasons(discovered_tools, tools_config)`** (D-14) — wrapper over `_compose_unparametrized_skips_from_config` that exposes only state-(a) unlisted + state-(c) explicit-skip entries, filtering state-(b) tools (configured with `skip=False`) since those are running pre-run.
3. **`_render_pre_run_digest(ctx, with_framework=False, explain=False, file=None)`** (D-01/D-03/D-04/D-12) — pre-run digest emitting the banner + 5 label rows + trailing blank; height ≤ 11 lines at any N (verified at N=70). `with_framework=True` appends a `+ framework self-tests` continuation line. `explain=True` omits the `(use --explain to list)` hint since the list renders inline below.
4. **`_render_skipped_tools_explain(ctx, file=None)`** (D-05/D-13) — `--explain` expansion emitting `Skipping (N):` header + alphabetically-sorted `  <tool>  — <reason>` lines + trailing blank. U+2014 em-dash separator; ljust column-aligned tool names. Empty case emits `Skipping (0):` rather than silence.

### Call-site change

- **`render_domain_ui` no longer calls `_render_header`** (D-01). The function body of `_render_header` is preserved as an internal helper (Plan 16-02 may exercise it for renderer-shape regression tests). Docstring updated to reflect `per-tool rows -> summary line` order.

### Test updates (in-place, no new tests in Plan 01)

- `test_render_domain_ui_full_flow` — assertion inverted from `"MCP Test Framework" in out` to `"MCP Test Framework" not in out` + `"=" * 40 not in out`. Per-tool rows / SKIP-reason / summary assertions preserved.
- `test_run_default_renders_full_domain_ui` (verbosity suite, CLI e2e) — banner assertion flipped from `in` to `not in` for the Plan 16-01 interim state. Plan 16-02 will wire the pre-run digest in `cli.py` and this assertion will flip back.
- `test_run_debug_appends_appendix_after_domain_ui` — same interim-state flip; ordering check rewritten to compare `Result:` index against appendix index instead of header index against appendix index.

## Commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1    | c69facb | CASES_PER_CONTRACT_TOOL + _compose_pre_run_skip_reasons |
| 2    | 24dbf5c | _render_pre_run_digest pre-run renderer |
| 3    | ff27ea6 | _render_skipped_tools_explain + drop header from render_domain_ui + test inversions |

## Verification

- `uv run python -c "from mcp_test_framework._runner import CASES_PER_CONTRACT_TOOL, _render_pre_run_digest, _render_skipped_tools_explain, _compose_pre_run_skip_reasons; assert CASES_PER_CONTRACT_TOOL == 10"` exits 0.
- Smoke `python -c` blocks from each task's `<automated>` field all pass (banner, em-dash, sort order, state-b filter, with_framework continuation, explain hint suppression).
- N=70 sanity: digest height = 11 lines (10 content + trailing newline element), confirming D-12 invariant.
- `tests/framework/test_runner_renderer.py` (16 tests) all pass.
- `tests/framework/test_runner_verbosity.py` (13 tests) all pass after the two interim-state assertion flips.
- `tests/framework/unit/test_runner_parser.py` (24 tests) all pass.
- Combined: 53 tests pass; no test added in Plan 16-01.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_compose_pre_run_skip_reasons` spec contradicted its own smoke test**

- **Found during:** Task 3 verification (running the `<automated>` block in the plan)
- **Issue:** The plan specifies a "thin wrapper that delegates to `_compose_unparametrized_skips_from_config(..., ran_tools=set())`" but the Task-3 smoke test asserts `'Skipping (2):'` for a fixture with 3 discovered tools and 1 state-b configured tool. The literal `ran_tools=set()` delegation returns 3 entries (state-b tools are defensively re-labeled `_REASON_NOT_SELECTED` by the post-run composer when they don't appear in `ran_tools`), failing the smoke assertion.
- **Fix:** Compute the running set (state-b: in `tools_config` AND `skip != True`) and pass it as `ran_tools` to the underlying composer. This filters state-b out via the existing `if name in ran_tools: continue` clause, leaving only state-(a) unlisted + state-(c) explicit-skip entries — exactly what the plan's smoke test (and the plan prose `"every state-(a)/(c) skip"`) requires.
- **Files modified:** `src/mcp_test_framework/_runner.py` (`_compose_pre_run_skip_reasons` body)
- **Commit:** ff27ea6

**2. [Rule 3 - Blocking issue] Verbosity CLI e2e tests break under render_domain_ui header removal**

- **Found during:** Task 3 (full test-suite run after dropping `_render_header` call)
- **Issue:** Plan 16-01 Task 3 removes the `_render_header` call from `render_domain_ui` but Plan 16-02 (CLI wiring) is responsible for re-emitting the banner pre-run via `_render_pre_run_digest`. Between these plans, two end-to-end CLI tests in `test_runner_verbosity.py` (`test_run_default_renders_full_domain_ui` line 216, `test_run_debug_appends_appendix_after_domain_ui` line 236) assert `"MCP Test Framework" in result.output` and fail because the CLI orchestration has no banner emitter yet. The plan's stated verification step "test_runner_verbosity.py -x exits 0" was inconsistent with the plan's own changes.
- **Fix:** Updated the two failing tests to assert banner ABSENCE for the Plan 16-01 interim state, with comments documenting that Plan 16-02 will re-wire the banner via the pre-run digest and these assertions will need to flip back. The remaining verbosity tests (`-q` summary-only, `-q --debug`, `--raw`) already assert banner absence and pass unchanged.
- **Files modified:** `tests/framework/test_runner_verbosity.py`
- **Commit:** ff27ea6

## Deferred Issues

See `.planning/phases/16-reporter-ux-overhaul/deferred-items.md` — 6 pre-existing test failures in `test_tool_config.py`, `test_cli_errors.py`, and `test_migration_doc.py` are out of scope for Plan 16-01 (reproduced on the pre-task baseline via `git stash`). These are environmental config-default conflicts with the `MCPTF_CONFIG_FILE` workaround needed to bypass the conftest preflight, plus a path-resolution bug and a missing-doc test set, unrelated to Plan 16-01.

## Plan 16-02 Hooks

When Plan 16-02 wires `cli.py` to call `_render_pre_run_digest` and `_render_skipped_tools_explain`:

1. Pass `with_framework=with_framework` and `explain=explain` from the Typer `run` command signature — both parameters are already supported by the renderer.
2. Flip the two verbosity-test interim-state assertions back to `"MCP Test Framework" in result.output`.
3. Flip the ordering check in `test_run_debug_appends_appendix_after_domain_ui` from `Result:` vs appendix back to `MCP Test Framework` (header) vs appendix.
4. Consider deleting `_render_header` if no renderer-shape regression test references it — it has no remaining call sites in production code paths.

## Threat Flags

None. Plan 16-01 introduces no new trust boundaries, input sources, or persisted state. All new functions are pure transforms over the existing `RenderContext`.

## Self-Check: PASSED

**Files exist:**
- src/mcp_test_framework/_runner.py — FOUND (modified)
- tests/framework/test_runner_renderer.py — FOUND (modified)
- tests/framework/test_runner_verbosity.py — FOUND (modified)
- .planning/phases/16-reporter-ux-overhaul/deferred-items.md — FOUND

**Symbols importable:**
- `CASES_PER_CONTRACT_TOOL == 10` — FOUND
- `_compose_pre_run_skip_reasons` — FOUND
- `_render_pre_run_digest` — FOUND
- `_render_skipped_tools_explain` — FOUND
- `_render_header` — FOUND (preserved as internal helper)

**Commits exist:**
- c69facb — FOUND (Task 1)
- 24dbf5c — FOUND (Task 2)
- ff27ea6 — FOUND (Task 3)
