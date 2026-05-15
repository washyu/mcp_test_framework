---
phase: 20-preflight-conditional-skip
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/STATE.md
autonomous: true
requirements:
  - REQ-SCRUB-01
must_haves:
  truths:
    - "STATE.md Decisions section records the Phase 20 reframe rationale"
    - "STATE.md Deferred Items table shows Phase 19 D-02 (CPU-cores bump impossible) as Resolved-by-deletion (Phase 20)"
    - "STATE.md Deferred Items table contains a new entry for 'hello-world MCP server for CI' (deferred to a future phase)"
    - "STATE.md upstream-fix entry for homelab-mcp inputSchema bug is unchanged (still Open)"
    - "Current Position / Last activity reflects that Phase 20 was reframed during discuss-phase"
  artifacts:
    - path: ".planning/STATE.md"
      provides: "Project state reflecting Phase 20 reframe and Phase 19 D-02 resolution"
      contains: "Resolved-by-deletion (Phase 20)"
  key_links:
    - from: ".planning/STATE.md (Deferred Items)"
      to: ".planning/phases/20-preflight-conditional-skip/20-CONTEXT.md (D-05)"
      via: "Resolved-by-deletion entry"
      pattern: "Resolved-by-deletion \\(Phase 20\\)"
---

<objective>
Update `.planning/STATE.md` to reflect the Phase 20 reframe: record the architectural decision under Decisions; mark Phase 19 deferred D-02 as Resolved-by-deletion; add a new deferred-items entry for the hello-world MCP CI fixture; leave the upstream homelab-mcp inputSchema entry untouched.

Purpose: STATE.md is the canonical "what's open / what's decided" reference for future planning agents. The reframe needs to be visible here so /gsd-plan-phase 21 (and beyond) reads the correct context.
Output: Updated `.planning/STATE.md`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/20-preflight-conditional-skip/20-CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update STATE.md Decisions block, Deferred Items table, and Last activity</name>
  <files>.planning/STATE.md</files>
  <read_first>
    - .planning/STATE.md (full file — note exact line positions of: Decisions section, Deferred Items table, Current Position block, Last activity line)
    - .planning/phases/20-preflight-conditional-skip/20-CONTEXT.md (D-01..D-13, especially D-05 and the <deferred> "Hello-world MCP server" entry)
  </read_first>
  <action>
Make THREE coordinated edits to `.planning/STATE.md` in this single task.

**Edit 1 — Append a Phase 20 reframe entry to the Decisions section.**

Find the existing `### Decisions` heading and the chronological decision blocks under it (the most recent one is the `**v1.3 roadmapping decisions (2026-05-12):**` block). Immediately AFTER the last bullet of that v1.3 block (the one ending with "...Phase 16 D-11 `--debug` per-judge breakdown remains deferred to v1.5 (cohort with SEED-003); v1.3 does NOT pick it up."), insert a blank line and then the following new block:

```
**v1.3 mid-flight reframe (Phase 20 discuss-phase, 2026-05-13):**

- **Phase 20 pivots from PREFLIGHT to scope correction.** Original Phase 20 goal ("`requires_homelab(...)` marker factory") was rejected during discuss-phase as a violation of the framework-primitives principle (SEED-022) — it bakes SUT-specific subsystem knowledge (`proxmox=`, `ollama=`) into the framework's API surface. The framework wraps tool calls (params/body/results) and nothing else; reachability checks belong to the SDET's test code via stock `@pytest.mark.skipif(not _probe(), reason=...)`.
- **Three Phase 20 deliverables replace the killed work.** (1) Delete `tests/sdet/test_proxmox_vm_lifecycle.py` outright — the Phase 19 dogfood is SUT-aware and can't run in CI without operator-specific Proxmox creds; the architectural patterns survive in Phase 19's CONTEXT/SUMMARY artifacts for Phase 21 docs to lift. (2) Drop PREFLIGHT-01/02 from REQUIREMENTS.md; replace with CLEANUP-DOGFOOD-01 + CODEGEN-COVERAGE-01 + REQ-SCRUB-01 reflecting the actual deliverables. (3) Add mock-fixture-driven codegen unit tests under `tests/framework/unit/` that feed a synthetic tool list through the codegen pipeline and assert the generated Params/Response/registry artifacts have the correct shape — pure-data, no live MCP, CI-safe.
- **Zero `src/` changes.** The reframe's load-bearing claim is that if the framework had to grow new code to satisfy `requires_homelab`, the requirement was wrong — not the implementation. Phase 20 ships only test-suite + planning-doc edits.
- **Hello-world MCP server for CI deferred.** A tiny in-tree MCP server with hand-crafted tools (covers required/optional params, scalars/arrays, declared/undeclared outputSchema) would let CI run a real end-to-end "every discovered tool gets wrapped" pass. User explicitly said "out of scope for now" but flagged the need — captured as a deferred item (see Deferred Items table).
- **v1.3 REQ count goes 21 → 22 (not 19 as the user initially estimated).** PREFLIGHT-01/02 removed (−2), but three new IDs added (+3). Phase coverage summary table reflects the net change.
```

**Edit 2 — Update the Deferred Items table.**

Find the table that starts with `| Category | Item | Status | Deferred At |`. Make these row-level edits:

(a) ADD a new row at the bottom of the table (after the last existing `docs-polish` row for EXTENDING.md IN-01):

```
| seed-defer | Hello-world MCP server for CI/CD coverage — tiny in-tree MCP with hand-crafted tools (required/optional params, scalars/arrays, declared/undeclared outputSchema) lets CI run a real end-to-end "every discovered tool gets wrapped" pass without operator infrastructure. | Open — future v1.x phase | Phase 20 reframe (2026-05-13) |
| deferred-resolved | Phase 19 D-02 (CPU-cores bump impossible via `manage_proxmox_vm` lifecycle-action-only tool) — defer to Phase 20 substitution decision | Resolved-by-deletion (Phase 20) — the dogfood file hosting the substitution was deleted in Phase 20 per D-04; no substitution needed | v1.3 Phase 19 close → resolved Phase 20 (2026-05-13) |
```

(b) The existing `upstream-fix` row for the homelab-mcp inputSchema bug (the one mentioning `create_proxmox_vm` / `'Input validation error: None is not of type 'string'`) is UNCHANGED. Do NOT delete or modify it.

**Edit 3 — Update the Current Position / Last activity block.**

Find the YAML-style frontmatter at the top of STATE.md (between the two `---` lines). Update these fields:

- `stopped_at:` — change from `Phase 20 context gathered (reframed)` to `Phase 20 planned (reframed scope: cleanup + mock-fixture codegen tests)`
- `last_updated:` — set to the current ISO-8601 UTC timestamp at edit time (use `Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"` in PowerShell or equivalent — value must be a valid ISO-8601 with `Z` suffix; do not hand-pick a date)
- `last_activity:` — change to `2026-05-13 -- Phase 20 reframed; PLAN files written for cleanup + mock-fixture codegen coverage; src/ untouched`

Then in the `# Project State` body, find the `## Current Position` section. Update:
- The `Phase: 19 ...` line stays (Phase 19 is still the most recently completed phase).
- The `Next:` line currently reads `Next: Phase 20 (PREFLIGHT) — \`requires_homelab\` marker; record upstream homelab-mcp bug as deferred-items entry.` — REPLACE with: `Next: Phase 20 (scope correction) — execute the four PLAN files written 2026-05-13 (REQUIREMENTS scrub, ROADMAP rewrite, STATE update [this plan], tests/sdet cleanup, mock-fixture codegen tests).`
- The `Last activity:` line — REPLACE with: `Last activity: 2026-05-13 -- Phase 20 reframed; PLAN files written for cleanup + mock-fixture codegen coverage; src/ untouched`

Find the `## Session Continuity` block at the very bottom. Update:
- `Last session:` — set to a fresh ISO-8601 UTC timestamp matching the frontmatter `last_updated`.
- `Stopped at:` — change to `Phase 20 planned (reframed scope)`
- `Resume next:` — change to `\`/gsd-execute-phase 20\` to run the reframed cleanup + mock-fixture codegen plans`

Make no other edits to STATE.md. Do NOT modify Performance Metrics, Quick Tasks Completed, Roadmap Evolution, or Blockers/Concerns sections.

Invariants to satisfy:
- The `requires_homelab` string only appears inside the new "v1.3 mid-flight reframe" decision block (as part of the historical narrative explaining what was rejected). It does NOT appear in the Current Position or Next lines or as a live commitment.
- Both new Deferred Items rows are present.
- The original upstream-fix homelab-mcp inputSchema row is preserved verbatim.
  </action>
  <verify>
    <automated>powershell -NoProfile -Command "$f='.planning/STATE.md'; $t=Get-Content $f -Raw; $checks=@{'reframe block present'=($t -match 'v1\.3 mid-flight reframe \(Phase 20 discuss-phase'); 'phase19 d02 resolved row'=($t -match 'Resolved-by-deletion \(Phase 20\)'); 'hello-world MCP deferred row'=($t -match 'Hello-world MCP server for CI/CD coverage'); 'upstream inputSchema bug preserved'=($t -match 'create_proxmox_vm.*Input validation error' -or ($t -match 'create_proxmox_vm' -and $t -match 'Input validation error')); 'next line updated'=($t -match 'Next: Phase 20 \(scope correction\)'); 'stopped_at updated'=($t -match 'stopped_at: Phase 20 planned'); 'no live requires_homelab commitment'=(($t -match 'Resume next.*requires_homelab') -eq $false); 'session continuity points at execute-phase 20'=($t -match 'Resume next: ``/gsd-execute-phase 20`' -or $t -match 'Resume next: `/gsd-execute-phase 20`')}; $fail=0; foreach($k in $checks.Keys){ if(-not $checks[$k]){ Write-Host \"FAIL: $k\"; $fail=1 } else { Write-Host \"OK: $k\" } }; exit $fail"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'v1.3 mid-flight reframe' .planning/STATE.md` returns `1`.
    - `grep -c 'Resolved-by-deletion (Phase 20)' .planning/STATE.md` returns at least `1`.
    - `grep -c 'Hello-world MCP server for CI/CD coverage' .planning/STATE.md` returns `1`.
    - `grep -c 'create_proxmox_vm' .planning/STATE.md` returns at least `1` (the original upstream-fix row is preserved).
    - `grep -c 'Next: Phase 20 (scope correction)' .planning/STATE.md` returns `1`.
    - `grep -c 'requires_homelab' .planning/STATE.md` returns at most a small number (only inside the historical narrative of the reframe decision block — NOT in the Current Position or Next line or Resume next line).
    - The frontmatter `stopped_at:` field contains "Phase 20 planned".
    - The `Resume next:` line references `/gsd-execute-phase 20`.
  </acceptance_criteria>
  <done>STATE.md Decisions block records the reframe; Deferred Items table marks Phase 19 D-02 as Resolved-by-deletion and adds the hello-world MCP entry; Current Position / Next / Last activity / Session Continuity all point at Phase 20 execution; the upstream homelab-mcp inputSchema entry is unchanged.</done>
</task>

</tasks>

<verification>
After this plan: STATE.md reflects the reframe (Decisions block), the resolution of Phase 19 D-02 (Deferred Items row), the new hello-world MCP deferred item, and the current execution position pointing at Phase 20.
</verification>

<success_criteria>
- Future planning agents reading STATE.md see the reframe explicitly recorded under Decisions.
- The Phase 19 D-02 deferred item is no longer "Open" — it's marked Resolved-by-deletion.
- The hello-world MCP CI fixture is tracked as a known-future-work item.
- The upstream homelab-mcp inputSchema bug entry is preserved as Open (still an upstream concern, not a framework concern).
</success_criteria>

<output>
After completion, create `.planning/phases/20-preflight-conditional-skip/20-03-SUMMARY.md`.
</output>
