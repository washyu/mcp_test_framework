---
phase: 20-preflight-conditional-skip
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/ROADMAP.md
autonomous: true
requirements:
  - CLEANUP-DOGFOOD-01
  - CODEGEN-COVERAGE-01
  - REQ-SCRUB-01
must_haves:
  truths:
    - "ROADMAP.md Phase 20 entry's Goal matches the reframed scope (no `requires_homelab` language)"
    - "ROADMAP.md Phase 20 Success Criteria describe: dogfood deletion + REQUIREMENTS edits landed + mock-fixture codegen unit tests added"
    - "ROADMAP.md Phase 20 Requirements line lists the three new IDs (no PREFLIGHT)"
    - "ROADMAP.md milestone bullet for Phase 20 no longer says `requires_homelab(...)`"
  artifacts:
    - path: ".planning/ROADMAP.md"
      provides: "Phase 20 entry rewritten to reflect reframed scope"
      contains: "CLEANUP-DOGFOOD-01"
  key_links:
    - from: ".planning/ROADMAP.md (Phase Details / Phase 20)"
      to: ".planning/REQUIREMENTS.md"
      via: "matching requirement IDs"
      pattern: "Requirements.*CLEANUP-DOGFOOD-01.*CODEGEN-COVERAGE-01.*REQ-SCRUB-01"
---

<objective>
Rewrite the ROADMAP.md Phase 20 entry to reflect the reframed scope locked in CONTEXT.md D-13. The current Goal ("An SDET decorating a scenario module with `requires_homelab(...)`...") is stale and was rejected during discuss-phase. Replace it with the actual deliverables: dogfood deletion, REQUIREMENTS scrub, mock-fixture codegen unit tests.

Purpose: Keep ROADMAP.md the canonical phase reference; downstream agents reading it should see the current scope, not the rejected pre-discuss-phase wording.
Output: Updated `.planning/ROADMAP.md` Phase 20 milestone bullet + Phase Details section.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/20-preflight-conditional-skip/20-CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite ROADMAP.md Phase 20 milestone bullet + Phase Details entry</name>
  <files>.planning/ROADMAP.md</files>
  <read_first>
    - .planning/ROADMAP.md (full file — read once; identify exact byte ranges for both edits before writing)
    - .planning/phases/20-preflight-conditional-skip/20-CONTEXT.md (D-13 and the <domain> "Three deliverables" framing)
  </read_first>
  <action>
Make TWO coordinated edits to `.planning/ROADMAP.md`. Land both in this single task.

**Edit 1 — Replace the Phase 20 line in the v1.3 milestone-bullet block.**

Find the line that reads:
```
- [ ] **Phase 20: Preflight + conditional skip** — `requires_homelab(...)` marker factory with fast, graceful reachability checks (PREFLIGHT-01..02)
```

Replace with:
```
- [ ] **Phase 20: v1.3 scope correction — dogfood cleanup + codegen coverage** — delete SUT-specific dogfood from `tests/sdet/`; replace PREFLIGHT-01/02 with mock-fixture codegen unit tests under `tests/framework/unit/`; rewrite REQUIREMENTS rows and this roadmap entry to match the reframed scope (CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01)
```

**Edit 2 — Replace the entire `### Phase 20: Preflight + conditional skip` block in the Phase Details section.**

Find the block that starts with `### Phase 20: Preflight + conditional skip` and ends just before `### Phase 21: SDET authoring docs + README parity`. Replace the whole block (heading + Goal + Depends on + Requirements + Success Criteria + Plans line) with this exact text:

```
### Phase 20: v1.3 scope correction — dogfood cleanup + codegen coverage
**Goal**: v1.3's PREFLIGHT requirements as originally written (`requires_homelab(...)` marker factory) violate the framework-primitives principle (SEED-022) by baking SUT-specific subsystem knowledge into the framework API surface. This phase retroactively corrects v1.3: delete the SUT-specific Proxmox dogfood from `tests/sdet/`, drop PREFLIGHT-01/02 from REQUIREMENTS.md, and replace the killed coverage with mock-fixture-driven unit tests that verify the codegen pipeline shape against a synthetic tool list (no live MCP, CI-safe). Zero `src/` framework changes.
**Depends on**: Phase 19 (the dogfood file deleted here was authored in Phase 19; the codegen surface tested here is owned by Phase 17)
**Requirements**: CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01
**Success Criteria** (what must be TRUE):
  1. `tests/sdet/test_proxmox_vm_lifecycle.py` is removed from the working tree (no archive, no `@pytest.mark.skip`, no comment-out). `tests/sdet/test_basic_call.py` disposition decided and applied (planner picks per CONTEXT.md D-06).
  2. PREFLIGHT-01 and PREFLIGHT-02 no longer appear anywhere in `.planning/REQUIREMENTS.md`; three new requirement IDs (CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01) are added to a new CLEANUP requirement group, the Traceability Table, and the Phase coverage summary table; v1.3 total requirements count is internally consistent (22).
  3. New mock-fixture-driven unit tests under `tests/framework/unit/` feed a hardcoded synthetic tool list (covering required scalar + optional-with-default + array + integer-with-default + outputSchema-declared + outputSchema-omitted branches) through the codegen pipeline into a temp directory, then `importlib.import_module` introspects the generated artifacts and asserts: `<ToolName>Params` Pydantic class shape; `<ToolName>Response` inherits `ToolResponse` and exposes `.raw` / `.data` / `.text` / `.is_error`; `_REGISTRY` tuple shape; module imports cleanly. Does NOT touch `src/mcp_test_framework/sdet/generated/homelab_mcp/`.
  4. `.planning/STATE.md` reflects: Phase 19 deferred D-02 marked Resolved-by-deletion (Phase 20); the reframe recorded under Decisions; upstream homelab-mcp inputSchema bug deferred-items entry untouched.
**Plans**: 5 plans (2 waves)
  - [ ] 20-01-requirements-scrub-PLAN.md — Remove PREFLIGHT-01/02 from REQUIREMENTS.md; add CLEANUP-DOGFOOD-01 / CODEGEN-COVERAGE-01 / REQ-SCRUB-01 to a new CLEANUP requirement group; update Traceability Table and Phase coverage summary; total goes 21->22 (CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01) [wave 1; depends_on: ]
  - [ ] 20-02-roadmap-rewrite-PLAN.md — Rewrite ROADMAP.md Phase 20 milestone bullet and Phase Details block to reflect the reframed scope (CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01) [wave 1; depends_on: ]
  - [ ] 20-03-state-update-PLAN.md — STATE.md: record reframe under Decisions; mark Phase 19 D-02 Resolved-by-deletion; add hello-world MCP deferred-items entry; preserve upstream-fix inputSchema row (REQ-SCRUB-01) [wave 1; depends_on: ]
  - [ ] 20-04-tests-sdet-cleanup-PLAN.md — Delete tests/sdet/test_proxmox_vm_lifecycle.py (D-04) and tests/sdet/test_basic_call.py (D-06 option c); preserve __init__.py + conftest.py (CLEANUP-DOGFOOD-01) [wave 1; depends_on: ]
  - [ ] 20-05-codegen-mock-fixture-tests-PLAN.md — Add tests/framework/unit/test_codegen_integration_mock.py with synthetic 3-tool fixture driven through codegen pipeline + importlib introspection (CODEGEN-COVERAGE-01) [wave 2; depends_on: 20-01]
```

Make no other edits to ROADMAP.md. Do NOT modify the Phase 17, 18, 19, 21, or 22 entries. Do NOT modify the Progress table.

Acceptance invariants to keep in mind while editing:
- Zero occurrences of `requires_homelab` anywhere in ROADMAP.md after the edits.
- Zero occurrences of `PREFLIGHT-01` or `PREFLIGHT-02` anywhere in ROADMAP.md.
- The three new requirement IDs appear at least once in the Phase 20 entry.
- The Phase 20 milestone bullet still starts with `- [ ] **Phase 20:` (not yet completed).
- Phase 21 heading is reachable by searching `### Phase 21: SDET authoring docs + README parity` and contents are unchanged.
  </action>
  <verify>
    <automated>powershell -NoProfile -Command "$f='.planning/ROADMAP.md'; $t=Get-Content $f -Raw; $checks=@{'no requires_homelab'=(($t -match 'requires_homelab') -eq $false); 'no PREFLIGHT-01'=(($t -match 'PREFLIGHT-01') -eq $false); 'no PREFLIGHT-02'=(($t -match 'PREFLIGHT-02') -eq $false); 'phase20 milestone bullet rewritten'=($t -match 'Phase 20: v1\.3 scope correction'); 'phase20 details heading'=($t -match '### Phase 20: v1\.3 scope correction --- dogfood cleanup' -or $t -match '### Phase 20: v1\.3 scope correction — dogfood cleanup'); 'has CLEANUP-DOGFOOD-01'=($t -match 'CLEANUP-DOGFOOD-01'); 'has CODEGEN-COVERAGE-01'=($t -match 'CODEGEN-COVERAGE-01'); 'has REQ-SCRUB-01'=($t -match 'REQ-SCRUB-01'); 'phase21 untouched'=($t -match '### Phase 21: SDET authoring docs \+ README parity'); 'phase17 untouched'=($t -match '### Phase 17: Schema-driven codegen surface'); 'phase19 untouched'=($t -match '### Phase 19: Stateful primitives \+ domain UI integration')}; $fail=0; foreach($k in $checks.Keys){ if(-not $checks[$k]){ Write-Host \"FAIL: $k\"; $fail=1 } else { Write-Host \"OK: $k\" } }; exit $fail"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'requires_homelab' .planning/ROADMAP.md` returns `0`.
    - `grep -c 'PREFLIGHT-0[12]' .planning/ROADMAP.md` returns `0`.
    - `grep -c '^### Phase 20: v1.3 scope correction' .planning/ROADMAP.md` returns `1`.
    - `grep -c '^### Phase 21: SDET authoring docs' .planning/ROADMAP.md` returns `1` (Phase 21 still intact).
    - `grep -c '^### Phase 17: Schema-driven codegen surface' .planning/ROADMAP.md` returns `1`.
    - `grep -c '^### Phase 19: Stateful primitives' .planning/ROADMAP.md` returns `1`.
    - Phase 20 milestone bullet line begins with `- [ ] **Phase 20: v1.3 scope correction` (still marked open, not checked).
    - The three new requirement IDs each appear at least once in ROADMAP.md.
  </acceptance_criteria>
  <done>ROADMAP.md Phase 20 milestone bullet and Phase Details block both reflect the reframed scope. Surrounding phase entries unchanged. Zero `requires_homelab` or `PREFLIGHT-0X` references survive.</done>
</task>

</tasks>

<verification>
After this plan completes, `.planning/ROADMAP.md` no longer mentions `requires_homelab` or PREFLIGHT-01/02. The Phase 20 entry's Goal + Success Criteria + Requirements line all reflect CONTEXT.md D-13.
</verification>

<success_criteria>
- Phase 20 ROADMAP entry tells future readers exactly what this phase delivers (cleanup + mock-fixture codegen tests + REQ scrub).
- No stale `requires_homelab` language remains.
- Adjacent phase entries untouched.
</success_criteria>

<output>
After completion, create `.planning/phases/20-preflight-conditional-skip/20-02-SUMMARY.md`.
</output>
