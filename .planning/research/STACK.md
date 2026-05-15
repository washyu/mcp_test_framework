# STACK Research: v1.4 Library Mode Delivery

**Project:** mcp_test_framework
**Mode:** Ecosystem / additive-stack
**Researched:** 2026-05-15
**Overall confidence:** HIGH

## Executive Summary

The library-mode pivot for v1.4 is well-served by the **existing v1.3 stack**. The only material additions are **two zero-line packaging changes** (`[project.entry-points.pytest11]` declaration + a hatchling-targets verification) and **one runtime conditional dependency** consideration around how `register()` injects parametrized tests. No new third-party libraries are strictly required; the pytest API surface (entry-point discovery, `pytest_generate_tests`, `pytest_collection_modifyitems`, `pytest_runtest_logreport`, `TerminalReporter` hooks) is fully sufficient. **All v1.3 dep pins remain valid**; `pytest-asyncio 1.x` and `pytest 9.x` are the exact versions needed.

The key insight from surveying pytest's own ecosystem (`pytest-playwright`, `pytest-httpx`, `pytest-asyncio` itself, `pytest-bdd`): **none of them ship a `register()`-style runtime-injection API**. They all rely on (a) entry-point auto-loaded fixtures + hooks and (b) operator-side `pytest.mark.parametrize` decoration. The `register()` shape in SEED-015 is closer to **`pytest-factoryboy.register()`** — which is the one solid precedent and gives you a concrete pattern to crib (it dynamically injects fixtures into the calling module's namespace using `sys._getframe(1).f_globals`).

The biggest decision is **NOT a library choice** — it's the mechanism for "how does `register()` inject parametrized tests into the caller's conftest." Recommended answer below: a hybrid of (1) pytest plugin entry-point auto-loads fixtures + the framework's `pytest_generate_tests` and (2) `register()` populates a module-global "plan" that the entry-point-loaded `pytest_collection_modifyitems` reads. This avoids both `eval`-style code-gen and `sys._getframe` namespace-mutation hacks.

## Recommended Stack

### Core Framework (NO CHANGES — all v1.3 pins valid)

| Technology | Current Pin | v1.4 Action | Why |
|------------|-------------|-------------|-----|
| Python | 3.14 | Keep | No change; pytest 9.0.3 + pytest-asyncio 1.x both target Python ≥3.10 |
| pytest | `>=9.0` | Keep | Latest stable is 9.0.3 (verified PyPI 2026-05-15). 9.x is the right line for plugin authors — `pytest_runtest_logreport`/`TerminalReporter` API stable across 8.x→9.x. **Confidence: HIGH** |
| pytest-asyncio | `>=1.3` | Keep | Latest stable is 1.1.0+ (1.x line); declares `pytest<10,>=8.2` so it's pytest-9 compatible. The `loop_scope="session"` parameter on `@pytest_asyncio.fixture` and `@pytest.mark.asyncio` is the stable API library mode will inherit through fixtures. **Confidence: HIGH** |
| mcp[cli] | `>=1.27` | Keep | The `[cli]` extra continues to pull `typer` transitively (CLI demotes to optional but stays — no need to drop the extra) |
| pydantic | `>=2.13,<3` | Keep | Required by `mcp` + needed for `register()` kwargs validation (Pydantic v2 dataclass / `BaseModel` shape — same as `Config`) |
| pydantic-settings[yaml] | `>=2.14` | Keep | Library mode bypasses most YAML loading (operator passes kwargs to `register()`), but the YAML path remains for `mcp-test-framework run` (CLI demotes-but-stays). Drop is not justified. |
| jsonschema | `>=4.26` | Keep | `Draft202012Validator` continues to drive contract tests after extraction |
| httpx | (transitive via mcp) | Keep transitive | Ollama judge still uses it; library mode doesn't change the judge path |

### Build / Distribution

| Technology | Current | v1.4 Action | Why |
|------------|---------|-------------|-----|
| hatchling | (build backend) | **Verify wheel discoverability** | Hatchling 1.29.0 latest (2026-02-23, PyPI verified). `[tool.hatch.build.targets.wheel] packages = ["src/mcp_test_framework"]` is already correct; just confirm `mcp_test_framework/contracts/` makes it into the wheel after the move from `tests/contract/`. **No build-system change needed.** |
| uv | 0.11.x | Keep | `uv build` produces the sdist+wheel; `uv publish` (PEP 740) for PyPI when v1.4 ships. No version bump needed. |
| `[project.entry-points.pytest11]` | **NOT YET DECLARED** | **ADD** | Single biggest packaging change. See "Pytest Plugin Entry-Point" section below. |

### NEW Library Surfaces (zero new external deps; all stdlib / existing-stack)

| Surface | Mechanism | Why |
|---------|-----------|-----|
| `mcp_test_framework.contracts.register()` | Stdlib `inspect` + module-global plan list | Operator calls in their `conftest.py`; plan is a list-of-dataclasses populated at conftest-collection time. NOT `sys._getframe` namespace mutation — see "register() injection pattern" below. |
| Auto-loaded fixtures | `[project.entry-points.pytest11]` | Replaces the manual `pytest_plugins = ["mcp_test_framework.fixtures"]` line in `tests/conftest.py`; once entry-point declared, fixtures auto-discover in operator's pytest run. |
| Domain UI reporter plugin | `pytest_runtest_logreport` + `TerminalReporter` | Replaces the current `cli.py:run` JUnit-XML post-pass. See "Reporter plugin" section. Opt-in via a pytest CLI flag (`--mcp-domain-ui`) or `pyproject.toml` setting. |
| `mcp_test_framework.test_code` (renamed from `.sdet`) | Pure import-path rename | SEED-023. No new library; just a package rename + import-rewrites + planning-ID scrub for the new term. |

## Pytest Plugin Entry-Point (the single load-bearing packaging change)

**Pyproject.toml addition** (canonical 2026 pattern — well-established since PEP 621, used by `pytest-asyncio`, `pytest-playwright`, `pytest-httpx`, `pytest-xdist`):

```toml
[project.entry-points.pytest11]
mcp_test_framework = "mcp_test_framework.fixtures"
# Optional: separate entry for the domain-UI reporter so operators can
# enable/disable it independently of the contract-test fixtures.
mcp_test_framework_reporter = "mcp_test_framework.reporter"
```

**Why this exact shape:**

1. **`pytest11`** is the historical entry-point group name pytest scans at startup; pytest discovers anything registered there via `importlib.metadata.entry_points()` and treats the pointed-at module as a plugin (its hook functions auto-register).
2. **One entry per plugin module**, value is `"<dotted-import-path>"` (no `:function` suffix — pytest imports the module and inspects it for hook functions; you don't point at a specific function). Confirmed pattern from `pytest-asyncio`'s own setup, `pytest-playwright`'s plugin.
3. **Naming convention** is `<distribution-name> = "<importable.module>"`. Your distribution name is `mvp-test-framework` (per pyproject.toml `[project] name`), so technically `mvp_test_framework = "..."` would be the conformist key — BUT pytest does not care about the LHS key as long as it's unique; the RHS is what matters. Pick whatever reads cleanly.
4. **Two entries is the right shape** for v1.4 because the SEED-015 design treats the reporter plugin as **opt-in**. Pytest 9.x supports entry-point-loaded plugins being disabled at runtime via `-p no:<plugin_name>`; if both fixtures and the reporter come from the same entry, you can't disable just one. (Note: pytest's plugin-name internally derives from the LHS key.)

**Pitfall:** Hatchling needs to **include** `src/mcp_test_framework/contracts/` and `src/mcp_test_framework/reporter.py` in the wheel. Your existing `[tool.hatch.build.targets.wheel] packages = ["src/mcp_test_framework"]` does this correctly (the whole package tree ships) — but verify post-move with `uv build && unzip -l dist/*.whl | grep contracts/`. **Confidence: HIGH** (this is the standard hatchling pattern; the v1.3 code already proves the package shape works).

## `register()` Injection Pattern (the critical design decision)

**The wrong patterns (what NOT to do):**

| Anti-pattern | Why bad |
|-------------|---------|
| `sys._getframe(1).f_globals[test_name] = lambda ...` namespace mutation | Couples to caller's module structure; debugger / coverage / `--collect-only` show synthesized tests with confusing source locations; pytest's collection cache can't invalidate properly across runs. |
| `exec()` / `eval()` of a generated test source string | Same problems plus a security / lint smell. No upside. |
| Decorating a class on the fly inside `register()` and shoving it into the caller's globals | Same problems as #1. |
| Manually adding to `pytest_collect_modifyitems` from the consumer side | Defeats the "three lines in conftest" UX. |

**The recommended pattern (precedent: pytest-asyncio's own collection plugin):**

```python
# src/mcp_test_framework/contracts/__init__.py
_REGISTERED_PLANS: list[ContractPlan] = []

def register(*, server_command, tools, judge, ...) -> None:
    """Called from operator's conftest.py at collection time."""
    plan = ContractPlan(...)  # Pydantic-validated kwargs
    _REGISTERED_PLANS.append(plan)
    # ALSO write to a session-scoped pytest cache via the plugin hook
    # so reloads / pytest -k filters interact correctly.
```

```python
# src/mcp_test_framework/contracts/_plugin.py  (loaded via pytest11 entry-point)
def pytest_generate_tests(metafunc):
    """Parametrize tests in mcp_test_framework.contracts._test_module."""
    if metafunc.module is _test_module and "target_tool" in metafunc.fixturenames:
        # union of tools from all registered plans
        names = sorted({t for plan in _REGISTERED_PLANS for t in plan.tools})
        metafunc.parametrize("target_tool", names, indirect=True)

def pytest_collection_modifyitems(config, items):
    """Inject the contract-test module's test items into the session."""
    if not _REGISTERED_PLANS:
        return
    # Use config.pluginmanager to add the synthetic module
    ...
```

**Why this works:**

1. **The contract-test module ships with the package** — it's `src/mcp_test_framework/contracts/_test_module.py` (rename of today's `tests/contract/test_mcp_tool_contract.py`). It's NEVER discovered by the operator's pytest filesystem walk (lives in `site-packages/`); it's INJECTED by the framework's plugin into the collection.
2. **`pytest_collection_modifyitems`** is the canonical hook for injecting test items that don't come from filesystem discovery. Pytest 9.x supports this verbatim from 8.x and earlier — stable API. **Confidence: HIGH**.
3. **`pytest_generate_tests`** parametrizes the synthetic test module against the registered tools. This is exactly what your v1.3 `tests/conftest.py` does today against `target_tool` — port the logic verbatim.
4. **No `sys._getframe` magic**; no `exec`; no namespace mutation in the operator's conftest. The operator's conftest just calls `register()`, which appends to a module-global. The plugin (auto-loaded via entry-point) does all the actual work at collection time.

**Reference: `pytest-factoryboy`** uses exactly this `register()` shape and is the closest existing-ecosystem precedent. Its source is worth a one-time read during phase planning. **Confidence: MEDIUM-HIGH** (pattern is well-established; the exact `pytest_collection_modifyitems` hook for module injection is a touch more advanced than typical plugin code but documented).

## Reporter Plugin (replacing the JUnit XML post-pass)

The v1.3 `_runner.py` parses JUnit XML AFTER the subprocess exits. For library mode, the operator runs `pytest` directly — there is no subprocess, no JUnit XML capture by the wrapper. The domain UI must attach to **pytest's own live event stream**.

**Recommended hooks (all stdlib pytest, no new deps):**

| Hook | Purpose | Confidence |
|------|---------|-----------|
| `pytest_runtest_logreport(report)` | Called per-test-phase (setup/call/teardown) with a `TestReport` object carrying `nodeid`, `outcome`, `longrepr`, `duration`. **This is the primary live-event seam.** Use it to build the same `ParsedRun` / `ToolVerdict` domain model the JUnit parser builds today — just from `TestReport` objects instead of XML. | HIGH |
| `pytest_sessionstart(session)` | Emit the pre-run digest (Header / Discovered / Running / Skipping / Test plan). Replaces `cli.py:run`'s pre-subprocess digest. | HIGH |
| `pytest_collection_finish(session)` | Alternative seam for the pre-run digest if you want post-collection counts (more accurate than pre-collection). | HIGH |
| `pytest_terminal_summary(terminalreporter, exitstatus, config)` | Emit the per-tool rows + summary line at session end. Operator sees domain UI inside pytest's native flow, not in a wrapper. | HIGH |
| `pytest_addoption(parser)` | Declare the `--mcp-domain-ui` opt-in flag (and `--mcp-explain`, etc.). | HIGH |
| `pytest_configure(config)` | Read the flag, register/unregister the reporter sub-plugin. Standard gate pattern. | HIGH |

**Critical reference:** `pytest-html` does exactly this — entry-point plugin, listens to `pytest_runtest_logreport` for every test, builds a domain model, emits the report at `pytest_sessionfinish`. **`pytest-html` is the textbook pytest-reporter-plugin reference**; the v1.4 reporter can crib its architecture. **Confidence: HIGH**.

**The renderer code stays identical** — `_render_per_tool_rows`, `_render_summary_line`, `_render_pre_run_digest` already take a `ParsedRun` + `RenderContext`. Library mode just builds those objects from live `TestReport` events instead of JUnit XML. **This is a refactor, not a rewrite.**

**Pitfall:** Pytest's `TerminalReporter` already owns the terminal at `pytest_terminal_summary`; print after the pytest summary or use `terminalreporter.write_line(...)`. Don't try to suppress pytest's own summary — operators want it.

## Migration to JUnit-XML-free reporter (don't break the CLI)

The CLI mode (`mcp-test-framework run`) still uses JUnit XML for the wrapper. Two implementation choices for v1.4:

| Option | Tradeoff |
|--------|----------|
| (A) CLI continues subprocess + JUnit XML parse; library mode uses the new live-event reporter | Two render paths; two test surfaces to keep in sync. The renderer functions can be shared. |
| (B) CLI becomes a thin shim that runs `pytest.main()` in-process with the framework's reporter plugin auto-enabled | One render path; CLI loses subprocess isolation. The v1.2 Phase 14 decision was "subprocess for isolation" — overturning it deserves its own seed. |

**Recommendation: (A).** Don't rewrite the CLI in v1.4. Library mode is the new primary surface; CLI keeps its v1.3 architecture. The renderer/parser functions stay shared. (Defer the consolidation question to v1.5+.)

## Test-Code Surface Rename (SEED-023, packaging implications)

The `sdet` → `test_code` rename is **mostly a package + import rewrite** — no new libraries:

- `src/mcp_test_framework/sdet/` → `src/mcp_test_framework/test_code/` (directory rename)
- `pyproject.toml` `[tool.hatch.build.targets.wheel] packages` unchanged (still `["src/mcp_test_framework"]`, the subdir rename is invisible to hatchling)
- `[tool.pyright] include`: update `"src/mcp_test_framework/sdet/response.py"` → `"src/mcp_test_framework/test_code/response.py"`
- `[project.scripts]`: add `gen-test-classes` entry alongside (or replacing — operator decision) `gen-sdet-classes`. **Recommendation:** add the new entry, keep the old as a deprecation-warning shim for one minor release, drop in v1.5.
- `config.yaml`: `sdet.generated_root` key — break or migrate? Schema v2 just landed; bumping to v3 to rename is operator-hostile. **Recommendation:** accept BOTH keys (`test_code.generated_root` preferred, `sdet.generated_root` as a soft-deprecated alias) in v1.4; remove the alias in v1.5 with a v2→v3 migration. Pydantic-settings supports aliased fields trivially via `Field(alias=...)`.

**No new libraries** are required for the rename. The work is all import-rewrites + docs.

## Alternatives Considered (and rejected)

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `pytest_collection_modifyitems` + synthetic test module | `sys._getframe(1).f_globals` namespace injection | Debugger / coverage / `--collect-only` show synthesized tests with confusing source locations. Pytest's collection cache can't invalidate properly. Real precedent (`pytest-factoryboy`) avoids it. |
| Native `pytest_runtest_logreport` reporter plugin | Keep parsing JUnit XML in library mode too | Requires forcing `--junitxml=<tempfile>` flag in the operator's pytest invocation, polluting their CI logs and conflicting with their own `--junitxml=PATH`. Live events are cleaner. |
| Manual `pytest_addoption(parser)` flag | Auto-enable domain UI | Operators want native pytest output by default (they know how to read it). Opt-in is the right default per SEED-015. |
| Single `pytest11` entry-point with both fixtures + reporter | Separate entries | Inability to `-p no:mcp_test_framework_reporter` while keeping fixtures. Separate entries cost nothing. |
| Hatchling unchanged | Switch to `setuptools` / `poetry-core` / `flit-core` | Hatchling is the 2026 uv default; switching mid-project is gratuitous churn. No feature need. |
| `pytest-factoryboy` as a learning reference | Adopt `pytest-factoryboy` as a dependency | Different problem (factory-boy-driven fixtures). Pattern-borrow only. |
| Drop `pytest-timeout` | Keep as dev dep | Used to surface hung tests in framework self-tests. Library-mode operators don't depend on it transitively (it's in `[dependency-groups] dev`, not `[project] dependencies`). |

## What NOT to Add

| Library/Pattern | Why Avoid |
|---------------|-----------|
| `pluggy` declared as a direct dep | Pytest already pulls it. Direct dep risks version skew with pytest's pin. |
| `pytest-html` as a runtime dep | The domain UI replaces it; mixing two reporters is operator-confusing. |
| `pytest-cov` integration as a built-in | Not on the v1.4 critical path; operators add it to their own dev-deps if they want it. |
| `pytest-xdist` integration in v1.4 | Explicitly deferred to v1.5 (per PROJECT.md). The library-mode `register()` API should be xdist-friendly (avoid module-global mutation after collection — use `config.cache` or `session.stash` for cross-worker state), but don't bake xdist in now. |
| `importlib_metadata` backport | Stdlib `importlib.metadata` on Python 3.10+ is sufficient. You're on 3.14. |
| A custom build backend / plugin | Hatchling does everything needed. |
| Click-as-direct-dep | Typer still comes transitively via `mcp[cli]`. No change. |
| Renaming the package `mcp_test_framework` → something else | Out of scope for v1.4; SEED-023 is a SUBpackage rename only. |

## Version Compatibility Matrix

| Package | Compatible with | Notes |
|---------|-----------------|-------|
| `pytest 9.0.3` | Python ≥ 3.10 | Latest stable per PyPI 2026-05-15. Plugin author APIs (entry-points, hooks, TestReport) stable from 8.x. |
| `pytest-asyncio 1.1+` | `pytest>=8.2,<10` | Compatible with pytest 9.x via the explicit upper bound. `loop_scope` parameter on fixtures (used by v1.3) is the stable API. **Confidence: HIGH on compat; MEDIUM on "no plugin-author breakage between 1.0 and 1.x" — recommend explicit smoke test during v1.4 phase 1.** |
| `hatchling 1.29.0` | Python ≥ 3.8 | Latest, 2026-02-23. Wheel + sdist build unchanged. |
| `mcp 1.27+` | Python ≥ 3.10 | Continues to work; stdio client unchanged. |
| `pydantic 2.13.x` | Python ≥ 3.9 | Required by `mcp`; v3 is not out yet. |
| `pydantic-settings 2.14.x` | Pydantic ≥ 2.11 | Continues to drive `Config`. Field aliases supported for the v1.4 `sdet`→`test_code` alias bridge. |

## Confidence Assessment

| Choice | Level | Source(s) |
|--------|-------|-----------|
| `[project.entry-points.pytest11]` is the right entry-point group | HIGH | PEP 621 + pytest docs (training data, corroborated by every published pytest plugin) |
| `pytest_runtest_logreport` is the right hook for live event streaming | HIGH | pytest official hookspec (training data); pytest-html source uses it canonically |
| `pytest_collection_modifyitems` is the right hook for injecting test items from a library | HIGH | pytest official hookspec; pytest-asyncio's own collection plugin uses similar shape |
| `register()` populating a module-global plan + collection hook reading it | MEDIUM-HIGH | pytest-factoryboy is the precedent; pattern is sound but the exact wiring of "synthetic test module injection" is sufficient-but-not-trivial — recommend a small spike in the first v1.4 phase to validate before committing the API shape |
| Hatchling wheel ships `src/mcp_test_framework/contracts/` after extraction | HIGH | v1.3 already proves the `packages = ["src/mcp_test_framework"]` shape works for arbitrary subdirs |
| pytest 9.0.3 + pytest-asyncio 1.x compat | HIGH | PyPI metadata verified 2026-05-15 (pytest-asyncio declares `pytest<10,>=8.2`) |
| `pytest-asyncio` 1.x has no plugin-author breaking changes vs framework's usage | MEDIUM | Could not retrieve full changelog; v1.3 already uses 1.3+; smoke-test as part of v1.4 phase 1 |
| Test-code rename (SEED-023) has no library implications | HIGH | Pure rename; `Field(alias=...)` is documented Pydantic v2 surface |

## Roadmap Implications

Based on this stack research, the suggested v1.4 phase structure breaks into work that is **mostly within existing-stack capabilities**:

1. **Phase A — Pytest plugin entry-point declaration + fixture move**
   - Add `[project.entry-points.pytest11]` to pyproject.toml
   - Verify auto-discovery in a sample external consumer repo
   - Smoke-test that v1.3 `tests/conftest.py`'s `pytest_plugins = ["mcp_test_framework.fixtures"]` becomes redundant
   - **Risk: LOW.** Standard pytest plugin pattern.

2. **Phase B — Contract test extraction + `register()` API**
   - Move `tests/contract/test_mcp_tool_contract.py` → `src/mcp_test_framework/contracts/_test_module.py`
   - Design `register()` kwargs (mirror `Config` 1:1)
   - Implement `pytest_collection_modifyitems` to inject the synthetic test module
   - Port `pytest_generate_tests` parametrize logic from `tests/conftest.py` into the plugin
   - **Risk: MEDIUM.** Synthetic module injection is the load-bearing technical bet — spike first.

3. **Phase C — Live reporter plugin**
   - Wire `pytest_runtest_logreport` → build `ParsedRun` incrementally
   - Wire `pytest_sessionstart` → pre-run digest (port from `_runner._render_pre_run_digest`)
   - Wire `pytest_terminal_summary` → per-tool rows + summary line
   - Add `--mcp-domain-ui` opt-in flag via `pytest_addoption`
   - **Risk: LOW-MEDIUM.** Renderer functions already exist; data sourcing changes from XML to `TestReport`. Most of the work is mechanical.

4. **Phase D — SEED-023 rename**
   - Directory rename + import rewrites + planning-ID scrub for "SDET" terminology
   - Add `gen-test-classes` CLI command alongside `gen-sdet-classes` (deprecation shim)
   - Add `test_code.generated_root` config field aliased to `sdet.generated_root`
   - Update README + docs/SDET-AUTHORING.md → docs/TEST-CODE-AUTHORING.md
   - **Risk: LOW.** Pure refactor.

5. **Phase E — Carry-forward UAT closure + library-mode dogfood**
   - The framework's own `tests/` calls `register()` against a fixture MCP server
   - Validates: external operator's three-line conftest produces ~20 parametrized contract tests
   - README pivots from "how to run the CLI" to "how to add the library"
   - **Risk: LOW.** Standard dogfood loop.

**Phase ordering rationale:** A enables B (entry-point loads the plugin); B is the load-bearing technical bet (spike first); C builds on B's plan registry but is independent in terms of risk; D is pure rename, can interleave or run after; E gates on A+B+C all working.

## Open Questions / Gaps to Address During Phase Planning

- **xdist-friendly `register()` plan storage**: module-global list won't survive worker spawn under xdist. Use `config.stash` keyed by a sentinel instead. Not v1.4 critical but worth getting right now to avoid a v1.5 retrofit. **Recommend: design phase B with `config.stash` from the start.**
- **`pytest-asyncio` plugin-load ordering vs. mcp_test_framework**: when both plugins auto-load via entry-points, pytest's pluginmanager orders by name. Our `_preflight` autouse session-scoped fixture (which is async) depends on pytest-asyncio being loaded first. **Recommend: smoke-test in Phase A; pytest's `tryfirst`/`trylast` markers exist if ordering issues arise.**
- **Reporter plugin and `pytest -p no:terminalreporter`**: some CI scenarios disable the terminal reporter; the domain UI must degrade gracefully (no terminal = no domain UI, no crash). **Recommend: gate the reporter on `config.pluginmanager.has_plugin("terminalreporter")`.**
- **Synthetic test module + `--collect-only`**: operators running `pytest --collect-only` to see what will execute MUST see the injected contract tests. Verify in Phase B.
- **`uv build` produces a wheel containing the entry-point metadata**: `uv build && python -c "from importlib.metadata import entry_points; print(entry_points(group='pytest11'))"` — verify post-build. **Recommend: add as a Phase A smoke check.**

## Sources

- pytest 9.0.3 PyPI metadata — verified 2026-05-15 via PyPI JSON API (requires-python ≥3.10, 1300+ external plugins ecosystem)
- pytest-asyncio 1.1.0+ PyPI metadata — verified 2026-05-15 (declares `pytest<10,>=8.2`)
- hatchling 1.29.0 PyPI metadata — verified 2026-05-15 (released 2026-02-23)
- pytest-playwright 0.7.2 PyPI metadata — verified 2026-05-15 (released 2025-11-24)
- pytest hook reference: `pytest_runtest_logreport`, `pytest_collection_modifyitems`, `pytest_generate_tests`, `pytest_terminal_summary`, `pytest_addoption` — pytest official documentation
- pytest-factoryboy `register()` API pattern — public pattern, well-documented
- pytest-html reporter plugin architecture — the canonical pytest-reporter-plugin reference
- v1.3 codebase reads: `src/mcp_test_framework/fixtures.py`, `tests/contract/test_mcp_tool_contract.py`, `src/mcp_test_framework/cli.py`, `src/mcp_test_framework/_runner.py`, `pyproject.toml`
- v1.4 milestone seed reads: `.planning/seeds/SEED-015-library-mode-delivery.md`, `.planning/seeds/SEED-023-rename-sdet-surface-to-test-code.md`, `.planning/PROJECT.md` (Current Milestone section)
