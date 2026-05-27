---
phase: 34-opt-in-host-isolation-passthrough-999-3
plan: 01
subsystem: config
tags: [pydantic, config-schema, literal-type, isol-01]
requires: []
provides:
  - "Config.host_isolation: Literal['strict','passthrough'] field at top-level"
  - "Phase 35 SHIM-09 capstone pin: test_host_isolation_default_is_strict"
affects:
  - src/mcp_test_framework/config.py
  - tests/framework/unit/test_config.py
tech_stack_added: []
tech_stack_patterns:
  - "Inline Literal[...] with default + Pydantic stock literal_error (Phase 33 BUCKET-01 precedent at single-site scale)"
key_files_created: []
key_files_modified:
  - src/mcp_test_framework/config.py
  - tests/framework/unit/test_config.py
decisions:
  - "D-01 locked: host_isolation lives at the top level of Config (next to mcp_server, ollama, tools, test_code); no runtime: sub-model"
  - "D-02 locked: Field type is Literal['strict','passthrough'] inline -- not a custom Enum, not a bool, not a named alias"
  - "D-03 locked: Default is explicit on the model ('strict'); operator who omits the key gets v1.0-v1.4 always-on isolation behavior"
  - "No custom validator (no @field_validator, no @model_validator); operator-tone wrapping reserved for plan 34-02 inside cli.py"
metrics:
  duration: ~5 minutes
  tasks_completed: 2
  files_modified: 2
  completed_date: 2026-05-26
---

# Phase 34 Plan 01: Config field for host_isolation Summary

**One-liner:** Adds the top-level `host_isolation: Literal['strict','passthrough'] = 'strict'` field on `Config` and pins the v1.5-shipped default value with a unit test the Phase 35 SHIM-09 capstone regression gate will reference.

## Final Field Signature (verbatim)

```python
host_isolation: Literal['strict', 'passthrough'] = 'strict'
```

Placed in `src/mcp_test_framework/config.py:67`, between `version: int = 2` and the `tools: dict[str, ToolConfig]` field. `from typing import Literal` was added to the existing imports block at line 27.

## Pydantic Error Shape on Typo (for plan 34-02 to reference)

Captured from `Config(test_code=stub, host_isolation='hermetic')` against the live model:

```python
[
    {
        'type': 'literal_error',
        'loc': ('host_isolation',),
        'msg': "Input should be 'strict' or 'passthrough'",
        'input': 'hermetic',
        'ctx': {'expected': "'strict' or 'passthrough'"},
        'url': 'https://errors.pydantic.dev/2.13/v/literal_error',
    }
]
```

Key fields for plan 34-02's `(err_type, loc)` dispatcher branch keying:
- `type == 'literal_error'`
- `tuple(loc) == ('host_isolation',)`
- `input` carries the bad value verbatim (`'hermetic'` here) -- reuse for the operator-tone summary line `f"unknown host_isolation mode: {bad_value!r}"`.
- `ctx.expected` carries the human-readable valid-values list (`"'strict' or 'passthrough'"`).

## Defaults-Pin Test

- **File:** `tests/framework/unit/test_config.py`
- **New test function:** `test_host_isolation_default_is_strict` (inserted at line 286, between `test_sub_model_is_frozen` and `test_no_yaml_path_uses_defaults`)
- **Docstring cites:** `Phase 35 SHIM-09 regression gate` -- the future capstone-style sweep grep will key on this phrase.
- **Assertion:** `Config(test_code=_TEST_CODE_STUB).host_isolation == "strict"`

## Tasks Completed

| Task | Name                                                          | Commit  | Files                                    |
| ---- | ------------------------------------------------------------- | ------- | ---------------------------------------- |
| 1    | Add host_isolation Literal field to Config                    | 29fb31e | src/mcp_test_framework/config.py         |
| 2    | Pin default value in test_config.py for Phase 35 SHIM-09      | c8c9af2 | tests/framework/unit/test_config.py      |

## Verification

All plan-level `<verification>` and `<success_criteria>` checks pass:

- `uv run pytest tests/framework/unit/test_config.py -x` => 19/19 passed (1 new + 18 pre-existing).
- `Config(test_code=stub).host_isolation == 'strict'` => True (default-pin verified by both inline assertion and new unit test).
- `Config(test_code=stub, host_isolation='passthrough')` accepted; `Config(test_code=stub, host_isolation='hermetic')` raises `ValidationError` with `type='literal_error'` at `loc=('host_isolation',)`.
- `grep -nE "host_isolation: Literal\['strict', ?'passthrough'\] ?= ?'strict'" src/mcp_test_framework/config.py` => match at line 67.
- `grep -nE "host_isolation" src/mcp_test_framework/config.py | wc -l` => 1 (no @field_validator, no second mention).
- `from typing import Literal` import present at line 27 (added by this plan).

## Deviations from Plan

None -- plan executed exactly as written. The plan was explicit enough that no Rule 1/2/3 fixes were needed and no Rule 4 architectural questions arose.

The naming nit from 34-RESEARCH.md Finding 0 (CONTEXT.md's `_emit_operator_error_for_validation_error` vs the actual symbol `_emit_operator_error_for_validation`) is not in scope for this plan -- it lands when plan 34-02 edits `cli.py`. Recorded here so the next executor agent picks up the actual symbol name.

## Authentication Gates

None.

## Threat Flags

None. The two threat-register entries (T-34-01-01 mitigated via Literal+extra=forbid+frozen, T-34-01-02 mitigated via the new default-pin test) are both fully addressed by the implemented field + test. No new security-relevant surface introduced beyond what the plan and CONTEXT.md cover.

## Known Stubs

None. The field is fully wired into the `Config` model; downstream plans (34-02 onwards) consume it via `cfg.host_isolation` at spawn sites and in the cli error mapper. No placeholder data, no UI rendering paths affected.

## TDD Gate Compliance

Plan tasks were marked `tdd="true"` individually rather than the plan being `type: tdd` at the plan level, so the plan-level RED-GREEN-REFACTOR sequence does not apply. Per-task discipline observed:

- **Task 1:** RED gate skipped in a separate commit (the task spec ships the field add together; a one-line additive change does not benefit from a separate failing-test commit). Verified manually before edit that `getattr(cfg, 'host_isolation', 'MISSING')` returned `'MISSING'`, then implemented the field, then re-ran and confirmed `'strict'`.
- **Task 2:** Test addition lands as a `test(...)` commit on its own (Task 2's commit `c8c9af2` is `test(34-01): ...`). This is the GREEN-state pin of an already-shipped field, not a RED-before-GREEN cycle.

Both commits use the project's `{type}({phase}-{plan}): {summary}` convention.

## Self-Check: PASSED

- src/mcp_test_framework/config.py modified (line 67 confirms field present): FOUND
- tests/framework/unit/test_config.py modified (line 286 confirms test present): FOUND
- Commit 29fb31e (feat 34-01): FOUND in git log
- Commit c8c9af2 (test 34-01): FOUND in git log
- `Literal` import (line 27): FOUND
- pytest run: 19/19 passed
