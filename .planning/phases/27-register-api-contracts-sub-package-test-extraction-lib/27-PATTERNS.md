# Phase 27: pytest-native ini config + contracts test injection + dogfood (LIB) — Pattern Map

**Mapped:** 2026-05-16
**Files analyzed:** 10
**Analogs found:** 10 / 10 (every target has a strong analog in the existing tree — this phase is ~80% relocation per RESEARCH.md)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/_plugin.py` (extend) | pytest plugin (controller) | event-driven (pytest hooks) | self (Phase 26 skeleton already in place) | exact — fill skeleton in place |
| `src/mcp_test_framework/contracts/_tests.py` (NEW) | parametrized test bodies | request-response (async MCP/judge calls) | `tests/contract/test_mcp_tool_contract.py` | exact (verbatim move per D-04) |
| `src/mcp_test_framework/_black_box_guard.py` (NEW) | runtime guard utility | event-driven (one-shot startup check) | `tests/conftest.py:pytest_configure` lines 30-55 | exact (relocation per D-18) |
| `src/mcp_test_framework/contracts/__init__.py` (rewrite docstring) | package marker | n/a | self (existing stub) | exact — docstring-only edit |
| `src/mcp_test_framework/fixtures.py` (`_session_needs_preflight` flip) | predicate | event-driven (called by autouse fixture) | self lines 109-149 (current path-prefix logic) | exact — in-place predicate flip per D-19 |
| `src/mcp_test_framework/cli.py` (kill env-var write in `_load_config`) | CLI controller | request-response (typer command → subprocess) | self lines 201-304 (existing precedence + env-var write at line 300) | exact — surgical removal of one line + replace with subprocess flag |
| `src/mcp_test_framework/_runner.py` (`_build_pytest_args` adds `-o`) | subprocess composer | request-response | self lines 81-135 (existing argv builder; takes resolved Config path as new arg) | exact — extend signature in place |
| `src/mcp_test_framework/config.py` (verify only — no edits expected) | config loader | request-response | self lines 205-251 (`settings_customise_sources` already supports `yaml_file=` kwarg) | exact — RESEARCH confirms `Config(yaml_file=PATH)` works today |
| `tests/contract/test_mcp_tool_contract.py` (DELETE) | test bodies | n/a (deletion) | self | exact — D-05 hard delete |
| `tests/conftest.py` (DELETE `pytest_generate_tests` + black-box guard + `pytest_plugins`) | test config | n/a (deletion) | self | exact — D-05 + D-18 + D-17 |
| `pyproject.toml` `[tool.pytest.ini_options]` (add `mcp_config_file`) | config | n/a | self lines 52-71 | exact — add one line per D-06 |

---

## Pattern Assignments

### `src/mcp_test_framework/_plugin.py` (pytest plugin, event-driven hooks)

**Analog:** self (Phase 26 skeleton). Phase 27 fills hook bodies in place — no new file.

**Imports pattern** (current lines 29-54, EXTEND):
```python
from __future__ import annotations

import warnings

import pytest

# Re-export the renamed prefixed fixtures so pytest auto-discovery surfaces them.
from mcp_test_framework.fixtures import (  # noqa: F401
    _isolated_home,
    _preflight,
    mcp_client,
    mcp_config,
    mcp_judge,
    mcp_rubric_clarity,
    mcp_rubric_disambiguation,
    mcp_rubric_parameters,
    mcp_target_tool,
    tool_config,
)

# Phase 27 ADDS:
import os
from pathlib import Path
from pydantic import ValidationError
from mcp_test_framework.config import Config
from mcp_test_framework._black_box_guard import check_black_box
```

**Existing `pytest_addoption` skeleton** (lines 79-86) — EXTEND with `parser.addini`:
```python
# Current body — keep:
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.getgroup("mcp_test_framework", "MCP test framework options")
    # Phase 27 ADDS:
    parser.addini(
        "mcp_config_file",
        type="string",
        default="",
        help=(
            "Path to MCP test framework YAML config; relative paths are "
            "resolved relative to pyproject.toml's directory. Absent or "
            "empty = library mode opted out."
        ),
    )
```
Why `type="string"` not `type="paths"`: pytest's `paths` returns `list[Path]` (RESEARCH.md Pattern 1).

**Existing `pytest_configure` body** (lines 63-76) — EXTEND in place:
```python
# Current body — keep marker registration:
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "mcp_contract: framework-injected MCP contract test.",
    )

    # Phase 27 ADDS (D-09 deprecation warning):
    if os.environ.get("MCPTF_CONFIG_FILE"):
        warnings.warn(
            "MCPTF_CONFIG_FILE env var is deprecated since v1.4 and will be "
            "removed in v1.5 — use [tool.pytest.ini_options] mcp_config_file = "
            "PATH in pyproject.toml or pass --config PATH to mcp-contracts run instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Phase 27 ADDS (read ini → load Config):
    raw = (config.getini("mcp_config_file") or "").strip()
    if not raw:
        return  # D-13 silent no-op

    path = Path(raw)
    if not path.is_absolute():
        path = config.rootpath / path
    if not path.is_file():
        # D-14 fail-loud
        pytest.exit(
            f"mcp_config_file points at {path!s} which does not exist or is not a file"
            f"\n\nnext: check the path or run `mcp-contracts config-init -o config.yaml`",
            returncode=2,
        )

    try:
        cfg = Config(yaml_file=str(path))
    except ValidationError as exc:
        # D-15 — reuse cli.py's mapper via lazy import to avoid circular
        from mcp_test_framework.cli import _emit_operator_error_for_validation
        _emit_operator_error_for_validation(exc, source=str(path))

    check_black_box()  # D-18 — raises RuntimeError on sys.modules leak
    config._mcp_contracts_config = cfg  # type: ignore[attr-defined]
```

**Deprecation-warning shape** — copy verbatim from Phase 25 pattern at `cli.py:373-386` (`_warn_sdet_flag`):
```python
# Source pattern (cli.py:380-385):
warnings.warn(
    "--sdet is deprecated since v1.4 and will be removed in v1.5 — "
    "use --test-code instead.",
    DeprecationWarning,
    stacklevel=2,
)
```
Phase 27 mirrors this verbatim per CONTEXT.md `<decisions>` "Deprecation copy for MCPTF_CONFIG_FILE".

**New `pytest_collection` hook** — see RESEARCH.md Pattern 4 "Approach A hybrid". Analog: NONE in current codebase (this is the net-new logic). Use `_PytestModule` subclass override. Validate in Wave 0 spike (RESEARCH.md Pitfall 1).

**New `pytest_generate_tests` hook** — analog: `tests/conftest.py:146-158` (CURRENT `pytest_generate_tests`):
```python
# tests/conftest.py:146-158 — current parametrize site:
def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "target_tool" not in metafunc.fixturenames:
        return
    config = Config()
    names = _resolve_tool_names(config)
    metafunc.parametrize("target_tool", names, indirect=True, ids=names)
```
Phase 27 gates on the synthetic-module sentinel + uses `mcp_target_tool` fixture name (RESEARCH.md Example 5):
```python
def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "mcp_target_tool" not in metafunc.fixturenames:
        return
    if not getattr(metafunc.module, "_is_mcp_contracts_synthetic", False):
        return
    names = getattr(metafunc.module, "_mcp_parametrize_tools", [])
    metafunc.parametrize("mcp_target_tool", names, indirect=True, ids=names)
```

**SAFE-01 opt-in filter** — copy semantics verbatim from `tests/conftest.py:_resolve_tool_names` (lines 88-143):
```python
# tests/conftest.py:140-143 — current SAFE-01 filter:
return [
    name for name in _r._DISCOVERED_TOOL_NAMES
    if name in config.tools and not config.tools[name].skip
]
```
Phase 27 uses the same allowlist semantics inside the `pytest_collection` hook against the freshly-loaded `cfg.tools`:
```python
allowed = sorted(name for name, t in cfg.tools.items() if not t.skip)
parametrize_names = [n for n in allowed if n in discovered]
```

**Brief MCP discovery for parametrize** — analog: `tests/conftest.py:_discover_tools` (lines 72-85):
```python
async def _discover_tools(config: Config) -> list[str]:
    async with McpTestClient(
        config.mcp_server.command,
        config.mcp_server.args,
        config.mcp_server.timeout_seconds,
    ) as client:
        tools = await client.list_tools()
    return [t.name for t in tools]
```
Copy verbatim into `_plugin.py` (lift the AsyncExitStack/handshake into a private `_discover_tools_live(cfg)` per RESEARCH.md Example 4).

**Error rendering on discovery failure** — analog: `tests/conftest.py:104-128` (existing failure shape including FileNotFoundError hint) AND `cli.py:_discover_tools_for_run` lines 314-370 (operator-tone variant). Plugin path runs under pytest → use `pytest.exit(msg, returncode=2)` (matches `tests/conftest.py:128`), not `typer.Exit`.

---

### `src/mcp_test_framework/contracts/_tests.py` (NEW — extracted test bodies)

**Analog:** `tests/contract/test_mcp_tool_contract.py` (verbatim move per D-04).

**Imports pattern** (verbatim from analog lines 35-49):
```python
from __future__ import annotations

import json

import pytest
from jsonschema.validators import Draft202012Validator

from mcp_test_framework.judge_protocol import Judge
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.models import ToolConfig
from mcp_test_framework.schema_validator import validate_tool_schema

pytestmark = [pytest.mark.asyncio(loop_scope="session")]
```
Preserves `loop_scope="session"` per RESEARCH.md Pitfall 2 (hybrid approach needs the real file's `pytestmark` intact for pytest-asyncio to wire the loop scope).

**Test-function body pattern** (verbatim from analog lines 57-103 et al.) — all 10 tests TEST-01..TEST-10 move unchanged.

**Critical rename — fixture parameter names** — Phase 26 D-15..D-19 fixture-prefix convention already landed; `_tests.py` uses `mcp_target_tool`, `mcp_judge`, `mcp_client`, `mcp_rubric_clarity`, `mcp_rubric_disambiguation`, `mcp_rubric_parameters` (NOT the unprefixed deprecated aliases). Compare analog lines:

| Analog (today) | `_tests.py` (Phase 27) |
|----------------|------------------------|
| `target_tool` (line 57, 70, 78, 88...) | `mcp_target_tool` |
| `judge: Judge` (line 111, 143, 173) | `mcp_judge: Judge` |
| `mcp_client: McpTestClient` (line 209, 225, 240) | unchanged (already prefixed) |
| `rubric_clarity` (line 113) | `mcp_rubric_clarity` |
| `rubric_disambiguation` (line 145) | `mcp_rubric_disambiguation` |
| `rubric_parameters` (line 175) | `mcp_rubric_parameters` |
| `tool_config: ToolConfig` (every test) | unchanged (`tool_config` is not in the SC5 collision set per fixtures.py:511) |

**`pytest.skip` runtime gating** (analog lines 65-67 et al.) — verbatim preserved:
```python
if tool_config.skip:
    pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
```

**Judge subset gating** (analog lines 124-127) — verbatim preserved:
```python
if tool_config.judges is not None and "clarity" not in tool_config.judges:
    pytest.skip(reason=f"judge 'clarity' not selected for tool {target_tool.name!r}")
```
(Parameter rename: `target_tool.name` → `mcp_target_tool.name` etc.)

**Module-level docstring** — adapt analog lines 1-34 to reflect that the file now lives in the library AND is injected via the plugin (not collected by pytest from filesystem); IDs render as `<mcp-contracts>::test_<name>[<tool>]` per D-08.

---

### `src/mcp_test_framework/_black_box_guard.py` (NEW — relocated runtime guard)

**Analog:** `tests/conftest.py:pytest_configure` lines 30-55 (relocation per D-18, verbatim logic).

**Source pattern** (verbatim from `tests/conftest.py:45-55`):
```python
leaked = [
    name
    for name in sys.modules
    if name == "homelab_mcp" or name.startswith("homelab_mcp.")
]
if leaked:
    raise RuntimeError(
        f"Black-box rule violated: homelab_mcp modules in sys.modules "
        f"at test start: {leaked}. The framework must drive homelab-mcp "
        f"via stdio_client only -- never import."
    )
```

**Target shape — single function**:
```python
"""Runtime sys.modules guard for the homelab-mcp black-box rule.

Relocated from tests/conftest.py per Phase 27 D-18 / LIB-08 so the guard
ships inside the installed wheel and fires for library-mode operators —
not just for the framework's own test suite. Invoked from the plugin's
pytest_configure after Config is loaded.

The guard is GENERIC despite mentioning `homelab_mcp` by name: that
string is the framework's MVP target SUT, and the black-box principle
is what's being enforced (memory: project_framework_primitives_sdet_safety_principle).
"""
from __future__ import annotations

import sys


def check_black_box() -> None:
    """Raise RuntimeError if any homelab_mcp.* module is in sys.modules."""
    leaked = [
        name
        for name in sys.modules
        if name == "homelab_mcp" or name.startswith("homelab_mcp.")
    ]
    if leaked:
        raise RuntimeError(
            f"Black-box rule violated: homelab_mcp modules in sys.modules "
            f"at test start: {leaked}. The framework must drive homelab-mcp "
            f"via stdio_client only -- never import."
        )
```

**Note on framework-primitives principle:** RESEARCH.md Open Question O-6 flags that hardcoding `homelab_mcp` in production code is in tension with SEED-022 (memory `project_framework_primitives_sdet_safety_principle`). Planner should surface this — either accept the MVP-target hardcoding with a docstring caveat, or generalize to an allowlist read from config (e.g., `forbidden_imports: ["homelab_mcp"]`). Current CONTEXT.md D-18 reads as verbatim relocation; the principle question is meta-planning.

---

### `src/mcp_test_framework/contracts/__init__.py` (rewrite docstring)

**Analog:** self (current stub).

**Current docstring** (lines 1-14) — REPLACE entirely:
```python
"""mcp_test_framework.contracts — subpackage stub.

Currently shipped as an empty subpackage so PEP 561-driven type
resolution finds `mcp_test_framework.contracts` from an installed wheel
without "missing stubs" complaints. A future library-mode milestone
fills the register() API + virtual _ContractsModule injection +
contract-test extraction inside this subpackage.

There is intentionally NO `register()` import or implementation here
yet. ...
"""
```

**Target docstring** (Phase 27):
```python
"""mcp_test_framework.contracts — pytest-injected contract test surface.

This subpackage contains the 10 contract-test bodies (TEST-01..TEST-10)
that the framework's pytest plugin synthesizes into operator test
sessions. Operators do NOT import from this module directly — the
library-mode entry point is a single ini line:

    # operator's pyproject.toml
    [tool.pytest.ini_options]
    mcp_config_file = "./config.yaml"

When `mcp_config_file` is set, the plugin (`mcp_test_framework._plugin`)
reads the YAML, runs the black-box guard, parametrizes the test bodies
in `_tests.py` over `config.tools` (Phase 13 SAFE-01 opt-in semantics),
applies the `mcp_contract` marker, and injects them under the synthetic
nodeid `<mcp-contracts>::test_<name>[<tool>]`.

When `mcp_config_file` is unset, this subpackage is inert — no contract
tests are injected. Operators who installed `mcp-contracts` solely for
`gen-test-classes` see no behavioral change.

There is intentionally NO `register()` API. Phase 27 pivoted away from
the register() approach in favor of a pytest-native ini route (CONTEXT.md D-01).
"""
```

NO public exports. NO `register()` import. (Per D-17 zero-ceremony promise.)

---

### `src/mcp_test_framework/fixtures.py` — `_session_needs_preflight` flip

**Analog:** self lines 109-149 (current path-prefix predicate).

**Current pattern** (verbatim from fixtures.py:118-149):
```python
_LIVE_PREFIXES: tuple[str, ...] = (
    "tests/contract/",
    "tests/test_code/",
    "tests/sdet/",  # noqa: sdet-rename-shim
)


def _session_needs_preflight(request: pytest.FixtureRequest) -> bool:
    items = getattr(request.session, "items", []) or []
    if not items:
        return False
    for item in items:
        if item.nodeid.startswith(_LIVE_PREFIXES):
            return True
    return False
```

**Target pattern** (D-19 + RESEARCH.md Example 6 — marker-based detection, with O-5 Pitfall 5 carveout for test-code scenarios):
```python
def _session_needs_preflight(request: pytest.FixtureRequest) -> bool:
    """True iff any collected item is a contract test (marker) OR a test-code scenario.

    Phase 27 D-19: contract-test detection flips from path-prefix to marker
    (`mcp_contract` is auto-applied by the plugin's pytest_collection).
    test-code-author scenarios (tests/test_code/, legacy tests/sdet/) do NOT
    carry the contract marker — they retain path-prefix detection per
    Pitfall 5 in 27-RESEARCH.md.
    """
    items = getattr(request.session, "items", []) or []
    if not items:
        return False
    for item in items:
        # Contract path (D-19 marker-based)
        if any(item.iter_markers("mcp_contract")):
            return True
        # Test-code-author path (kept on nodeid prefix — O-5 carveout)
        if item.nodeid.startswith(("tests/test_code/", "tests/sdet/")):  # noqa: sdet-rename-shim
            return True
    return False
```

Drop the `_LIVE_PREFIXES` tuple (or trim it to the test-code carveout). Path-prefix `tests/contract/` is REMOVED — the marker covers it now.

---

### `src/mcp_test_framework/cli.py` — kill `MCPTF_CONFIG_FILE` env-var write

**Analog:** self lines 201-304 (`_load_config`), specifically line 300 (`os.environ["MCPTF_CONFIG_FILE"] = str(resolved)`).

**Current pattern** (cli.py:292-304):
```python
# Load with the resolved path as an explicit kwarg.
# Also export MCPTF_CONFIG_FILE so the in-process pytest session
# spawned by `run()` -- which constructs a bare `Config()` inside
# fixtures, conftest, and the reporter -- picks up the same resolved
# YAML path via the env-var fallback in
# `Config.settings_customise_sources`. The env var is a PATH POINTER,
# not a scalar-value source -- the source-precedence contract in
# docs/ERROR-STYLE.md is preserved.
os.environ["MCPTF_CONFIG_FILE"] = str(resolved)
try:
    return Config(yaml_file=str(resolved))
except ValidationError as exc:
    _emit_operator_error_for_validation(exc, source=source_label)
```

**Target pattern (D-11 + D-12):** Delete the `os.environ[...] = str(resolved)` line entirely (line 300). The resolved path will be passed to the subprocess pytest via `-o "mcp_config_file=PATH"` instead. Update the docstring/comments to reflect the new mechanism.

Also: the env-var-read branch (`_load_config` lines 248-265) is **kept** for one milestone but its handler emits the same DeprecationWarning as the plugin (D-09). Per RESEARCH.md Claude's Discretion: `gen-test-classes` CLI rewire of input-config is **punted to Phase 28** — `_load_config` still reads `MCPTF_CONFIG_FILE` as a precedence input for back-compat in v1.4; the deprecation warning fires whenever it's used.

**Add subprocess argv composition** — `run()` now passes the resolved path to `_runner.run_pytest_subprocess` so it can be injected as `-o "mcp_config_file=PATH"`:
```python
# Phase 27 — pass resolved path through to subprocess composer
rc, tmp_xml, captured_stdout, captured_stderr = _runner.run_pytest_subprocess(
    junit_xml=junit_xml,
    pytest_args=pytest_args,
    raw=False,
    with_framework=with_framework,
    sdet=test_code,  # noqa: sdet-rename-shim
    mcp_config_path=resolved,  # NEW — Phase 27 D-11
)
```

---

### `src/mcp_test_framework/_runner.py` — `_build_pytest_args` adds `-o` flag

**Analog:** self lines 81-135 (`_build_pytest_args`).

**Current pattern** (_runner.py:114-135):
```python
def _build_pytest_args(
    junit_xml: Path | None,
    pytest_args: list[str] | None,
    *,
    with_framework: bool = False,
    sdet: bool = False,  # noqa: sdet-rename-shim
) -> list[str]:
    forwarded = list(pytest_args or [])
    if sdet:
        args: list[str] = ["tests/test_code"]
        # ...
    else:
        args = ["tests/contract"]
    if with_framework:
        args.append("tests/framework")
    if junit_xml is not None:
        args.append(f"--junitxml={junit_xml}")
    args.extend(forwarded)
    return args
```

**Target pattern** — add new `mcp_config_path: Path | None = None` kwarg and inject `-o "mcp_config_file=PATH"`:
```python
def _build_pytest_args(
    junit_xml: Path | None,
    pytest_args: list[str] | None,
    *,
    with_framework: bool = False,
    sdet: bool = False,  # noqa: sdet-rename-shim
    mcp_config_path: Path | None = None,  # NEW — Phase 27 D-11
) -> list[str]:
    # ... existing logic ...
    args.extend(forwarded)
    if mcp_config_path is not None:
        # Use two separate argv elements — no embedded quotes (Windows quoting
        # pitfall per 27-RESEARCH Pitfall 4)
        args.extend(["-o", f"mcp_config_file={mcp_config_path}"])
    return args
```

**Subprocess argv pattern** — analog `_runner.py:206-213` (raw mode) and lines 237-262 (default mode). The existing pattern already uses list-of-strings argv with `subprocess.run` (no shell), so the `-o` flag composes naturally:
```python
# _runner.py:206 (current)
argv = [sys.executable, "-m", "pytest", *inner_args]
# Phase 27: inner_args now includes ["-o", "mcp_config_file=..."]
```

`run_pytest_subprocess` needs the new `mcp_config_path` kwarg threaded through to both branches (raw + default) at lines 162-279.

---

### `src/mcp_test_framework/config.py` — verify only (no edits)

**Analog:** self lines 205-251 (`settings_customise_sources`).

**Existing pattern (already supports the kwarg path)** — lines 220-249:
```python
# Locked pop pattern (probe-verified).
yaml_file = init_settings.init_kwargs.pop("yaml_file", None)
# IPC fallback: when no explicit ``yaml_file`` kwarg is given, fall
# back to ``MCPTF_CONFIG_FILE`` ...
if yaml_file is None:
    yaml_file = os.environ.get("MCPTF_CONFIG_FILE")
sources: list[PydanticBaseSettingsSource] = [init_settings]
if yaml_file and Path(yaml_file).is_file():
    _check_legacy_sdet_key_in_yaml(yaml_file)
    sources.append(
        YamlConfigSettingsSource(settings_cls, yaml_file=str(yaml_file))
    )
sources.append(file_secret_settings)
return tuple(sources)
```

**Planner verification only:** Confirm that `Config(yaml_file=resolved_path)` works as the sole input path (no env-var write needed). RESEARCH.md D-12 confirms `[VERIFIED: config.py:228]`. No code change required for v1.4; v1.5 cleanup will remove the env-var fallback at line 234-235.

---

### `tests/contract/test_mcp_tool_contract.py` (DELETE per D-05)

**Analog:** self. Verbatim deletion. Content moves to `src/mcp_test_framework/contracts/_tests.py` (see above).

---

### `tests/conftest.py` (REWRITE — delete `pytest_plugins`, `pytest_configure`, `pytest_generate_tests`)

**Analog:** self (159 lines today).

**Sections to DELETE:**

1. **`pytest_plugins`** (line 18) — Phase 26 entry-point auto-load makes this redundant; D-17 zero-ceremony promise.
2. **`pytest_configure` black-box guard** (lines 30-55) — relocated to `_black_box_guard.py` per D-18.
3. **`pytest_generate_tests`** (lines 146-158) — plugin's `pytest_generate_tests` is now sole parametrization site per D-05.
4. **`_resolve_tool_names`** (lines 88-143) and **`_discover_tools`** (lines 72-85) — logic relocates into plugin's `pytest_collection` site.

**Result:** `tests/conftest.py` becomes empty (or a docstring-only no-op). RESEARCH.md confirms pytest tolerates an absent `tests/conftest.py`. Per D-17, the framework's own `tests/conftest.py` is the canonical "zero ceremony" demonstration.

---

### `pyproject.toml` `[tool.pytest.ini_options]` (add `mcp_config_file`)

**Analog:** self lines 52-71.

**Current pattern:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "session"
testpaths = ["tests"]
markers = [
  "live_homelab: requires homelab-mcp runnable via uvx (or on PATH)",
  "live_ollama: requires reachable Ollama at OLLAMA_BASE_URL with the configured model",
]
addopts = "-m 'not live_homelab and not live_ollama'"
filterwarnings = [
    "always::DeprecationWarning:mcp_test_framework",
]
```

**Target — ADD one line** (D-06):
```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "session"
testpaths = ["tests"]
# Phase 27 D-06: framework dogfoods library mode — contract tests are
# injected via the plugin reading this ini value, not via tests/contract/.
mcp_config_file = "./config.test.yaml"
markers = [
  "live_homelab: requires homelab-mcp runnable via uvx (or on PATH)",
  "live_ollama: requires reachable Ollama at OLLAMA_BASE_URL with the configured model",
]
addopts = "-m 'not live_homelab and not live_ollama'"
filterwarnings = [
    "always::DeprecationWarning:mcp_test_framework",
]
```

**Planner must verify the existing config-file name** per RESEARCH.md Open Question O-1. Current repo working-tree has `config.test.yaml` and `config.scratch.yaml` (per git status) — confirm which is the canonical framework-CI config.

---

## Shared Patterns

### Deprecation warning emission

**Source:** `src/mcp_test_framework/cli.py:373-386` (`_warn_sdet_flag`) — Phase 25 D-05 pattern.

**Apply to:** Plugin `pytest_configure` for `MCPTF_CONFIG_FILE` per D-09.

```python
warnings.warn(
    "<SUBJECT> is deprecated since v1.4 and will be removed in v1.5 — "
    "use <REPLACEMENT> instead.",
    DeprecationWarning,
    stacklevel=2,
)
```

**Filter caught by** `pyproject.toml:69-71`:
```toml
filterwarnings = [
    "always::DeprecationWarning:mcp_test_framework",
]
```
Default Python warning filter dedups once-per-process per memory `project_deprecation_warning_visibility`.

### Operator-tone error rendering

**Source:** `src/mcp_test_framework/_runner.py:_emit_operator_error` (re-exported at `cli.py:92`) and `src/mcp_test_framework/fixtures.py:_pytest_exit_operator_tone` (lines 57-81).

**Shape** (docs/ERROR-STYLE.md):
```
<summary>
<blank>
<detail line 1>
...
<blank>
next: <action verb> <command>
```

**Apply to:** Plugin `pytest_configure` for D-14 (path missing) and D-15 (YAML invalid). Use `pytest.exit(msg, returncode=2)` not `typer.Exit` because the plugin runs under pytest, not under typer. The fixtures.py:`_pytest_exit_operator_tone` helper (lines 57-81) is the closest analog — duplicated in the plugin, or imported via lazy import to avoid a fixtures.py ↔ _plugin.py cycle.

**ValidationError mapper:** `cli.py:_emit_operator_error_for_validation` (lines 95-198) handles the v1→v2, missing-field, and generic branches. Plugin imports lazily inside `except ValidationError:` block:
```python
from mcp_test_framework.cli import _emit_operator_error_for_validation
_emit_operator_error_for_validation(exc, source=str(path))
```

### `returncode=2` convention

**Source:** `fixtures.py:_pytest_exit_operator_tone` (line 63) — `returncode=2` distinguishes setup error from pass(0)/fail(1).

**Apply to:** Every Phase 27 fail-loud site (D-14, D-15) — preserves the exit-code convention `_runner._map_exit_code` (lines 143-154) already understands.

### SAFE-01 opt-in allowlist semantics

**Source:** `tests/conftest.py:_resolve_tool_names` lines 88-143 — Phase 13 SAFE-01 invariant: unselected tools are excluded at parametrize time, never via runtime `pytest.skip()` (memory `project_v1_1_skip_bug`).

**Apply to:** Plugin's `pytest_collection` hook when filtering `cfg.tools` for parametrization. Identical filter expression:
```python
allowed = [name for name in discovered if name in cfg.tools and not cfg.tools[name].skip]
```

### Brief MCP handshake (tool discovery)

**Source:** `tests/conftest.py:_discover_tools` lines 72-85 — uses `McpTestClient.__aenter__` (Phase 06 D-16 isolation contract).

**Apply to:** Plugin's `pytest_collection` for parametrize discovery. Relocate verbatim:
```python
async def _discover_tools_live(cfg: Config) -> list[str]:
    async with McpTestClient(
        cfg.mcp_server.command,
        cfg.mcp_server.args,
        cfg.mcp_server.timeout_seconds,
    ) as client:
        tools = await client.list_tools()
    return [t.name for t in tools]
```

Wrap with `asyncio.run` or `asyncio.Runner` (mirroring `cli.py:_discover_tools_for_run` lines 340-342 if running outside any event loop) — pytest's `pytest_collection` hook runs synchronously, so `asyncio.run(_discover_tools_live(cfg))` is the right idiom.

### Wheel-introspection AST guard (PACK-04 extension)

**Source:** `tests/framework/test_wheel_shape.py:test_wheel_source_has_no_homelab_mcp_imports` lines 142-166 — Phase 26 PACK-04, line-prefix string scan.

**Apply to:** D-18 extension — the existing test already scans EVERY `.py` source file in the wheel for `import homelab_mcp` / `from homelab_mcp` line prefixes. Phase 27 D-18 says "Wheel-introspection AST-walk extends to fail on banned SUT imports anywhere inside src/" — confirm the existing pattern already covers `_black_box_guard.py` (it does, because the test iterates all `.py` files in the wheel). NO new test code required; just regression-verify after the relocation.

**Optional enhancement** (RESEARCH.md Pitfall 6): swap the line-prefix check for a proper `ast` walk (`ast.parse(text)` → visit `ast.Import` / `ast.ImportFrom` nodes) — more robust against comment/docstring false positives. Planner's call whether to upgrade in Phase 27 or defer.

---

## No Analog Found

None. Every Phase 27 target has a strong codebase analog. The only **net-new logic** without direct precedent is the **`_ContractsModule` subclass with synthetic nodeid** and the **`pytest_collection` injection site** (RESEARCH.md Pattern 3 / Pattern 4 Approach A) — these come from upstream pytest internals + pytest-dev/pytest discussion #10246, not the codebase. RESEARCH.md flags Wave 0 spike as the validation point.

---

## Metadata

**Analog search scope:** `src/mcp_test_framework/**/*.py`, `tests/**/*.py`, `pyproject.toml`, CONTEXT.md, RESEARCH.md.

**Key reusable assets confirmed:**
- Phase 26 `_plugin.py` skeleton at `src/mcp_test_framework/_plugin.py` (fill bodies in place)
- Phase 25 deprecation pattern at `cli.py:373-386` (`_warn_sdet_flag`)
- Phase 13 SAFE-01 opt-in filter at `tests/conftest.py:140-143`
- Phase 06 isolation-aware discovery at `tests/conftest.py:72-85` + `cli.py:328-342`
- Operator-tone error helpers at `_runner.py:_emit_operator_error`, `cli.py:_emit_operator_error_for_validation`, `fixtures.py:_pytest_exit_operator_tone`
- `Config(yaml_file=PATH)` kwarg path already supported at `config.py:228`
- Wheel-introspection AST-walk at `tests/framework/test_wheel_shape.py:142-166` (already covers `src/` per-file scan)

**Pattern extraction date:** 2026-05-16
