---
phase: 33-per-bucket-skip-granularity-in-toolconfig-999-1
plan: "05"
subsystem: docs
tags:
  - docs
  - bucket
  - BUCKET-05
  - skip_buckets
  - create_proxmox_vm

dependency_graph:
  requires:
    - 33-01  # ToolConfig.skip_buckets field
    - 33-02  # Pydantic validation + skip/skip_buckets redundancy rejection
    - 33-03  # per-bucket collection-time filter
    - 33-04  # --explain bucket= lines + pre-run digest Bucket skips: line
  provides:
    - README worked example for skip_buckets using create_proxmox_vm
    - docs/LIBRARY-MODE.md parity worked example (D-03)
    - test-bucket vs result-bucket disambiguation in both docs
  affects:
    - README.md
    - docs/LIBRARY-MODE.md

tech_stack:
  added: []
  patterns:
    - Operator-tone doc subsection with YAML + expected output blocks
    - D-03 parity: same example in both docs (byte-aligned YAML/output blocks)

key_files:
  created: []
  modified:
    - README.md
    - docs/LIBRARY-MODE.md

decisions:
  - "Insertion point in README: immediately after Block B (judges subset) and before the call_arguments note — closest existing per-tool knob documentation"
  - "Insertion point in LIBRARY-MODE.md: after injected test surface section and before Markers — explains per-tool bucket filtering adjacent to where per-tool test injection is documented"
  - "Opening paragraph in LIBRARY-MODE.md adjusted for library-mode voice (pytest-ini-first framing) while keeping YAML/output blocks verbatim identical to README"

metrics:
  duration: "~53 minutes"
  completed: "2026-05-26"
  tasks_completed: 2
  tasks_total: 2
  files_created: 0
  files_modified: 2
---

# Phase 33 Plan 05: Per-bucket skip documentation (BUCKET-05) Summary

**One-liner:** Worked example for `skip_buckets: ["output"]` on `create_proxmox_vm` added to README and docs/LIBRARY-MODE.md, with YAML config + `--explain` output slice + pre-run digest slice and explicit test-bucket vs result-bucket disambiguation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add worked example to README.md | 05649ba | README.md |
| 2 | Add the SAME worked example to docs/LIBRARY-MODE.md | 2bef649 | docs/LIBRARY-MODE.md |

## What Was Built

### Task 1: README.md

New subsection `### Skipping individual test buckets per tool` added immediately after `### Block B: judges subset` in the "Per-tool configuration" section. The subsection contains:

1. Rationale paragraph naming the problem (required-field tools), the feature (`skip_buckets`), valid bucket names (`schema`, `judge`, `output`), and the test-bucket vs result-bucket disambiguation.
2. YAML code block: `tools.create_proxmox_vm.skip_buckets: ["output"]`
3. Expected `--explain` output block with the locked grep-anchor: `bucket=output: skipped via tools.create_proxmox_vm.skip_buckets`
4. Pre-run digest slice with `Bucket skips:  1  (use --explain to list)`
5. Closing sentence: output-bucket tests absent from `--collect-only`; `skip: true` + `skip_buckets` rejected at config load.

Total subsection: 45 lines.

### Task 2: docs/LIBRARY-MODE.md

Same subsection `### Skipping individual test buckets per tool` added after the injected test surface block and before the `## Markers` section. Adjustments from README:

- Opening paragraph rephrased for library-mode / pytest-ini-first voice: leads with "Same `tools.<name>.skip_buckets` field as the CLI surface — works identically in library mode."
- YAML block, `--explain` block, pre-run digest block, closing sentence: verbatim identical to README (D-03 parity).

Total subsection: 44 lines.

## Verification Results

All plan-level acceptance criteria passed:

```
grep -c "bucket=output: skipped via tools.create_proxmox_vm.skip_buckets" README.md docs/LIBRARY-MODE.md
README.md:1
docs/LIBRARY-MODE.md:1

grep -c "create_proxmox_vm" README.md docs/LIBRARY-MODE.md
README.md:8
docs/LIBRARY-MODE.md:6

grep -c "skip_buckets" README.md docs/LIBRARY-MODE.md
README.md:4
docs/LIBRARY-MODE.md:4

grep -c "Bucket-skipped tools (1):" README.md docs/LIBRARY-MODE.md
README.md:1
docs/LIBRARY-MODE.md:1

uv run pytest tests/framework/ -x --ignore=tests/framework/smoke --ignore=tests/framework/parity -q
727 passed, 1 skipped, 12 deselected, 1 xfailed in 90.73s
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Both doc sections reference the real implementation fields (`skip_buckets` in `ToolConfig`, `--explain` output path in `_runner.py`, digest line in `_render_pre_run_digest`) shipped in Waves 1-2 of this phase.

## Threat Flags

None. Documentation contains only non-secret tool names and expected CLI output. No new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

Files exist and were modified:
- FOUND: README.md (modified, +45 lines) ✓
- FOUND: docs/LIBRARY-MODE.md (modified, +44 lines) ✓

Commits exist:
- FOUND: 05649ba — docs(33-05): add skip_buckets worked example to README.md ✓
- FOUND: 2bef649 — docs(33-05): add skip_buckets worked example to LIBRARY-MODE.md ✓

Framework tests green: 727 passed, no regressions ✓
