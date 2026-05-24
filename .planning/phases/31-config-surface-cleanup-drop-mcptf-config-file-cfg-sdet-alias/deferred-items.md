# Phase 31 Deferred Items

Items discovered during plan execution that are explicitly scoped to a later plan in this phase.

## From Plan 31-01 (SHIM-04 sdet alias removal)

After Task 1 removed the `cfg.sdet.*` alias machinery, several pre-existing tests
that wrote `sdet:` into YAML fixtures now correctly hit the new `extra_forbidden`
+ D-02 rejection path and fail. These are **scoped to Plan 31-06**
(`v1drop-04-sdet-yaml-swaps-and-test-cleanup`) per the phase roadmap, NOT to
Plan 31-01.

Affected test files (each carries one or more `sdet:` YAML fixtures that need
to be swapped to `test_code:`):

| File | sdet: occurrences |
|------|-------------------|
| tests/framework/unit/test_sdet_cli.py | (multiple) |
| tests/framework/unit/test_runner_migration.py | (multiple) |
| tests/framework/unit/test_runner_explain.py | (multiple) |
| tests/framework/unit/test_list_tools_format.py | (multiple) |
| tests/framework/unit/test_cli_errors.py | (multiple) |
| tests/framework/test_runner_verbosity.py | (multiple) |
| tests/framework/test_runner_subprocess.py | 2 (lines 220, 241) |

**Sample failing assertion** (test_runner_subprocess.py::test_run_exit_code_5_maps_to_0):
```
assert result.exit_code == 0  # 5 mapped to 0
  +  where 2 = <Result SystemExit(2)>.exit_code
```
The exit-code-2 is the new D-02 sdet-rejection (Task 2's branch) firing inside
`_load_config` BEFORE the test's `subprocess.run` stub runs. This is the
**correct** new behavior; the fix is to swap `sdet:` -> `test_code:` in the
test fixture, which is Plan 31-06's job.

**Do NOT fix in Plan 31-01** -- the plan's `<files_modified>` lists only
config.py, cli.py, and test_error_style.py. Pre-rewriting these test files
would create a merge-conflict surface against Plan 06 and violate the
plan-files contract.
