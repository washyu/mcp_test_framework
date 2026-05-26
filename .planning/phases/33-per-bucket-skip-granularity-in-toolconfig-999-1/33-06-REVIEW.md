---
phase: 33-per-bucket-skip-granularity-in-toolconfig-999-1 (33-06 gap-closure)
reviewed: 2026-05-26T00:00:00Z
depth: quick
files_reviewed: 2
files_reviewed_list:
  - src/mcp_test_framework/_runner.py
  - tests/framework/test_pre_run_digest_buckets.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 33-06: Code Review Report

**Reviewed:** 2026-05-26
**Depth:** quick
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Targeted follow-up review of the 33-06 gap-closure that fixed CR-01 BLOCKER
from the prior 33-REVIEW. Diff is surgical:

- `src/mcp_test_framework/_runner.py`: +1 import (`TEST_FUNCTION_BUCKETS`),
  +1 module-level `_BUCKET_SIZE` dict, and a 7-line replacement of
  `planned_cases = running_n * CASES_PER_CONTRACT_TOOL` with a per-tool,
  bucket-aware accumulator.
- `tests/framework/test_pre_run_digest_buckets.py`: +91 lines appending
  `test_digest_test_plan_count_deducts_skip_buckets` with four scenarios
  (A baseline, B single bucket, C all buckets, D mixed).

The core arithmetic is correct. Bucket sizes derived from
`contracts/_buckets.py` are schema=4, judge=3, output=3 (sum=10, matching
`CASES_PER_CONTRACT_TOOL`). All four scenario expected values reconcile.
The `running` filter at line 1181-1185 guarantees every `t` passed to
`ctx.tools_config.get(t)` is a key in `tools_config`, so the `.get()`
cannot return `None` in normal flow. The `getattr(..., [])` + `or []`
chain remains defensively correct even if `tools_config[t].skip_buckets`
is `None`.

Baseline byte-identity (test 1 at line 46) is preserved because every
running tool contributes `sum(_BUCKET_SIZE.values()) == 10` when
`skip_buckets` is empty.

CR-01 internal-consistency (Bucket-skips line ↔ Test-plan line) is fixed
and now regression-pinned by Scenario B/C/D. No new blockers identified.

One WARNING (test isolation depends on a module-level dict that may be
reset by a future bucket re-balance) and two INFO items below.

## Warnings

### WR-01: `_BUCKET_SIZE` captured at module-import time; test re-derives independently

**File:** `src/mcp_test_framework/_runner.py:50`, `tests/framework/test_pre_run_digest_buckets.py:184`
**Issue:** `_BUCKET_SIZE` is computed once at module import as a top-level
dict comprehension over `TEST_FUNCTION_BUCKETS`. The new regression test
*also* re-derives a local `bucket_size` from the same source. This is
correct for catching arithmetic regressions in `_render_pre_run_digest`,
but it has a subtle property the reviewer is required to flag (per
scope_guidance): the test expectations and the SUT both read from the
*same* live import of `TEST_FUNCTION_BUCKETS`. If a future bucket
re-balance silently breaks the `CASES_PER_CONTRACT_TOOL == 10` invariant
(e.g., schema gains a fifth function pushing the sum to 11), Scenario A
will read `2 * 11 == 22` from both sides and pass — silently masking the
drift between `_BUCKET_SIZE` and the locked `CASES_PER_CONTRACT_TOOL`
constant. The cross-check that pins the sum invariant lives in
`tests/framework/test_bucket_map.py` (per the comment at line 49) and in
`test_cases_per_contract_tool_matches_actual_parametrize_count` (per
docstring at line 440-442), but neither is co-located with this digest
regression; a future bucket-rebalance PR that also bumps
`CASES_PER_CONTRACT_TOOL` in lockstep would leave Scenario A green even
if the digest line started over-reporting against the actual pytest
collection. Scenarios B/C/D would still catch *relative* drift, so the
mitigation gap is narrow but worth a sentinel.
**Fix:** Add one explicit invariant assertion at the top of the new test
to anchor the sum invariant locally:
```python
assert full_tool == CASES_PER_CONTRACT_TOOL, (
    f"bucket sum ({full_tool}) drifted from CASES_PER_CONTRACT_TOOL "
    f"({CASES_PER_CONTRACT_TOOL}); rebalance buckets or update the "
    "locked constant in _runner.py"
)
```
This makes the digest regression test fail loudly if anyone re-balances
the buckets without also adjusting the locked constant — closing the
"both sides re-derive the same wrong number" loophole.

## Info

### IN-01: Repeated `set(...)` allocation inside hot loop

**File:** `src/mcp_test_framework/_runner.py:1200-1206`
**Issue:** Inside the `for t in running:` loop a fresh
`set(getattr(ctx.tools_config.get(t), "skip_buckets", []) or [])` is
constructed per tool. For homelab-mcp (~70 tools) this allocates ~70
small sets per pre-run digest emission. Performance is explicitly
out of v1 scope per the review prompt, but this is also a minor
readability concern: the `set(...)` only exists to enable the `b not in
skipped_buckets` membership test, which would work equally well against
the list directly (3 entries max per bucket-name domain). The clarity
trade is negligible either way.
**Fix:** No change required. If touched in a future polish pass, drop
the `set(...)` and rely on the small fixed-size list lookup:
```python
skipped_buckets = getattr(ctx.tools_config.get(t), "skip_buckets", []) or []
planned_cases += sum(
    sz for b, sz in _BUCKET_SIZE.items() if b not in skipped_buckets
)
```

### IN-02: Import ordering — new `TEST_FUNCTION_BUCKETS` import uses absolute path while sibling import is relative

**File:** `src/mcp_test_framework/_runner.py:44-45`
**Issue:** The diff adds:
```python
from .rubrics import RUBRIC_IDS
from mcp_test_framework.contracts._buckets import TEST_FUNCTION_BUCKETS
```
The first uses a package-relative import (`.rubrics`); the second uses
the absolute `mcp_test_framework.contracts._buckets` path. Both resolve
identically at runtime, but mixing styles within adjacent lines of the
same module is inconsistent. The rest of `_runner.py` consistently uses
relative imports (e.g., `from .rubrics import RUBRIC_IDS`).
**Fix:** Use a relative import for symmetry:
```python
from .contracts._buckets import TEST_FUNCTION_BUCKETS
```

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick_
