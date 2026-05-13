---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Homelab Scenario Testing
status: executing
stopped_at: Phase 18 context gathered
last_updated: "2026-05-13T07:02:06.855Z"
last_activity: 2026-05-13
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 14
  completed_plans: 12
  percent: 86
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-12 after v1.2 milestone close)

**Core value:** A `pytest`-runnable test suite that exercises one MCP tool end-to-end (schema → call → judge) and exits non-zero on any failure — proving the framework's integration contract before adding breadth.
**Current focus:** Phase 18 — sdet-test-surface-typed-errors

## Current Position

Phase: 18 (sdet-test-surface-typed-errors) — EXECUTING
Plan: 3 of 8
Status: Ready to execute
Last activity: 2026-05-13

## Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| v1.0 closing metrics (reference) | 7 phases / 22 plans / 29 reqs | shipped 2026-05-06 |
| v1.1 closing metrics (reference) | 6 phases / 17 plans / 25 reqs | shipped 2026-05-08 |
| v1.2 closing metrics | 5 phases / 30 plans / 31 reqs | shipped 2026-05-12 |
| v1.2 source diff | +37,100 / −1,928 across 168 files | doc churn + tests dominate |
| v1.2 timeline | 4 days (2026-05-09 → 2026-05-12) | 236 commits in range |
| v1.2 quick tasks | 1 (260512-dcs) | CLEAN-03 closure via audit |
| v1.3 scoping metrics | 5 phases / 21 reqs / plans TBD | roadmap created 2026-05-12 |
| Cross-milestone totals (shipped) | 18 phases / 69 plans / 85 reqs | all satisfied at milestone close |
| Phase 18 P03 | 365 | 1 tasks | 4 files |
| Phase 18 P04 | 51 | 1 tasks | 1 files |

## Accumulated Context

### Decisions

Full decision log lives in PROJECT.md "Key Decisions" table (with outcomes assessed at v1.0 + v1.1 close).

**v1.2 roadmapping decisions (2026-05-09):**

- **Phase 12 (CLEAN + PERSONA merged) lands first.** SEED-009 says "FIRST in v1.2" for doc cleanup — foundational hygiene that other phases benefit from (clean docs not churned twice). SEED-007 says "Surface FIRST during milestone framing — cheap to land but expensive to retrofit." Both are doc-heavy and small; merging avoids the overhead of two near-trivial phases. The merged phase still passes the "complete capability" test: an operator browsing a clean repo with a runnable scaffold and persona-correct docs is a coherent verifiable outcome.
- **Phase 13 (SAFE) is the semantic core.** Riskiest single chunk because of the schema v1→v2 migration + opt-in inversion + dropping `.env`. Lands after Phase 12 so the missing-config error and the v1→v2 migration error can both reference the now-complete `config-init` scaffold from CLEAN-05.
- **Phase 14 (RUNNER) before Phase 15 (SURFACE) — explicit user decision locked at scoping.** SEED-011: "Decide BEFORE SEED-010 folder split." The runner contract drives what the folder split needs to support; reversing the order would make the folder split speculative.
- **Phase 16 (UX) lands last.** SEED-008: "Land AFTER SEED-006 (semantics) and SEED-009 (doc cleanup), since this is the UX layer over the new semantics." UX-03 explicitly subsumes v1.1's `_reporter.py`, which RUNNER-01 may obsolete entirely — sequencing UX after RUNNER lets the reporter rebuild rather than be ported.
- **5 phases for 31 reqs.** Comparable density to v1.1 (6 phases / 25 reqs). Phase 12 is intentionally larger (9 reqs) because CLEAN+PERSONA is mostly mechanical doc work; Phase 13 (7 reqs) is the heaviest single technical chunk (schema migration). No phase is a "feature half" — each delivers a coherent operator-perceivable capability.
- **Granularity = standard.** v1.1's "coarse" justification (each phase genuinely separable) holds here too; calibrated 5 phases without padding or compression.
- **No v1.3+ work in v1.2.** xdist (SEED-002), OpenAI-compat backend (SEED-005), warm-up stage all deferred per scoping decision. v1.2 = operator-first foundations.

**v1.3 roadmapping decisions (2026-05-12):**

- **Pivot from "performance + portability" to "SDET + stateful primitives".** v1.2 close + operator pain-point clarification ("manually testing through the Claude client is time-consuming") reframed the v1.3 driver. The originally-pencilled xdist + OpenAI-compat cohort is real, but it deepens the existing contract-validation product; SDET + state opens a new persona (SDET) and unblocks coverage of stateful homelab-mcp tools (VM lifecycle, etc.) that the contract-rubric model can't exercise meaningfully. SEED-014 + SEED-004 pulled forward from `target_milestone: v2.0+`; SEED-015 (library mode) deferred to v1.4 so the SDET surface stabilizes on CLI first. SEED-005/SEED-003 carry to v1.4–v1.5.
- **Phase 17 (CODEGEN) lands first.** Every downstream phase imports from the generated `<ToolName>Params` / `<ToolName>Response` classes (`tool("name").call(params)`). Without codegen, the SDET surface in Phase 18 is stringly-typed and the STATE dogfood in Phase 19 has no typed response object to pass through module-scope fixtures. CODEGEN is the structural seam the other phases hang off.
- **Phase 18 (SDET surface + UI-02 typed error) bundles the API and the typed-error class.** `ToolCallError` is raised by the call wrapper built in this phase and consumed by both contract and SDET paths — keeping it with the wrapper avoids a v1.3.1 retrofit. SDET-01..04 + UI-02 together = "the SDET can write a test and see structured failure detail."
- **Phase 19 (STATE + UI-01) bundles primitives with their first visible consumer.** STATE-01..04 alone is paperwork (yield-fixture pattern doc); STATE-01..04 + UI-01 + a shipping VM-lifecycle scenario = "stateful testing is observably real in the operator UI." Avoids the SEED-004 "half-product" trap explicitly flagged in the seed.
- **Phase 20 (PREFLIGHT) is a small standalone phase.** PREFLIGHT-01..02 are dependency-light (just need the `mcp_test_framework.sdet` namespace from Phase 18); could in principle run in parallel with Phase 19 by the planner. Kept as its own phase because the capability ("clean operator-domain SKIP when env is absent") is verifiable independently, and folding it into Phase 19 would have made that phase a 7-req grab-bag.
- **Phase 21 (DOC-SDET) lands last per the v1.2 Phase 12/16 precedent.** Docs after the surface stabilizes, not against a moving target. DOC-SDET-03 (README char-for-char parity) literally cannot land before Phase 19 ships the renderer integration.
- **5 phases for 21 reqs.** Comparable density to v1.0 (5 reqs/phase) and v1.2 (6 reqs/phase). v1.3 = 4.2 reqs/phase, slightly lower density because Phase 20 is intentionally small (2 reqs) and Phase 21 is a 3-req doc capstone. No phase is a "feature half".
- **Granularity = coarse (per config.json).** Each phase delivers a coherent SDET- or operator-perceivable capability; no phase is splittable without losing coherence. Phase 17 (codegen) is the technically heaviest single chunk because the codegen library choice + Pydantic-from-JSON-Schema + idempotent regen + ToolResponse uniformity are all interlocking.
- **Carry-forward debt:** Phase 13 + 14 live-stack UATs from v1.2 will close opportunistically during v1.3 — the SDET runs against live homelab-mcp + Proxmox + Ollama are the same live-stack exercise those UATs were waiting on. Phase 16 D-11 `--debug` per-judge breakdown remains deferred to v1.5 (cohort with SEED-003); v1.3 does NOT pick it up.

**v1.2 plan-checks (preserved from v1.2 milestone):**

- [Phase ?]: Plan 16-01: _compose_pre_run_skip_reasons filters state-b via computed running set (Rule 1 deviation; smoke-test contract wins)
- [Phase ?]: Plan 16-01: render_domain_ui no longer emits banner; two verbosity CLI e2e tests temporarily flipped to banner-ABSENCE until 16-02 wires pre-run digest
- [Phase ?]: Plan 16-02: --explain owned by Typer wrapper, never forwarded to pytest (D-07 enforced by subprocess stub assert)
- [Phase ?]: Plan 16-02: pre-run RenderContext built before subprocess (total_planned_cases=0), rebuilt post-parse with parsed.total_cases for summary line
- [Phase ?]: Plan 16-02: Phase 14 D-14 negative test renamed in place preserving the regression breadcrumb (test_run_help_lists_explain_phase16)
- [Phase 16]: Plan 16-03: README documents Phase 16 pre-run digest + --explain composition matrix + Phase 16 sample green run
- [Phase 16]: Plan 16-03: docs/mcp_test_framework_mvp_spec.md zero-diff (intentional) — spec is MVP design contract, not operator CLI output reference
- [Phase ?]: Mirror renderer output literally in docs — README sample blocks quote what _runner.py emits char-for-char, including whitespace quirks.
- [Phase ?]: Plan 18-03 mcp_session fixture: Rule 3 deviation added public McpTestClient.server_info accessor (mcp SDK's ClientSession discards InitializeResult.serverInfo after caching only _server_capabilities)

### Roadmap Evolution

- 2026-05-13: Phase 22 added — scrub requirement-ID leaks from `src/` (5 user-visible CLI docstrings + 58 internal references). Surfaced during Phase 17 live UAT when `mcp-test-framework --help` exposed `CLI-01`/`PERSONA-02`/`CODEGEN-01`-style tags. Source-code analog of the v1.2 doc scrub. v1.3 milestone range extended from Phases 17–21 to Phases 17–22.

### Blockers/Concerns

None at roadmap stage. Open design questions captured in REQUIREMENTS.md (CLI surface for `gen-sdet-classes`, generated-file location, server-slug derivation, `requires_homelab` location, `tool()` vs attribute-access idiom, stub vs alias for outputSchema-undeclared responses) are deferred to plan-phase decisions, not roadmap blockers.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260506-qxs | Diagnostic spike — homelab-mcp host-state surface (recon for v1.1 isolation) | 2026-05-07 | 23cc6e1 | [260506-qxs-diagnostic-spike-identify-what-user-visi](./quick/260506-qxs-diagnostic-spike-identify-what-user-visi/) |
| 260507-j6i | Enrich `MCP server command not on PATH` error with MCPTF_CONFIG_FILE / config.example.yaml hint | 2026-05-07 | bfc1e65 | [260507-j6i-enrich-mcp-server-not-on-path-error-with](./quick/260507-j6i-enrich-mcp-server-not-on-path-error-with/) |
| 260507-n0g | Safe-by-default tool skips in `config.example.yaml` (55 new skip entries; only `list_keyring_credentials` + `suggest_deployments` enabled) | 2026-05-07 | 0d8337b | [260507-n0g-safe-by-default-tool-skips](./quick/260507-n0g-safe-by-default-tool-skips/) |
| 260508-p0b | v1.1.1 hotfix: filter `tools.<name>.skip:true` at parametrize time so skipped tools are absent from collection (not runtime-SKIPPED 10x each); 691 → 133 collected under config.example.yaml | 2026-05-08 | 509daee | [260508-p0b-fix-v1-1-skip-doesnt-filter-parametrize-](./quick/260508-p0b-fix-v1-1-skip-doesnt-filter-parametrize-/) |
| 260512-dcs | Migrate example configs to schema v2 (closes CLEAN-03 BLOCKER from v1.2 milestone audit; examples/homelab-mcp.yaml + config.example.yaml flipped to `version: 2`, `.env` precedence comment stripped) | 2026-05-12 | 814d743 | [260512-dcs-flip-example-config-version-1-to-2-close](./quick/260512-dcs-flip-example-config-version-1-to-2-close/) |

## Deferred Items

Items acknowledged at v1.0 / v1.1 close and carried into v1.2+ scope:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| upstream-fix | `homelab-mcp` `list_registered_servers` description rewrite (would let TEST-06 pass against the original target tool) | Open | v1.0 close (2026-05-07) |
| testing-scaffold | Automated cross-platform SIGINT UAT (Get-Process / pgrep + programmatic SIGINT helper) | Open | v1.0 close (2026-05-07) |
| open-source-prep | Scrub homelab IP from README (05-SECURITY.md AR-05-12) | Partially absorbed into v1.2 Phase 12 (CLEAN-02..04) | v1.0 close (2026-05-07) |
| open-source-prep | Scrub homelab-specific captures from `.planning/` (05-SECURITY.md AR-05-15) | Open — only triggers if/when repo goes public | v1.0 close (2026-05-07) |
| process-hygiene | Backfill 04.1-VERIFICATION.md (UAT.md status:complete is current evidence of record) | Open — optional | v1.0 close (2026-05-07) |
| seed | SEED-001 — Replace rubric-style judge with full agent tool-use loop | dormant | v1.1 close (2026-05-08) |
| seed | SEED-002 — Tool-level parallelism via pytest-xdist with read/write resource markers | dormant — v1.4 cohort | v1.1 close (2026-05-08) |
| seed | SEED-003 — Dynamic judging protocol — rubrics as data, not code | dormant — v1.5 | v1.1 close (2026-05-08) |
| seed | SEED-004 — Stateful tool testing with resource setup/teardown | activated → Phase 19 (v1.3) | v1.1 close (2026-05-08) |
| seed | SEED-005 — OpenAI-compatible judge backend as the unifier (local-first / hosted-opt-in) | dormant — v1.4 or v1.5 | v1.1 close (2026-05-08) |
| seed | SEED-006 — Config loading safety + opt-in tool selection | activated → Phase 13 (v1.2) | 2026-05-09 (v1.2 framing) |
| seed | SEED-007 — Vibe-coded MCP user persona reframe | activated → Phase 12 (v1.2) | 2026-05-09 (v1.2 framing) |
| seed | SEED-008 — Reporter UX overhaul — pre-run digest + --explain flag | activated → Phase 16 (v1.2) | 2026-05-09 (v1.2 framing) |
| seed | SEED-009 — Doc & example cleanup phase (v1.2) | activated → Phase 12 (v1.2) | 2026-05-09 (v1.2 framing) |
| seed | SEED-010 — Separate operator-facing tests from framework self-tests | activated → Phase 15 (v1.2) | 2026-05-09 (v1.2 framing) |
| seed | SEED-011 — Hybrid runner with domain-language UI | activated → Phase 14 (v1.2) | 2026-05-09 (v1.2 framing) |
| seed | SEED-014 — Programmatic SDET test authoring (param/response classes + scenario API) | activated → Phases 17–21 (v1.3) | 2026-05-12 (v1.3 framing) |
| seed | SEED-015 — Library mode / pytest plugin delivery | dormant — v1.4 (post-SDET-stabilization) | 2026-05-12 (v1.3 framing) |
| defer | Phase 16 D-11 `--debug` per-judge breakdown block | dormant — v1.5 cohort with SEED-003 | v1.2 close (2026-05-12) |
| live-uat | Phase 13 live-stack UAT (v2 config + migration walkthrough) | Open — closes opportunistically during v1.3 | v1.2 close (2026-05-12) |
| live-uat | Phase 14 live-stack UAT (test_runner_live_smoke.py + visual domain UI checks) | Open — closes opportunistically during v1.3 | v1.2 close (2026-05-12) |
| docs-polish | EXTENDING.md WR-01: line-range citation `_isolation.py:33-36` should be `36-39` (11-REVIEW.md) | Absorbed into Phase 12 (CLEAN-01 sweep) | v1.1 close (2026-05-08) |
| docs-polish | EXTENDING.md IN-01: "five entries" framing for `_PASSTHROUGH_ALLOWLIST` (4-tuple + separate `_MCP_PREFIX`) (11-REVIEW.md) | Absorbed into Phase 12 (CLEAN-01 sweep) | v1.1 close (2026-05-08) |

## Session Continuity

Last session: 2026-05-13T07:02:06.847Z
Stopped at: Phase 18 context gathered
Resume next: `/gsd-plan-phase 17`
