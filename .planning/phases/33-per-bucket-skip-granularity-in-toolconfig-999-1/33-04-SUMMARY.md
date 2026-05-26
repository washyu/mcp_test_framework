---
phase: 33-per-bucket-skip-granularity-in-toolconfig-999-1
plan: "04"
subsystem: reporter
tags:
  - reporter
  - explain
  - digest
  - bucket-skip

dependency_graph:
  requires:
    - 33-01  # ToolConfig.skip_buckets field
  provides:
    - _render_skipped_tools_explain bucket extension
    - _count_bucket_skips helper
    - _render_pre_run_digest Bucket skips: line
  affects:
    - src/mcp_test_framework/_runner.py

tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN with io.StringIO capture for renderer unit tests
    - Gated digest line (omit when feature unused) to avoid noise

key_files:
  created:
    - tests/framework/test_explain_buckets.py
    - tests/framework/test_pre_run_digest_buckets.py
  modified:
    - src/mcp_test_framework/_runner.py

decisions:
  - "Extend existing per-tool block in _render_skipped_tools_explain rather than adding parallel structure per CONTEXT.md D-3"
  - "_count_bucket_skips helper follows _compose_judges_from_tool_configs shape — pure function, getattr-safe"
  - "Bucket skips: line position: between Skipping: and Judges: lines in digest"
  - "explain=True omits (use --explain to list) hint on Bucket skips: line, matching Skipping: behavior"

metrics:
  duration: ~15 minutes
  completed: "2026-05-26"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 33 Plan 04: --explain bucket extension + digest Bucket skips: line Summary

Per-bucket skip granularity surfaced in `--explain` output and pre-run digest via two renderer extensions to `_runner.py`.

## What Was Built

**Task 1: `_render_skipped_tools_explain` extension (BUCKET-04 / SC#3 part 1)**

Extended the existing `--explain` per-tool block renderer with a new Section 2 for bucket-level skips on running tools. The new section:

- Emits `Bucket-skipped tools (M):` header only when M > 0
- Lists each affected tool with `  <tool>:` then indented `    bucket=<name>: skipped via tools.<tool>.skip_buckets`
- Is completely absent when no tool has non-empty `skip_buckets` (byte-identical to v1.5 baseline)
- Is grep-able by the literal `bucket=` substring (CONTEXT.md D-3 locked grep anchor)
- Also defensively renders bucket lines under whole-tool-skipped tools that carry `skip_buckets` (load-time-rejected by Pydantic but rendered for traceability)

**Task 2: `_count_bucket_skips` + `_render_pre_run_digest` extension (BUCKET-04 / SC#3 part 2)**

Added `_count_bucket_skips()` helper and inserted a gated `Bucket skips:` line in the pre-run digest:

- New `_count_bucket_skips(tools_config)` returns total `(tool, bucket)` pair count across all tools
- Digest inserts `Bucket skips:{N:>3}  (use --explain to list)` between `Skipping:` and `Judges:` lines
- Line is entirely omitted when N == 0 (T-33-12 mitigation: no noise for operators not using the feature)
- `explain=True` omits the `(use --explain to list)` hint, matching the existing `Skipping:` behavior

## Commits

| Hash | Message |
|------|---------|
| 9e17b0e | test(33-04): add failing tests for --explain bucket= lines (RED) |
| a81af1f | feat(33-04): extend _render_skipped_tools_explain with per-bucket lines (GREEN) |
| e56e0f1 | test(33-04): add failing tests for digest per-bucket skip count (RED) |
| d8cec09 | feat(33-04): add _count_bucket_skips helper and Bucket skips: line to digest (GREEN) |

## Test Results

- 8 new self-tests all green:
  - `tests/framework/test_explain_buckets.py` (4 tests)
  - `tests/framework/test_pre_run_digest_buckets.py` (4 tests)
- 718 total framework tests pass (zero regressions)
- Existing digest tests: 42 selected, 42 passed

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. All changes are pure formatting output paths.

## TDD Gate Compliance

Both tasks followed RED/GREEN order:
1. Task 1: `test(33-04)` RED commit (9e17b0e) -> `feat(33-04)` GREEN commit (a81af1f)
2. Task 2: `test(33-04)` RED commit (e56e0f1) -> `feat(33-04)` GREEN commit (d8cec09)

## Self-Check: PASSED

Files exist:
- FOUND: src/mcp_test_framework/_runner.py (modified)
- FOUND: tests/framework/test_explain_buckets.py (created)
- FOUND: tests/framework/test_pre_run_digest_buckets.py (created)

Commits exist:
- FOUND: 9e17b0e test(33-04): add failing tests for --explain bucket= lines (RED)
- FOUND: a81af1f feat(33-04): extend _render_skipped_tools_explain with per-bucket lines (GREEN)
- FOUND: e56e0f1 test(33-04): add failing tests for digest per-bucket skip count (RED)
- FOUND: d8cec09 feat(33-04): add _count_bucket_skips helper and Bucket skips: line to digest (GREEN)
