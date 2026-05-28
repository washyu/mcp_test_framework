# Roadmap: mcp_test_framework

## Milestones

- ✅ **v1.0 MVP** — Phases 01–05 (shipped 2026-05-06) — see [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Multi-Tool + Isolation + JUnit** — Phases 06–11 (shipped 2026-05-08) — see [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Operator-First Design** — Phases 12–16 (shipped 2026-05-12) — see [v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Homelab Scenario Testing** — Phases 17–24 (shipped 2026-05-15) — see [v1.3-ROADMAP.md](milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 Library Mode Delivery** — Phases 25–30 (shipped 2026-05-22) — see [v1.4-ROADMAP.md](milestones/v1.4-ROADMAP.md)
- ✅ **v1.5 Shim Retirement + Operator Escape Hatches** — Phases 31–35 (shipped 2026-05-28) — see [v1.5-ROADMAP.md](milestones/v1.5-ROADMAP.md)

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

<details>
<summary>✅ v1.4 Library Mode Delivery (Phases 25–30) — SHIPPED 2026-05-22</summary>

- [x] Phase 25: Public-API rename (SEED-023) — sdet → test_code (6/6 plans) — completed 2026-05-16
- [x] Phase 26: Packaging foundation — entry-point + py.typed + dist-name + plugin skeleton (5/5 plans) — completed 2026-05-16
- [x] Phase 27: pytest-native ini config + contracts test injection + dogfood (LIB) (5/5 plans) — completed 2026-05-17
- [x] Phase 28: Codegen output path (CODEGEN) (4/4 plans) — completed 2026-05-17
- [x] Phase 29: Live domain-UI reporter plugin (3/3 plans) — completed 2026-05-17
- [x] Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite (4/4 plans) — completed 2026-05-22

</details>

<details>
<summary>✅ v1.5 Shim Retirement + Operator Escape Hatches (Phases 31–35) — SHIPPED 2026-05-28</summary>

- [x] **Phase 31: Config-surface cleanup — drop `MCPTF_CONFIG_FILE` + `cfg.sdet.*` alias + v1-schema decommission** — Tighten the config surface around `mcp_config_file` ini route as the sole library-mode config source; delete the v1→v2 migration path; relax pinned-message self-tests.
 (completed 2026-05-24)
- [x] **Phase 32: Surface-shim removals — CLI + package + fixtures + discovery** — Delete the v1.4-introduced `sdet`-flavored CLI, package, fixture, console-script, and discovery shims; operator hits operator-tone migration errors pointing at the post-v1.4 names.
 (completed 2026-05-25)
- [x] **Phase 33: Per-bucket skip granularity in `ToolConfig` (999.1)** — Operator escape hatch for required-field tools: opt out of the output bucket per tool while preserving schema + judge signal; collection-time filtering; digest + `--explain` reflect per-bucket skip; docs walkthrough.
 (completed 2026-05-26)
- [x] **Phase 34: Opt-in host isolation passthrough (999.3)** — Audit bare `Config()` callers; ship `host_isolation: strict | passthrough` so live-UAT + SDET scenarios reach operator credentials; passthrough clamps xdist to 1; SEED-022 safety delegation surfaced in docs.
 (completed 2026-05-27)
- [x] **Phase 35: Zero-shim regression gate (capstone)** — Single CI-runnable sweep across import / CLI / config / fixture / discovery surfaces pinning zero matches for every retired shim; blocks reintroduction.
 (completed 2026-05-28)

Full phase details + requirements archived in [v1.5-ROADMAP.md](milestones/v1.5-ROADMAP.md) and [v1.5-REQUIREMENTS.md](milestones/v1.5-REQUIREMENTS.md).

</details>

## Progress

**Execution Order (v1.5):**
Phases execute in numeric order: 31 → 32 → 33 → 34 → 35. Phase 33 (BUCKET) and Phase 34 (ISOL) are nominally independent of each other and both depend only on Phase 31's settled config surface — order between them is interchangeable; canonical order is 33 then 34. Phase 35 lands LAST (regression gate cannot pass until every other v1.5 shim ships). Decimal phases (e.g., 31.1) reserved for INSERTED urgent fixes between integer phases.

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
| 25. Public-API rename (SEED-023) — sdet → test_code | v1.4 | 6/6 | Complete | 2026-05-16 |
| 26. Packaging foundation -- entry-point + py.typed + dist-name + plugin skeleton | v1.4 | 5/5 | Complete | 2026-05-16 |
| 27. register() API + contracts sub-package + test extraction | v1.4 | 5/5 | Complete | 2026-05-17 |
| 28. Codegen output path (CODEGEN) | v1.4 | 4/4 | Complete | 2026-05-17 |
| 29. Live domain-UI reporter plugin | v1.4 | 3/3 | Complete | 2026-05-17 |
| 30. CLI demotion + carry-forward UAT closure + docs rewrite | v1.4 | 4/4 | Complete | 2026-05-20 |
| 31. Config-surface cleanup — drop MCPTF_CONFIG_FILE + cfg.sdet.* alias + v1-schema decommission | v1.5 | 6/6 | Complete   | 2026-05-24 |
| 32. Surface-shim removals — CLI + package + fixtures + discovery | v1.5 | 6/6 | Complete    | 2026-05-25 |
| 33. Per-bucket skip granularity in ToolConfig (999.1) | v1.5 | 6/6 | Complete    | 2026-05-26 |
| 34. Opt-in host isolation passthrough (999.3) | v1.5 | 9/9 | Complete    | 2026-05-28 |
| 35. Zero-shim regression gate (capstone) | v1.5 | 1/1 | Complete    | 2026-05-28 |

## Backlog

### Phase 999.2: Codegen-driven parameter-test generation for required-field tools (PLANNED)

**Goal:** Extend `mcp-contracts gen-test-classes` to emit `<tool>_call_smoke.py` typed SDET scenarios for every tool whose `inputSchema.required` is non-empty. Operator drops example arg dicts under `tools.<name>.examples:` in `config.yaml`; codegen owns the boilerplate, operator owns the values (SEED-022). Pairs with Phase 33 per-bucket skip — operator pairs `skip_buckets: ["output"]` + `examples:` to restore output-bucket signal via codegen scenarios.
**Requirements:** GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, GEN-06, GEN-07, GEN-08 (derived in 999.2-RESEARCH.md; ROADMAP-level requirements remain TBD until v1.6+ promotion)
**Plans:** 6/6 plans complete

Plans:
- [x] 999.2-01-PLAN.md — GEN-01: ToolConfig.examples field + validator (Wave 1)
- [x] 999.2-02-PLAN.md — GEN-03/04/05: _emit_smoke_scenario pure-data emitter + 10 unit tests (Wave 1)
- [x] 999.2-03-PLAN.md — GEN-02/06: generate() loop wiring + cli.py thread-through + 5 integration tests (Wave 2)
- [x] 999.2-04-PLAN.md — GEN-08: end-to-end self-tests (header parity, overwrite, init integrity, importability) (Wave 3)
- [x] 999.2-05-PLAN.md — GEN-07: config.example.yaml Pattern D + examples/homelab-mcp.yaml opt-in template (Wave 1)
- [x] 999.2-06-PLAN.md — GEN-07: docs touch (LIBRARY-MODE + TEST-CODE-AUTHORING + README) (Wave 3)

**Context (captured 2026-05-19 during Phase 30 UAT-1):** The output-conformance bucket calls every enabled tool with `tool_config.call_arguments` (defaults to `{}`). For tools whose inputSchema declares `required: [...]`, the empty-args call is rejected upstream — the test is structurally non-meaningful unless the operator hand-authors `call_arguments:` per tool. Phase 17 / SEED-014 already ships codegen that derives `<ToolName>Params` Pydantic classes from each tools inputSchema. Proposal: extend `gen-test-classes` to ALSO emit a `tests/test_code/_generated/<tool>_call_smoke.py` per required-field tool — a typed SDET scenario that constructs `<ToolName>Params(...)` from inputSchema example values (or operator-supplied `examples:` blocks) and calls the tool through `tool("name").call(params)` with the Phase 24 `exclude_unset=True` serializer. Authoring story: the operator drops `examples:` into `config.yaml` or `pyproject.toml`, `gen-test-classes` reads them, generated scenarios show up under `tests/test_code/` and run in the test-code surface. Codegen owns the boilerplate; the operator owns the example values (SEED-022 respected). Adjacent: a CLI subcommand `mcp-contracts list-required` that reads inputSchema + emits the example-values template the operator needs to fill in. Pairs with v1.5 Phase 33 (per-bucket skip) — operator can keep the schema+judge buckets running while output-bucket coverage shifts to codegen-generated SDET scenarios.

### Phase 999.5: Framework self-test pollution when MCPTF_CONFIG_FILE is set (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

**Context (captured 2026-05-19 during Phase 30 UAT-4 closure):** `tests/framework/test_tool_config.py::TestV111SkipFilter::test_allowlist_filters_out_skip_true_tools` passes in isolation and passes when targeted with `-o mcp_config_file=./config_safe_run.yaml`. It FAILS only under the full library-mode run (`pytest -o mcp_config_file=... --mcp-domain-ui=force`) when the operators PowerShell session also has `$env:MCPTF_CONFIG_FILE = "config.yaml"` set (left over from the UAT-1 workaround for the test-code scenarios import-time bare Config() call).

The symptom is a cross-test pollution that only surfaces when bare `Config()` callers fire BEFORE the SkipFilter test runs. The test constructs its own `Config(test_code=..., tools={"a":..., "b":..., "c":...})` and expects `allowed == ["a","c"]`. The failure mode is consistent with another test (or framework code path) mutating shared state that the SkipFilter assertion ends up reading.

Likely culprits (NOT investigated -- candidate hypotheses):
  1. Pydantic-settings nested-dict merge between init_kwargs and YAML source: when bare-ish `Config(tools={...})` is called with `MCPTF_CONFIG_FILE` set, the source pipeline merges the YAMLs `tools:` (49-skip allowlist) with the init_kwargs `tools` instead of fully overriding. If true, every test that constructs Config with a custom `tools` dict is potentially polluted by the operators shell env.
  2. Some test outside `TestV111SkipFilter` is mutating module-global state that the SkipFilter reads. The `_reset_discovery_cache` autouse fixture covers `_runner._DISCOVERED_TOOL_NAMES` -- maybe a different cache exists (e.g. `_plugin._MCP_SERVER_INFO`, a pydantic-settings sources cache) that doesnt get reset.
  3. Order-dependent leak from the contract plugins `pytest_configure` interacting with framework-test imports.

**Why this matters:** The frameworks own self-tests are not robust to operator env. An operator running `pytest` in their normal shell (with `MCPTF_CONFIG_FILE` set per docs/LIBRARY-MODE.md) can see spurious self-test failures that arent actually framework bugs. This will surface again every time someone tries to verify library-mode behavior against a populated config.

**Note (post-v1.5 Phase 31):** SHIM-05 removes the `MCPTF_CONFIG_FILE` env-var route entirely in v1.5; the specific repro under "operator shell has MCPTF_CONFIG_FILE set" may no longer reach the framework via the env-var path after Phase 31. The underlying class-of-bug (pydantic-settings deep-merge between init_kwargs and any YAML source under bare `Config()` callers) survives the env-var removal — re-assess at v1.5 close (Phase 34 ISOL-05 audit will surface the bare-caller inventory).

**Proposed resolution scope:**
- Reproduce in a clean shell post-Phase-31 to confirm whether the env-var removal closes the symptom or only the surface trigger.
- Add a `monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)` to a session-scoped autouse fixture under `tests/framework/conftest.py` (defensive even post-removal).
- If the root cause IS pydantic-settings deep-merging, audit every framework self-test that constructs Config with a custom `tools` dict and either pin them via `Config(yaml_file=tmp_yaml)` (explicit YAML source) or strip the env via monkeypatch.
- Pairs naturally with v1.5 Phase 34 (always-on isolation) -- both stem from the same problem: framework code paths leaking host env into spawn / test surfaces. Phase 34 is operator-facing; 999.5 is framework-internal.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)
