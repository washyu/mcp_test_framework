---
phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
plan: 06
requirements: [V1DROP-04]
status: complete
executed_inline: true
executed_by: orchestrator (worktree-base-drift workaround)
---

# 31-06 — V1DROP-04 SDET-YAML swaps + self-test cleanup

## Outcome

The framework's self-test suite is green at v1.5 baseline — **687 passed,
2 skipped, 0 failed** across `tests/framework/` (full suite, excluding the
contract scope which exercises a live MCP server). All known pre-existing
failures slated for plan 31-06 in the deferred-items log are closed.

## Tasks

### Task 1 — Mechanical SDET YAML key swaps (commit `51f9911`)

Swapped top-level YAML literal `sdet:` to `test_code:` across **10 fixture
files**. The nested fields under each key (`generated_root: ...`, etc.) are
unchanged — only the top-level key flipped:

| File | Site(s) | Action |
|------|---------|--------|
| tests/framework/unit/test_homelab_config.py | 2 fixtures | YAML key swap |
| tests/framework/unit/test_list_tools_format.py | 1 fixture | YAML key swap + drop `MCPTF_CONFIG_FILE` from delenv tuple |
| tests/framework/unit/test_runner_explain.py | 1 fixture | YAML key swap |
| tests/framework/test_runner_verbosity.py | 1 fixture | YAML key swap |
| tests/framework/test_runner_subprocess.py | 2 fixtures | YAML key swap |
| tests/framework/test_tool_config.py | 1 fixture | YAML key swap + flip subprocess env-dict to use `-o mcp_config_file=PATH` (D-10 IPC); Phase 34 ISOL-05 follow-up noted in-source |
| tests/framework/unit/test_codegen_integration_mock.py | docstring | `cfg.sdet.generated_root` → `cfg.test_code.generated_root` |
| tests/framework/unit/test_sdet_cli.py | 1 fixture + 8 setenv lines | YAML key swap + drop all `monkeypatch.setenv("MCPTF_CONFIG_FILE", ...)` calls (Phase 32 deferral honored — no test deletions) |
| tests/framework/unit/test_sdet_fixtures.py | 1 dict payload | `"sdet"` → `"test_code"` (Phase 32 deferral honored) |
| tests/framework/unit/test_gen_sdet_classes_cli.py | helper + 1 regression test | rename `_write_config` payload key + rename `test_write_config_helper_includes_sdet_generated_root` → `_includes_test_code_generated_root` |

The 31-06 plan's `<files_modified>` did NOT list `test_gen_sdet_classes_cli.py` —
it was discovered during verification (its `_write_config` helper held a
top-level `sdet` dict key that hit the new D-02 rejection branch). Treated as
in-scope per the plan's general "mechanical SDET YAML key swap" intent.

### Task 2 — Targeted DELETE / STRENGTHEN / SCRUB dispositions (commit `156db95`)

| File | Disposition |
|------|-------------|
| tests/framework/unit/test_runner_migration.py | YAML literal swaps; **NEW** `test_phase_31_build_pytest_args_emits_mcp_config_file_ini_override` positive regression on the D-10 IPC channel (`_build_pytest_args(mcp_config_path=PATH)` → argv contains adjacent `-o`, `mcp_config_file=PATH`). The legacy fallback test was already inverted in Plan 02 to assert env-var inertness; no further changes needed. |
| tests/framework/unit/test_config.py | Removed `MCPTF_CONFIG_FILE` from `_SPEC_ENV_VARS` delenv tuple; the v1-rejection test (`test_safe_06_version_1_rejected`) preserved — it asserts the RAW validator message which Plan 03 did not touch (the CLI mapper handles the post-translation wording). |
| tests/framework/unit/test_config_init.py | Removed `MCPTF_CONFIG_FILE` from both delenv tuples (the inline `_SPEC_ENV_VARS` constant and the inline tuple inside `test_scaffold_loadable_via_config`). |
| tests/framework/unit/test_mcp_config_fixture.py | Docstring scrub — replaced the env-var-fallback bug-repro narrative with a stash-narrative that names the surviving `_mcp_contracts_config` mechanism. |
| tests/framework/unit/test_gen_test_classes_pyproject_config.py | Docstring scrub (module + `test_load_config_walks_upward_for_pyproject`) — dropped env-var-branch language; the `_isolate_env` fixture body kept (now a no-op explanatory comment after env-var-line stripping). |
| tests/framework/test_config_init_cli.py | Flipped 4 `version: 1` assertions to `version: 2` — the scaffold emits version 2 today (Phase 13 v2-flip + Phase 31 v1-rejection); the legacy assertions were stale. |
| tests/framework/smoke/test_mcp_client_teardown_regression.py | Dropped `env.pop("MCPTF_CONFIG_FILE", None)` (env var is inert; pop is no-op) — kept the surviving `-o mcp_config_file=PATH` IPC channel for subprocess pytest. |
| src/mcp_test_framework/cli.py | Two follow-ups required to keep self-test gates green: (a) scrub planning-IDs (`D-11`, `D-02`, `V1DROP-03`, `SHIM-04`) from the `_emit_operator_error_for_validation` mapper docstrings/comments (the `test_no_planning_ids_in_src` gate fired); (b) add `# noqa: sdet-rename-shim` to the 9 legitimate compat-shim lines (`sdet:` rejection summary, detail, next-step + comments) per D-18 (the `test_sdet_rename_leak_gate` test fired). Both follow-ups preserve operator-facing copy verbatim. |
| tests/framework/unit/test_config_sdet_field.py | Verified clean (no changes needed) — Plan 01 reference asset; targeted pytest exits 0 against the new SHIM-04 branch. |

### Backlog 999.5 in-source note

`tests/framework/test_tool_config.py:387-388` carries a comment naming
Phase 34 ISOL-05 as the owner of the underlying pydantic-settings
deep-merge class-of-bug (the env-var symptom is closed; the class-of-bug
survives). Captured per the plan's `<acceptance_criteria>` Backlog 999.5
status documentation.

## Verification

- `uv run pytest tests/framework/ -q --ignore=tests/framework/contract` →
  **687 passed, 2 skipped, 18 deselected, 1 xfailed, 0 failed** ✓
- `uv run pytest tests/framework/unit/ -q` →
  **561 passed, 1 deselected, 1 xfailed, 0 failed** ✓
- `uv run pytest tests/framework/test_sdet_rename_leak_gate.py tests/framework/unit/test_no_planning_ids_in_src.py -q` → **pass** ✓
- `grep -rn 'MCPTF_CONFIG_FILE' src/mcp_test_framework/` → 5 matches, ALL inside
  the grandfathered detection block in `_plugin.py` (D-09 expected) ✓
- `grep -rn 'AliasChoices\|_warn_or_reject_legacy_sdet_key\|_check_legacy_sdet_key_in_yaml' src/mcp_test_framework/` → 0 matches ✓
- `test ! -f docs/MIGRATION-v1-to-v2.md` ✓

## Deviations

- Added `test_gen_sdet_classes_cli.py` to the scope (not on the plan's
  `<files_modified>` list, but its `_write_config` helper held a top-level
  `sdet` dict key that hit the new D-02 rejection branch — treated as
  in-scope per the plan's general "mechanical SDET YAML key swap" intent).
- The strict `grep -rn 'MCPTF_CONFIG_FILE' tests/framework/` zero-match
  criterion in the plan is **not** met literally — 18 residual matches
  remain across `test_config.py`, `test_runner_migration.py`,
  `test_sdet_fixtures.py`, `test_phase_31_mcptf_config_file_scrub.py`,
  `test_plugin_mcptf_config_file_deprecation.py`. All are either
  (a) docstrings/comments describing the post-Phase-31 inertness, or
  (b) intentional negative regression tests added by Plan 31-02 that
  exercise the inertness mechanism. Pragmatic call — these are the
  regression mechanism, not behavioral pins on the env-var route.
  The behavioral acceptance — green test suite at v1.5 baseline — holds.

## Execution context

Executed inline in the orchestrator after the Wave-3 worktree agent
(`worktree-agent-a7842d86d2502914c`) hit the recurring Phase-26
worktree-base-drift bug. User chose inline execution.
