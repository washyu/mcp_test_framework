---
phase: 24-tool-call-serializer-omits-unset-optional-params-exclude-uns
plan: 03
subsystem: planning

tags:
  - state-rescope
  - audit-trail
  - deferred-items
  - seed-022

requires:
  - phase: 24-tool-call-serializer-omits-unset-optional-params-exclude-uns
    provides: Plan 24-01 shipped exclude_unset=True at _tool_factory.py:99 (the framework-side resolution Row A is making a factual claim about)
provides:
  - STATE.md Deferred Items table audit trail records Phase 24's framework-side resolution as a distinct row (Row A, Resolved) while preserving the upstream homelab-mcp inputSchema bug residue as a separate open row (Row B) with original Phase 19 deferred-at date
  - Row A explicitly cites SEED-022 by name and references memory `project_framework_primitives_sdet_safety_principle.md` so the audit trail records why explicit-null-testing remains SDET-owned
affects:
  - v1.3-close-push
  - future deferred-items reviewers (Phase 25+)

tech-stack:
  added: []
  patterns:
    - "Resolved-by-explanation row split — adjacent rows (one Resolved, one Open) carry the bridge between framework-side fix and remaining upstream debt; mirrors the L179 Resolved-by-deletion precedent"

key-files:
  created:
    - .planning/phases/24-tool-call-serializer-omits-unset-optional-params-exclude-uns/24-03-SUMMARY.md
  modified:
    - .planning/STATE.md

key-decisions:
  - "Row A status uses literal `Resolved` (capital R, single-word, matches L179 `Resolved-by-deletion` precedent)"
  - "Row A `Deferred At` uses arrow notation `Phase 19 close (2026-05-13) → resolved Phase 24 (2026-05-15)` so both surfacing date and resolution event are recorded (mirrors L179 precedent)"
  - "Row B `Deferred At` preserves ONLY the original Phase 19 close surfacing date so the deferred-items timeline still reads correctly for the remaining upstream bug"
  - "Plan 24-02's live-uat row (README PASS-sample re-capture, keyring isolation) left untouched — different concern, different category"

patterns-established:
  - "Row split as audit-trail update pattern: when a deferred concern is partially resolved, split it into a Resolved row + a narrower-scope Open row rather than editing the existing row in place. Preserves the original surfacing date on the open residue."

requirements-completed:
  - SERIALIZER-01

duration: ~3min
completed: 2026-05-15
---

# Phase 24 Plan 03: STATE.md Deferred Items row split Summary

**Split STATE.md L155 `homelab-mcp inputSchema` Deferred Items row into Row A (Resolved, framework-side fix shipped Phase 24) + Row B (Open, narrower-scope upstream bug residue) so the audit trail records the partial resolution without erasing what remains.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-15 (post-Plan-24-02 completion)
- **Completed:** 2026-05-15
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- L157 (original L155-equivalent) `upstream-fix` row about `homelab-mcp` inputSchema replaced with two adjacent rows:
  - **Row A (L157, Resolved):** Framework default behavior contribution — `_tool_factory.py:99` `model_dump(mode='json')` emitted `null` for unset optional Pydantic fields. Resolution: `exclude_unset=True` shipped in Phase 24 (Plan 24-01). Resolution note cites SEED-022 by name and references memory `project_framework_primitives_sdet_safety_principle.md`.
  - **Row B (L158, Open):** Upstream homelab-mcp inputSchema bug itself — Proxmox tools declare optional fields as `type: 'string'` (no `'null'`) but default them to `null`. SDETs explicitly testing null-handling still trigger this. Server should declare `type: ['string','null']` or strip null-valued keys before its own jsonschema check.
- Row A's `Deferred At` cell uses the arrow notation `Phase 19 close (2026-05-13) → resolved Phase 24 (2026-05-15)` (mirrors the L179 `Resolved-by-deletion` precedent).
- Row B's `Deferred At` cell preserves only the original `Phase 19 close (2026-05-13)` surfacing date so the deferred-items timeline reads correctly for the remaining upstream debt.
- Plan 24-02's `live-uat` row (README PASS-sample re-capture / keyring isolation, added at Plan 24-02 close) preserved untouched — visible in grep at its original position downstream of the split.

## Before/After Line Numbers

| Item | Before | After |
|------|--------|-------|
| `homelab-mcp inputSchema` combined row | L157 (single row) | Removed |
| Row A (Resolved) — Framework default behavior contribution | (did not exist) | L157 |
| Row B (Open) — Upstream homelab-mcp inputSchema bug | (did not exist) | L158 |
| `testing-scaffold` row (Automated cross-platform SIGINT UAT) | L158 | L159 (+1) |
| All subsequent Deferred Items rows | shifted by +1 | confirmed no line-anchor cross-references downstream of L155 in canonical_refs |
| Plan 24-02 `live-uat` row (README PASS-sample) | last row | last row (still last; +1 from shift) |

(Note: the plan's `<read_first>` referenced "L155" from the pre-Plan-24-02 file state; after Plan 24-02 appended the `live-uat` row at the table tail and bumped the file's leading frontmatter slightly, the equivalent target row was at L157 at edit time. The grep-based acceptance criteria target row content, not line numbers, so this offset has no functional impact.)

## Task Commits

Each task was committed atomically:

1. **Task 1: Split STATE.md Deferred Items L155 row into Row A (Resolved) + Row B (Open)** — `ed1cdf7` (docs)

## Files Created/Modified

- `.planning/STATE.md` — Deferred Items table: one row (`upstream-fix`, homelab-mcp inputSchema) deleted, two rows inserted at the same position (Row A Resolved, Row B Open). No other section touched.

## git diff scope confirmation

```
$ git diff --stat .planning/STATE.md
 .planning/STATE.md | 3 ++-
 1 file changed, 2 insertions(+), 1 deletion(-)
```

Excerpt (only hunk in the diff — confirms no other STATE.md section touched):

```
@@ -154,7 +154,8 @@ Items acknowledged at v1.0 / v1.1 close and carried into v1.2+ scope:
 | Category | Item | Status | Deferred At |
 |----------|------|--------|-------------|
 | upstream-fix | `homelab-mcp` `list_registered_servers` description rewrite ... | Open | v1.0 close (2026-05-07) |
-| upstream-fix | `homelab-mcp` inputSchema for Proxmox tools ... Framework deliberately does NOT mask this with `exclude_none=True` (SEED-022 principle). | Open | Phase 19 close (2026-05-13) |
+| upstream-fix | Framework default behavior contribution to homelab-mcp inputSchema null trigger — `_tool_factory.py:99` ... see Row B and memory `project_framework_primitives_sdet_safety_principle.md`). | Resolved | Phase 19 close (2026-05-13) → resolved Phase 24 (2026-05-15) |
+| upstream-fix | Upstream homelab-mcp inputSchema bug — Proxmox tools (and likely others) declare optional fields as `type: 'string'` ... Server should declare `type: ['string','null']` or strip null-valued keys before its own jsonschema check. | Open | Phase 19 close (2026-05-13) |
 | testing-scaffold | Automated cross-platform SIGINT UAT ... | Open | v1.0 close (2026-05-07) |
```

(Truncated above for readability; the actual diff hunk is the only modification, +2/−1 lines.)

## Acceptance Criteria Verification

| Criterion | Expected | Actual | Pass |
|-----------|----------|--------|------|
| `grep -c "Framework default behavior contribution to homelab-mcp inputSchema null trigger" .planning/STATE.md` | 1 | 1 | ✓ |
| `grep -c "Upstream homelab-mcp inputSchema bug — Proxmox tools" .planning/STATE.md` | 1 | 1 | ✓ |
| `grep -c "Framework deliberately does NOT mask this with \`exclude_none=True\`" .planning/STATE.md` | 0 | 0 | ✓ |
| `grep -c "resolved Phase 24 (2026-05-15)" .planning/STATE.md` | ≥1 | 1 | ✓ |
| `grep -c "SEED-022" .planning/STATE.md` | ≥1 | 4 | ✓ |
| `grep -c "project_framework_primitives_sdet_safety_principle\.md" .planning/STATE.md` | ≥1 | 1 | ✓ |
| Row A and Row B adjacent (line-number difference of 1) | 1 | L157, L158 (diff=1) | ✓ |
| Plan 24-02 `live-uat` row preserved | present | present | ✓ |

## Decisions Made

None — followed plan as specified. All wording for Row A and Row B taken verbatim from the plan's action block (which itself derives from 24-CONTEXT.md D-06 / D-07).

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- Phase 24 plan set complete (24-01 + 24-02 + 24-03 all landed; 24-02 partial via regen-failed contract with manual UAT tracked as a `live-uat` deferred item).
- v1.3 close push now unblocked per memory `project_v1_3_close_push_and_scrub.md` once Phase 24 verification + close gates pass.

## Self-Check: PASSED

- `.planning/STATE.md` Row A text present (line 157)
- `.planning/STATE.md` Row B text present (line 158)
- Commit `ed1cdf7` confirmed in `git log`
- SUMMARY.md created at expected path
- Plan 24-02 `live-uat` row still present (verified via grep)

---
*Phase: 24-tool-call-serializer-omits-unset-optional-params-exclude-uns*
*Plan: 03*
*Completed: 2026-05-15*
