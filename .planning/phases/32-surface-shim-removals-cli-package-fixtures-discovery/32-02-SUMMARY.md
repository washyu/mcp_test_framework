---
phase: 32-surface-shim-removals-cli-package-fixtures-discovery
plan: 02
subsystem: testing
tags: [shim-removal, typer-cli, operator-tone-error, v1.5, click-8.3]

# Dependency graph
requires:
  - phase: 32-01
    provides: "Operator-tone three-part error message template + first SHIM removal precedent (sdet package import)"
provides:
  - "Hard-rejecting `--sdet` CLI flag with `typer.BadParameter` + operator-tone three-part text pointing at `--test-code`"
  - "Pinned-text regression test `test_error_style_sdet_flag_removed` using `typer.testing.CliRunner`"
  - "Confirmation that README has zero `--sdet` mentions (Plan 32-01 already scrubbed)"
affects: [32-03, 32-04, 32-05, 32-06, 32-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hidden-intercept CLI flag: `hidden=True` + `is_eager=True` + body that raises -- keeps the option registered through the deprecation window so the operator-tone migration pointer is guaranteed (vs Typer's stock 'No such option' block)"
    - "Click 8.3 CliRunner compatibility: `mix_stderr` kwarg removed; output captured via `result.output` (combined by default)"

key-files:
  created: []
  modified:
    - "src/mcp_test_framework/cli.py - renamed _warn_sdet_flag -> _sdet_flag_removed (callback body flips from DeprecationWarning to typer.BadParameter raise); updated --sdet option help text; deleted dead sdet_legacy -> test_code coercion in run() body"
    - "tests/framework/unit/test_error_style.py - added test_error_style_sdet_flag_removed pinning the verbatim three-part text"

key-decisions:
  - "Plan's verify command used `CliRunner(mix_stderr=False)` which is incompatible with installed Click 8.3.3 (kwarg removed). Adapted test to use bare `CliRunner()` and pin against `result.output` (which captures combined streams). Behavior unchanged; only the inspection API moved."
  - "Reduced redundant `# noqa: sdet-rename-shim` markers on the option-registration block (kept only on `def` line + `callback=` line per plan's verbatim diff in Steps A and B). Plan Step E's `Decrease by exactly 1` heuristic was inconsistent with the plan's own verbatim diff -- deferred to the literal diff."
  - "Task 3 (README scrub) was a no-op-confirm. Plan 32-01 commit `a02b12b` already scrubbed every README `--sdet` reference. Grep returned zero matches; no commit required for Task 3."

patterns-established:
  - "Hidden-intercept SHIM removal: keep the CLI option registered through the next deprecation window (hidden=True) so the eager callback raises with an operator-tone pointer to the new flag, instead of Typer's stock 'No such option' block. Clean-delete deferred to the milestone after."

requirements-completed: [SHIM-02]

# Metrics
duration: ~13min
completed: 2026-05-25
---

# Phase 32 Plan 02: SHIM-02 `--sdet` CLI Flag Removal Summary

**Hard-reject `--sdet` CLI flag via Typer eager callback raising `typer.BadParameter` with operator-tone three-part message naming `--test-code`; option stays registered as hidden intercept per amended ROADMAP SC#2.**

## Performance

- **Duration:** ~13 min
- **Started:** 2026-05-25T00:23:29Z (Phase 32 execution started per STATE.md)
- **Completed:** 2026-05-25T00:36:27Z
- **Tasks:** 3 (2 code + 1 no-op-confirm)
- **Files modified:** 2 (cli.py + test_error_style.py)

## Accomplishments

- `_warn_sdet_flag` callback flipped from `DeprecationWarning` to `typer.BadParameter` raise (renamed `_sdet_flag_removed`)
- Verbatim three-part operator-tone text shipped: summary (`--sdet was removed in v1.5`) + body (rename history + behavior-unchanged note) + `next:` line (pointer at `--test-code`)
- Dead `if sdet_legacy: test_code = True` coercion block deleted from `run()` body (eager callback raises before body executes)
- Hidden-intercept invariant preserved per amended ROADMAP SC#2 (`hidden=True`, `is_eager=True`, body raises) — clean-delete deferred to v1.6 per CONTEXT D-04
- Pinned-text regression test added; full framework unit suite remains green (563 passed, 0 failed)

## Task Commits

1. **Task 1: Rewrite `_warn_sdet_flag` -> `_sdet_flag_removed` + delete coercion** — `0d11c0f` (feat)
2. **Task 2: Add pinned-text regression test** — `34fb524` (test)
3. **Task 3: README scrub** — no commit (no-op-confirm; README already clean post-Plan-32-01 `a02b12b`)

## Files Created/Modified

- `src/mcp_test_framework/cli.py` — renamed callback `_warn_sdet_flag` → `_sdet_flag_removed` with `typer.BadParameter` body; updated `--sdet` option `help=` text; deleted dead `if sdet_legacy:` coercion block in `run()`; pruned redundant noqa markers per plan's verbatim diff
- `tests/framework/unit/test_error_style.py` — added `test_error_style_sdet_flag_removed` pinning verbatim three-part operator-tone text via `CliRunner`

## Decisions Made

- **Click 8.3.3 CliRunner adaptation:** Plan's verify code and Task 2's specified test body used `CliRunner(mix_stderr=False)`, but the installed Click 8.3.3 dropped the `mix_stderr` kwarg (`TypeError` on construction). Adapted test to use bare `CliRunner()` and pin against `result.output` (which captures combined streams in Click 8.3). Documented in test docstring as a Click-version note. Behavior pinned is identical: exit code 2, all three-part substrings present.
- **Hidden-intercept preserved:** Per amended ROADMAP SC#2 (commit `c9481b1` referenced in plan must-haves), `--sdet` option remains registered (`hidden=True`); without registration, Typer would emit stock `No such option: --sdet` and the migration pointer would be lost. Clean-delete deferred to v1.6 per CONTEXT D-04.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Click 8.3 dropped `CliRunner(mix_stderr=False)` kwarg**
- **Found during:** Task 1 verify (and would have re-blocked Task 2 test as written)
- **Issue:** Plan's verify command and Task 2's specified test body construct `CliRunner(mix_stderr=False)`, which raises `TypeError: CliRunner.__init__() got an unexpected keyword argument 'mix_stderr'` on the installed Click 8.3.3. The kwarg was deprecated and removed.
- **Fix:** Use bare `CliRunner()` and pin against `result.output`, which captures combined stdout+stderr in Click 8.3 by default. Test docstring documents the Click 8.3 note.
- **Files modified:** `tests/framework/unit/test_error_style.py` (the test we wrote)
- **Verification:** `uv run pytest tests/framework/unit/test_error_style.py::test_error_style_sdet_flag_removed -xv` passes; the full framework unit suite (563 tests) remains green.
- **Committed in:** `34fb524` (Task 2 commit)

**2. [Rule 1 - Bug] Plan Step E marker-count heuristic inconsistent with plan's own verbatim diff**
- **Found during:** Task 1 (Step E verification)
- **Issue:** Plan Step E says "Decrease by exactly 1 (the coercion block's marker)" but Steps A and B's verbatim diffs show the rewritten callback body has zero `# noqa: sdet-rename-shim` markers (was ~10) and the option registration keeps markers only on the `def`/`callback=` lines (was 7). Following the literal diffs reduced the count by 18 (53 → 35), not 1.
- **Fix:** Deferred to the literal verbatim diffs in Steps A and B (those are the source of truth for code shape; Step E's count was a stale heuristic). Surviving markers correctly grandfather the hidden-intercept registration through v1.5 → v1.6.
- **Files modified:** `src/mcp_test_framework/cli.py`
- **Verification:** `grep -c "def _warn_sdet_flag"` → 0; `grep -c "def _sdet_flag_removed"` → 1; `grep -c "if sdet_legacy:"` → 0; planning-ID leak guard green.
- **Committed in:** `0d11c0f` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking — upstream library version drift; 1 plan-internal consistency — chose literal diff over stale count heuristic)
**Impact on plan:** Both deviations were necessary to land the plan's behavior contract. No scope creep — final code shape and tests match the plan's verbatim diffs in Steps A and B. The literal three-part operator-tone text is identical to the spec.

## Issues Encountered

- None beyond the deviations above. PowerShell shim mangling of bash command substitution intermittently broke the verify scripts; bypassed by running the assertions directly via `uv run python -c` and the Grep tool.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 32-02 (SHIM-02) closed. The hidden-intercept pattern is now established and reusable for SHIM-03 (`gen-sdet-classes` CLI shim, Plan 32-03) and SHIM-08 (`mcp-test-framework` console-script alias, Plan 32-06).
- The `sdet=test_code` kwarg threading into `_runner.run_pytest_subprocess` (cli.py L837 + L940) intentionally retained per plan Step D — that rename is SHIM-06's territory (Plan 32-04).
- No blockers for downstream Phase 32 waves.

## Verification Matrix

```
1. uv run pytest tests/framework/unit/test_error_style.py -x                          -> 10 passed
2. uv run pytest tests/framework/unit/test_error_style.py::test_error_style_sdet_flag_removed -xv -> PASSED
3. uv run pytest tests/framework/unit/ -x --tb=short                                  -> 563 passed, 0 failed
4. uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py -x               -> 1 passed
5. CliRunner invoke ['run', '--sdet']: exit_code=2 with full three-part text          -> PASS
6. grep -E "(Phase 32|Plan 32-02|SHIM-02|D-04)" src/mcp_test_framework/cli.py         -> 0 matches
7. README --sdet mention count                                                        -> 0 (Plan 32-01 scrub)
```

## Self-Check: PASSED

- `src/mcp_test_framework/cli.py` modified: FOUND (commit `0d11c0f`)
- `tests/framework/unit/test_error_style.py` modified: FOUND (commit `34fb524`)
- Commit `0d11c0f` in git log: FOUND
- Commit `34fb524` in git log: FOUND
- `_sdet_flag_removed` function exists in cli.py: FOUND (grep count = 1)
- `_warn_sdet_flag` removed: FOUND (grep count = 0)
- `if sdet_legacy:` deleted: FOUND (grep count = 0)
- Test `test_error_style_sdet_flag_removed` exists and passes: FOUND
- Hidden-intercept invariant preserved (`sdet_legacy: bool = typer.Option(..., "--sdet", hidden=True, ..., is_eager=True)` line retained): FOUND
- Three surviving `# noqa: sdet-rename-shim` markers on the `--sdet` surface in `cli.py` (def line, option-block def, option-block callback=): FOUND

---
*Phase: 32-surface-shim-removals-cli-package-fixtures-discovery*
*Completed: 2026-05-25*
