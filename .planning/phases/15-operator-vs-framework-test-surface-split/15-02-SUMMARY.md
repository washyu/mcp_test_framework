---
phase: 15-operator-vs-framework-test-surface-split
plan: 02
subsystem: runner-cli
tags: [feat, cli-surface, scope-flip, with-framework, tdd]
dependency_graph:
  requires:
    - "Phase 15 Plan 01 (tests/contract/ and tests/framework/ subtrees on disk)"
    - "Phase 14 D-01..D-15 (subprocess pytest dispatch contract)"
  provides:
    - "Operator-default scope = tests/contract/ only (~20 cases for 2-tool config per SC-1)"
    - "`--with-framework` opt-in flag that APPENDS tests/framework/ (D-02 superset semantics)"
    - "`--raw` follows the same scope (D-11): --raw alone = tests/contract/, --raw --with-framework = both"
    - "Updated --raw help text anchor citing tests/contract/ (D-12)"
  affects:
    - "Plan 15-04 (verification) — can now smoke-test the operator default = ~20 cases contract"
tech_stack:
  added: []
  patterns:
    - "Keyword-only bool param threaded through three layers (cli -> run_pytest_subprocess -> _build_pytest_args)"
key_files:
  created: []
  modified:
    - src/mcp_test_framework/_runner.py
    - src/mcp_test_framework/cli.py
    - tests/framework/test_runner_subprocess.py
decisions:
  - "D-01 honored: flag name is exactly --with-framework"
  - "D-02 honored: APPEND semantics — with_framework=True emits [tests/contract, tests/framework]"
  - "D-03 honored: _build_pytest_args emits [tests/contract] when False, [tests/contract, tests/framework] when True"
  - "D-11 honored: --raw follows the same scope (both call sites in _runner forward the kwarg)"
  - "D-12 honored: cli.py --raw help text anchor updated from tests/ to tests/contract/"
  - "Phase 09 D-01a precedence preserved: positional scope first, then --junitxml=, then forwarded args"
  - "_runner.run_pytest_subprocess docstring (lines 136-160 area) left as-is — verbatim inspection found no prose mentioning 'tests/' as the collected path (the docstring describes _build_pytest_args(None, pytest_args) abstractly)"
metrics:
  duration_minutes: ~15
  files_modified: 3
  tasks_completed: 2
  commits: 2
  tdd_tests_added: 5
  completed: 2026-05-11
---

# Phase 15 Plan 02: Runner default scope flip + --with-framework opt-in — Summary

Scope-aware pytest argv: the operator's `mcp-test-framework run` now collects only `tests/contract/` by default, with `--with-framework` as the opt-in superset that appends `tests/framework/`. The change is a single keyword-argument threaded through three layers (`cli.py:run` -> `run_pytest_subprocess` -> `_build_pytest_args`) plus a new Typer flag declaration and a one-string help-text anchor update. The `--raw` mode picks up the same scope behavior automatically because both default-mode and raw-mode argv builders go through `_build_pytest_args`.

## What Was Built

**Two atomic commits:**

| Task | Commit  | Description                                                                    |
| ---- | ------- | ------------------------------------------------------------------------------ |
| 1    | 01e1272 | Add scope-aware `with_framework` kwarg to `_build_pytest_args` + 5 TDD tests   |
| 2    | d7346c5 | Add `--with-framework` Typer flag + plumbing + `--raw` help text anchor (D-12) |

### Three plumbed call sites (the threading)

1. **Typer surface** — `cli.py:run` declares `with_framework: bool = typer.Option(False, "--with-framework", ...)` between the `quiet` flag and the `pytest_args` positional argument.
2. **CLI -> runner** — Both `_runner.run_pytest_subprocess(...)` invocations in `cli.py:run` (raw branch and default branch) forward `with_framework=with_framework`.
3. **Runner -> args builder** — `run_pytest_subprocess` accepts a keyword-only `with_framework: bool = False` parameter and forwards it to both `_build_pytest_args(...)` call sites (raw branch ~line 164, default branch ~line 194).

### Argv shape

| Invocation                          | with_framework value | Emitted positional argv                |
| ----------------------------------- | -------------------- | -------------------------------------- |
| `mcp-test-framework run`            | `False`              | `["tests/contract"]`                   |
| `mcp-test-framework run --with-framework` | `True`         | `["tests/contract", "tests/framework"]` |
| `mcp-test-framework run --raw`      | `False`              | `["tests/contract"]`                   |
| `mcp-test-framework run --raw --with-framework` | `True`     | `["tests/contract", "tests/framework"]` |

The rest of the argv (`--junitxml=PATH`, forwarded passthrough args) is unchanged: positional scope first, then explicit flags, then forwarded args — Phase 09 D-01a precedence preserved.

### New Typer flag

```python
with_framework: bool = typer.Option(
    False,
    "--with-framework",
    help=(
        "Also collect tests/framework/ (the framework's own self-tests) "
        "in addition to the operator-default tests/contract/. Use this for "
        "maintainer runs and CI jobs that need the full suite. The default "
        "(without this flag) collects only the SUT-contract surface."
    ),
),
```

### Help text anchor update (D-12)

`cli.py:371` (the `--raw` help text):

```diff
- "`uv run pytest tests/` modulo the config pre-flight gate "
+ "`uv run pytest tests/contract/` modulo the config pre-flight gate "
```

### Docstring update for `run_pytest_subprocess` (per D-12)

The plan asked the executor to inspect `_runner.py:136-160` (the `run_pytest_subprocess` docstring) for any prose mentioning `tests/` as the collected path. **Finding:** the docstring describes `_build_pytest_args(None, pytest_args)` abstractly, with no literal mention of `tests/`. Left as-is. Documented here per the plan's "document this finding in the task summary" instruction.

The `_build_pytest_args` docstring itself was extended with a new paragraph citing Phase 15 D-03:

```
Phase 15 D-03: scope is operator-default ``tests/contract`` only;
``with_framework=True`` APPENDS ``tests/framework`` (not REPLACE) so
``--with-framework`` is a superset matching the pre-split
``pytest tests/`` collection.
```

## TDD Test Additions

Five new tests in `tests/framework/test_runner_subprocess.py` pin the scope contract:

| Test                                                                       | Asserts                                                                                                |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `test_build_pytest_args_default_scope_is_contract_only`                    | `with_framework=False` -> `["tests/contract"]`                                                         |
| `test_build_pytest_args_with_framework_appends_framework_subtree`          | `with_framework=True` -> `["tests/contract", "tests/framework"]` (APPEND, D-02)                       |
| `test_build_pytest_args_default_kwarg_omitted_is_contract_only`            | Omitting the kwarg behaves like `with_framework=False`                                                 |
| `test_build_pytest_args_junitxml_inserted_after_scope_before_passthrough`  | Phase 09 D-01a precedence: positional scope, then `--junitxml=`, then forwarded args                  |
| `test_build_pytest_args_with_framework_keeps_junit_and_passthrough_order`  | Scope expansion does not reshuffle the rest of the argv                                                |

**RED phase confirmed:** all 5 failed before implementation (4 with `TypeError: unexpected keyword argument 'with_framework'`, 1 with `AssertionError: ['tests'] == ['tests/contract']`).
**GREEN phase confirmed:** all 5 pass after implementation.

## Requirements Implemented

- **SURFACE-02** — `--with-framework` opt-in flag at the operator CLI; APPEND semantics; default scope = `tests/contract/`.

## Verification Checklist (from PLAN §verification)

1. ✓ `uv run mcp-test-framework run --help 2>&1 | grep -E "with-framework|tests/contract"` shows both the new flag and the updated `--raw` anchor:
   ```
   pytest tests/contract/` modulo the config
   --with-framework                Also collect tests/framework/ (the
                                   the operator-default tests/contract/. Use
   ```
2. ✓ `uv run pytest tests/framework/test_runner_subprocess.py` — 25 of 26 tests pass (the 1 deselected is a pre-existing path-bug introduced by Plan 15-01's file move; see Deferred Issues below). The 5 new TDD tests pass.
3. ✓ Function-body-scoped static check: `awk` slice of `_build_pytest_args` shows 0 occurrences of bare `"tests"`, exactly 1 occurrence of `"tests/contract"`, exactly 1 occurrence of `"tests/framework"`.
4. ✓ `--with-framework` declared as `typer.Option(False, ...)` — verified by `grep -n '"--with-framework"' cli.py` returning line 396.
5. ✓ Both `_runner.run_pytest_subprocess(...)` invocations in `cli.py:run` forward `with_framework=with_framework` — verified by `grep -c 'with_framework=with_framework' cli.py` returning 2.

## Acceptance Criteria (PLAN §acceptance_criteria, both tasks)

**Task 1:**
- ✓ All 5 new TDD tests pass.
- ✓ Function-body bare `"tests"` literal eliminated (count 0).
- ✓ Function-body `"tests/contract"` count exactly 1; `"tests/framework"` count exactly 1.
- ✓ `grep -n 'with_framework'` in `_runner.py` returns 3 hits (Task 1: param + gate + docstring); after Task 2 the count grew to include the `run_pytest_subprocess` signature.
- ✓ Keyword-only marker (`*,`) present in signature.
- ✓ Full file suite passes for the new tests (regression-free for all other tests except the pre-existing path bug).

**Task 2:**
- ✓ `with_framework: bool = False` appears in `_runner.py` exactly 2 times (one in each function's signature).
- ✓ `with_framework=with_framework` appears in `_runner.py` exactly 2 times (the two `_build_pytest_args` call sites).
- ✓ `with_framework=with_framework` appears in `cli.py` exactly 2 times (the two `run_pytest_subprocess` call sites).
- ✓ `--with-framework` Typer Option declared exactly once in `cli.py`.
- ✓ Old anchor `\`uv run pytest tests/\` modulo` gone (0 matches in `cli.py`).
- ✓ New anchor `uv run pytest tests/contract/` appears in `cli.py` (1 match at line 371 plus the help-text reference at line 399).
- ✓ `--help` renders the new flag with its help text.
- ✓ Framework test suite runs without regressions in the runner-subprocess module.

## Deviations from Plan

**None of substance.**

### Notes worth recording

1. **Pre-existing path bug in `test_plugins_list_does_not_register_reporter`.** After Plan 15-01 moved `test_runner_subprocess.py` from `tests/` to `tests/framework/`, the test's `Path(__file__).resolve().parents[1]` logic resolves to `tests/`, not the project root, so the fallback file read at `repo_root / "tests" / "conftest.py"` looks for `tests/tests/conftest.py` (a path that does not exist). The test fails identically with or without Plan 15-02's changes — verified by `git stash` reproducing the failure on a clean Plan 15-01 baseline. Logged in `deferred-items.md` for Plan 15-04 (verification) or a follow-up quick task. Out of scope per the executor's "directly caused by the current task's changes" boundary.

2. **Worktree config bootstrap.** The worktree lacks `config.yaml` by default; copied from parent and edited to `version: 2` with `model: qwen3:0.6b` (the locally installed Ollama model). This matches the project's `feedback_worktree_config_setup.md` memory note. The created `config.yaml` is local-only (the repo's `.gitignore` covers it; nothing tracked).

3. **Docstring update for `run_pytest_subprocess` reduced to zero.** Per the plan's Task 1 step 3, inspected the `run_pytest_subprocess` docstring (lines 136-160) for any literal mention of `tests/` as the collected path. None found — the docstring describes `_build_pytest_args(None, pytest_args)` abstractly. The `_build_pytest_args` docstring itself received the Phase 15 D-03 paragraph as part of Task 1.

## Auto-fixed Issues

None — pure additive plumbing change; no bugs encountered in the new code path. The pre-existing path bug in `test_plugins_list_does_not_register_reporter` was deferred per scope boundary.

## Deferred Issues

See `.planning/phases/15-operator-vs-framework-test-surface-split/deferred-items.md` for the pre-existing `test_plugins_list_does_not_register_reporter` path-bug introduced by Plan 15-01's file relocation. Two-character fix (`parents[1]` -> `parents[2]`) recommended for Plan 15-04 or a follow-up quick task.

## Threat Flags

None. The new `with_framework` flag is a typed Boolean from the Typer surface; no operator-supplied string ever reaches the pytest argv. Threat register T-15-05/T-15-06/T-15-07 in the PLAN were already assessed as NONE/LOW.

## Self-Check: PASSED

- ✓ `src/mcp_test_framework/_runner.py` modified — `_build_pytest_args` and `run_pytest_subprocess` both accept `with_framework: bool = False`.
- ✓ `src/mcp_test_framework/cli.py` modified — `--with-framework` flag declared, both `_runner.run_pytest_subprocess(...)` invocations forward it, `--raw` help anchor updated to `tests/contract/`.
- ✓ `tests/framework/test_runner_subprocess.py` modified — 5 new TDD tests added under "Plan 15-02" comment block.
- ✓ Commit `01e1272` exists in git log.
- ✓ Commit `d7346c5` exists in git log.
- ✓ No edits to `STATE.md`, `ROADMAP.md`, `README.md`, or `docs/` (per parallel-execution guardrails).
