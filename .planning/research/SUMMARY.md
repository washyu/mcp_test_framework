# Project Research Summary — v1.4 Library Mode Delivery

**Project:** mcp_test_framework
**Domain:** pytest plugin packaging / importable test-library delivery for an MCP contract framework
**Researched:** 2026-05-15
**Confidence:** HIGH

## Executive Summary

v1.4 reframes `mcp_test_framework` from a CLI-first runner into an importable pytest plugin: operator adds the package to `pyproject.toml`, writes three lines in `tests/conftest.py` (`from mcp_test_framework.contracts import register; register(server_command=[...])`), and runs their existing `pytest`. The four research surfaces agree on the shape: the existing v1.3 stack carries forward unchanged, the **only material packaging change is declaring `[project.entry-points.pytest11]`** plus shipping a `py.typed` marker; everything else is refactor work redistributing v1.3 capabilities behind a new public seam.

The load-bearing technical bet is the **`register()` injection pattern**: operator's `conftest.py` call appends to a frozen `_REGISTRATIONS` plan, and the plugin's `pytest_collect_file` hook synthesizes a virtual `_ContractsModule` from `src/mcp_test_framework/contracts/_tests.py` (where today's `tests/contract/test_mcp_tool_contract.py` bodies move verbatim). This is the `pytest-bdd` / `pytest-factoryboy` / `pytest-django` precedent — well-trodden but slightly more advanced than typical plugin code; recommend a Phase 3 spike before locking the API shape. The renderer split is mechanical: `_runner._render_per_tool_rows` is already input-agnostic, so library mode adds `_build_parsed_run_from_reports(TestReport[...])` alongside `parse_junit_xml(path)` and both feed the same `ParsedRun` value.

The risk profile is dominated by **nine packaging/contract pitfalls** that are individually fixable but collectively will produce a broken first release if not addressed in early phases: `_preflight` autouse firing in operators' unrelated test sessions, `MCPTF_CONFIG_FILE` leaking across CI projects in library mode, fixture-name collisions (operators have their own `config` fixture), codegen output writing into `site-packages/`, missing `py.typed` invalidating v1.3's typing investment, the `mvp-test-framework` PyPI dist-name typo blocking `pip install mcp-test-framework`, `register()` kwarg surface freezing too early as a Stable API, the domain UI plugin hijacking operators' terminal under xdist/sugar/html, and the black-box rule's `ruff`+`sys.modules` enforcement not shipping in the wheel. The mitigation pattern is consistent across all nine: **library-mode-specific defaults must invert "shared infrastructure" assumptions** (no path-based discrimination, no env-var fallback, no autouse without registration, no autoload reporter).

## Key Findings

### Recommended Stack

**No new third-party dependencies.** All v1.3 pins (pytest 9.0.3, pytest-asyncio 1.x, mcp 1.27+, pydantic 2.13+, pydantic-settings[yaml] 2.14+, jsonschema 4.26+, httpx, hatchling 1.29+, uv 0.11+) remain valid and version-compatible with Python 3.14. See `.planning/research/STACK.md`.

**Core packaging additions (the only material changes):**
- `[project.entry-points.pytest11] mcp_test_framework = "mcp_test_framework._plugin"` in `pyproject.toml` — auto-loads the plugin in operators' pytest sessions; canonical 2026 pattern.
- `src/mcp_test_framework/py.typed` (empty PEP 561 marker) — without it, pyright/mypy silently treats every framework import as `Unknown` and v1.3's typing investment is invisible to operators.
- Verify hatchling wheel ships `src/mcp_test_framework/contracts/` after the move from `tests/contract/` (existing `packages = ["src/mcp_test_framework"]` declaration is correct; just verify post-build).
- Rename PyPI distribution `mvp-test-framework` → `mcp-test-framework` (current name is a typo from v1.0 that blocks `pip install mcp-test-framework`).

**Pytest hook surface used (all stdlib, no new deps):** `pytest_collect_file` (virtual contract module injection), `pytest_generate_tests` (port v1.3 parametrize), `pytest_runtest_logreport` + `pytest_terminal_summary` (live reporter), `pytest_addoption` + `pytest_configure` (`--mcp-domain-ui` opt-in flag).

### Expected Features

See `.planning/research/FEATURES.md` for full pattern survey of pytest-playwright / pytest-httpx / pytest-bdd / pytest-asyncio / schemathesis.

**Must have (table stakes — operators expect these in any 2026 pytest plugin):**
- TS-1: Auto-loaded plugin via `[project.entry-points.pytest11]` (no `pytest_plugins=[...]` in operator conftest)
- TS-2: `register()` call injects parametrized contract tests into operator's collection
- TS-3: Fixtures (`mcp_client`, `judge`, `target_tool`, etc.) auto-available once plugin loads
- TS-4: Operator's existing `uv run pytest` Just Works — discovers injected tests + operator's own tests in one run
- TS-5: Pytest-native output by default (no domain UI imposed — `.F.E` style is what operators already know)
- TS-6: Selection via `-k` and markers (`@pytest.mark.mcp_contract` on every injected item)
- TS-7: `register()` kwargs mirror `config.yaml` keys 1:1 (single Pydantic Config materialization)
- TS-8: `[tool.pytest.ini_options]` support for non-call-site config
- TS-9: Coexist cleanly with operator's own tests (no global `asyncio_mode`, scope-by-marker not scope-by-path)
- TS-10: Operator-tone diagnostics carry forward from v1.3 (`pytest.exit` with friendly error)
- SEED-023 rename (`sdet` → `test_code`) **must land before public-API freeze** — irreversible after first PyPI publish

**Should have (differentiators, high value / low complexity):**
- DIFF-1: Opt-in domain UI reporter plugin (`--mcp-domain-ui` flag; ports `_render_per_tool_rows` to consume live `TestReport` events instead of JUnit XML)
- DIFF-2: `--judge=stub` for CI without Ollama (exercises the v1.0 JUDGE-01 Protocol seam)
- DIFF-3: Per-tool config via `register(tool_config={...})` kwarg
- DIFF-6: Codegen `generated_root` defaults to `tests/_generated/` when operator's cwd has a `tests/` directory
- DIFF-7: `register()` returns a `RegistrationHandle` exposing `.discovered_tools` / `.selected_tools` / `.skipped`
- DIFF-8: Auto-apply `@pytest.mark.asyncio(loop_scope="session")` to injected tests

**Defer to v1.5+:**
- DIFF-4: `scoped_register()` context manager for multi-server repos — wait for a real operator with the need
- pytest-xdist parallelism (SEED-002) — library API must stabilize first
- OpenAI-compat judge (SEED-005) — DIFF-2 stub backend already exercises the Protocol seam

### Architecture Approach

See `.planning/research/ARCHITECTURE.md` for full diagrams and component boundaries.

**The single most important architectural insight:** the CLI becomes one of `register()`'s clients, not a parallel implementation. Everything the operator can do, the CLI does — by calling `register()` itself from `tests/contract/conftest.py`. CLI mode keeps its subprocess + JUnit XML round-trip (subprocess isolation is valuable for signal handling, operator-tone error envelopes, `--debug` capture); library mode hooks into pytest's live event stream. Both feed the same `ParsedRun` domain model and the same renderer helpers.

**Major components (new in v1.4):**
1. `src/mcp_test_framework/_plugin.py` — pytest11 entry-point module hosting hooks (thin file; no business logic)
2. `src/mcp_test_framework/contracts/__init__.py` — public exports `register` (sub-package, not single module)
3. `src/mcp_test_framework/contracts/_api.py` — `register()` impl: kwargs → frozen `Config` materialization; accepts scalar kwargs OR `config_file=PATH` escape hatch
4. `src/mcp_test_framework/contracts/_registry.py` — `_Intent` frozen dataclass + `_REGISTRATIONS` list + `_INJECTED` one-shot latch
5. `src/mcp_test_framework/contracts/_tests.py` — the 10 parametrized contract test bodies extracted verbatim from `tests/contract/test_mcp_tool_contract.py`

**Modified components:** `_runner.py` (add `_build_parsed_run_from_reports`); `fixtures.py` (`_preflight` predicate keys on `mcp_contract` marker not path); `cli.py` (CLI's `tests/contract/conftest.py` calls `register()`); `pyproject.toml` (entry-point + py.typed + dist-name fix).

**Renamed (SEED-023):** `src/mcp_test_framework/sdet/` → `test_code/`; `gen-sdet-classes` → `gen-test-classes`; `--sdet` → `--test-code`; `cfg.sdet.*` → `cfg.test_code.*` with one-milestone deprecation alias.

**Untouched (entire core substrate carries forward):** `config.py`, `models.py`, `mcp_client.py`, `ollama_judge.py`, `schema_validator.py`, `rubrics.py`, `judge_protocol.py`, `_isolation.py`.

### Watch Out For — Critical Pitfalls

See `.planning/research/PITFALLS.md` for the full nine + four moderate + four minor. The nine criticals are individually small fixes; collectively, missing any one ships a broken first release.

1. **`_preflight` autouse fires in operators' unrelated test sessions (HIGH)** — gate on `_REGISTRATIONS` non-empty AND on `pytest.mark.mcp_contract` marker, not path prefix. Phase 3 critical — must NOT ship contract extraction before this lands.
2. **`MCPTF_CONFIG_FILE` env var leaks across operator's CI ecosystem (HIGH)** — library mode IGNORES the env var entirely; `register()` kwargs are the only config seam. Hard-error if both set.
3. **Black-box rule breaks in wheel install (HIGH)** — move `sys.modules` guard from `tests/conftest.py` into `src/mcp_test_framework/_black_box_guard.py` called from `register()`. Add wheel-introspection AST-walk CI test.
4. **`py.typed` marker missing (HIGH)** — verified: file does NOT exist. Ship empty marker in every operator-imported subpackage; verify in wheel-content snapshot test.
5. **Distribution name typo `mvp-test-framework` on PyPI (HIGH)** — rename to `mcp-test-framework` before any v1.4 publish; leave deprecation shim for one milestone.
6. **`register()` kwarg surface freezes too early as Stable API (HIGH)** — explicit typed kwargs (NO `**kwargs`); `RegisterParams` TypedDict; `config_file=` escape hatch; signature snapshot test pinned. Ship as "Stable v1.5+" — one milestone of operator soak before semver lockdown.
7. **Codegen output writes into `site-packages/` (HIGH)** — default to `<cwd>/tests/_generated/` when `<cwd>/tests/` exists; freeze path at `register()` time; FORBID writing under any `sys.path` directory containing the installed package.
8. **Domain UI plugin hijacks operator's terminal (HIGH)** — opt-in via `--mcp-domain-ui`, NEVER autoload. Separate entry-point key. Detect CI/no-TTY for default-off. Gate xdist emission to master-only.
9. **Coexistence pitfalls grouped (HIGH):** namespace ALL public fixtures with `mcp_` prefix (`mcp_config`, `mcp_judge`, `mcp_target_tool`, `mcp_tool_config` — `config` is virtually guaranteed to collide); `register()` validates caller frame is `conftest.py` + collection phase active + raises on multiple calls; `pytest_configure` self-check on `asyncio_default_fixture_loop_scope` with friendly fail-fast.

## Implications for Roadmap

**Phase-count reconciliation:** The three researchers proposed 5 phases (Stack: A-E), 10 phases (Architecture: A-J), and 9 phases (Pitfalls). The milestone's typical 5-7 phase shape and the atomic/coherent-capability rule suggest a **6-phase structure** that compresses Architecture's J-list by bundling related work and elevates Pitfalls' #1-9 from hidden risk to explicit phase-acceptance criteria. The rename (SEED-023) is its own Phase 1 because all three researchers agree it's irreversible after first publish.

### Phase 1: Rename (SEED-023) — `sdet` → `test_code`
**Rationale:** Pure refactor; must land BEFORE any new public-API expansion locks "sdet" into the v1.4 surface. Low risk; large surface area (code + requirements + docs + config schema + planning IDs).
**Delivers:** `test_code/` package; `gen-test-classes` CLI; `--test-code` flag; `tests/test_code/` discovery; `cfg.test_code.*` schema with `cfg.sdet.*` alias (drops in v1.5); `docs/TEST-CODE-AUTHORING.md`; updated CLAUDE.md / README / planning entries.
**Addresses:** SEED-023; Pitfall 11 (stale imports — compat shim + first-run regen check).

### Phase 2: Packaging foundation — entry-point + py.typed + dist-name + plugin skeleton
**Rationale:** Smallest atomic capability that unblocks everything else. The plugin entry-point auto-discovery is the precondition for fixture availability and test injection. The dist-name fix is a one-time-only PyPI reservation. The plugin skeleton lands as empty hooks so subsequent phases add hooks one-at-a-time without re-touching `pyproject.toml`.
**Delivers:** `[project.entry-points.pytest11]` declaration; `_plugin.py` skeleton with marker registration + `--mcp-domain-ui` flag declared but inert; `py.typed` markers across subpackages; dist name fix with shim; wheel-content snapshot CI test; wheel-introspection AST-walk for SEED-022; fixture rename to `mcp_*` prefix with compat aliases.
**Addresses:** Pitfalls 3 (asyncio config self-check), 5 (fixture namespace), 9-wheel (black-box from src/), 10 (py.typed), 13 (wheel content), 14 (dist rename).

### Phase 3: `register()` API + contracts sub-package + test extraction
**Rationale:** The load-bearing technical bet. Combines Architecture phases C+D+F (registry → extract → inject) because they're a coherent capability that's only useful as a unit. Recommend a small spike at phase entry to validate the `pytest_collect_file` virtual-module injection pattern.
**Delivers:** `contracts/{__init__.py,_api.py,_registry.py,_tests.py}`; explicit typed `register()` kwargs (no `**kwargs`); `RegisterParams` TypedDict; signature snapshot test; `_Intent` frozen dataclass; `_REGISTRATIONS` + `_INJECTED` latch; `pytest_collect_file` synthesizes `_ContractsModule`; `pytest_generate_tests` port; `@pytest.mark.mcp_contract` on every injected item; `_preflight` predicate rewritten to key on marker not path; call-site validation; `tests/contract/test_mcp_tool_contract.py` becomes shim (or deleted with conftest.py calling `register()`).
**Addresses:** Pitfalls 1 (_preflight autouse), 6 (wrong scope validation), 7 (kwarg signature snapshot), 16 (collect-only performance), 17 (no I/O in register frame).
**Research flag:** Spike `pytest_collect_file` injection before committing API shape. Confidence MEDIUM-HIGH on pattern; HIGH after spike.

### Phase 4: Config seam + codegen output path
**Rationale:** Library-mode config flow has to be settled before docs reference `register()` examples. Codegen output path is coupled — operators have no `config.yaml` to set `generated_root`, so the default must work. Cheaper after Phase 3 (uses register's kwarg surface as source of truth).
**Delivers:** `register(config_file=PATH)` escape hatch; `[tool.pytest.ini_options]` precedence (kwargs > pyproject > defaults); URL-style sugar (`judge="ollama://..."`); MCPTF_CONFIG_FILE ignored in library mode (hard-error if both set); `generated_root` defaults to `<cwd>/tests/_generated/`; absolute-path resolution at register time; refusal to write under `sys.path` directories containing the package; `# generated against mcp_test_framework==X.Y.Z` stamp + stale-on-upgrade warning.
**Addresses:** Pitfalls 2 (MCPTF_CONFIG_FILE leak), 4 (codegen into site-packages).

### Phase 5: Live domain-UI reporter plugin
**Rationale:** Orthogonal to test injection. Independent landability. Renderer is already input-agnostic — refactor not rewrite.
**Delivers:** `_runner._build_parsed_run_from_reports(TestReport[...])`; `pytest_runtest_logreport` aggregates per-test reports; `pytest_terminal_summary` emits per-tool rows + summary; pre-run digest from `pytest_collection_modifyitems` when active; default OFF (TS-5); CI/no-TTY detection forces OFF; xdist coexistence via master-only emission; separate entry-point key so `-p no:mcp_test_framework_reporter` works while keeping fixtures.
**Addresses:** Pitfall 8 (UI hijack under xdist/sugar/html/CI).
**Research flag:** Verify `pytest_runtest_logreport` event ordering survives xdist (relevant for SEED-002 in v1.5).

### Phase 6: CLI demotion + carry-forward UAT closure + docs rewrite
**Rationale:** Docs LAST to avoid doc-then-redoc thrash. CLI demotion completes after library mode is proven end-to-end. UATs validate full library-mode story against real homelab-mcp before milestone close.
**Delivers:** `tests/contract/conftest.py` calls `register(config=Config())`; `tests/conftest.py:pytest_generate_tests` deleted (fully replaced by plugin); CLI/library parity test (enumerate Typer flags + `register()` kwargs via `inspect.signature`); README leads with library mode; CLI demoted to "Appendix: CLI usage"; `docs/LIBRARY-MODE.md` primary reference; README §SDET-scenarios PASS-sample re-capture; Phase 17 SC1 live-stack confirmation at ~70-tool scale; v1.2 Phase 13 + Phase 14 live-stack UATs; planning-ID regex sweep.
**Addresses:** Pitfalls 12 (CLI/library drift via parity gate), 15 (docs drift via mode-comment lint + planning-ID sweep).

### Phase Ordering Rationale

- **Rename first:** SEED-023 irreversible after first PyPI publish; all three researchers agree.
- **Packaging foundation second:** Six pitfalls (3, 5, 9-wheel, 10, 13, 14) preventively addressed in one phase; unblocks everything else.
- **`register()` + extraction + injection third:** Load-bearing capability; isolate to avoid entangling with downstream reporter/CLI work. Highest MEDIUM-risk phase.
- **Config seam fourth:** Cheaper after `register()` exists (uses its kwarg surface as source of truth).
- **Reporter plugin fifth:** Orthogonal to injection — independently landable; pairs naturally with renderer split.
- **Docs + UAT + CLI demotion last:** Docs LAST. CLI demotion is the proof point. Carry-forward debt closes naturally here.

### Research Flags

**Needs research during planning:**
- **Phase 3:** Spike `pytest_collect_file` virtual `_ContractsModule` injection before committing API shape.
- **Phase 5:** Verify `pytest_runtest_logreport` ordering under pytest-xdist; verify CI environment detection across GitHub Actions / Jenkins.

**Standard patterns (skip research-phase):**
- **Phase 1 (Rename):** Pure refactor; full blast radius captured in SEED-023; `Field(alias=...)` documented.
- **Phase 2 (Packaging):** `pytest11` is canonical 2026 pattern; PEP 561 well-documented; hatchling unchanged.
- **Phase 4 (Config seam):** `pydantic-settings` precedence proven in v1.2; ini-options pattern is pytest-asyncio's.
- **Phase 6 (Docs/UAT):** Mostly carry-forward verification under new namespace.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All v1.3 pins verified via PyPI 2026-05-15; entry-point pattern verified across pytest-asyncio/playwright/httpx; only material change is one toml block + one empty file |
| Features | HIGH on patterns (mature ecosystem precedent); MEDIUM on specific API shape (multiple defensible designs; pytest-factoryboy is closest precedent but narrow) |
| Architecture | HIGH | pytest plugin patterns stable since pytest 3.x; `pytest_collect_file` is the documented mechanism (pytest-bdd, -django, -mock all use it); SEED-022 invariant mechanically enforced |
| Pitfalls | HIGH on the four repo-specific (_isolation, _preflight, MCPTF_CONFIG_FILE, banned-imports — verified against current src/); HIGH on integration (pytest-asyncio/xdist/sugar — well-documented in issue trackers); MEDIUM on codegen-output-in-site-packages (inferred from PEP 561 + wheel semantics, not from operator repro) |

**Overall confidence:** HIGH

### Gaps to Address

- **`register()` injection pattern spike (Phase 3):** `pytest_collect_file` returning a virtual `_ContractsModule` is documented but the exact `from_parent` + `_getobj` wiring for a non-filesystem module needs validation. Mitigation: time-box spike at Phase 3 entry; fall back to operator-writes-one-re-export-file if blocked.
- **pytest-asyncio 1.x plugin-author API compat:** Full 1.0→1.3 changelog not retrievable; recommend explicit smoke test during Phase 2 on operator-sample-repo CI matrix.
- **`pytest --collect-only` against offline MCP:** Not verified end-to-end. Phase 3 test: cache tool list across collections; skip MCP spawn under collect-only.
- **URL-style judge kwarg vs split kwargs:** Design intuition not user-tested. Plan Phase 4 to accept both; Phase 6 carry-forward UATs drive deprecation of losing form before v1.5 lock.
- **Multiple `register()` calls per conftest:** Phase 3 decision point — raise-on-second (safer for Stable API) vs merge-configs (monorepo support). Lean raise-on-second for v1.4.
- **`gen-test-classes` in library mode:** Phase 1/4 decision point — expose `mcp_test_framework.test_code.generate_classes` callable or require CLI install.

## Sources

### Primary (HIGH confidence)
- pytest 9.0.3 / pytest-asyncio 1.x / hatchling 1.29.0 / mcp 1.27+ / pydantic 2.13+ — PyPI metadata verified 2026-05-15
- pytest official docs — hook reference (`pytest_collect_file`, `pytest_collection_modifyitems`, `pytest_generate_tests`, `pytest_runtest_logreport`, `pytest_terminal_summary`, `pytest_addoption`, `pytest_configure`)
- PEP 561 — `py.typed` marker semantics
- Codebase: `src/mcp_test_framework/{fixtures.py,_runner.py,cli.py,config.py,mcp_client.py,_isolation.py,sdet/__init__.py,sdet/_tool_factory.py}`; `tests/{conftest.py,contract/test_mcp_tool_contract.py,sdet/conftest.py}`; `pyproject.toml`; `CLAUDE.md`; `.planning/PROJECT.md`; `.planning/seeds/SEED-015,SEED-022,SEED-023`
- Reference plugins: pytest-bdd (virtual collection), pytest-factoryboy (closest `register()` precedent), pytest-asyncio, pytest-html (reporter precedent), pytest-django, pytest-sugar (DeferredXdistPlugin for terminal coexistence)

### Secondary (MEDIUM confidence)
- pytest issue #3966 — fixture name collision is silent
- pytest-xdist docs — `-s` doesn't work; worker stdout dropped
- AnyIO docs — `auto` mode conflict; recommend `strict`
- schemathesis docs — `@schema.parametrize` injection (alternative to `register()`)

### Memory entries cited
- `project_mcptf_config_file_silent_fail`, `project_dotenv_silently_beats_config` — Pitfall 2 precedent
- `project_doc_scrub_planning_artifacts` — Pitfall 15 precedent
- `project_v1_1_skip_bug` — collection-time vs runtime filtering precedent
- `project_vibe_coded_persona` — informs Pitfalls 6/8
- `project_framework_primitives_sdet_safety_principle` (SEED-022) — black-box enforcement

---
*Research completed: 2026-05-15*
*Ready for roadmap: yes*
