# Roadmap: mcp_test_framework

## Milestones

- ✅ **v1.0 MVP** — Phases 01–05 (shipped 2026-05-06) — see [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Multi-Tool + Isolation + JUnit** — Phases 06–11 (shipped 2026-05-08) — see [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Operator-First Design** — Phases 12–16 (shipped 2026-05-12) — see [v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md)
- 🚧 **v1.3 Homelab Scenario Testing** — Phases 17–22 (planning, scoped 2026-05-12)

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

### 🚧 v1.3 Homelab Scenario Testing (Phases 17–22) — IN PLANNING

- [x] **Phase 17: Schema-driven codegen surface** — `gen-sdet-classes` command + Pydantic param/response classes + `ToolResponse` base + typed call wrappers (CODEGEN-01..06)
 (completed 2026-05-13)
- [x] **Phase 18: SDET test surface + typed errors** — `tests/sdet/` discovery scope, `mcp_session` + `tool(name)` fixtures, `--sdet` flag, `ToolCallError` (SDET-01..04, UI-02) (completed 2026-05-13)
- [x] **Phase 19: Stateful primitives + domain UI integration** — yield-fixture cleanup contract, module-scope state passing, cross-file ordering recipe, scenario rendering through `_render_per_tool_rows`, VM-lifecycle dogfood scenario (STATE-01..04, UI-01) (completed 2026-05-13, PASS-WITH-DEFERRALS — D-02 CPU-cores bump deferred to Phase 20; upstream homelab-mcp inputSchema bug filed against the server, NOT a framework fix per SEED-022)
- [x] **Phase 20: v1.3 scope correction — dogfood cleanup + codegen coverage** — delete SUT-specific dogfood from `tests/sdet/`; replace PREFLIGHT-01/02 with mock-fixture codegen unit tests under `tests/framework/unit/`; rewrite REQUIREMENTS rows and this roadmap entry to match the reframed scope (CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01)
 (completed 2026-05-14)
- [ ] **Phase 21: SDET authoring docs + README parity** — `docs/SDET-AUTHORING.md` walkthrough, codegen regen workflow, README scenario sample with char-for-char renderer parity, CLAUDE.md dual-persona note (DOC-SDET-01..03)
- [ ] **Phase 22: Scrub requirement-ID leaks from src/** — remove `CLI-01`/`PERSONA-02`/`CODEGEN-01`-style requirement IDs from operator-facing CLI docstrings (5 commands surface them via `--help`) and from 58 internal references across `src/mcp_test_framework/`; source-code analog of v1.2 doc scrub (SCRUB-SRC-01)

## Phase Details

### Phase 17: Schema-driven codegen surface
**Goal**: An SDET can run a single command and get importable, typed Python classes for every tool the connected MCP server advertises — covering both `outputSchema`-declared and `outputSchema`-undeclared tools through a uniform base.
**Depends on**: Phase 16 (v1.2 close — runner contract, config gate)
**Requirements**: CODEGEN-01, CODEGEN-02, CODEGEN-03, CODEGEN-04, CODEGEN-05, CODEGEN-06
**Success Criteria** (what must be TRUE):
  1. Operator can run `mcp-test-framework gen-sdet-classes` against a configured MCP server and find generated `<ToolName>Params` / `<ToolName>Response` classes under `src/mcp_test_framework/sdet/generated/<server_slug>/` that compile under mypy/pyright with no errors.
  2. Re-running `gen-sdet-classes` is idempotent — only the generated files inside `generated/<server_slug>/` change; nothing outside that tree is touched; generated files carry a clear "do not hand-edit" header.
  3. A test file importing a generated `Params` class and calling `tool("name").call(params)` validates the params against the live `inputSchema` before the wire call (Pydantic) and returns a typed response object on the way back.
  4. The `ToolResponse` base provides `.raw`, `.data`, `.text`, `.is_error` uniformly — test code accessing `.data["..."]` or `.text` does not need to branch on whether the response type is `outputSchema`-declared or generic.
**Plans**: 5 plans (4 waves)
  - [x] 17-01-PLAN.md — ToolResponse base (CODEGEN-04) [wave 1; depends_on: ]
  - [x] 17-02-PLAN.md — JSON-Schema walker + file emitter (CODEGEN-02, CODEGEN-03, CODEGEN-06) [wave 2; depends_on: 17-01]
  - [x] 17-03-PLAN.md — tool() factory + Phase-18 seam (CODEGEN-05) [wave 2; depends_on: 17-01]
  - [x] 17-04-PLAN.md — gen-sdet-classes Typer command (CODEGEN-01) [wave 3; depends_on: 17-01, 17-02, 17-03]
  - [x] 17-05-PLAN.md — pyright dev dep + typecheck gate (CODEGEN-01..06 verification) [wave 4; depends_on: 17-02, 17-04]

### Phase 18: SDET test surface + typed errors
**Goal**: An SDET can write `tests/sdet/test_<name>.py`, import `mcp_session` + `tool("name")` from a stable public seam, and run those tests via `mcp-test-framework run --sdet` — with tool-side errors surfacing as a typed `ToolCallError` instead of an untyped `CallToolResult` blob.
**Depends on**: Phase 17 (call wrappers wrap the generated response classes)
**Requirements**: SDET-01, SDET-02, SDET-03, SDET-04, UI-02
**Success Criteria** (what must be TRUE):
  1. `tests/sdet/` is a recognized discovery scope; the default `mcp-test-framework run` collects only `tests/contract/` (no behavior change); `mcp-test-framework run --sdet` opts the SDET scope into the run and composes cleanly with `-q`, `--explain`, `--debug`, `--raw`, and `--with-framework`.
  2. An SDET importing `from mcp_test_framework.sdet import mcp_session, tool` gets a session-scoped `McpTestClient` wrapper and a `tool(name)` builder; both require `@pytest.mark.asyncio` markers under pytest-asyncio strict mode.
  3. When a tool call returns `result.isError = True`, the call wrapper raises `ToolCallError` with `.tool` / `.code` / `.message` / `.raw` populated; the existing em-dash failure-detail pattern from Phase 16 surfaces `.code` / `.message` in default-mode FAIL rows.
  4. Under `--debug`, the raw `CallToolResult` for a failed call is dumped into the debug appendix without crashing the renderer.
**Plans**: 8 plans
  - [x] 18-01-errors-module-PLAN.md — Ship ToolCallError + _extract_code_message (UI-02; D-07 + D-08) [wave 1; depends_on: none]
  - [x] 18-02-tool-wrapper-body-PLAN.md — Fill ToolWrapper.call() body + add _ACTIVE_CLIENT slot (SDET-03, UI-02) [wave 2; depends_on: 18-01]
  - [x] 18-03-mcp-session-fixture-PLAN.md — Ship mcp_session fixture with D-02 registry activation + D-03 fail-loud (SDET-03, SDET-04) [wave 3; depends_on: 18-02]
  - [x] 18-04-sdet-public-surface-PLAN.md — Re-export mcp_session, tool, ToolCallError from sdet/__init__.py (SDET-03, SDET-04, UI-02) [wave 4; depends_on: 18-01, 18-02, 18-03]
  - [x] 18-05-sdet-cli-flag-PLAN.md — Register --sdet Typer flag; thread through _build_pytest_args + run_pytest_subprocess (SDET-01, SDET-02, SDET-04) [wave 1; depends_on: none]
  - [x] 18-06-runner-renderer-integration-PLAN.md — D-09 JUnit-property parser hook + D-06 scenario digest + D-11 --debug appendix (SDET-02, UI-02) [wave 2; depends_on: 18-01, 18-05]
  - [x] 18-07-tests-sdet-scaffolding-PLAN.md — tests/sdet/ __init__.py + conftest.py (D-09 hook) + test_basic_call.py sanity (SDET-01, SDET-03, SDET-04, UI-02) [wave 5; depends_on: 18-04, 18-06] — completed 2026-05-13
  - [x] 18-08-framework-self-tests-PLAN.md — Pin D-01..D-11 via test_tool_call_error/test_sdet_fixtures/test_sdet_cli/test_sdet_renderer + update test_tool_factory (SDET-01, SDET-02, SDET-03, SDET-04, UI-02) [wave 5; depends_on: 18-04, 18-06, 18-07] — completed 2026-05-13
**UI hint**: yes

### Phase 19: Stateful primitives + domain UI integration
**Goal**: An SDET can author a create-modify-delete scenario whose teardown reliably executes even when an intervening assertion fails, see each scenario step rendered as a nested row under its parent tool group in the domain UI, and have the framework's own dogfood scenario (VM lifecycle against Proxmox) demonstrate the canonical idiom end-to-end.
**Depends on**: Phase 18 (uses `mcp_session` + `tool()` + `ToolCallError`)
**Requirements**: STATE-01, STATE-02, STATE-03, STATE-04, UI-01
**Success Criteria** (what must be TRUE):
  1. The VM-lifecycle dogfood scenario (`create_vm` → `modify_vm` → `delete_vm`) ships in this repo under `tests/sdet/`, uses module-scope yield fixtures, and on a live Proxmox-reachable run produces a clean green result.
  2. A deliberately-failing dogfood test in `tests/framework/` (or equivalent self-test surface) asserts that a stateful fixture's `yield`-teardown still ran after an intervening test raised — cleanup-on-failure is enforced and observable.
  3. SDET scenario runs render through `_render_per_tool_rows`: each scenario module appears as a per-tool group header (e.g. `proxmox_vm_lifecycle`); individual test functions render as nested rows with their function names (`create_returns_pending_vm`, `modify_accepts_cpu_increase`, etc.) and the same PASS/FAIL/SKIP glyph vocabulary the contract pass already uses.
  4. Cross-file scenario ordering via `pytest-order` (or equivalent) is documented as a recipe; the framework ships no custom ordering mechanism.
**Plans**: 4 plans (2 waves)
  - [ ] 19-01-PLAN.md — STATE-02 cleanup-on-failure self-test (xfail strict + module-global counter) [wave 1; depends_on: ]
  - [ ] 19-02-PLAN.md — homelab.proxmox.dogfood_vmid_range Pydantic sub-model + Config wiring + example YAML [wave 1; depends_on: ]
  - [ ] 19-03-PLAN.md — _runner.py parser + renderer extension for tests/sdet/ scenario rows (UI-01) [wave 1; depends_on: ]
  - [ ] 19-04-PLAN.md — VM-lifecycle dogfood scenario (STATE-01/03/04 + STATE-04 pytest-order recipe) [wave 2; depends_on: 19-02, 19-03]
**UI hint**: yes

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
  - [x] 20-01-requirements-scrub-PLAN.md — Remove PREFLIGHT-01/02 from REQUIREMENTS.md; add CLEANUP-DOGFOOD-01 / CODEGEN-COVERAGE-01 / REQ-SCRUB-01 to a new CLEANUP requirement group; update Traceability Table and Phase coverage summary; total goes 21->22 (CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01) [wave 1; depends_on: ]
  - [x] 20-02-roadmap-rewrite-PLAN.md — Rewrite ROADMAP.md Phase 20 milestone bullet and Phase Details block to reflect the reframed scope (CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01) [wave 1; depends_on: ]
  - [x] 20-03-state-update-PLAN.md — STATE.md: record reframe under Decisions; mark Phase 19 D-02 Resolved-by-deletion; add hello-world MCP deferred-items entry; preserve upstream-fix inputSchema row (REQ-SCRUB-01) [wave 1; depends_on: ]
  - [x] 20-04-tests-sdet-cleanup-PLAN.md — Delete tests/sdet/test_proxmox_vm_lifecycle.py (D-04) and tests/sdet/test_basic_call.py (D-06 option c); preserve __init__.py + conftest.py (CLEANUP-DOGFOOD-01) [wave 1; depends_on: ]
  - [x] 20-05-codegen-mock-fixture-tests-PLAN.md — Add tests/framework/unit/test_codegen_integration_mock.py with synthetic 3-tool fixture driven through codegen pipeline + importlib introspection (CODEGEN-COVERAGE-01) [wave 2; depends_on: 20-01]

### Phase 21: SDET authoring docs + README parity
**Goal**: A new SDET arriving at the repo finds a step-by-step authoring walkthrough using the VM-lifecycle scenario as the worked example, understands the codegen regeneration workflow, and sees one scenario sample in the README whose output is char-for-char identical to what the runner emits.
**Depends on**: Phases 17–20 (docs describe the shipped surface, not a moving target)
**Requirements**: DOC-SDET-01, DOC-SDET-02, DOC-SDET-03
**Success Criteria** (what must be TRUE):
  1. `docs/SDET-AUTHORING.md` exists, uses the VM-lifecycle scenario as its worked example, and covers: fixture patterns (`mcp_session`, `tool()`), module-scope state passing, `requires_homelab` preflight, response-typing degradation for `outputSchema`-undeclared tools, and the cleanup-on-failure contract.
  2. The codegen regeneration workflow is documented (when to regen, what gets overwritten, mypy/pyright as the change-detection signal, import-surface stability contract); CLAUDE.md updated to note the dual operator+SDET persona.
  3. The README has one SDET scenario sample whose rendered output block matches the runner's emission char-for-char (Phase 16 / SEED-008 doc-mirroring contract); a snippet-correctness test in `tests/framework/` pins the parity against drift.
**Plans**: 4 plans (3 waves)
  - [x] 21-01-PLAN.md — Author docs/SDET-AUTHORING.md (DOC-SDET-01, DOC-SDET-02) [wave 1; depends_on: ]
  - [x] 21-02-PLAN.md — README ## SDET scenarios section with char-for-char snapshot (DOC-SDET-03) [wave 2; depends_on: 21-01]
  - [x] 21-03-PLAN.md — CLAUDE.md dual-persona note (DOC-SDET-02) [wave 2; depends_on: 21-01]
  - [x] 21-04-PLAN.md — End-of-phase verification matrix (DOC-SDET-01, DOC-SDET-02, DOC-SDET-03) [wave 3; depends_on: 21-01, 21-02, 21-03]

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
| 17. Schema-driven codegen surface | v1.3 | 6/6 | Complete   | 2026-05-13 |
| 18. SDET test surface + typed errors | v1.3 | 8/8 | Complete | 2026-05-13 |
| 19. Stateful primitives + domain UI integration | v1.3 | 0/4 | Not started | — |
| 20. Preflight + conditional skip | v1.3 | 5/5 | Complete   | 2026-05-14 |
| 21. SDET authoring docs + README parity | v1.3 | 1/4 | In Progress|  |

### Phase 22: Scrub requirement-ID leaks from src/

**Goal:** Operator running `mcp-test-framework --help` (or any subcommand `--help`) sees no requirement-ID leaks like `CLI-01`, `PERSONA-02`, `CODEGEN-01`, `SAFE-03`, etc. — only descriptive prose. Internal source comments are also scrubbed so future grep doesn't surface planning-system artifacts inside the shipped package.

**Scope:**
  - 5 user-visible Typer command docstrings (`run`, `list-tools`, `version`, `gen-sdet-classes`, `_emit_yaml_scaffold`) that render through `--help`
  - 58 additional in-source references across `src/mcp_test_framework/` (module docstrings, decision-anchor comments, inline annotations)
  - Replace with prose, or drop entirely when the reference adds no value; preserve only references that explicitly aid future maintenance reasoning (and move those to `.planning/` if so)

**Depends on:** Phase 21 (last v1.3 functional phase — scrub lands as the v1.3 close-hygiene pass; same sequencing pattern as v1.2's CLEAN-03 closure)
**Requirements**: SCRUB-SRC-01 (TBD — formalize during plan-phase)
**Success Criteria** (what must be TRUE):
  1. `uv run mcp-test-framework --help` and each subcommand `--help` show zero matches for the regex `(CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB)-\d+`
  2. `grep -rE '(CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB)-\d+' src/mcp_test_framework/` returns zero hits (or only an allowlist of intentional references with justification)
  3. All Phase 17 unit tests still pass after the scrub (no behavior changes — pure documentation/comment edits)
  4. `mcp-test-framework --help` and each subcommand `--help` still describe the command's purpose clearly (the prose is at least as informative as the current ID-tagged version)

**Plans:** 1/4 plans executed

Plans:
- [ ] TBD (run /gsd-plan-phase 22 to break down)

### Phase 23: Test suite debt cleanup

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 22
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 23 to break down)
