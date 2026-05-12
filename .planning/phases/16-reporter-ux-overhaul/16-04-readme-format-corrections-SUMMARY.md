---
phase: 16-reporter-ux-overhaul
plan: 04
subsystem: docs
tags: [docs, gap-closure, readme, reporter, verification]
gap_closure: true
requirements:
  - UX-01
  - UX-05
dependency-graph:
  requires:
    - "16-01 (renderer baseline shipped)"
    - "16-02 (--explain CLI wiring shipped)"
    - "16-03 (initial documentation refresh)"
  provides:
    - "README documentation that mirrors _render_summary_line and _render_per_tool_rows output char-for-char"
  affects:
    - README.md
tech-stack:
  added: []
  patterns:
    - "docs-as-mirror: README sample blocks quote renderer output verbatim, including whitespace quirks (double space before 'in') and conditional segments ([/ S SKIP])"
key-files:
  created: []
  modified:
    - README.md
decisions:
  - "Mirror renderer output literally — no creative rewording of Result: line shape or per-tool row layout."
  - "Leave the --explain block placeholder unchanged: VERIFICATION.md's reference to 'lines 109-110' was a verifier counting error against digest rows, not per-tool rows."
  - "Reword adjacent prose ('skipped field' -> 'SKIP segment', '560 skipped cases' -> '560 SKIP cases') so terminology in narrative matches the renderer's verb shape."
metrics:
  duration: "~5 minutes"
  completed: "2026-05-12T15:21:43Z"
  tasks: 2
  files_modified: 1
  commits: 2
---

# Phase 16 Plan 04: README Format Corrections Summary

Closed both `16-VERIFICATION.md` documentation-drift gaps by rewriting six README locations to mirror `_runner.py`'s renderer output char-for-char — pure docs fix, no code or tests touched.

## Objective

Phase 16 Plan 03 invented `Result:` summary-line and per-tool row shapes for README's sample output blocks without reading the renderer. `gsd-verifier` caught two gaps:

- **CR-01 BLOCKER (Gap 1):** Documented `Result: N passed, M failed, S skipped` vs. actual `Result: N PASS / M FAIL [/ S SKIP]  in T.Ts`.
- **IN-02 WARNING (Gap 2):** Per-tool row examples rendered flush-left vs. actual section-header (`passing:`) + 2-space-indented rows.

This plan rewrites the affected README sections to mirror what `_render_summary_line` (`_runner.py:898`) and `_render_per_tool_rows` (`_runner.py:843-870`) actually emit.

## Tasks Completed

### Task 1: Fix `Result:` summary line in three README locations

**Commit:** `b1bc5dc`

Four surgical replacements:

1. **README.md line 84 (default sample output block):**
   - Before: `Result: 20 passed, 0 failed, 560 skipped`
   - After:  `Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s`

2. **README.md line 92 (`-q` / `--quiet` table row):**
   - Before: `Emits only the final `Result: N passed, M failed, S skipped` line.`
   - After:  `Emits only the final `Result: N PASS / M FAIL [/ S SKIP]  in T.Ts` line (the `SKIP` segment is omitted entirely when zero skips; double space before `in` is literal).`

3. **README.md line 228 (Sample green run block):**
   - Before: `Result: 20 passed, 0 failed, 560 skipped`
   - After:  `Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s`

4. **README.md line 240-241 (adjacent prose):**
   - Before: `their counts roll into the `Result:` line's `skipped` field at the parametrized-case level (56 tools × 10 cases = 560 skipped cases).`
   - After:  `their counts roll into the `Result:` line's `SKIP` segment at the parametrized-case level (56 tools × 10 cases = 560 SKIP cases).`

### Task 2: Add `passing:` section headers + 2-space indent to per-tool row examples

**Commit:** `ef4c884`

Two surgical replacements:

1. **README.md lines 81-82 (default sample output block):**
   - Before:
     ```
     list_keyring_credentials  ✓ PASS
     suggest_deployments       ✓ PASS
     ```
   - After:
     ```
     passing:
       list_keyring_credentials  ✓ PASS
       suggest_deployments       ✓ PASS
     ```

2. **README.md lines 225-226 (Sample green run block):**
   - Before:
     ```
     list_keyring_credentials  ✓ PASS
     suggest_deployments       ✓ PASS
     ```
   - After:
     ```
     passing:
       list_keyring_credentials  ✓ PASS
       suggest_deployments       ✓ PASS
     ```

The `--explain` example block (README.md lines 102-121) was deliberately left unchanged. VERIFICATION.md's reference to "lines 109-110" as per-tool rows was a verifier counting error — those lines contain `Running:` / `Skipping:` digest rows, not per-tool rows, and they are correctly rendered. The block's placeholder `(pytest subprocess runs here, then per-tool rows + Result: line)` at line 120 remains intact.

## Verification Gates

All 11 grep gates from the plan's `<verification>` section pass:

```
Gap 1 (CR-01 BLOCKER):
  Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s  -> 2  (expected 2)
  Result: N PASS / M FAIL [/ S SKIP]  in T.Ts   -> 1  (expected 1)
  Result: .* passed, .* failed                   -> 0  (expected 0)
  N passed, M failed, S skipped                  -> 0  (expected 0)
  560 skipped cases                              -> 0  (expected 0)
  560 SKIP cases                                 -> 1  (expected 1)

Gap 2 (IN-02 WARNING):
  ^passing:$                                     -> 2  (expected >= 2)
  ^  list_keyring_credentials  ✓ PASS$           -> 2  (expected 2)
  ^  suggest_deployments       ✓ PASS$           -> 2  (expected 2)
  ^list_keyring_credentials  ✓ PASS$             -> 0  (expected 0)
  ^suggest_deployments       ✓ PASS$             -> 0  (expected 0)

--explain placeholder untouched:
  (pytest subprocess runs here, then per-tool rows + Result: line)  -> 1  (expected 1)
```

`git diff --stat HEAD~2..HEAD` shows only `README.md` (11 insertions, 9 deletions). No source code, no tests, no other docs were touched.

## Deviations from Plan

None — plan executed exactly as written. Every replacement string in the plan's `<action>` block was applied verbatim, and every gate in the plan's `<verify>` block passed on first run.

## Authentication Gates

None.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- README.md exists and contains the corrected strings (verified via 11 grep gates above).
- Commit `b1bc5dc` exists in `git log` for Task 1.
- Commit `ef4c884` exists in `git log` for Task 2.
- `git diff --stat HEAD~2..HEAD` confirms only README.md was modified.
