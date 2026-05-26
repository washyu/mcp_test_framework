---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Shim Retirement + Operator Escape Hatches
status: executing
stopped_at: Phase 33 context gathered
last_updated: "2026-05-26T18:48:59.389Z"
last_activity: 2026-05-26 -- Phase 33 execution started
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 18
  completed_plans: 17
  percent: 94
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22 after v1.4 milestone close)

**Core value:** A `pytest`-runnable test suite — now an importable pytest plugin (`mcp-contracts`) — that exercises every MCP tool end-to-end (schema → call → judge) for the operator persona AND lets an SDET author typed scenario tests against the same MCP server for stateful coverage; exits non-zero on any failure, no SUT-specific code in framework `src/` (SEED-022).
**Current focus:** Phase 33 — per-bucket-skip-granularity-in-toolconfig-999-1

## Current Position

Phase: 33 (per-bucket-skip-granularity-in-toolconfig-999-1) — EXECUTING
Plan: 1 of 6
Status: Executing Phase 33
Last activity: 2026-05-26 -- Phase 33 execution started

## Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| v1.0 closing metrics (reference) | 7 phases / 22 plans / 29 reqs | shipped 2026-05-06 |
| v1.1 closing metrics (reference) | 6 phases / 17 plans / 25 reqs | shipped 2026-05-08 |
| v1.2 closing metrics | 5 phases / 30 plans / 31 reqs | shipped 2026-05-12 |
| v1.2 source diff | +37,100 / −1,928 across 168 files | doc churn + tests dominate |
| v1.2 timeline | 4 days (2026-05-09 → 2026-05-12) | 236 commits in range |
| v1.2 quick tasks | 1 (260512-dcs) | CLEAN-03 closure via audit |
| v1.3 closing metrics | 9 phases / 42 plans / 29 reqs | shipped 2026-05-15 |
| v1.4 closing metrics | 6 phases / 27 plans / 28 reqs (LIB-05 + CFG-02 removed by decision) | shipped 2026-05-22 |
| v1.4 source diff | +34,284 / −2,120 across 181 files | dominated by _plugin.py + _reporter.py + contracts/ + tests + docs rewrite |
| v1.4 timeline | 7 days (2026-05-15 → 2026-05-22) | 174 commits in range |
| v1.5 scoping metrics | 5 phases / 24 reqs / plans TBD | roadmap created 2026-05-23 |
| Cross-milestone totals (shipped) | 33 phases / 138 plans / 142 reqs | v1.0 + v1.1 + v1.2 + v1.3 + v1.4 |

## Accumulated Context

### Decisions

Full decision log lives in PROJECT.md "Key Decisions" table (with outcomes assessed at v1.0 + v1.1 + v1.2 + v1.3 + v1.4 close).

**v1.5 roadmapping decisions (2026-05-23):**

- **Phase numbering continues from v1.4 (Phase 30 → Phase 31).** No `--reset-phase-numbers` flag passed; continuous numbering across milestones preserved (v1.0=01-05, v1.1=06-11, v1.2=12-16, v1.3=17-24, v1.4=25-30, v1.5=31-35).
- **5 phases for 24 reqs.** Density 4.8 reqs/phase, comparable to v1.4 (4.7) and slightly higher than v1.3 (4.2). Granularity = coarse (per config.json). Phase 35 is intentionally a 1-req capstone — past precedent: v1.3 Phase 22 (4 plans / 1 SCRUB-SRC-01 req) and v1.0 OPS-03 capstone. The regression gate cannot semantically land until SHIM-01..08 + V1DROP-01..04 + BUCKET surfaces are all stable, so it earns its own phase rather than getting smuggled into the last feature phase.
- **Phase 31 (config-surface cleanup) bundles SHIM-04 + SHIM-05 + V1DROP-01..04.** SHIM-04 (`cfg.sdet.*` alias removal) and V1DROP-03 (validator tightening) share the `_validate_version` + `extra="forbid"` codepath; SHIM-05 (`MCPTF_CONFIG_FILE` removal) closes the env-var config-source story alongside the schema-version cleanup. V1DROP-04 self-test relaxation depends on V1DROP-03 validator changes AND on SHIM-04 alias removal (both alter the rejection-message surface). Cohesive single phase — operator's config-surface story settles in one shot.
- **Phase 32 (surface-shim removals) is the orthogonal mechanical phase.** SHIM-01 (sdet package import) + SHIM-02 (--sdet) + SHIM-03 (gen-sdet-classes) + SHIM-06 (tests/sdet discovery) + SHIM-07 (unprefixed fixtures) + SHIM-08 (mcp-test-framework console-script). All independent removals across import/CLI/discovery/fixture surfaces; each surfaces an operator-tone migration error. Lands after Phase 31 so the migration-error paths reference the cleaned config surface (post-V1DROP-03, no migration verbiage anywhere; post-SHIM-05, the no-env-var story is consistent across CLI + package).
- **Phase 33 (BUCKET 999.1) is orthogonal to SHIM/V1DROP.** Touches `ToolConfig` schema (new `skip_buckets` field), the parametrize hook (collection-time filtering — same hotfix pattern as v1.1.1 / 260508-p0b), and the reporter digest + `--explain` block. Docs included in same phase per v1.2 Phase 12 + v1.1 Phase 08 precedent (self-contained additive feature ships its docs alongside). Order between Phase 33 and Phase 34 is interchangeable; canonical 33→34 chosen so the smaller feature (5 reqs) lands first and the heavier audit-driven phase has a stable Pydantic surface to extend.
- **Phase 34 (ISOL 999.3) bundles audit + passthrough mode + docs.** ISOL-05 (bare `Config()` callers audit) is foundation work — identifies where the new `host_isolation` field needs to flow — landing alongside ISOL-01..04 (passthrough mode + xdist clamp) avoids a follow-up phase to remediate audit findings. ISOL-04 xdist clamp is preemptive (the framework doesn't yet use pytest-xdist; SEED-002 is explicitly out of v1.5 scope) — detect via `config.getoption('-n')` or `workerinput` in `pytest_configure`, refuse to run with operator-tone message; NOT actually running parallel.
- **Phase 35 (regression gate capstone) lands LAST.** SHIM-09 explicitly asserts zero matches across import + CLI + config + fixture + discovery surfaces; cannot pass until every other v1.5 phase ships. Past precedent for capstone phases: v1.0 Phase 05 (acceptance), v1.3 Phase 22 (scrub gate), v1.4 Phase 30 (CLI demotion + UAT closure).
- **Docs land in their owning phase, not a separate close phase.** v1.5 has no dedicated docs/close phase — V1DROP-01/02 docs in Phase 31, BUCKET-05 docs in Phase 33, ISOL-06 docs in Phase 34. The milestone is small enough (5 phases) and the docs are tightly coupled to each feature's surface; consolidating into a capstone docs phase would mean rewriting BUCKET + ISOL docs after Phase 35 changes nothing in those areas. Different shape from v1.2 Phase 16 / v1.3 Phase 21 / v1.4 Phase 30 (which had broader cross-cutting doc rewrites).
- **No new external dependencies.** All v1.5 work is within `mcp_test_framework` package + tests + docs.
- **Out of v1.5 (deferred to v1.6+):** SEED-002 (xdist parallelism — informs ISOL-04 clamp but not delivered), SEED-005 (OpenAI-compat judge backend), SEED-003 + Phase 16 D-11 (dynamic rubrics + per-judge breakdown), backlog 999.2 (codegen-driven param-test gen — pairs with Phase 33 BUCKET but scoped out), backlog 999.5 (self-test env pollution — likely re-surfaces during Phase 34 ISOL-05 audit; re-assess at v1.5 close). All explicitly captured in REQUIREMENTS.md "Future Requirements" section.

### Roadmap Evolution

- 2026-05-23: v1.5 ROADMAP.md created — 5 phases / 24 reqs (SHIM×9, BUCKET×5, ISOL×6, V1DROP×4). 100% coverage; no orphans. Phase numbering starts at 31. Phase 33 + Phase 34 nominally order-interchangeable (both depend only on Phase 31); canonical order 33→34. Phase 35 (regression gate) lands LAST per SHIM-09 dependency constraint.

### Blockers/Concerns

None at roadmap stage. Two design questions deferred to plan-phase decisions:

- **Phase 31 V1DROP-04 — delete vs relax self-tests.** REQUIREMENTS.md states "deleted or relaxed"; planner decides per-test whether the assertion has independent value (relax to operator-tone-error-shape) or is redundant with V1DROP-03's generic rejection (delete).
- **Phase 34 ISOL-04 xdist clamp mechanism.** Detect via `config.getoption('-n')` (CLI flag-driven) vs `workerinput` (worker-side fork detection) — both work; planner picks based on whichever fires earliest in the plugin lifecycle. Operator-tone message text + exit code policy (refuse-to-run vs warn-and-serialize) decided at plan time.

Open design questions deferred to plan-phase decisions (not roadmap blockers):

- Phase 33 BUCKET-02 collection-time filter integration with existing `pytest_generate_tests` hook (parametrize-list excision vs marker-based deselection).
- Phase 32 SHIM-07 unprefixed-fixture removal — clean delete vs error-surfacing stub fixture that raises operator-tone message at fixture-resolution time.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260506-qxs | Diagnostic spike — homelab-mcp host-state surface (recon for v1.1 isolation) | 2026-05-07 | 23cc6e1 | [260506-qxs-diagnostic-spike-identify-what-user-visi](./quick/260506-qxs-diagnostic-spike-identify-what-user-visi/) |
| 260507-j6i | Enrich `MCP server command not on PATH` error with MCPTF_CONFIG_FILE / config.example.yaml hint | 2026-05-07 | bfc1e65 | [260507-j6i-enrich-mcp-server-not-on-path-error-with](./quick/260507-j6i-enrich-mcp-server-not-on-path-error-with/) |
| 260507-n0g | Safe-by-default tool skips in `config.example.yaml` (55 new skip entries; only `list_keyring_credentials` + `suggest_deployments` enabled) | 2026-05-07 | 0d8337b | [260507-n0g-safe-by-default-tool-skips](./quick/260507-n0g-safe-by-default-tool-skips/) |
| 260508-p0b | v1.1.1 hotfix: filter `tools.<name>.skip:true` at parametrize time so skipped tools are absent from collection (not runtime-SKIPPED 10x each); 691 → 133 collected under config.example.yaml | 2026-05-08 | 509daee | [260508-p0b-fix-v1-1-skip-doesnt-filter-parametrize-](./quick/260508-p0b-fix-v1-1-skip-doesnt-filter-parametrize-/) |
| 260512-dcs | Migrate example configs to schema v2 (closes CLEAN-03 BLOCKER from v1.2 milestone audit; examples/homelab-mcp.yaml + config.example.yaml flipped to `version: 2`, `.env` precedence comment stripped) | 2026-05-12 | 814d743 | [260512-dcs-flip-example-config-version-1-to-2-close](./quick/260512-dcs-flip-example-config-version-1-to-2-close/) |
| 260513-chh | Fix `_session_needs_preflight` nodeid path mismatch — invert predicate to live-scope allowlist (`tests/contract/`, `tests/sdet/`); 9-case regression test added; framework unit tests no longer trigger live MCP preflight | 2026-05-13 | 1ba103b | [260513-chh-fix-session-needs-preflight-nodeid-path-](./quick/260513-chh-fix-session-needs-preflight-nodeid-path-/) |

## Deferred Items

Items acknowledged at v1.0 / v1.1 / v1.2 / v1.3 / v1.4 close and carried into v1.5+ scope:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| upstream-fix | `homelab-mcp` `list_registered_servers` description rewrite (would let TEST-06 pass against the original target tool) | Open | v1.0 close (2026-05-07) |
| upstream-fix | Upstream homelab-mcp inputSchema bug — Proxmox tools (and likely others) declare optional fields as `type: 'string'` (no `'null'`) but default them to `null`. SDETs explicitly testing null-handling hit `Input validation error: None is not of type 'string'`. Server should declare `type: ['string','null']` or strip null-valued keys before its own jsonschema check. | Open | Phase 19 close (2026-05-13) |
| testing-scaffold | Automated cross-platform SIGINT UAT (Get-Process / pgrep + programmatic SIGINT helper) | Open | v1.0 close (2026-05-07) |
| open-source-prep | Scrub homelab-specific captures from `.planning/` (05-SECURITY.md AR-05-15) | Open — only triggers if/when repo goes public | v1.0 close (2026-05-07) |
| process-hygiene | Backfill 04.1-VERIFICATION.md (UAT.md status:complete is current evidence of record) | Open — optional | v1.0 close (2026-05-07) |
| seed | SEED-001 — Replace rubric-style judge with full agent tool-use loop | dormant | v1.1 close (2026-05-08) |
| seed | SEED-002 — Tool-level parallelism via pytest-xdist with read/write resource markers | dormant — v1.6+ cohort (deferred from v1.4 + v1.5); informs Phase 34 ISOL-04 clamp without delivery | v1.1 close (2026-05-08) |
| seed | SEED-003 — Dynamic judging protocol — rubrics as data, not code | dormant — v1.6+ (deferred from v1.5 per v1.5 scoping) | v1.1 close (2026-05-08) |
| seed | SEED-005 — OpenAI-compatible judge backend as the unifier | dormant — v1.6+ (deferred from v1.4 + v1.5) | v1.1 close (2026-05-08) |
| defer | Phase 16 D-11 `--debug` per-judge breakdown block | dormant — v1.6+ cohort with SEED-003 (deferred from v1.5) | v1.2 close (2026-05-12) |
| backlog | Phase 999.2 — Codegen-driven parameter-test generation for required-field tools | Backlog — pairs with v1.5 Phase 33 (BUCKET); promote at v1.5 close if 999.1 lands clean | Phase 30 UAT-1 (2026-05-19) |
| backlog | Phase 999.5 — Framework self-test pollution when MCPTF_CONFIG_FILE is set | Backlog — likely re-surfaces during v1.5 Phase 34 ISOL-05 audit; re-assess at v1.5 close | Phase 30 UAT-4 (2026-05-19) |
| seed | 15+ remaining dormant seeds in backlog parking lot (SEED-001/002/003/005/006/012/013/016/017/018/021 etc.) | Backlog parking lot — re-triage at v1.5 close | v1.4 close (2026-05-22) |
| quick_task | 260508-p0b / 260512-dcs / 260513-chh quick-task files missing (pre-v1.3 leftover) | Open — file missing; carry to next milestone triage | v1.3 close (2026-05-15) |

## Session Continuity

Last session: 2026-05-26T15:34:54.169Z
Stopped at: Phase 33 context gathered
Resume next: `/gsd-plan-phase 31` to plan Phase 31 (config-surface cleanup)
