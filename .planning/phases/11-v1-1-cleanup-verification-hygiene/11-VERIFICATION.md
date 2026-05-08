---
phase: 11-v1-1-cleanup-verification-hygiene
verified: 2026-05-08T00:00:00Z
status: passed
score: 6/6 ROADMAP success criteria verified
criteria_met: 6
criteria_total: 6
requirements_completed: 0
requirements_total: 0
re_verification: false
findings:
  pass: 6
  partial: 0
  fail: 0
  human_verify: 0
audit_items_closed:
  - "W-1: 09-VERIFICATION.md authored from existing SUMMARY trio + tests/test_reporter.py evidence"
  - "W-3: docs/EXTENDING.md absorbs the _isolation.py env-passthrough-allowlist warning (Phase 06 SC-4 EXTENDING.md half)"
  - "W-4: REQUIREMENTS.md traceability table reads Complete for every v1.1 REQ-ID; DOC-04..07 body checkboxes are [x]; Coverage: 25/25 (100%)"
  - "W-5: ROADMAP.md Phase 06 SC-1 wording 'mtimes' -> 'sha256'"
  - "W-6: WR-04 disposition recorded as Branch B (rationale-only, no _isolation.py code change)"
  - "Planner-flagged Phase 07 drift: bullet checkbox + Progress row marked Complete 2026-05-07"
known_findings_carried_forward:
  - finding: "WR-01 (REVIEW.md): docs/EXTENDING.md:181 cites _isolation.py:33-36 but warning actually starts at line 36 (range 36-39)"
    severity: WARNING
    why_not_blocker: "The verbatim warning text IS present in the blockquote; only the line-range citation pointer is off-by-three. Audit W-3 asks for the warning to be absorbed into EXTENDING.md (it is); the citation precision is a doc-quality nit, not an audit-closure gap."
    disposition: "Defer to a v1.2 docs polish pass (or quick fix-forward); does not block Phase 11 closure."
  - finding: "IN-01 (REVIEW.md): docs/EXTENDING.md:162 says '_PASSTHROUGH_ALLOWLIST of exactly five entries' but the tuple in _isolation.py:50-63 has four entries; MCP_* is a separate _MCP_PREFIX prefix-match (line 64)"
    severity: INFO
    why_not_blocker: "User-facing concept (five passthrough categories) is correct; the structural framing conflates tuple-membership with category-count. A contributor who reads the source will see the truth (four-tuple + prefix). Doc-quality nit."
    disposition: "Defer to a v1.2 docs polish pass; does not block Phase 11 closure."
notes:
  - "Phase 11 is a paper-only audit-closure phase: zero source-code changes, four documentation edits across .planning/ and docs/. The phase goal is consistency between artifacts already shipped, not new functionality."
  - "Audit W-2 (capture deferred Phase 09 live evidence with --timeout=600) remains open by design — it is the lift path recorded in 09-VERIFICATION.md G-01 and audit recommendation A's explicit out-of-scope item. Not a Phase 11 SC; not a Phase 11 gap."
  - "WR-04 disposition is Branch B per audit recommendation: _isolation.py:50-63 untouched (the locked v1.1 allowlist names exactly USERNAME); rationale captured in EXTENDING.md '### Why POSIX `USER` is NOT in the allowlist' subsection."
---

# Phase 11: v1.1 Cleanup & Verification Hygiene — Verification Report

**Phase Goal:** Close all paper-only gaps surfaced by the v1.1 milestone audit so the milestone artifacts are internally consistent before archiving — every phase has a VERIFICATION.md, every traceability table reflects actual completion, every cross-reference in code is documented in the docs it points at.

**Verified:** 2026-05-08
**Status:** PASSED
**Score:** 6/6 ROADMAP success criteria verified
**Re-verification:** No — initial verification

---

## Goal Achievement

The phase goal is achieved end-to-end. Five audit items (W-1, W-3, W-4, W-5, W-6) plus the planner-flagged Phase 07 ROADMAP drift are now closed. The v1.1 milestone artifacts are internally consistent: Phase 09 has a formal VERIFICATION.md matching the 06/07/08/10 convention, REQUIREMENTS.md traceability shows 25/25 Complete with all DOC-04..07 body checkboxes flipped, ROADMAP.md uses the actually-shipped "sha256" wording for ISOL-03 SC-1 and marks Phase 07 Complete on 2026-05-07, and docs/EXTENDING.md absorbs the in-source `_PASSTHROUGH_ALLOWLIST` widening warning plus the WR-04 Branch B rationale (POSIX `USER` deliberately omitted; `USERNAME` alone is sufficient because the load-bearing isolation guarantee is the HOME redirect, not user identity).

Evidence is fourfold: (1) `.planning/phases/09-junit-xml-output-per-tool-reporting/09-VERIFICATION.md` (205 lines, frontmatter matches 06-VERIFICATION.md shape, cites all three 09-0N-SUMMARYs + tests/test_reporter.py + 3 deferred live tests by name); (2) `.planning/REQUIREMENTS.md` shows zero `| Pending |` cells and 25 `| Complete |` cells, plus all four `- [x] **DOC-0[4567]**` body bullets; (3) `.planning/ROADMAP.md` line 41 reads "the sha256 hashes of" (no "mtimes" remaining), line 26 has `[x] **Phase 07: ... (completed 2026-05-07)`, line 147 has `1/1 | Complete | 2026-05-07`; (4) `docs/EXTENDING.md` has a new H2 section at line 152 with the verbatim "DO NOT widen" blockquote, all five `_PASSTHROUGH_ALLOWLIST` entries enumerated, the H3 USER-vs-USERNAME rationale, and a Further-reading back-link.

`src/mcp_test_framework/_isolation.py` is unchanged — Branch B disposition for WR-04 is a deliberate no-code-change outcome.

---

## Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 09-VERIFICATION.md exists, cites SUMMARY trio + tests/test_reporter.py + 3 deferred live tests, frontmatter shape matches 06/07/08/10 (W-1) | PASS | `.planning/phases/09-junit-xml-output-per-tool-reporting/09-VERIFICATION.md` (205 lines): frontmatter has 12 keys (phase, verified, status, score, criteria_met, criteria_total, requirements_completed, requirements_total, re_verification, findings, deferred, notes) matching 06-VERIFICATION.md; status=passed; deferred block names test_junit_xml_emitted_and_well_formed, test_junit_xml_testcase_names_carry_tool_suffix, test_per_tool_summary_section_always_on; body cites 09-01-SUMMARY, 09-02-SUMMARY, 09-03-SUMMARY, tests/test_reporter.py at file:line precision; SC-1/SC-2/SC-3 sections all PASS; OUTPUT-01/OUTPUT-02/OUTPUT-03 all PASS; Final Verdict line `VERIFICATION PASSED` |
| 2 | docs/EXTENDING.md absorbs `_isolation.py` env-passthrough-allowlist warning (W-3, Phase 06 SC-4 EXTENDING.md half) | PASS | `docs/EXTENDING.md:152` `## Environment passthrough allowlist` H2; line 184 verbatim "DO NOT widen `_PASSTHROUGH_ALLOWLIST`" blockquote (matches `_isolation.py:36-39` warning); all 5 allowlist entries enumerated (lines 164-170); `_HOME_OVERRIDES` (HOME/USERPROFILE/TEMP/TMP/TMPDIR) enumerated (line 172); `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` literal (line 174); `_PASSTHROUGH_ALLOWLIST` token appears 6 times in section. Two REVIEW findings noted in `known_findings_carried_forward` (line-range nit, "five entries" framing) — neither blocks audit-closure since the warning text and rationale are present. |
| 3 | REQUIREMENTS.md Traceability table shows Complete for every v1.1 REQ-ID; DOC-04..07 checkboxes [x]; Coverage 25/25 (W-4) | PASS | `.planning/REQUIREMENTS.md`: `grep -c "\| Pending \|"` = 0; `grep -c "\| Complete \|"` = 25; lines 47-50 show `- [x] **DOC-04**` / `**DOC-05**` / `**DOC-06**` / `**DOC-07**` (no `[ ]` remaining for DOC-04..07); line 85 reads `Coverage: 25/25 (100%)` |
| 4 | ROADMAP.md Phase 06 SC-1 wording uses "sha256" not "mtimes" (W-5) | PASS | `.planning/ROADMAP.md:41` reads `the sha256 hashes of \`~/.homelab_mcp/credential_registry.json\`, ...`; `grep -c "the mtimes of" .planning/ROADMAP.md` = 0 |
| 5 | ROADMAP.md Phase 07 checkbox is [x] and Progress row says Complete 2026-05-07 (planner-flagged drift) | PASS | `.planning/ROADMAP.md:26` reads `- [x] **Phase 07: Multi-tool discovery & parameterized testing** ... (completed 2026-05-07)`; line 147 reads `\| 07. Multi-tool discovery & parameterized testing \| v1.1 \| 1/1 \| Complete \| 2026-05-07 \|` |
| 6 | WR-04 disposition recorded: either USER added to _PASSTHROUGH_ALLOWLIST + test, OR rationale recorded explaining USERNAME alone is sufficient (W-6) | PASS (Branch B) | `docs/EXTENDING.md:206` `### Why POSIX \`USER\` is NOT in the allowlist` H3 subsection records the Branch B rationale: locked v1.1 allowlist (D-07) names exactly USERNAME; HOME redirect is the load-bearing isolation guarantee and does not depend on user identity; USERNAME is informational only per `_isolation.py:55-62`. Audit-trail references to `06-VERIFICATION.md G-03` and `v1.1-MILESTONE-AUDIT.md W-6` present at line 226. `git log --oneline -- src/mcp_test_framework/_isolation.py` confirms `_isolation.py` unchanged in Phase 11 (Branch B = no code change). |

**Score:** 6/6 truths verified

---

## Audit Item Cross-Reference

The audit (`.planning/v1.1-MILESTONE-AUDIT.md`) lists six tech-debt items in the `tech_debt:` frontmatter. Phase 11's scope (per ROADMAP) was W-1, W-3, W-4, W-5, W-6 (five items) plus the planner-flagged Phase 07 drift. W-2 is explicitly out of scope (recorded in audit recommendation A and in 09-VERIFICATION.md G-01 as the lift path).

| Audit Item | Source | Phase 11 SC | Closed By | Status |
|-----------|--------|-------------|-----------|--------|
| W-1 (Phase 09 missing VERIFICATION.md) | audit lines 17-18 | SC-1 | Plan 11-01 (commit `69610a3`) | CLOSED |
| W-2 (Capture deferred Phase 09 live evidence) | audit lines 19, 111-112 | n/a (out of scope) | Tracked in 09-VERIFICATION.md G-01; audit-recommendation A explicitly marks W-2 as v1.2 / future | DEFERRED (not a Phase 11 SC) |
| W-3 (Phase 06 SC-4 EXTENDING.md half) | audit lines 22-23, 114-115 | SC-2 | Plan 11-04 (commit `bff1a28`) | CLOSED |
| W-4 (REQUIREMENTS.md traceability drift + DOC-04..07 checkboxes) | audit lines 26-28, 117-118 | SC-3 | Plan 11-03 (commits `334dd3c`, `185797d`) | CLOSED |
| W-5 (ROADMAP wording mtimes → sha256) | audit lines 30-31, 120-121 | SC-4 | Plan 11-02 (commit `0e50cd7`) | CLOSED |
| W-6 (WR-04 POSIX USER allowlist parity) | audit lines 24, 123-124 | SC-6 | Plan 11-04 Branch B rationale (commit `bff1a28`) | CLOSED |
| Planner-flagged: Phase 07 ROADMAP checkbox + Progress row drift | ROADMAP.md was the only artifact still showing Phase 07 as Planned | SC-5 | Plan 11-02 (commit `0e50cd7`) | CLOSED |

Every audit item the plan claimed to close IS accounted for in the codebase. W-2 is correctly NOT in scope and is correctly deferred via 09-VERIFICATION.md G-01.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.planning/phases/09-junit-xml-output-per-tool-reporting/09-VERIFICATION.md` | New file, 205 lines, frontmatter matches 06-VERIFICATION.md, cites SUMMARY trio + tests/test_reporter.py + 3 deferred live tests | VERIFIED | File present (205 lines per 11-01-SUMMARY); frontmatter has 12 expected keys; status: passed; deferred block names all 3 live test functions; body has SC-1/SC-2/SC-3 + OUTPUT-01..03 + Required Artifacts + Key Link Verification + Behavioural Spot-Checks + Deferred Items + Verification Gaps + Final Verdict (`VERIFICATION PASSED`) |
| `.planning/ROADMAP.md` | Phase 06 SC-1 says "sha256 hashes"; Phase 07 bullet `[x] (completed 2026-05-07)`; Phase 07 row `1/1 \| Complete \| 2026-05-07` | VERIFIED | All three edits present at lines 41, 26, 147 respectively; `the mtimes of` count = 0; `the sha256 hashes of` count = 1; line count 151 (no restructuring) |
| `.planning/REQUIREMENTS.md` | DOC-04..07 body bullets `[x]`; ISOL-03/06 + DOC-04..07 traceability rows say `Complete`; Coverage 25/25 | VERIFIED | All 4 DOC body checkboxes flipped (lines 47-50); zero `\| Pending \|` cells; 25 `\| Complete \|` cells; `Coverage: 25/25 (100%)` line preserved at line 85 |
| `docs/EXTENDING.md` | New `## Environment passthrough allowlist` H2 + H3 `### Why POSIX USER is NOT in the allowlist` + DO NOT widen blockquote + Further-reading bullet | VERIFIED | H2 at line 152; H3 at line 206; blockquote at line 184 (verbatim warning from `_isolation.py:36-39`); 5 allowlist entries + 5 HOME-overrides + keyring null-backend literal all enumerated; Further-reading bullet at line 243 with anchor `#environment-passthrough-allowlist`; `_PASSTHROUGH_ALLOWLIST` appears 6 times (≥3 required); audit-trail references to `W-6` and `G-03` at line 226 |
| `src/mcp_test_framework/_isolation.py` | UNCHANGED (Branch B disposition for WR-04) | VERIFIED | File contents preserved; `_PASSTHROUGH_ALLOWLIST` tuple at lines 50-63 still exactly four entries (PATH, SYSTEMROOT, LANG, USERNAME); `_MCP_PREFIX = "MCP_"` at line 64 unchanged. Branch B = no code change. |

---

## Key Link Verification

| From | To | Via | Status |
|------|-----|-----|--------|
| 09-VERIFICATION.md | 09-01-SUMMARY.md / 09-02-SUMMARY.md / 09-03-SUMMARY.md | Explicit citations in body (each ≥1 occurrence) | WIRED |
| 09-VERIFICATION.md | tests/test_reporter.py | Behavioural Spot-Checks table + Deferred Items table referencing 29 unit tests + 3 live tests by function name | WIRED |
| 09-VERIFICATION.md frontmatter `deferred:` block | 3 live test functions in tests/test_reporter.py | All three function names (test_junit_xml_emitted_and_well_formed, test_junit_xml_testcase_names_carry_tool_suffix, test_per_tool_summary_section_always_on) listed verbatim | WIRED |
| ROADMAP.md Phase 06 SC-1 | 06-VERIFICATION.md SC-1 (which already says sha256) | wording alignment — both now say "sha256" | WIRED |
| ROADMAP.md Phase 07 bullet + Progress row | 07-VERIFICATION.md (passed) | completion-state alignment — bullet [x], Progress row Complete 2026-05-07 | WIRED |
| REQUIREMENTS.md ISOL-03/06 rows | 06-VERIFICATION.md SC-1/SC-2 (passed) | status column matches verification verdict (Complete) | WIRED |
| REQUIREMENTS.md DOC-04..07 rows | 10-v1-1-documentation/VERIFICATION.md (18/18 passed) | status column + body checkbox both reflect verification outcome | WIRED |
| docs/EXTENDING.md `## Environment passthrough allowlist` | `src/mcp_test_framework/_isolation.py:36-39` warning | Verbatim blockquote of the in-source warning text | WIRED (with WR-01 line-range citation nit — see known_findings) |
| docs/EXTENDING.md `## Further reading` | `## Environment passthrough allowlist` | GitHub auto-anchor `#environment-passthrough-allowlist` | WIRED |
| docs/EXTENDING.md `### Why POSIX USER...` | audit-trail (W-6 + G-03) | inline reference at line 226 | WIRED |

No orphan or stub artifacts. Every cross-reference between the four edited files (and the unchanged `_isolation.py`) resolves.

---

## Behavioural Spot-Checks

| Behaviour | Command | Result | Status |
|-----------|---------|--------|--------|
| 09-VERIFICATION.md exists at canonical path | `Glob .planning/phases/09-junit-xml-output-per-tool-reporting/09-VERIFICATION.md` | 1 file (205 lines per SUMMARY) | PASS |
| 09-VERIFICATION.md frontmatter shape (12 keys) | `Grep -E "^(phase\|verified\|status\|score\|criteria_met\|...)" 09-VERIFICATION.md` | 12 keys present | PASS |
| 09-VERIFICATION.md cites SUMMARY trio | `Grep "09-0[123]-SUMMARY" 09-VERIFICATION.md` | each cited ≥1 time | PASS |
| 09-VERIFICATION.md cites tests/test_reporter.py | `Grep "tests/test_reporter.py" 09-VERIFICATION.md` | multiple matches | PASS |
| 09-VERIFICATION.md names 3 deferred live tests | `Grep "test_junit_xml_emitted_and_well_formed\|test_junit_xml_testcase_names_carry_tool_suffix\|test_per_tool_summary_section_always_on"` | all 3 present | PASS |
| ROADMAP.md sha256 wording | `Grep "the sha256 hashes of" ROADMAP.md` | 1 match (line 41) | PASS |
| ROADMAP.md mtimes wording absent | `Grep "the mtimes of" ROADMAP.md` | 0 matches | PASS |
| ROADMAP.md Phase 07 [x] bullet | `Grep "^- \[x\] \*\*Phase 07: Multi-tool"` | 1 match (line 26) with `(completed 2026-05-07)` suffix | PASS |
| ROADMAP.md Phase 07 Progress row | `Grep "07\. Multi-tool discovery & parameterized testing \| v1.1 \| 1/1 \| Complete \| 2026-05-07"` | 1 match (line 147) | PASS |
| REQUIREMENTS.md zero Pending | `Grep "\| Pending \|" REQUIREMENTS.md` | 0 matches | PASS |
| REQUIREMENTS.md 25 Complete | `Grep "\| Complete \|" REQUIREMENTS.md` | 25 matches | PASS |
| REQUIREMENTS.md DOC-04..07 [x] | `Grep "^- \[x\] \*\*DOC-0[4567]\*\*"` | 4 matches (lines 47-50) | PASS |
| REQUIREMENTS.md DOC-04..07 [ ] absent | `Grep "^- \[ \] \*\*DOC-0[4567]\*\*"` | 0 matches | PASS |
| REQUIREMENTS.md Coverage 25/25 | `Grep "Coverage: 25/25 \(100%\)"` | 1 match (line 85) | PASS |
| EXTENDING.md H2 section | `Grep "^## Environment passthrough allowlist$"` | 1 match (line 152) | PASS |
| EXTENDING.md H3 USER subsection | `Grep "^### Why POSIX \`USER\` is NOT in the allowlist$"` | 1 match (line 206) | PASS |
| EXTENDING.md DO NOT widen blockquote | `Grep "DO NOT widen"` | 1 match (line 184) | PASS |
| EXTENDING.md keyring null-backend literal | `Grep "PYTHON_KEYRING_BACKEND=keyring.backends.null.Null"` | 1 match (line 174) | PASS |
| EXTENDING.md _PASSTHROUGH_ALLOWLIST mentions | `Grep "_PASSTHROUGH_ALLOWLIST"` | 6 matches (≥3 required) | PASS |
| EXTENDING.md audit-trail reference | `Grep "(W-6\|G-03)"` | both present (line 226) | PASS |
| EXTENDING.md Further-reading anchor link | `Grep "(#environment-passthrough-allowlist)"` | 1 match (line 243) | PASS |
| `_isolation.py` unchanged (Branch B) | Read `src/mcp_test_framework/_isolation.py:50-63` — `_PASSTHROUGH_ALLOWLIST` still 4-tuple (PATH, SYSTEMROOT, LANG, USERNAME), no USER added | PASS (no code change, as Branch B requires) | PASS |

All spot-checks pass.

---

## Requirements Coverage

Phase 11 closes audit gaps; it does NOT introduce new requirements. The plan frontmatter for all four sub-plans (11-01, 11-02, 11-03, 11-04) has `requirements: []`. ROADMAP Phase 11 explicitly states "**Type**: gap closure (no new requirements; cleans up existing artifacts)".

No REQUIREMENTS.md cross-reference is required for Phase 11 itself. The phase's effect on REQUIREMENTS.md is to flip ISOL-03 / ISOL-06 / DOC-04..07 traceability cells from Pending → Complete (now reflecting Phase 06 / Phase 10 verification verdicts that were already PASS) — those requirements were always satisfied; Phase 11 only fixes the documentation drift.

---

## Anti-Patterns Found

None. The phase is paper-only documentation cleanup. No source-code changes; no TODO/FIXME/PLACEHOLDER additions; no stub patterns.

The two REVIEW.md findings (WR-01 line-range nit, IN-01 "exactly five entries" framing) are both in `docs/EXTENDING.md` — they are doc-quality nits, not anti-patterns or stubs. Both are recorded in `known_findings_carried_forward` in this VERIFICATION's frontmatter for traceability. Per user verification instruction: these do NOT block W-3 closure since the warning text and rationale are present.

---

## Verification Gaps

None blocking. Two informational findings carried forward from 11-REVIEW.md:

### F-01 — Off-by-three line-range citation in EXTENDING.md (WR-01)

**Severity:** WARNING (does not block phase or audit closure)

**What:** `docs/EXTENDING.md:181` cites `_isolation.py:33-36` as the home of the "DO NOT widen" warning. The warning actually lives at `_isolation.py:36-39` (line 36 is the first warning line; line 39 is the trailing prose; lines 33-35 are an unrelated paragraph about cmdkey recon).

**Why it's not a blocker:** W-3's audit-closure requirement is "EXTENDING.md absorbs the warning text" — the verbatim warning IS in the blockquote (line 184), so the audit item IS closed. The line-range pointer is metadata about WHERE the warning lives in the source, not part of the warning itself.

**Recommendation:** Quick fix-forward (one-line edit to change `33-36` → `36-39` at EXTENDING.md:181) or defer to v1.2 docs polish.

### F-02 — "Exactly five entries" structural-vs-conceptual framing in EXTENDING.md (IN-01)

**Severity:** INFO

**What:** `docs/EXTENDING.md:162` says `_PASSTHROUGH_ALLOWLIST` has "exactly five entries" then lists PATH, SYSTEMROOT, LANG, USERNAME, MCP_*. In the actual source, `_PASSTHROUGH_ALLOWLIST` is a four-tuple (PATH, SYSTEMROOT, LANG, USERNAME); MCP_* is matched via the separate `_MCP_PREFIX` constant.

**Why it's not a blocker:** Conceptually correct (five passthrough categories). Audit W-3 is about absorbing the warning, not about the structural enumeration shape.

**Recommendation:** Defer to v1.2 docs polish; either tighten the prose to "tuple of four exact-match entries plus a separate `_MCP_PREFIX` prefix-match branch" or add a parenthetical clarifying that MCP_* is prefix-matched alongside the tuple.

---

## Deferred Items

| Item | Source | Lift Path |
|------|--------|-----------|
| Audit W-2 — capture Phase 09 deferred live test evidence (results.xml + per-tool summary stdout) into a `raw/` artifact | audit lines 19, 111-112; 09-VERIFICATION.md G-01 | Re-run `mcp-test-framework run -- -m live_homelab` with `--timeout=600` on a developer host or CI; capture artifacts. NOT a Phase 11 SC; explicitly out of scope per audit recommendation A. |

W-2 deferral is correct and pre-accepted. It does NOT affect Phase 11 closure.

---

## Final Verdict

**VERIFICATION PASSED** — Phase 11 achieves the goal "Close all paper-only gaps surfaced by the v1.1 milestone audit so the milestone artifacts are internally consistent before archiving." 6/6 ROADMAP success criteria are met. All five in-scope audit items (W-1, W-3, W-4, W-5, W-6) plus the planner-flagged Phase 07 ROADMAP drift are CLOSED. W-2 (deferred Phase 09 live evidence capture) is correctly out of scope and remains tracked in 09-VERIFICATION.md G-01.

Two non-blocking REVIEW findings are carried forward for awareness:
- **F-01 (WR-01):** EXTENDING.md cites `_isolation.py:33-36` instead of the correct `36-39`. Doc-quality nit; warning text itself is present and verbatim.
- **F-02 (IN-01):** EXTENDING.md says `_PASSTHROUGH_ALLOWLIST` "exactly five entries"; the tuple has four plus a separate prefix-match. Conceptually correct, structurally loose.

Both findings are appropriate for a v1.2 docs polish pass and explicitly do NOT block W-3 closure (the warning IS absorbed; the H3 rationale subsection IS present; the audit-trail references W-6 + G-03 ARE inline).

The v1.1 milestone is now in a clean audit-PASS state suitable for `/gsd-complete-milestone v1.1`.

---

_Verified: 2026-05-08_
_Verifier: Claude (gsd-verifier — goal-backward verification of Phase 11 audit-closure scope)_
