---
phase: 33-per-bucket-skip-granularity-in-toolconfig-999-1
plan: "01"
subsystem: config-models
tags:
  - pydantic
  - config
  - bucket
  - tdd

dependency_graph:
  requires: []
  provides:
    - "mcp_test_framework.contracts._buckets.TEST_FUNCTION_BUCKETS"
    - "mcp_test_framework.contracts._buckets.BucketName"
    - "ToolConfig.skip_buckets field"
  affects:
    - "src/mcp_test_framework/models.py"
    - "src/mcp_test_framework/contracts/_buckets.py"

tech_stack:
  added: []
  patterns:
    - "Pydantic list[Literal[...]] for enum-constrained list field (no custom validator needed)"
    - "frozenset values in explicit dict constant for immutable, importable bucket mapping"
    - "inspect.getmembers for introspective self-tests that pin module structure"

key_files:
  created:
    - src/mcp_test_framework/contracts/_buckets.py
    - tests/framework/test_bucket_map.py
  modified:
    - src/mcp_test_framework/models.py
    - tests/framework/test_tool_config.py

decisions:
  - "Explicit dict constant (TEST_FUNCTION_BUCKETS) chosen over @pytest.mark.bucket decorators or name-prefix regex -- single grep-able import target for Phase 35 capstone, zero _tests.py touches, rename-drift caught at CI time"
  - "BucketName = Literal['schema','judge','output'] reused in models.py via import (not redefined) -- single source of truth"
  - "No custom field_validator for bucket-name rejection -- Pydantic stock Literal error already names all 3 valid values (CONTEXT D-03)"

metrics:
  duration: "approx 10 minutes"
  completed: "2026-05-26"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 2
---

# Phase 33 Plan 01: _buckets.py source-of-truth + ToolConfig.skip_buckets Summary

**One-liner:** Explicit `TEST_FUNCTION_BUCKETS` dict constant and `ToolConfig.skip_buckets: list[Literal["schema","judge","output"]]` field landing BUCKET-01 + BUCKET-03 via TDD.

## What Was Built

### Task 1: contracts/_buckets.py (TDD)

Created `src/mcp_test_framework/contracts/_buckets.py` with:

- `BucketName = Literal["schema", "judge", "output"]`
- `TEST_FUNCTION_BUCKETS: dict[BucketName, frozenset[str]]` mapping each of the 3 buckets to a frozenset of the 10 contract test function names from `_tests.py`

Created `tests/framework/test_bucket_map.py` with 3 self-tests:
1. `test_every_contract_test_function_belongs_to_exactly_one_bucket` - introspects `contracts._tests` via `inspect.getmembers` and asserts the union matches all `test_*` callables
2. `test_buckets_are_disjoint` - asserts pairwise frozenset intersections are empty
3. `test_bucket_names_are_literal_schema_judge_output` - asserts key set is exactly `{"schema", "judge", "output"}`

### Task 2: ToolConfig.skip_buckets field (TDD)

Modified `src/mcp_test_framework/models.py`:
- Added `from mcp_test_framework.contracts._buckets import BucketName` import
- Added `skip_buckets: list[BucketName] = Field(default_factory=list, ...)` field after `depends_on`

Added 7 tests to `tests/framework/test_tool_config.py`:
- `test_skip_buckets_default_is_empty_list`
- `test_skip_buckets_accepts_single_valid_bucket`
- `test_skip_buckets_accepts_empty_list`
- `test_skip_buckets_accepts_all_three_buckets`
- `test_skip_buckets_rejects_typo_names_all_valid_in_error` (BUCKET-03)
- `test_skip_buckets_rejects_string_not_list`
- `test_skip_buckets_is_frozen_with_toolconfig`

## Commits

| Task | Phase | Commit | Description |
|------|-------|--------|-------------|
| 1 RED | test | ef253fe | Failing tests for TEST_FUNCTION_BUCKETS bucket map |
| 1 GREEN | feat | 616f554 | Add contracts/_buckets.py source-of-truth |
| 2 RED | test | 574cb9e | Failing tests for ToolConfig.skip_buckets field |
| 2 GREEN | feat | 1d9e107 | Add ToolConfig.skip_buckets field (BUCKET-01 + BUCKET-03) |

## Verification Results

```
uv run pytest tests/framework/test_tool_config.py tests/framework/test_bucket_map.py -xvs
31 passed, 3 deselected

uv run pytest tests/framework/ -x --timeout=30 -q
710 passed, 2 skipped, 18 deselected, 1 xfailed
```

## Success Criteria Check

- [x] BUCKET-01: `ToolConfig(skip_buckets=["output"])` constructs; `ToolConfig()` defaults to `[]`
- [x] BUCKET-03: `ToolConfig(skip_buckets=["otput"])` raises ValidationError naming `'schema'`, `'judge'`, `'output'`
- [x] Phase 35 zero-shim import target: `from mcp_test_framework.contracts._buckets import TEST_FUNCTION_BUCKETS`
- [x] `sum(len(v) for v in TEST_FUNCTION_BUCKETS.values()) == 10`

## Deviations from Plan

None - plan executed exactly as written. The explicit dict constant approach was pre-selected by the planner (Claude's Discretion in CONTEXT.md); no alternatives were considered during execution.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. The new surface is:
- `ToolConfig.skip_buckets`: list of strings validated at Pydantic load time (T-33-01 in plan threat model -- mitigated by `list[Literal[...]]`)
- `TEST_FUNCTION_BUCKETS`: read-only frozenset dict (T-33-02 -- mitigated by `test_bucket_map.py` introspection gate)

Both threats are within plan scope and mitigations are implemented.

## Known Stubs

None. Both artifacts are fully implemented and wired:
- `_buckets.py` is a complete constant (no placeholder values)
- `ToolConfig.skip_buckets` is a complete Pydantic field (plan 33-03 will consume it at collection time)

## Self-Check: PASSED

Files exist:
- `src/mcp_test_framework/contracts/_buckets.py` FOUND
- `tests/framework/test_bucket_map.py` FOUND
- `src/mcp_test_framework/models.py` modified FOUND

Commits exist:
- ef253fe FOUND
- 616f554 FOUND
- 574cb9e FOUND
- 1d9e107 FOUND
