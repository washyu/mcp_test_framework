# Feature Landscape — v1.4 Library Mode Delivery

**Domain:** pytest-plugin / importable test-library delivery for an MCP contract framework
**Researched:** 2026-05-15
**Overall confidence:** HIGH on patterns (well-trodden pytest plugin design), MEDIUM on the specific API shape (judgement calls — multiple defensible designs).

---

## TL;DR — The first 15 minutes (operator-facing)

What it should feel like for an operator dropping `mcp-test-framework` into their existing MCP server repo:

```
0:00–0:02   uv add --dev mcp-test-framework
0:02–0:04   open tests/conftest.py, paste 3 lines:
                from mcp_test_framework.contracts import register
                register(server_command=["uvx", "my-mcp"],
                         judge="ollama://127.0.0.1:11434/qwen3:0.6b")
0:04–0:08   uv run pytest -k mcp_contract       # picks up 20 cases × N tools
0:08–0:12   read green/red output in pytest's native form OR
                uv run pytest -k mcp_contract --mcp-domain-ui
0:12–0:15   add --judge=stub for CI without Ollama; tweak `tools=[...]` allowlist
```

If the operator's first 15 minutes require *anything else* — config file, separate CLI invocation, custom test file, pytest_plugins string in conftest, asyncio_mode tweak — the delivery model has leaked framework-author ergonomics into the operator surface (the exact failure mode SEED-015 names).

---

## Pattern survey — how peer plugins solve this

Cite-anchors for each design decision below. The table is "what the ecosystem actually does", not "what we should do" — the recommendation column comes later.

| Plugin | API shape | Where registered | Injection mechanism | Fixtures flow via | CLI? | Reporter? | Cite |
|--------|-----------|------------------|---------------------|-------------------|------|-----------|------|
| **pytest-playwright** | Pure fixtures + markers; no `register()` — operator just *uses* `page` / `browser` fixtures | Auto-loaded via `pytest11` entry-point. Operator overrides defaults by re-declaring fixtures (`browser_type_launch_args`, `browser_context_args`) in their `conftest.py` | Fixtures, not test injection — operator writes their own tests using the fixtures | Fixture override + `pytest.ini`/`pyproject.toml` CLI flags (`--browser`, `--headed`, `--video`) | No (pure plugin) | Yes — opt-in `--video`, `--screenshot`, `--tracing` | playwright.dev/python/docs/test-runners |
| **pytest-httpx** | Pure fixture (`httpx_mock`) + marker (`@pytest.mark.httpx_mock(...)`) | Auto-loaded via `pytest11`. Marker can be set globally via `pytestmark = pytest.mark.httpx_mock(...)` in root `conftest.py`, or via a `pytest_collection_modifyitems` hook to add the marker to every item | Fixtures only — operator writes assertions | Marker-driven config + fixture | No | No | github.com/Colin-b/pytest_httpx |
| **pytest-asyncio** | Marker (`@pytest.mark.asyncio`) + config knob (`asyncio_mode`, `asyncio_default_fixture_loop_scope`) | Auto-loaded via `pytest11`. Config in `pyproject.toml`'s `[tool.pytest.ini_options]` | Marker + collection hooks rewrite async tests/fixtures into sync-runnable wrappers | `[tool.pytest.ini_options]` settings | No | No | pytest-asyncio Context7 docs |
| **pytest-trio** | Same model as pytest-asyncio | `pytest11` + `[tool.pytest.ini_options].trio_mode = true` OR `@pytest.mark.trio` | Same | Config | No | No | python-trio/pytest-trio |
| **pytest-mock** | Pure fixture (`mocker`) | Auto-loaded via `pytest11` | Fixture only | Fixture body | No | No | pypi.org/project/pytest-mock |
| **pytest-django** | Marker (`@pytest.mark.django_db`) + many fixtures (`client`, `rf`, `db`, `transactional_db`) + `DJANGO_SETTINGS_MODULE` env or `pytest.ini` setting | `pytest11` + a single `django_settings` ini value (or env var) — Django itself does the heavy lifting | Markers gate DB access; fixtures wrap Django's test client | ini setting + env var + markers | No (django-admin handles that side) | Limited (db reuse summary) | pytest-django docs |
| **pytest-bdd** | `scenarios("features/")` call at module top-level, OR `@scenario(...)` decorator on a function | Called inline at module import time — directly injects parametrized test functions into the calling module | `scenarios()` programmatically discovers `.feature` files and creates one test function per scenario in the importing module's namespace | Fixture-style step-defs registered in `conftest.py` via `@given/@when/@then` | No | No | pytest-bdd.readthedocs.io |
| **pytest-benchmark** | Fixture (`benchmark`) + many CLI flags (`--benchmark-only`, `--benchmark-save`) + a custom group in pytest's terminal output | `pytest11` | Fixture | CLI flags read in plugin hook | Optional via `pytest-benchmark compare` subcommand on the user's own histories | Yes — custom terminal-summary section | github.com/ionelmc/pytest-benchmark |
| **pytest-xdist** | `-n NUM` flag | `pytest11` | Hooks reshape test execution into worker processes | CLI flag | No | Yes — custom progress reporter | pytest-xdist |
| **schemathesis (pytest mode)** | `schema = schemathesis.from_uri(...)` at module top-level; then `@schema.parametrize()` decorator on a test function — schemathesis injects every API operation as a parametrize-id | Function call at module-top-level + decorator on a *user-written* test stub | Hypothesis-driven test parametrization injected by the decorator | The function-call return holds config; decorator does the injection | Yes (separate `schemathesis run`) | Yes — also has a CLI runner | schemathesis.readthedocs.io |
| **pytest-trio / anyio plugins** | Same model as pytest-asyncio | Config + marker | Same | Config | No | No | — |

**Two patterns dominate; pick deliberately:**

1. **Fixture-only / Marker-only ("invisible plugin")** — pytest-playwright, pytest-httpx, pytest-mock, pytest-asyncio. Operator never calls `register()`; just imports nothing and uses fixtures. Config flows via `pyproject.toml` `[tool.pytest.ini_options]` or fixture-override.
2. **Inline-injection ("active library")** — pytest-bdd's `scenarios()`, schemathesis's `from_uri() + @parametrize`. Operator makes an explicit call at module-top-level; that call *injects* test functions into the importing module.

**The seed sketches `register()` — that's option 2.** It's the right call for this framework because the operator MUST point at their own MCP server (no sensible global default), and the auto-loaded fixture pattern can't express "spin up THIS server with THESE tools." But the precedent is narrower (pytest-bdd, schemathesis, hypothesis's `@given` are the only mainstream cases), so we should be deliberate about the ergonomics.

---

## Table-stakes features

Features the operator expects in 2026. Missing any = "this isn't really a pytest plugin."

### TS-1 — Auto-loaded plugin entry-point (no `pytest_plugins = [...]` needed)

**Why expected:** Every modern pytest plugin (playwright, httpx, asyncio, mock) self-registers via `[project.entry-points.pytest11]` in `pyproject.toml`. Operators who add the dep expect `pytest` to pick it up.
**Implementation:** Add `[project.entry-points.pytest11] mcp_test_framework = "mcp_test_framework.plugin"` to our `pyproject.toml`. `plugin.py` becomes the public plugin module that imports/exposes fixtures + hooks.
**Complexity:** Small.
**Depends on:** Nothing — pure packaging change. Cleanest first phase.
**Operator interaction:** Operator never sees this; it's the "no `pytest_plugins` boilerplate in conftest.py" gift.
**Cite:** pytest "Writing plugins" doc (docs.pytest.org/en/stable/how-to/writing_plugins.html), pytest-playwright pyproject, every pytest11 plugin in the ecosystem.

### TS-2 — `register()` call injects contract tests into operator's conftest

**Why expected:** The seed's three-line UX. Operator's conftest.py becomes:
```python
from mcp_test_framework.contracts import register
register(server_command=["uvx", "my-mcp"])
```
Pytest picks up ~7-10 contract tests × N tools without the operator writing a test file.
**Implementation:** `register()` stores config in a module-level registry, then `pytest_generate_tests` (hook installed by the plugin) reads the registry, discovers tools at collection time, and calls `metafunc.parametrize` to inject one test-case per tool per assertion. Alternatively (cleaner): `register()` returns nothing but installs a "synthetic test module" via `pytest_collectstart` / `pytest_collection_modifyitems`. **Recommend the parametrize path** — it's the same mechanism `tests/contract/test_mcp_tool_contract.py` already uses today; we're just moving the data source from `tests/conftest.py:_resolve_tool_names` to a function arg.
**Complexity:** Medium. The hook plumbing is well-trodden, but the "discover tools live during collection" piece needs care — collection runs once per session, but the MCP handshake is async, so we either need a sync wrapper or we need to use `pytest_configure` (which CAN run async if we adopt anyio's eager-pump approach, but it's brittle). **Recommend** caching tool discovery in a session-scoped autouse fixture and emitting "pending parametrize" markers that the fixture resolves — pattern stolen from pytest-bdd's lazy step-binding.
**Depends on:** TS-1 (plugin must exist), CONTRACT-REORG-1 below.
**Operator interaction:** Operator MUST call `register()` — if they don't, the plugin is dormant (no auto-collection, no surprise tests appearing). This is the explicit-over-magic call.
**Cite:** pytest "How to parametrize" (`metafunc.parametrize`); pytest-bdd's `scenarios()` pattern.

### TS-3 — Fixtures auto-available once plugin loads

**Why expected:** Once the plugin is auto-loaded (TS-1), the operator's `tests/test_my_business_logic.py` can request `mcp_client`, `mcp_session`, `judge`, `target_tool`, `tool_config` without copying `src/mcp_test_framework/fixtures.py`. This is how pytest-playwright's `page` fixture appears.
**Implementation:** The plugin module (`mcp_test_framework.plugin`) `from .fixtures import *` (or re-exports the fixture functions). pytest's plugin loader sees them and makes them available. We already have the session-scoped fixture set in `src/mcp_test_framework/fixtures.py`; the v1.4 work is wiring + naming + documentation.
**Complexity:** Small. Trickier piece: today's fixtures pull from `config` (`Config()`) which reads `MCPTF_CONFIG_FILE`. In library mode the config source is the `register()` kwargs. Need a Config-provider seam — see LIB-CONFIG-1.
**Depends on:** TS-1, LIB-CONFIG-1.
**Operator interaction:** Operator MAY use fixtures directly in their own scenario tests (especially relevant for the SDET / test-code surface). MUST use them via `register()` for the contract injection.
**Cite:** pytest-playwright fixture pattern (playwright.dev/python/docs/test-runners), pytest-httpx (Colin-b/pytest_httpx README).

### TS-4 — Operator's existing pytest invocation Just Works

**Why expected:** `uv run pytest` (the command they already type) discovers the injected contract tests + their own tests + runs them through the same pytest pipeline. No `mcp-test-framework run` required.
**Implementation:** Falls out for free once TS-1 + TS-2 + TS-3 land. Verification = the framework's own dogfood: a self-test that imports `register()` in a fixture-conftest and asserts that `pytest --collect-only` shows the expected node IDs.
**Complexity:** Small (mostly a dogfood test that proves the prior three).
**Depends on:** TS-1, TS-2, TS-3.
**Operator interaction:** Operator MUST adapt their CI step from `mcp-test-framework run` to plain `pytest` (if they care — CLI also still works).
**Cite:** every pytest plugin ever.

### TS-5 — Pytest-native output by default (no domain UI imposed)

**Why expected:** pytest-playwright doesn't override pytest's terminal reporter. pytest-httpx doesn't. pytest-asyncio doesn't. The operator already knows how to read pytest output (dots/F/E, `--verbose` for test names, `-v --tb=short` for failures). Imposing a custom renderer = "this isn't pytest, this is a tool that uses pytest."
**Implementation:** No-op on the test-injection side. Plugin emits *parametrize IDs* that read well (`test_schema_passes_structural_checks[list_keyring_credentials]`) and lets pytest's default reporter render them. The Phase 14 domain UI moves to opt-in (REP-1 below).
**Complexity:** Small / negative — we *remove* the runner's domain-UI auto-rendering for library-mode invocations. CLI mode keeps it.
**Depends on:** REP-1's design (need to confirm domain UI as opt-in, not default).
**Operator interaction:** Operator never sees the domain UI unless they ask for it. Default is `.` `.` `.` `F` `.` (pytest's terminal reporter), exactly like pytest-playwright.
**Cite:** pytest-playwright, pytest-httpx (neither overrides the reporter).

### TS-6 — Selection via `-k` and markers (no custom selectors)

**Why expected:** Operator already knows `pytest -k smoke`, `pytest -m slow`, `pytest tests/test_unit.py::test_foo`. Library mode must expose tests via the same selectors.
**Implementation:** Inject contract tests with stable, selectable identity:
- A class-marker like `@pytest.mark.mcp_contract` on every injected test so the operator can `-m mcp_contract` or `-m "not mcp_contract"`.
- Predictable test names (`test_<rubric>[<tool_name>]`) so `-k` works (`pytest -k schema`, `pytest -k list_keyring_credentials`).
- Register the marker via `pytest_configure(config)` so the operator doesn't get a `PytestUnknownMarkWarning`.
**Complexity:** Small. Marker registration is `config.addinivalue_line("markers", "mcp_contract: ...")`. Test naming is already what we do.
**Depends on:** TS-2.
**Operator interaction:** Operator MAY use `-k` / `-m` to filter the framework's tests away from their own (e.g. `pytest -m "not mcp_contract"` for their unit test runs, `pytest -m mcp_contract` for the contract-only CI step).
**Cite:** pytest "How to use markers" doc; standard pytest selectors.

### TS-7 — Kwargs mirror the v1.3 `config.yaml` keys 1:1

**Why expected:** Operators with an existing `config.yaml` can copy values into `register()` calls and vice-versa. Reduces conceptual surface to one schema.
**Implementation:**
```python
register(
    server_command=["uvx", "my-mcp"],   # cfg.mcp_server.command + .args
    server_timeout=60,                   # cfg.mcp_server.timeout_seconds
    judge="ollama://127.0.0.1:11434/qwen3:0.6b",  # cfg.ollama.base_url + .model
    tools=["foo", "bar"],                # cfg.tools (allowlist)
    tool_config={"foo": {"call_arguments": {"x": 1}}},  # cfg.tools.<name> body
    judge_pass_threshold=4,
)
```
We build a `Config` Pydantic model from kwargs (reusing the v1.3 model). YAML-mode and library-mode hit the same target. The two URL-style shorthands (`judge="ollama://..."`) are sugar over splitting into `ollama.base_url` + `ollama.model`.
**Complexity:** Medium. Designing the kwargs surface is the bikeshed risk. Recommend: thin layer that builds `Config(**kwargs)` and forwards. The URL shorthand for `judge=` is one parser function and pays for itself in onboarding clarity.
**Depends on:** LIB-CONFIG-1.
**Operator interaction:** Operator MUST pass at least `server_command`. Everything else has defaults.
**Cite:** Inspired by httpx's URL-string config, OpenAI SDK's `base_url` + `api_key` pair.

### TS-8 — `pyproject.toml` `[tool.pytest.ini_options]` for non-call-site config

**Why expected:** Modern plugins accept config in `pyproject.toml` so the operator doesn't have to duplicate values across `register()` calls in multiple conftests. Examples: pytest-asyncio's `asyncio_mode`, pytest-django's `DJANGO_SETTINGS_MODULE`.
**Implementation:** Add a small `[tool.pytest.ini_options]` section the operator can write:
```toml
[tool.pytest.ini_options]
mcp_judge = "ollama://127.0.0.1:11434/qwen3:0.6b"
mcp_judge_threshold = 4
asyncio_mode = "strict"   # we'll co-opt this
asyncio_default_fixture_loop_scope = "session"   # required for our session-scoped MCP client
```
Read via `pytest_addoption` + `config.getini("mcp_judge")`. `register()` kwargs override `pyproject` values (which override defaults).
**Complexity:** Small. Mostly: define the precedence (kwargs > pyproject > defaults) and document it.
**Depends on:** LIB-CONFIG-1, TS-7.
**Operator interaction:** Operator MAY use this to keep `register()` calls short. MUST set `asyncio_default_fixture_loop_scope = "session"` because our fixtures require it — see LIB-ASYNC-1.
**Cite:** pytest-asyncio `[tool.pytest.ini_options]`, pytest-django `pytest.ini` settings.

### TS-9 — Coexist with operator's existing tests cleanly

**Why expected:** The operator's `tests/test_my_business_logic.py` already exists. The framework's tests must not break their tests. Specifically: no global `asyncio_mode = "auto"`, no autouse fixture that runs for every test (only ours), no global `pytest_collection_modifyitems` that rewrites foreign items.
**Implementation:**
- The `_preflight` autouse fixture **must scope itself** — it already does via `_session_needs_preflight` (live-MCP-scope check). v1.4 reframes this from "scope = `tests/contract/`+`tests/sdet/`" to "scope = items with the `mcp_contract` / `mcp_test_code` marker." The marker becomes the live-MCP signal.
- Plugin hooks (`pytest_collection_modifyitems`, etc.) MUST early-return when no `register()` call has happened (registry empty).
- Plugin MUST NOT set global pytest defaults — only document them as required.
**Complexity:** Medium. The scope-from-path → scope-from-marker rewrite is a known v1.3 fragility (see fixtures.py:117 comment) and v1.4 is the right time.
**Depends on:** TS-2, TS-6.
**Operator interaction:** Operator never sees this; it's the "the plugin doesn't break my unit tests" gift.
**Cite:** pytest-asyncio strict-mode rationale (avoids hijacking unmarked tests). The path-prefix→marker rewrite resolves a known fragility in our own `_preflight`.

### TS-10 — Diagnostics surface when things go wrong

**Why expected:** Today's CLI emits an "operator-tone" error (see `_pytest_exit_operator_tone` in fixtures.py) — "Cannot reach Ollama judge at...; next: verify Ollama is running with `ollama serve`". That UX must survive into library mode.
**Implementation:** Already implemented in `fixtures.py` — `pytest.exit(reason, returncode=2)` with operator-tone formatting. The fixture-level diagnostics work the same in library mode (pytest prints the exit reason).
**Complexity:** Small (carry-forward — already exists).
**Depends on:** Existing v1.3 work.
**Operator interaction:** Operator sees the same diagnostic shape when Ollama is down / MCP binary missing / config invalid.
**Cite:** docs/ERROR-STYLE.md (project-internal).

---

## Differentiators

Features that distinguish library mode from "just another pytest plugin." Not expected, but valued.

### DIFF-1 — Opt-in domain UI reporter plugin

**Value prop:** The Phase 14 domain UI ("MCP server: ..., Discovered: N tools, Running: ...,  Result: 20 PASS / 0 FAIL / 560 SKIP") is genuinely better than pytest's `.....F.` for someone scanning a 70-tool run. Operators who want it can opt in with `pytest --mcp-domain-ui`.
**Implementation:** The current `_runner.py` reads JUnit XML *post-hoc*. The library-mode version becomes a `pytest_runtest_logreport` reporter that consumes `TestReport` objects live, populates the same `ParsedRun` / `ToolVerdict` model, and renders at `pytest_terminal_summary` time. The `_render_per_tool_rows` logic is data-driven and ports unchanged; only the input plumbing changes (JUnit XML → live TestReport events).
**Complexity:** Medium. The renderer code is already there; what changes is the event source. Risk: `pytest_runtest_logreport` fires three times per test (setup, call, teardown) — need to aggregate. Pattern stolen from `pytest-html`.
**Depends on:** TS-1, TS-2, TS-3.
**Operator interaction:** Operator MAY pass `--mcp-domain-ui` (CLI flag) OR set `pyproject.toml`'s `[tool.pytest.ini_options].mcp_domain_ui = true`. Default OFF.
**Why opt-in not autoload:** Autoloading the reporter would override pytest's default terminal output for operators who never asked for it — violation of TS-5.
**Cite:** pytest's `pytest_runtest_logreport` hook (docs.pytest.org/en/stable/reference/reference.html), pytest-benchmark's terminal-summary pattern (github.com/ionelmc/pytest-benchmark), pytest-html's report-consumer pattern.

### DIFF-2 — `--judge=stub` for CI without Ollama

**Value prop:** Many operators want the schema + output-conformance checks in their PR CI but don't want a GPU-equipped runner for the Ollama judge. A `stub` judge backend that auto-passes (or auto-skips) the rubric tests lets contract-CI run on free GitHub-Actions runners; the full judge run happens on a self-hosted nightly.
**Implementation:** Already half-built — we have `judge_protocol.Judge` Protocol. Add `StubJudge` that returns `JudgeResult(score=5, reasoning="stub backend; rubric not evaluated")`. Wire `--judge=stub` (CLI flag → `register(judge="stub://")`) and `[tool.pytest.ini_options].mcp_judge = "stub://"`.
**Complexity:** Small. The Protocol seam is the v1.0 JUDGE-01 enabler shipping at zero cost.
**Depends on:** TS-7, TS-8 (judge URL parsing).
**Operator interaction:** Operator MAY pass `--judge=stub` for fast contract-only runs.
**Note:** This unblocks v1.5's OpenAI-compat backend (SEED-005) by exercising the Judge Protocol seam in a second backend.
**Cite:** Existing `judge_protocol.Judge` Protocol in this repo.

### DIFF-3 — Per-tool `[tool.pytest.ini_options]` tool config

**Value prop:** Today's `config.yaml` has `tools.<name>` blocks (skip / call_arguments / judges allowlist). Library mode operators who don't want to also keep a config file can express the same in `register()` kwargs OR pyproject.
**Implementation:** `register(tool_config={"foo": {"skip": True}, "bar": {"call_arguments": {"x": 1}}})`. Pydantic validates per-tool entries the same way `Config.tools` does today.
**Complexity:** Small. Just an extra kwarg → `Config.tools` mapping.
**Depends on:** TS-7.
**Operator interaction:** Operator MAY express per-tool overrides without a YAML file.
**Cite:** v1.3 TOOLCFG-01..07 (existing); pytest-django's per-test `@pytest.mark.django_db(transaction=True)` pattern.

### DIFF-4 — `scoped_register()` context-manager for nested test classes

**Value prop:** The seed mentions this. Operators with multiple MCP servers (one per microservice) can scope `register()` to a test class:
```python
class TestServiceA:
    with scoped_register(server_command=["uvx", "service-a"]):
        # injected tests here only
```
**Complexity:** Medium. Requires the registry to be stack-aware, hooks to read the topmost stack entry.
**Depends on:** TS-2.
**Operator interaction:** Operator MAY use for multi-server repos. Probably <5% of operators in v1.4 — defer to v1.5 if scope-pressed.
**Recommendation:** Defer to v1.5. Single-server `register()` is enough for the milestone.
**Cite:** Seed SEED-015 line 82.

### DIFF-5 — `gen-test-classes` and the SDET/test-code surface ship in the same package

**Value prop:** Once `register()` is the primary surface, operators who graduate from "I just want contract checks" to "I want to author my own scenario tests" don't install a second tool. `mcp_test_framework.test_code` (post-rename) exposes `mcp_session`, `tool()`, `ToolCallError`, and the `<Tool>Params`/`<Tool>Response` codegen target.
**Implementation:** Carry-forward — already shipped in v1.3 under the `sdet` name. v1.4 work is the SEED-023 rename (`sdet` → `test_code`) and the import-path stability commitment.
**Complexity:** Medium. The rename touches code, docs, requirements, planning artifacts (see SEED-023 blast radius §). Scope-wise, this is its own phase before the public-API lockdown.
**Depends on:** The rename MUST land BEFORE TS-2 is documented externally — once `mcp_test_framework.contracts.register` is on PyPI, the sibling import path `mcp_test_framework.sdet` vs `mcp_test_framework.test_code` is no longer renameable without a deprecation cycle.
**Operator interaction:** Operator MAY graduate from contract pass to scenario authoring without changing dep. Most operators will only ever use the contract surface (90/10 — see PROJECT.md primary audience).
**Cite:** SEED-023 rename plan; v1.3 SDET-01..04.

### DIFF-6 — Codegen output path defaults to `tests/_generated/<server_slug>/`

**Value prop:** Today's `cfg.sdet.generated_root` is a REQUIRED field — operator must set it. In library mode where the framework is `pip install`'d, the v1.3 default (under the framework's `src/`) is unwritable; library-mode operators should get a sensible default in *their* tree.
**Implementation:** Default `generated_root` to `tests/_generated/` when (a) the operator's cwd has a `tests/` directory AND (b) no explicit override is set. Fall back to fail-loud if no `tests/` and no explicit override.
**Complexity:** Small. Detect-and-default in `Config.__init__` or `register()`'s kwargs-builder.
**Depends on:** SEED-023 rename (path becomes `tests/_generated/` not `tests/sdet/_generated/`).
**Operator interaction:** Operator MAY override. MAY accept the default. Default = "where pytest already looks."
**Cite:** SEED-015 § "Codegen output path must become configurable"; operator quote 2026-05-13.

### DIFF-7 — `register()` returns a handle for advanced introspection

**Value prop:** Returns a `RegistrationHandle` exposing `.discovered_tools`, `.selected_tools`, `.skipped` — operators can `assert len(handle.discovered_tools) == 7` to fail fast if their MCP server's tool count changes unexpectedly.
**Complexity:** Small. Just a return value; no behavior change.
**Depends on:** TS-2.
**Operator interaction:** Operator MAY ignore the return value (default path) OR MAY inspect for assertions.
**Recommendation:** Include in v1.4. Costs nothing, opens authoring patterns.
**Cite:** schemathesis's `from_uri()` returns a Schema object operators inspect.

### DIFF-8 — Async-marker auto-application

**Value prop:** Today's contract tests carry `pytestmark = [pytest.mark.asyncio(loop_scope="session")]`. In library mode, the injected tests need the same marker — operators shouldn't have to know our async discipline.
**Implementation:** When `pytest_generate_tests` injects parametrize cases, also apply the `asyncio(loop_scope="session")` marker to the test function. Pytest-asyncio honors per-test markers.
**Complexity:** Small. One `metafunc.definition.add_marker(...)` call.
**Depends on:** TS-2.
**Operator interaction:** Operator never sees this; their `pyproject.toml` needs `asyncio_default_fixture_loop_scope = "session"` (we document this in TS-8).
**Cite:** pytest-asyncio docs on `loop_scope`.

---

## Anti-features (deliberately NOT building)

| Anti-feature | Why avoid | What to do instead |
|--------------|-----------|--------------------|
| **Auto-call `register()` from `pyproject.toml`** | Magical config-driven test injection (the framework sees no Python entry-point from the operator) violates explicit-over-magic; operators can't grep for `register(` to find where tests come from | Always require a Python-level `register(...)` call in `conftest.py`. Keep `[tool.pytest.ini_options]` for *values*, not *activation*. |
| **Domain UI as default reporter** | Hijacks pytest's terminal output for every operator, including those who never opted in. Same trap pytest-asyncio's `auto` mode falls into | Opt-in `--mcp-domain-ui` flag (DIFF-1). Default is pytest's `.F.E` reporter (TS-5). |
| **A "wrapper" CLI that re-implements pytest** | Today's `mcp-test-framework run` subprocesses pytest. Library mode means pytest IS the runner. Keeping CLI mode as a parallel re-runner makes the two modes diverge (the v1.3 destination) | Keep `mcp-test-framework run` as a thin shim over `pytest <args>` for CI one-liners; demote to optional convenience (SEED-015 § "CLI demotes"). |
| **A separate `mcp-test-framework-lib` package** | Two PyPI names for one framework doubles the install surface | One package, two surfaces (CLI + library). Standard pattern — see flask vs flask-cli (flask ships both). |
| **`mcp_test_framework.testing.pytest`-style nested namespace** | The seed proposes `mcp_test_framework.contracts` (descriptive, matches SEED-010 split language) — alternative names like `.testing`, `.api`, `.pytest_plugin` are less informative | Pick `mcp_test_framework.contracts.register` and stick with it. |
| **Per-MCP-server kwargs sprawl on `register()`** | If `register()` keeps growing kwargs (judge_*, server_*, tool_*, isolation_*, reporter_*) it becomes a god-function. pytest-asyncio's `asyncio_mode` is a single knob; httpx's `httpx_mock.add_response` is one method | Pass a `Config` object directly OR pass kwargs that mirror `Config` 1:1 (TS-7). Resist adding "register-only" kwargs that don't live in `Config`. |
| **A `requires_homelab(...)`-style marker for SUT-aware skipping** | SEED-022 lock — framework primitives only, no SUT-specific surface | Operators use stock pytest primitives (`@pytest.mark.skipif`) in their own test code. |
| **Auto-discovery of MCP servers from the operator's `pyproject.toml`** | Magical; assumes a convention the operator may not follow | Explicit `server_command=[...]` in `register()`. |
| **Multiple `register()` calls in one conftest** | Today's `Config` model is single-server. Adding multi-server in v1.4 doubles the scope | Single `register()` per conftest. Multi-server is a v1.5+ ask via `scoped_register()` (DIFF-4 deferred). |
| **CLI flag → library-only feature parity (or vice versa)** | If `--explain` only works in CLI mode, `--mcp-domain-ui` only works in library mode, operators learn two incompatible surfaces | Every CLI flag has a `[tool.pytest.ini_options]` equivalent OR is structurally CLI-only (`config-init` makes no sense in library mode). |

---

## Feature dependency graph

```
TS-1 (entry-point)
  ├─→ TS-3 (auto-fixtures)
  │     ├─→ LIB-ASYNC-1 (asyncio config docs)
  │     └─→ TS-9 (coexist)
  │           └─→ scope-by-marker rewrite (touches fixtures.py:117)
  ├─→ TS-2 (register-injects-tests)
  │     ├─→ TS-4 (pytest works)
  │     ├─→ TS-6 (markers + -k)
  │     ├─→ DIFF-1 (reporter)
  │     ├─→ DIFF-7 (handle)
  │     └─→ DIFF-8 (async marker auto-apply)
  └─→ LIB-CONFIG-1 (kwargs→Config seam)
        ├─→ TS-7 (kwargs mirror YAML)
        │     └─→ DIFF-3 (per-tool overrides)
        ├─→ TS-8 (pyproject ini)
        └─→ DIFF-2 (stub judge URL)

CONTRACT-REORG-1 (move test_mcp_tool_contract.py → src/)
  └─→ TS-2

SEED-023 RENAME (sdet → test_code)
  ├─→ MUST land before public-API freeze on TS-3
  └─→ DIFF-5, DIFF-6

TS-10 (operator-tone errors) — carry-forward, no new dep
```

**Critical-path summary:**
1. **Rename first.** SEED-023 (`sdet` → `test_code`) is irreversible after first PyPI publish. Block on this.
2. **Plugin entry-point next.** TS-1 — small, foundational.
3. **Config seam.** LIB-CONFIG-1 + TS-7 + TS-8 — the kwargs/pyproject/YAML unification.
4. **Contract reorg + register().** CONTRACT-REORG-1 + TS-2 — moves the test logic from `tests/contract/` into `src/`, with `register()` as the injection API.
5. **Fixtures auto-available + coexist.** TS-3 + TS-9 — the scope-by-marker rewrite lives here.
6. **Markers + selectors.** TS-6 — small, polish.
7. **Reporter plugin.** DIFF-1 — adapt `_runner.py` to live event consumption.
8. **Differentiators.** DIFF-2 (stub judge), DIFF-3 (per-tool kwargs), DIFF-6 (default generated path), DIFF-7 (handle), DIFF-8 (async marker).
9. **Carry-forward UAT closure** — README sample, Phase 17 SC1, v1.2 Phase 13/14.

---

## MVP recommendation for v1.4

**Must ship (table stakes + the rename):**
- SEED-023 rename (`sdet` → `test_code`) — entire blast radius (code, requirements, docs, planning IDs)
- TS-1 plugin entry-point
- TS-2 `register()` + parametrize injection
- TS-3 auto-fixtures
- TS-4 pytest works
- TS-5 pytest-native default output
- TS-6 markers + `-k`
- TS-7 kwargs ↔ Config 1:1
- TS-8 `[tool.pytest.ini_options]`
- TS-9 coexist cleanly (scope-by-marker rewrite)
- TS-10 operator-tone errors (verify carry-forward)
- CONTRACT-REORG-1 move parametrized tests into `src/`
- LIB-CONFIG-1 config seam
- LIB-ASYNC-1 documented asyncio settings
- Carry-forward UAT closure (README sample, Phase 17 SC1, v1.2 Phase 13/14)

**Should ship (high value, low complexity):**
- DIFF-1 opt-in domain UI reporter
- DIFF-2 stub judge backend
- DIFF-3 per-tool kwargs
- DIFF-6 default generated_root → `tests/_generated/`
- DIFF-7 register() return handle
- DIFF-8 async marker auto-application

**Defer to v1.5+:**
- DIFF-4 `scoped_register()` — wait for a real multi-server operator
- xdist parallelism (SEED-002) — stable library API first
- OpenAI-compat judge (SEED-005) — DIFF-2 stub backend already exercises the seam

---

## Open design questions (decide during phase planning, not now)

1. **`register()` vs class decorator vs scenarios()-style.** SEED-015 sketches `register()`. pytest-bdd uses both `scenarios()` (top-level call) and `@scenario` (decorator). schemathesis uses `@schema.parametrize`. The seed's call is the right default — most-explicit, hardest-to-misuse.
2. **What does the URL shorthand for judge look like?** `judge="ollama://host:port/model"` vs `judge="ollama"` + separate `ollama_*` kwargs vs `judge=Judge.ollama(...)`. URL form is densest but parsing is a small surface; bikeshed-worthy.
3. **Tool discovery timing — collection-time vs first-test-time?** Today's `tests/conftest.py:_resolve_tool_names` does it at collection time (sync wrapper around async). Library-mode `register()` can do the same; a lazier approach where the first test triggers discovery is cleaner but breaks `pytest --collect-only`. Recommend collection-time, matches today's behavior.
4. **Plugin module path: `mcp_test_framework.plugin` vs `mcp_test_framework.pytest_plugin` vs `mcp_test_framework._plugin`?** Convention is no consensus. pytest-asyncio uses `pytest_asyncio.plugin`. Recommend `mcp_test_framework.plugin` (single canonical, no underscore — this IS the public plugin).
5. **Where do contract tests *physically* live in `src/`?** Seed says `src/mcp_test_framework/contracts/`. Alternatives: `src/mcp_test_framework/_contract_tests.py` (underscore = "don't import directly"), `src/mcp_test_framework/contract.py` (singular). Recommend `src/mcp_test_framework/contracts/__init__.py` re-exports `register`, with implementation in `_tests.py` siblings.
6. **What's the deprecation policy for the CLI?** Seed says "demotes to optional convenience, never removed." Lock that policy in v1.4 docs so we don't accidentally drift toward removal in v1.5+.
7. **Should `register()` validate the server is reachable eagerly?** Today's `_preflight` runs on session start (collection-time). Library mode can either keep that (single preflight) or do eager-validate inside `register()` (fail at conftest-import-time). Recommend keep `_preflight` (eager validate inside `register()` blocks `pytest --collect-only` against an offline MCP — bad UX).

---

## Sources

**HIGH confidence (Context7 / official docs / our own codebase):**
- pytest "Writing plugins" — https://docs.pytest.org/en/stable/how-to/writing_plugins.html
- pytest "Reference: customize" / `[tool.pytest.ini_options]` — https://docs.pytest.org/en/stable/reference/customize.html
- pytest "How to parametrize" — https://docs.pytest.org/en/stable/how-to/parametrize.html
- pytest "Hook reference: pytest_runtest_logreport" — https://docs.pytest.org/en/stable/reference/reference.html
- pytest-playwright "Pytest Plugin Reference" — https://playwright.dev/python/docs/test-runners
- pytest-httpx README — https://github.com/Colin-b/pytest_httpx
- pytest-bdd docs — https://pytest-bdd.readthedocs.io/en/stable/
- This repo: `src/mcp_test_framework/fixtures.py`, `tests/contract/test_mcp_tool_contract.py`, `src/mcp_test_framework/_runner.py`, `.planning/seeds/SEED-015-library-mode-delivery.md`, `.planning/seeds/SEED-023-rename-sdet-surface-to-test-code.md`, `.planning/PROJECT.md`

**MEDIUM confidence (WebSearch corroborated by multiple sources):**
- pytest11 entry-point precedence (pyproject `[project.entry-points.pytest11]`) — verified across pytest docs, setuptools docs, blog.pecar.me, github issue 10721
- pytest-benchmark terminal-summary reporter pattern — github.com/ionelmc/pytest-benchmark
- schemathesis `@schema.parametrize` injection model — schemathesis.readthedocs.io
- pytest-asyncio `[tool.pytest.ini_options]` config keys — pytest-asyncio Context7 docs

**LOW confidence (single-source / inference):**
- Specific 2026 adoption rates of `register()`-style APIs in pytest plugins — qualitative judgment, not measured
- Whether operators prefer URL-style `judge="ollama://..."` vs split kwargs — design intuition, not user-tested

**Not verified (flag for phase planning):**
- Behavior of `pytest --collect-only` against a `register()`-injected suite when the MCP server is unreachable — needs a Phase 1 spike
- Whether `pytest_runtest_logreport` event ordering survives `pytest-xdist` (relevant when SEED-002 lands in v1.5) — needs verification before DIFF-1 implementation locks in a design that breaks under xdist
