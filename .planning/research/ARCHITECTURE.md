# Architecture Patterns — v1.4 Library Mode Delivery

**Domain:** Library-mode delivery for an existing pytest-based test framework (mcp_test_framework)
**Researched:** 2026-05-15
**Mode:** Project Research — ARCHITECTURE (subsequent milestone, additive)
**Overall confidence:** HIGH (pytest plugin patterns are stable since pytest 3.x; codebase is fully read; SEED-015 already enumerates the surface; SEED-022 invariant is mechanically enforced and well-understood)

---

## TL;DR — The Architecture in One Diagram

```
                        +-------------------------------------------+
                        |        operator's MCP server repo         |
                        |                                           |
                        |  pyproject.toml                           |
                        |    [dev-dependencies]                     |
                        |    mcp-test-framework>=1.4                |
                        |                                           |
                        |  tests/conftest.py                        |
                        |    from mcp_test_framework.contracts \    |
                        |      import register                      |
                        |    register(                              |
                        |      server_command=["uvx","my-mcp"],     |
                        |      tools=["foo","bar"],                 |
                        |    )                                      |
                        |                                           |
                        |  tests/test_my_business_logic.py  (theirs)|
                        +-------------------+-----------------------+
                                            |
                                            | `uv run pytest`
                                            v
+--------------------------------------------------------------------------+
|              pytest process (operator-side, library mode)                |
|                                                                          |
|  1. pytest11 entry-point auto-loads:                                     |
|     mcp_test_framework._plugin                                           |
|        - registers fixtures from mcp_test_framework.fixtures             |
|        - installs pytest_generate_tests hook (parametrize)               |
|        - installs pytest_collection_modifyitems hook (inject contracts)  |
|        - installs pytest_runtest_logreport hook (live domain UI, opt-in) |
|                                                                          |
|  2. operator's tests/conftest.py is imported by pytest:                  |
|     register(...) call writes an _Intent record into                     |
|     mcp_test_framework.contracts._registry  (module-level state)         |
|                                                                          |
|  3. Plugin's pytest_collection_modifyitems reads the registry,           |
|     calls into contracts._tests (parametrized contract test bodies),     |
|     and injects them into the operator's pytest session.                 |
|                                                                          |
|  4. Tests run alongside operator's own tests; same exit code.            |
+--------------------------------------------------------------------------+

                                +-------------+
                                |    SAME     |
                                |   core lib  |
                                +------+------+
                                       |
                                       v
+--------------------------------------------------------------------------+
|             CLI process (`mcp-test-framework run`, still supported)      |
|                                                                          |
|  cli.py:run                                                              |
|    - resolves config (CLI > env > YAML)                                  |
|    - spawns subprocess: pytest tests/contract/ ...                       |
|    - subprocess pytest's pytest11 entry-point loads the SAME plugin      |
|    - subprocess pytest runs and writes JUnit XML to a tempfile           |
|    - cli reads tempfile, calls render_domain_ui (still JUnit-XML driven) |
|                                                                          |
|  Effectively: CLI is a *separate* operator who happens to be us.         |
|  It uses register() the same way an external operator does, just         |
|  injected via a built-in conftest in tests/contract/.                    |
+--------------------------------------------------------------------------+
```

The single most important architectural insight: **the CLI becomes one
of `register()`'s clients, not a parallel implementation.** Everything
the operator can do, the CLI does — by calling `register()` itself.

---

## 1. `register()` — Where It Lives and What It Returns

### Module path

`src/mcp_test_framework/contracts/__init__.py`

```python
from mcp_test_framework.contracts._api import register, scoped_register
from mcp_test_framework.contracts._tests import (
    test_target_tool_exists,
    test_schema_passes_structural_checks,
    test_description_min_length,
    test_every_parameter_has_description_and_type,
    test_description_clarity,
    test_description_disambiguation,
    test_parameters_self_explanatory,
    test_empty_args_call_returns_non_error,
    test_result_has_content_or_structured,
    test_text_content_parses_as_json,
)

__all__ = ["register"]   # scoped_register held back to v1.5
```

The submodule `_tests` contains the parametrized test bodies extracted
verbatim from `tests/contract/test_mcp_tool_contract.py`. The leading
underscore signals "internal — the public surface is `register()`,
not these function names."

### Recommended shape: module-level call

```python
# operator's tests/conftest.py
from mcp_test_framework.contracts import register

register(
    server_command=["uvx", "my-mcp"],
    tools=["foo", "bar"],
    judge="ollama://127.0.0.1:11434/qwen3:0.6b",
    # all other Config fields available as kwargs; YAML overlay also supported
    config_file="config.yaml",   # optional
)
```

**What it returns:** `None`. It has a side effect: appends an `_Intent`
dataclass to a module-level `_REGISTRATIONS: list[_Intent]` slot inside
`mcp_test_framework.contracts._registry`.

**Why not a fixture factory?** Fixtures cannot inject *new* test items
into pytest's collection; they only parametrize / configure existing
ones. The contract test bodies need to appear as collected items even
though the operator's tests/ folder has no file that imports them.

**Why not a decorator?** Decorators only work on existing functions in
the operator's tree. The contract tests live in our package, not
theirs. A decorator could mark the operator's *own* conftest as
"please load my contract tests" — but that's a less clear surface than
the imperative `register()`.

**Why not autouse plugin reading `pyproject.toml`?** Two reasons:
(1) operators would have to learn yet another config surface, and
(2) it can't be unit-tested cleanly (no path for the test to register
"the same way an operator would"). Both deferred to a future seed if
demand surfaces.

### `_Intent` dataclass

```python
# src/mcp_test_framework/contracts/_registry.py
@dataclass(frozen=True)
class _Intent:
    """One register() call's worth of intent.

    Frozen so a stray `intent.tools.append(...)` between collection
    and test-execution can't corrupt the parametrize plan.
    """
    server_command: tuple[str, ...]    # frozen, not list
    tools: tuple[str, ...] | None      # None = auto-discover
    config: Config                     # the resolved, frozen Pydantic Config
    judges_subset: tuple[str, ...] | None = None
    # ...other knobs from SEED-015 sketch

_REGISTRATIONS: list[_Intent] = []
```

The `Config` field is the load-bearing detail: `register()` accepts
either a `config_file=PATH` kwarg or scalar kwargs (`server_command=`,
`ollama_base_url=`, etc.) and resolves them into the *same* frozen
`Config` model the CLI uses. **Single source of truth at the Pydantic
boundary.**

---

## 2. How Contract Tests Get Injected Into the Operator's Collection

This is the load-bearing architectural question. Three viable
mechanisms, in order of complexity:

### Recommended: `pytest_collection_modifyitems` hook reading `_REGISTRATIONS`

The plugin's `pytest_collection_modifyitems` runs AFTER the operator's
`conftest.py` has been imported (so `register()` has populated
`_REGISTRATIONS`). At that point we know exactly what contract tests
to inject. **But** `modifyitems` cannot create new items — only filter
/ reorder them.

So the actual mechanism is two hooks working together:

1. **`pytest_collect_file`** (returns a synthetic `pytest.Module` from
   a virtual file path). We provide a `Module` whose contents are the
   parametrized contract tests. pytest's collection machinery
   parametrizes and turns them into `Item`s the operator's session
   "owns."
2. **`pytest_generate_tests`** (already in our codebase, in
   `tests/conftest.py`) populates the `target_tool` indirect
   parametrize from `_REGISTRATIONS[*].tools` plus discovery.

Concretely:

```python
# src/mcp_test_framework/_plugin.py  (NEW MODULE, the pytest11 entry point)

from pathlib import Path
import pytest

from mcp_test_framework.contracts import _registry, _tests as _contract_tests


def pytest_collect_file(parent, file_path):
    """Synthesize a virtual contracts module the first time collection runs.

    Returns a single pytest.Module for the "virtual" path
    `<rootdir>/__mcp_test_framework_contracts__.py`. Operator never
    sees this file on disk; pytest only needs the path to be unique
    within the session.
    """
    if _registry._REGISTRATIONS and not _registry._INJECTED:
        _registry._INJECTED = True   # idempotency latch
        virtual_path = parent.config.rootpath / "__mcp_test_framework_contracts__.py"
        return _ContractsModule.from_parent(parent, path=virtual_path)
    return None


class _ContractsModule(pytest.Module):
    def _getobj(self):
        # Return a module-like object whose attributes are the contract
        # test functions. pytest's collect_python will pick them up.
        return _contract_tests   # the submodule holding test_* functions
```

This is the pattern `pytest-html`, `pytest-bdd`, and `pytest-django`
all use for "tests this plugin contributes."

**Confidence: HIGH** that this is the right shape. Both `pytest-bdd`
(virtual collection from .feature files) and `pytest-mock` (which
inserts test items from external sources) use this exact pattern. The
virtual-path-with-unique-name trick is in the pytest docs under
"creating a custom collector."

### Alternative considered: re-export the tests module so operators import it

```python
# operator's tests/test_mcp_contracts.py
from mcp_test_framework.contracts._tests import *   # noqa: F401, F403
```

Operator pytest collects the re-exported names directly. Simpler
mechanically — no virtual-file machinery. But: requires the operator
to create a new file just to host the wildcard import, which directly
contradicts SEED-015's "three lines in conftest.py" pitch. **Rejected**
as primary mechanism; could be kept as a fallback or escape hatch in
docs ("if the plugin injection misbehaves with your tooling, here's
the explicit form").

### Anti-pattern: monkeypatch the test bodies into the operator's `conftest`

Some plugins inject test functions into `conftest.__dict__` from a
`pytest_configure` hook. **Don't do this.** It's brittle (pytest's
collection cache may have run already), surprising (operator's
`conftest.py` mysteriously grows attributes they didn't write), and
breaks `-k` selectors because pytest's introspection sees the conftest
file as the test source.

---

## 3. Suggested Layout for `src/mcp_test_framework/contracts/`

**Sub-package, not single module.** Single-module gets unwieldy because
the contract surface has three distinct concerns: API (`register()`),
test bodies (the 10 functions extracted from `tests/contract/`), and
runtime state (`_REGISTRATIONS`). Splitting them along those seams
gives each its own test file in `tests/framework/unit/contracts/`.

```
src/mcp_test_framework/contracts/
  __init__.py          # public exports: register, (scoped_register)
  _api.py              # register() impl, kwargs→Config materialization
  _registry.py         # _Intent dataclass + _REGISTRATIONS module-state
  _tests.py            # the 10 parametrized contract test bodies
                       #   (extracted verbatim from tests/contract/
                       #    test_mcp_tool_contract.py, but moved to src/)
```

`_tests.py` is the bigger surprise: we are SHIPPING test bodies as part
of the production package. They live under `src/` (not `tests/`) so
they import cleanly from an installed wheel. The `_` prefix makes the
"don't call these directly" signal explicit; the operator-facing way
to invoke them is `register()`.

### Why not put `_tests.py` under a different path?

I considered `src/mcp_test_framework/_internal/contract_tests.py`,
but `contracts/_tests.py` reads more obviously: "this is the
*contracts* sub-package; here are its tests." It also keeps the
single-source-of-truth clean: anything contract-related is in one
folder.

---

## 4. Reporter Plugin — JUnit-XML Path vs. Live `pytest_runtest_logreport`

### Current state

`_runner.py` parses JUnit XML written by a subprocess pytest. It works
because the CLI controls when pytest runs and can write to a
tempfile JUnit destination it owns. In library mode, the operator
controls when pytest runs — they invoke `pytest` directly — and we
have no opportunity to read a JUnit XML between collection and exit.

### Recommended split

Refactor the renderer into **two surfaces sharing the same domain model
(`ParsedRun` / `ToolVerdict`)**:

| Surface | Input | Driven by |
|---------|-------|-----------|
| `render_domain_ui_from_xml(path, ctx)` | JUnit XML path | CLI mode (kept as-is) |
| `render_domain_ui_from_reports(reports, ctx)` | live `TestReport` list | Library-mode plugin (NEW) |

Both produce the SAME `ParsedRun` value and call the SAME
`_render_per_tool_rows` / `_render_summary_line` helpers (already
data-driven and stream-agnostic in current code — see lines 981–1103
of `_runner.py`). The fork is at the *front* of the renderer (how do
we build `ParsedRun`?), not the *back* (what does it print?).

### Live reporter plugin shape

```python
# src/mcp_test_framework/_plugin.py (continued)

class _LiveDomainReporter:
    """Collects TestReport objects, renders domain UI at session end.

    The default is "register this reporter but stay quiet" -- operators
    who want the domain UI add `--mcp-domain-ui` or set
    [tool.pytest.ini_options] mcp_domain_ui = true in pyproject.toml.
    """

    def __init__(self):
        self._reports: list[pytest.TestReport] = []
        self._enabled: bool = False

    def pytest_addoption(self, parser):
        parser.addoption(
            "--mcp-domain-ui",
            action="store_true",
            help="Render the MCP Test Framework domain UI at session end.",
        )
        parser.addini(
            "mcp_domain_ui",
            help="Render the domain UI (boolean).",
            default=False,
            type="bool",
        )

    def pytest_configure(self, config):
        self._enabled = (
            config.getoption("--mcp-domain-ui")
            or config.getini("mcp_domain_ui")
        )

    def pytest_runtest_logreport(self, report):
        # Capture only "call" phase reports for our parametrized contract
        # items. The dispatching live in _runner._build_parsed_run_from_reports.
        if not self._enabled:
            return
        if report.when == "call":
            self._reports.append(report)

    def pytest_sessionfinish(self, session, exitstatus):
        if not self._enabled or not self._reports:
            return
        parsed = _runner._build_parsed_run_from_reports(self._reports)
        ctx = _runner.RenderContext(...)
        _runner.render_domain_ui(parsed, ctx)
```

The XML-driven path stays for CLI mode because the subprocess
isolation is still valuable (the CLI wraps pytest precisely because
it wants out-of-process control over signals, exit codes, and the
operator-tone error envelope from `_load_config`).

**Key insight: the renderer becomes input-agnostic.** Today's `_runner.py`
already separates parsing from rendering at the `ParsedRun` boundary
(lines 416–432). The reporter plugin slots in alongside `parse_junit_xml`
as a second producer of `ParsedRun`. **Zero change to the per-tool row
renderer or the summary line.**

### What about the pre-run digest?

The CLI emits a pre-run digest from `_render_pre_run_digest` BEFORE
pytest starts (it has the tool discovery cache in hand). In library
mode there's no separate "before pytest" moment — pytest is already
running. Options:

1. Emit the digest from `pytest_collection_modifyitems` (which runs
   after collection but before tests execute). Tool discovery has
   completed by then because `pytest_generate_tests` ran first.
2. Skip the pre-run digest in library mode entirely; the live reporter
   prints rows as they complete and the post-run summary at the end.

**Recommendation: option (1)** — emit the digest from
`pytest_collection_modifyitems` when `--mcp-domain-ui` is active. It's
information-preserving and matches the CLI's UX (operators who
opt-in to the domain UI get the same shape regardless of mode).

---

## 5. Build Order Across Phases

The dependency graph is non-trivial. The recommended order:

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Phase A: SEED-023 rename (sdet → test_code)                         │
  │    - move src/.../sdet/ → src/.../test_code/                         │
  │    - move tests/sdet/ → tests/test_code/                             │
  │    - gen-sdet-classes → gen-test-classes                             │
  │    - --sdet flag → --test-code                                       │
  │    - docs scrub                                                       │
  │  RATIONALE: rename BEFORE adding the new contracts/ sub-package so    │
  │  we don't accidentally lock "sdet" into v1.4's public API alongside  │
  │  the new register() surface. Doing rename in Phase A keeps Phase B+  │
  │  on the post-rename name space from day one.                         │
  └──────────────────────────────────────────────────────────────────────┘
                                  ↓
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Phase B: pytest plugin entry point + skeleton                       │
  │    - add src/mcp_test_framework/_plugin.py (empty hooks at first)    │
  │    - add pyproject.toml [project.entry-points.pytest11] entry        │
  │    - test: the plugin loads when pytest imports mcp_test_framework   │
  │    - DOES NOT yet wire in fixtures, just proves the entry point      │
  │  RATIONALE: must precede everything else because the plugin module   │
  │  is what hosts all the future hooks. Land it as a skeleton so later  │
  │  phases add hooks one at a time without touching pyproject.toml.     │
  └──────────────────────────────────────────────────────────────────────┘
                                  ↓
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Phase C: register() API + _registry module                          │
  │    - add contracts/_api.py, contracts/_registry.py                   │
  │    - register() accepts kwargs, builds a frozen Config               │
  │    - register() appends _Intent to _REGISTRATIONS                    │
  │    - NO test injection yet — just state                              │
  │    - tests: register() roundtrips a Config matching the YAML path    │
  │  RATIONALE: pure-data layer with no pytest hooks. Easy to unit-test  │
  │  in isolation; gives the next phase something concrete to consume.   │
  └──────────────────────────────────────────────────────────────────────┘
                                  ↓
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Phase D: Contract extraction (tests/contract/ → contracts/_tests.py)│
  │    - move the 10 test_* functions from tests/contract/ into          │
  │      src/mcp_test_framework/contracts/_tests.py                      │
  │    - tests/contract/test_mcp_tool_contract.py becomes a 5-line       │
  │      shim: `from mcp_test_framework.contracts._tests import *`       │
  │      (or, cleaner: deleted, and tests/contract/ becomes the          │
  │       framework's own register()-driven dogfood — see §10 below)    │
  │    - existing test suite stays green (the tests' bodies are bytes-  │
  │      identical to before; only their physical path changes)         │
  │  RATIONALE: smallest blast radius. The 10 test bodies are pure       │
  │  functions of fixtures; moving them is rename-like.                  │
  └──────────────────────────────────────────────────────────────────────┘
                                  ↓
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Phase E: Plugin wires in the fixtures + parametrize hook            │
  │    - _plugin.py exports pytest_plugins = [...fixtures...] OR adds    │
  │      an explicit register-via-conftest seam                          │
  │    - move tests/conftest.py:pytest_generate_tests into the plugin    │
  │    - operator's pytest sees target_tool fixture + parametrize        │
  │      automatically after `import` of the package, no conftest line   │
  │  RATIONALE: fixture availability is a precondition for anything      │
  │  using register() to actually work; gating it as its own phase       │
  │  keeps the test-injection phase clean.                               │
  └──────────────────────────────────────────────────────────────────────┘
                                  ↓
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Phase F: Test injection via pytest_collect_file                     │
  │    - _plugin.py grows pytest_collect_file returning _ContractsModule │
  │    - reads _REGISTRATIONS; synthesizes virtual module                │
  │    - operator's `pytest` from their repo, with three-line conftest,  │
  │      now collects + runs contract tests                              │
  │  RATIONALE: this is the milestone-defining capability. Should be     │
  │  its own phase so failures here don't entangle with the rename or    │
  │  fixture-wiring phases.                                              │
  └──────────────────────────────────────────────────────────────────────┘
                                  ↓
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Phase G: Live domain-UI reporter plugin                             │
  │    - _plugin.py grows _LiveDomainReporter (pytest_runtest_logreport, │
  │      pytest_sessionfinish, --mcp-domain-ui flag)                     │
  │    - refactor _runner: extract _build_parsed_run_from_reports        │
  │      alongside parse_junit_xml                                       │
  │    - CLI mode keeps reading XML (no behavioral change)               │
  │  RATIONALE: orthogonal to test injection (live mode works without    │
  │  the reporter; reporter without injection works for SDET tests in    │
  │  library mode). Independent landability.                             │
  └──────────────────────────────────────────────────────────────────────┘
                                  ↓
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Phase H: CLI demotion — make CLI a register() client                │
  │    - tests/contract/conftest.py grows a `register(...)` call         │
  │      (replacing the static parametrize logic that moves to the      │
  │       plugin in Phase E)                                             │
  │    - CLI's run() command remains the same wrapper; pytest subprocess │
  │      now invokes the same register()-driven path                     │
  │    - delete dead code in tests/conftest.py:pytest_generate_tests if  │
  │      it's been fully replaced by the plugin                          │
  │  RATIONALE: AFTER the library-mode path is proven end-to-end. CLI    │
  │  becomes the "we eat our own dog food" demonstration.                │
  └──────────────────────────────────────────────────────────────────────┘
                                  ↓
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Phase I: Docs rewrite                                               │
  │    - README leads with library mode ("add to pyproject.toml,         │
  │      three lines in conftest.py")                                    │
  │    - CLI demotes to "Appendix: CLI usage for CI one-liners"          │
  │    - new docs: contracts/register-api-reference.md                   │
  │    - SDET → test-code rename ripples through (Phase A scope)         │
  │  RATIONALE: docs LAST. Avoid the "doc-then-redoc" thrash that        │
  │  SEED-015's "open design questions" notes warn about.                │
  └──────────────────────────────────────────────────────────────────────┘
                                  ↓
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Phase J: Carry-forward UAT closure (live homelab-mcp runs)          │
  │    - README §SDET-scenarios PASS-sample re-capture                   │
  │    - Phase 17 SC1 live-stack confirmation at ~70-tool scale          │
  │    - v1.2 Phase 13 + Phase 14 live-stack UATs                        │
  │  RATIONALE: validates the full library-mode story against a real    │
  │  MCP server before milestone close. The UAT debt was already going   │
  │  to be re-validated anyway; fold it in here.                         │
  └──────────────────────────────────────────────────────────────────────┘
```

**Critical dependency callouts:**
- Phase A (rename) MUST precede Phase C (register) so the rename
  doesn't touch the brand-new contracts/ folder.
- Phase B (plugin skeleton) MUST precede Phase F (test injection)
  because injection needs hooks to hang off.
- Phase D (extract) MUST precede Phase F (inject) so there's
  something to inject.
- Phase G (live reporter) can land in parallel with Phase H (CLI
  demotion) — they touch different files.

---

## 6. Shared-Code Integration Points

The CLI mode and library mode share a deliberately large surface — to
the point that **CLI mode is just library mode running in a subprocess
the CLI happens to launch**. The shared layer:

| Component | Owner | CLI uses | Library uses |
|-----------|-------|----------|--------------|
| `Config` (frozen Pydantic) | `config.py` | yes — via `_load_config` | yes — `register()` materializes one from kwargs OR loads from `config_file=` |
| `McpTestClient` (async stdio) | `mcp_client.py` | yes — through `mcp_client` fixture | yes — through `mcp_client` fixture (plugin-loaded) |
| Fixtures (`mcp_client`, `judge`, `target_tool`, `tool_config`, `config`, `_preflight`, `_isolated_home`, rubric_*) | `fixtures.py` | yes | yes — auto-loaded via `pytest_plugins` in plugin |
| `OllamaJudge` + `Judge` protocol | `ollama_judge.py` + `judge_protocol.py` | yes | yes |
| `schema_validator.py` (7 deterministic checks) | same | yes (TEST-02) | yes (TEST-02) |
| `rubrics.py` (ClarityRubric / DisambiguationRubric / ParametersRubric) | same | yes | yes |
| Contract test bodies (TEST-01 .. TEST-10) | `contracts/_tests.py` (NEW) | yes — injected via the same plugin hook | yes — injected via the same plugin hook |
| Domain UI rendering (`_render_per_tool_rows`, `_render_summary_line`, `RenderContext`) | `_runner.py` | yes — fed from JUnit XML | yes — fed from live `TestReport` objects |
| Pre-run digest (`_render_pre_run_digest`) | `_runner.py` | yes — pre-pytest-subprocess | yes — opt-in via `--mcp-domain-ui`, emitted from `pytest_collection_modifyitems` |
| `_isolation.py` (HOME/USERPROFILE redirect, env allowlist) | same | yes | yes — applies to library-mode pytest the same way |
| Pytest plugin (`_plugin.py`) | NEW | loads via subprocess pytest | loads via operator's pytest |
| `register()` / `_REGISTRATIONS` / `_Intent` | `contracts/_api.py` + `contracts/_registry.py` (NEW) | yes — CLI calls register() too, via tests/contract/conftest.py | yes — operator calls register() in their conftest.py |
| `gen-test-classes` codegen + ToolResponse base + `mcp_session` + `tool()` | `test_code/` (post-rename) | yes — secondary surface | yes — secondary surface |

The **only CLI-mode-specific code** is:
- `cli.py` (Typer command parsing, `_load_config` precedence, operator-tone
  error envelopes)
- `_runner.run_pytest_subprocess` (subprocess pytest spawning, tempfile JUnit
  XML capture, exit code mapping)
- `_runner.parse_junit_xml` (JUnit XML → `ParsedRun`)
- `_runner.render_domain_ui` orchestration when called with an XML path

The **only library-mode-specific code** is:
- `_plugin.py` (hook implementations + entry point glue)
- `contracts/_api.py:register()` kwargs → `Config` materialization
- The live reporter (`_LiveDomainReporter`) — though it lives in `_plugin.py`,
  it's library-mode-only because CLI mode doesn't go through pytest's live
  hooks (it parses XML at the end).

Everything else — config, fixtures, judge, MCP client, schema validators,
contract test bodies, domain model, renderer helpers — is **shared
verbatim**.

---

## 7. Coexistence With the Operator's Own Tests

The operator's `tests/` folder typically already contains their own
business-logic tests. After `register()`, the layout becomes:

```
operator-mcp-server/
  tests/
    conftest.py                # contains register(...) call
    test_my_business_logic.py  # operator's own tests
    test_my_other_thing.py     # operator's own tests
    # NO contract test file — those are injected by the plugin
```

### How they coexist mechanically

1. **Pytest collection sees both.** Operator's own test files contribute
   `Item`s as always. The plugin's `pytest_collect_file` contributes a
   virtual `_ContractsModule` whose items are the 10 parametrized
   contract tests, multiplied by the tool list.
2. **Fixtures are namespace-scoped to pytest, not file-scoped.** The
   plugin's `mcp_client` / `judge` / `target_tool` fixtures are visible
   from every conftest scope. Operator's own tests can opt to use them
   (e.g. an SDET-style scenario test that calls `tool("foo").call(...)`)
   or ignore them.
3. **Pytest collection skips the framework's autouse `_preflight`
   when no live-MCP-scope items are collected** — see
   `fixtures.py:_session_needs_preflight`. This logic already keys on
   path prefixes (`tests/contract/`, `tests/sdet/`). For library mode
   the predicate has to change: it should key on **whether the
   collected items are contract / sdet items**, not on file paths.
   Easiest: tag injected contract items with a custom marker
   (`@pytest.mark.mcp_contract`) and have `_preflight` check
   `request.session.items` for that marker.

### Selectors operators can use

```bash
# Run only the framework's contract tests:
pytest -k "mcp_contract"           # if we tag with a marker
pytest -m "mcp_contract"           # ditto

# Run only the operator's own tests:
pytest -k "not mcp_contract"
pytest -m "not mcp_contract"

# Skip contract tests in PR runs, only in main:
pytest -m "not mcp_contract"       # PR
pytest                              # main (everything)
```

**Recommendation: ship a `mcp_contract` pytest marker** declared in the
plugin's `pytest_configure` via `config.addinivalue_line("markers", ...)`,
and apply it to every contract item the plugin injects. Operators get
clean `-m` / `-k` selectors without us inventing a custom selector
mechanism. Documented in the public API.

### What about the operator's own conftest fixtures?

These work unchanged. Pytest composes conftests from inner to outer
scope, and plugin-loaded fixtures live in an outermost scope. An
operator who defines their own `mcp_client` fixture in their conftest
**overrides** the plugin's version — which is correct behavior for
the corner case where they want a custom MCP client (e.g. a test
double).

---

## 8. Component Boundaries (Post-Refactor)

| Component | Responsibility | Inputs | Outputs | Communicates With |
|-----------|---------------|--------|---------|-------------------|
| `cli.py` (Typer surface) | Parse CLI args, resolve config precedence, emit operator-tone errors, dispatch to subprocess pytest | argv, env vars | exit code, stdout/stderr | `_load_config`, `_runner.run_pytest_subprocess`, `contracts.register` (NEW — for CLI's own dogfood path) |
| `config.py` | Frozen Pydantic Config model + YAML loader | YAML path, init kwargs | `Config` instance | Validators in `models.py` |
| `models.py` | Pydantic sub-models (ToolConfig, OllamaConfig, McpServerConfig, SdetConfig→TestCodeConfig) | scalar values | typed sub-models | — |
| `mcp_client.py` | async stdio `ClientSession` wrapper, owner-task lifecycle | command + args, `_isolated_home` env | `McpTestClient` context manager | `mcp` SDK |
| `ollama_judge.py` | `/api/chat` httpx client with qwen3 belt-and-braces | rubric + subject + context | `JudgeResult` | httpx |
| `schema_validator.py` | 7 deterministic structural checks | `mcp.types.Tool` | `list[ValidationIssue]` | jsonschema |
| `rubrics.py` | 3 rubric prompts (clarity / disambiguation / parameters) | — | rubric instances | — |
| `judge_protocol.py` | `Judge` Protocol seam | — | — | — |
| `fixtures.py` | Session-scoped pytest fixtures (`mcp_client`, `judge`, `target_tool`, `config`, `_preflight`, `_isolated_home`) | `Config` | fixture values | All of the above |
| `_isolation.py` | HOME/USERPROFILE tempdir + env allowlist | tempdir path | env dict | — |
| **`_plugin.py` (NEW)** | pytest11 entry-point. Hosts: `pytest_collect_file`, `pytest_generate_tests`, `_LiveDomainReporter`, marker registration, `--mcp-domain-ui` flag, `pytest_plugins=[…fixtures…]` | pytest hooks | injected items, live UI | `contracts._registry`, `fixtures`, `_runner` |
| **`contracts/__init__.py` (NEW)** | Public exports (`register`) | — | — | `_api`, `_registry`, `_tests` |
| **`contracts/_api.py` (NEW)** | `register()` impl: kwargs → frozen `Config` → `_Intent` append | kwargs / `config_file=PATH` | `None` (side effect) | `config.Config`, `_registry._REGISTRATIONS` |
| **`contracts/_registry.py` (NEW)** | Module-level state (`_REGISTRATIONS`, `_Intent`, `_INJECTED` latch) | — | — | — |
| **`contracts/_tests.py` (NEW)** | The 10 contract test bodies — extracted verbatim from `tests/contract/test_mcp_tool_contract.py` | fixtures (target_tool, tool_config, judge, etc.) | pytest pass/fail | fixtures |
| `_runner.py` (MODIFIED) | (1) `parse_junit_xml` → `ParsedRun` (CLI mode), (2) `_build_parsed_run_from_reports` (NEW; library mode), (3) renderer helpers (input-agnostic), (4) subprocess pytest spawn (CLI mode only) | JUnit XML path OR `TestReport` list, `RenderContext` | rendered stdout | — |
| `test_code/` (RENAMED from `sdet/`) | Codegen + `mcp_session` + `tool()` + `ToolResponse` + `ToolCallError` | live MCP server | typed call wrapper | mcp_client, codegen |

**New components:** 4 (`_plugin.py`, `contracts/_api.py`, `contracts/_registry.py`, `contracts/_tests.py`)
**Renamed components:** 1 sub-package (`sdet/` → `test_code/`)
**Modified components:** `_runner.py` (split parser from XML),
`fixtures.py` (`_preflight` predicate keys on marker not path),
`cli.py` (CLI calls register() in dogfood path), `pyproject.toml` (pytest11
entry point), `tests/contract/test_mcp_tool_contract.py` (becomes shim or deleted)
**Untouched components:** `config.py`, `models.py`, `mcp_client.py`,
`ollama_judge.py`, `schema_validator.py`, `rubrics.py`, `judge_protocol.py`,
`_isolation.py` — the entire core library substrate

---

## 9. Patterns to Follow

### Pattern 1: Plugin module hosts hooks; sub-packages host domain logic

**What:** `_plugin.py` is a thin file containing only pytest hook
functions and their dispatch into domain modules. It owns no business
logic. Tests for hooks use pytest's `pytester` plugin (lets us run
mini-pytest sessions inside our test suite to verify the plugin's
behavior end-to-end).

**When:** for the v1.4 plugin entry-point and every future hook we add.

**Example:**
```python
# _plugin.py
def pytest_collect_file(parent, file_path):
    from mcp_test_framework.contracts import _registry
    return _registry.maybe_synthesize_module(parent, file_path)

# _registry.py — owns the actual logic; testable in isolation
def maybe_synthesize_module(parent, file_path) -> pytest.Module | None:
    if not _REGISTRATIONS:
        return None
    ...
```

### Pattern 2: Module-level state guarded by a one-shot latch

**What:** `_REGISTRATIONS` is a list. `_INJECTED` is a bool that flips
once and never unflips. This makes the test-injection idempotent
within a session — pytest may probe `pytest_collect_file` multiple
times during collection, and we don't want to re-emit the virtual
module each time.

**When:** any module-level mutable state we add for plugin coordination.

**Why this is safe in pytest:** pytest's collection runs in a single
process; the state's lifetime equals the lifetime of that process. We
do not need cross-process locking. Tests that need a fresh state
patch the module-level slots in a fixture teardown — the same pattern
already used by `_tool_factory.py::_REGISTRIES`.

### Pattern 3: Single source of truth at the Pydantic boundary

**What:** `register()` accepts EITHER scalar kwargs OR `config_file=`,
materializes them into ONE `Config` instance, and `_Intent.config` is
the only thing downstream code reads. No "kwargs override file" or
"file overrides kwargs" precedence rules to debug — those are folded
into the materialization step.

**When:** anywhere we accept config from multiple surfaces (kwargs,
YAML, env). Already the pattern used in `cli.py:_load_config`; library
mode preserves it.

**Why:** the v1.2 `.env` precedence-confusion bug (see Memory:
`project_dotenv_silently_beats_config`) was caused by having multiple
config sources without a single materialization point. Don't repeat
the mistake in v1.4.

### Pattern 4: Marker-tagged injection over path-based discrimination

**What:** instead of `if nodeid.startswith("tests/contract/"):`, the
plugin tags injected items with `@pytest.mark.mcp_contract` and
`_preflight` checks for that marker. Path-based logic dies when the
operator's repo has no `tests/contract/` directory.

**When:** anywhere we currently key on file paths. The `_LIVE_PREFIXES`
tuple in `fixtures.py:117` is the prime refactor target.

**Why:** in library mode, the operator's contract tests have no
on-disk path — they live in a virtual `_ContractsModule`. Path
prefixes don't exist. Markers compose; paths don't.

### Pattern 5: Renderer is input-agnostic

**What:** `_render_per_tool_rows`, `_render_summary_line`, etc., take
`ParsedRun + RenderContext` and write to `file=sys.stdout`. They DO
NOT read JUnit XML, pytest reports, or any source. The producers
(`parse_junit_xml` for CLI; `_build_parsed_run_from_reports` for
library) sit upstream and emit the same `ParsedRun` value.

**When:** for any future renderer (e.g., a JSON exporter, a CI
annotation emitter). Add new producers; never re-implement rows or
summary.

---

## 10. The Framework's Own Dogfood Loop (Self-Test)

SEED-015 calls this out explicitly: "the framework's own `tests/`
invokes `register()` against a fixture MCP server and asserts the
right tests get injected and pass."

### Current `tests/contract/` becomes the framework's register() dogfood

After Phase D (contract extraction), the current `tests/contract/test_mcp_tool_contract.py`
file has two viable futures:

**Option A: Delete it; tests/contract/conftest.py becomes pure register()**

```python
# tests/contract/conftest.py  (post-Phase H)
"""Framework's own contract-pass dogfood — register() against live homelab-mcp.

This is the framework's self-test of library mode. We use the same
public API (register()) that operators use in their own conftests.
The contract tests collected here are the same tests that operators
get; the only difference is that we run them against homelab-mcp via
the existing CLI config, while operators run them against their own
servers.
"""
from mcp_test_framework.contracts import register
from mcp_test_framework.config import Config

# Reuse the existing _load_config / MCPTF_CONFIG_FILE precedence so the
# CLI's `mcp-test-framework run` (which sets MCPTF_CONFIG_FILE before
# spawning pytest) drives this dogfood the same way an operator would
# drive register() against their own server.
register(config=Config())   # bare Config() picks up MCPTF_CONFIG_FILE
```

**Option B: Keep test_mcp_tool_contract.py as a shim re-importing the bodies**

```python
# tests/contract/test_mcp_tool_contract.py  (post-Phase D, pre-Phase H)
"""Compatibility shim. The real test bodies live at
mcp_test_framework.contracts._tests. This file is kept so the existing
tests/contract/ collection path continues to work during the v1.4
migration. Will be deleted in Phase H when tests/contract/conftest.py
calls register() instead.
"""
from mcp_test_framework.contracts._tests import *   # noqa: F401, F403
```

**Recommendation: Option A by milestone close, Option B as a
transitional waypoint between Phase D and Phase H.** Option A is the
real dogfood — it proves library mode works by routing the
framework's own contract suite through it.

### Fixture MCP server for plugin-mechanics tests

For tests of the plugin mechanics themselves (does `register()` cause
items to appear? does the marker work? does the live reporter render
correctly?), we want a fixture MCP server that runs in-process — not
homelab-mcp via uvx.

Add to `tests/framework/unit/contracts/`:

```python
# tests/framework/unit/contracts/test_register_injects_items.py
import pytest

pytest_plugins = ["pytester"]   # opt into pytester for sub-pytest sessions

def test_register_injects_contract_items(pytester):
    # Use pytester to spin up a mini-pytest session with a conftest
    # that calls register() against a fake MCP server.
    pytester.makeconftest("""
        from mcp_test_framework.contracts import register
        register(
            server_command=["python", "-m", "tests.framework.fixtures.fake_mcp_server"],
            tools=["fake_tool_one"],
        )
    """)
    result = pytester.runpytest("--collect-only", "-q")
    # The 10 contract tests, parametrized over 1 tool = 10 collected items
    result.stdout.fnmatch_lines(["*10 tests collected*"])
```

`tests/framework/fixtures/fake_mcp_server.py` is a minimal MCP server
process that responds to `initialize` + `list_tools` + `call_tool`
with canned data. **This file does not violate SEED-022** — it's a
test fixture in `tests/framework/`, not framework code in `src/`.
It's the framework's mock-SUT for self-testing, analogous to a Django
test app or pytest's own example tests.

### Why pytester is the right tool for plugin self-tests

`pytester` (built into pytest, no extra install) runs a real pytest
process from within a parent pytest, with isolated rootdir, conftest,
and item collection. It's the canonical way pytest plugins self-test.
`pytest-bdd`, `pytest-mock`, `pytest-asyncio`, and `pytest-django` all
use it.

---

## 11. Anti-Patterns to Avoid

### Anti-Pattern 1: Re-implementing config precedence in `register()`

**What:** writing `register()` with its own kwargs precedence rules
that differ from CLI mode's CLI > env > YAML > defaults stack.

**Why bad:** two precedence stacks to debug, two test surfaces to keep
in sync, two doc paragraphs explaining "but if you also pass…"

**Instead:** `register()` always materializes a single frozen `Config`
either by `Config(**kwargs)` (scalar kwargs path) or `Config(yaml_file=PATH)`
(file path), both flowing through the same `settings_customise_sources`
already in `config.py`. The CLI uses the same `Config` class through
`_load_config`.

### Anti-Pattern 2: `register()` does work at import time

**What:** spawning a subprocess MCP server in `register()`'s body to
discover tools, or opening an Ollama HTTP connection, etc.

**Why bad:** conftest imports are eager and synchronous. Side-effecting
imports break `--collect-only`, IDE test-discovery, and `pytest
--help`. Any error becomes a confusing "I imported conftest and it
crashed" message before pytest even started.

**Instead:** `register()` only appends to `_REGISTRATIONS` and resolves
the `Config`. All MCP / Ollama I/O happens in the existing session
fixtures (`mcp_client`, `judge`), invoked lazily during the test
phase. Tool discovery happens in `pytest_generate_tests` (already
async-safe via `asyncio.run` on a brief McpTestClient session).

### Anti-Pattern 3: SUT-specific code in `contracts/_tests.py`

**What:** any branching in the test bodies that says "if this is
homelab-mcp, do X." Any import of `homelab_mcp`. Any hard-coded tool
name that isn't an MCP-protocol-level constant.

**Why bad:** violates SEED-022 ("framework primitives; SDET owns safety").
Carries the "framework that knows about your server" trap that
PREFLIGHT-01/02 fell into and triggered Phase 19 → Phase 20 reframe.

**Instead:** test bodies receive `target_tool`, `tool_config`, `judge`,
`mcp_client` as fixtures and assert against generic MCP contracts only.
The 10 functions in `tests/contract/test_mcp_tool_contract.py` today
already adhere to this — keep them as-is when moving to
`contracts/_tests.py`. The mechanical enforcement (`ruff TID251` ban
on `homelab_mcp`, `sys.modules` guard in `tests/conftest.py`) carries
into v1.4 unchanged.

### Anti-Pattern 4: Bypass the plugin and import contracts directly into operator conftest

**What:** instructing operators to write
`from mcp_test_framework.contracts._tests import *` in their
conftest.py instead of `register(...)`.

**Why bad:** (1) `_tests` is private (underscore prefix); operators
poking at it locks the surface and we can never refactor. (2) Loses
all `register()`-time config materialization. (3) Operators don't get
the per-tool parametrize / `target_tool` fixture wiring "for free"
— they'd have to set up their own.

**Instead:** `register()` is the only public path. Document it as
such. `_tests` stays internal.

### Anti-Pattern 5: Plugin hooks doing config discovery

**What:** plugin's `pytest_configure` hook reading `MCPTF_CONFIG_FILE`,
loading a YAML, etc.

**Why bad:** library-mode operators pass their config in code via
`register()`. The plugin reading env vars or YAML files on its own
creates a precedence puzzle ("did register() win or did
MCPTF_CONFIG_FILE win?") — exactly the v1.2 `.env` bug we already
solved by dropping env-overlay.

**Instead:** plugin reads `_REGISTRATIONS` only. `register()` is the
single config injection seam. CLI mode invokes `register()` from
`tests/contract/conftest.py`, where the bare `Config()` call picks
up `MCPTF_CONFIG_FILE` via the existing env-pointer fallback (which
is fine — CLI mode is the layer that knows about env precedence).

---

## 12. Scalability Considerations

| Concern | At 1 tool (MVP) | At ~70 tools (homelab-mcp) | At 500+ tools (hypothetical large server) |
|---------|----------------|------------------------------|-----------------------------------------|
| Collection time | <100ms | ~1s (10 tests × 70 tools = 700 items) | ~5s. Consider lazy tool discovery (defer to first `target_tool` request) |
| Pre-run digest height | 8 lines | 8 lines + N-line `--explain` | same; `--explain` already grep-friendly per Memory `project_pre_run_tool_summary` |
| Per-tool row block | 3 lines | ~210 lines (acceptable; sortable) | ~1500 lines. Consider opt-in collapsed mode |
| MCP discovery cost | 1 subprocess spawn (~300ms) | 1 subprocess spawn (~500ms; same call) | same — list_tools is one RPC |
| Live reporter buffering | trivial | ~700 `TestReport` objects (~MB) | ~5K reports (~10MB). Stream-and-flush at boundaries |
| `_REGISTRATIONS` size | 1 entry | 1 entry (one register() call per server) | 1 entry per server — operators rarely register multiple |
| Idempotency latch (`_INJECTED`) | n/a | 1 atomic flip | 1 atomic flip — scales as O(1) regardless of tool count |

**No scaling cliff between MVP and ~70-tool homelab-mcp.** The 500+
hypothetical surfaces a future seed for collapsed per-tool output, but
that's a v1.5+ concern.

---

## 13. Decision Records

### D-1: `register()` is module-level call, not decorator/fixture-factory

| Option | Pros | Cons |
|--------|------|------|
| **Module-level `register(...)` call** | Most explicit; matches SEED-015's three-line pitch verbatim; trivial to unit-test (just call it); easy to grep for in operator codebases | Mutable module-level state (`_REGISTRATIONS`) — though already a pattern in `_tool_factory.py` |
| Decorator `@register(...)` on a test function | Pythonic-feeling; familiar to pytest users | Requires the operator to write a *fake* test function just to hold the decorator; contract tests still come from us, not them — confusing |
| Fixture factory returning a `Registrar` | Composable in nested test classes | Fixtures cannot inject new items into collection; would need a secondary hook anyway; adds a layer of indirection |
| Autouse plugin reading `pyproject.toml` | Zero conftest lines for operator | Loses the explicit "I'm opting in" moment; harder to test; introduces yet another config surface |

**Recommendation: module-level call.** Most boring; most explicit; matches
SEED-015 sketch line-for-line. Confidence: HIGH.

### D-2: Plugin module name is `_plugin.py` (underscore prefix)

| Option | Pros | Cons |
|--------|------|------|
| **`_plugin.py`** | Signals "internal — don't import directly"; matches existing `_runner.py` / `_reporter.py` / `_isolation.py` naming convention | None |
| `plugin.py` | Public-looking, suggests an importable surface | We don't want operators importing it directly — entry-point auto-loads it |
| `pytest_plugin.py` | Self-documenting | Verbose; doesn't match the `_underscore` convention already established |

**Recommendation: `_plugin.py`.** Consistent with existing naming.

### D-3: Test injection via `pytest_collect_file`, not `pytest_collection_modifyitems`

`modifyitems` cannot create new items — it can only filter / reorder.
`pytest_collect_file` is the official mechanism for plugins
contributing collectable items from non-Python sources. Used by
pytest-bdd (feature files), pytest-typeguard, and the pytest doctest
plugin (for doctests in .txt files). Confidence: HIGH.

### D-4: The `mcp_contract` marker is the discrimination mechanism, not path prefix

Existing `_preflight` predicate checks `tests/contract/` / `tests/sdet/`
path prefixes. Library mode breaks this — virtual items have no path.
The plugin applies `pytest.mark.mcp_contract` to injected items; the
predicate becomes "any collected item has the marker?" Same logic;
path-independent. Confidence: HIGH.

### D-5: CLI mode keeps the JUnit XML round-trip

Don't try to unify CLI and library modes onto the live reporter. The
CLI's subprocess isolation is valuable for:
- Signal handling (SIGINT → exit 130 contract)
- Operator-tone error envelopes from `_load_config`
- Independent stderr/stdout capture for `--debug` appendix
- Tempfile JUnit XML the operator can opt to keep via `--junit-xml=PATH`

The XML parser stays. The renderer becomes a shared backend that
accepts `ParsedRun` from either source. Confidence: HIGH.

### D-6: Phase A (rename) lands before any other v1.4 work

SEED-023 explicitly says: "rename before any new public-API expansion lands."
Library mode IS new public-API expansion. Doing rename mid-milestone
multiplies the doc churn and risks `sdet` getting embedded in
`register()`'s public kwargs. Confidence: HIGH.

---

## 14. Open Questions Deferred to Phase Planning

These don't block roadmap creation but will surface in phase plans:

1. **`scoped_register()` API shape.** SEED-015 sketches this as a
   fixture-scoped context manager for nested test classes. Defer to
   v1.5 or later — `register()` covers the operator's three-line pitch;
   `scoped_register` is for advanced users who haven't asked for it
   yet.
2. **Auto-discovery vs. explicit tool allowlist in `register()`.** If
   `tools=None` (the default), should `register()` cause the framework
   to call every tool the server advertises? Or fail loud à la v1.2's
   opt-in posture? **Lean toward fail-loud-on-None** — it preserves
   the destructive-tool safety lesson from Memory
   `project_config_discovery_and_safety`. Phase planning resolves.
3. **How does `gen-test-classes` work in library mode?** Operator runs
   `mcp-test-framework gen-test-classes` from CLI — but library-mode
   operators may not have the CLI installed. Do we expose a
   `from mcp_test_framework.test_code import generate_classes` callable?
   Or require CLI install? Phase planning resolves.
4. **Multiple `register()` calls in the same conftest** — for testing
   against multiple MCP servers from one operator repo. SEED-015 says
   "out of scope"; library-mode mechanics make it ALMOST free (just
   loop `_REGISTRATIONS`). Decide explicitly in Phase planning whether
   to enable or fail-loud.
5. **What happens to `tests/contract/test_mcp_tool_contract.py`?**
   Option A (delete; conftest.py calls register) or Option B (shim
   re-import) — see §10. Resolved in Phase D or H.
6. **`config_file=` vs scalar kwargs precedence in `register()`** — what
   if operator passes BOTH? Mirror CLI mode's stack: kwargs win, file
   overlays defaults. Explicit in `register()` docstring.

---

## 15. Sources

- `.planning/PROJECT.md` — Current Milestone (v1.4 Library Mode), Long-term Vision, Out of Scope, v1.3 close state
- `.planning/seeds/SEED-015-library-mode-delivery.md` — surface sketch, scope estimate, breadcrumbs
- `.planning/seeds/SEED-023-rename-sdet-surface-to-test-code.md` — rename blast radius
- `src/mcp_test_framework/cli.py` — current CLI surface, `_load_config`, `_discover_tools_for_run`
- `src/mcp_test_framework/_runner.py` — current runner, JUnit XML parser, `ParsedRun` / `ToolVerdict` dataclasses, renderer helpers
- `src/mcp_test_framework/fixtures.py` — session fixtures, `_preflight` predicate, isolation
- `src/mcp_test_framework/config.py` — frozen Config + pydantic-settings precedence
- `src/mcp_test_framework/models.py` — sub-model definitions (ToolConfig, OllamaConfig, McpServerConfig, SdetConfig)
- `src/mcp_test_framework/sdet/_tool_factory.py` — `tool()` / `ToolWrapper` / `_REGISTRIES` module-state pattern (already a precedent for what `_REGISTRATIONS` follows)
- `src/mcp_test_framework/sdet/session.py` — `mcp_session` fixture activation pattern, single-source-of-truth at Config boundary
- `tests/contract/test_mcp_tool_contract.py` — the 10 test bodies that move to `contracts/_tests.py`
- `tests/conftest.py` — current `pytest_plugins=["mcp_test_framework.fixtures"]` registration, `pytest_generate_tests` parametrize hook
- `tests/sdet/conftest.py` — `pytest_exception_interact` ToolCallError → JUnit user_properties hook (a reference for how plugin hooks integrate with the existing test code)
- `pyproject.toml` — current build config, dependency-groups dev block, hatchling wheel packages declaration
- `CLAUDE.md` — project constraints, black-box rule, SEED-022 invariant
- Memory: `project_v1_3_close_push_and_scrub`, `feedback_phase_scope_intent`, `project_dotenv_silently_beats_config`, `project_config_discovery_and_safety`, `project_framework_primitives_sdet_safety_principle`
- Training data on pytest plugin patterns: `pytest_collect_file`, `pytest_collection_modifyitems`, `pytest_runtest_logreport`, `pytest_sessionfinish`, `pytester` self-test fixture, `[project.entry-points.pytest11]` discovery — all stable since pytest 3.x (~2017), well-documented in pytest's official "writing plugins" guide
- Reference plugins (training data): pytest-bdd (virtual collection from .feature files; same pattern as our virtual ContractsModule), pytest-mock (item injection), pytest-django (large fixture surface auto-loaded), pytest-asyncio (already in our deps; uses pytest11 entry point + `pytest_collectstart` hook for marker handling)
