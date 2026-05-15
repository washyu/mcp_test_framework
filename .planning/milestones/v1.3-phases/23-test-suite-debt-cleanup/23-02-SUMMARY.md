---
phase: 23-test-suite-debt-cleanup
plan: 02
subsystem: testing
tags: [pytest, path-resolution, parents, regression-test, framework-self-tests]

# Dependency graph
requires:
  - phase: 15-operator-vs-framework-test-surface-split
    provides: tests/framework/unit/ folder split that broke parents[2] depth
  - phase: 23-test-suite-debt-cleanup-plan-01
    provides: Cluster B red-test inventory (5 fails) and D-04 mechanical-bump strategy
provides:
  - Cluster B (parents[N] off-by-one) closed: all 5 reds in test_migration_doc.py and test_cli_errors.py go green
  - parents[3] resolution at the two depth-3 sites under tests/framework/unit/
affects: [phase-23-plan-final-close-gate, future-tests-framework-additions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Heterogeneous parents[N] vs walk-to-pyproject path-resolution styles intentionally retained per D-04"

key-files:
  created: []
  modified:
    - tests/framework/unit/test_migration_doc.py
    - tests/framework/unit/test_cli_errors.py

key-decisions:
  - "Mechanical one-line bump only — parents[2] -> parents[3] at exactly two sites; no shared helper, no walk-to-pyproject refactor (Phase 23 D-04)"
  - "Misleading 'Walk up...' comment in test_cli_errors.py left untouched per D-04 — heterogeneous styles + minor comment drift acceptable in debt-cleanup phase"

patterns-established:
  - "Pattern S3 applied: depth-3 files under tests/framework/unit/ use parents[3]"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-05-15
---

# Phase 23 Plan 02: Cluster B parents[2] -> parents[3] Bump Summary

**Mechanical one-line edits at tests/framework/unit/test_migration_doc.py:14 and tests/framework/unit/test_cli_errors.py:407 — closes Cluster B (5 reds) by bumping repo-root depth post Phase 15 folder split.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-15T04:07:38Z
- **Completed:** 2026-05-15T04:09:30Z (approx)
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `tests/framework/unit/test_migration_doc.py:15` `parents[2]` -> `parents[3]` (the `_repo_root()` body)
- `tests/framework/unit/test_cli_errors.py:407` `parents[2]` -> `parents[3]` (inside `test_cli_errors_static_call_sites_no_banned_tokens`)
- 5 Cluster B reds (4 in test_migration_doc.py + 1 in test_cli_errors.py) all go green; 24/24 tests pass across the two files

## Task Commits

Each task was committed atomically:

1. **Task 1: Bump test_migration_doc.py parents[2] -> parents[3] at line 15** — `4d4c27d` (fix)
2. **Task 2: Bump test_cli_errors.py parents[2] -> parents[3] at line 407** — `141a59d` (fix)

## Files Created/Modified

- `tests/framework/unit/test_migration_doc.py` — bumped depth in `_repo_root()` so MIGRATION_DOC resolves to `<repo>/docs/MIGRATION-v1-to-v2.md` (not `tests/docs/MIGRATION-v1-to-v2.md`)
- `tests/framework/unit/test_cli_errors.py` — bumped depth in `test_cli_errors_static_call_sites_no_banned_tokens` so the AST scan reads `<repo>/src/mcp_test_framework/cli.py` (not `tests/src/mcp_test_framework/cli.py`)

## Pre/Post Test Results

**Pre-fix** (`uv run pytest tests/framework/unit/test_migration_doc.py tests/framework/unit/test_cli_errors.py --tb=no -q`):
```
FFFF...................F                                                 [100%]
FAILED tests/framework/unit/test_migration_doc.py::test_migration_doc_exists
FAILED tests/framework/unit/test_migration_doc.py::test_migration_doc_pins_v2_keywords
FAILED tests/framework/unit/test_migration_doc.py::test_migration_doc_uses_ascii_dashes_not_emdash
FAILED tests/framework/unit/test_migration_doc.py::test_migration_doc_does_not_leak_planning_ids
FAILED tests/framework/unit/test_cli_errors.py::test_cli_errors_static_call_sites_no_banned_tokens
5 failed, 19 passed in 0.48s
```

**Post-fix:**
```
........................                                                 [100%]
24 passed in 0.24s
```

All 5 Cluster B reds resolved.

## Exact Line Numbers Patched

| File | Line | Before | After |
|------|------|--------|-------|
| `tests/framework/unit/test_migration_doc.py` | 15 | `return Path(__file__).resolve().parents[2]` | `return Path(__file__).resolve().parents[3]` |
| `tests/framework/unit/test_cli_errors.py` | 407 | `repo_root = Path(__file__).resolve().parents[2]` | `repo_root = Path(__file__).resolve().parents[3]` |

Each diff is exactly one line changed.

## Decisions Made

- **Followed D-04 verbatim:** mechanical bump only. Did NOT extract a shared helper, did NOT switch to the walk-to-`pyproject.toml` style used in `test_doc_scrub.py:16-21`, did NOT touch the (slightly misleading) "Walk up from this test file..." comment in test_cli_errors.py.

## Deviations from Plan

None - plan executed exactly as written. Both tasks were single-line edits matching the BEFORE/AFTER snippets in the plan, verified one site each via Grep before editing.

## Issues Encountered

- **Worktree base mismatch:** worktree HEAD was on `5e25c1e` (v1.1 milestone, pre Phase 15 — `tests/framework/unit/` folder did not exist). Per the agent prompt's `<worktree_branch_check>` block, hard-reset to the prescribed base `8d269ef`. After reset, target files existed at expected paths. No further issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Cluster B is closed.
- Cluster A (5 fails + 1 error from `Config()` bare-construction) and Cluster C (README content drift) are independent and remain in scope for sibling Plan(s) in Phase 23.
- The phase-final close-gate plan (D-08) can now expect Cluster B to contribute 0 reds in the `uv run pytest tests/framework/ --tb=no -q` baseline.

## Self-Check: PASSED

- `tests/framework/unit/test_migration_doc.py` exists — FOUND
- `tests/framework/unit/test_cli_errors.py` exists — FOUND
- Commit `4d4c27d` exists — FOUND
- Commit `141a59d` exists — FOUND
- Both diffs are exactly one line each — VERIFIED via `git diff` post-edit

---
*Phase: 23-test-suite-debt-cleanup*
*Completed: 2026-05-15*
