# Roadmap: mcp_test_framework

## Milestones

- ✅ **v1.0 MVP** — Phases 01–05 (shipped 2026-05-06) — see [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Multi-Tool + Isolation + JUnit** — Phases 06–11 (shipped 2026-05-08) — see [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Operator-First Design** — Phases 12–16 (shipped 2026-05-12) — see [v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Homelab Scenario Testing** — Phases 17–24 (shipped 2026-05-15) — see [v1.3-ROADMAP.md](milestones/v1.3-ROADMAP.md)
- 🚧 **v1.4 Library Mode Delivery** — Phases 25–30 (in progress)

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

### 🚧 v1.4 Library Mode Delivery (In Progress)

**Milestone Goal:** Reframe the framework as an importable Python test package — operator adds it to their MCP server's `pyproject.toml`, writes three lines in `conftest.py`, runs their existing `pytest`. Playwright-for-MCPs.

**Phase Numbering:**
- Integer phases (25, 26, 27, ...): Planned milestone work
- Decimal phases (e.g., 27.1): Reserved for INSERTED urgent fixes mid-milestone

Phases execute in numeric order: 25 → 26 → 27 → 28 → 29 → 30.

- [ ] **Phase 25: Public-API rename (SEED-023) — `sdet` → `test_code`** — Lock the public import surface before library mode hardens it. Pure refactor; irreversible after first PyPI publish.
- [ ] **Phase 26: Packaging foundation — entry-point + py.typed + dist-name + plugin skeleton** — Smallest atomic capability that unblocks plugin auto-discovery, typed imports, and the wheel-level black-box guarantee.
- [ ] **Phase 27: `register()` API + contracts sub-package + test extraction (LIB)** — The load-bearing technical bet. Operator's three-line `register()` call injects parametrized contract tests into their pytest collection via `pytest_collect_file` virtual-module synthesis.
- [ ] **Phase 28: Config seam + codegen output path** — Library-mode config flow (kwargs > pyproject > defaults; `MCPTF_CONFIG_FILE` ignored) and a `tests/_generated/` default that refuses to write into `site-packages/`.
- [ ] **Phase 29: Live domain-UI reporter plugin** — `--mcp-domain-ui` opt-in reporter driven by live `pytest_runtest_logreport` events; CI/no-TTY auto-OFF; xdist master-only emission.
- [ ] **Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite** — Framework's own `tests/contract/conftest.py` calls `register()` (library-mode dogfood); README leads with library mode; carry-forward live-UAT items from v1.2 / v1.3 close as part of the dogfood pass.

## Phase Details

### Phase 25: Public-API rename (SEED-023) — `sdet` → `test_code`
**Goal**: Lock the public import surface for operators and SDETs (`mcp_test_framework.test_code`, `gen-test-classes`, `--test-code` flag, `tests/test_code/`, `cfg.test_code.*`) before v1.4 freezes it into "API-this-can't-change" territory.
**Depends on**: Nothing (first phase of v1.4); irreversible after Phase 26 publishes the corrected dist name to PyPI.
**Requirements**: RENAME-01, RENAME-02, RENAME-03, RENAME-04, RENAME-05, RENAME-06
**Success Criteria** (what must be TRUE):
  1. Operator can run `from mcp_test_framework.test_code import mcp_session, tool` and the import resolves to the renamed package.
  2. Operator can run `mcp-test-framework gen-test-classes` and `mcp-test-framework run --test-code` against a real config and the old `gen-sdet-classes` / `--sdet` invocations still work but print a deprecation warning naming the new name.
  3. Operator can set either `cfg.test_code.generated_root` or `cfg.sdet.generated_root` in `config.yaml` and both load the same field (Pydantic `Field(alias=...)` shim); deprecation warning fires on the old key.
  4. Operator-authored tests under `tests/test_code/` are discovered by the framework's discovery scope (`tests/sdet/` continues to work for one milestone with a deprecation note).
  5. Operator-facing docs (README, `docs/TEST-CODE-AUTHORING.md`, CLAUDE.md, inline CLI docstrings) consistently use "test-code" terminology; planning-ID regex sweep returns zero matches in operator-facing surfaces.
**Plans**: 6 plans
  - [x] 25-01-PLAN.md — Rename src/mcp_test_framework/sdet/ package to test_code/ with back-compat shim
  - [x] 25-02-PLAN.md — Rename gen-sdet-classes CLI command + --sdet flag with hidden deprecation shims
  - [x] 25-03-PLAN.md — Rename SdetConfig to TestCodeConfig with AliasChoices + ambiguity validator
  - [x] 25-04-PLAN.md — Move tests/sdet/ to tests/test_code/ with dual-discovery + pyproject filterwarnings
  - [ ] 25-05-PLAN.md — Sweep operator-facing docs/examples for test-code terminology + planning-ID strip
  - [ ] 25-06-PLAN.md — CI-runnable acceptance gate (tests/framework/test_sdet_rename_leak_gate.py)

### Phase 26: Packaging foundation — entry-point + py.typed + dist-name + plugin skeleton
**Goal**: Operator adds `mcp-test-framework` to `pyproject.toml`, runs `uv add` / `pip install`, and their pytest auto-loads the framework's plugin with typed imports — without any business-logic hooks yet. Establishes the packaging substrate that every later phase hangs off.
**Depends on**: Phase 25 (rename must land before the entry-point string references `mcp_test_framework.test_code` or any operator-imported subpackage).
**Requirements**: PACK-01, PACK-02, PACK-03, PACK-04
**Success Criteria** (what must be TRUE):
  1. Operator running `pip install mcp-test-framework` (corrected from `mvp-test-framework`) or `uv add mcp-test-framework` succeeds against the PyPI-published wheel; a one-milestone shim under the old name redirects.
  2. Operator with the package installed runs `pytest --trace-config` (or equivalent) and sees `mcp_test_framework` listed as an auto-discovered plugin without any `pytest_plugins=[...]` in their conftest.
  3. Operator's `pyright` / `mypy` resolves typed signatures from every operator-imported subpackage (`mcp_test_framework`, `mcp_test_framework.contracts`, `mcp_test_framework.test_code`) — `py.typed` markers ship in the wheel.
  4. Framework CI fails if the built wheel is missing `mcp_test_framework/contracts/`, `mcp_test_framework/test_code/`, any required `py.typed` marker, or contains accidental `tests/` leakage — wheel introspection gate runs on every build.
  5. Operator's existing fixture names (`config`, `judge`, `client`, `target_tool`) do not collide — framework fixtures ship under `mcp_*` prefixed names with one-milestone unprefixed compatibility aliases.
**Plans**: TBD

### Phase 27: `register()` API + contracts sub-package + test extraction (LIB)
**Goal**: Operator writes three lines in `tests/conftest.py` — `from mcp_test_framework.contracts import register; register(server_command=[...], tools=[...], judge=...)` — and parametrized contract tests appear in their pytest collection with the same pass/fail signal as today's CLI. Load-bearing technical bet of v1.4.
**Depends on**: Phase 26 (plugin entry-point is the precondition for hook registration; `register()` injection requires the plugin to be auto-loaded).
**Requirements**: LIB-01, LIB-02, LIB-03, LIB-04, LIB-05, LIB-06, LIB-07, LIB-08
**Success Criteria** (what must be TRUE):
  1. Operator writes `register(server_command=[...], tools=[...], judge="ollama://...")` in `tests/conftest.py` and runs `pytest --collect-only`; injected contract tests appear with stable nodeids of the form `<contracts-module>::test_<name>[<tool>]` — and no MCP server subprocess is spawned during collection.
  2. Operator runs `pytest` and every contract test runs against every tool listed in `register(tools=[...])` and emits the same pass/fail signal as today's `mcp-test-framework run` against the same server (test bodies extracted verbatim; v1.3 assertion semantics unchanged).
  3. Operator can run `pytest -m mcp_contract` (or `pytest -m "not mcp_contract"`) and the selection works — every injected item carries the marker; the `_preflight` autouse fires only when `register()` is non-empty AND `mcp_contract`-marked tests are being collected, never against operator's unrelated tests.
  4. Operator calling `register()` twice in one conftest sees a friendly `RegistrationError` naming the prior call's source location; calling it outside `conftest.py` or outside collection phase also raises a friendly error. `register()` accepts only explicit typed kwargs (NO `**kwargs`); signature is pinned by a snapshot test.
  5. Operator installing the framework into a vanilla project sees the black-box rule enforced in the wheel install — `sys.modules` runtime guard fires from `register()`; wheel-introspection AST-walk CI test fails on banned SUT imports inside `src/`.
**Plans**: TBD

### Phase 28: Config seam + codegen output path
**Goal**: Operator's library-mode config flow is settled — `register()` kwargs are the single source of truth, `MCPTF_CONFIG_FILE` cannot silently leak from a sibling project, and `gen-test-classes` writes generated classes to a sensible default path inside the operator's project (never into `site-packages/`).
**Depends on**: Phase 27 (`register()` kwarg surface is the source of truth for config seam; codegen path defaults use the cwd-relative `tests/` convention introduced alongside `register()`).
**Requirements**: CFG-01, CFG-02, CODEGEN-LIB-01, CODEGEN-LIB-02
**Success Criteria** (what must be TRUE):
  1. Operator running `pytest` in a project where `MCPTF_CONFIG_FILE` is set (e.g. leaked from a sibling CI job) and `register()` is called sees a friendly error directing them to remove the env var — library mode IGNORES the env var entirely.
  2. Operator can pass `register(config_file=PATH)` as an explicit escape hatch for YAML-driven config; kwargs override the file's values; precedence is `register()` kwargs > `[tool.pytest.ini_options]` > file > defaults; source-of-truth is frozen into the internal intent record.
  3. Operator running `mcp-test-framework gen-test-classes` from a project with a `tests/` directory and no config set gets generated classes under `<cwd>/tests/_generated/<server_slug>/` by default; operator in a project without `tests/` gets a friendly error directing them to set `cfg.test_code.generated_root` or pass `--output-dir`.
  4. `gen-test-classes` refuses to write under any `sys.path` directory containing the installed `mcp_test_framework` package — the resolved absolute target path is checked at command start and aborts with a friendly error if it falls inside an installed-package tree.
**Plans**: TBD

### Phase 29: Live domain-UI reporter plugin
**Goal**: Operator who wants the v1.2/v1.3-style MCP domain UI output (header / per-tool rows / summary) under library mode passes `--mcp-domain-ui` to pytest and gets it driven by live `pytest_runtest_logreport` events. Default OFF so operators see pytest-native output; CI/no-TTY environments default OFF even with the flag set unless `--mcp-domain-ui=force` is passed.
**Depends on**: Phase 27 (reporter needs `mcp_contract` marker + injected nodeids to attribute per-tool rows); independent of Phase 28 (orthogonal capability).
**Requirements**: REPORTER-01, REPORTER-02
**Success Criteria** (what must be TRUE):
  1. Operator running `pytest --mcp-domain-ui` against a library-mode-registered server sees the MCP-domain header, per-tool rows, and summary line emitted from live `pytest_runtest_logreport` events (NO JUnit XML parsing path) alongside or replacing pytest's native output.
  2. Operator running `pytest` without `--mcp-domain-ui` (the default) sees only pytest's native output — no domain UI emission, even when contract tests are present.
  3. Operator running `pytest --mcp-domain-ui` under CI / no-TTY environments sees the reporter remain OFF unless they pass `--mcp-domain-ui=force` — `pytest-html`, `pytest-sugar`, and similar terminal-coexistence plugins are not hijacked.
  4. Operator running `pytest --mcp-domain-ui -n auto` (pytest-xdist) sees the domain UI emitted from the master process only; worker output is not multiplexed into the per-tool rows. Reporter ships under a separate `[project.entry-points.pytest11]` key so `-p no:mcp_test_framework_reporter` disables it while keeping contract fixtures.
**Plans**: TBD

### Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite
**Goal**: Library mode is dogfooded by the framework's own CI (`tests/contract/conftest.py` calls `register()`); CLI continues to ship but README and `docs/LIBRARY-MODE.md` lead with library-mode usage; carry-forward live-UAT items from v1.2 / v1.3 close (README PASS-sample re-capture, Phase 17 SC1 at ~70 tools, Phase 13 + 14 live-stack UATs) close as part of the dogfood pass.
**Depends on**: Phase 27 (`register()` exists), Phase 28 (config seam + codegen path settled), Phase 29 (reporter shape known so docs can describe it accurately). Last phase of v1.4.
**Requirements**: CLOSE-01, CLOSE-02, CLOSE-03, CLOSE-04
**Success Criteria** (what must be TRUE):
  1. Framework's own `tests/contract/conftest.py` calls `register(config=Config())` and the existing `tests/conftest.py:pytest_generate_tests` is deleted — all contract-test parametrization flows through the plugin's hooks; library-mode dogfood loop is proven end-to-end.
  2. Operator running `mcp-test-framework run` and operator running `pytest` against the same `register()` call see identical pass/fail signal — CLI/library parity gated by a CI test that enumerates Typer flags via `inspect.signature` and asserts every flag has a matching `register()` kwarg or is documented as CLI-only.
  3. New operator reading the README sees library-mode usage first ("Add to your `pyproject.toml`, write three lines in `conftest.py`, run pytest"); CLI usage demotes to an "Appendix: CLI usage" section; `docs/LIBRARY-MODE.md` is the primary reference document for the library API surface.
  4. Carry-forward live-UAT items close as part of the library-mode dogfood: README §test-code-scenarios PASS-sample re-captured against live homelab-mcp + Proxmox; Phase 17 SC1 confirmed at ~70 tools (`gen-test-classes` + `uv run pyright` on real generated dir); v1.2 Phase 13 (v2 config + migration walkthrough with `register()` example) and Phase 14 (`test_runner_live_smoke.py` + visual domain UI checks under both CLI and library modes) UATs close.
**Plans**: TBD

## Progress

**Execution Order (v1.4):**
Phases execute in numeric order: 25 → 26 → 27 → 28 → 29 → 30. Decimal phases (e.g., 27.1) reserved for INSERTED urgent fixes between integer phases.

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
| 25. Public-API rename (SEED-023) — sdet → test_code | v1.4 | 4/6 | In Progress|  |
| 26. Packaging foundation — entry-point + py.typed + dist-name + plugin skeleton | v1.4 | 0/TBD | Not started | - |
| 27. register() API + contracts sub-package + test extraction | v1.4 | 0/TBD | Not started | - |
| 28. Config seam + codegen output path | v1.4 | 0/TBD | Not started | - |
| 29. Live domain-UI reporter plugin | v1.4 | 0/TBD | Not started | - |
| 30. CLI demotion + carry-forward UAT closure + docs rewrite | v1.4 | 0/TBD | Not started | - |
