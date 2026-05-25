---
phase: 32-surface-shim-removals-cli-package-fixtures-discovery
plan: 03
subsystem: cli
tags: [shim-removal, typer-cli, operator-tone-error, v1.5, click-8.3]

# Dependency graph
requires:
  - phase: 32-02
    provides: "Hidden-intercept SHIM removal pattern (CLI surface) + Click 8.3 CliRunner.output convention established by test_error_style_sdet_flag_removed"
provides:
  - "Hard-rejecting `gen-sdet-classes` Typer command with `typer.BadParameter` + operator-tone three-part text pointing at `gen-test-classes`"
  - "Pinned-text regression test `test_error_style_gen_sdet_classes_removed` using `typer.testing.CliRunner`"
  - "Confirmation that README has zero `gen-sdet-classes` mentions (already absent at plan start)"
affects: [32-04, 32-05, 32-06, 32-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hidden-intercept CLI command: `@app.command(name, hidden=True)` + body that raises typer.BadParameter -- keeps the command registered through the deprecation window so the operator-tone migration pointer is guaranteed (vs Typer's stock 'No such command' block). Sibling to the hidden-intercept option pattern established by 32-02."
    - "Click 8.3 CliRunner: bare `CliRunner()` + `result.output` (combined streams), avoiding the removed `mix_stderr` kwarg. Re-used from 32-02."

key-files:
  created: []
  modified:
    - "src/mcp_test_framework/cli.py - replaced _gen_sdet_classes_shim warn-then-delegate body with _gen_sdet_classes_removed raising typer.BadParameter; removed inline `import warnings`, `warnings.warn(...)`, and `gen_test_classes(config=config)` delegation; `--config` option preserved (hidden=True) so legacy argv parses through to the body; pruned 19 in-body `# noqa: sdet-rename-shim` markers (only the decorator marker survives, grandfathering the hidden command through v1.5)"
    - "tests/framework/unit/test_error_style.py - added test_error_style_gen_sdet_classes_removed pinning the verbatim three-part text via CliRunner"
    - "tests/framework/unit/test_gen_sdet_classes_cli.py - retargeted four tests from gen-sdet-classes (now hard-rejecting) to canonical gen-test-classes; updated test_help_lists_flags docstring to note the alias removal"
    - "tests/framework/unit/test_gen_sdet_classes_config_driven.py - retargeted two tests from gen-sdet-classes to gen-test-classes; updated module docstring to reflect the closed v1.4 deprecation window; rejection-message assertion now pins the v1.5 'test_code' field name instead of the removed 'sdet' alias"

key-decisions:
  - "Plan's Task 2 specified test body used `CliRunner(mix_stderr=False)` (incompatible with Click 8.3.3); adapted to bare `CliRunner()` + `result.output` per the convention established by 32-02. Behavior pinned is identical: exit code 2, all three-part substrings present."
  - "Three pre-existing tests in `test_gen_sdet_classes_cli.py` and one in `test_gen_sdet_classes_config_driven.py` were intentional v1.4-deprecation-window coverage that invoked the legacy alias to drive code paths in gen-test-classes. SHIM-03 closes that window. Retargeted in-place at the canonical `gen-test-classes` command rather than deleted -- preserves the underlying coverage (help-listing, missing-MCP operator-tone, missing-test_code-generated_root config validation) without scope creep."

patterns-established:
  - "Hidden-intercept SHIM removal at the CLI command level: keep the @app.command registration with hidden=True, replace the body with a typer.BadParameter raise carrying the operator-tone three-part text. Argv dispatches into the body; the migration pointer is guaranteed. Mirrors the 32-02 option-level pattern."
  - "Deprecation-window coverage retargeting: when a v1.x deprecation window closes, in-place retarget tests that intentionally exercised the shim at the canonical replacement surface instead of deleting them -- preserves the regression coverage for the underlying behavior."

requirements-completed: [SHIM-03]

# Metrics
duration: ~18min
completed: 2026-05-25
---

# Phase 32 Plan 03: SHIM-03 `gen-sdet-classes` CLI Command Removal Summary

**Invert `gen-sdet-classes` hidden Typer command from warn-then-delegate to a hard-rejecting body raising `typer.BadParameter` with an operator-tone three-part message naming `gen-test-classes`. Command stays registered as `hidden=True` per amended ROADMAP SC#2; `--config` preserved (hidden=True) so legacy argv parses through to the body.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-05-25 (Phase 32 Wave 3 spawn)
- **Completed:** 2026-05-25
- **Tasks:** 3 (2 code + 1 no-op-confirm) + 1 auto-fix deviation commit
- **Files modified:** 4 (cli.py + test_error_style.py + two legacy-shim-coverage test files)

## Accomplishments

- `_gen_sdet_classes_shim` warn-then-delegate body replaced with `_gen_sdet_classes_removed` raising `typer.BadParameter` (exit 2)
- Verbatim three-part operator-tone text shipped: summary (`gen-sdet-classes was removed in v1.5`) + body (rename history + flags-unchanged note) + `next:` line (`invoke \`mcp-contracts gen-test-classes\` (same flags)`)
- `import warnings` + `warnings.warn(...)` + `gen_test_classes(config=config)` delegation deleted from body
- `--config` option preserved (`hidden=True`) so legacy argv `gen-sdet-classes --config foo.yaml` parses cleanly to the body raise
- Hidden-intercept invariant preserved per amended ROADMAP SC#2 (`@app.command("gen-sdet-classes", hidden=True)`) -- clean-delete deferred to v1.6 per CONTEXT D-04
- Surviving `# noqa: sdet-rename-shim` marker scoped to the decorator line only (19 in-body markers deleted alongside the warn/delegate code paths)
- Pinned-text regression test added; full framework unit suite remains green (564 passed, 0 failed)
- `gen-test-classes` canonical command verified unchanged (CliRunner --help exit 0)

## Task Commits

1. **Task 1: Invert `_gen_sdet_classes_shim` body into hard-raise `_gen_sdet_classes_removed`** -- `ff48edd` (feat)
2. **Task 2: Add pinned-text regression test** -- `3d6e55b` (test)
3. **Task 3: README sweep** -- no commit (no-op-confirm; README already had zero `gen-sdet-classes` mentions at plan start)
4. **Deviation auto-fix: Retarget legacy shim tests** -- `d6c86ec` (test)

## Files Created/Modified

- `src/mcp_test_framework/cli.py` -- renamed function `_gen_sdet_classes_shim` -> `_gen_sdet_classes_removed`; body now raises `typer.BadParameter`; `--config` option kept with `hidden=True`; net 19 noqa markers removed from the body, 1 surviving on the decorator
- `tests/framework/unit/test_error_style.py` -- added `test_error_style_gen_sdet_classes_removed` pinning verbatim three-part operator-tone text via `CliRunner`
- `tests/framework/unit/test_gen_sdet_classes_cli.py` -- retargeted 4 invocations (`test_help_lists_flags`, `test_no_config_safe03_fails_loud`, `test_config_path_not_found_fails_loud`, `test_mcp_command_not_on_path_operator_error`, plus the deselected `test_live_homelab_emit_smoke`) from the legacy alias to canonical `gen-test-classes`
- `tests/framework/unit/test_gen_sdet_classes_config_driven.py` -- retargeted 2 invocations (`test_help_does_not_mention_legacy_hardcoded_path`, `test_missing_sdet_generated_root_exits_2`) and updated module docstring; rejection-message pin now reads `test_code` (v1.5 field name) instead of `sdet`

## Decisions Made

- **Click 8.3.3 CliRunner adaptation:** Plan's Task 2 action specified `CliRunner(mix_stderr=False)` plus separate `result.stdout`/`result.stderr` reads, but installed Click 8.3.3 dropped the `mix_stderr` kwarg. Adapted to bare `CliRunner()` + `result.output` per the convention 32-02 already established for SHIM-02 (`test_error_style_sdet_flag_removed` at L167-192). The Task 1 inline verify script was also adjusted to match. Behavior pinned is identical.
- **Hidden-intercept preserved:** Per amended ROADMAP SC#2 (commit `c9481b1`), the `gen-sdet-classes` command remains registered (`hidden=True`). Without registration, Typer would emit stock `No such command: gen-sdet-classes` block and the migration pointer would be lost. Clean-delete deferred to v1.6 per CONTEXT D-04.
- **No-op README sweep:** Pre-execution grep of `README.md` returned zero `gen-sdet-classes` matches. No edit, no commit -- recorded as no-op-confirm in this summary.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Click 8.3 dropped `CliRunner(mix_stderr=False)` kwarg**
- **Found during:** Task 1 inline verify script and Task 2 test scaffolding
- **Issue:** Plan's literal test body for Task 2 constructed `CliRunner(mix_stderr=False)` and read `result.stdout`/`result.stderr` separately. Click 8.3.3 (installed) removed the kwarg -- the construction raises `TypeError` and the separate-stream reads don't exist.
- **Fix:** Use bare `CliRunner()` and pin against `result.output` (combined stream). Re-used the convention 32-02 already established for SHIM-02. Test docstring left neutral.
- **Files modified:** `tests/framework/unit/test_error_style.py` (the test we wrote)
- **Verification:** `uv run pytest tests/framework/unit/test_error_style.py::test_error_style_gen_sdet_classes_removed -xv` passes.
- **Committed in:** `3d6e55b` (Task 2 commit)

**2. [Rule 1 - Bug] Legacy v1.4-window coverage tests fail post-Task-1**
- **Found during:** Full-suite verification after Task 1 + Task 2 commits
- **Issue:** Three tests (`test_help_lists_flags`, `test_mcp_command_not_on_path_operator_error` in `test_gen_sdet_classes_cli.py`; `test_missing_sdet_generated_root_exits_2` in `test_gen_sdet_classes_config_driven.py`) were intentional v1.4-deprecation-window coverage. They invoked `gen-sdet-classes` to drive code paths inside the delegated body (help-listing with `--config` visible, FileNotFoundError operator-tone branch, missing-test_code-generated_root config-validation branch). With SHIM-03's hard-rejection body, those paths never fire -- the tests hit BadParameter exit 2 instead of the expected behavior.
- **Fix:** Retargeted the invocations to the canonical `gen-test-classes` command (the actual code paths under test). The legacy alias removal itself is now covered by the new SHIM-03 regression test added in Task 2. Updated `test_help_lists_flags` docstring to note the alias removal explanation (alias's `--config` is now `hidden=True` so it no longer appears in `--help`, which is by design). Updated `test_missing_sdet_generated_root_exits_2` assertion from substring `sdet` to substring `test_code` (the v1.5 canonical field name surfaced by the rejection message).
- **Files modified:** `tests/framework/unit/test_gen_sdet_classes_cli.py`, `tests/framework/unit/test_gen_sdet_classes_config_driven.py`
- **Verification:** Both files now pass cleanly; full framework unit suite ends at 564 passed / 0 failed / 1 deselected / 1 xfailed / 2 warnings.
- **Committed in:** `d6c86ec`

---

**Total deviations:** 2 auto-fixed (1 blocking -- upstream library version drift, same as 32-02; 1 bug -- direct consequence of Task 1's body inversion on plan-scope legacy-window coverage)
**Impact on plan:** Both deviations were necessary to land the plan's behavior contract and keep the full framework unit suite green. No scope creep -- final code shape matches the plan's verbatim diff in Task 1. The literal three-part operator-tone text is identical to the spec.

## Issues Encountered

- None beyond the deviations above. PowerShell verify script syntax mangled when nested under bash heredoc; bypassed by using the Grep tool directly.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness

- Plan 32-03 (SHIM-03) closed. The CLI command-level hidden-intercept pattern is now established alongside 32-02's option-level pattern. Reusable for SHIM-08 (`mcp-test-framework` console-script alias, Plan 32-06).
- The `_codegen.py` AUTOGENERATED header marker still emits `gen-sdet-classes`; that terminology lives in `_codegen.py` and is owned by Plan 32-06's terminology sweep (out of 32-03 scope).
- No blockers for downstream Phase 32 waves.

## Verification Matrix

```
1. uv run pytest tests/framework/unit/test_error_style.py -x                                          -> 11 passed
2. uv run pytest tests/framework/unit/test_error_style.py::test_error_style_gen_sdet_classes_removed -xv -> PASSED
3. uv run pytest tests/framework/unit/ --tb=short                                                     -> 564 passed, 0 failed, 1 deselected, 1 xfailed
4. uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py -x                               -> 1 passed
5. CliRunner invoke ['gen-sdet-classes']: exit_code=2 + verbatim three-part text                     -> PASS
6. CliRunner invoke ['gen-sdet-classes', '--config', 'nonexistent.yaml']: exit_code=2 + same text     -> PASS
7. CliRunner invoke ['gen-test-classes', '--help']: exit_code=0 (canonical command unchanged)         -> PASS
8. grep -E "(Phase 32|Plan 32-03|SHIM-03|D-04)" src/mcp_test_framework/cli.py                         -> 0 matches
9. grep -c "def _gen_sdet_classes_shim" src/mcp_test_framework/cli.py                                 -> 0
10. grep -c "def _gen_sdet_classes_removed" src/mcp_test_framework/cli.py                             -> 1
11. README gen-sdet-classes mention count                                                             -> 0
```

## Self-Check: PASSED

- `src/mcp_test_framework/cli.py` modified: FOUND (commit `ff48edd`)
- `tests/framework/unit/test_error_style.py` modified: FOUND (commit `3d6e55b`)
- `tests/framework/unit/test_gen_sdet_classes_cli.py` modified: FOUND (commit `d6c86ec`)
- `tests/framework/unit/test_gen_sdet_classes_config_driven.py` modified: FOUND (commit `d6c86ec`)
- Commit `ff48edd` in git log: FOUND
- Commit `3d6e55b` in git log: FOUND
- Commit `d6c86ec` in git log: FOUND
- `_gen_sdet_classes_removed` function exists in cli.py: FOUND (grep count = 1)
- `_gen_sdet_classes_shim` removed: FOUND (grep count = 0)
- `warnings.warn(...)` body deleted: FOUND (no warn-then-delegate body in `_gen_sdet_classes_removed`)
- `gen_test_classes(config=config)` delegation deleted: FOUND (no delegation call inside the new body; the canonical `gen_test_classes` function itself is untouched)
- Test `test_error_style_gen_sdet_classes_removed` exists and passes: FOUND
- Hidden-intercept invariant preserved (`@app.command("gen-sdet-classes", hidden=True)` line retained): FOUND
- Surviving `# noqa: sdet-rename-shim` marker scoped to the decorator only (19 in-body markers removed): FOUND
- README `gen-sdet-classes` count: 0 (at most 1 required)

---
*Phase: 32-surface-shim-removals-cli-package-fixtures-discovery*
*Completed: 2026-05-25*
