---
phase: 20-preflight-conditional-skip
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/REQUIREMENTS.md
autonomous: true
requirements:
  - CLEANUP-DOGFOOD-01
  - CODEGEN-COVERAGE-01
  - REQ-SCRUB-01
must_haves:
  truths:
    - "REQUIREMENTS.md no longer contains PREFLIGHT-01 or PREFLIGHT-02 rows"
    - "REQUIREMENTS.md contains three new requirement IDs replacing the PREFLIGHT pair: CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01"
    - "Traceability table maps the three new IDs to Phase 20 with status Pending"
    - "Phase coverage summary table shows Phase 20 with the three new IDs (count 3)"
    - "Total requirements count in REQUIREMENTS.md is internally consistent (22)"
  artifacts:
    - path: ".planning/REQUIREMENTS.md"
      provides: "Updated requirements with PREFLIGHT-01/02 removed and three Phase 20 replacements added"
      contains: "CLEANUP-DOGFOOD-01"
  key_links:
    - from: ".planning/REQUIREMENTS.md (Traceability Table)"
      to: ".planning/REQUIREMENTS.md (Phase coverage summary)"
      via: "matching counts and IDs"
      pattern: "CLEANUP-DOGFOOD-01.*Phase 20.*Pending"
---

<objective>
Scrub PREFLIGHT-01 and PREFLIGHT-02 from REQUIREMENTS.md (per D-11) and add the three new requirements that describe what Phase 20 actually delivers (per D-12). These new IDs are referenced by the frontmatter of every other Phase 20 plan, so this plan MUST land first.

Purpose: Restore alignment between REQUIREMENTS.md and the reframed Phase 20 scope (test-cleanup + mock-fixture codegen coverage + req-scrub).
Output: Updated `.planning/REQUIREMENTS.md` with three new rows in a new requirement group, two PREFLIGHT rows removed, and matching updates to the Traceability Table and Phase coverage summary.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/20-preflight-conditional-skip/20-CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace the PREFLIGHT requirement group with the new CLEANUP-DOGFOOD / CODEGEN-COVERAGE / REQ-SCRUB rows</name>
  <files>.planning/REQUIREMENTS.md</files>
  <read_first>
    - .planning/REQUIREMENTS.md (full file — read once, plan all edits in a single pass)
    - .planning/phases/20-preflight-conditional-skip/20-CONTEXT.md (D-11, D-12, and the <specifics> "REQUIREMENTS.md edit shape" sketch)
  </read_first>
  <action>
Edit `.planning/REQUIREMENTS.md` in three coordinated locations. Make ALL three edits in this single task — no partial states.

**Edit 1 — Replace the "### PREFLIGHT — Conditional execution and environment checks" section.**

Find the entire section that starts at the heading `### PREFLIGHT — Conditional execution and environment checks` and ends just before `### UI — Domain rendering for SDET runs`. Replace the whole section (heading + table + the two PREFLIGHT-01/02 rows) with this exact text:

```
### CLEANUP — v1.3 retroactive scope correction (Phase 20)

| ID                  | Description                                                                                                                                                                                                                       |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CLEANUP-DOGFOOD-01  | SUT-specific dogfood test files removed from `tests/sdet/`; the project's shipped test suite stays SUT-agnostic so CI can run without operator-specific infrastructure (Proxmox, Ansible, etc.).                                  |
| CODEGEN-COVERAGE-01 | Mock-fixture-driven unit tests verify the codegen pipeline produces correctly-shaped `<ToolName>Params` / `<ToolName>Response` / `_REGISTRY` artifacts for a synthetic tool list (no live MCP, CI-safe).                          |
| REQ-SCRUB-01        | PREFLIGHT-01 and PREFLIGHT-02 removed from REQUIREMENTS.md; "hello-world MCP server for CI-runnable end-to-end coverage" recorded as a deferred item for a future v1.x phase.                                                     |
```

**Edit 2 — Update the Traceability Table.**

Find the table that starts with `| Requirement ID | Phase    | Status   |`. Locate the two rows:
```
| PREFLIGHT-01   | Phase 20 | Pending  |
| PREFLIGHT-02   | Phase 20 | Pending  |
```
DELETE both rows.

Then ADD three new rows immediately after `| STATE-04       | Phase 19 | Pending  |` (preserve existing row ordering — Phase 19 cluster, then Phase 20 cluster, then UI-01 row stays where it is). The three new rows go where PREFLIGHT-01/02 used to be (between Phase 19 and UI-01):

```
| CLEANUP-DOGFOOD-01  | Phase 20 | Pending  |
| CODEGEN-COVERAGE-01 | Phase 20 | Pending  |
| REQ-SCRUB-01        | Phase 20 | Pending  |
```

Also update the totals line:
- Before: `**Total: 21 requirements mapped across 5 phases (17–21). Coverage: 21/21 (100%).**`
- After: `**Total: 22 requirements mapped across 5 phases (17–21). Coverage: 22/22 (100%).**`

**Edit 3 — Update the Phase coverage summary table.**

Find the row `| 20    | PREFLIGHT-01, PREFLIGHT-02                                                  | 2     |` and REPLACE it with:

```
| 20    | CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01                       | 3     |
```

Make no other edits to REQUIREMENTS.md. Do NOT touch the Milestone Goal, Out of Scope, or Open Design Questions sections. Do NOT modify rows for SDET-*, CODEGEN-*, STATE-*, UI-*, or DOC-SDET-*.

After editing, the file MUST satisfy these invariants (you will grep-verify these in the next task — keep them in mind while editing):
- Zero occurrences of `PREFLIGHT-01` or `PREFLIGHT-02` anywhere in the file.
- Exactly one heading line `### CLEANUP — v1.3 retroactive scope correction (Phase 20)`.
- Exactly three Traceability Table rows mapping the new IDs to `Phase 20 | Pending`.
- Exactly one totals line containing `Total: 22 requirements`.
- Exactly one Phase coverage summary row for Phase 20 listing all three new IDs.
  </action>
  <verify>
    <automated>powershell -NoProfile -Command "$f='.planning/REQUIREMENTS.md'; $t=Get-Content $f -Raw; $checks=@{'no PREFLIGHT-01'=(($t -match 'PREFLIGHT-01') -eq $false); 'no PREFLIGHT-02'=(($t -match 'PREFLIGHT-02') -eq $false); 'has CLEANUP section'=($t -match '### CLEANUP --- v1.3 retroactive scope correction \(Phase 20\)' -or $t -match '### CLEANUP — v1.3 retroactive scope correction \(Phase 20\)'); 'has CLEANUP-DOGFOOD-01'=($t -match 'CLEANUP-DOGFOOD-01'); 'has CODEGEN-COVERAGE-01'=($t -match 'CODEGEN-COVERAGE-01'); 'has REQ-SCRUB-01'=($t -match 'REQ-SCRUB-01'); 'totals 22'=($t -match 'Total: 22 requirements'); 'phase20 row has all 3 IDs'=($t -match '\| 20 +\| CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01')}; $fail=0; foreach($k in $checks.Keys){ if(-not $checks[$k]){ Write-Host \"FAIL: $k\"; $fail=1 } else { Write-Host \"OK: $k\" } }; exit $fail"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'PREFLIGHT-0[12]' .planning/REQUIREMENTS.md` returns `0`.
    - `grep -c '^### CLEANUP' .planning/REQUIREMENTS.md` returns `1`.
    - `grep -c 'CLEANUP-DOGFOOD-01' .planning/REQUIREMENTS.md` returns at least `3` (group row + traceability row + phase coverage summary row).
    - `grep -c 'CODEGEN-COVERAGE-01' .planning/REQUIREMENTS.md` returns at least `3`.
    - `grep -c 'REQ-SCRUB-01' .planning/REQUIREMENTS.md` returns at least `3`.
    - `grep -c 'Total: 22 requirements' .planning/REQUIREMENTS.md` returns `1`.
    - `grep -c 'Total: 21 requirements' .planning/REQUIREMENTS.md` returns `0`.
    - The Phase 20 row in the Phase coverage summary table reads `| 20    | CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01                       | 3     |` (column-padding may vary by one space — content match is what matters).
  </acceptance_criteria>
  <done>REQUIREMENTS.md has zero PREFLIGHT references, three new requirement rows in a new CLEANUP group, three new traceability rows, updated totals (21→22), and a corrected Phase 20 row in the Phase coverage summary. All invariants above pass.</done>
</task>

</tasks>

<verification>
After this plan completes:
- `grep -E 'PREFLIGHT-0[12]' .planning/REQUIREMENTS.md` returns nothing.
- The three new requirement IDs each appear at least 3 times (group definition, traceability, phase summary).
- Totals + phase-count internal consistency holds.
</verification>

<success_criteria>
- REQUIREMENTS.md reflects D-11 (PREFLIGHT removed) and D-12 (three new IDs added).
- Downstream Phase 20 plans can reference the three new IDs in their `requirements:` frontmatter and they exist in REQUIREMENTS.md.
- No structural damage to unrelated requirement groups (SDET, CODEGEN, STATE, UI, DOC-SDET unchanged).
</success_criteria>

<output>
After completion, create `.planning/phases/20-preflight-conditional-skip/20-01-SUMMARY.md`.
</output>
