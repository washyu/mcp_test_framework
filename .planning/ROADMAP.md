# Roadmap: mcp_test_framework

## Milestones

- ✅ **v1.0 MVP** — Phases 01–05 (shipped 2026-05-06) — see [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- 🚧 **v1.1 Multi-Tool + Isolation + JUnit** — Phases 06–10 (planning, started 2026-05-07)

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

### 🚧 v1.1 — Multi-Tool + Isolation + JUnit

- [x] **Phase 06: Per-session host-state isolation** — Spawn MCP subprocess in a per-session tempdir so test runs no longer mutate the user's real `~/.homelab_mcp/` state; gated by a keyring-touch investigation (completed 2026-05-07)
- [ ] **Phase 07: Multi-tool discovery & parameterized testing** — Generalize from one-tool-per-run to N-tools-per-run via `pytest.mark.parametrize` over discovered tools (no codegen)
- [ ] **Phase 08: Per-tool config registry** — `tools.<name>` config block with skip / call_arguments / judges; reserve `setup:` / `depends_on:` for SEED-004 forward-compat; `extra="forbid"` + `version: 1`
- [ ] **Phase 09: JUnit XML output & per-tool reporting** — `--junit-xml=<path>` passthrough; per-tool granularity in test IDs and summary line
- [ ] **Phase 10: v1.1 documentation** — README + `docs/EXTENDING.md` updates: per-tool config, isolation guarantee, JUnit usage, adding new tool targets

## Phase Details

### Phase 06: Per-session host-state isolation
**Goal**: Test runs no longer mutate the user's real `~/.homelab_mcp/` state. The user can run the test suite while their real `homelab-mcp` instance is in active use without bleed-through.
**Depends on**: Nothing (first v1.1 phase; v1.0 is shipped)
**Requirements**: ISOL-01, ISOL-02, ISOL-03, ISOL-04, ISOL-05, ISOL-06, ISOL-07
**Success Criteria** (what must be TRUE):
  1. After a full `uv run mcp-test-framework run` invocation, the mtimes of `~/.homelab_mcp/credential_registry.json`, `~/.homelab_mcp/known_hosts`, and `~/.homelab_mcp/migration_state.json` are unchanged from before the run (verified by a dedicated test).
  2. The spawned MCP subprocess's `os.path.expanduser('~')` resolves to a per-session tempdir on both Windows (`USERPROFILE`) and POSIX (`HOME`); the tempdir is auto-cleaned on session exit.
  3. The first task of the phase (ISOL-01) produces a recorded answer to "does `list_keyring_credentials` / `list_registered_servers` touch the OS keyring?" — that answer either turns on `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` (ISOL-04) or documents the deferral with explicit triggers.
  4. The env-var passthrough allowlist (`PATH`, `SYSTEMROOT`, `LANG`, `USERNAME`, `MCP_*`) is documented in code comments and EXTENDING.md so future contributors don't widen it accidentally.
  5. No orphaned tempdirs exist on disk after a clean run completes (lifecycle owned by a session-scoped fixture; cleanup automatic via context-manager exit).
**Plans:** 3/3 plans executed

Plans:
- [x] 06-01-PLAN.md -- ISOL-01 keyring-touch recon (gating ship-or-defer for ISOL-04)
- [x] 06-02-PLAN.md -- _isolation.py module + _isolated_home fixture + env-injection at both spawn sites (ISOL-02/04/05/07)
- [x] 06-03-PLAN.md -- tests/test_isolation.py sha256-equality + tempdir-positive verification (ISOL-03/06)

### Phase 07: Multi-tool discovery & parameterized testing
**Goal**: A single test-suite invocation exercises all tools advertised by the connected MCP server (modulo skip-list), with per-tool failures clearly attributed in pytest output.
**Depends on**: Phase 06 (multi-tool spawn pressure exacerbates state bleed-through; isolation must land first)
**Requirements**: MULTI-01, MULTI-02, MULTI-03, MULTI-04
**Success Criteria** (what must be TRUE):
  1. With no `target.tool_name` set, `uv run mcp-test-framework run` discovers and tests every tool the server advertises at session startup; `homelab-mcp` produces N test cases per test function, one per discovered tool.
  2. Per-tool test IDs render as `<test_name>[<tool_name>]` (e.g. `test_schema_is_structurally_valid[list_keyring_credentials]`) in both terminal output and JUnit XML.
  3. With `target.tool_name` set explicitly, the run is restricted to that tool — full v1.0 behavior preserved.
  4. Discovery happens at collection time via `pytest.mark.parametrize`; the test list always reflects the live server, not a codegen artifact.
**Plans:** 1 plan

Plans:
- [x] 07-01-multi-tool-discovery-PLAN.md -- discovery hook + target_tool indirect parametrize + TargetConfig widening + module rename (MULTI-01..04)

### Phase 08: Per-tool config registry
**Goal**: A test author can declaratively control per-tool behavior (skip with reason, fixed `call_arguments`, judge subset selection) via a validated `tools.<tool_name>` config block, without touching framework code.
**Depends on**: Phase 07 (parameterized multi-tool execution is the consumer of the per-tool config)
**Requirements**: TOOLCFG-01, TOOLCFG-02, TOOLCFG-03, TOOLCFG-04, TOOLCFG-05, TOOLCFG-06, TOOLCFG-07
**Success Criteria** (what must be TRUE):
  1. A user can mark a tool `skip: true` with a `skip_reason` string in `config.yaml`; the run reports `<tool_name>: SKIP — <reason>` in pytest output (terminal + JUnit) without modifying framework code.
  2. Typos in config field names (e.g. `srtip:` instead of `skip:`, `clarty` instead of `clarity`) produce a clear Pydantic validation error at config load — not a silent test omission.
  3. A user can select a judge subset per tool via `judges: [clarity, parameters]`; only the listed rubrics run for that tool. Tools without a `judges` entry run all available rubrics.
  4. A user can pin `call_arguments: {key: value}` per tool; the framework passes those exact arguments to `call_tool` instead of the default `{}`.
  5. The config schema includes `version: 1` at top level and Optional unused `setup:` / `depends_on:` fields per tool — present in the model, ignored at runtime, ready for SEED-003 / SEED-004 to activate additively.
**Plans:** 4 plans

Plans:
- [ ] 08-01-PLAN.md — ToolConfig + version + Config wiring + rubric IDs (TOOLCFG-01..05)
- [ ] 08-02-PLAN.md — Runtime guards: tool_config fixture + skip/judges/call_arguments threading + warnings (TOOLCFG-01/06/07)
- [ ] 08-03-PLAN.md — config-init Typer subcommand (D-21..D-24; TOOLCFG-01/02/04)
- [ ] 08-04-PLAN.md — Tests + worked config.example.yaml (TOOLCFG-01..07 verification)

### Phase 09: JUnit XML output & per-tool reporting
**Goal**: A CI engineer can wire the test suite into their pipeline using JUnit XML and trend per-tool failure rates; locally, a concise per-tool summary helps triage failures without reading full pytest output.
**Depends on**: Phase 07 (per-tool granularity in JUnit requires multi-tool test IDs); Phase 08 (skip reporting needs the registry)
**Requirements**: OUTPUT-01, OUTPUT-02, OUTPUT-03
**Success Criteria** (what must be TRUE):
  1. `uv run mcp-test-framework run --junit-xml=results.xml` produces a standard JUnit XML file at `results.xml` consumable by GitHub Actions / Jenkins / generic CI dashboards.
  2. Each test case in the JUnit XML carries a `[<tool_name>]` suffix in its name, so CI dashboards can filter and trend per-tool failure rates over time.
  3. The terminal output of `mcp-test-framework run` includes a per-tool result section showing `<tool_name>: PASS|FAIL|SKIP — <reason>` for every discovered tool — readable at a glance without scrolling pytest detail.
**Plans**: TBD

### Phase 10: v1.1 documentation
**Goal**: A new contributor or CI engineer can adopt v1.1's new capabilities (per-tool config, isolation, JUnit, adding new tool targets) using only the README and `docs/EXTENDING.md` — no source-reading required.
**Depends on**: Phases 06, 07, 08, 09 (documents the surface they ship)
**Requirements**: DOC-04, DOC-05, DOC-06, DOC-07
**Success Criteria** (what must be TRUE):
  1. README has a "Per-tool configuration" section showing a worked example for the homelab-mcp tools currently exercised (skip, call_arguments, judges) — copy-pasteable.
  2. README has an "Isolation guarantee" section that states "test runs do not mutate your real homelab-mcp state" and points the reader at the ISOL-03 verification test as proof.
  3. README has a "CI integration" section with a copy-pasteable GitHub Actions snippet using `--junit-xml=` and the test-results action.
  4. `docs/EXTENDING.md` describes how to add a new MCP tool target via per-tool config alone (no code change required for tools that fit the existing rubric pattern); includes a worked example.
**Plans**: TBD

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
| 07. Multi-tool discovery & parameterized testing | v1.1 | 0/1 | Planned | — |
| 08. Per-tool config registry | v1.1 | 0/4 | Planned | — |
| 09. JUnit XML output & per-tool reporting | v1.1 | 0/? | Not started | — |
| 10. v1.1 documentation | v1.1 | 0/? | Not started | — |
