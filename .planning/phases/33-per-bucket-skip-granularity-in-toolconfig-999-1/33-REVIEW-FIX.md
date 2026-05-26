---
phase: 33-per-bucket-skip-granularity-in-toolconfig-999-1
fixed_at: 2026-05-26T00:00:00Z
review_path: .planning/phases/33-per-bucket-skip-granularity-in-toolconfig-999-1/33-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 6
skipped: 1
status: partial
---

# Phase 33: Code Review Fix Report

**Fixed at:** 2026-05-26
**Source review:** `.planning/phases/33-per-bucket-skip-granularity-in-toolconfig-999-1/33-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (CR-01 + WR-01..WR-06)
- Fixed: 6 (all warnings)
- Skipped: 1 (CR-01, already resolved by phase 33-06)
- Info findings (IN-01..IN-04): not in scope this pass

Framework test suite ran green after every fix
(`uv run pytest tests/framework/ -x -q --tb=short`):
- baseline before fixes: 728 passed
- after WR-01: 729 passed (+1 regression test)
- after WR-02: 732 passed (+3 regression tests)
- after WR-03: 733 passed (+1 regression test)
- after WR-04: 734 passed (+1 regression test)
- after WR-05: 734 passed (existing test updated to new layout)
- after WR-06: 735 passed (+1 regression test)

No pre-existing tests broke; one existing test
(`test_pre_run_digest_emits_banner_and_label_block`) was updated in
lockstep with the WR-05 layout change.

## Fixed Issues

### WR-01: `skip_buckets` allows silent duplicates

**Files modified:** `src/mcp_test_framework/models.py`, `tests/framework/test_tool_config.py`
**Commit:** 702a586
**Applied fix:** Added `_no_duplicate_buckets` field validator on
`ToolConfig.skip_buckets` that raises a `ValidationError` with an
operator-tone message when the list contains duplicate bucket names.
Regression test (`test_skip_buckets_rejects_duplicate_entries`) covers
both straight duplicate (`["output", "output"]`) and mixed-duplicate
(`["schema", "judge", "schema"]`) inputs.

### WR-02: `_count_bucket_skips` and `--explain` Section 2 ignore `discovered_tools`

**Files modified:** `src/mcp_test_framework/_runner.py`, `tests/framework/test_pre_run_digest_buckets.py`, `tests/framework/test_explain_buckets.py`
**Commit:** 2001c14
**Applied fix:** `_count_bucket_skips` gained an optional `discovered`
parameter; when supplied (the new digest call passes
`ctx.discovered_tools`), tools absent from the discovery list are
excluded from the count. `_render_skipped_tools_explain`'s Section 2
filters `bucket_skipped` against `discovered_set` so undiscovered
configured tools no longer appear in the explain block. Legacy callers
that omit the parameter retain the pre-WR-02 behavior so
`tests/framework/test_pre_run_digest_buckets.py::test_count_bucket_skips_helper`
continues to pass unmodified. Two new regression tests pin the new
filter on both the helper and the renderer surface.

### WR-03: Section 1 / Section 2 indentation mismatch

**Files modified:** `src/mcp_test_framework/_runner.py`, `tests/framework/test_explain_buckets.py`
**Commit:** 3b9d526
**Applied fix:** Section 1's defensive bucket emit in
`_render_skipped_tools_explain` switched from 2-space to 4-space lead
so bucket rows visually nest under their tool's whole-tool line,
matching Section 2's nested shape. Regression test uses
`ToolConfig.model_construct` to bypass the model validator (which
normally rejects `skip=True + skip_buckets`) and exercise the
defensive branch directly.

### WR-04: `Judges:` digest line does not reflect judge-bucket suppression

**Files modified:** `src/mcp_test_framework/_runner.py`, `tests/framework/unit/test_runner_pre_run_digest.py`
**Commit:** a04e361
**Applied fix:** `_compose_judges_from_tool_configs` skips tools where
`"judge" in skip_buckets`. The union of judges now reflects only tools
that will actually run judge tests, so the `Judges:` line cannot lie
when every running tool has bucket-skipped judges. Regression test
covers both helper output (`[]` for single tool with
`skip_buckets=["judge"]`) and renderer output (`Judges:      (none
configured)` in the digest).

### WR-05: `Bucket skips:` column alignment drifts from `Skipping:`

**Files modified:** `src/mcp_test_framework/_runner.py`, `tests/framework/unit/test_runner_pre_run_digest.py`, `README.md`, `docs/LIBRARY-MODE.md`
**Commit:** 61d5427
**Applied fix:** Widened the `Skipping:` value field in
`_render_pre_run_digest` from `:>2` to `:>3` so both `Skipping:` and
`Bucket skips:` number columns right-align at the same character.
Updated `README.md` and `docs/LIBRARY-MODE.md` canonical example outputs
in lockstep (one extra space between `Skipping:` and the digit) so the
docs do not drift. `_render_header` and `_render_scenario_pre_run_digest`
were intentionally NOT changed -- they are separate functions/regimes
and were not flagged by the review. Updated the existing baseline test
`test_pre_run_digest_emits_banner_and_label_block` to expect the new
layout.

### WR-06: Validator order surfaces `skip_reason` error before mutual-exclusion error

**Files modified:** `src/mcp_test_framework/models.py`, `tests/framework/test_tool_config.py`
**Commit:** 7b336ca
**Applied fix:** Reordered the two `model_validator(mode="after")`
methods so `_skip_buckets_not_with_whole_tool_skip` runs ahead of
`_skip_requires_reason`. An operator who writes
`skip=True, skip_buckets=["..."]` (with or without `skip_reason`) now
sees the mutual-exclusion message first -- the more informative
diagnostic in that case. Regression test asserts the mutual-exclusion
message is present when both rules are violated. Other existing
validator-error tests (e.g.
`test_skip_true_with_non_empty_skip_buckets_rejected`,
`test_skip_true_with_blank_skip_reason_rejected`) still pass; both
validators still fire, only the surface ordering changed.

## Skipped Issues

### CR-01: Pre-run "Test plan" count ignores `skip_buckets`

**File:** `src/mcp_test_framework/_runner.py:1184`
**Reason:** already_resolved (out of scope per orchestrator instruction).
The REVIEW.md was written before plan 33-06 landed. The CR-01 BLOCKER was
fixed by commit `99d3775` (`_render_pre_run_digest` now computes
`planned_cases` per-tool with bucket-aware deductions; see
`src/mcp_test_framework/_runner.py:1199-1206` and the canonical
`_BUCKET_SIZE` mapping at line 45-50) and commit `1df8772` (regression
test 5 in `tests/framework/test_pre_run_digest_buckets.py` --
`test_digest_test_plan_count_deducts_skip_buckets`, lines 174-252 --
pins the new behavior across four scenarios including the
`create_proxmox_vm + skip_buckets=["output"]` README example).
**Original issue:** Pre-run digest's `Test plan: N contract cases`
overstated cases by `len(skip_buckets) * bucket_size` per tool because
the count was `running_n * 10` and ignored `skip_buckets`.

---

_Fixed: 2026-05-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
