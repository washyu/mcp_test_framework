---
phase: 33-per-bucket-skip-granularity-in-toolconfig-999-1
plan: 06
subsystem: reporter
tags:
  - reporter
  - digest
  - gap-closure
  - bucket-04
  - cr-01
requirements:
  - BUCKET-04
gap_closure: true
dependency_graph:
  requires:
    - 33-01 (TEST_FUNCTION_BUCKETS source-of-truth mapping)
    - 33-04 (Bucket skips: digest line — the half this fix completes)
  provides:
    - Bucket-aware planned_cases computation in _render_pre_run_digest
    - Regression guard against future drift between Bucket skips and Test plan lines
  affects:
    - src/mcp_test_framework/_runner.py::_render_pre_run_digest
    - tests/framework/test_pre_run_digest_buckets.py
tech_stack:
  added: []
  patterns:
    - module-level _BUCKET_SIZE precompute from TEST_FUNCTION_BUCKETS (single-pass lookup)
    - per-tool loop with set-membership bucket filter
    - dynamic expected-value derivation in regression test (test computes from source-of-truth)
key_files:
  created: []
  modified:
    - src/mcp_test_framework/_runner.py
    - tests/framework/test_pre_run_digest_buckets.py
decisions:
  - "Kept CASES_PER_CONTRACT_TOOL constant and its docstring reference verbatim — surgical scope; WR-04..WR-06 polish deferred per plan instruction."
  - "Used direct render-and-parse with io.StringIO over Pytester subprocess fixture — cheaper to maintain (matches existing 4 tests' style)."
  - "Expected values derived dynamically from TEST_FUNCTION_BUCKETS inside the test — protects against future bucket re-balancing (T-33-13 mitigation)."
metrics:
  duration_minutes: 7
  tasks_completed: 2
  files_modified: 2
  tests_added: 1
  framework_tests_total_after: 728
  framework_tests_total_before: 727
  completed_date: 2026-05-26
---

# Phase 33 Plan 06: Bucket-aware Test plan count (CR-01 gap-closure) Summary

Replaced the constant-multiplier `planned_cases = running_n * CASES_PER_CONTRACT_TOOL` at `_runner.py:1184` with a per-tool, bucket-aware loop that subtracts the case count of each bucket listed in that tool's `skip_buckets`, and pinned the invariant with a 4-scenario regression test.

## One-liner

CR-01 BLOCKER fix: `Test plan: N` now reflects per-tool `skip_buckets` deductions, restoring digest internal consistency with the `Bucket skips: M` line (Truth #3 in `33-VERIFICATION.md` flips ✗ → ✓).

## What changed

### `src/mcp_test_framework/_runner.py`

**Edit 1 — Import + module-level cache.** Added after `from .rubrics import RUBRIC_IDS`:

```python
from mcp_test_framework.contracts._buckets import TEST_FUNCTION_BUCKETS

# Per-bucket case counts derived from the source-of-truth mapping in
# contracts/_buckets.py. Sum across buckets == CASES_PER_CONTRACT_TOOL (10),
# pinned invariant by tests/framework/test_bucket_map.py.
_BUCKET_SIZE: dict[str, int] = {b: len(fns) for b, fns in TEST_FUNCTION_BUCKETS.items()}
```

**Edit 2 — Replaced line 1184.**

Before:

```python
planned_cases = running_n * CASES_PER_CONTRACT_TOOL
```

After:

```python
# Per-tool, bucket-aware total. For each running tool, sum the case
# counts of every bucket NOT in that tool's skip_buckets. When no
# tool has skip_buckets, the result is mathematically identical to
# running_n * CASES_PER_CONTRACT_TOOL — baseline byte-identity is
# preserved (the invariant tested by test_pre_run_digest_buckets.py's
# baseline case). For a tool with skip_buckets=["output"] (3 cases),
# the tool contributes 7 instead of 10. CR-01 fix (phase 33-06):
# without this loop the Test plan: line would contradict the
# Bucket skips: line emitted above (digest internal consistency).
planned_cases = 0
for t in running:
    skipped_buckets = set(
        getattr(ctx.tools_config.get(t), "skip_buckets", []) or []
    )
    planned_cases += sum(
        sz for b, sz in _BUCKET_SIZE.items() if b not in skipped_buckets
    )
```

`CASES_PER_CONTRACT_TOOL: int = 10` at line 437 is preserved (still referenced in the docstring at ~1150 and reserved for external callers). The `_render_pre_run_digest` docstring's `R * CASES_PER_CONTRACT_TOOL` mention is intentionally NOT touched — that polish lands under WR-04..WR-06 in a follow-up plan per the plan's explicit out-of-scope guidance.

### `tests/framework/test_pre_run_digest_buckets.py`

Appended one new test: **`test_digest_test_plan_count_deducts_skip_buckets`** — exercises 4 scenarios via sequential assert blocks, each rendering through `io.StringIO` and extracting the integer from the `Test plan:` line:

| Scenario | Tools / skip_buckets | Expected `Test plan:` |
|----------|----------------------|------------------------|
| A — baseline | 2 tools, both `ToolConfig()` | 20 (2 × 10) |
| B — one bucket skipped | 1 tool with `skip_buckets=["output"]` | 7 (10 − 3) |
| C — all buckets skipped | 1 tool with `skip_buckets=["schema","judge","output"]` | 0 |
| D — multi-tool, mixed | tool_a `["judge"]`, tool_b `["output"]` | 14 (7 + 7) |

Expected values are computed dynamically from `TEST_FUNCTION_BUCKETS` at test time, so any future re-balance of bucket contents in `contracts/_buckets.py` shifts both the implementation and the expected value in lockstep (T-33-13 drift mitigation).

The pre-existing 4 tests (`test_digest_with_no_skip_buckets_is_byte_identical_to_baseline`, `test_digest_emits_bucket_skips_line_when_any_tool_has_skip_buckets`, `test_digest_bucket_skips_with_explain_omits_hint`, `test_count_bucket_skips_helper`), the module-level docstring, the imports, and the `_ctx` helper are unchanged.

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest tests/framework/test_pre_run_digest_buckets.py -v` | 5 passed |
| `uv run pytest tests/framework/ -x` | 728 passed, 2 skipped, 18 deselected, 1 xfailed (vs 727 before) |
| Manual smoke: `create_proxmox_vm` + `skip_buckets=["output"]` | `Test plan:   7 contract cases` (NOT 10) |
| Manual smoke: `create_proxmox_vm` + no `skip_buckets` | `Test plan:   10 contract cases` (baseline byte-identity preserved) |
| `grep "from mcp_test_framework.contracts._buckets import TEST_FUNCTION_BUCKETS" src/mcp_test_framework/_runner.py` | 1 line |
| `grep "_BUCKET_SIZE" src/mcp_test_framework/_runner.py` | 2 lines (def + use) |
| `grep "planned_cases = running_n \* CASES_PER_CONTRACT_TOOL" src/mcp_test_framework/_runner.py` | 0 matches (old line removed) |
| `grep "CASES_PER_CONTRACT_TOOL" src/mcp_test_framework/_runner.py` | 4 occurrences (constant + docstring + comment refs retained) |
| `grep "def test_" tests/framework/test_pre_run_digest_buckets.py` | 5 |
| `grep "def test_digest_test_plan_count_deducts_skip_buckets"` | 1 line |

## Deviations from Plan

None — plan executed exactly as written. The two edits to `_runner.py` and the appended test in `test_pre_run_digest_buckets.py` match the plan's verbatim code blocks byte-for-byte. WR-01..WR-06 warnings remain out of scope as instructed.

## Cross-references

- **Gap source:** `.planning/phases/33-per-bucket-skip-granularity-in-toolconfig-999-1/33-VERIFICATION.md` — CR-01 BLOCKER section. Truth #3 ("digest is internally consistent: 'Bucket skips: M' and 'Test plan: N' agree") flips from ✗ to ✓ on re-verification.
- **Sibling plans:**
  - `33-01` — landed `TEST_FUNCTION_BUCKETS` mapping (the source-of-truth this fix imports).
  - `33-03` — landed the collection-time filter that actually deselects bucket-skipped cases; this plan only fixes the *digest count*, the runtime behavior was already correct.
  - `33-04` — landed the `Bucket skips:` digest line whose contradiction with `Test plan:` is now resolved.

## Commits

- `99d3775` `fix(33-06): make Test plan count bucket-aware in pre-run digest`
- `1df8772` `test(33-06): pin Test plan count against bucket-aware expected value`

## TDD Gate Compliance

Both tasks were marked `tdd="true"` in the plan. The plan author's intended cycle here is "broken pre-existing state (RED, documented in 33-VERIFICATION.md CR-01) → implementation fix (GREEN, Task 1) → regression pin (Task 2)". The commit log shows `fix(33-06)` followed by `test(33-06)` — a `fix`+`test` pair rather than the canonical `test`+`feat` RED/GREEN gates, because:

- The RED state is a documented BLOCKER in `33-VERIFICATION.md`, not a transient test commit.
- The plan's Task 1 acceptance criteria explicitly requires Task 1 to pass the existing 4 tests in isolation, with Task 2 landing additively.
- Strict canonical RED-then-GREEN would have required committing a failing test first, which the plan does not request.

This is a documented, intentional deviation from the strict TDD gate sequence — flagged here per the plan-level TDD enforcement protocol.

## Self-Check: PASSED

- `src/mcp_test_framework/_runner.py` modified — FOUND
- `tests/framework/test_pre_run_digest_buckets.py` modified — FOUND
- Commit `99d3775` (fix Task 1) — FOUND
- Commit `1df8772` (test Task 2) — FOUND
- All 5 tests in `test_pre_run_digest_buckets.py` PASS
- Full framework suite (728 tests) PASSES with no regressions
- Both manual smoke tests produce the expected literal lines
