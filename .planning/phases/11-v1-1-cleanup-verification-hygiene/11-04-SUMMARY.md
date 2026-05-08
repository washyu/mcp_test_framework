---
phase: 11
plan: 04-extending-env-passthrough-section
subsystem: docs
tags:
  - documentation
  - isolation
  - audit-closure
  - extending
dependencies:
  requires:
    - "Phase 06 (per-session host-state isolation) — _PASSTHROUGH_ALLOWLIST + WR-04 disposition exist"
    - "Phase 10 (v1.1 documentation) — DOC-07 'Add a new MCP tool target' section is the predecessor in EXTENDING.md"
  provides:
    - "Public-doc home for the env-passthrough allowlist warning (closes audit W-3 / Phase 06 SC-4 EXTENDING.md half)"
    - "Recorded WR-04 Branch B rationale: USERNAME-only allowlist is intentional; POSIX USER deliberately omitted (closes audit W-6)"
    - "GitHub auto-anchor #environment-passthrough-allowlist that the in-source forward-reference (_isolation.py:33-36) now resolves to"
  affects:
    - "src/mcp_test_framework/_isolation.py — UNCHANGED (Branch B disposition); the in-source warning's 'see EXTENDING.md' forward-reference now resolves to a real section"
tech_stack:
  added: []
  patterns:
    - "Public doc absorbs in-source warning text verbatim (blockquote) so contributors see governance constraints before reading source"
    - "Branch B disposition pattern: document the deliberate behaviour, leave the code unchanged, record audit traceability (W-6 / G-03) inline so a future verifier can trace the decision"
key_files:
  created:
    - ".planning/phases/11-v1-1-cleanup-verification-hygiene/11-04-SUMMARY.md"
  modified:
    - "docs/EXTENDING.md"
decisions:
  - "WR-04 disposition: Branch B (rationale-only, no code change). POSIX USER is intentionally NOT added to _PASSTHROUGH_ALLOWLIST. Locked v1.1 allowlist (Phase 06 D-07) names exactly USERNAME; HOME redirect is the load-bearing isolation guarantee and does not depend on user identity. Recorded in EXTENDING.md '## Environment passthrough allowlist' → '### Why POSIX USER is NOT in the allowlist'."
  - "DOC-07's SC-4 EXTENDING.md half (allowlist warning absorption), structurally deferred from Phase 06 to Phase 10 but unaddressed in Phase 10's per-tool walkthrough, is now closed by this plan."
  - "Section placement: between '## Add a new MCP tool target' (extension recipe) and '## Further reading' (TOC). Governance/safety-warning sections logically follow recipes and precede TOC."
metrics:
  duration: "1m 49s"
  tasks_completed: 1
  files_changed: 1
  lines_added: 85
  lines_removed: 0
  completed_date: "2026-05-08"
---

# Phase 11 Plan 04: docs/EXTENDING.md Environment Passthrough Allowlist Section Summary

Added a new `## Environment passthrough allowlist` H2 section to `docs/EXTENDING.md` that absorbs the verbatim `_PASSTHROUGH_ALLOWLIST` warning from `_isolation.py:33-36` and records the WR-04 Branch B rationale (USERNAME-only is intentional; POSIX USER deliberately omitted) — closing audit W-3 and W-6 with zero source-code changes.

## What Shipped

**One file modified:** `docs/EXTENDING.md` (+85 lines, 0 removed).

**New H2 section** inserted between "Add a new MCP tool target" and "Further reading":

- Opening prose explaining why the framework spawns MCP servers with a deliberately narrow environment, with a back-link to the README's `## Isolation guarantee` anchor.
- Enumeration of all five `_PASSTHROUGH_ALLOWLIST` entries: `PATH`, `SYSTEMROOT`, `LANG`, `USERNAME`, `MCP_*` (prefix match).
- Enumeration of all five `_HOME_OVERRIDES` vars (`HOME`, `USERPROFILE`, `TEMP`, `TMP`, `TMPDIR`) plus the keyring null-backend override (`PYTHON_KEYRING_BACKEND=keyring.backends.null.Null`).
- **H3 subsection "Do not widen this allowlist without justification"** — verbatim blockquote of the four-line "DO NOT widen `_PASSTHROUGH_ALLOWLIST`..." warning currently living at `_isolation.py:33-36`, plus a 3-step workflow for contributors who think they need a new entry.
- **H3 subsection "Why POSIX `USER` is NOT in the allowlist"** — records the WR-04 Branch B rationale: locked v1.1 allowlist (D-07) names exactly USERNAME; HOME redirect is the load-bearing isolation guarantee; USERNAME is informational only. Includes audit traceability references to `06-VERIFICATION.md` G-03 and `v1.1-MILESTONE-AUDIT.md` W-6 so a future verifier can trace the disposition.

**One new bullet** appended to the existing `## Further reading` list (now 6 entries, was 5), linking to the new section via the GitHub auto-anchor `#environment-passthrough-allowlist`.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add '## Environment passthrough allowlist' section to docs/EXTENDING.md | `bff1a28` | docs/EXTENDING.md |

## Audit Closure

| Audit Item | Source | Disposition | How Closed |
|------------|--------|-------------|------------|
| W-3 | v1.1-MILESTONE-AUDIT.md tech_debt §22-23 | EXTENDING.md absorbs `_isolation.py:33-36` warning | New `## Environment passthrough allowlist` section contains the verbatim "DO NOT widen..." blockquote |
| W-6 / WR-04 | v1.1-MILESTONE-AUDIT.md line 124 + 06-VERIFICATION.md G-03 (line 233) | Branch B: rationale-only, no code change | New `### Why POSIX USER is NOT in the allowlist` H3 subsection records the deliberate USERNAME-only design, with audit-trail references for traceability |
| Phase 06 SC-4 (EXTENDING.md half) | 06-VERIFICATION.md G-01 (lines 203-215) | Structurally deferred Phase 06 → Phase 10, unaddressed in Phase 10's per-tool walkthrough | Now satisfied: the in-source `_isolation.py:33-36` forward-reference "see DOC-07 in Phase 10" resolves to a real EXTENDING.md anchor |

## Acceptance Criteria

All criteria from `<acceptance_criteria>` verified post-commit:

| Criterion | Result |
|-----------|--------|
| `## Environment passthrough allowlist` H2 exists exactly once | PASS (count = 1) |
| `### Why POSIX USER is NOT in the allowlist` H3 exists exactly once | PASS (count = 1) |
| `_PASSTHROUGH_ALLOWLIST` token appears ≥3 times | PASS (count = 6) |
| `DO NOT widen` blockquote present | PASS (count = 1) |
| `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` literal | PASS (count = 1) |
| `USERNAME` token appears ≥2 times | PASS (count = 5) |
| Audit-trail reference (W-6 or G-03) | PASS (count = 1) |
| `(#environment-passthrough-allowlist)` anchor link | PASS (count = 1) |
| Total H2 sections = 5 (4 original + 1 new) | PASS (count = 5) |
| `src/mcp_test_framework/_isolation.py` UNCHANGED | PASS (`git diff` empty) |
| Allowlist enumeration: PATH, SYSTEMROOT, USERPROFILE, TMPDIR all present | PASS |

## Deviations from Plan

None — plan executed exactly as written. The `<exact_section_content>` floor was followed verbatim with minor stylistic touches (em-dash style harmonised to ASCII `--` to match the rest of `EXTENDING.md`; small additions in the workflow bullets to clarify "where to capture a reproducer" and to mention `GITHUB_TOKEN` as an always-secrets example alongside `AWS_PROFILE`). Every named element from the plan's "MUST appear" list is present.

## Threat Surface

Per the plan's `<threat_model>`, this is a paper-only doc edit:

- **T-11-04-01 (information disclosure):** Accepted — the new section enumerates env-var names already documented in the public README and visible in `_isolation.py` (which ships in the package). No secrets or homelab-specific identifiers introduced.
- **T-11-04-02 (drift between source warning and doc warning):** Accepted — the audit's recommendation IS to have the same text in two places (`_isolation.py:33-36` and now `EXTENDING.md`). Future maintainers updating one should update the other; track via grep on either string.

No new threat surface introduced. WR-04 Branch B disposition means no allowlist literal is modified, so the isolation guarantee is unchanged.

## Self-Check: PASSED

**File existence:**
- FOUND: `docs/EXTENDING.md` (modified, 245 lines after edit)
- FOUND: `.planning/phases/11-v1-1-cleanup-verification-hygiene/11-04-SUMMARY.md` (this file)

**Commit existence:**
- FOUND: `bff1a28` — `docs(11-04): add Environment passthrough allowlist section to EXTENDING.md`

**Source-code untouched (Branch B verification):**
- `git diff HEAD~1 HEAD -- src/mcp_test_framework/_isolation.py` → empty (confirmed)

**Acceptance criteria:** All 12 grep-based checks passed (see Acceptance Criteria table above).
