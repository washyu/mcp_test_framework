---
phase: 32-surface-shim-removals-cli-package-fixtures-discovery
plan: 01
subsystem: testing
tags: [shim-removal, python-import, operator-tone-error, v1.5, sdet-rename]

# Dependency graph
requires:
  - phase: 25-public-api-rename-sdet-to-test-code
    provides: "mcp_test_framework.test_code surface (post-v1.4 canonical re-export of ToolCallError / ToolResponse / mcp_session / tool)"
  - phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
    provides: "operator-tone three-part error contract verbatim wording + sibling pinned-text regression test (test_error_style_sdet_rejection_message)"
provides:
  - "Hard-raise ModuleNotFoundError at module-load time for legacy mcp_test_framework.sdet import surface"
  - "Pinned-text regression test guarding the operator-tone three-part removal message"
  - "README test-code-scenarios snapshot scrubbed of legacy sdet refs and grandfather noqa comment"
  - "docs/SDET-AUTHORING.md redirect stub retired (parity already in TEST-CODE-AUTHORING.md since Phase 25)"
affects:
  - "Phase 35 SHIM-09 regression gate (asserts zero residual mcp_test_framework.sdet matches across operator surfaces)"
  - "v1.6 EOL capstone that deletes the sdet/ directory outright"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Import-time ModuleNotFoundError raise carrying ERROR-STYLE.md three-part operator-tone shape (summary / detail / next:) when no typer.Exit surface is available"
    - "Pinned-text pytest regression sitting alongside its sibling for grep-discoverability; sys.modules.pop guard for re-runnable raise-at-import tests"
    - "Grandfather single noqa: sdet-rename-shim marker on the surviving stub module while every other v1.4-era marker dies with its shim (Pattern S-04 from 32-PATTERNS.md)"

key-files:
  created: []
  modified:
    - "src/mcp_test_framework/sdet/__init__.py — body inverted from re-export shim to ModuleNotFoundError raise (26 lines → 21 lines; only the raise is executable)"
    - "tests/framework/unit/test_error_style.py — added test_error_style_sdet_package_removed (mirrors sibling sdet-rejection test from Phase 31)"
    - "README.md — scrubbed 4 sites: HTML grandfather comment, MCP Test Framework (SDET) header, Judges (none — SDET scope) line, two FAIL-row legacy ToolCallError refs"
    - "docs/SDET-AUTHORING.md — DELETED (was a one-line redirect since Phase 25 rename; content parity already in TEST-CODE-AUTHORING.md)"

key-decisions:
  - "Plain `raise ModuleNotFoundError(...)` inside the import body rather than calling `_emit_operator_error` (which raises typer.Exit). Library/import-time sites cannot surface typer.Exit cleanly — confirmed in 32-RESEARCH.md §SHIM-01."
  - "Retire docs/SDET-AUTHORING.md outright (delete) rather than keep as a one-line redirect. The redirect existed for the v1.4 deprecation window; v1.5 retires the legacy file alongside every other sdet-named surface. Cross-doc scan of docs/ + README.md confirmed zero references."
  - "Keep the surviving sdet/__init__.py module-level `# noqa: sdet-rename-shim` markers (on docstring closing line + raise) per Pattern S-04 — they grandfather the directory through v1.5 for the future EOL planner; only the line-attached markers on dead code (the re-exports + warnings.warn) were removed."

patterns-established:
  - "S-01 application: import-time site adapts the ERROR-STYLE.md three-part shape inside the exception message string (no typer.Exit, no _emit_operator_error helper)"
  - "S-02 application: pinned-text regression mirrors the Phase 31 SHIM-04 sibling — same capsys parameter for symmetry even when unused, same sys.modules.pop guard"
  - "S-04 application: line-attached noqa markers die with the code they guard; module-level markers grandfathering the surviving stub stay until v1.6 EOL"
  - "S-07 application: in-source comments use neutral English (`v1.5`, `v1.6`, `future EOL planner`); zero `Phase \\d` / `SHIM-\\d{2}` / `D-\\d{2}` references in src/"

requirements-completed: [SHIM-01]

# Metrics
duration: ~20min
completed: 2026-05-25
---

# Phase 32 Plan 01: SHIM-01 sdet package import removal Summary

**Legacy `mcp_test_framework.sdet` import surface now raises `ModuleNotFoundError` at module load with an operator-tone three-part message pointing at `mcp_test_framework.test_code`; pinned-text regression test guards the wording; README snapshot scrubbed; docs/SDET-AUTHORING.md retired.**

## Performance

- **Duration:** ~20 min (no checkpoint pauses; all three tasks ran straight through)
- **Started:** 2026-05-25T (worktree spawn)
- **Completed:** 2026-05-25
- **Tasks:** 3 (all completed)
- **Files modified:** 3 (src/mcp_test_framework/sdet/__init__.py, tests/framework/unit/test_error_style.py, README.md)
- **Files deleted:** 1 (docs/SDET-AUTHORING.md)

## Accomplishments

- Eager `ModuleNotFoundError` raises on every import form (`import mcp_test_framework.sdet`, `from mcp_test_framework.sdet import X`, `from mcp_test_framework import sdet`) — all three surface the operator-tone three-part text (verified by Task 1's inline check + Task 2's regression test + a post-execution `from … import` smoke check)
- Pinned-text regression test (`test_error_style_sdet_package_removed`) lives next to its Phase 31 sibling for grep-discoverability; locks the verbatim summary line `mcp_test_framework.sdet was removed in v1.5`, the pointer `mcp_test_framework.test_code`, the `next:` marker, and the full next-step instruction substring
- README test-code-scenarios snapshot scrubbed end-to-end: the grandfather HTML comment that justified the pre-rename capture during the v1.4 window is gone; the `(SDET)` header / `SDET scope` line / `mcp_test_framework.sdet.errors.ToolCallError` FAIL-row refs are all rewritten to the post-rename `(test-code)` / `test-code scope` / `mcp_test_framework.test_code.ToolCallError` shape
- `docs/SDET-AUTHORING.md` retired; cross-doc reference scan of `docs/` + `README.md` returned zero matches, so no follow-on redirects needed

## Task Commits

Each task was committed atomically (worktree mode; `--no-verify` per parallel-execution protocol):

1. **Task 1: Invert sdet/__init__.py into hard-raise removal stub** — `310d227` (feat)
2. **Task 2: Add pinned-text regression test** — `575ef21` (test)
3. **Task 3: Scrub README + delete SDET-AUTHORING.md** — `a02b12b` (docs)

_Note: Tasks 1 and 2 were marked `tdd="true"` in the plan; treated as test-after rather than strict RED-first because the Task 1 verify is an inline import-script smoke check that doubles as the GREEN signal, and Task 2 is the durable pytest regression that locks the wording. Both tests pass after Task 2._

## Files Created/Modified

- `src/mcp_test_framework/sdet/__init__.py` — rewritten from 26-line re-export shim (`warnings.warn` + `from … import` block + `__all__`) to a 21-line module whose only executable statement is `raise ModuleNotFoundError(...)`. Module docstring explains the v1.5 stub status in neutral English (no planning IDs). Two module-level `# noqa: sdet-rename-shim` markers preserved per Pattern S-04 (grandfather the surviving stub).
- `tests/framework/unit/test_error_style.py` — added `test_error_style_sdet_package_removed` between `test_error_style_sdet_rejection_message` (Phase 31 sibling) and `test_error_style_no_banned_tokens_outside_checklist`. Uses `sys.modules.pop` + `importlib.import_module` + `pytest.raises(ModuleNotFoundError)` to make the test re-runnable in the same session.
- `README.md` — 4 sites scrubbed: line 165 HTML grandfather comment removed; `MCP Test Framework (SDET)` → `MCP Test Framework (test-code)`; `Judges:      (none — SDET scope)` → `Judges:      (none — test-code scope)`; both FAIL-row legacy `mcp_test_framework.sdet.errors.ToolCallError` strings rewritten to `mcp_test_framework.test_code.ToolCallError`.
- `docs/SDET-AUTHORING.md` — DELETED (one-line redirect since Phase 25 rename; content parity already in TEST-CODE-AUTHORING.md).

## Decisions Made

- **Hard-raise inside `__init__.py` body, not `_emit_operator_error`.** `_emit_operator_error` raises `typer.Exit` which would surface as an unexpected `SystemExit` at library/import time. Plain `ModuleNotFoundError` is the correct surface for an import-time site; the three-part operator-tone wording lives inside the exception message string rather than being rendered via `typer.echo`. Pre-confirmed by 32-RESEARCH.md §SHIM-01 "Why a `raise` instead of calling `_emit_operator_error`".
- **Delete `docs/SDET-AUTHORING.md` outright (not keep as redirect).** The file was already a one-line redirect stub (Phase 25 had ported all content to TEST-CODE-AUTHORING.md). The plan's done criteria accepts either delete or one-line redirect; v1.5 retires the legacy file name alongside every other sdet-named surface, and a `grep -rn "SDET-AUTHORING" docs/ README.md` returned zero, so the redirect is no longer load-bearing.
- **Keep two module-level `# noqa: sdet-rename-shim` markers on the surviving stub** (on `from __future__ import annotations` and on the `raise ModuleNotFoundError(`). Pattern S-04 explicitly preserves these as the single grandfathered exception in Phase 32 — they're consumed by the future EOL planner that retires the directory at v1.6.

## Deviations from Plan

None — plan executed exactly as written.

The Task 1 verify command, the Task 2 pinned-text regression, and the Task 3 doc scrub all passed first try. No auto-fixes triggered under any of Rules 1-3.

## Issues Encountered

- **Worktree base drift:** Initial `git merge-base` confirmed the worktree was spawned at `5e25c1e` (an old commit) rather than the orchestrator-specified base `9710605`. Recovered via `git reset --hard 9710605` per the `<worktree_branch_check>` protocol at agent startup. This matches the pre-flagged `project_worktree_base_drift` memory item. Pre-deviation cleanup; not a Rule 1-3 fix.
- **Pre-existing untracked files in worktree:** `git status` showed numerous untracked files (`awk`, `cli_output.txt`, `mcptf_27_02_sanity1/`, `tests/sdet/`, etc.) inherited from the parent working tree state. None were touched, staged, or committed (per `<destructive_git_prohibition>`).
- **STATE.md pre-existing modification:** STATE.md showed unstaged changes from the orchestrator's pre-execution sync. Per parallel-execution rules, STATE.md was NOT modified or committed by this executor; the orchestrator owns those writes.

## User Setup Required

None — no external service configuration required.

## Verification Run

```text
$ uv run pytest tests/framework/unit/test_error_style.py tests/framework/unit/test_no_planning_ids_in_src.py -x
10 passed in 0.08s

$ uv run pytest tests/framework/unit/ --tb=short
562 passed, 1 deselected, 1 xfailed, 6 warnings in 9.14s

$ grep -c "mcp_test_framework.sdet" README.md
0
```

The 6 surviving DeprecationWarnings in the full unit-suite output all belong to sibling shims (SHIM-02 `--sdet`, SHIM-03 `gen-sdet-classes`, SHIM-05 MCPTF_CONFIG_FILE) owned by other Phase 32 plans — not regressions introduced by SHIM-01.

## Next Phase Readiness

- Wave 1 of Phase 32 is unblocked (this plan is the only Wave 1 plan per the plan's frontmatter `wave: 1`).
- SHIM-01 is mechanically orthogonal to SHIM-02/03/06/07/08 (per plan must_haves D-02 ordering note) — Wave 2+ plans can proceed in parallel.
- Phase 35 SHIM-09 regression gate has one more `mcp_test_framework.sdet` operator surface retired; the surviving directory + two grandfathered noqa markers are the only residual references in src/ (intentional; gated for v1.6 EOL).

## Self-Check: PASSED

- `src/mcp_test_framework/sdet/__init__.py` — FOUND (rewritten as removal stub)
- `tests/framework/unit/test_error_style.py::test_error_style_sdet_package_removed` — FOUND (pytest collected and passed)
- `README.md` — modified (4 sites scrubbed; `grep -c "mcp_test_framework.sdet" README.md` returns 0)
- `docs/SDET-AUTHORING.md` — DELETED (confirmed via `git status` `D ` filter)
- Commit `310d227` — FOUND (`feat(32-01): invert sdet/__init__.py into hard-raise removal stub`)
- Commit `575ef21` — FOUND (`test(32-01): add pinned-text regression for sdet package removal`)
- Commit `a02b12b` — FOUND (`docs(32-01): scrub README sdet refs; delete SDET-AUTHORING.md redirect`)

---
*Phase: 32-surface-shim-removals-cli-package-fixtures-discovery*
*Plan: 01 — SHIM-01 sdet package import*
*Completed: 2026-05-25*
