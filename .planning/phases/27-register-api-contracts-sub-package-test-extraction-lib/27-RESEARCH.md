# Phase 27: pytest-native ini config + contracts test injection + dogfood (LIB) — Research

**Researched:** 2026-05-16
**Domain:** pytest plugin internals (`addini` / `pytest_collect_file` / virtual `Module` synthesis) + pydantic-settings runtime path injection + Phase 26 plugin skeleton extension + framework's own move-and-dogfood refactor
**Confidence:** HIGH on locked mechanism choices (pytest hooks, `-o` override, pydantic-settings init_kwargs path), MEDIUM on synthetic-nodeid edge cases (no official pytest API; consumes-known-stable patterns)

---

## Summary

Phase 27 fills the Phase 26 plugin skeleton with three coherent pieces:

1. **Ini-driven config resolution** — registers `mcp_config_file` via `parser.addini(..., type="string")`, reads it in `pytest_configure`, drives the existing `Config(yaml_file=...)` loader.
2. **Synthetic test injection** — extracts the 10 contract test bodies from `tests/contract/test_mcp_tool_contract.py` to `src/mcp_test_framework/contracts/_tests.py`, then injects them at collection time via `pytest_collect_file` (or `pytest_pycollect_makemodule`) returning a custom `Module` subclass with overridden `nodeid` rendering as `<mcp-contracts>::test_<name>[<tool>]`.
3. **Move-and-dogfood** — the framework's own `pyproject.toml` adds `mcp_config_file = "./config.test.yaml"` and the legacy `tests/contract/test_mcp_tool_contract.py` + `tests/conftest.py:pytest_generate_tests` are deleted. Every framework CI run becomes a library-mode operator simulation.

**Primary recommendation:** Use `pytest_collect_file` (called once per real file under `testpaths`) is NOT the right hook here because the synthetic module is not on the operator's filesystem. Use **`pytest_collection`** to inject a freshly-constructed `_ContractsModule` directly as a top-level child of `session`, OR a hybrid that reuses `_tests.py`'s real on-disk source (located inside the installed wheel) but constructs the `Module` with an overridden `nodeid` and a synthetic `Path`. The hybrid is more pytest-asyncio-compatible (real file → real `pytestmark`, real `pytest_pycollect_makemodule` fires); the pure-synthetic path is cleaner but loses some plugin coverage. **Pick the hybrid** and time-box a spike in Wave 0 to confirm pytest-asyncio's `loop_scope="session"` collection survives the `nodeid` override.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Approach pivot (pytest-native ini config replaces `register()`):** The `register()` API specified by LIB-01..08 is **dropped**. Library-mode entry point becomes a single `mcp_config_file` ini value in `[tool.pytest.ini_options]` (or any pytest config surface accepting `addini` values). REQUIREMENTS.md LIB-01..08 + CFG-01..02 to be amended; phase title to be amended.

**D-02 — Ini key name:** `mcp_config_file` (lowercase + underscores per pytest convention). Registered via `parser.addini("mcp_config_file", type="string", help="...")`. Path resolved relative to `pyproject.toml`'s directory.

**D-03 — Config file format:** Today's v1.3 schema, **unchanged**. `mcp_server.{command,args,timeout_seconds}`, `ollama.{base_url,model,timeout_seconds}`, `tools: dict[str, ToolOptions]`, `test_code.generated_root`. Loaded via existing pydantic-settings machinery.

**D-04 — Test bodies move:** `tests/contract/test_mcp_tool_contract.py` → `src/mcp_test_framework/contracts/_tests.py`. The 10 test bodies are extracted verbatim (TEST-01..TEST-10); v1.3 assertion semantics unchanged.

**D-05 — Old paths deleted:** `tests/contract/test_mcp_tool_contract.py` is deleted. `tests/conftest.py:pytest_generate_tests` is deleted. The plugin's `pytest_collect_file` (or sibling injection hook) is the sole parametrization path.

**D-06 — Framework dogfoods library mode:** Framework's own `pyproject.toml` `[tool.pytest.ini_options]` sets `mcp_config_file = "./config.test.yaml"` (planner verifies the exact path — see Open Question O-1). Framework's CI runs contract tests exclusively through the library-mode injection path.

**D-07 — Phase 30 CLOSE-01 pre-empted:** Dogfood goal already achieved here; Phase 30 CLOSE-01 becomes "verify still green at v1.4 close."

**D-08 — Nodeid shape:** `<mcp-contracts>::test_<name>[<tool>]` — synthetic literal, NOT a real file path. Implemented by overriding `nodeid` on the synthesized `Module`.

**D-09 — `MCPTF_CONFIG_FILE` env var killed:** Phase 27 emits one-time-per-process `DeprecationWarning` when the env var is set in environment, regardless of mode. Removed in v1.5.

**D-10 — Library mode ignores `MCPTF_CONFIG_FILE`:** Does not read it. Deprecation warning fires from single check at plugin `pytest_configure` time.

**D-11 — CLI mode rewires:** `mcp-contracts run --config PATH` subprocesses `pytest -o "mcp_config_file=PATH"` instead of setting env var. One config route across CLI and library mode.

**D-12 — `Config()` loader:** Path-via-kwarg already supported (see Existing Code Insights below). The plugin constructs `Config(yaml_file=resolved_path)` directly. Internal env-var-set workaround is REJECTED on principle (reintroduces the env-var magic just killed).

**D-13..D-17 — Failure modes:**
- D-13: `mcp_config_file` unset → silent no-op.
- D-14: Path doesn't exist → loud `pytest.exit("...", returncode=2)` operator-tone.
- D-15: YAML malformed / schema fail → loud operator-tone error.
- D-16: `tools:` empty dict → silent no contract tests injected (Phase 13 SAFE-01).
- D-17: Operator's `tests/conftest.py` requires **zero ceremony**.

**D-18 — Black-box guard relocation:** `sys.modules` `homelab_mcp` check moves from `tests/conftest.py:pytest_configure` → `src/mcp_test_framework/_black_box_guard.py`. Single function `check_black_box() -> None` raising `RuntimeError` on leak. Invoked from plugin's `pytest_configure`. Wheel-introspection AST-walk CI test extends to fail on banned SUT imports anywhere in `src/`.

**D-19 — `_preflight` predicate flip:** `_session_needs_preflight()` flips from path-prefix detection to: returns `True` iff `mcp_config_file` ini value is set AND any collected item carries `pytest.mark.mcp_contract`. Test-code-author tests (`tests/test_code/`) do NOT carry the marker — see Open Question O-5.

### Claude's Discretion

- Plugin hook choice (`pytest_collect_file` vs `pytest_collection_modifyitems` vs hybrid) — researched below; **recommendation: hybrid pattern using `pytest_collect_file` with the existing on-disk `_tests.py` re-rooted via `nodeid` override, OR `pytest_collection` + manual `Module.from_parent` if pytest-asyncio plays nice.**
- `Config()` loader rewiring — **resolved**: existing loader already accepts `yaml_file=` kwarg via `init_settings.init_kwargs.pop("yaml_file")`. Use the existing surface; do NOT internal-set env var.
- `_session_needs_preflight()` mechanics (nodeid prefix vs `iter_markers`) — **recommendation: `iter_markers("mcp_contract")` — semantically honest, decouples from nodeid stability.**
- Deprecation copy for `MCPTF_CONFIG_FILE` — hardcoded literal per Phase 25 + Phase 26 pattern; see "Deprecation Copy" section below.
- `gen-test-classes` CLI rewire — **recommendation: punt to Phase 28.** The `gen-test-classes` codepath uses `--config PATH > MCPTF_CONFIG_FILE > ./config.yaml` precedence; killing the middle tier in Phase 27 forces a Phase 28 follow-up anyway when codegen output paths get touched.

### Deferred Ideas (OUT OF SCOPE)

- `register()` API surface — dropped entirely.
- `RegistrationError`, frame validation, double-call detection — moot.
- Multi-config (list of paths) — v1.5.
- URL-style judge config — moot (YAML uses nested form).
- `xdist`-parallel — v1.5.
- Tool auto-discovery — v1.5; v1.4 retains opt-in allowlist semantics from Phase 13 SAFE-01.
- Production PyPI publish — Phase 30.
- README rewrite leading with library mode — Phase 30.
- Codegen output path defaults — Phase 28.
- `MCPTF_CONFIG_FILE` deprecation-shim removal — v1.5 cleanup phase.

</user_constraints>

<phase_requirements>
## Phase Requirements

LIB-05 is **removed entirely** (D-01: no `register()` to validate). LIB-01..04, LIB-06..08 + CFG-01..02 still apply, with text amendments captured in CONTEXT.md `<downstream_impact>`.

| ID | Description (post-pivot) | Research Support |
|----|--------------------------|------------------|
| LIB-01 | Operator adds **one line** in `[tool.pytest.ini_options]` (`mcp_config_file = "./config.yaml"`) and parametrized contract tests appear in `pytest` collection. | Architecture: plugin `pytest_configure` reads ini; `pytest_collect_file` returns synthesized `Module`. See "Plugin Hook Choice" + "Ini-driven Config Resolution" below. |
| LIB-02 | `pytest --collect-only` lists every injected contract test with stable nodeids `<mcp-contracts>::test_<name>[<tool>]` — without spawning MCP server (collection phase only). | Two-phase discovery: brief MCP `list_tools` runs at `pytest_configure` time (collection IS one of pytest's phases — discovery must run there). Memory: existing `_runner._DISCOVERED_TOOL_NAMES` cache. See "Tool Discovery Lifecycle" below. **Resolved spike for the no-MCP-spawn-during-collect-only worry: D-13 silent no-op means `--collect-only` with no `mcp_config_file` set does NOT spawn the server.** |
| LIB-03 | Each contract test runs against every tool in `config.tools` (skip=False) and produces the same pass/fail signal as today's CLI run. Test bodies extracted verbatim. | D-04. v1.3 assertion semantics unchanged. See "Test-Body Extraction Recipe" below. |
| LIB-04 | `pytest -m mcp_contract` selects framework-injected tests; marker auto-applied at injection time. | Phase 26 already registers the marker. Phase 27 applies it via `add_marker(pytest.mark.mcp_contract)` on each injected `Function` item OR via the synthesized `Module`'s `pytestmark`. See "Marker Application Site" below. |
| ~~LIB-05~~ | ~~RegistrationError, frame validation, double-call~~ | **Removed** per D-01 — no register() to validate. |
| LIB-06 | Operator's existing fixture names (`config`, `judge`, `client`, `target_tool`) do not collide — all public fixtures namespaced with `mcp_*` prefix. | Already shipped in Phase 26. No Phase 27 work; verify the prefixed names still resolve through the new injection path. |
| LIB-07 | `_preflight` predicate flips from path-prefix to marker-based detection. | D-19. See "Preflight Predicate Flip" below. |
| LIB-08 | Black-box rule enforceable in wheel install — runtime `sys.modules` guard relocated to `src/mcp_test_framework/_black_box_guard.py`. | D-18. See "Black-Box Guard Relocation" below. |
| CFG-01 | (Amended per `<downstream_impact>`) Framework KILLS `MCPTF_CONFIG_FILE` in v1.4 with one-milestone deprecation; precedence becomes `pytest -o "mcp_config_file=..."` > `[tool.pytest.ini_options]` > defaults. | D-09, D-11. See "Config Precedence" below. |
| CFG-02 | (Amended) `register(config_file=PATH)` removed; the ini value IS the escape hatch. | D-01. No Phase 27 surface required. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Ini key registration | Plugin (`_plugin.py:pytest_addoption`) | — | Pytest's `addini` is plugin-scope; cannot live in `tests/conftest.py` once operator's conftest is ceremony-free. |
| Config file load + validation | Plugin (`_plugin.py:pytest_configure`) | Existing `Config()` loader | Plugin owns the entry; loader does the parsing. Single read site for `mcp_config_file`. |
| Synthetic test injection | Plugin (`_plugin.py:pytest_collect_file` or `pytest_collection`) | `contracts/_tests.py` (test source) | Operator's filesystem has no contract tests; framework injects from its own installed wheel. |
| Tool discovery (brief MCP handshake) | Plugin (`pytest_configure`) | Reuses `McpTestClient.__aenter__` | Single discovery per session; results parametrize the synthesized Module. |
| SAFE-01 opt-in filter (Phase 13) | Plugin (filter `config.tools.keys()` at parametrize) | `Config.tools` registry | Identical semantics to today's `tests/conftest.py:_resolve_tool_names`; relocates verbatim. |
| Black-box `sys.modules` guard | `_black_box_guard.py` (NEW) | Plugin invokes from `pytest_configure` | Wheel-shippable; no longer lives under `tests/`. |
| `_preflight` autouse fixture | `fixtures.py` (existing) | `mcp_contract` marker (Phase 26) | Marker is the predicate input — flips path-prefix dependency. |
| CLI mode → library mode bridge | `cli.py:_load_config` + `_runner.run_pytest_subprocess` | Pytest's `-o` flag | Subprocess passes `pytest -o "mcp_config_file=PATH"`; one route end-to-end. |
| `MCPTF_CONFIG_FILE` deprecation | Plugin (`pytest_configure`) | stdlib `warnings.warn(DeprecationWarning)` | Single emission site per Phase 25 precedent. |
| Test-code-author preflight | Plugin OR fixture predicate | (See O-5) | Open question — test-code tests don't carry `mcp_contract` marker; need alternative gate. |

## Project Constraints (from CLAUDE.md)

- **MCP transport stdio only**; never raw `subprocess.Popen` — use `mcp.client.stdio.stdio_client`.
- **Black-box rule**: framework never imports `homelab_mcp` or its submodules. Phase 27 PRESERVES this via D-18 relocation; LIB-08 extends the wheel AST guard.
- **Async**: `pytest-asyncio` strict mode; `@pytest.mark.asyncio(loop_scope="session")` on all async tests; `asyncio_default_fixture_loop_scope = "session"`. Extracted `_tests.py` carries the same `pytestmark` declaration verbatim.
- **Config precedence post-Phase 27**: `pytest -o "mcp_config_file=PATH"` > `[tool.pytest.ini_options] mcp_config_file` > (no env var) > silent no-op. `MCPTF_CONFIG_FILE` emits deprecation warning if set; ignored in library mode.
- **GSD workflow**: this is a planned phase under `/gsd-execute-phase`, not `/gsd-quick`.
- **Public-API freeze**: `mcp_config_file` ini key joins the v1.5 API-stability set — same lockdown as the v1.4 fixture-name rename.

---

## Standard Stack

No new dependencies. Phase 27 is pure refactor over already-pinned stack.

| Library | Already-pinned version | Phase 27 usage | Why already in deptree |
|---------|------------------------|----------------|------------------------|
| `pytest>=9.0` | dev-dep | `parser.addini`, `pytest_collect_file`, `Module.from_parent`, marker registration | Existing test runner |
| `pytest-asyncio>=1.3` | dev-dep | `loop_scope="session"` on extracted tests; strict mode preserved | Existing test framework `[CITED: pyproject.toml]` |
| `pydantic-settings[yaml]>=2.14` | runtime | `Config(yaml_file=PATH)` constructor kwarg (already supported in config.py:228) | Existing config loader |
| `mcp[cli]>=1.27` | runtime | `McpTestClient.__aenter__` brief handshake for parametrize discovery | Existing client |

**Installation:** No new packages. `[VERIFIED: pyproject.toml inspected]`

**Version verification:** Already locked by Phase 26; no changes.

### Alternatives Considered

| Recommended | Alternative | Tradeoff |
|-------------|-------------|----------|
| `pytest_collect_file` hook returning custom `Module.from_parent` | `pytest_collection_modifyitems` post-collection injection | `pytest_collection_modifyitems` runs AFTER pytest builds the item tree from real files; injecting items there bypasses pytest's `pytest_pycollect_makemodule` event sequence and breaks pytest-asyncio's marker discovery on the items. `pytest_collect_file` participates in the standard collection lifecycle and pytest-asyncio sees the items. `[CITED: pytest discussion #10246 — synthetic items via modifyitems are documented as a hack that misses other plugins]` |
| Custom `Module` subclass with `nodeid` override | `pytest.Module` directly | Subclass needed to override `nodeid` property (synthetic literal `<mcp-contracts>`). Default `Module.nodeid` returns the filesystem path. |
| Reuse `Config(yaml_file=PATH)` kwarg from `cli.py:_load_config` | Refactor `Config()` to take path as positional argument | Existing surface already supports kwarg-path via `init_settings.init_kwargs.pop("yaml_file")` in `settings_customise_sources`. Refactor adds churn without benefit. **`[VERIFIED: src/mcp_test_framework/config.py:228]`** |
| One-shot tool discovery in plugin `pytest_configure` | Lazy first-test discovery (today's `tests/conftest.py:pytest_generate_tests` pattern) | Discovery must happen before parametrize fires; `pytest_configure` is the canonical site. Discovery cost is one short subprocess (≤1s on a warm machine). |
| `pytest -o "mcp_config_file=PATH"` subprocess from CLI mode | Two routes (env var for CLI, ini for library) | Two routes violate the one-mechanism principle (memories: `project_dotenv_silently_beats_config`, `project_mcptf_config_file_silent_fail`). `[CITED: CONTEXT.md D-11]` |

---

## Architecture Patterns

### System Architecture Diagram

```
                ┌──────────────────────────────────┐
operator        │  pyproject.toml                  │
sets one  ───►  │  [tool.pytest.ini_options]       │
ini line        │  mcp_config_file = "./config.yaml" │
                └──────────────┬───────────────────┘
                               │ pytest reads ini
                               ▼
                ┌──────────────────────────────────┐
                │  _plugin.py:pytest_addoption     │
                │  parser.addini("mcp_config_file") │
                └──────────────┬───────────────────┘
                               │
                               ▼
                ┌──────────────────────────────────┐  set?  no  ┌──────────────────────┐
                │  _plugin.py:pytest_configure     ├───────────►│ silent no-op (D-13)  │
                │  - read mcp_config_file ini      │            │ operator opted out   │
                │  - if MCPTF_CONFIG_FILE in env:  │            └──────────────────────┘
                │      DeprecationWarning (D-09)   │
                │  - resolve path (inipath-rel)    │  unset ►  fail-loud (D-14)
                │  - Config(yaml_file=path)        │  parse ►  fail-loud (D-15)
                │  - _black_box_guard.check()      │
                │  - stash on config._mcp_cfg      │
                └──────────────┬───────────────────┘
                               │
                               ▼
                ┌──────────────────────────────────┐
                │  brief MCP handshake             │
                │  list_tools → discovered names   │
                │  (one subprocess; reuses         │
                │   McpTestClient.__aenter__)      │
                └──────────────┬───────────────────┘
                               │
                               ▼
                ┌──────────────────────────────────┐
                │  _plugin.py:pytest_collect_file  │
                │  (synthesizes virtual Module)    │
                │                                  │
                │  filter:   tools where skip=False│ (Phase 13 SAFE-01)
                │  source:   _tests.py (10 funcs)  │
                │  parametrize over filtered tools │
                │  add marker mcp_contract         │
                │  override nodeid → <mcp-contracts>│
                └──────────────┬───────────────────┘
                               │
                               ▼
                ┌──────────────────────────────────┐
                │ pytest item tree:                │
                │  <mcp-contracts>::test_01[t1]    │
                │  <mcp-contracts>::test_01[t2]    │
                │  ... (10 tests × N tools)        │
                └──────────────┬───────────────────┘
                               │
                               ▼
                ┌──────────────────────────────────┐
                │ fixtures.py:_preflight (autouse) │
                │  _session_needs_preflight():     │
                │   - mcp_config_file set AND      │  (D-19)
                │   - item.iter_markers(           │
                │       "mcp_contract") any        │
                │  → Check shutil.which / Ollama / │
                │    list_tools (existing logic)   │
                └──────────────┬───────────────────┘
                               │
                               ▼
                ┌──────────────────────────────────┐
                │ test bodies execute              │
                │ (mcp_client, mcp_judge fixtures) │
                └──────────────────────────────────┘


    ┌──────────────────────────────────────────────┐
    │ CLI MODE (mcp-contracts run --config PATH)   │
    │                                              │
    │ cli.py:_load_config(PATH)                    │
    │   → validates path + loads YAML              │
    │ _runner.run_pytest_subprocess(...)           │
    │   argv += [-o "mcp_config_file=PATH"]        │ (D-11)
    │   no longer sets MCPTF_CONFIG_FILE           │
    └─────────────────┬────────────────────────────┘
                      │ subprocess pytest
                      ▼
              (same ini-driven path as library mode)
```

### Recommended Project Structure (post-Phase-27)

```
src/mcp_test_framework/
  _plugin.py          # Phase 26 skeleton + Phase 27 hook bodies (extended in place)
  _black_box_guard.py # NEW per D-18 — sys.modules check_black_box()
  contracts/
    __init__.py       # docstring rewrite (ini-route, no register())
    _tests.py         # NEW per D-04 — 10 test bodies moved from tests/contract/
    py.typed          # already shipping
  config.py           # NO CHANGE — yaml_file= kwarg already supported
  cli.py              # _load_config: env-var write replaced with kwarg-only
  _runner.py          # run_pytest_subprocess: subprocess argv adds `-o "mcp_config_file=PATH"`
  fixtures.py         # _session_needs_preflight: predicate flips to marker-based

tests/
  conftest.py         # DELETED or empty stub (D-05; pytest tolerates absent conftest)
  contract/
    test_mcp_tool_contract.py  # DELETED per D-05
  framework/          # unchanged (self-tests, AST checks, etc.)
  test_code/          # unchanged (operator-scenario authoring scope)

pyproject.toml        # [tool.pytest.ini_options] adds mcp_config_file = "./config.test.yaml"
```

### Pattern 1: Ini Key Registration

**What:** Register `mcp_config_file` via `parser.addini` in the plugin's existing `pytest_addoption` hook (Phase 26 P26-02 reserved the `--mcp-*` option group; ini registration is sibling).

**When to use:** Exactly once per plugin, in `pytest_addoption`. Pytest's `parser.addini` MUST be called from `pytest_addoption` — not from `pytest_configure` or any other hook.

**Example:**

```python
# Source: pytest docs + project _plugin.py
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.getgroup("mcp_test_framework", "MCP test framework options")
    parser.addini(
        "mcp_config_file",
        type="string",  # NOT "paths" — see note below
        default="",
        help=(
            "Path to MCP test framework YAML config; relative paths are "
            "resolved relative to pyproject.toml's directory. Absent or "
            "empty = library mode opted out (no contract tests injected)."
        ),
    )
```

**Critical:** Use `type="string"` (not `type="paths"`). `type="paths"` triggers pytest's automatic relative-path resolution against `inipath`, but resolves to a `list[Path]` — the wrong shape for a single-file lookup. Manual resolution against `config.rootpath` (the pytest 7+ canonical accessor; aliased as `config.inipath` for historical reasons) keeps the plugin's resolution explicit and inspectable. `[CITED: pytest reference docs; verified against pytest 9.0.x type system]`

### Pattern 2: Reading the Ini Value + Resolving Path

**What:** In `pytest_configure`, read the ini, resolve relative to `config.rootpath`, fail-loud if set-but-missing, no-op if absent.

```python
# Source: pytest docs + cli.py:_load_config (operator-tone error pattern)
def pytest_configure(config: pytest.Config) -> None:
    # Existing Phase 26 P26-02 body kept intact:
    config.addinivalue_line(
        "markers",
        "mcp_contract: framework-injected MCP contract test.",
    )

    # MCPTF_CONFIG_FILE deprecation warning (D-09)
    if os.environ.get("MCPTF_CONFIG_FILE"):
        warnings.warn(
            "MCPTF_CONFIG_FILE env var is deprecated since v1.4 and will be "
            "removed in v1.5 — use [tool.pytest.ini_options] mcp_config_file = "
            "PATH in pyproject.toml or pass --config PATH to mcp-contracts run instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Read the ini value
    raw = config.getini("mcp_config_file") or ""
    if not raw:
        # D-13: silent no-op (operator opted out)
        return

    # Resolve relative to inipath
    path = Path(raw)
    if not path.is_absolute():
        # config.rootpath is the directory containing pyproject.toml
        path = config.rootpath / path

    if not path.is_file():
        # D-14: fail-loud
        pytest.exit(
            f"mcp_config_file points at {path!s} which does not exist or is not a file\n"
            f"\nnext: check the path or run mcp-contracts config-init -o config.yaml",
            returncode=2,
        )

    # Load via existing pydantic-settings machinery (D-12)
    try:
        cfg = Config(yaml_file=str(path))
    except ValidationError as exc:
        # D-15: operator-tone, reuse cli.py's mapper if importable, else inline
        _pytest_exit_for_validation(exc, source=str(path))

    # Run the relocated black-box guard
    from mcp_test_framework._black_box_guard import check_black_box
    check_black_box()  # raises RuntimeError on leak

    # Stash on config for pytest_collect_file to pick up
    config._mcp_contracts_config = cfg  # type: ignore[attr-defined]
```

### Pattern 3: Virtual Module Synthesis via `pytest_collect_file`

**Status of this pattern in pytest's design:** pytest has NO official synthetic-module API. The maintainers themselves call current workarounds "at best a hack when a custom additional collection tree can't be provided." `[CITED: pytest-dev/pytest discussion #10246]`. However, the documented workarounds DO work for established plugins (e.g. pytest-bdd does similar synthesis).

**Two viable approaches:**

#### Approach A: Hybrid — real `_tests.py` file, custom Module override (recommended)

The `contracts/_tests.py` file IS a real Python file on disk (inside the installed wheel). The hybrid approach lets pytest's natural file-collection lifecycle run for `_tests.py`, but with a `Module` subclass that overrides `nodeid` and applies dynamic parametrization via `pytest_generate_tests` (defined inside `_tests.py` OR inside the plugin).

Trade-off: pytest's default file-walk collection won't visit `_tests.py` (it's outside `testpaths`). The plugin must explicitly inject it via `pytest_collectstart` / `pytest_collection`, OR call `Module.from_parent` directly inside `pytest_collection` and append to the session's items. This is the most pytest-asyncio-compatible path because the real file means `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` is discovered normally.

```python
# Source: pytest internals + pytest discussion #10246 + project pattern adapted
from pathlib import Path
import pytest
from _pytest.python import Module as _PytestModule

class _ContractsModule(_PytestModule):
    """Pytest Module subclass with overridden nodeid for synthetic display."""

    @property
    def nodeid(self) -> str:
        # Synthetic literal — does NOT use self.path or self.parent.nodeid
        return "<mcp-contracts>"

def pytest_collection(session: pytest.Session) -> None:
    """Inject the contracts module at top-level of the session."""
    cfg = getattr(session.config, "_mcp_contracts_config", None)
    if cfg is None:
        return  # D-13: no-op

    # SAFE-01 filter (Phase 13): only tools with skip=False are injected
    allowed_tools = sorted(
        name for name, t in cfg.tools.items() if not t.skip
    )
    if not allowed_tools:
        return  # D-16: empty allowlist, silent no inject

    # Discover live tool names (brief MCP handshake)
    discovered = _discover_tools_live(cfg)
    # Intersect: only tools the server advertises AND operator opted into
    parametrize_names = [n for n in allowed_tools if n in discovered]

    # Find the on-disk path to _tests.py inside the installed wheel
    from mcp_test_framework.contracts import _tests as _contracts_tests
    tests_path = Path(_contracts_tests.__file__)

    # Synthesize the Module and attach to session
    mod = _ContractsModule.from_parent(
        parent=session,
        path=tests_path,
    )
    # Stash the tool list on the module so its pytest_generate_tests sees it
    mod._mcp_parametrize_tools = parametrize_names  # type: ignore[attr-defined]
    mod._mcp_marker = pytest.mark.mcp_contract

    session.items.append(mod)  # actually need genitems; see Open Question O-2
```

**Critical caveat:** `session.items` is the post-collection flat list. To inject a `Module` at collection-start, the right hook is `pytest_collectstart` or `pytest_collection` returning the session collector. Wave 0 spike must validate exact attachment point — the difference between "appears in `--collect-only`" and "fixtures resolve correctly" can hinge on it. **Recommended Wave 0 spike: build a minimal end-to-end injection and run `pytest --collect-only` + a fixture-using test, verify pytest-asyncio still wires the loop scope.**

#### Approach B: Pure synthetic — `pytest_collect_file` with fake path

```python
def pytest_collect_file(parent: pytest.Collector, file_path: Path) -> pytest.Module | None:
    # Only fires for real files in testpaths; we IGNORE those and synthesize once
    return None  # synthesizing here doesn't trigger reliably

def pytest_collection(session: pytest.Session):
    # Manually construct the Module
    fake_path = session.config.rootpath / "<mcp-contracts>"
    mod = _ContractsModule.from_parent(parent=session, path=fake_path)
    # ... must implement collect() manually to yield Function items
```

Approach B requires re-implementing `Module.collect()` to walk the source and produce `Function` items WITHOUT pytest reading the file. This loses pytest-asyncio integration. **NOT RECOMMENDED.**

### Pattern 4: Parametrize at Injection Time (Phase 13 SAFE-01 Preserved Verbatim)

The 10 test bodies in `_tests.py` each take fixtures `(mcp_target_tool, tool_config, mcp_client, mcp_judge, mcp_rubric_*)` — these resolve naturally once `mcp_target_tool` is indirect-parametrized.

Today's `tests/conftest.py:pytest_generate_tests` does:

```python
metafunc.parametrize("target_tool", names, indirect=True, ids=names)
```

(Where `names` is the SAFE-01-filtered list.) Phase 27 moves this either into:
- **Option A**: A `pytest_generate_tests` hook INSIDE `contracts/_tests.py` itself (module-level), reading the parametrize list from `metafunc.config._mcp_contracts_config`. Pytest discovers and invokes it during the synthesized Module's collect phase.
- **Option B**: A `pytest_generate_tests` hook in the plugin, gated on `metafunc.definition.parent.nodeid.startswith("<mcp-contracts>")` or `metafunc.module.__name__ == "mcp_test_framework.contracts._tests"`.

**Recommendation: Option B (in `_plugin.py`).** Keeps `_tests.py` framework-agnostic and re-parameter-driven; plugin owns the SAFE-01 logic. Mirrors today's `tests/conftest.py` cleanly.

```python
def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Inject indirect parametrize for synthesized contract tests."""
    if "mcp_target_tool" not in metafunc.fixturenames:
        return
    if not getattr(metafunc.module, "_is_mcp_contracts_synthetic", False):
        return
    names: list[str] = getattr(metafunc.module, "_mcp_parametrize_tools", [])
    metafunc.parametrize(
        "mcp_target_tool",
        names,
        indirect=True,
        ids=names,
    )
```

**Marker auto-application:** apply `pytest.mark.mcp_contract` to the synthesized Module via `mod.add_marker(pytest.mark.mcp_contract)` so every Function child inherits it. Verified to propagate through `pytest_collection_modifyitems` and `item.iter_markers`.

### Anti-Patterns to Avoid

- **Don't** call `parser.addini` from `pytest_configure` — pytest's contract requires it from `pytest_addoption` only. Silently dropped otherwise.
- **Don't** set `os.environ["MCPTF_CONFIG_FILE"]` inside the plugin as a workaround for D-12. The whole point of D-09 is to kill the env var; reintroducing it internally violates the one-mechanism principle.
- **Don't** use `type="paths"` on `addini` for `mcp_config_file`. Returns `list[Path]`, not the single-path string we want.
- **Don't** inject items via `pytest_collection_modifyitems` (post-collection mutation) — pytest-asyncio's session-scope wiring runs during collection and won't see post-modify items. `[CITED: pytest discussion #10246]`
- **Don't** call `pytest.skip()` at runtime for unselected tools. The Phase 13 SAFE-01 + v1.1.1 hotfix invariant is: unselected tools are EXCLUDED FROM PARAMETRIZE (never collected), not runtime-skipped. (Memory: `project_v1_1_skip_bug`.)
- **Don't** modify `tests/contract/test_mcp_tool_contract.py` and `tests/conftest.py:pytest_generate_tests` instead of deleting — leaving both alive creates two parametrize paths and silent collection-duplication. D-05 is hard delete.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Loading YAML into the Config schema | New YAML loader | Existing `Config(yaml_file=PATH)` via pydantic-settings | Loader already supports kwarg-path; validation paths already operator-tone via `_emit_operator_error_for_validation`. |
| Resolving relative paths against pyproject location | Walk-up-tree heuristic | `config.rootpath / path` | Pytest 7+ canonical; handles edge cases like `pytest.ini` co-located with `pyproject.toml`. |
| Brief MCP handshake for tool discovery | Open-coded stdio_client | `McpTestClient.__aenter__` | Isolation-aware per Phase 06 D-16; same code path as cli.py's `_discover_tools_for_run`. |
| Operator-tone error rendering | New rendering function | `cli.py:_emit_operator_error` (or fixtures.py:`_pytest_exit_operator_tone`) | Already shaped per docs/ERROR-STYLE.md; pinned by regression test. |
| Marker application | Manual list mutation | `item.add_marker(pytest.mark.mcp_contract)` or `Module.pytestmark` | Native pytest API; `iter_markers` sees both forms. |
| DeprecationWarning emission semantics | Custom dedup logic | stdlib `warnings.warn(DeprecationWarning, stacklevel=2)` + pyproject `filterwarnings = ["always::DeprecationWarning:mcp_test_framework"]` | Phase 25 already established the pattern; default filter handles once-per-process dedup. |
| Black-box guard logic | New file checks | Existing `sys.modules` scan (relocated verbatim from `tests/conftest.py:46-55`) | Behavior contract is unchanged; only the file location moves. |

**Key insight:** Phase 27 is 80% relocation, 20% net-new code. The new code is: ini key registration, the `_ContractsModule` subclass with nodeid override, the synthesizing `pytest_collection` hook, the marker-based preflight predicate, the relocated `_black_box_guard.py` (one function from existing logic), the CLI subprocess flag flip (one-line change in `_runner.py:_build_pytest_args` + `cli.py:_load_config` env-var removal).

---

## Runtime State Inventory

This is a relocation + small-net-add phase, not a rename. Still worth a check.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no databases, no on-disk caches that store the literal string `MCPTF_CONFIG_FILE` or `mcp_config_file`. | None. |
| Live service config | None — n8n / Datadog / etc. not in scope; framework runs in-process. | None. |
| OS-registered state | None — no scheduled tasks, no pm2 processes, no systemd units. | None. |
| Secrets/env vars | `MCPTF_CONFIG_FILE` exists in shells and dev `.env` files but is plain env-var-as-pointer (no secret material). After D-09, code stops READING it (library mode) and stops WRITING it (CLI mode). Operators with stale exports get a DeprecationWarning. | Document in deprecation copy; v1.5 removal commit also strips env-var sets from `cli.py:_load_config` (currently writes the env var on line 300). |
| Build artifacts | None — the deleted `tests/contract/test_mcp_tool_contract.py` is git-tracked, not a build artifact. `tests/conftest.py` is git-tracked. No `.pyc` cleanup needed (Python re-resolves imports from `.py` automatically). | None. |

**Canonical question — "After every file in the repo is updated, what runtime systems still have the old string cached, stored, or registered?"** Answer: shell `MCPTF_CONFIG_FILE` exports survive across sessions; the deprecation warning will surface these to operators on next run. No data migration needed; just a behavioral nudge.

---

## Environment Availability

Phase 27 is pure code/config refactor — no new external dependencies. Skipped per the standard rule.

Step 2.6: SKIPPED (no external dependencies identified beyond the already-installed stack: Python 3.14, uv, pytest, pytest-asyncio, pydantic-settings, mcp SDK).

---

## Common Pitfalls

### Pitfall 1: `pytest_collect_file` doesn't fire for non-filesystem paths

**What goes wrong:** Plugin tries to use `pytest_collect_file` for a fake `Path("<mcp-contracts>")` — never fires because pytest only invokes the hook for files it walks from `testpaths`.

**Why it happens:** `pytest_collect_file` is filesystem-driven by design.

**How to avoid:** Use `pytest_collection` (called once for the session) to manually construct and attach the `Module`. The Module's underlying `path` attribute can still point to the real `_tests.py` inside the installed wheel; only `nodeid` is synthetic.

**Warning signs:** `--collect-only` shows zero items even with `mcp_config_file` set and a valid config; no errors raised.

### Pitfall 2: pytest-asyncio strict mode + synthetic Module = no async loop

**What goes wrong:** Synthesized Module's test items run but raise `RuntimeError: no event loop running` or `pytest-asyncio detected unknown loop scope`.

**Why it happens:** pytest-asyncio reads `pytestmark = [...]` from the module's source. If Approach B (pure synthetic) is used, the module's `__file__` is fake and pytest-asyncio can't introspect it.

**How to avoid:** Approach A (hybrid) uses the real `_tests.py` on disk. Verify in Wave 0 spike that `mod.path` points at the real file and pytest-asyncio sees the `pytestmark` declaration. Approach B requires manually adding `mod.add_marker(pytest.mark.asyncio(loop_scope="session"))` to every injected item AND ensuring `asyncio_default_fixture_loop_scope = "session"` is set in pyproject (it is).

**Warning signs:** Tests collected but error out at fixture-setup time with cancel-scope or loop-binding errors.

### Pitfall 3: `parser.getini` returns empty string when ini missing AND `default=""` set

**What goes wrong:** Plugin tests `if not config.getini("mcp_config_file")` to detect "unset", but pytest returns the configured default ("") in BOTH the unset-with-default and explicitly-empty-string cases.

**Why it happens:** pytest's `getini` doesn't distinguish "unset" from "set to default".

**How to avoid:** Set `default=""` and treat empty string as "operator did not configure". This matches D-13 silent-no-op semantics — operator who writes `mcp_config_file = ""` explicitly gets the same behavior as operator who omits the line. Documented behavior; not a bug.

**Warning signs:** Operator confused about why their `mcp_config_file = ""` doesn't disable injection (it does — but they may not have realized that's what happened).

### Pitfall 4: pytest's `-o key=value` quoting on Windows PowerShell

**What goes wrong:** CLI mode's subprocess argv `pytest -o "mcp_config_file=C:\path\to\config.yaml"` gets parsed weirdly under PowerShell's argument splitting.

**Why it happens:** PowerShell handles quoted strings differently from POSIX shells; backslash in path may confuse pytest's `-o` parser.

**How to avoid:** Use `subprocess.run(argv, ...)` with `argv = [..., "-o", f"mcp_config_file={path}"]` (two separate list elements, no embedded quotes). `subprocess.run` does NOT shell-interpret; quoting concerns vanish. This matches `_runner.py`'s existing argv-list pattern (`subprocess.run([sys.executable, "-m", "pytest", ...])`).

**Warning signs:** Manual `pytest -o "mcp_config_file=..."` works fine from a terminal; CLI mode fails with "unknown ini option" or "no tests collected" only on Windows.

### Pitfall 5: Test-code-author preflight breaks (test-code tests don't carry `mcp_contract` marker)

**What goes wrong:** Phase 21's `tests/test_code/` scenarios fire against live homelab-mcp via the preflight gate today (path-prefix match on `tests/test_code/`). After D-19 flips to marker-based, test-code tests have NO matching marker and `_session_needs_preflight()` returns False → preflight skipped → live MCP fails at fixture-setup time with a cryptic error instead of the operator-tone "Cannot reach Ollama".

**Why it happens:** D-19's marker predicate is correct for contract tests but wrong for test-code-author tests (they're operator scenarios, not framework-injected).

**How to avoid:** Extend `_session_needs_preflight()` to accept EITHER `mcp_contract` marker OR a nodeid prefix check (`tests/test_code/` or `tests/sdet/`). Alternative: auto-apply a separate `mcp_test_code` marker via a `tests/test_code/conftest.py` `pytest_collection_modifyitems` hook (operator-facing scope still uses a marker; semantically honest).

**Warning signs:** Framework's own test-code dogfood scenarios suddenly fail with raw MCP timeout errors instead of preflight diagnostics. Phase 27 plan MUST address this — see Open Question O-5.

### Pitfall 6: Wheel-introspection AST guard scope expansion (PACK-04 → LIB-08)

**What goes wrong:** Phase 26 PACK-04 wheel test only checks `tests/` doesn't leak into the wheel. Phase 27 D-18 + LIB-08 ALSO require the test to fail on banned `homelab_mcp` imports anywhere inside `src/` (because the runtime guard now lives in production code, not test code).

**Why it happens:** Scope expansion of an existing AST walker.

**How to avoid:** Extend the visitor in `tests/framework/test_wheel_introspection.py` (or wherever PACK-04 landed) to walk every `.py` file inside `src/mcp_test_framework/` and flag `ast.Import` / `ast.ImportFrom` nodes whose module starts with `homelab_mcp`. Today's check is per-file glob existence; the AST walk is net-new logic.

**Warning signs:** A `from homelab_mcp.client import X` accidentally added to `src/mcp_test_framework/_black_box_guard.py` (ironically) goes undetected.

---

## Code Examples

Verified patterns from official sources + project codebase.

### Example 1: `parser.addini` ini key registration

```python
# Source: pytest reference docs + _pytest/config/argparsing.py
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.getgroup("mcp_test_framework", "MCP test framework options")
    parser.addini(
        name="mcp_config_file",
        type="string",
        default="",
        help="Path to MCP test framework YAML config (relative to pyproject.toml dir).",
    )
```

### Example 2: Reading ini value + path resolution

```python
# Source: project pattern (cli.py:_load_config) adapted
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "mcp_contract: framework-injected MCP contract test.")
    raw = (config.getini("mcp_config_file") or "").strip()
    if not raw:
        return  # D-13
    path = Path(raw)
    if not path.is_absolute():
        path = config.rootpath / path
    if not path.is_file():
        pytest.exit(f"mcp_config_file points at {path!s} which does not exist", returncode=2)  # D-14
    try:
        cfg = Config(yaml_file=str(path))
    except ValidationError as exc:
        # D-15 — reuse cli.py mapper OR inline operator-tone
        pytest.exit(_format_validation_error(exc, source=str(path)), returncode=2)
    from mcp_test_framework._black_box_guard import check_black_box
    check_black_box()  # raises RuntimeError on leak
    config._mcp_contracts_config = cfg  # type: ignore[attr-defined]
```

### Example 3: Custom Module subclass with synthetic nodeid

```python
# Source: pytest internals + #10246 discussion adapted
from _pytest.python import Module as _PytestModule

class _ContractsModule(_PytestModule):
    """Synthesized contracts module with nodeid override.

    Underlying `path` points at the real `_tests.py` inside the installed
    wheel so pytest-asyncio's pytestmark discovery works normally.
    `nodeid` is overridden to render as `<mcp-contracts>` in pytest's
    output instead of `.venv/lib/.../contracts/_tests.py`.
    """

    @property
    def nodeid(self) -> str:
        return "<mcp-contracts>"
```

### Example 4: Plugin's `pytest_collection` injection (Approach A)

```python
# Source: project pattern; spike-validated in Wave 0
def pytest_collection(session: pytest.Session) -> None:
    cfg = getattr(session.config, "_mcp_contracts_config", None)
    if cfg is None:
        return
    allowed = sorted(name for name, t in cfg.tools.items() if not t.skip)
    if not allowed:
        return  # D-16
    discovered = _discover_tools_live(cfg)
    parametrize_names = [n for n in allowed if n in discovered]
    if not parametrize_names:
        return

    from mcp_test_framework.contracts import _tests as _ct
    tests_path = Path(_ct.__file__)
    mod = _ContractsModule.from_parent(parent=session, path=tests_path)
    mod._is_mcp_contracts_synthetic = True
    mod._mcp_parametrize_tools = parametrize_names
    mod.add_marker(pytest.mark.mcp_contract)

    # pytest's session.perform_collect picks this up via session.items / session.collect()
    # Exact attachment ritual confirmed by spike (Wave 0).
    session.testscollected = (session.testscollected or 0) + 0  # touch to trigger
    # Returning the items happens via session._collect() — see _pytest/main.py
```

**Wave 0 spike NEEDED:** The exact session-attachment ritual. The spike should output `pytest --collect-only` showing one Module under `<mcp-contracts>` with N×10 items.

### Example 5: Parametrize over discovered tools

```python
def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "mcp_target_tool" not in metafunc.fixturenames:
        return
    if not getattr(metafunc.module, "_is_mcp_contracts_synthetic", False):
        return
    names = getattr(metafunc.module, "_mcp_parametrize_tools", [])
    metafunc.parametrize("mcp_target_tool", names, indirect=True, ids=names)
```

### Example 6: Marker-based preflight predicate (D-19)

```python
# Source: project pattern (fixtures.py:_session_needs_preflight) adapted
def _session_needs_preflight(request: pytest.FixtureRequest) -> bool:
    config = request.config
    # No ini set = library mode opted out = no preflight (D-13)
    if not (config.getini("mcp_config_file") or "").strip():
        # BUT still need to support tests/test_code/ scenarios — see Open Question O-5
        return _has_test_code_scope(request)
    # Any item carries the mcp_contract marker?
    for item in (getattr(request.session, "items", []) or []):
        if any(item.iter_markers("mcp_contract")):
            return True
    # Fall-back: test-code-author scope handling (until O-5 resolved)
    return _has_test_code_scope(request)


def _has_test_code_scope(request: pytest.FixtureRequest) -> bool:
    """Phase 21 carry-forward: tests/test_code/ tests need preflight too."""
    for item in (getattr(request.session, "items", []) or []):
        # Use POSIX-style separators; pytest normalizes.
        if "tests/test_code/" in item.nodeid or "tests/sdet/" in item.nodeid:
            return True
    return False
```

### Example 7: CLI mode subprocess flag

```python
# Source: project pattern (_runner.py:_build_pytest_args) adapted
def _build_pytest_args(
    junit_xml: Path | None,
    pytest_args: list[str] | None,
    *,
    mcp_config_file: Path | None = None,  # NEW
    with_framework: bool = False,
    sdet: bool = False,
) -> list[str]:
    args = ["tests/contract"]  # ... existing logic ...
    if mcp_config_file is not None:
        # D-11: -o flag overrides ini at runtime; subprocess argv list form
        # avoids any quoting concerns on Windows.
        args.extend(["-o", f"mcp_config_file={mcp_config_file}"])
    # ... rest unchanged
```

And `cli.py:_load_config` drops its `os.environ["MCPTF_CONFIG_FILE"] = str(resolved)` line (currently `cli.py:300`):

```python
# Before (cli.py:300):
os.environ["MCPTF_CONFIG_FILE"] = str(resolved)
return Config(yaml_file=str(resolved))

# After: caller passes `resolved` down to the subprocess builder.
return Config(yaml_file=str(resolved))  # only the kwarg load remains
```

`run_pytest_subprocess` receives `mcp_config_file=resolved` and threads it into `_build_pytest_args`.

---

## State of the Art

| Old Approach (pre-Phase-27) | Current Approach (post-Phase-27) | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `tests/conftest.py:pytest_generate_tests` walks discovered tool list | Plugin's `pytest_generate_tests` is gated on synthetic-module flag; SAFE-01 filter relocated | Phase 27 | Operator no longer needs `tests/` directory at all to consume contract tests |
| `MCPTF_CONFIG_FILE` env var as path pointer (in-process AND subprocess) | `mcp_config_file` ini key (operator pyproject) + `-o "mcp_config_file=..."` (CLI subprocess) | Phase 27 D-09..D-12 | One config-resolution route; precedence-confusion class of bug closed |
| `tests/contract/test_mcp_tool_contract.py` file lives in operator's test tree | Test bodies in `src/mcp_test_framework/contracts/_tests.py`; injected via plugin | Phase 27 D-04..D-05 | Operator no longer copies/maintains framework's test bodies |
| Black-box `sys.modules` guard in `tests/conftest.py` | Same logic in `src/mcp_test_framework/_black_box_guard.py` | Phase 27 D-18 | Enforceable in wheel installs (Phase 26's wheel-introspection AST extends) |
| `_session_needs_preflight()` keys on nodeid path prefix | Keys on `mcp_contract` marker presence | Phase 27 D-19 | Library-mode preflight semantically honest; carry-forward fix for test-code path (see O-5) |

**Deprecated/outdated as of Phase 27:**
- `MCPTF_CONFIG_FILE` env var — DeprecationWarning emitted; removed in v1.5.
- `register()` API surface — never shipped; the post-pivot route IS the public API.
- `tests/contract/conftest.py` calling `register(...)` (Phase 30 CLOSE-01 original wording) — pre-empted by D-07.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `pytest_collection` is the canonical hook for session-level Module synthesis (vs `pytest_collect_file` or `pytest_collectstart`) | "Pattern 3" + "Pitfall 1" | MEDIUM: spike resolves; if wrong, fallback to `pytest_collectstart` with similar shape. Pytest discussion #10246 acknowledges multiple approaches work, none is officially blessed. [ASSUMED — pytest docs do not authoritatively recommend one] |
| A2 | pytest-asyncio's `pytestmark` / `loop_scope` discovery works on a Module whose `nodeid` is overridden but `path` is real | "Approach A (hybrid)" | HIGH: if pytest-asyncio reads `__module__.__file__` instead of `mod.path`, the discovery works regardless. If it keys on `mod.nodeid`, we may need to apply `pytest.mark.asyncio(loop_scope="session")` per-item manually. [ASSUMED — not verified in spike yet] |
| A3 | Operator-tone `_emit_operator_error` (in `_runner.py`) is callable from plugin context (no Typer import cycle) | "Pattern 2" | LOW: `_emit_operator_error` already lives in `_runner.py` (post Phase 14 reloc) and uses `typer.echo` + `typer.Exit`. From the plugin context, `typer.Exit` would NOT exit pytest cleanly. Use `pytest.exit(message, returncode=2)` instead (matches `fixtures.py:_pytest_exit_operator_tone`). [VERIFIED: fixtures.py:57 already has the pytest-native version] |
| A4 | `config.test.yaml` is the framework's existing test config file path that D-06 should reference | "Standard Stack" + Open Question O-1 | LOW: file exists at repo root (verified via glob). May want a different filename for clarity (e.g., `config.framework-ci.yaml`) but `config.test.yaml` is sufficient. [VERIFIED: file exists] |
| A5 | Phase 26 already shipped the pytest11 entry point and the plugin auto-loads in editable installs | "Architecture Patterns" | HIGH risk if wrong, but [VERIFIED: pyproject.toml:27-32 shows `[project.entry-points.pytest11] mcp_test_framework = "mcp_test_framework._plugin"`. uv editable installs honor entry points.] |
| A6 | Brief MCP handshake (one subprocess) at `pytest_configure` time is acceptable (≤1s warm) | "Tool Discovery Lifecycle" | LOW: today's CLI mode does exactly this via `_discover_tools_for_run`; library mode adds at most one extra short subprocess per pytest invocation. If operator runs `pytest --collect-only` they still pay this cost — could matter for IDE collect-on-save loops. Mitigation: cache results on `config._mcp_contracts_discovered` so re-runs in the same process are free. [ASSUMED tolerable] |
| A7 | The `Config(yaml_file=PATH)` constructor kwarg surface is identical between CLI mode and the plugin's library-mode call site | "Pattern 2" | LOW: [VERIFIED: src/mcp_test_framework/config.py:228 — the loader pops `yaml_file` from `init_settings.init_kwargs` regardless of caller.] |
| A8 | Today's `tests/conftest.py:pytest_generate_tests` discovery cache `_runner._DISCOVERED_TOOL_NAMES` does NOT need to survive — plugin owns its own short-lived discovery | "Tool Discovery Lifecycle" + Open Question O-4 | MEDIUM: `_runner._DISCOVERED_TOOL_NAMES` IS used by the CLI wrapper's reporter for "Skipping (N)" header counts. After D-05 deletes `pytest_generate_tests`, this cache's only consumer is the wrapper-side discovery in cli.py — which already exists and uses its own RenderContext storage. Plugin's discovery can be entirely separate. Recommendation: keep `_runner._DISCOVERED_TOOL_NAMES` as-is (used by allowlist unit tests that patch it directly per memory: line 1366 of `_runner.py`). [ASSUMED based on grep + memory] |
| A9 | `mod.add_marker(pytest.mark.mcp_contract)` on a Module propagates to child Function items at `iter_markers` time | "Pattern 4" | LOW: pytest's marker resolution walks up the parent chain. [CITED: pytest reference docs on item.iter_markers — walks `item -> module -> class -> session`.] |
| A10 | The `gen-test-classes` CLI command's `MCPTF_CONFIG_FILE` read site (cli.py:_load_config) is the SAME function the `run` and `list-tools` commands use, so Phase 27's `cli.py:_load_config` rewire (removing the `os.environ` set) cascades through ALL commands consistently | "Claude's Discretion — gen-test-classes punt" | LOW: [VERIFIED: cli.py:_load_config is shared across `run`, `list-tools`, `config-init`, `gen-test-classes`]. The rewire is one function-body change; all commands benefit. |

---

## Open Questions

### O-1: Exact framework test config file path for D-06

- **What we know:** `config.test.yaml`, `config.yaml`, and `config.scratch.yaml` all exist at repo root. `config.example.yaml` is the template. The framework's CI tests pass `--config` explicitly OR rely on `MCPTF_CONFIG_FILE` set by harness.
- **What's unclear:** Which file should `mcp_config_file = "./..."` point at? The most useful candidate is `config.test.yaml` (matches naming convention; intended for framework CI). However, `config.test.yaml` may not contain all the tools the contract suite expects to parametrize over. Currently the framework's own CI runs `pytest tests/contract` with `MCPTF_CONFIG_FILE=config.test.yaml` or similar.
- **RESOLVED**: use `config.test.yaml` for framework dogfood (per Plan 27-05 Task 1).
- **Recommendation:** Wave 0 spike inspects `config.test.yaml` contents; if it has at least one `skip:false` tool, use it. Otherwise either (a) update `config.test.yaml` to enable 1–2 tools for the dogfood run (matches operator config style), or (b) create a new `config.dogfood.yaml` with `list_keyring_credentials` + `suggest_deployments` enabled. Either way, the planner should ALSO update `.gitignore` or the test fixture to ensure operators don't trip over the dogfood config when scaffolding from `config.example.yaml`.

### O-2: Exact session-attachment ritual for the synthesized Module

- **What we know:** pytest's `pytest_collection` hook receives `session` and can manipulate the collection tree. `Module.from_parent(parent=session, path=...)` constructs the Module. The exact step that makes the items appear in `--collect-only` and reach test execution is implementation-detail-shaped — pytest's internal `Session._collect()` walks the configured `testpaths` and synthesizes Module collectors for matching files, NOT from `pytest_collection` hook return.
- **What's unclear:** Whether to (a) attach the Module to `session._collected` (a private list), (b) override `session.collect()` via a subclass or monkey-patch, (c) yield the Module from a custom `pytest_collectstart` hook, or (d) use the `pytest_collection` hook with a wrapper that returns `[mod]` to extend the discovered set. Each has different post-collection consequences for `pytest_collection_modifyitems`, marker propagation, and pytest-asyncio integration.
- **RESOLVED**: Wave 0 spike in Plan 27-01 Task 3 validates the session-attachment ritual; fallback to thin re-export-file pattern documented (`tests/contract/test_mcp_tool_contract.py` → `from mcp_test_framework.contracts._tests import *`).
- **Recommendation:** **Time-box a Wave 0 spike (1-2 hours).** Build the minimal `_ContractsModule` + `pytest_collection` injection, run `pytest --collect-only`, iterate until items show up under `<mcp-contracts>`. The spike output IS the implementation pattern; capture it as a code snippet in plan 27-02. Fallback if blocked: revert to a thin `tests/contract/test_mcp_tool_contract.py` that does `from mcp_test_framework.contracts._tests import *` (operator never sees it; CI dogfood still works; D-04 satisfied with one-file indirection).

### O-3: pytest-asyncio `pytestmark` discovery on synthesized Module

- **What we know:** `_tests.py` declares `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` (matches today's `test_mcp_tool_contract.py:49`). pytest-asyncio reads pytestmark by introspecting `mod.obj` (the actual Python module object).
- **What's unclear:** Does `_ContractsModule(_PytestModule)` with overridden `nodeid` (but real `path`) still let pytest-asyncio find `pytestmark`? Likely yes — `Module.obj` resolves via `path` not `nodeid` — but unverified.
- **RESOLVED**: Wave 0 spike sub-check D verifies pytest-asyncio `loop_scope="session"` survives the synthetic-nodeid override; explicit `mod.add_marker(pytest.mark.asyncio(loop_scope="session"))` is the captured fallback.
- **Recommendation:** Bundle into the Wave 0 spike. Add ONE async test to the spike's `_tests.py`, run it, verify it actually executes (not skipped, not errored at loop-binding). If it fails, fall back to `mod.add_marker(pytest.mark.asyncio(loop_scope="session"))` at injection time (applied to the Module, inherited by children).

### O-4: `_runner._DISCOVERED_TOOL_NAMES` cache survival

- **What we know:** `_runner._DISCOVERED_TOOL_NAMES` is used by today's `tests/conftest.py:pytest_generate_tests` for parametrize-time filtering, and ALSO by allowlist unit tests that patch it directly (`_runner._DISCOVERED_TOOL_NAMES = [...]`). After D-05 deletes `pytest_generate_tests`, the cache loses its primary consumer.
- **What's unclear:** Do the allowlist unit tests still need to patch the cache, or do they migrate to patching the plugin's discovery helper? Are there other in-pytest paths (tests/framework/...) that read it?
- **RESOLVED**: `_runner._DISCOVERED_TOOL_NAMES` cache survives for v1.4 CLI header counts; revisit in Phase 28 (chose option A — minimal-diff). Plan 27-03 plugin populates the cache during its discovery run for downstream consumers; allowlist unit tests remain unchanged.
- **Recommendation:** Plan should include a grep audit of `_DISCOVERED_TOOL_NAMES` references and decide whether to:
  - **A**: Keep the cache alive (plugin populates it during `pytest_configure`; allowlist tests unchanged); OR
  - **B**: Delete the cache; migrate allowlist tests to patch the plugin's discovery seam (`mcp_test_framework._plugin._discover_tools_live`).
  - Suggest **A** for minimal-diff; revisit in Phase 28 alongside CFG cleanup.

### O-5: Test-code-author preflight predicate post-D-19

- **What we know:** D-19 flips `_session_needs_preflight` to marker-based detection. Test-code tests (`tests/test_code/`) do NOT carry `mcp_contract` (they're operator scenarios). Today's predicate fires for them via the `tests/test_code/` path prefix.
- **What's unclear:** Should the predicate (a) OR-in a path-prefix check for `tests/test_code/` and `tests/sdet/`, (b) auto-apply a separate `mcp_test_code` marker via a `tests/test_code/conftest.py` hook, or (c) something else?
- **RESOLVED**: `_session_needs_preflight` predicate uses marker primary + path-prefix carveout for `tests/test_code/` + `tests/sdet/` (Plan 27-04 Task 3 enforces this). Path-prefix OR (option a). Lowest churn; preserves existing test-code-author behavior verbatim. The two predicates can coexist:
  ```python
  return (
      _has_mcp_contract_marker(request) or
      _has_test_code_scope_nodeid(request)
  )
  ```
  Both paths still gate on `mcp_config_file` being set when running contract tests. Plan must include a test asserting test-code scope still triggers preflight after the flip.

### O-6: `gen-test-classes` CLI input-config rewire — Phase 27 or Phase 28?

- **What we know:** `gen-test-classes` uses `cli.py:_load_config` (same as `run`, `list-tools`). After Phase 27 removes the `os.environ["MCPTF_CONFIG_FILE"] = ...` write at cli.py:300, ALL CLI commands stop writing the env var. Reading is unchanged at the env-var branch (cli.py:248-265).
- **What's unclear:** Should `_load_config`'s env-var-read branch ALSO be removed (D-09 spirit: kill the env var entirely), or kept for one milestone as a compat path?
- **RESOLVED**: `gen-test-classes` env-var-read branch retained in v1.4 for consistency with `_load_config` (CLI mode preserves env-var READ for v1.4 back-compat); removed in v1.5 cleanup alongside the plugin's deprecation-warning emission. Keep the env-var-read branch in `_load_config` for v1.4 — operators with `MCPTF_CONFIG_FILE` in their shell still get a working CLI run. The DeprecationWarning fires once from the plugin (library mode) AND once from `_load_config` (CLI mode) — both via the same hardcoded copy. Remove both call sites in v1.5. This keeps Phase 27 narrowly scoped to "stop WRITING the env var; warn when READING it from operator's env."

---

## Validation Architecture

> The phase-level workflow.nyquist_validation is **disabled** for v1.4 per CONTEXT.md and project config. Including this section is informational — captures the test infrastructure Phase 27 depends on so the planner can verify it during dogfood.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 1.x (strict mode) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/framework/unit -x` |
| Full suite command | `uv run pytest tests/` (post-Phase-27: `uv run pytest` reads `testpaths = ["tests"]`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIB-01 | Operator with `mcp_config_file` ini set sees contract tests in collection | integration (live MCP) | `pytest --collect-only` against a real config | partial — Wave 0 spike creates first; later plan formalizes as `tests/framework/integration/test_library_mode_injection.py` |
| LIB-01 | Operator with `mcp_config_file` unset sees ZERO injected tests | unit | `pytest --collect-only` with empty ini | Wave 0 |
| LIB-02 | Nodeid renders as `<mcp-contracts>::test_<name>[<tool>]` | unit | `pytest --collect-only -q` regex assertion in framework self-test | Wave 0 |
| LIB-04 | `pytest -m mcp_contract` selects injected tests | unit | new framework self-test | Wave 0 |
| LIB-07 | `_session_needs_preflight()` returns True iff marker present AND ini set | unit | `tests/framework/unit/test_preflight_predicate.py` (existing — extend) | extend existing |
| LIB-08 | Wheel-introspection AST walk fails on banned `homelab_mcp` imports in `src/` | unit | extend `tests/framework/test_wheel_introspection.py` (PACK-04 file) | extend existing |
| D-09 | `MCPTF_CONFIG_FILE` env-var set triggers DeprecationWarning (once per process) | unit | `tests/framework/unit/test_mcptf_config_file_deprecation.py` | Wave 0 |
| D-14 | Path-not-exists triggers operator-tone `pytest.exit(returncode=2)` | unit | new framework self-test (subprocess pytest) | Wave 0 |
| D-15 | Malformed YAML triggers operator-tone error | unit | new framework self-test | Wave 0 |
| D-19 | Marker-based preflight predicate | unit | extend `tests/framework/unit/test_preflight_predicate.py` | extend existing |
| Move-and-dogfood (D-04..D-07) | Framework's own CI passes through library-mode injection path | integration (CI) | `uv run pytest` from clean checkout | end-to-end dogfood |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/framework/unit -x` (fast, no live MCP)
- **Per wave merge:** `uv run pytest tests/framework -x` (framework self-tests, still no live MCP)
- **Phase gate:** `uv run pytest` (full suite including the live contract path via library-mode injection)

### Wave 0 Gaps

- [ ] `tests/framework/unit/test_library_mode_injection.py` — collection-only tests for D-13, D-14, D-15, D-16, nodeid shape, marker auto-application
- [ ] `tests/framework/unit/test_mcptf_config_file_deprecation.py` — DeprecationWarning emission semantics (once-per-process, hardcoded copy)
- [ ] Extension of `tests/framework/unit/test_preflight_predicate.py` (or wherever the existing predicate test lives) for D-19 + O-5
- [ ] Extension of `tests/framework/test_wheel_introspection.py` (PACK-04) for banned-imports AST walk in src/
- [ ] Spike script `scripts/spike_phase27_collect.py` OR `tests/framework/spike_test_collect_synth.py` validating session-attachment ritual + pytest-asyncio compat
- [ ] **`src/mcp_test_framework/contracts/_tests.py`** — created in plan 27-XX with 10 test bodies relocated verbatim
- [ ] **`src/mcp_test_framework/_black_box_guard.py`** — created in plan 27-XX with `check_black_box()` function

---

## Sources

### Primary (HIGH confidence)

- `src/mcp_test_framework/_plugin.py` (the Phase 26 skeleton being extended) — read in full
- `src/mcp_test_framework/config.py` (verified `yaml_file` kwarg surface at line 228) — read in full
- `src/mcp_test_framework/cli.py` (verified env-var-write site at line 300; shared `_load_config` across commands) — read in full
- `src/mcp_test_framework/_runner.py` (verified subprocess argv-list pattern; `_DISCOVERED_TOOL_NAMES` cache location) — read in full
- `src/mcp_test_framework/fixtures.py` (verified `_session_needs_preflight` predicate at line 125-149; preflight body) — read in full
- `tests/contract/test_mcp_tool_contract.py` (10 test bodies to extract verbatim) — read in full
- `tests/conftest.py` (verified `pytest_generate_tests` + black-box guard at line 30-55) — read in full
- `pyproject.toml` (verified pytest11 entry-point declaration at line 27-32 + `[tool.pytest.ini_options]` block) — read in full
- `.planning/phases/27-register-api-contracts-sub-package-test-extraction-lib/27-CONTEXT.md` — SOURCE OF TRUTH per pivot
- `.planning/phases/27-register-api-contracts-sub-package-test-extraction-lib/27-DISCUSSION-LOG.md` — pivot rationale + locked decisions

### Secondary (MEDIUM confidence — verified against multiple sources)

- pytest documentation on `parser.addini` types — [Configuration (latest)](https://docs.pytest.org/en/stable/reference/customize.html) + [argparsing source](https://docs.pytest.org/en/stable/_modules/_pytest/config/argparsing.html)
- pytest `-o key=value` override semantics — [Configuration override](https://docs.pytest.org/en/stable/reference/customize.html) (note: last occurrence wins; multiple `-o` flags supported per [Issue #6464](https://github.com/pytest-dev/pytest/issues/6464))
- pydantic-settings `YamlConfigSettingsSource` runtime kwarg pattern — [Pydantic Settings docs](https://docs.pydantic.dev/latest/api/pydantic_settings/) + [pydantic-settings #259](https://github.com/pydantic/pydantic-settings/issues/259)
- pytest custom directory collector pattern — [pytest custom directory example](https://docs.pytest.org/en/stable/example/customdirectory.html)

### Tertiary (LOW confidence — needs Wave 0 spike to verify)

- Synthetic-module collection via `pytest_collection` hook session attachment — [pytest discussion #10246](https://github.com/pytest-dev/pytest/discussions/10246) (maintainers acknowledge this is a documented hack; multiple plugins use it but none has the "official" implementation pattern)
- pytest-asyncio's `pytestmark` discovery on Module subclass with overridden `nodeid` but real `path` — no authoritative source found; spike-validated

---

## Metadata

**Confidence breakdown:**

- Locked-by-CONTEXT decisions (D-01..D-19): HIGH — explicitly captured + traced to user-as-visionary calls
- Ini key registration mechanics (Pattern 1): HIGH — pytest's `parser.addini` API is stable since pytest 3.x; verified against current docs
- Pydantic-settings `yaml_file=PATH` kwarg surface (D-12): HIGH — VERIFIED against existing `config.py:228` (no inference required)
- `-o key=value` subprocess flag for CLI mode (D-11): HIGH — VERIFIED against pytest reference docs + Issue #6464
- Synthetic Module injection mechanics (Pattern 3 + O-2): MEDIUM — no official API; spike-validated approach
- pytest-asyncio compat with synthetic Module (Pitfall 2 + O-3): MEDIUM — likely works via real `path`; spike validates
- Test-code-author preflight side-effect of D-19 (Pitfall 5 + O-5): MEDIUM — predicate-OR is the recommended workaround, but the user should sign off
- Marker propagation Module→Function (A9): HIGH — pytest's `iter_markers` is well-documented
- CLI mode subprocess one-route (D-11 cascade): HIGH — `_runner._build_pytest_args` already returns an argv list; the new flag is one mechanical addition
- LIB-08 wheel-AST scope expansion: HIGH — extending an existing AST visitor is mechanical
- Move-and-dogfood mechanics (D-04..D-07): HIGH — file moves, deletions, and a one-line pyproject change; mechanical refactor

**Research date:** 2026-05-16
**Valid until:** 2026-06-15 (stable pytest 9.x + pydantic-settings 2.14.x for at least 30 days; pytest collection-hook semantics have not changed in a major version since pytest 7.0)

**Sources:**
- [pytest customize/configuration](https://docs.pytest.org/en/stable/reference/customize.html)
- [pytest argparsing source](https://docs.pytest.org/en/stable/_modules/_pytest/config/argparsing.html)
- [pytest custom directory collector](https://docs.pytest.org/en/stable/example/customdirectory.html)
- [pytest discussion #10246 — synthesizing tests as a plugin](https://github.com/pytest-dev/pytest/discussions/10246)
- [pytest Issue #6464 — multiple -o flags](https://github.com/pytest-dev/pytest/issues/6464)
- [pydantic-settings API](https://docs.pydantic.dev/latest/api/pydantic_settings/)
- [pydantic-settings Issue #259 — runtime YAML path override](https://github.com/pydantic/pydantic-settings/issues/259)
