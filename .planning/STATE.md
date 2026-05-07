---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Multi-Tool + Isolation + JUnit
status: human_needed
stopped_at: Phase 07 verified PASS-WITH-NOTES -- 3 live MCP-server checks deferred to manual run
last_updated: "2026-05-07T20:30:00Z"
last_activity: 2026-05-07 -- Phase 07 verification complete (PASS-WITH-NOTES)
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-07 after v1.0 milestone)

**Core value:** A `pytest`-runnable test suite that exercises one MCP tool end-to-end (schema → call → judge) and exits non-zero on any failure — proving the framework's integration contract before adding breadth.
**Current focus:** Phase 07 — multi-tool-discovery-and-parameterized-testing

## Current Position

Phase: 07 (multi-tool-discovery-and-parameterized-testing) — VERIFIED (PASS-WITH-NOTES)
Plan: 1 of 1 (complete)
Status: Phase 07 complete; human verification needed for live MCP-server checks (collection IDs, single-tool restriction, ISOL-03 regression on machine with homelab-mcp on PATH)
Last activity: 2026-05-07 -- Phase 07 verification complete

## Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Phases planned | 5 | 06, 07, 08, 09, 10 |
| Phases complete | 0 | |
| Requirements scoped | 25 | All v1.1 reqs mapped 1:1 to phases (no orphans) |
| Requirements complete | 0 | |
| Phase 06 P01 | 7min | 3 tasks | 15 files |
| Phase 06 P02 | 4min | 3 tasks | 3 files |
| Phase 06 P03 | 5min | 2 tasks | 9 files |
| Phase 07 P01 | 6min | 3 tasks | 5 files (1 renamed) |

## Accumulated Context

### Decisions

Full decision log lives in PROJECT.md "Key Decisions" table (with outcomes assessed at v1.0 close).

**v1.1 roadmapping decisions (2026-05-07):**

- **Phase 06 first.** Isolation is a current usability bug AND a prerequisite for safely scaling the multi-tool surface in Phase 07. Without isolation, more spawns = more bleed-through.
- **ISOL-01 (keyring investigation) is the gating first task** of Phase 06. Its outcome determines whether ISOL-04 (`PYTHON_KEYRING_BACKEND=null`) ships in v1.1 or is deferred with documented triggers.
- **5 phases under "coarse" granularity.** Justified because each phase is genuinely separable (isolation precedes multi-tool; config registry is its own concern; JUnit is reporting; docs close out across all four). Merging would couple unrelated work; splitting would fragment.
- **Forward-compat reservations honored.** TOOLCFG-03 reserves `setup:` / `depends_on:` for SEED-004 (v1.5+). TOOLCFG-04 uses string IDs for judges — keeps SEED-003 (v1.3 dynamic rubrics) additive, not breaking.
- **No v1.2/v1.3/v1.4/v1.5 work in v1.1.** xdist (SEED-002), OpenAI-compat backend (SEED-005), dynamic rubrics (SEED-003), agentic judge (SEED-001), stateful testing (SEED-004) are all deferred per Long-term Vision.
- [Phase ?]: Phase 06-01: SHIP ISOL-04 (PyPI README documents OS keyring as sole credential store; Plan 06-02 must add PYTHON_KEYRING_BACKEND=keyring.backends.null.Null to _build_isolated_env)
- [Phase ?]: Phase 06-02: ISOL-04 SHIPped — PYTHON_KEYRING_BACKEND=keyring.backends.null.Null injected; CLI __aenter__ path also isolated (D-16/D-17), Phase 04.1 anyio invariant preserved
- [Phase ?]: Phase 06-03: ISOL-03/ISOL-06 verified — empirical PASS on Windows 11 (3/3 sha256 hashes byte-identical, 0 tempdir orphans); ISOL-06 POSIX-arm verification deferred to a future non-Windows dev run
- [Phase 07-01]: TargetConfig.tool_name widened to Optional[str] (default None = discover-all); empty-string-to-None field_validator added; _preflight membership check made conditional on tool_name is not None
- [Phase 07-01]: pytest_generate_tests + indirect parametrize hook added in tests/conftest.py; reuses McpTestClient.__aenter__ for the third spawn site (Phase 06 D-16 isolation inheritance); module-level _DISCOVERED_TOOL_NAMES cache (CD-01); CD-05 short-circuit when TARGET_TOOL_NAME is set
- [Phase 07-01]: tests/test_homelab_list_registered_servers.py renamed -> tests/test_mcp_tool_contract.py via git mv (88% similarity); TEST-08/09/10 take target_tool fixture and use target_tool.name

### Blockers/Concerns

None at roadmap stage. Open question Q2 from `260506-qxs/FINDINGS.md` (does `list_keyring_credentials` touch the OS keyring?) is intentionally surfaced as ISOL-01 — it's a planned investigation, not a roadmap blocker.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260506-qxs | Diagnostic spike — homelab-mcp host-state surface (recon for v1.1 isolation) | 2026-05-07 | 23cc6e1 | [260506-qxs-diagnostic-spike-identify-what-user-visi](./quick/260506-qxs-diagnostic-spike-identify-what-user-visi/) |

## Deferred Items

Items acknowledged at v1.0 close and carried into v2 scope:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| upstream-fix | `homelab-mcp` `list_registered_servers` description rewrite (would let TEST-06 pass against the original target tool) | Open | v1.0 close (2026-05-07) |
| testing-scaffold | Automated cross-platform SIGINT UAT (Get-Process / pgrep + programmatic SIGINT helper) | Open | v1.0 close (2026-05-07) |
| open-source-prep | Scrub homelab IP from README (05-SECURITY.md AR-05-12) | Open — only triggers if/when repo goes public | v1.0 close (2026-05-07) |
| open-source-prep | Scrub homelab-specific captures from `.planning/` (05-SECURITY.md AR-05-15) | Open — only triggers if/when repo goes public | v1.0 close (2026-05-07) |
| process-hygiene | Backfill 04.1-VERIFICATION.md (UAT.md status:complete is current evidence of record) | Open — optional | v1.0 close (2026-05-07) |

## Session Continuity

Last session: 2026-05-07T20:20:16Z
Stopped at: Phase 07 plan 01 complete -- SUMMARY written
Resume file: .planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-01-SUMMARY.md
