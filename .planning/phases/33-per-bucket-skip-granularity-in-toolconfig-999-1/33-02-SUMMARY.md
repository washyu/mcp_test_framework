---
phase: 33-per-bucket-skip-granularity-in-toolconfig-999-1
plan: "02"
subsystem: models / config-validation / docs
tags:
  - pydantic
  - validator
  - error-style
  - tdd
dependency_graph:
  requires:
    - 33-01  # skip_buckets field must exist before redundancy validator can reference it
  provides:
    - BUCKET-01-redundancy-guard  # skip+skip_buckets fail-loud at load time
  affects:
    - src/mcp_test_framework/models.py
    - tests/framework/test_tool_config.py
    - docs/ERROR-STYLE.md
tech_stack:
  added: []
  patterns:
    - "@model_validator(mode='after') sibling validator pattern — mirrors _skip_requires_reason shape"
    - "operator-tone three-part error message registered in ERROR-STYLE.md"
key_files:
  modified:
    - src/mcp_test_framework/models.py
    - tests/framework/test_tool_config.py
    - docs/ERROR-STYLE.md
decisions:
  - "Validator placed immediately after _skip_requires_reason so both redundancy-related validators are co-located"
  - "grep -c returns 1 (not 2) for the validator name because @model_validator(mode='after') decorator does not contain the method name — plan AC was an authoring oversight; behavior is correct"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-26"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 33 Plan 02: Skip+Skip_buckets Redundancy Validator Summary

Reject `skip: true` + non-empty `skip_buckets: [...]` at config load time as redundant operator input. Operator-tone three-part error message registered verbatim in `docs/ERROR-STYLE.md` as a locked reference message.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for redundancy validator | 46eb871 | tests/framework/test_tool_config.py |
| 1 (GREEN) | _skip_buckets_not_with_whole_tool_skip model_validator | 223051b | src/mcp_test_framework/models.py |
| 2 | Register redundancy message in ERROR-STYLE.md | e7c5d82 | docs/ERROR-STYLE.md |

## What Was Built

A new `@model_validator(mode="after")` named `_skip_buckets_not_with_whole_tool_skip` on `ToolConfig`. It sits immediately after the existing `_skip_requires_reason` validator so both redundancy-related validators are co-located. When `skip=True` AND `skip_buckets` is non-empty, Pydantic raises a `ValidationError` at config load time with the operator-tone three-part message:

```
skip=true and skip_buckets are mutually exclusive

skip=true is whole-tool: every bucket is already skipped.
layering skip_buckets on top is redundant intent and the framework will not silently pick which lever wins.

next: keep skip=true to disable every bucket, OR remove skip and use skip_buckets alone to disable named buckets.
```

Four tests pin all four behavioral cases:
- `skip=True` + empty `skip_buckets` — valid (no redundancy)
- `skip=False` + non-empty `skip_buckets` — valid (per-bucket opt-out)
- `skip=False` + empty `skip_buckets` — valid (default state)
- `skip=True` + non-empty `skip_buckets` — **rejected** with operator-tone error

## TDD Gate Compliance

RED commit: `46eb871` — failing test added before implementation
GREEN commit: `223051b` — implementation makes test pass
No refactor needed.

## Deviations from Plan

### Minor: grep -c returns 1 not 2 for validator name

The plan acceptance criteria states `grep -c "_skip_buckets_not_with_whole_tool_skip" src/mcp_test_framework/models.py` should return >= 2 ("decorator line + def line"). However, `@model_validator(mode="after")` does not contain the function name — only the `def` line does. The existing `_skip_requires_reason` validator exhibits the same pattern and also returns 1. The validator is correctly implemented; the AC was an authoring oversight about how Python decorators work. No action needed.

## Verification Results

- `uv run pytest tests/framework/test_tool_config.py -xvs` — 32 passed (0 failures)
- `uv run pytest tests/framework/ -x` — 714 passed, 2 skipped, 1 xfailed (full regression clean)
- `grep -c "skip=true and skip_buckets are mutually exclusive" src/mcp_test_framework/models.py docs/ERROR-STYLE.md` — returns `1` per file (locked verbatim string present in both)

## Known Stubs

None.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. Threats T-33-04 and T-33-05 mitigated as planned.

## Self-Check: PASSED

- [x] `src/mcp_test_framework/models.py` modified — `_skip_buckets_not_with_whole_tool_skip` present
- [x] `tests/framework/test_tool_config.py` modified — 4 new tests present
- [x] `docs/ERROR-STYLE.md` modified — new subsection present
- [x] Commit 46eb871 exists (RED)
- [x] Commit 223051b exists (GREEN)
- [x] Commit e7c5d82 exists (docs)
