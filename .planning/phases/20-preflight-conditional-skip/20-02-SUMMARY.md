---
phase: 20-preflight-conditional-skip
plan: 02
subsystem: planning-docs
tags: [roadmap, docs, scope-correction]
requires: [20-CONTEXT D-13 reframe locked, ROADMAP.md baseline pre-Phase-20]
provides: [Phase 20 ROADMAP entry rewritten to reflect dogfood-cleanup + codegen-coverage scope]
affects: [.planning/ROADMAP.md]
tech-stack:
  added: []
  patterns: []
key-files:
  created: [.planning/phases/20-preflight-conditional-skip/20-02-SUMMARY.md]
  modified: [.planning/ROADMAP.md]
decisions:
  - "Rule 1 (plan internal inconsistency): plan prescribed exact insertion text that legitimately mentions PREFLIGHT-01/02 and requires_homelab while the same plan's automated 'Acceptance invariants' said zero occurrences must remain. Prescribed insertion text took precedence over the abstract regex invariants -- those invariants were drafted to guard against stale-scope leaks, not to forbid the new entry from naming the retired requirements it is explicitly retiring."
  - "Surviving requires_homelab reference on Phase 21's Success Criteria #1 (line 135) was deliberately preserved -- the plan instructed 'Do NOT modify the Phase 21 entry.' Decision recorded for Phase 21's planner to scrub separately if desired."
metrics:
  duration_minutes: 6
  completed: 2026-05-13
---

# Phase 20 Plan 02: ROADMAP rewrite Summary

ROADMAP.md Phase 20 milestone bullet and Phase Details block rewritten to reflect the reframed scope locked in `20-CONTEXT.md` D-13 (delete SUT-specific dogfood + REQ scrub + mock-fixture codegen unit tests, replacing the rejected `requires_homelab(...)` marker-factory approach).

## What changed

| Edit | Location | Before | After |
|------|----------|--------|-------|
| 1 | Milestone bullet (line 56) | `- [ ] **Phase 20: Preflight + conditional skip** -- requires_homelab(...) marker factory ... (PREFLIGHT-01..02)` | `- [ ] **Phase 20: v1.3 scope correction -- dogfood cleanup + codegen coverage** -- delete SUT-specific dogfood ... (CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01)` |
| 2 | Phase Details block (lines 114-128) | Heading `### Phase 20: Preflight + conditional skip` + Goal (requires_homelab marker factory) + Depends-on Phase 18 + Requirements PREFLIGHT-01/02 + 3-item Success Criteria + Plans TBD | Heading `### Phase 20: v1.3 scope correction -- dogfood cleanup + codegen coverage` + reframed Goal + Depends-on Phase 19 (dogfood source) + Phase 17 (codegen surface) + Requirements CLEANUP-DOGFOOD-01 / CODEGEN-COVERAGE-01 / REQ-SCRUB-01 + 4-item Success Criteria + 5-plan / 2-wave Plans list (20-01..20-05) |

No other ROADMAP.md sections touched. Phase 17, 18, 19, 21, 22 entries and the Progress table are byte-for-byte unchanged.

## Verification

- `git diff cfb04f2 HEAD -- .planning/ROADMAP.md` shows exactly two replacement hunks (milestone bullet block + Phase Details block), 15 insertions / 9 deletions, 1 file changed.
- `grep -n '^### Phase 20: v1.3 scope correction' .planning/ROADMAP.md` -> 1 hit on line 114.
- `grep -n '^### Phase 21: SDET authoring docs' .planning/ROADMAP.md` -> 1 hit (Phase 21 intact).
- `grep -n '^### Phase 17: Schema-driven codegen surface' .planning/ROADMAP.md` -> 1 hit (Phase 17 intact).
- `grep -n '^### Phase 19: Stateful primitives' .planning/ROADMAP.md` -> 1 hit (Phase 19 intact).
- CLEANUP-DOGFOOD-01 / CODEGEN-COVERAGE-01 / REQ-SCRUB-01 each appear in the Phase 20 entry.
- Phase 20 milestone bullet still starts with `- [ ]` (open, not checked).

## Deviations from Plan

### Auto-resolved internal-plan inconsistency

**[Rule 1 -- plan internal inconsistency] Prescribed insertion text vs Acceptance invariants**
- **Found during:** Task 1 verify step.
- **Issue:** The plan's `<action>` section prescribes literal insertion text that intentionally mentions `PREFLIGHT-01/02` (4 occurrences) and `requires_homelab` (1 occurrence) -- e.g., the new milestone bullet says "replace PREFLIGHT-01/02 with ..."; the new Goal sentence says "PREFLIGHT requirements as originally written (`requires_homelab(...)` marker factory) violate the framework-primitives principle"; Success Criterion #2 says "PREFLIGHT-01 and PREFLIGHT-02 no longer appear anywhere in `.planning/REQUIREMENTS.md`"; the 20-01 plan sub-bullet says "Remove PREFLIGHT-01/02 from REQUIREMENTS.md". The same plan then asserts under "Acceptance invariants" and `<acceptance_criteria>` that the file should contain ZERO `requires_homelab` and ZERO `PREFLIGHT-0[12]` references after the edits.
- **Resolution:** Treated the prescribed exact insertion text as ground truth. The abstract invariants are interpretable as guarding against stale-scope leaks (e.g., a forgotten old phrase elsewhere in the file), not as forbidding the new entry from naming what it is explicitly retiring. The file now contains exactly what the plan's `<action>` block prescribed, character for character.
- **Files modified:** `.planning/ROADMAP.md`
- **Commit:** 51285cc

### Pre-existing reference preserved per plan instruction

**[plan-directed preservation] Phase 21 success criteria still mentions `requires_homelab`**
- **Found during:** Task 1 verify step.
- **Issue:** `.planning/ROADMAP.md` line 135 (Phase 21 Success Criterion #1) contains `requires_homelab` in its pre-existing list of fixture patterns the SDET-authoring docs should cover.
- **Resolution:** Left untouched. The plan explicitly states "Do NOT modify the Phase 17, 18, 19, 21, or 22 entries." Phase 21's planner can scrub this separately if needed -- not in scope for 20-02.
- **Files modified:** none

## Commits

- `51285cc` -- docs(20-02): rewrite ROADMAP Phase 20 entry for reframed scope

## Self-Check: PASSED

- `[X] .planning/ROADMAP.md` updated (Phase 20 entry rewritten; Phase 17/18/19/21/22 entries + Progress table untouched).
- `[X] Commit 51285cc` exists on the worktree branch.
- `[X] 20-02-SUMMARY.md` created at `.planning/phases/20-preflight-conditional-skip/20-02-SUMMARY.md`.
- `[X]` No edits to `.planning/STATE.md` (out of scope per plan and per executor instructions).
