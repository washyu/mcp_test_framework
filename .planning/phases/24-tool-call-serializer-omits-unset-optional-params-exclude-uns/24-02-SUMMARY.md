---
phase: 24-tool-call-serializer-omits-unset-optional-params-exclude-uns
plan: 02
subsystem: sdet
tags: [docs, readme-parity, sdet-authoring, seed-022, serializer-doc, partial-completion]
verify_status: partial

# Dependency graph
requires:
  - phase: 24-tool-call-serializer-omits-unset-optional-params-exclude-uns
    plan: 01
    provides: live `exclude_unset=True` serializer behavior (the post-fix reality the docs must describe)
  - phase: 21-sdet-authoring-docs-readme-parity
    provides: README §`## SDET scenarios` sample block + post-snapshot framing paragraph + SDET-AUTHORING.md §`## The inputSchema workaround` section + Phase 21 D-06 SEED-022 lock-in
provides:
  - softened `docs/SDET-AUTHORING.md` §`## The inputSchema workaround` framing (default-path no longer trips bug; `_CpuBumpManageVmParams(extra='allow')` is the explicit-null-test escape hatch only)
  - SERIALIZER-DOC-01 requirement row + traceability + Phase 24 coverage row updates
  - documented partial-completion via regen-failed contract (live README re-capture deferred to manual UAT)
affects: [phase-24-close, v1.3-close-push, README §SDET-scenarios sample]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Plan partial-completion via `regen-failed` operator-checkpoint branch + Deferred Items row in STATE.md (24-02-PLAN.md L429-L447 contract)"
    - "Doc-framing soften without removing SEED-022 teaching content (Phase 21 D-06 lock honored)"

key-files:
  created: []
  modified:
    - ".planning/REQUIREMENTS.md — SERIALIZER-DOC-01 row added to SERIALIZER group; traceability + phase-24 coverage rows updated; rollup 28→29 reqs across 8 phases"
    - "docs/SDET-AUTHORING.md — §`## The inputSchema workaround` framing softened; `_CpuBumpManageVmParams(extra='allow')` code block + SEED-022 teaching preserved verbatim per Phase 21 D-06"
    - ".planning/STATE.md — Current Position updated to `24-02 partial`; live-uat Deferred Items row appended; frontmatter last_updated/last_activity + Session Continuity refreshed"
  intentionally_unmodified:
    - "README.md — pre-Plan-24-02 state preserved per regen-failed contract step 2; live PASS-sample re-capture deferred to manual UAT"
    - "tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py — already tracked from Phase 21.1; not resurrected/touched in this plan branch"

key-decisions:
  - "D-1 (operator, 2026-05-15): regen-failed branch invoked after Task 3a/3b retry — Proxmox credential keyring unreachable from agent shell. Operator verbatim: 'The credentials should have already been added i think the isolation is blocking access to the keyring so i don't think we can fix this without a manual UAT'"
  - "D-2: Phase 24 closes with the partial — Plan 24-02 reaches terminal state on the regen-failed branch (Tasks 1+2 committed; Tasks 3a/3b deferred to manual UAT). Plan marked complete in ROADMAP.md with `verify_status: partial` cross-referenced in STATE.md Deferred Items."
  - "D-3: SEED-022 invariant preserved — Task 2's SDET-AUTHORING soften kept the `_CpuBumpManageVmParams(extra='allow')` code block + the 'framework doesn't paper over upstream bugs' teaching per Phase 21 D-06."

patterns-established:
  - "regen-failed partial-completion contract — plan exits successfully with documented gap when a live-stack human-verify checkpoint cannot be exercised in the executing environment (here: agent shell isolation from the OS keyring)"

requirements-completed: [SERIALIZER-DOC-01]

# Metrics
duration: ~30min (Tasks 1+2 + Tasks 3a/3b retries + partial-completion recovery)
completed: 2026-05-15
---

# Phase 24 Plan 02: SDET-AUTHORING soften + SERIALIZER-DOC-01 (partial — README re-capture deferred)

**`docs/SDET-AUTHORING.md` §`## The inputSchema workaround` framing softened (the `_CpuBumpManageVmParams(extra='allow')` pattern is now documented as the explicit-null-test escape hatch only, not the always-needed default for Proxmox calls); SERIALIZER-DOC-01 row added to REQUIREMENTS.md. The README §`## SDET scenarios` PASS-sample re-capture (Tasks 3a/3b) is deferred to a manual UAT via the plan's `regen-failed` partial-completion contract — Proxmox keyring credentials are unreachable from the agent shell that runs under this executor.**

## Performance

- **Duration:** ~30 min (Tasks 1+2 + Tasks 3a/3b retry attempts + recovery sequence)
- **Started:** 2026-05-15 (Task 1 commit `520b3a8`)
- **Completed:** 2026-05-15 (partial-completion recovery commit; SUMMARY.md commit to follow)
- **Tasks:** 4 (2 complete, 2 deferred via regen-failed contract)
- **Files modified:** 3 (1 requirement doc, 1 SDET doc, 1 state doc)
- **Files intentionally unmodified:** 2 (README.md, tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py)

## Task-by-Task Results

### Task 1: Add SERIALIZER-DOC-01 requirement row to REQUIREMENTS.md — COMPLETE

- **Commit:** `520b3a8` (`docs(24-02): add SERIALIZER-DOC-01 requirement row`)
- **Acceptance criteria:** all met
  - `grep -c "^| SERIALIZER-DOC-01" .planning/REQUIREMENTS.md` = `2` (group + traceability)
  - Coverage rollup updated: `Total: 29 requirements mapped across 8 phases (17–24)`
  - Phase 24 coverage row reads `SERIALIZER-01, SERIALIZER-DOC-01` (2 reqs)
- **Files modified:** `.planning/REQUIREMENTS.md`

### Task 2: Soften docs/SDET-AUTHORING.md §`## The inputSchema workaround` framing — COMPLETE

- **Commit:** `250a59d` (`docs(24-02): soften inputSchema workaround framing in SDET-AUTHORING`)
- **Acceptance criteria:** all met
  - `_CpuBumpManageVmParams(extra='allow')` code block preserved (SEED-022 teaching intact)
  - `project_framework_primitives_sdet_safety_principle.md` reference preserved
  - Framing shift landed: pattern is now positioned as the explicit-null-test escape hatch, not the default-Proxmox-call requirement
  - Phase 21 D-06 lock honored — no SEED-022 teaching content removed
- **Files modified:** `docs/SDET-AUTHORING.md`

### Task 3a: Capture live PASS run of the sample scenario — DEFERRED (regen-failed)

- **Status:** Deferred to manual UAT via plan's regen-failed partial-completion contract (24-02-PLAN.md L429-L447).
- **Reason:** Proxmox credentials registered in the operator's OS keyring are unreachable from the agent's PowerShell session even after `MCPTF_DOGFOOD_PROXMOX_HOST=192.168.10.20` is exported. homelab-mcp reports `No Proxmox credentials found for 192.168.10.20`. Two attempts confirmed the failure mode is environmental, not a fixable in-loop blocker.
- **Operator decision (verbatim, 2026-05-15):** "The credentials should have already been added i think the isolation is blocking access to the keyring so i don't think we can fix this without a manual UAT"
- **Cross-reference:** New `live-uat` row in STATE.md Deferred Items (added in recovery commit) — see "Deferred Items" section below.

### Task 3b: Paste captured PASS output into README.md + rewrite intro/framing paragraphs — DEFERRED (regen-failed)

- **Status:** Deferred to manual UAT — depends on Task 3a output.
- **README.md state:** untouched from pre-Plan-24-02 (`git diff HEAD -- README.md` empty). Intro paragraph (L266-L272) and post-snapshot framing paragraph (L420-L427) remain in their pre-Phase-24 form (still describe the snapshot as "shown here mid-failure" and the `✗` rows as "the framework doing its job"). This is a documented gap, not a partial edit.
- **Sample test file state:** `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py` untouched at HEAD (already tracked from Phase 21.1; was never resurrected/edited in this plan branch).
- **Temp capture file:** `.planning/phases/24-.../24-02-readme-capture.txt` deleted in recovery sequence (was an untracked artifact from the failed Task 3a attempt).
- **Cross-reference:** same STATE.md Deferred Items row as Task 3a.

### Task 4: Human-verify checkpoint — RESOLVED via `regen-failed` branch

- **Resume signal received:** `regen-failed: keyring isolation`
- **Recovery sequence executed (per 24-02-PLAN.md L429-L447):**
  1. Tasks 1+2 stay committed (`520b3a8`, `250a59d`) — confirmed via `git log --oneline -5`
  2. README.md confirmed in pre-Plan-24-02 state — `git diff HEAD -- README.md` empty
  3. Sample test file confirmed untouched — `git diff HEAD -- tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py` empty
  4. Untracked temp capture file deleted: `.planning/phases/24-.../24-02-readme-capture.txt`
  5. STATE.md Deferred Items row appended (`live-uat` category)
  6. STATE.md frontmatter + Current Position + Session Continuity updated to reflect `24-02 partial`
  7. Recovery commit landed (STATE.md only)
  8. This SUMMARY.md written with `verify_status: partial`

## Deviations from Plan

### Deferred via plan-defined regen-failed contract

**1. [Plan-defined contract] Tasks 3a/3b deferred to manual UAT — keyring isolation**

- **Found during:** Task 3a execution (second attempt) by prior continuation agent
- **Issue:** Agent shell cannot reach the operator's OS keyring where Proxmox credentials are registered. Setting `MCPTF_DOGFOOD_PROXMOX_HOST=192.168.10.20` is necessary but not sufficient — the keyring lookup inside homelab-mcp fails regardless.
- **Resolution:** Operator invoked the plan's `regen-failed` partial-completion contract. This is NOT a Rule 1/2/3 deviation — the plan explicitly defined a partial-completion path for exactly this scenario (live-stack reachability outside Claude's control).
- **Files unchanged as a result:** `README.md`, `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py`
- **Tracking:** New `live-uat` row in `.planning/STATE.md` Deferred Items table; carries forward to next phase close-out review.

### No auto-fix deviations (Rules 1-3)

Tasks 1+2 executed exactly as written. No bugs, missing functionality, or blocking issues were discovered in the doc/requirements edits.

## Deferred Items (cross-reference)

The recovery sequence appended this row to `.planning/STATE.md` §`## Deferred Items`:

```
| live-uat | README §`## SDET scenarios` PASS-sample re-capture (Plan 24-02 Task 3a/3b) — Proxmox credential keyring is not reachable from the agent's PowerShell session even after `MCPTF_DOGFOOD_PROXMOX_HOST=192.168.10.20` is set; homelab-mcp reports `No Proxmox credentials found for 192.168.10.20`. The README §`## SDET scenarios` snapshot still shows the pre-Phase-24 FAIL output even though the framework default no longer triggers it; intro paragraph (L266-L272) and post-snapshot framing paragraph (L420-L427) remain in their pre-Plan-24-02 state. Tasks 1+2 of Plan 24-02 committed (SERIALIZER-DOC-01 row + SDET-AUTHORING soften). Re-snapshot manually when running in an operator shell that has keyring access — see Phase 21 D-14 manual-snapshot precedent. | Open — manual UAT | Phase 24 Plan 24-02 close (2026-05-15) |
```

Re-capture pre-conditions for a future operator-shell run:
- Operator shell with OS-keyring access (PowerShell session running as the operator, not under an agent harness)
- `MCPTF_DOGFOOD_PROXMOX_HOST=<host>` exported
- homelab-mcp on PATH with Proxmox credentials pre-registered in the keyring
- `uv run mcp-test-framework run --sdet -k proxmox_vm_lifecycle_readme_sample`
- Output expected to show `Result: <N> PASS / 0 FAIL / <K> SKIP` with N >= 2
- Paste verbatim into README.md §`## SDET scenarios`; rewrite intro paragraph (L266-L272) and post-snapshot framing paragraph (L420-L427) per Task 3b plan steps

## Acceptance Criteria Status

### Task 1 (SERIALIZER-DOC-01 row) — MET

- [x] `grep -c "^| SERIALIZER-DOC-01" .planning/REQUIREMENTS.md` = `2`
- [x] Rollup updated: 29 reqs / 8 phases / 100%
- [x] Phase 24 coverage row: `SERIALIZER-01, SERIALIZER-DOC-01` (2 reqs)

### Task 2 (SDET-AUTHORING soften) — MET

- [x] `grep -F "_CpuBumpManageVmParams(extra=" docs/SDET-AUTHORING.md` matches
- [x] `grep -F "project_framework_primitives_sdet_safety_principle.md" docs/SDET-AUTHORING.md` matches
- [x] Phase 21 D-06 lock honored (SEED-022 teaching content preserved verbatim)

### Task 3a (live PASS-output capture) — DEFERRED

- [ ] Live `mcp-test-framework run --sdet -k proxmox_vm_lifecycle_readme_sample` run produces PASS output → DEFERRED (keyring isolation)
- [ ] Capture file with `Result: <N> PASS / 0 FAIL / <K> SKIP` → DEFERRED

### Task 3b (README paste + intro/framing rewrite) — DEFERRED

- [ ] README.md §`## SDET scenarios` shows PASS-output snapshot → DEFERRED
- [ ] Intro paragraph (L266-L272) rewritten → DEFERRED
- [ ] Post-snapshot framing paragraph (L420-L427) rewritten → DEFERRED
- [ ] `grep -F "exclude_unset" README.md` matches → DEFERRED (README unchanged)
- [ ] `grep -F "shown here mid-failure" README.md` returns 0 → NOT MET (string still present; deferred)
- [ ] `grep -F "surfaces that contract bug as a real test failure" README.md` returns 0 → NOT MET (string still present; deferred)
- [x] Resurrected sample test file absent: file was never resurrected in this branch; pre-existing tracked file at HEAD untouched
- [x] Temp capture file absent: deleted in recovery sequence

### Task 4 (operator checkpoint) — RESOLVED (regen-failed branch)

- [x] Operator returned `regen-failed: <reason>` with verbatim explanation
- [x] Partial-completion contract executed: Tasks 1+2 committed; README untouched; STATE.md Deferred Items row appended; SUMMARY.md `verify_status: partial`

## SEED-022 Invariant Preservation

The `_CpuBumpManageVmParams(extra='allow')` code block in `docs/SDET-AUTHORING.md` is preserved verbatim per Phase 21 D-06. The teaching that "the framework doesn't paper over upstream bugs — explicit-null testing flows null through to the wire" remains in the doc, just reframed as the explicit-null-test escape hatch rather than the default-Proxmox-call requirement. SERIALIZER-DOC-01 captures this framing-shift requirement.

## Files Touched (this plan)

**Modified:**
- `.planning/REQUIREMENTS.md` — SERIALIZER-DOC-01 row + traceability + phase-24 coverage
- `docs/SDET-AUTHORING.md` — §`## The inputSchema workaround` framing softened
- `.planning/STATE.md` — Current Position, frontmatter, Session Continuity, Deferred Items

**Intentionally NOT modified (per regen-failed contract):**
- `README.md` — pre-Plan-24-02 state preserved; manual UAT will re-capture
- `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py` — already tracked from Phase 21.1; never resurrected/edited in this branch

**Deleted (untracked artifact):**
- `.planning/phases/24-tool-call-serializer-omits-unset-optional-params-exclude-uns/24-02-readme-capture.txt` — failed-attempt temp file from prior continuation agent; removed in recovery

## Commit Trail

| Order | Hash | Type | Description |
|-------|------|------|-------------|
| 1 | `520b3a8` | docs | Task 1 — add SERIALIZER-DOC-01 requirement row |
| 2 | `250a59d` | docs | Task 2 — soften inputSchema workaround framing in SDET-AUTHORING |
| 3 | `afe4d2c` | docs | Partial-completion recovery — STATE.md Deferred Items row + Current Position update |
| 4 | (this commit) | docs | SUMMARY.md write + ROADMAP.md plan-progress update |

## Self-Check: PASSED

- File `.planning/REQUIREMENTS.md` modified by Task 1 (commit `520b3a8`) — verified via `git log --oneline -5`
- File `docs/SDET-AUTHORING.md` modified by Task 2 (commit `250a59d`) — verified
- File `.planning/STATE.md` modified by recovery (commit `afe4d2c`) — verified
- File `README.md` confirmed untouched at HEAD — verified via empty `git diff HEAD -- README.md`
- File `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py` confirmed untouched at HEAD — verified via empty `git diff HEAD -- tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py`
- Untracked capture file `.planning/phases/24-.../24-02-readme-capture.txt` confirmed deleted — verified via `ls` returning "No such file or directory"
- All three commit hashes (`520b3a8`, `250a59d`, `afe4d2c`) present in `git log` history
