# mcp_test_framework — v1.4 Requirements

**Milestone:** v1.4 Library Mode Delivery
**Goal:** Reframe the framework as an importable Python test package — operator adds it to `pyproject.toml`, sets one line in `[tool.pytest.ini_options]` pointing at their YAML config, runs their existing `pytest`. Pytest-native MCP contract testing.
**Defined:** 2026-05-15

---

## Active Requirements

Grouped by category. Each REQ is atomic, testable, and user-centric. Traceability to phases populated by the roadmapper.

### Rename — `sdet` → `test_code` (SEED-023)

- [x] **RENAME-01**: Operator can import the test-code surface as `from mcp_test_framework.test_code import ...` (package directory `src/mcp_test_framework/sdet/` renamed to `test_code/`; all internal imports updated).
- [x] **RENAME-02**: Operator can run `mcp-test-framework gen-test-classes` (new CLI command name); `gen-sdet-classes` continues to work in v1.4 as a deprecation-warning shim and is removed in v1.5.
- [x] **RENAME-03**: Operator can pass `--test-code` to `mcp-test-framework run` (replacing `--sdet`); old flag deprecated with warning in v1.4, removed in v1.5.
- [x] **RENAME-04**: Operator-authored test code lives under `tests/test_code/` (replacing `tests/sdet/`); discovery scope updated; library-mode default unchanged (operators choose any path).
- [x] **RENAME-05**: Operator can set `cfg.test_code.generated_root` in `config.yaml`; `cfg.sdet.generated_root` continues to work via Pydantic `Field(alias=...)` deprecation alias in v1.4, removed in v1.5 with schema v2→v3 migration.
- [x] **RENAME-06**: Operator-facing docs use "test-code" terminology consistently — `docs/SDET-AUTHORING.md` renamed to `docs/TEST-CODE-AUTHORING.md`; README, CLAUDE.md, and inline CLI docstrings updated; planning-ID regex sweep returns zero matches in operator-facing surfaces.

### Packaging Foundation (PACK)

- [x] **PACK-01**: Operator's pytest auto-discovers the framework plugin without any `pytest_plugins=[...]` in their conftest — `[project.entry-points.pytest11]` declared in `pyproject.toml` points at the framework's plugin module.
- [x] **PACK-02**: Operator's `pyright` / `mypy` see typed signatures from every framework import — `py.typed` PEP 561 marker present in `src/mcp_test_framework/` and every operator-imported subpackage; wheel ships markers verified.
- [x] **PACK-03**: Operator can `pip install mcp-contracts` and `uv add mcp-contracts` successfully — PyPI distribution name corrected from the planning-stage placeholder `mvp-test-framework` to the final shipping name `mcp-contracts` (Phase 26 D-01; the originally-targeted `mcp-test-framework` is taken on PyPI by an unrelated project per D-03). Per D-02: no PyPI shim under the legacy name is needed because the project was never published. A console-script shim under `mcp-test-framework` is retained in v1.4 for local-install compatibility (Phase 26 D-06) and drops in v1.5.
- [x] **PACK-04**: Wheel-content regression test fails CI if the built wheel is missing `mcp_test_framework/contracts/`, `mcp_test_framework/test_code/`, any `py.typed` marker, or contains accidental `tests/` leakage — wheel introspection runs as part of the framework's own CI gate.

### Library API — pytest-native ini config + Test Injection (LIB)

- [x] **LIB-01**: Operator adds one line in `[tool.pytest.ini_options]` (`mcp_config_file = "./config.yaml"`) in `pyproject.toml` and parametrized contract tests appear in their `pytest` collection. No `register()` call; no `conftest.py` edit; no `pytest_plugins` declaration.
- [x] **LIB-02**: Operator's `pytest --collect-only` lists every injected contract test with stable nodeids of the form `<mcp-contracts>::test_<name>[<tool>]` — without spawning the MCP server (collection phase only).
- [x] **LIB-03**: Each contract test runs against every tool listed under `config.tools` with `skip: false` and produces the same pass/fail signal as today's `mcp-test-framework run` against the same server. Contract test bodies extracted verbatim from `tests/contract/test_mcp_tool_contract.py` into `src/mcp_test_framework/contracts/_tests.py`; v1.3 assertion semantics unchanged.
- [x] **LIB-04**: Operator's pytest selects framework-injected contract tests with `pytest -m mcp_contract` (or excludes with `-m "not mcp_contract"`); marker is auto-applied at injection time via the plugin's `pytest_collection`. The plugin's `_ContractsModule(_PytestModule)` subclass with overridden `nodeid` synthesizes the injected items.
- [x] **LIB-05** (Removed — register() API dropped per Phase 27 D-01): RegistrationError, frame validation, and double-call detection are moot — the pytest-native ini route replaces the `register()` API entirely. LIB-05 closes by virtue of the underlying mechanism it described no longer existing.
- [x] **LIB-06**: Operator's existing fixtures named `config`, `judge`, `client`, `target_tool` do not collide with framework fixtures — all public framework fixtures namespaced with `mcp_` prefix (`mcp_config`, `mcp_judge`, `mcp_client`, `mcp_target_tool`). Unprefixed names kept as compatibility aliases in v1.4; removed in v1.5.
- [x] **LIB-07**: Operator's `_preflight` autouse session-scoped MCP-readiness check fires only when at least one collected item carries `@pytest.mark.mcp_contract` (the plugin auto-applies the marker per injected item) or sits under a test-code-author path prefix. Predicate flips from path-prefix (`tests/contract/`) to marker-based detection.
- [x] **LIB-08**: Framework's black-box rule (no `homelab-mcp` or arbitrary SUT imports from `src/`) is enforceable in a wheel install — `sys.modules` runtime guard relocated from `tests/conftest.py` into `src/mcp_test_framework/_black_box_guard.py:check_black_box` and invoked from `mcp_test_framework._plugin:pytest_configure`; wheel-introspection AST-walk CI test fails on banned imports anywhere inside `src/`.

### Config Seam (CFG)

- [x] **CFG-01**: Operator's `[tool.pytest.ini_options] mcp_config_file = PATH` is the sole library-mode config source. The framework KILLS `MCPTF_CONFIG_FILE` env var in v1.4 with a one-milestone `DeprecationWarning` emitted by the plugin's `pytest_configure`; removal lands in v1.5 cleanup. Precedence ladder: `pytest -o "mcp_config_file=..."` (CLI subprocess + runtime override) > `[tool.pytest.ini_options]` (ini) > defaults. CLI mode (`mcp-contracts run --config PATH`) internally subprocesses `pytest -o "mcp_config_file=PATH"` — single config-resolution route end-to-end.
- [x] **CFG-02** (Removed — register() API dropped per Phase 27 D-01): `register(config_file=PATH)` escape hatch dropped — the ini value IS the explicit escape hatch. Multi-config (list of paths) deferred to v1.5 if a real use case emerges.

### Codegen Output Path (CODEGEN)

- [ ] **CODEGEN-LIB-01**: Operator who runs `gen-test-classes` from a project with a `tests/` directory gets generated classes under `<cwd>/tests/_generated/<server_slug>/` by default — no config required. Operators in projects without a `tests/` directory get a friendly error directing them to set `cfg.test_code.generated_root` or use `--output-dir`.
- [x] **CODEGEN-LIB-02**: `gen-test-classes` refuses to write under any `sys.path` directory containing the installed `mcp_test_framework` package (typically `site-packages/`); resolves the target path absolute at command-start and aborts with a friendly error if the resolved path is inside an installed-package tree.

### Reporter Plugin (REPORTER)

- [ ] **REPORTER-01**: Operator passing `--mcp-domain-ui` to `pytest` sees the MCP domain-language output (header / per-tool rows / summary) alongside or replacing pytest's native output — driven by live `pytest_runtest_logreport` events, NOT JUnit XML parsing. Default OFF; CI / no-TTY environments default OFF even with the flag set unless `--mcp-domain-ui=force` is passed.
- [ ] **REPORTER-02**: Operator running under `pytest-xdist` sees the domain UI emitted from the master process only; worker output is not multiplexed into the domain UI rows. Reporter plugin loaded under separate `[project.entry-points.pytest11]` key so operator can `-p no:mcp_test_framework_reporter` while keeping contract fixtures.

### CLI Demotion + Carry-Forward UAT + Docs (CLOSE)

- [ ] **CLOSE-01**: Framework's own `tests/contract/conftest.py` calls `register(config=Config())` — proving the library-mode dogfood loop end-to-end. `tests/conftest.py`'s `pytest_generate_tests` is removed; all contract-test parametrization flows through the plugin's hooks. CLI-mode path (`mcp-test-framework run`) continues to subprocess pytest with JUnit XML round-trip and shares the same `ParsedRun` domain model and renderer helpers.
- [ ] **CLOSE-02**: Operator running `mcp-contracts run --config PATH` sees identical pass/fail signal to operator running `pytest` against the same `[tool.pytest.ini_options] mcp_config_file = PATH` — CLI/library parity gated by a CI test that drives both routes against the same fixture config and asserts equivalent JUnit XML output.
- [ ] **CLOSE-03**: New operator reading the README sees library-mode usage first ("Add to your `pyproject.toml`, write three lines in `conftest.py`, run pytest"); CLI usage demotes to an "Appendix: CLI usage" section; `docs/LIBRARY-MODE.md` is the primary reference document for the library API surface.
- [ ] **CLOSE-04**: Carry-forward live-UAT items from v1.2 / v1.3 close as part of the library-mode dogfood pass:
  - README §test-code-scenarios PASS-sample re-capture (the post-Phase-24 capture deferred via Plan 24-02 regen-failed contract; needs operator shell with Proxmox keyring access)
  - Phase 17 SC1 live-stack confirmation at ~70-tool scale (`gen-test-classes` against live homelab-mcp + `uv run pyright` on real generated dir)
  - v1.2 Phase 13 live-stack UAT (v2 config + migration walkthrough with library-mode `mcp_config_file` ini example)
  - v1.2 Phase 14 live-stack UAT (`test_runner_live_smoke.py` + visual domain UI checks under both CLI and library modes)

---

## Future Requirements (Deferred)

Items deliberately scoped OUT of v1.4 but explicitly planned for v1.5+ to prevent re-triage churn:

- **xdist-parallel test execution (SEED-002)** — library API must stabilize first; deferred to v1.5. v1.4 ini-route plan storage uses module-level state inside the plugin; v1.5 will migrate to `config.stash` if/when xdist adoption requires it.
- **OpenAI-compatible judge backend (SEED-005)** — judge Protocol seam from v1.0 is exercise-ready; v1.4 ships only the local Ollama backend; deferred to v1.5 alongside DIFF-2 stub backend.
- **Multi-server context-manager seam for monorepos** — wait for a real operator with the need; v1.4 supports a single `mcp_config_file` per pytest session.
- **URL-style judge kwarg sugar (`judge="ollama://host:port/model"`)** — config surface ships split (`ollama.base_url`, `ollama.model`) in v1.4; URL parser can be added in v1.5 without breaking semver.
- **`gen-test-classes` as a library callable (`mcp_test_framework.test_code.generate_classes()`)** — v1.4 requires the CLI install for codegen; library-mode-only operators wait for v1.5.
- **Auto-discovery of all server-side tools when `config.tools` is empty** — v1.4 requires an explicit allowlist; auto-discovery deferred until v1.5 dogfood proves the safer default.
- **Removal of deprecation aliases (CLI command, flag, fixture names, config schema)** — all v1.4 deprecation shims drop in v1.5 with one round of explicit warnings between them.
- **Per-judge `--debug` breakdown block (Phase 16 D-11)** — dormant carry-over from v1.2; targeting v1.5 cohort with SEED-003 dynamic rubrics.
- **Library-mode pytest plugin discovery in non-uv environments** — uv-first install path documented; pip-installed-without-uv operator support tracked but not gated.

---

## Out of Scope

Explicit exclusions for v1.4, with reasoning preserved for future audits:

- **Removing the CLI** — `mcp-test-framework run|list-tools|config-init|gen-test-classes|version` continue to ship in v1.4; CLI demotes to a "secondary convenience" surface but is NOT deprecated. Operators with CI one-liners and operators doing ad-hoc tool discovery keep their workflow.
- **Multiple MCP servers in one pytest session** — single-server scope per `mcp_config_file` value; multi-server seam deferred to v1.5+.
- **Free-form `[tool.pytest.ini_options]` extension keys for the plugin** — only `mcp_config_file` is part of the public ini surface in v1.4; further opt-in keys ship behind named milestones to keep the semver-stable surface explicit.
- **Auto-loading the domain UI reporter plugin** — explicit opt-in via `--mcp-domain-ui` flag; operators expect native pytest output by default.
- **Schema v2→v3 migration in v1.4** — schema v2 stays; the `cfg.sdet.*` → `cfg.test_code.*` rename rides Pydantic field aliases (no version bump). Migration to v3 deferred to v1.5 when alias drops.
- **Replacing the JUnit XML round-trip in CLI mode** — CLI keeps subprocess + JUnit XML pipeline for v1.4 (subprocess isolation is valuable for `--debug`, signal handling, operator-tone errors). Consolidation question deferred to v1.5+ as its own seed.
- **`pytest-bdd`-style scenario keys in `config.yaml`** — `config.scenarios:` style schema is not the v1.4 shape; per-tool `tools.<name>` knobs only.
- **README badge rewrites, branding, or marketing surface** — out of scope; v1.4 is a delivery-shape pivot, not a marketing relaunch.

---

## Traceability

REQ → Phase mapping populated by roadmapper 2026-05-15. All 28 v1.4 requirements mapped; 100% coverage; no orphans, no duplicates.

| REQ ID | Phase | Status |
|--------|-------|--------|
| RENAME-01 | Phase 25 | Complete |
| RENAME-02 | Phase 25 | Complete |
| RENAME-03 | Phase 25 | Complete |
| RENAME-04 | Phase 25 | Complete |
| RENAME-05 | Phase 25 | Complete |
| RENAME-06 | Phase 25 | Complete |
| PACK-01 | Phase 26 | Complete |
| PACK-02 | Phase 26 | Complete |
| PACK-03 | Phase 26 | Complete |
| PACK-04 | Phase 26 | Complete |
| LIB-01 | Phase 27 | Complete |
| LIB-02 | Phase 27 | Complete |
| LIB-03 | Phase 27 | Complete |
| LIB-04 | Phase 27 | Complete |
| LIB-05 | Phase 27 | Removed (Phase 27 D-01) |
| LIB-06 | Phase 27 | Complete |
| LIB-07 | Phase 27 | Complete |
| LIB-08 | Phase 27 | Complete |
| CFG-01 | Phase 27 | Complete |
| CFG-02 | Phase 27 | Removed (Phase 27 D-01) |
| CODEGEN-LIB-01 | Phase 28 | Pending |
| CODEGEN-LIB-02 | Phase 28 | Complete |
| REPORTER-01 | Phase 29 | Pending |
| REPORTER-02 | Phase 29 | Pending |
| CLOSE-01 | Phase 30 | Pending |
| CLOSE-02 | Phase 30 | Pending |
| CLOSE-03 | Phase 30 | Pending |
| CLOSE-04 | Phase 30 | Pending |

---
*Last updated: 2026-05-15 — Traceability populated by roadmapper after 6-phase shape (25–30) approved. 28 requirements across 7 categories; phase assignment 6/4/8/4/2/4 (RENAME / PACK / LIB / CFG+CODEGEN / REPORTER / CLOSE).*
