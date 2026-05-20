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

**Milestone Goal:** Reframe the framework as an importable Python test package — operator adds it to their MCP server's `pyproject.toml`, sets one line in `[tool.pytest.ini_options]` pointing at their YAML config, runs their existing `pytest`. Pytest-native MCP contract testing.

**Phase Numbering:**
- Integer phases (25, 26, 27, ...): Planned milestone work
- Decimal phases (e.g., 27.1): Reserved for INSERTED urgent fixes mid-milestone

Phases execute in numeric order: 25 → 26 → 27 → 28 → 29 → 30.

- [x] **Phase 25: Public-API rename (SEED-023) — `sdet` → `test_code`** — Lock the public import surface before library mode hardens it. Pure refactor; irreversible after first PyPI publish.
 (completed 2026-05-16)
- [x] **Phase 26: Packaging foundation — entry-point + py.typed + dist-name + plugin skeleton** — Smallest atomic capability that unblocks plugin auto-discovery, typed imports, and the wheel-level black-box guarantee.
 (completed 2026-05-16)
- [x] **Phase 27: pytest-native ini config + contracts test injection + dogfood (LIB)** — The load-bearing technical bet. Operator sets `[tool.pytest.ini_options] mcp_config_file = "./config.yaml"` and the framework plugin injects parametrized contract tests into their pytest collection via a `_ContractsModule(_PytestModule)` virtual-module synthesis.
 (completed 2026-05-17)
- [x] **Phase 28: Codegen output path (CODEGEN)** — `gen-test-classes` refuses to invent an output path or write under its own install tree, prompts before overwriting non-empty targets, and reads the same `mcp_config_file` ini route pytest uses.
 (completed 2026-05-17)
- [x] **Phase 29: Live domain-UI reporter plugin** — `--mcp-domain-ui` opt-in reporter driven by live `pytest_runtest_logreport` events; CI/no-TTY auto-OFF; xdist master-only emission.
 (completed 2026-05-17)
- [x] **Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite** — Framework's `pyproject.toml` already sets `[tool.pytest.ini_options] mcp_config_file = "./config.test.yaml"` (Phase 27 D-06 pre-empt of original CLOSE-01 scope); README leads with library mode; carry-forward live-UAT items from v1.2 / v1.3 close as part of the dogfood pass. (completed 2026-05-20)

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
  - [x] 25-05-PLAN.md — Sweep operator-facing docs/examples for test-code terminology + planning-ID strip
  - [x] 25-06-PLAN.md — CI-runnable acceptance gate (tests/framework/test_sdet_rename_leak_gate.py)

### Phase 26: Packaging foundation — entry-point + py.typed + dist-name + plugin skeleton
**Goal**: Operator adds `mcp-contracts` to `pyproject.toml`, runs `uv add` / `pip install`, and their pytest auto-loads the framework's plugin with typed imports — without any business-logic hooks yet. Establishes the packaging substrate that every later phase hangs off.
**Depends on**: Phase 25 (rename must land before the entry-point string references `mcp_test_framework.test_code` or any operator-imported subpackage).
**Requirements**: PACK-01, PACK-02, PACK-03, PACK-04
**Success Criteria** (what must be TRUE):
  1. Operator running `pip install mcp-contracts` or `uv add mcp-contracts` succeeds against the **TestPyPI**-published wheel (Phase 26 ships a TestPyPI dry-run + local-install verification; production PyPI publish defers to Phase 30 CLOSE-01..04). No PyPI shim under the legacy `mvp-test-framework` name is needed — D-02: the project has never been published, so PACK-03's "one-milestone shim" clause is closed-by-non-applicability.
  2. Operator with the package installed runs `pytest --trace-config` (or equivalent) and sees `mcp_test_framework` listed as an auto-discovered plugin without any `pytest_plugins=[...]` in their conftest.
  3. Operator's `pyright` / `mypy` resolves typed signatures from every operator-imported subpackage (`mcp_test_framework`, `mcp_test_framework.contracts`, `mcp_test_framework.test_code`) — `py.typed` markers ship in the wheel.
  4. Framework CI fails if the built wheel is missing `mcp_test_framework/contracts/`, `mcp_test_framework/test_code/`, any required `py.typed` marker, or contains accidental `tests/` leakage — wheel introspection gate runs on every build.
  5. Operator's existing fixture names (`config`, `judge`, `client`, `target_tool`) do not collide — framework fixtures ship under `mcp_*` prefixed names with one-milestone unprefixed compatibility aliases.
**Plans**: 5 plans
  - [x] 26-01-PLAN.md — pyproject.toml dist-rename, entry-points, scripts; cli.py:974 version-string fix
  - [x] 26-02-PLAN.md — _plugin.py skeleton + _deprecated_script.py shim + fixtures.py rename surgery
  - [x] 26-03-PLAN.md — contracts/ subpackage stub + py.typed markers
  - [x] 26-04-PLAN.md — Wheel-introspection regression gate + cli-version regression test
  - [x] 26-05-PLAN.md — Docs sweep + TestPyPI dry-run + acceptance verification + ROADMAP SC1 amendment

### Phase 27: pytest-native ini config + contracts test injection + dogfood (LIB)
**Goal**: Operator sets one line in `pyproject.toml` — `[tool.pytest.ini_options] mcp_config_file = "./config.yaml"` — and parametrized contract tests appear in their pytest collection with the same pass/fail signal as today's CLI. Load-bearing technical bet of v1.4.
**Depends on**: Phase 26 (plugin entry-point is the precondition for hook registration; ini-driven injection requires the plugin to be auto-loaded).
**Requirements**: LIB-01, LIB-02, LIB-03, LIB-04, LIB-05, LIB-06, LIB-07, LIB-08, CFG-01, CFG-02
**Success Criteria** (what must be TRUE):
  1. Operator sets `[tool.pytest.ini_options] mcp_config_file = PATH` in `pyproject.toml` and runs `pytest --collect-only`; injected contract tests appear with stable nodeids of the form `<mcp-contracts>::test_<name>[<tool>]` — and no MCP server subprocess is spawned during collection.
  2. Operator runs `pytest` and every contract test runs against every tool listed in `config.tools` with `skip: false` and emits the same pass/fail signal as today's `mcp-contracts run` against the same server (test bodies extracted verbatim; v1.3 assertion semantics unchanged).
  3. Operator can run `pytest -m mcp_contract` (or `pytest -m "not mcp_contract"`) and the selection works — every injected item carries the marker; the `_preflight` autouse fires only when at least one `mcp_contract`-marked item is being collected, never against operator's unrelated tests.
  4. Operator setting `mcp_config_file` to a non-existent path sees a friendly `pytest.exit` operator-tone error with `returncode=2` (D-14). Operator with a malformed YAML sees a friendly validation error (D-15). Operator with `MCPTF_CONFIG_FILE` set in their environment sees a one-time `DeprecationWarning` pointing at the new ini route (D-09).
  5. Operator installing the framework into a vanilla project sees the black-box rule enforced in the wheel install — `sys.modules` runtime guard fires from the plugin's `pytest_configure`; wheel-introspection AST-walk CI test fails on banned SUT imports anywhere inside `src/`.
**Plans**: 5 plans
  - [x] 27-01-PLAN.md — Wave 0 spike (`_ContractsModule` hybrid synthesis pattern) + extract `_tests.py` + relocate `_black_box_guard.py`
  - [x] 27-02-PLAN.md — Plugin `pytest_addoption` ini key + `pytest_configure` (Config load, black-box guard, MCPTF_CONFIG_FILE deprecation warning)
  - [x] 27-03-PLAN.md — Plugin `pytest_collection` synthetic Module injection + `pytest_generate_tests` indirect parametrize + marker auto-application
  - [x] 27-04-PLAN.md — CLI subprocess `-o "mcp_config_file=PATH"` rewire + `_preflight` predicate flip to marker-based detection
  - [x] 27-05-PLAN.md — Framework dogfood (pyproject ini) + delete legacy `tests/contract/` + REQUIREMENTS/ROADMAP amendments

### Phase 28: Codegen output path (CODEGEN)
**Goal**: `gen-test-classes` refuses to invent an output path or write under its own install tree, and reads the same `mcp_config_file` ini route pytest uses. Driver: the framework knows nothing about the operator's project layout (rejecting "smart default" framing); single config-resolution route extended from the pytest plugin to the Typer CLI.
**Depends on**: Phase 27 (`mcp_config_file` ini route is the source of truth for config; `gen-test-classes` reads `cfg.test_code.generated_root` from the same Config object).
**Requirements**: CODEGEN-LIB-01, CODEGEN-LIB-02
**Success Criteria** (what must be TRUE):
  1. Operator running `mcp-contracts gen-test-classes` without `cfg.test_code.generated_root` set sees a fail-loud operator-tone error naming the missing field and pointing at `mcp-contracts config-init`. Operator with the field set sees codegen succeed (target dir is created if missing; non-empty target prompts for confirmation in a TTY; non-TTY non-empty target aborts with a helpful error and exit code 2 — no `--yes` / `--force` flag exists).
  2. `gen-test-classes` refuses to write under any directory containing the installed `mcp_test_framework` package — the resolved absolute target path is checked at command start (BEFORE the MCP handshake) and aborts with an operator-tone error naming `test_code.generated_root`, the resolved target path, and the framework install root if it falls inside the installed-package tree. No bypass flag or config knob exists.
  3. Operator who set `[tool.pytest.ini_options] mcp_config_file = PATH` in pyproject.toml sees `mcp-contracts gen-test-classes` use the same config file as `pytest`, without passing `--config`. Precedence ladder: `--config PATH` > pyproject.toml ini value > `MCPTF_CONFIG_FILE` env var (deprecated, removed v1.5) > `./config.yaml` autodiscovery > fail-loud.
**Plans**: 4 plans
  - [x] 28-01-site-packages-guard-PLAN.md — Pre-handshake site-packages guard (CODEGEN-LIB-02)
  - [x] 28-02-pyproject-ini-config-route-PLAN.md — gen-test-classes reads pyproject.toml mcp_config_file ini value
  - [x] 28-03-overwrite-prompt-PLAN.md — Non-empty-dir overwrite prompt + non-TTY abort
  - [x] 28-04-docs-sweep-PLAN.md — REQUIREMENTS.md + ROADMAP.md amendments to reflect actual Phase 28 scope

### Phase 29: Live domain-UI reporter plugin
**Goal**: Operator who wants the v1.2/v1.3-style MCP domain UI output (header / per-tool rows / summary) under library mode passes `--mcp-domain-ui` to pytest and gets it driven by live `pytest_runtest_logreport` events. Default OFF so operators see pytest-native output; CI/no-TTY environments default OFF even with the flag set unless `--mcp-domain-ui=force` is passed.
**Depends on**: Phase 27 (reporter needs `mcp_contract` marker + injected nodeids to attribute per-tool rows); independent of Phase 28 (orthogonal capability).
**Requirements**: REPORTER-01, REPORTER-02
**Success Criteria** (what must be TRUE):
  1. Operator running `pytest --mcp-domain-ui` against a library-mode-registered server sees the MCP-domain header, per-tool rows, and summary line emitted from live `pytest_runtest_logreport` events (NO JUnit XML parsing path) alongside or replacing pytest's native output.
  2. Operator running `pytest` without `--mcp-domain-ui` (the default) sees only pytest's native output — no domain UI emission, even when contract tests are present.
  3. Operator running `pytest --mcp-domain-ui` under CI / no-TTY environments sees the reporter remain OFF unless they pass `--mcp-domain-ui=force` — `pytest-html`, `pytest-sugar`, and similar terminal-coexistence plugins are not hijacked.
  4. Operator running `pytest --mcp-domain-ui -n auto` (pytest-xdist) sees the domain UI emitted from the master process only; worker output is not multiplexed into the per-tool rows. Reporter ships under a separate `[project.entry-points.pytest11]` key so `-p no:mcp_test_framework_reporter` disables it while keeping contract fixtures.
**Plans**: 3 plans
  - [x] 29-01-PLAN.md — Live TestReport adapter (`_build_parsed_run_from_reports` in `_runner.py`) + unit tests (REPORTER-01 data backbone)
  - [x] 29-02-PLAN.md — Reporter plugin module (`_reporter.py`) + `pytest11` entry-point + subprocess integration tests (REPORTER-01 + REPORTER-02)
  - [x] 29-03-PLAN.md — CLI rewire: delete default render call, pass `--mcp-domain-ui` driven by `-q` flag (REPORTER-01 operator-path payoff)

### Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite
**Goal**: Library mode is dogfooded by the framework's own CI (framework `pyproject.toml` sets `[tool.pytest.ini_options] mcp_config_file = "./config.test.yaml"` — pre-empted by Phase 27 D-06); CLI continues to ship but README and `docs/LIBRARY-MODE.md` lead with library-mode usage; carry-forward live-UAT items from v1.2 / v1.3 close (README PASS-sample re-capture, Phase 17 SC1 at ~70 tools, Phase 13 + 14 live-stack UATs) close as part of the dogfood pass.
**Depends on**: Phase 27 (ini config route exists; framework dogfood already landed in Phase 27 D-06), Phase 28 (codegen path settled), Phase 29 (reporter shape known so docs can describe it accurately). Last phase of v1.4.
**Requirements**: CLOSE-01, CLOSE-02, CLOSE-03, CLOSE-04
**Success Criteria** (what must be TRUE):
  1. Framework's own `pyproject.toml` already sets `[tool.pytest.ini_options] mcp_config_file = "./config.test.yaml"` (landed in Phase 27 D-06 / D-07 pre-emption); Phase 30 verifies the dogfood loop is still green at v1.4 close. CLI-mode path (`mcp-contracts run`) continues to subprocess pytest with JUnit XML round-trip and shares the same `ParsedRun` domain model and renderer helpers.
  2. Operator running `mcp-contracts run --config PATH` and operator running `pytest` against the same `[tool.pytest.ini_options] mcp_config_file = PATH` see identical pass/fail signal — CLI/library parity gated by a CI test that drives both routes against the same fixture config and asserts equivalent JUnit XML output.
  3. New operator reading the README sees library-mode usage first ("Add to your `pyproject.toml`, set one line in `[tool.pytest.ini_options]`, run pytest"); CLI usage demotes to an "Appendix: CLI usage" section; `docs/LIBRARY-MODE.md` is the primary reference document for the library API surface.
  4. Carry-forward live-UAT items close as part of the library-mode dogfood: README §test-code-scenarios PASS-sample re-captured against live homelab-mcp + Proxmox; Phase 17 SC1 confirmed at ~70 tools (`gen-test-classes` + `uv run pyright` on real generated dir); v1.2 Phase 13 (v2 config + migration walkthrough with `mcp_config_file` ini example) and Phase 14 (`test_runner_live_smoke.py` + visual domain UI checks under both CLI and library modes) UATs close.
**Plans**: 4 plans
  - [x] 30-01-PLAN.md — CLI/library parity test (CLOSE-02): tests/framework/parity/test_cli_vs_pytest_route.py + parity marker registration in tests/framework/conftest.py
  - [x] 30-02-PLAN.md — Docs rewrite + REQUIREMENTS amendments (CLOSE-01 text + CLOSE-03): docs/LIBRARY-MODE.md created, README.md leads with library mode + CLI demoted to Appendix, REQUIREMENTS.md CLOSE-01/CLOSE-03 text amended
  - [x] 30-03-PLAN.md — UAT capture protocols (CLOSE-04): 30-UAT.md authored with 4 carry-forward UAT sections (user-driven; non-blocking)
  - [x] 30-04-PLAN.md — Dogfood verification at v1.4 close (CLOSE-01 verification act): uv run pytest green, STATE.md updated

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
| 25. Public-API rename (SEED-023) — sdet → test_code | v1.4 | 6/6 | Complete    | 2026-05-16 |
| 26. Packaging foundation -- entry-point + py.typed + dist-name + plugin skeleton | v1.4 | 5/5 | Complete    | 2026-05-16 |
| 27. register() API + contracts sub-package + test extraction | v1.4 | 5/5 | Complete   | 2026-05-17 |
| 28. Codegen output path (CODEGEN) | v1.4 | 4/4 | Complete   | 2026-05-17 |
| 29. Live domain-UI reporter plugin | v1.4 | 3/3 | Complete    | 2026-05-17 |
| 30. CLI demotion + carry-forward UAT closure + docs rewrite | v1.4 | 4/4 | Complete   | 2026-05-20 |

## Backlog

### Phase 999.1: Per-test-bucket / per-judge opt-in granularity in ToolConfig (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

**Context (captured 2026-05-19 during Phase 30 UAT-1):** `ToolConfig.skip: true` is whole-tool only. The operator wants per-bucket granularity so the output-conformance bucket (`test_empty_args_call_returns_non_error`, `test_result_has_content_or_structured`, `test_text_content_parses_as_json`) can be skipped for tools whose inputSchema declares required fields, while the deterministic schema bucket and the LLM judge bucket still run. Current workarounds: (a) `skip: true` on the whole tool — loses judge signal; (b) author `call_arguments:` per tool. Proposal: add `ToolConfig.skip_buckets: list[Literal["schema","judge","output"]] = []` so the operator can opt out by bucket. Also consider an auto-skip-output-when-required heuristic (off by default, opt-in via top-level flag) so the framework can detect required-field tools and silently skip the empty-args bucket without per-tool enumeration. SEED-022 (framework primitives; SDET owns safety) stays intact — the operator still chooses; the framework just gets a more precise lever.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.2: Codegen-driven parameter-test generation for required-field tools (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

**Context (captured 2026-05-19 during Phase 30 UAT-1):** The output-conformance bucket calls every enabled tool with `tool_config.call_arguments` (defaults to `{}`). For tools whose inputSchema declares `required: [...]`, the empty-args call is rejected upstream — the test is structurally non-meaningful unless the operator hand-authors `call_arguments:` per tool. Phase 17 / SEED-014 already ships codegen that derives `<ToolName>Params` Pydantic classes from each tools inputSchema. Proposal: extend `gen-test-classes` to ALSO emit a `tests/test_code/_generated/<tool>_call_smoke.py` per required-field tool — a typed SDET scenario that constructs `<ToolName>Params(...)` from inputSchema example values (or operator-supplied `examples:` blocks) and calls the tool through `tool("name").call(params)` with the Phase 24 `exclude_unset=True` serializer. Authoring story: the operator drops `examples:` into `config.yaml` or `pyproject.toml`, `gen-test-classes` reads them, generated scenarios show up under `tests/test_code/` and run in the test-code surface. Codegen owns the boilerplate; the operator owns the example values (SEED-022 respected). Adjacent: a CLI subcommand `mcp-contracts list-required` that reads inputSchema + emits the example-values template the operator needs to fill in. Pairs with backlog 999.1 (per-bucket skip) — operator can keep the schema+judge buckets running while output-bucket coverage shifts to codegen-generated SDET scenarios.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)
