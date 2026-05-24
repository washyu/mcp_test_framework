---
phase: 31
plan: 03
subsystem: cli
tags: [v1-decommission, operator-error, self-test-relaxation, V1DROP-03, V1DROP-04]
requires: [31-01]
provides:
  - D-11-v1-rejection-wording-in-cli.py
  - SAFE-06-test-pins-D-11-wording
  - sdet-yaml-literals-swapped-in-test_cli_errors.py
affects:
  - src/mcp_test_framework/cli.py
  - tests/framework/unit/test_cli_errors.py
  - tests/framework/unit/test_error_style.py
tech-stack:
  added: []
  patterns:
    - "Pydantic-error message regex-parse for {v} substitution into D-11 wording"
key-files:
  modified:
    - src/mcp_test_framework/cli.py
    - tests/framework/unit/test_cli_errors.py
    - tests/framework/unit/test_error_style.py
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/deferred-items.md
  created: []
decisions:
  - "Honored CONTEXT D-11 verbatim wording (operator-approved during /gsd-discuss-phase); did not reword."
  - "Honored CONTEXT D-12 RELAX-not-DELETE default for self-tests; only deleted assertions, not whole tests where possible."
  - "Relaxed test_error_style_contains_safe_06_message to a neutral non-empty existence check (avoids churn through Plan 05 ERROR-STYLE.md scrub)."
  - "Per plan §verification step 3, removed all `MIGRATION-v1-to-v2` references from src/cli.py + both test files including docstring residues -- not just assertions."
metrics:
  duration_minutes: ~25
  completed_date: 2026-05-23
  tasks_completed: 3
  files_modified: 4
  commits: 4
---

# Phase 31 Plan 03: V1-rejection rewrite (V1DROP-03 + V1DROP-04 partial) Summary

Rewrote the v1->v2 migration walkthrough error in `cli.py:_emit_operator_error_for_validation` to the D-11 generic three-part operator-tone wording, and simultaneously rewrote the pinned self-tests in `test_cli_errors.py` + `test_error_style.py` to honor RESEARCH §"Strict ordering constraint 2" (message rewrite + test relaxation land same plan).

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Rewrite cli.py version branch to D-11 wording | 2299716 | src/mcp_test_framework/cli.py |
| 2 | Rewrite SAFE-06 v1-rejection assertions to D-11; sdet->test_code YAML swaps | af73c82 | tests/framework/unit/test_cli_errors.py |
| 3 | Rewrite SAFE-06 cli-wiring assertion to D-11; relax ERROR-STYLE.md pin | 1f2e49c | tests/framework/unit/test_error_style.py |
| - | Record sdet-literal cleanup status in deferred-items.md | 23bc39e | .planning/.../deferred-items.md |

## What Changed

### `src/mcp_test_framework/cli.py` (Task 1)

The `_emit_operator_error_for_validation` version branch was rewritten end-to-end. Before:

- Multi-line `detail` block walking through v1 (opt-out) vs v2 (opt-in) semantics
- Cross-reference to `docs/MIGRATION-v1-to-v2.md`
- `next_step` pointing at the legacy `mcp-test-framework` console-script

After (D-11 verbatim from CONTEXT.md):

- `summary  = "unsupported config version {v}"` -- {v} parsed from the Pydantic error message via regex
- `detail   = ["this build supports schema version 2.", "your config declares version {v}, which is no longer accepted."]`
- `next_step = "run \`mcp-contracts config-init -o config.yaml\` to generate a current scaffold"`

Exit code 2 preserved per ERROR-STYLE.md. Mapping-rules docstring updated to drop the migration-walkthrough framing.

### `tests/framework/unit/test_cli_errors.py` (Task 2)

- `test_safe_06_v1_config_emits_locked_migration_message`: assertion block swapped from legacy migration-walkthrough phrases to D-11 verbatim. Test name preserved per RESEARCH inventory ("preserves test count + names is fine"). Added a regression guard against `"the difference matters"` (the v1-vs-v2 walkthrough giveaway).
- Mechanical `sdet:`/`tests/sdet/_generated` -> `test_code:`/`tests/test_code/_generated` swap at three call sites (`test_list_tools_mcp_spawn_failure`, `test_config_init_mcp_spawn_failure`, `test_safe_02_cwd_autodiscovery_picks_up_local_config`). Required because Plan 01 removed the `sdet:` AliasChoices and `extra='forbid'` now rejects the legacy key.
- Per plan acceptance criterion: `grep 'MIGRATION-v1-to-v2'` returns zero matches (no negative-assertion residue either).
- The legacy `test_safe_06_v1_config_via_env_var_emits_locked_migration_message` and `test_safe_04_mcptf_config_file_typo_exits_2` tests were ALREADY DELETED by Plans 01/02 (replaced with Phase-31 inversion tests). No further deletions needed in this task.
- 20/20 pass after change.

### `tests/framework/unit/test_error_style.py` (Task 3)

- `test_error_style_safe_06_body_matches_cli_wiring`: REWRITE. Replaces Phase-13 D-08 pins (schema-version-2-opt-in / opt-out / `in v1 a tool with no entry runs by default, in v2 it skips` / `docs/MIGRATION-v1-to-v2.md` / `config-init -o config.yaml.new`) with the D-11 verbatim text (`unsupported config version`, `this build supports schema version 2`, `config-init -o config.yaml`).
- `test_error_style_contains_safe_06_message`: RELAX. Replaced ERROR-STYLE.md migration-walkthrough header/cross-ref pins with a neutral non-empty assertion that survives both Plan 04 (migration-doc deletion) and Plan 05 (ERROR-STYLE.md scrub).
- Removed `MIGRATION-v1-to-v2.md` and `test_error_style_safe_04_body_matches_cli_wiring` docstring residues so plan-level grep verification (zero MIGRATION refs across the three target files) holds.
- `test_error_style_safe_04_env_var_branch_is_gone` (Plan 02 inversion test) is UNCHANGED -- structurally orthogonal to v1-rejection wording.
- 8/8 pass after change.

## Verification

### Phase-level checks

1. `uv run pytest tests/framework/unit/test_cli_errors.py tests/framework/unit/test_error_style.py -q`: **28 passed in 0.25s**.
2. End-to-end v1-rejection smoke (per Task 1 `<automated>` block):
   - Created `/tmp/v1-test.yaml` with `version: 1\ntest_code:\n  generated_root: x\n`
   - `uv run --active mcp-contracts run --config <path>`: exit code 2
   - stderr contains: `unsupported config version 1`, `this build supports schema version 2.`, `config-init -o config.yaml`
   - stderr does NOT contain: `MIGRATION-v1-to-v2`, `opt-in`, `opt-out`, `the difference matters`, `migration walkthrough`
3. `grep -rn 'MIGRATION-v1-to-v2' src/mcp_test_framework/cli.py tests/framework/unit/test_cli_errors.py tests/framework/unit/test_error_style.py`: **0 matches** across all three files.

### Acceptance criteria (all met)

Task 1 (cli.py):
- `grep -n 'unsupported config version' src/mcp_test_framework/cli.py`: exactly 1 match (the version branch) -- met.
- `grep -n 'this build supports schema version 2' src/mcp_test_framework/cli.py`: exactly 1 match -- met.
- `grep -n 'MIGRATION-v1-to-v2' src/mcp_test_framework/cli.py`: 0 matches -- met.
- `grep -n 'config-init -o config.yaml' src/mcp_test_framework/cli.py`: multiple matches including version branch -- met.
- Python probe synthesizing a version=1 ValidationError exits via `typer.Exit(2)` -- met.

Task 2 (test_cli_errors.py):
- `grep -n 'test_safe_06_v1_config_via_env_var_emits_locked_migration_message'`: 0 -- met (deleted by Plan 02).
- `grep -n 'test_safe_04_mcptf_config_file_typo_exits_2'`: 0 -- met (deleted by Plan 02).
- `grep -n 'test_safe_06_v1_config_emits'`: 1 -- met.
- `grep -n 'MIGRATION-v1-to-v2'`: 0 -- met.
- `grep -n 'sdet:'`: 0 -- met (mechanical swap to test_code:).
- `grep -n 'unsupported config version'`: 1 -- met.
- `uv run pytest tests/framework/unit/test_cli_errors.py -q`: 20 passed -- met.

Task 3 (test_error_style.py):
- `grep -n 'test_error_style_safe_04_body_matches_cli_wiring'`: 0 -- met (Plan 02 already inverted; docstring residue removed in this plan).
- `grep -n 'MIGRATION-v1-to-v2'`: 0 -- met.
- `grep -n 'in v1 a tool with no entry'`: 0 -- met.
- `grep -n 'unsupported config version\|this build supports schema version 2'`: matches -- met.
- `uv run pytest tests/framework/unit/test_error_style.py -q`: 8 passed -- met.

## Deviations from Plan

### Minor adjustments

**1. [Rule 3 - Adjust to upstream state] env-var SAFE-04/SAFE-06 tests already deleted by Plans 01/02**

- **Found during:** Task 2 read-first
- **Issue:** Plan's Task 2 action items 2-3 instructed DELETING `test_safe_06_v1_config_via_env_var_emits_locked_migration_message` and `test_safe_04_mcptf_config_file_typo_exits_2`. Both functions no longer exist in the test file -- Plans 01/02 (already merged to my base) replaced them with Phase-31 inversion tests (`test_phase_31_v1_config_via_env_var_no_longer_routed`, `test_phase_31_mcptf_config_file_typo_no_longer_routed`) that assert SAFE-03 fires instead.
- **Fix:** No action -- plan intent already achieved. New inversion tests are orthogonal to v1-rejection wording (they pin SAFE-03 surfaces, not the v1-rejection body) and left untouched.
- **Files modified:** none (no-op)
- **Commit:** N/A

**2. [Rule 2 - Critical functionality] Removed docstring `MIGRATION-v1-to-v2.md` and `test_error_style_safe_04_body_matches_cli_wiring` references**

- **Found during:** Task 3 verification
- **Issue:** Plan §verification step 3 specifies `grep -rn 'MIGRATION-v1-to-v2'` returns **zero matches** across the three target files -- no negative-assertion residue. My initial Task 2/3 edits left docstring/comment references that satisfied "no positive assertion" but failed the literal grep. Same applies to the SAFE-04 docstring reference in the Plan 02 inversion test.
- **Fix:** Edited the residual docstring lines to use neutral synonyms (e.g., "legacy migration-walkthrough body" instead of `docs/MIGRATION-v1-to-v2.md`; "legacy SAFE-04 body-match test" instead of the full function-name reference). All three target files now return 0 for `grep MIGRATION-v1-to-v2` and 0 for `grep test_error_style_safe_04_body_matches_cli_wiring`.
- **Files modified:** tests/framework/unit/test_cli_errors.py, tests/framework/unit/test_error_style.py
- **Commit:** af73c82 (test_cli_errors), 1f2e49c (test_error_style)

## Deferred Issues

26 framework-unit-test failures in `tests/framework/unit/{test_runner_explain,test_runner_migration,test_sdet_cli,test_sdet_fixtures}.py` are caused by remaining `sdet:` YAML literals in those test fixtures triggering the Plan 01 D-02 rejection. These are explicitly scoped to Plan 31-06 per the existing `deferred-items.md` register. Plan 31-03 swept the three `sdet:` literals in `test_cli_errors.py` (per the plan's Task 2 action items 4-5); the remaining 7 test files stay deferred. Aggregate baseline at HEAD of Plan 31-03: 26 failed, 534 passed across `tests/framework/unit/`. None caused by the v1-rejection rewrite.

## Threat Model Realization

- T-31-03-01 (Tampering -- self-test relaxation hiding regression): MITIGATED. Body-text pins were swapped for D-11 verbatim wording rather than removed; structural assertions (exit code 2, three-part shape, summary-keyword presence) survive. The sibling `test_load_config_validation_error_version` (L96-126) is unmodified and continues to act as a permissive regression sibling.
- T-31-03-02 (Information Disclosure -- {v} substitution): ACCEPTED. Operator's own version-field value is reflected back -- non-sensitive by definition.

## Threat Flags

None. The version branch reads a Pydantic-validated `int` field from the operator's config and parses it via regex from the validator's own error message -- no new network/auth/file surface introduced.

## Commits

| Hash | Type | Message |
| ---- | ---- | ------- |
| 2299716 | feat | rewrite v1-rejection to D-11 operator-tone wording (V1DROP-03) |
| af73c82 | test | rewrite SAFE-06 v1-rejection assertions to D-11 wording (V1DROP-04) |
| 1f2e49c | test | rewrite SAFE-06 body assertions to D-11; relax SAFE-06 ERROR-STYLE pin (V1DROP-04) |
| 23bc39e | docs | record sdet: literal cleanup status in deferred-items.md |

## Self-Check: PASSED

- File exists: `src/mcp_test_framework/cli.py` -- FOUND
- File exists: `tests/framework/unit/test_cli_errors.py` -- FOUND
- File exists: `tests/framework/unit/test_error_style.py` -- FOUND
- File exists: `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/deferred-items.md` -- FOUND
- Commit 2299716 -- FOUND (`feat(31-03): rewrite v1-rejection to D-11 operator-tone wording (V1DROP-03)`)
- Commit af73c82 -- FOUND (`test(31-03): rewrite SAFE-06 v1-rejection assertions to D-11 wording (V1DROP-04)`)
- Commit 1f2e49c -- FOUND (`test(31-03): rewrite SAFE-06 body assertions to D-11; relax SAFE-06 ERROR-STYLE pin (V1DROP-04)`)
- Commit 23bc39e -- FOUND (`docs(31-03): record sdet: literal cleanup status in deferred-items.md`)
- Phase-level pytest verification: 28/28 pass on target files
- End-to-end v1-rejection smoke: exit 2 with D-11 wording, no MIGRATION ref
