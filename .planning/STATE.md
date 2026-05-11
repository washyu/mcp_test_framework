---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Operator-First Design
status: verifying
stopped_at: Phase 15 context gathered
last_updated: "2026-05-11T20:16:03.880Z"
last_activity: 2026-05-11 -- Phase 13 UAT complete (2/2 pass); SAFE-01 opt-in semantics + v1→v2 migration walkthrough both confirmed by operator
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 21
  completed_plans: 21
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-08 after v1.1 milestone close)

**Core value:** A `pytest`-runnable test suite that exercises one MCP tool end-to-end (schema → call → judge) and exits non-zero on any failure — proving the framework's integration contract before adding breadth.
**Current focus:** Between phases — Phase 15 (operator vs framework test surface split) is next

## Current Position

Phase: — (between phases; Phase 14 complete, Phase 15 not started)
Plan: —
Status: All planned plans in v1.2 phases 12-14 complete and human-verified
Last activity: 2026-05-11 -- Phase 13 UAT complete (2/2 pass); SAFE-01 opt-in semantics + v1→v2 migration walkthrough both confirmed by operator

## Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Phases planned | 5 | 12, 13, 14, 15, 16 |
| Phases complete | 0 | |
| Requirements scoped | 31 | All v1.2 reqs mapped 1:1 to phases (no orphans) |
| Requirements complete | 0 | |
| v1.1 closing metrics (reference) | 6 phases / 17 plans / 25 reqs | shipped 2026-05-08 |

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
- **No v1.3+ work in v1.2.** xdist (SEED-002), OpenAI-compat backend (SEED-005), warm-up stage all deferred to v1.3 per scoping decision. v1.2 = operator-first foundations; v1.3 = performance + portability.

### Blockers/Concerns

None at roadmap stage. Open design questions captured in REQUIREMENTS.md (e.g., RUNNER-01's subprocess-vs-`pytest.main` choice, RUNNER-03's `--raw` flag name) are deferred to plan-phase decisions, not roadmap blockers.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260506-qxs | Diagnostic spike — homelab-mcp host-state surface (recon for v1.1 isolation) | 2026-05-07 | 23cc6e1 | [260506-qxs-diagnostic-spike-identify-what-user-visi](./quick/260506-qxs-diagnostic-spike-identify-what-user-visi/) |
| 260507-j6i | Enrich `MCP server command not on PATH` error with MCPTF_CONFIG_FILE / config.example.yaml hint | 2026-05-07 | bfc1e65 | [260507-j6i-enrich-mcp-server-not-on-path-error-with](./quick/260507-j6i-enrich-mcp-server-not-on-path-error-with/) |
| 260507-n0g | Safe-by-default tool skips in `config.example.yaml` (55 new skip entries; only `list_keyring_credentials` + `suggest_deployments` enabled) | 2026-05-07 | 0d8337b | [260507-n0g-safe-by-default-tool-skips](./quick/260507-n0g-safe-by-default-tool-skips/) |
| 260508-p0b | v1.1.1 hotfix: filter `tools.<name>.skip:true` at parametrize time so skipped tools are absent from collection (not runtime-SKIPPED 10x each); 691 → 133 collected under config.example.yaml | 2026-05-08 | 509daee | [260508-p0b-fix-v1-1-skip-doesnt-filter-parametrize-](./quick/260508-p0b-fix-v1-1-skip-doesnt-filter-parametrize-/) |

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
| seed | SEED-002 — Tool-level parallelism via pytest-xdist with read/write resource markers | dormant — v1.3 cohort | v1.1 close (2026-05-08) |
| seed | SEED-003 — Dynamic judging protocol — rubrics as data, not code | dormant | v1.1 close (2026-05-08) |
| seed | SEED-004 — Stateful tool testing with resource setup/teardown | dormant | v1.1 close (2026-05-08) |
| seed | SEED-005 — OpenAI-compatible judge backend as the unifier (local-first / hosted-opt-in) | dormant — v1.3 cohort | v1.1 close (2026-05-08) |
| seed | SEED-006 — Config loading safety + opt-in tool selection | activated → Phase 13 | 2026-05-09 (v1.2 framing) |
| seed | SEED-007 — Vibe-coded MCP user persona reframe | activated → Phase 12 | 2026-05-09 (v1.2 framing) |
| seed | SEED-008 — Reporter UX overhaul — pre-run digest + --explain flag | activated → Phase 16 | 2026-05-09 (v1.2 framing) |
| seed | SEED-009 — Doc & example cleanup phase (v1.2) | activated → Phase 12 | 2026-05-09 (v1.2 framing) |
| seed | SEED-010 — Separate operator-facing tests from framework self-tests | activated → Phase 15 | 2026-05-09 (v1.2 framing) |
| seed | SEED-011 — Hybrid runner with domain-language UI | activated → Phase 14 | 2026-05-09 (v1.2 framing) |
| docs-polish | EXTENDING.md WR-01: line-range citation `_isolation.py:33-36` should be `36-39` (11-REVIEW.md) | Absorbed into Phase 12 (CLEAN-01 sweep) | v1.1 close (2026-05-08) |
| docs-polish | EXTENDING.md IN-01: "five entries" framing for `_PASSTHROUGH_ALLOWLIST` (4-tuple + separate `_MCP_PREFIX`) (11-REVIEW.md) | Absorbed into Phase 12 (CLEAN-01 sweep) | v1.1 close (2026-05-08) |

## Session Continuity

Last session: 2026-05-11T20:16:03.872Z
Stopped at: Phase 15 context gathered
Resume next: `/gsd-plan-phase 12`
