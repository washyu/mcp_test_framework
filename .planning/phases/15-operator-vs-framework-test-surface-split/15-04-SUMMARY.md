---
phase: 15-operator-vs-framework-test-surface-split
plan: 04
subsystem: verification
tags: [verification, test-surface, history-preservation, post-split]
dependency_graph:
  requires:
    - "Plan 15-01 (folder split executed)"
    - "Plan 15-02 (runner default-scope flip + --with-framework opt-in)"
    - "Plan 15-03 (README + MVP spec doc refresh)"
  provides:
    - "15-VERIFICATION.md with PASS verdict for all 4 ROADMAP success criteria"
    - "Auto-fixed two relocation-induced regressions in framework tests"
  affects:
    - "Phase 15 ROADMAP closeout — all 4 plans complete pending human checkpoint"
tech_stack:
  added: []
  patterns: []
key_files:
  created:
    - .planning/phases/15-operator-vs-framework-test-surface-split/15-VERIFICATION.md
  modified:
    - tests/framework/test_runner_subprocess.py
    - tests/framework/test_banned_imports.py
  moved: []
decisions:
  - "Recipe 4 verified on BOTH channels (argv via --raw + wrapper-rendered domain UI) per plan acceptance criteria — both clear of framework-test leakage"
  - "Pre-existing test bugs caused by Plan 15-01's relocation auto-fixed in scope as Rule 1 deviations (commits 327af82, d8d464c); rationale: phase title = operator vs framework test surface split, regressions were squarely in scope"
  - "Used config.yaml (v2 worktree config) with 2-tool allowlist (list_keyring_credentials, suggest_deployments) for Recipes 4/5 — matches CONTEXT.md SC-1 ~20-cases-for-2-tools expectation"
metrics:
  duration_minutes: ~20
  files_created: 1
  files_modified: 2
  commits: 3
  recipes_executed: 7
  success_criteria_verified: 4
  completed: 2026-05-11
---

# Phase 15 Plan 04: Run verification recipes + human checkpoint — Summary

Ran all 7 verification recipes named in CONTEXT.md `Claude's Discretion` step 4, capturing exact outputs against the live homelab-mcp / live Ollama (`qwen3:0.6b`) stack, and recorded results in `15-VERIFICATION.md`. All 4 ROADMAP success criteria (SC-1..SC-4) verified PASS. Two pre-existing test bugs caused by Plan 15-01's mechanical file relocation were auto-fixed in scope (two-character path-component fixes in `test_runner_subprocess.py` and `test_banned_imports.py`), keeping the phase shippable in a single closure window. Task 2 — the human-verify checkpoint — is pending; this summary closes out Plan 15-04's automated portion.

## What Was Built

### Three commits

| Task    | Commit  | Description                                                                          |
| ------- | ------- | ------------------------------------------------------------------------------------ |
| 1 (pre) | 327af82 | `fix(15-04): repair test_plugins_list_does_not_register_reporter after 15-01 file move` |
| 1 (pre) | d8d464c | `fix(15-04): repair test_banned_imports fixture path after 15-01 file move`          |
| 1       | 0ec5a48 | `docs(15-04): record verification recipe outputs for SURFACE-01..04`                 |

### Recipe Results

| Recipe | Command                                                         | Verdict | Evidence                                                                |
| ------ | --------------------------------------------------------------- | ------- | ----------------------------------------------------------------------- |
| 1      | `pytest tests/contract/ --collect-only -q`                      | PASS    | exit 0, 20 tests, 0 framework leaks                                     |
| 2      | `pytest tests/framework/ --collect-only -q`                     | PASS    | exit 0, 289/304 tests, 0 contract leaks                                 |
| 3      | `pytest tests/ --collect-only -q`                               | PASS    | exit 0, 309/324 tests (20 contract + 289 framework)                     |
| 4a     | `mcp-test-framework run --raw -- --collect-only -q`             | PASS    | exit 0, 20 contract appearances, 0 framework leaks (argv channel)       |
| 4b     | `mcp-test-framework run` (wrapper-rendered)                     | PASS    | exit 1 (real judge failures), 0 of the 12 framework-test names leaked    |
| 5      | `mcp-test-framework run --with-framework --raw -- --collect-only -q` | PASS  | exit 0, both subtrees (20 contract + 289 framework)                     |
| 6      | `git log --follow` on 3 representative files                    | PASS    | All 3 show pre-move history (Phase 04, Phase 01, Phase 06 origins)      |
| 7      | `pytest tests/framework/test_banned_imports.py -v`              | PASS (post-fix) | 3 passed in 5.78s after fixture-path repair                       |

### Two-Channel Verification of SC-1

Recipe 4 explicitly verified SC-1's "operator output" invariant on both channels per plan acceptance criterion:

- **Channel A (argv via `--raw`):** `tests/framework/` strings: 0; `tests/contract/` strings: 20. Confirms the operator scope flip in `_build_pytest_args` (Plan 15-02) correctly defaults to contract-only.
- **Channel B (wrapper-rendered domain UI, no `--raw`):** Zero matches against the 12-name framework-test regex (`test_isolation|test_runner_renderer|test_runner_subprocess|test_runner_verbosity|test_readme_snippets|test_config_init_cli|test_tool_config|test_runner_live_smoke|test_banned_imports|test_smoke_homelab_mcp|test_smoke_ollama_judge|test_mcp_client_teardown_regression`); zero `tests/framework/` strings; zero `tests/contract/` strings (paths hidden behind the MCP-domain UI as designed). Operator sees only `MCP server`, `Discovered`, `Running`, `Skipping`, `Test plan`, tool names, and verdict rows.

## Acceptance Criteria Verification

All seven `<acceptance_criteria>` items from the plan pass:

- [x] `15-VERIFICATION.md` exists and contains the 4 SC sections + 3 supporting recipes — verified by `grep -q "SC-1|SC-2|SC-3|SC-4"` (all four present)
- [x] Recipe 1: exit code 0 (NOT 5), collected count 20 >= 1 — `tests/contract/` non-empty
- [x] Recipe 4a: `grep -c "tests/framework"` against output == **0** (SC-1 argv channel)
- [x] Recipe 4b: 12-name framework-test grep returned **0 matches** against `recipe4b-stdout.log` (SC-1 operator-visible channel)
- [x] Recipe 5: both `tests/contract` and `tests/framework` present (SC-2)
- [x] Recipe 6: each of the 3 files shows >= 2 commit lines (SC-3) — actual counts 4, 2, 5
- [x] Recipe 7: pytest collected and ran the test from `tests/framework/test_banned_imports.py` (SC-4) — and after the in-scope fixture-path fix, all 3 sub-tests pass
- [x] File committed with prefix `docs(15-04):` (commit `0ec5a48`)
- [x] Overall Status line: PASS

## Requirements Implemented

- **SURFACE-01..04** — Verified by recipes 1-7. All four ROADMAP success criteria (SC-1..SC-4) recorded PASS in `15-VERIFICATION.md`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `test_plugins_list_does_not_register_reporter` path bug**
- **Found during:** Pre-flight prep (flagged in `deferred-items.md` from Plan 15-02)
- **Issue:** After Plan 15-01 moved `test_runner_subprocess.py` from `tests/` to `tests/framework/`, `Path(__file__).resolve().parents[1]` resolved to `tests/` (instead of repo root). The conftest probe at `repo_root / "tests" / "conftest.py"` looked for `tests/tests/conftest.py` and raised `FileNotFoundError`.
- **Fix:** Changed `parents[1]` to `parents[2]`. Added a docstring paragraph explaining the post-split path.
- **Files modified:** `tests/framework/test_runner_subprocess.py`
- **Commit:** `327af82`
- **Verification:** Targeted invocation `uv run pytest tests/framework/test_runner_subprocess.py::test_plugins_list_does_not_register_reporter -v` → `1 passed in 4.40s`

**2. [Rule 1 - Bug] Fixed `test_banned_imports.py` fixture path bug**
- **Found during:** Recipe 7 execution (the SURFACE-04 enforcement check)
- **Issue:** `_FIXTURE` constant hardcoded `tests/_fixtures/banned_import_should_fail.py.txt`. Plan 15-01 moved the fixture to `tests/framework/_fixtures/banned_import_should_fail.py.txt` (as part of the bulk hoist of the test from `tests/unit/`), but the constant was not updated. Result: `test_ruff_tid251_fires_on_top_level_import` failed with `AssertionError: fixture missing`.
- **Fix:** Updated `_FIXTURE` path component from `tests/_fixtures/...` to `tests/framework/_fixtures/...`. Added a code comment explaining the post-split path.
- **Files modified:** `tests/framework/test_banned_imports.py`
- **Commit:** `d8d464c`
- **Verification:** Recipe 7 re-run after fix → `3 passed in 5.78s`

**Rationale for in-scope handling of both auto-fixes:**

- Per CLAUDE.md `Phase scope = phase title` user preference (memory: `feedback_phase_scope_intent.md`), Phase 15 is "operator vs framework test surface split" — regressions caused by 15-01's mechanical relocation are squarely in phase scope.
- The orchestrator's `<parallel_execution>` note explicitly invited evaluation: "Lean toward fixing if doing so does not contradict the plan's literal task list." Plan 15-04's literal task list is "run verification recipes and record outcomes." Fixing two-character bugs that the recipes surface does not contradict that scope — it produces accurate PASS verdicts instead of a PARTIAL with deferred items.
- The fixes are 100% mechanical (path-component updates), 100% test-only (zero `src/` touched), and each verified by a targeted pytest invocation.

## Auto-fixed Issues

See "Deviations from Plan" above — both Rule 1 auto-fixes documented with full diagnosis, fix, files, commits, and verification.

## Deferred Issues

None. Both `deferred-items.md` entries from Plan 15-02 closed by this plan's auto-fixes; the `deferred-items.md` file is left as-is for traceability.

Observations worth surfacing at the human checkpoint (not blockers):

- Recipe 2's collection count is **289 / 304** (not the ~107 cited in SEED-010's narrative). The growth is from v1.2's framework-self-test expansion (Phases 12/13/14). Phase invariant met; SEED-010 narrative may want a count refresh for v1.3+ retrospective.
- Recipe 4b exits **1** (test failures) — that is the SC-1 outcome semantics: SC-1 verifies the operator output **format** (the wrapper renders MCP-domain UI without framework leakage), not whether the operator's SUT passes its rubrics. The 2 FAILs are real-world `qwen3:0.6b` clarity-rubric verdicts against `homelab-mcp` tool descriptions (score 2 vs threshold 4) — the framework correctly catching a real description-quality gap on the SUT.

## Known Stubs

None. All recipe verdicts are recorded with actual evidence, not placeholders.

## Threat Flags

None. The verification artifact is markdown-only; the recipes themselves exercise the same code paths as a normal user-initiated run. Threat register T-15-10/T-15-11/T-15-12 (from the PLAN) was already assessed as NONE/LOW; this plan's two auto-fixes touched only test files (zero `src/` mutation), introducing no new threat surface.

## Self-Check: PASSED

- ✓ `.planning/phases/15-operator-vs-framework-test-surface-split/15-VERIFICATION.md` exists (verified via `git log` showing commit `0ec5a48`)
- ✓ VERIFICATION.md contains substrings `SC-1`, `SC-2`, `SC-3`, `SC-4` (all four sections present)
- ✓ Commit `327af82` exists (test_runner_subprocess.py fix)
- ✓ Commit `d8d464c` exists (test_banned_imports.py fix)
- ✓ Commit `0ec5a48` exists (15-VERIFICATION.md docs commit)
- ✓ `tests/framework/test_runner_subprocess.py::test_plugins_list_does_not_register_reporter` passes (verified targeted run)
- ✓ `tests/framework/test_banned_imports.py` (3 sub-tests) all pass (verified post-fix Recipe 7)
- ✓ Working tree clean modulo `.claude/` worktree-scratch + `config.yaml` (local-only, .gitignore-covered)
- ✓ No edits to STATE.md or ROADMAP.md (parallel-execution contract honored)
