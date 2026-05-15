---
phase: 20-preflight-conditional-skip
plan: 01
subsystem: planning-docs
tags:
  - requirements-scrub
  - phase-20
  - reframe
dependency_graph:
  requires:
    - 20-CONTEXT.md D-11 (drop PREFLIGHT-01/02)
    - 20-CONTEXT.md D-12 (add CLEANUP/CODEGEN-COVERAGE/REQ-SCRUB)
  provides:
    - CLEANUP-DOGFOOD-01 requirement ID (referenceable from downstream Phase 20 plans)
    - CODEGEN-COVERAGE-01 requirement ID
    - REQ-SCRUB-01 requirement ID
  affects:
    - downstream Phase 20 plans whose frontmatter cite the three new IDs
    - Phase coverage summary table (Phase 20 row count 2 -> 3)
tech_stack:
  added: []
  patterns: []
key_files:
  modified:
    - .planning/REQUIREMENTS.md
  created: []
decisions:
  - id: D-PLAN-20-01-01
    summary: Reworded REQ-SCRUB-01 description to avoid literal "PREFLIGHT-01"/"PREFLIGHT-02" tokens
    rationale: Plan's strict acceptance criterion `grep -c 'PREFLIGHT-0[12]' == 0` conflicted with the literal text the plan dictated for REQ-SCRUB-01's description ("PREFLIGHT-01 and PREFLIGHT-02 removed from REQUIREMENTS.md"). Resolved by rewording the description to refer to "the two prior Phase 20 preflight requirements (`requires_homelab(...)` marker factory + reachability checks)" — preserves meaning, satisfies the grep invariant, keeps `must_haves.truths` "REQUIREMENTS.md no longer contains PREFLIGHT-01 or PREFLIGHT-02 rows" satisfied.
metrics:
  duration_minutes: ~6
  completed: 2026-05-14
---

# Phase 20 Plan 01: Requirements Scrub Summary

**One-liner:** PREFLIGHT-01/02 removed from `.planning/REQUIREMENTS.md`; replaced with three new Phase 20 requirement IDs (CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01) describing what Phase 20 actually delivers; Traceability Table and Phase coverage summary updated consistently (21 → 22 total).

## What Changed

Single coordinated edit pass over `.planning/REQUIREMENTS.md`, made in one task to avoid partial states:

1. **Requirement Groups section** — The `### PREFLIGHT — Conditional execution and environment checks` heading + its 2-row table was replaced by `### CLEANUP — v1.3 retroactive scope correction (Phase 20)` + a 3-row table introducing `CLEANUP-DOGFOOD-01`, `CODEGEN-COVERAGE-01`, and `REQ-SCRUB-01`. The new heading sits in the same position (between STATE and UI groups).

2. **Traceability Table** — Two rows deleted (`PREFLIGHT-01`, `PREFLIGHT-02`). Three rows inserted immediately after `STATE-04` (Phase 19 cluster ends, Phase 20 cluster begins, UI-01 row preserved next). All three new rows carry `Phase 20 | Pending`. Totals line bumped: `21 requirements ... 21/21 (100%)` → `22 requirements ... 22/22 (100%)`.

3. **Phase coverage summary table** — Phase 20 row text changed from `PREFLIGHT-01, PREFLIGHT-02 | 2` to `CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01 | 3`. No other rows touched.

## Verification

All `<verify>` automated checks PASS:

| Check                                 | Result |
| ------------------------------------- | ------ |
| no PREFLIGHT-01 anywhere in file      | OK     |
| no PREFLIGHT-02 anywhere in file      | OK     |
| has CLEANUP section heading           | OK     |
| has CLEANUP-DOGFOOD-01 (3 occurrences) | OK     |
| has CODEGEN-COVERAGE-01 (3 occurrences) | OK    |
| has REQ-SCRUB-01 (3 occurrences)      | OK     |
| Total: 22 requirements                | OK     |
| no Total: 21 requirements             | OK     |
| Phase 20 row has all 3 IDs            | OK     |

Each new ID appears in exactly the three expected locations: (a) the group definition row, (b) its Traceability Table row, (c) the Phase coverage summary cell. No structural damage to unrelated requirement groups (SDET, CODEGEN, STATE, UI, DOC-SDET unchanged in this edit).

## Tasks Completed

| Task | Name                                                                                             | Commit  | Files                       |
| ---- | ------------------------------------------------------------------------------------------------ | ------- | --------------------------- |
| 1    | Replace PREFLIGHT requirement group with new CLEANUP/CODEGEN-COVERAGE/REQ-SCRUB rows + table sync | 7dbb97f | .planning/REQUIREMENTS.md   |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reworded REQ-SCRUB-01 description to satisfy strict acceptance criterion**

- **Found during:** Task 1 verify step.
- **Issue:** The plan's prescribed REQ-SCRUB-01 description ("PREFLIGHT-01 and PREFLIGHT-02 removed from REQUIREMENTS.md; ...") literally contains the tokens `PREFLIGHT-01` and `PREFLIGHT-02`. This contradicts the plan's own acceptance criterion `grep -c 'PREFLIGHT-0[12]' .planning/REQUIREMENTS.md returns 0` and the verify-step PowerShell regex which also requires zero matches anywhere in the file.
- **Resolution:** Rewrote the REQ-SCRUB-01 description to refer to "the two prior Phase 20 preflight requirements (`requires_homelab(...)` marker factory + reachability checks)" — semantically identical (the new wording still describes the scrub action accurately and unambiguously) but doesn't contain the literal `PREFLIGHT-01` / `PREFLIGHT-02` tokens. The `<must_haves>.truths` invariant ("REQUIREMENTS.md no longer contains PREFLIGHT-01 or PREFLIGHT-02 rows") remains satisfied — there are no rows for those IDs.
- **Files modified:** `.planning/REQUIREMENTS.md` (single line in the CLEANUP table — REQ-SCRUB-01 description column)
- **Commit:** 7dbb97f (this deviation is folded into the single task commit; rewording happened mid-task during verify-loop)

No other deviations. No authentication gates. No architectural decisions.

## Threat Flags

None. This plan modifies only planning-document text in `.planning/REQUIREMENTS.md`; no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## Known Stubs

None. No code shipped (zero `src/` changes, zero new tests). Plan delivers planning-doc edits only.

## Self-Check: PASSED

- File `.planning/REQUIREMENTS.md` exists: FOUND
- Commit `7dbb97f` exists in worktree branch: FOUND
- All `<verify>` automated checks: 9/9 OK
- All `<acceptance_criteria>` invariants pass:
  - `PREFLIGHT-0[12]` occurrences: 0
  - `### CLEANUP` heading count: 1
  - `CLEANUP-DOGFOOD-01` count: 3
  - `CODEGEN-COVERAGE-01` count: 3
  - `REQ-SCRUB-01` count: 3
  - `Total: 22 requirements` count: 1
  - `Total: 21 requirements` count: 0
  - Phase 20 row in summary table: lists all three new IDs with count 3
