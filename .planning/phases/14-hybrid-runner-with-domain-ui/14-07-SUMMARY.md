---
phase: 14-hybrid-runner-with-domain-ui
plan: 07
subsystem: tests/regression-pins
status: complete
tags: [gap-closure, safe-01, v1.1.1, patch-seam-migration, phase-14]
dependency_graph:
  requires:
    - 14-05 (cache migration from _reporter to _runner)
    - 13 (SAFE-01 v1.1.1 skip-filter semantics)
  provides:
    - SAFE-01 v1.1.1 skip-filter regression coverage restored on the new cache seam
    - Permanent audit pin preventing future plans from re-introducing the dead seam
  affects:
    - tests/test_tool_config.py
tech_stack:
  added: []
  patterns:
    - "TestV111SkipFilter class wraps v1.1.1 regression tests with a narrowly-scoped autouse `_reset_discovery_cache` fixture (mirrors tests/unit/test_runner_migration.py)"
    - "Module-walking audit test (rglob *.py + triple-quoted-string tracking) as a permanent pin against patch-seam drift"
    - "@pytest.mark.xfail(strict=False, reason=...) to preserve a test's history without failing CI when the test depends on retired schema surface"
key_files:
  created: []
  modified:
    - tests/test_tool_config.py
decisions:
  - "Use direct attribute assignment `_r._DISCOVERED_TOOL_NAMES = [...]` (matching tests/unit/test_runner_migration.py verbatim) rather than the helper `_set_discovered_tool_names(...)` -- keeps the two regression files stylistically identical"
  - "Wrap the v1.1.1 regression tests in a TestV111SkipFilter class so the autouse reset fixture only resets the cache for those two tests, not the whole module (avoids collateral damage to schema tests and the AsyncMock proof above/below)"
  - "Preserve `test_resolve_tool_names_explicit_target_overrides_skip_true` via @pytest.mark.xfail (strict=False) rather than deleting it -- Phase 13 v2-schema dropped `target:` (extra_forbidden), so the test fails at Config construction; the xfail keeps git blame intact for the Phase 13 verification follow-up"
  - "Implement the audit's docstring/string-literal exclusion via triple-quoted-string state tracking (not file-self-exclusion); this lets the audit catch real writes anywhere in tests/ while tolerating documentation that quotes the dead seam"
metrics:
  duration: "4.3 min"
  completed: "2026-05-11"
  tasks: 2
  files_modified: 1
  commits: 2
---

# Phase 14 Plan 07: Stale cache patch path (GAP 3 gap-closure) Summary

## One-liner

Retargeted the SAFE-01 v1.1.1 skip-filter regression test from the dead seam `tests.conftest._DISCOVERED_TOOL_NAMES` (left orphaned by Plan 14-05's cache migration) to the new canonical path `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES`, and added a permanent module-walking audit pin so future migrations cannot silently re-introduce the dead seam.

## What changed

Single file: `tests/test_tool_config.py`.

1. **Removed dead-seam import** (`import tests.conftest as _conftest_module`) from line 35. The conftest module attribute is no longer the cache; it is a stale alias that silently no-ops when written.
2. **Added a permanent audit test** `test_no_stale_conftest_module_discovered_tool_names_writes` that walks `tests/**/*.py`, tracks triple-quoted-string state, and flags any executable write `_conftest_module._DISCOVERED_TOOL_NAMES = ...`. Documentation/docstrings that quote the dead-seam pattern (for explanatory reference) are tolerated.
3. **Grouped the two v1.1.1 regression tests into a `TestV111SkipFilter` class** with a class-scoped `autouse=True` `_reset_discovery_cache` fixture mirroring `tests/unit/test_runner_migration.py:_reset_discovery_cache`. The class scope narrows the fixture's blast radius -- schema tests above and the AsyncMock proof below are unaffected.
4. **Retargeted `test_resolve_tool_names_filters_out_skip_true_tools`** to assign `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES = ["a", "b", "c"]` directly (matching the reference pattern in `tests/unit/test_runner_migration.py:54`). The test now exercises the live cache that `tests/conftest._resolve_tool_names` actually consumes.
5. **Xfailed `test_resolve_tool_names_explicit_target_overrides_skip_true`** with `@pytest.mark.xfail(strict=False, reason="Phase 13 v2-schema rework dropped the `target:` block ...")`. The test is preserved-not-deleted so git blame survives the Phase 13 verification follow-up that will restore (or replace) the explicit-override semantics under the v2 schema.

## Why the partner test was xfailed instead of deleted

Per 14-HUMAN-UAT.md Gap 3 diagnosis: the partner test fails for a DIFFERENT reason than the skip-filter test -- it constructs `Config(target={"tool_name": "b"})`, but Phase 13's v2-schema rework dropped the `target:` block (raising Pydantic `extra_forbidden` at construction time). That is Phase 13 verification debt, NOT Phase 14 gap-closure scope.

`strict=False` is intentional: if Phase 13's follow-up restores a v2 equivalent of the explicit-override semantics, the test will silently start passing without manual intervention; if it stays unsupported, it remains XFAIL without failing CI. Either way, the test body documents the semantics the v1.1.1 hotfix preserved (the D-12 `_preflight` warning path at fixtures.py:200-213) so the intent survives for whoever picks up the Phase 13 follow-up.

## The audit pin is permanent

`test_no_stale_conftest_module_discovered_tool_names_writes` is a load-bearing regression pin, not a one-shot grep. Any future plan that re-introduces a `_conftest_module._DISCOVERED_TOOL_NAMES = ...` write (or any other test file that resurrects the dead seam) will fail this test at the next pytest collection -- catching the same class of failure that Plan 14-05 verification missed because it ran with `--confcutdir=tests/unit`.

The audit's heuristic tracks triple-quoted-string state so it tolerates documentation that quotes the dead-seam pattern (for explanatory purposes, like the docstring in the audit test itself or future migration notes). It does NOT tolerate executable assignments.

## Reference parity confirmed

`tests/test_tool_config.py` and `tests/unit/test_runner_migration.py` now use identical patch shapes:
- Both import via `from mcp_test_framework import _runner as _r` function-locally inside each test.
- Both assign the cache directly: `_r._DISCOVERED_TOOL_NAMES = [...]`.
- Both rely on an `autouse=True` `_reset_discovery_cache` fixture that nulls the cache on setup and teardown.

Future plans touching the cache seam should follow the same shape; the audit test will flag deviations.

## Verification results

Run with `MCPTF_CONFIG_FILE=./config.yaml uv run pytest ...`:

| Suite                                                                                                              | Result                                                          |
| ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------- |
| `tests/test_tool_config.py -k "SkipFilter or no_stale_conftest_module"`                                            | 2 passed, 1 xfailed (target subset GREEN)                       |
| `tests/test_tool_config.py` (full file)                                                                            | 18 passed, 1 xfailed, 3 failed (the 3 are Phase 13 v2-schema debt, see below) |
| `tests/unit/test_runner_migration.py tests/test_runner_subprocess.py tests/test_runner_renderer.py tests/unit/test_runner_parser.py` | 66 passed (Phase 14 main verification suite unaffected)         |

The 3 remaining failures in `tests/test_tool_config.py` are PRE-EXISTING Phase 13 v2-schema migration debt called out in 14-HUMAN-UAT.md Test 3 → notes bullet 3 (the plan's success criteria explicitly accepts these as out-of-scope):

- `test_default_config_version_and_tools` -- still asserts `cfg.version == 1`; Phase 13 made the build version=2
- `test_config_rejects_unsupported_version[2]` -- parametrized over `[0, 2, -1, 99]`; v2 is now the supported version, so the `[2]` case incorrectly fails
- `test_yaml_overlay_loads_tools_block` -- writes `version: 1` to YAML; Phase 13 rejects it

These three are tracked under Phase 13 verification follow-up. Plan 14-07's `<success_criteria>`: "No NEW regressions in `tests/test_tool_config.py` beyond the 5 already-known Phase 13 v2-schema debts" -- we have 3, well within the known-debt budget.

## Deviations from Plan

### Rule 1 - Bug: Audit heuristic needed triple-quoted-string tracking

**Found during:** Task 1 RED-state verification.

**Issue:** The plan's initial heuristic (`stripped.startswith("#")` etc.) didn't skip docstring continuation lines. The audit caught its own docstring at line 221 (a backtick-prefixed reference to the dead-seam pattern) as a false-positive offender. The plan explicitly anticipated this: "If by some accident the comment-skip heuristic causes the audit to PASS prematurely, tighten the pattern."

**Fix:** Implemented triple-quoted-string state tracking. The audit now toggles `in_triple` state on each `"""`/`'''` delimiter and skips lines fully enclosed in a docstring. Real executable assignments (which never live inside docstrings) are still flagged.

**Files modified:** `tests/test_tool_config.py` (audit body only).

**Commit:** 04c4aab (Task 1 -- the tightened heuristic landed in the same commit as the audit, since it was needed to achieve the proper RED state).

### Rule 3 - Setup: Worktree lacked config.yaml

**Found during:** First `uv run pytest` invocation.

**Issue:** The worktree branch was created before any phase-14 config artifacts existed. The `tests/conftest.py` session preflight aborts at collection with `MCP command 'homelab-mcp' not found on PATH` when no `MCPTF_CONFIG_FILE` is set and no `config.yaml` is autodiscovered.

**Fix:** Copied `config-v2-worktree.yaml` from the parent repo root into `config.yaml` in the worktree (matches the documented [Worktree config setup](feedback_worktree_config.md) memory). Then exported `MCPTF_CONFIG_FILE` to the worktree's `config.yaml` for every pytest invocation.

**No commit:** `config.yaml` is environment scaffolding, not source. It is gitignored.

### Worktree merge with main

The worktree branch (`worktree-agent-a4c0137274a584b75`) was originally created before Phase 14 even began. To pick up `_runner.py`, `tests/unit/test_runner_migration.py`, the 14-07-PLAN.md itself, and 30+ other Phase 14 artifacts, I merged `main` into the worktree branch before starting Task 1. The merge had no conflicts. This is a one-time worktree-setup step, not a deviation from the plan content -- but it's worth noting because the executor's first git operation in this session was a `git merge main`.

## Self-Check

- File `tests/test_tool_config.py`: FOUND (modified)
- File `.planning/phases/14-hybrid-runner-with-domain-ui/14-07-SUMMARY.md`: created this commit
- Commit `04c4aab` (Task 1 -- audit pin RED): FOUND in `git log`
- Commit `1b0f2c1` (Task 2 -- retarget GREEN + xfail partner): FOUND in `git log`

## Self-Check: PASSED
