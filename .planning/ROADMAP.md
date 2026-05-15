# Roadmap: mcp_test_framework

## Milestones

- ✅ **v1.0 MVP** — Phases 01–05 (shipped 2026-05-06) — see [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Multi-Tool + Isolation + JUnit** — Phases 06–11 (shipped 2026-05-08) — see [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Operator-First Design** — Phases 12–16 (shipped 2026-05-12) — see [v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Homelab Scenario Testing** — Phases 17–24 (shipped 2026-05-15) — see [v1.3-ROADMAP.md](milestones/v1.3-ROADMAP.md)
- 📋 **v1.4 (TBD)** — to be scoped via `/gsd-new-milestone`

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 01–05) — SHIPPED 2026-05-06</summary>

- [x] Phase 01: Foundation & Pure-Data Core (4/4 plans) — completed 2026-05-04
- [x] Phase 02: MCP Client Wrapper (3/3 plans) — completed 2026-05-05
- [x] Phase 02.1: Close Phase 2 verification gaps — config + UAT (3/3 plans, INSERTED) — completed 2026-05-05
- [x] Phase 03: Ollama Judge (3/3 plans) — completed 2026-05-05
- [x] Phase 04: Fixtures & Test Cases (3/3 plans) — completed 2026-05-06
- [x] Phase 04.1: McpTestClient session-teardown fix (1/1 plan, INSERTED) — completed 2026-05-06
- [x] Phase 05: CLI, README & Acceptance (5/5 plans) — completed 2026-05-06

</details>

<details>
<summary>✅ v1.1 Multi-Tool + Isolation + JUnit (Phases 06–11) — SHIPPED 2026-05-08</summary>

- [x] Phase 06: Per-session host-state isolation (3/3 plans) — completed 2026-05-07
- [x] Phase 07: Multi-tool discovery & parameterized testing (1/1 plan) — completed 2026-05-07
- [x] Phase 08: Per-tool config registry (4/4 plans) — completed 2026-05-07
- [x] Phase 09: JUnit XML output & per-tool reporting (3/3 plans) — completed 2026-05-08
- [x] Phase 10: v1.1 documentation (2/2 plans) — completed 2026-05-08
- [x] Phase 11: v1.1 cleanup & verification hygiene (4/4 plans) — completed 2026-05-08

</details>

<details>
<summary>✅ v1.2 Operator-First Design (Phases 12–16) — SHIPPED 2026-05-12</summary>

- [x] Phase 12: Doc & persona foundation (9/9 plans) — completed 2026-05-10
- [x] Phase 13: Config safety & opt-in tool selection (5/5 plans) — completed 2026-05-11
- [x] Phase 14: Hybrid runner with domain UI (7/7 plans) — completed 2026-05-11
- [x] Phase 15: Operator vs framework test surface split (4/4 plans) — completed 2026-05-12
- [x] Phase 16: Reporter UX overhaul (5/5 plans) — completed 2026-05-12

Quick task in milestone: 260512-dcs (CLEAN-03 closure — example configs migrated to v2 schema).

</details>

<details>
<summary>✅ v1.3 Homelab Scenario Testing (Phases 17–24) — SHIPPED 2026-05-15</summary>

- [x] Phase 17: Schema-driven codegen surface (6/6 plans) — completed 2026-05-13
- [x] Phase 18: SDET test surface + typed errors (8/8 plans) — completed 2026-05-13
- [x] Phase 19: Stateful primitives + domain UI integration (4/4 plans) — completed 2026-05-13 (PASS-WITH-DEFERRALS; D-02 Resolved-by-deletion in Phase 20)
- [x] Phase 20: v1.3 scope correction — dogfood cleanup + codegen coverage (5/5 plans) — completed 2026-05-14
- [x] Phase 21: SDET authoring docs + README parity (4/4 plans) — completed 2026-05-14 (operator-approved FAIL-sample override)
- [x] Phase 21.1: SDET generated output relocation (4/4 plans, INSERTED) — completed 2026-05-14
- [x] Phase 22: Scrub requirement-ID leaks from src/ (4/4 plans) — completed 2026-05-15
- [x] Phase 23: Test suite debt cleanup (4/4 plans, INSERTED) — completed 2026-05-15
- [x] Phase 24: Tool call serializer omits unset optional params (3/3 plans, INSERTED) — completed 2026-05-15

</details>

### 📋 Next Milestone (v1.4)

To be scoped via `/gsd-new-milestone`. v1.3 close push and live-UAT items (Phase 17 SC1 at scale, README PASS-sample re-capture per SERIALIZER-DOC-01) carry into v1.4 triage. See `.planning/milestones/v1.3-MILESTONE-AUDIT.md` for the full deferred-items list.

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 01. Foundation & Pure-Data Core | v1.0 | 4/4 | Complete | 2026-05-04 |
| 02. MCP Client Wrapper | v1.0 | 3/3 | Complete | 2026-05-05 |
| 02.1. Close Phase 2 verification gaps | v1.0 | 3/3 | Complete | 2026-05-05 |
| 03. Ollama Judge | v1.0 | 3/3 | Complete | 2026-05-05 |
| 04. Fixtures & Test Cases | v1.0 | 3/3 | Complete | 2026-05-06 |
| 04.1. McpTestClient teardown fix | v1.0 | 1/1 | Complete | 2026-05-06 |
| 05. CLI, README & Acceptance | v1.0 | 5/5 | Complete | 2026-05-06 |
| 06. Per-session host-state isolation | v1.1 | 3/3 | Complete | 2026-05-07 |
| 07. Multi-tool discovery & parameterized testing | v1.1 | 1/1 | Complete | 2026-05-07 |
| 08. Per-tool config registry | v1.1 | 4/4 | Complete | 2026-05-07 |
| 09. JUnit XML output & per-tool reporting | v1.1 | 3/3 | Complete | 2026-05-08 |
| 10. v1.1 documentation | v1.1 | 2/2 | Complete | 2026-05-08 |
| 11. v1.1 cleanup & verification hygiene | v1.1 | 4/4 | Complete | 2026-05-08 |
| 12. Doc & persona foundation | v1.2 | 9/9 | Complete | 2026-05-10 |
| 13. Config safety & opt-in tool selection | v1.2 | 5/5 | Complete | 2026-05-11 |
| 14. Hybrid runner with domain UI | v1.2 | 7/7 | Complete | 2026-05-11 |
| 15. Operator vs framework test surface split | v1.2 | 4/4 | Complete | 2026-05-12 |
| 16. Reporter UX overhaul | v1.2 | 5/5 | Complete | 2026-05-12 |
| 17. Schema-driven codegen surface | v1.3 | 6/6 | Complete | 2026-05-13 |
| 18. SDET test surface + typed errors | v1.3 | 8/8 | Complete | 2026-05-13 |
| 19. Stateful primitives + domain UI integration | v1.3 | 4/4 | Complete | 2026-05-13 |
| 20. v1.3 scope correction — dogfood cleanup + codegen coverage | v1.3 | 5/5 | Complete | 2026-05-14 |
| 21. SDET authoring docs + README parity | v1.3 | 4/4 | Complete | 2026-05-14 |
| 21.1. SDET generated output relocation | v1.3 | 4/4 | Complete | 2026-05-14 |
| 22. Scrub requirement-ID leaks from src/ | v1.3 | 4/4 | Complete | 2026-05-15 |
| 23. Test suite debt cleanup | v1.3 | 4/4 | Complete | 2026-05-15 |
| 24. Tool call serializer omits unset optional params | v1.3 | 3/3 | Complete | 2026-05-15 |
