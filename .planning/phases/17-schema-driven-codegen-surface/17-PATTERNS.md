# Phase 17: Schema-driven codegen surface — Pattern Map

**Mapped:** 2026-05-12
**Files analyzed:** 12 (8 new src + tests, 3 modified, 1 config)
**Analogs found:** 12 / 12 (all new files have at least a role-match analog in this codebase)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/sdet/__init__.py` (new) | package init / public-surface curator | static re-export | `src/mcp_test_framework/__init__.py` | role-match (current `__init__.py` is empty modulo `__version__`; pattern lifted from cli.py re-export idiom at line 78) |
| `src/mcp_test_framework/sdet/response.py` (new) | model (Pydantic v2 BaseModel with @computed_field) | transform / lazy parse | `src/mcp_test_framework/ollama_judge.py:98-118` (`JudgeResult`) | role-match (closest Pydantic model with `model_config = ConfigDict(...)` + bounded scalar fields; no `@computed_field` analog exists yet in repo) |
| `src/mcp_test_framework/sdet/_codegen.py` (new) | utility / code generator | transform (dict → str) | `src/mcp_test_framework/schema_validator.py:74-205` (`validate_tool_schema`) + `src/mcp_test_framework/cli.py:901-950` (`_format_param_signature`) | role-match (pure-data walker over `Tool.inputSchema`; scalar-type map lifted verbatim from `_format_param_signature`) |
| `src/mcp_test_framework/sdet/_tool_factory.py` (new) | utility / registry lookup | request-response (name → class) | `src/mcp_test_framework/rubrics.py` (registry pattern w/ `RUBRIC_IDS`, `resolve_rubric_id`) | role-match (string-keyed registry with loud-fail on miss; closest pattern in repo) |
| `src/mcp_test_framework/sdet/generated/.gitkeep` (new) | placeholder | n/a | — | none needed (zero-byte placeholder) |
| `src/mcp_test_framework/sdet/generated/<slug>/__init__.py` (generated) | re-export + registry table | static re-export | `src/mcp_test_framework/cli.py:78` (re-export idiom) | partial (no in-tree precedent for generated files; format is unique) |
| `src/mcp_test_framework/sdet/generated/<slug>/<tool_name>.py` (generated, one per tool) | model (generated Pydantic Params + Response) | static data class | `src/mcp_test_framework/models.py:36-73` (`OllamaConfig`, `McpServerConfig`) | role-match (the existing-est nested-BaseModel-with-Field-defaults pattern in repo) |
| `src/mcp_test_framework/cli.py` (modified — add `gen-sdet-classes` command) | controller / Typer command | request-response | `src/mcp_test_framework/cli.py:705-868` (`config-init` command), `cli.py:283-340` (`_discover_tools_for_run`) | exact (same registration site, same `_load_config` helper, same `McpTestClient` + `asyncio.Runner` plumbing) |
| `pyproject.toml` (modified — add `pyright>=1.1.409` + `[tool.pyright]` block) | config | static | `pyproject.toml:27-38` (existing `[dependency-groups].dev`) | exact (add a line + a TOML table; pattern already on disk) |
| `tests/framework/unit/test_codegen_walker.py` (new) | test | pure-sync unit | `tests/framework/unit/test_schema_validator.py` | exact (per-rule unit tests over a pure walker that returns structured data) |
| `tests/framework/unit/test_codegen_emitter.py` (new) | test | unit (file I/O) | `tests/framework/unit/test_config_init.py` (uses `tmp_path`, parses scaffold text) | exact (assertions on emitted text + file layout under `tmp_path`) |
| `tests/framework/unit/test_codegen_typecheck.py` (new) | test (subprocess) | unit (subprocess assertion) | `tests/framework/test_runner_subprocess.py` (already drives a subprocess + asserts exit code; see Glob result) | role-match (subprocess invocation w/ exit-code assertion under `tmp_path`) |
| `tests/framework/unit/test_tool_response.py` (new) | test (pure data) | unit | `tests/framework/unit/test_ollama_judge.py` (pure-sync tests on Pydantic model + module-level helpers) | exact (Pydantic-model-construction + property-output assertions, no event loop) |
| `tests/framework/unit/test_gen_sdet_classes_cli.py` (new) | test (Typer `CliRunner`) | unit | `tests/framework/test_config_init_cli.py` | exact (same CliRunner shape, `_invoke("...", "--help")` helper, refuse-to-overwrite parallel) |

**Notes on file scope:**
- The phase does NOT modify `src/mcp_test_framework/mcp_client.py`. The research flagged an Open Question about a `server_info` accessor; CONTEXT.md does not lock that change. Plan should either (a) read `initialize()`'s return via a fresh `ClientSession` call inside `gen-sdet-classes` (mirroring the locked-down `mcp_client.py:170-171` `await session.initialize()` line — but that result is currently discarded), or (b) add a thin `McpTestClient.server_info` accessor. CONTEXT.md treats `mcp_client.py:106-210` as "LOCKED — do not modify" (line 121); planner should adopt option (a) and reach `serverInfo` via a parallel local `ClientSession` open inside `gen-sdet-classes`, OR explicitly justify adding the accessor as a minimal additive change.

---

## Pattern Assignments

### `src/mcp_test_framework/sdet/__init__.py` (package init, static re-export)

**Analog:** `src/mcp_test_framework/__init__.py` (3 lines today) + the in-module re-export idiom at `cli.py:78`.

**Module docstring + version pattern** (from `__init__.py` lines 1-3):
```python
"""mcp_test_framework -- pytest framework for testing MCP servers end-to-end."""

__version__ = "0.1.0"
```

**Re-export idiom** (from `cli.py:74-78`):
```python
# Re-exported from _runner.py (Phase 14 D-01); cli.py keeps the public symbol
# so existing test imports `from mcp_test_framework.cli import _emit_operator_error`
# continue working after the helper moved out of this module to avoid the
# cli.py <-> _runner.py circular-import that Phase 14 would otherwise create.
from mcp_test_framework._runner import _emit_operator_error  # noqa: E402
```

**Apply to `sdet/__init__.py`:** Top-of-file `from __future__ import annotations` + module docstring + re-export `ToolResponse` (from `response.py`) and `tool` (from `_tool_factory.py`). The `tool` factory's per-server registry is populated lazily on first import of `generated/<slug>/__init__.py`, mirroring how `_emit_operator_error` is re-exported without import-time side effects.

---

### `src/mcp_test_framework/sdet/response.py` (Pydantic BaseModel with @computed_field)

**Analog:** `src/mcp_test_framework/ollama_judge.py:98-118` (`JudgeResult`). Closest existing Pydantic v2 BaseModel in the repo using `model_config = ConfigDict(...)` + bounded scalar fields. NO `@computed_field` precedent exists in this codebase — Phase 17 introduces it.

**Imports pattern** (from `ollama_judge.py:61-69`):
```python
from __future__ import annotations

import json
import logging
import re
from contextlib import AsyncExitStack

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
```

**Pydantic model + frozen ConfigDict pattern** (from `ollama_judge.py:98-118`):
```python
class JudgeResult(BaseModel):
    """Validated structured result of a single judge call.

    Domain-local Pydantic model (D-04 \ Established Patterns: result types
    live in their owning module). Frozen so callers cannot accidentally
    mutate a result mid-test. ``score`` is bounded to the 1..5 inclusive
    rubric range -- out-of-range values raise ``ValidationError`` and are
    caught by the parser fallback (D-09 step 4).
    """

    model_config = ConfigDict(frozen=True)

    passed: bool
    score: int = Field(..., ge=1, le=5)
    reasoning: str
    raw_response: str = ""
```

**Apply to `ToolResponse`:**
- `from __future__ import annotations` + the standard Pydantic imports (drop `httpx` / `logging` / `re` — pure-data module).
- `from mcp.types import CallToolResult` (used in `mcp_client.py:44`).
- `model_config = ConfigDict(arbitrary_types_allowed=True)` per D-07 (NOT `frozen=True`; downstream subclasses may want mutable typed fields).
- `@computed_field` + `@property` on `is_error`, `data`, `text` per D-07. Lazy evaluation (not eager in `__init__`).
- Module docstring follows the format used in `mcp_client.py:1-30` and `ollama_judge.py:1-60` (multiline triple-quoted, references CODEGEN-01..06, names CONTEXT.md decisions).

**Imports for `CallToolResult` (from `mcp_client.py:44`):**
```python
from mcp.types import CallToolResult, Tool
```

---

### `src/mcp_test_framework/sdet/_codegen.py` (walker + emitter, pure-data transform)

**Analog (primary):** `src/mcp_test_framework/schema_validator.py:74-205` (`validate_tool_schema`). Pure-data, no I/O, walks `Tool.inputSchema`, returns structured output. Phase 17's walker is the same shape but emits source strings instead of `ValidationIssue` records.

**Analog (scalar-type map):** `src/mcp_test_framework/cli.py:901-950` (`_format_param_signature`). The `type_map` dict (`cli.py:918-925`) is the existing JSON-Schema-scalar → Python-type mapper; lift it verbatim and extend.

**Imports pattern** (from `schema_validator.py:30-37`):
```python
from __future__ import annotations

from typing import Any, Literal

from jsonschema.validators import Draft202012Validator, validator_for
from mcp.types import Tool
from pydantic import BaseModel
```

**Pure-data walker shape** (from `schema_validator.py:74-205`):
- Single top-level function that accepts an `mcp.types.Tool` and returns structured output (list of `ValidationIssue` there; emitted source `str` here).
- Module docstring enumerates the rules being applied (`schema_validator.py:1-29` enumerates the 7 structural checks — Phase 17's walker docstring should enumerate the D-02 coverage rules).
- Short-circuit on early failure (`schema_validator.py:108-117` — when `inputSchema` isn't a dict, return immediately).
- Schema-validity pre-flight via `validator_for(schema, default=Draft202012Validator).check_schema(schema)` (lines 119-136). Phase 17 reuses this exact call to refuse to translate an invalid schema.

**Scalar-type map to lift** (from `cli.py:918-930`):
```python
type_map = {
    "string": "str",
    "integer": "int",
    "boolean": "bool",
    "number": "float",
    "array": "list",
    "object": "dict",
}

def _pytype(jtype: object) -> str:
    if isinstance(jtype, str):
        return type_map.get(jtype, "Any")
    return "Any"
```

**Required-vs-optional ordering** (from `cli.py:932-950`):
```python
req_parts: list[str] = []
for name in required:
    if name in props:
        req_parts.append(f"{name}: {_pytype(props[name].get('type'))}")

kw_parts: list[str] = []
for name in sorted(p for p in props if p not in required):
    prop = props[name] or {}
    ptype = _pytype(prop.get("type"))
    if "default" in prop:
        kw_parts.append(f"{name}: {ptype} = {prop['default']!r}")
    else:
        kw_parts.append(f"{name}: {ptype} = ...")
```

This same required/optional split + alphabetical kwarg ordering applies to Pydantic field emission (required → `Field(...)`; optional → `Field(default=...)`).

**Apply to `_codegen.py`:**
- Module docstring enumerating D-01..D-03 coverage rules + degradation behavior (mirrors `schema_validator.py:1-29` format).
- Pure-data API: `translate_tool(tool: Tool) -> str` (emits source for one tool's file), `slugify(name: str) -> str`, `pascal_case(name: str) -> str`, `_emit_field(name, schema, *, required) -> FieldSpec` (per RESEARCH §Pattern 1).
- File emission via `pathlib.Path.write_text(..., encoding="utf-8")` — mirrors `cli.py:832, 868` (the `config-init` emitter).
- Wipe-and-write via `shutil.rmtree(path, ignore_errors=True)` per D-03; `shutil` already imported in `cli.py:38`.
- Schema-validity pre-flight via `Draft202012Validator` / `validator_for` per CONTEXT.md "Reusable Assets".

---

### `src/mcp_test_framework/sdet/_tool_factory.py` (registry lookup)

**Analog:** `src/mcp_test_framework/rubrics.py` (registry with `RUBRIC_IDS` + `resolve_rubric_id`). The Phase 17 factory is structurally similar — a string-keyed lookup with a loud-fail on miss.

**Loud-fail-on-miss pattern** (from `models.py:102-118`, which calls `resolve_rubric_id`):
```python
@field_validator("judges", mode="after")
@classmethod
def _validate_judge_ids(cls, v: Optional[list[str]]) -> Optional[list[str]]:
    if v is None:
        return v
    for rubric_id in v:
        if rubric_id not in RUBRIC_IDS:
            # Delegate to resolve_rubric_id for the canonical error message
            # (single source per CD-03).
            resolve_rubric_id(rubric_id)
    return v
```

**Domain-local error pattern** (from `mcp_client.py:51-65`):
```python
class ToolNotFoundError(LookupError):
    """Raised by McpTestClient.get_tool when the named tool is not registered.

    Carries the candidate tool list so Phase 4's target_tool fixture (FIX-03)
    can fail the run early with a useful diagnostic. Parallels ValidationIssue
    in schema_validator.py: domain-specific type living in its owning module
    rather than a cross-cutting models.py.
    """

    def __init__(self, tool_name: str, available: list[str]) -> None:
        self.tool_name = tool_name
        self.available = available
        super().__init__(
            f"Tool {tool_name!r} not found. Available tools: {available!r}"
        )
```

**Apply to `_tool_factory.py`:**
- `from __future__ import annotations` + minimal imports.
- Module-level `_REGISTRY: dict[str, type[ToolResponse]]` populated by the generated `generated/<slug>/__init__.py` at import time.
- `tool(name: str)` factory function that does a registry lookup, returns a typed call-wrapper. On miss, raise a `LookupError` subclass carrying the candidate names (mirroring `ToolNotFoundError`).
- The actual `.call(...)` runtime is Phase 18 — Phase 17 only ships the dispatch shape per CONTEXT.md "Architectural Responsibility Map" row 5.

---

### `src/mcp_test_framework/sdet/generated/<slug>/<tool_name>.py` (generated Pydantic model file)

**Analog:** `src/mcp_test_framework/models.py:36-73` (`OllamaConfig`, `McpServerConfig`). Closest in-repo example of a Pydantic v2 model with required + optional fields, default factories, and per-class `model_config`.

**Pydantic model shape to emit** (from `models.py:36-53`):
```python
class OllamaConfig(BaseModel):
    """Ollama judge configuration."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    base_url: str = Field(
        default="http://127.0.0.1:11434",
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "base_url"),
    )
    model: str = Field(
        default="qwen3.6:latest",
        validation_alias=AliasChoices("OLLAMA_MODEL", "model"),
    )
    timeout_seconds: int = Field(
        default=120,
        ge=1,
        validation_alias=AliasChoices("OLLAMA_TIMEOUT_SECONDS", "timeout_seconds"),
    )
```

**`extra="forbid"` precedent on input shapes** (from `models.py:93`):
```python
class ToolConfig(BaseModel):
    """...
    `extra="forbid"` makes typos (e.g. `srtip:` instead of `skip:`) fail at load time
    per TOOLCFG-05 / D-15.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")
```

**Apply to generated files:**
- Header marker per CONTEXT.md §Specifics (4 lines: AUTOGENERATED / Source / Regenerated / Extend by subclassing).
- `from __future__ import annotations` (matches repo-wide convention per CONTEXT.md §Established Patterns).
- `import typing` for `typing.Any` degradation fallback.
- `from pydantic import BaseModel, ConfigDict, Field`.
- `from mcp_test_framework.sdet.response import ToolResponse` (for the Response class subclass).
- Per CONTEXT.md Claude's Discretion (last bullet) + D-02: emit `model_config = ConfigDict(extra="forbid")` on `<Tool>Params` classes (typo-catch on operator), NOT on `<Tool>Response` (server output is not under operator control).
- For required fields use `field: Type = Field(...)` (Ellipsis); for optional with default use `field: Type = Field(default=...)` — exactly the convention in `models.py:42-73`.

---

### `src/mcp_test_framework/sdet/generated/<slug>/__init__.py` (generated re-export + registry)

**Analog:** Same header-marker pattern as the per-tool files. Re-export idiom from `cli.py:78`.

**Apply:**
- Same 4-line header marker.
- One line per tool: `from .<tool_module> import <Tool>Params, <Tool>Response`.
- Module-level `_REGISTRY: dict[str, type[ToolResponse]] = {"create_vm": CreateVmResponse, ...}` — consumed by `sdet/_tool_factory.py:tool(name)`.
- Sorted alphabetically by tool name so re-runs are diff-stable.

---

### `src/mcp_test_framework/cli.py` — add `gen-sdet-classes` command (modified)

**Analog (exact):** `cli.py:705-868` (`config-init`) + `cli.py:283-340` (`_discover_tools_for_run`) + `cli.py:881-898` (`_list_tools_async`).

**Typer command registration pattern** (from `cli.py:705-712`):
```python
@app.command("config-init")
def config_init(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Path to a YAML config (overrides MCPTF_CONFIG_FILE and ./config.yaml autodiscovery).",
    ),
    ...
) -> None:
    """Emit a starter YAML config scaffold for the connected MCP server.
    ...
    """
```

**`--config` precedence (Phase 13) helper invocation pattern** (from `cli.py:477` for `run` and `cli.py:659` for `list-tools`):
```python
cfg = _load_config(config)  # raises typer.Exit(2) on any unrecoverable error.
```

For `gen-sdet-classes`, per CONTEXT.md D-08, use the strict (non-bootstrap) form: `cfg = _load_config(config)` (NOT `allow_missing=True`). `gen-sdet-classes` requires a real config; an unconfigured directory should hit SAFE-03 fail-loud, matching `run`'s contract.

**Async lifecycle pattern** (from `cli.py:881-898` `_list_tools_async`):
```python
async def _list_tools_async(cfg: Config) -> list[Tool]:
    async with AsyncExitStack() as stack:
        client = await stack.enter_async_context(
            McpTestClient(
                cfg.mcp_server.command,
                cfg.mcp_server.args,
                cfg.mcp_server.timeout_seconds,
            )
        )
        return await client.list_tools()
```

**Runner invocation** (from `cli.py:799-801`):
```python
try:
    with asyncio.Runner() as runner:
        tools = runner.run(_list_tools_async(cfg))
except KeyboardInterrupt:
    raise typer.Exit(code=130)
```

**Operator-tone error pattern** (from `cli.py:672-690` — `list-tools` MCP-spawn failure):
```python
except FileNotFoundError as exc:
    if str(exc).startswith("MCP server command not on PATH:"):
        _emit_operator_error(
            summary=f"MCP server command not found: {cfg.mcp_server.command!r}",
            detail=[
                f"the framework tried to launch the server with "
                f"`{cfg.mcp_server.command} {' '.join(cfg.mcp_server.args)}`",
                "and the command is not on PATH.",
            ],
            next_step=(
                "update `mcp_server.command` / `mcp_server.args` in your "
                "config.yaml so the launch command resolves on PATH"
            ),
        )
    _emit_operator_error(
        summary="MCP server failed to start",
        detail=[f"the launch attempt raised: {exc.__class__.__name__}: {exc}"],
        next_step="verify the launch command runs cleanly in your shell",
    )
```

**Apply to `gen-sdet-classes`:**
- Decorate with `@app.command("gen-sdet-classes")` (kebab-case explicit, matching `"list-tools"` / `"config-init"`).
- Single `--config` Path option mirroring `config-init`'s signature lines 707-711. No `--output-dir`, no `--force` per D-08.
- Body: `cfg = _load_config(config)` → `asyncio.Runner` → open `McpTestClient` via `AsyncExitStack` → call both `client._session.initialize()` for `serverInfo` (or expose via a tiny accessor — see planner-discretion note above) and `client.list_tools()` → call into `_codegen.translate_and_emit(tools, server_info, target_root)`.
- KeyboardInterrupt → `typer.Exit(130)` (parity with `cli.py:670, 801`).
- `FileNotFoundError` operator-tone branch identical to `cli.py:672-690`.
- Empty `serverInfo.name` operator-error path per D-05 / CONTEXT.md Claude's Discretion ("error with a clear message naming the served command"). Use `_emit_operator_error` shape.
- Empty `serverInfo.name` operator-error path per D-05 / CONTEXT.md Claude's Discretion.
- One-line-per-tool digest output post-emit, per CONTEXT.md §"What `gen-sdet-classes` prints" Claude-Discretion bullet. Re-use the visual aesthetic of `_runner._render_pre_run_digest` (`_runner.py:732-802`) — `print(f"  {name}: ...")` per tool, sorted alphabetically, bounded height.

**Stdout reconfigure pattern** (from `cli.py:462-472`) — `gen-sdet-classes` should likely NOT need this (no Unicode glyphs in output), but if any em-dash or check appears in the digest, copy that exact `hasattr(...).reconfigure(...)` block verbatim.

---

### `pyproject.toml` — modified

**Analog:** `pyproject.toml:27-38` (existing `[dependency-groups].dev`).

**Existing pattern:**
```toml
[dependency-groups]
dev = [
    "pytest>=9.0",
    "pytest-asyncio>=1.3",
    "pytest-timeout>=2.4",
    "ruff>=0.8",
]
```

**Apply:**
- Add `"pyright>=1.1.409"` to the `dev` list per CONTEXT.md D-04.
- Add a new `[tool.pyright]` block scoped to `src/mcp_test_framework/sdet/generated/` (the exact content is in RESEARCH §"Installation" — already drafted).

---

### Test files — patterns by file

#### `tests/framework/unit/test_codegen_walker.py` (new)

**Analog (exact):** `tests/framework/unit/test_schema_validator.py`.

**Pattern (from `test_schema_validator.py:19-43`):**
```python
"""Unit tests for mcp_test_framework.schema_validator.
... per-check unit tests over a pure walker that returns structured data.
"""
from __future__ import annotations

from mcp.types import Tool

from mcp_test_framework.schema_validator import (
    ValidationIssue,
    validate_tool_schema,
)


def _clean_tool() -> Tool:
    return Tool(
        name="my_tool",
        description="A clean tool with a non-empty description.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )
```

**Apply:** One test per coverage rule from D-02 (string/int/number/bool, object+properties+required, array+scalar items) plus one degradation test per construct (enum, oneOf, anyOf, $ref, nullable). Pure-sync (no `@pytest.mark.asyncio`). Construct `Tool(...)` literals inline mirroring `_clean_tool()`.

#### `tests/framework/unit/test_codegen_emitter.py` (new)

**Analog:** `tests/framework/unit/test_config_init.py`.

**Pattern (from `test_config_init.py:1-29`):**
```python
"""Self-contained-scaffold coverage for Phase 12 CLEAN-05 + D-01/D-02/D-03."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from mcp_test_framework.cli import _format_tools_yaml_scaffold


class _StubTool:
    """Minimal stand-in for mcp.types.Tool -- only `name` is read by the scaffold."""

    def __init__(self, name: str) -> None:
        self.name = name


def _scaffold(tool_names: list[str]) -> str:
    return _format_tools_yaml_scaffold([_StubTool(n) for n in tool_names])
```

**Apply:** Use `tmp_path` (pytest builtin) for file emission. Assertions on (a) header marker presence (4 specific lines), (b) `model_config = ConfigDict(extra="forbid")` on `<Tool>Params`, (c) absence of `extra="forbid"` on `<Tool>Response`, (d) idempotence (run emit twice, diff bytes match), (e) one-file-per-tool layout.

#### `tests/framework/unit/test_codegen_typecheck.py` (new)

**Analog:** `tests/framework/test_runner_subprocess.py` (drives a subprocess + asserts on its exit / output).

**Pattern (general subprocess-test idiom, in this codebase):**
- Use `subprocess.run([sys.executable, "-m", "pyright", str(generated_dir)], capture_output=True, text=True, check=False)`.
- Assert `result.returncode == 0` with `result.stdout + result.stderr` as the failure message.
- Drive the emit step via `_codegen.translate_and_emit(...)` against a synthetic fixture under `tmp_path` to avoid coupling to live homelab-mcp.

**Apply:** Single test function `test_pyright_strict_clean_against_synthetic()`. Synthetic fixture: 4-5 inline `Tool(...)` literals exercising scalar/object/array + a degradation case. Skip cleanly if pyright is not on PATH (CI fallback) — `pytest.skip("pyright not installed")` is the canonical phrase, mirroring how `pytest-timeout` is opt-in in `pyproject.toml:31-36`.

#### `tests/framework/unit/test_tool_response.py` (new)

**Analog:** `tests/framework/unit/test_ollama_judge.py:1-39` (pure-sync tests on a Pydantic model + module-level helpers).

**Pattern:** No event loop, no fixtures. Construct `CallToolResult(...)` literals + wrap in `ToolResponse(raw=...)`. Assertions on `.is_error`, `.text`, `.data`. Test the CODEGEN-04 fallback chain:
1. `structuredContent={"foo": 1}` → `.data == {"foo": 1}`.
2. No `structuredContent`, single `TextContent(text='{"foo": 1}')` → `.data == {"foo": 1}`.
3. No `structuredContent`, malformed JSON text → `.data == {"text": "..."}` fallback.
4. `isError=True` → `.is_error is True`.
5. `text` concatenation across multiple `TextContent` blocks.

#### `tests/framework/unit/test_gen_sdet_classes_cli.py` (new)

**Analog (exact):** `tests/framework/test_config_init_cli.py`.

**Pattern (from `test_config_init_cli.py:13-39`):**
```python
from __future__ import annotations
from pathlib import Path
import pytest
from typer.testing import CliRunner
from mcp_test_framework.cli import app


def _invoke(*args: str):
    """CliRunner construction site -- isolated for forward-compat with future
    Typer kwargs (e.g. mix_stderr deprecation)."""
    return CliRunner().invoke(app, list(args))


def test_help_lists_flags() -> None:
    result = _invoke("gen-sdet-classes", "--help")
    assert result.exit_code == 0, result.output
    assert "--config" in result.output
```

**Apply:** `--help` test, no-config fail-loud SAFE-03 test (mirror `test_config_init_cli.py`'s refuse-overwrite at lines 42-55), and a `@pytest.mark.live_homelab` end-to-end emit test against live homelab-mcp that asserts the directory `src/mcp_test_framework/sdet/generated/homelab_mcp/` is populated.

---

## Shared Patterns

### Module docstring shape

**Source:** every src/mcp_test_framework/*.py file (e.g. `mcp_client.py:1-30`, `ollama_judge.py:1-60`, `schema_validator.py:1-29`).

**Apply to:** all new src modules (`response.py`, `_codegen.py`, `_tool_factory.py`, `sdet/__init__.py`).

**Format:**
```python
"""<one-line summary>

<paragraph linking to the spec / CONTEXT.md decisions by name>

Per Phase 17 CONTEXT.md decisions (D-01..D-09):
- <decision N>: <explanation>
- ...

<Phase N consumer note: how downstream code uses this module>
"""
```

### `from __future__ import annotations`

**Source:** every src/mcp_test_framework/*.py module top-of-file (verified in `mcp_client.py:31`, `schema_validator.py:30`, `ollama_judge.py:61`, `cli.py:32`, `models.py:20`).

**Apply to:** ALL new src files AND generated files. Critical for forward references in generated code (a `<Tool>Response` may reference a sibling-generated nested model).

### Operator-tone error pattern

**Source:** `src/mcp_test_framework/_runner.py:_emit_operator_error` (re-exported at `cli.py:78`).

**Apply to:** the new `gen-sdet-classes` Typer command's error paths (FileNotFoundError, empty `serverInfo.name`, schema-validity pre-flight failure).

**Shape (3 named args):**
```python
_emit_operator_error(
    summary="<short summary, lowercase, no trailing period>",
    detail=["<line 1>", "<line 2>", "", "<paragraph 2>"],
    next_step="<imperative verb> <command or action>",
)
```

`_emit_operator_error` raises `typer.Exit(2)`. Exit-code-130 SIGINT path uses `raise typer.Exit(code=130)` directly.

### Pydantic model_config conventions

**Source:** `src/mcp_test_framework/models.py:36-93`, `src/mcp_test_framework/ollama_judge.py:108`.

**Apply to:**
- `ToolResponse` base: `ConfigDict(arbitrary_types_allowed=True)` per D-07. (`CallToolResult` is a Pydantic v2 model so this is belt-and-suspenders.)
- Generated `<Tool>Params` classes: `ConfigDict(extra="forbid")` per CONTEXT.md Claude-Discretion last bullet.
- Generated `<Tool>Response` classes: no `model_config` line at all — they inherit `ToolResponse`'s.

### Repo-wide test conventions

**Source:** `tests/framework/unit/test_schema_validator.py`, `test_ollama_judge.py`, `test_config_init.py`, `test_config_init_cli.py`.

**Apply to:** all new test files under `tests/framework/unit/`.

**Conventions:**
- `from __future__ import annotations` at top.
- Module docstring enumerating what is being pinned and why.
- Tests are pure-sync unless they involve the MCP client or Ollama (in which case `@pytest.mark.asyncio` is mandatory per `pyproject.toml:45`).
- Live-server tests gated behind `@pytest.mark.live_homelab` or `@pytest.mark.live_ollama` (markers declared in `pyproject.toml:48-51`).
- `CliRunner` tests use a `_invoke(*args)` helper (verified at `test_config_init_cli.py:22-25`).
- `tmp_path` (pytest builtin) used for any test that writes files; never repo-relative paths.

### Generated-file header marker

**Source:** CONTEXT.md §Specifics (lines 197-203). Repo has no existing precedent for AUTOGENERATED files — Phase 17 introduces this.

**Apply to:** every file written under `src/mcp_test_framework/sdet/generated/<slug>/`.

```python
# AUTOGENERATED by mcp-test-framework gen-sdet-classes — DO NOT HAND-EDIT.
# Source: <server_slug> (serverInfo.name="<actual_name>", version="<version>")
# Regenerated: <ISO timestamp>
# Extend by subclassing in tests/sdet/, not by editing this file.
```

### `# codegen: degraded` comment shape

**Source:** CONTEXT.md §Specifics (lines 205-209). No repo precedent — Phase 17 introduces.

**Apply to:** every emitted field where the walker degrades to `typing.Any`. Place directly above the field, e.g.:
```python
    # codegen: degraded — oneOf not in v1.3 coverage; got Any
    target_id: typing.Any
```

Test (`test_codegen_walker.py`) must assert the literal `# codegen: degraded` token appears in emitted source for each degradation path (D-02).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/mcp_test_framework/sdet/response.py` (`@computed_field`) | model | lazy transform | No `@computed_field` precedent in the codebase. `JudgeResult` is the closest Pydantic-model analog but uses plain fields. Apply the model_config + Field-default conventions from `JudgeResult`, but the `@computed_field` + `@property` lazy-derive idiom is new to this repo. Reference: pydantic v2 docs (already pinned as `pydantic>=2.13,<3` in pyproject.toml). |
| `src/mcp_test_framework/sdet/generated/<slug>/__init__.py` (auto-generated, with `_REGISTRY` table) | generator output | static re-export | No existing auto-generated file in the repo. The header marker + `_REGISTRY` shape is novel to Phase 17; locked by CONTEXT.md §Specifics + D-09. |
| `tests/framework/unit/test_codegen_typecheck.py` (pyright subprocess) | test | subprocess | No existing pyright test. `tests/framework/test_runner_subprocess.py` is the closest subprocess-driving precedent. Pyright invocation pattern documented in CONTEXT.md D-04 + RESEARCH §Installation. |

These three lack an in-repo analog. The planner should:
1. For `response.py`: follow Pydantic v2 docs verbatim (`@computed_field` + `@property` is standard since pydantic 2.0).
2. For the generated `__init__.py`: invent the shape from CONTEXT.md §Specifics — locked there.
3. For `test_codegen_typecheck.py`: model on `subprocess.run([sys.executable, "-m", "pyright", ...])` per RESEARCH; skip if pyright is not on PATH.

---

## Metadata

**Analog search scope:**
- `src/mcp_test_framework/` (12 modules)
- `tests/framework/unit/` (18 files) + `tests/framework/` top-level (8 files)
- `pyproject.toml` (project deps + dev-deps)
- `.planning/phases/17-schema-driven-codegen-surface/` (CONTEXT.md, RESEARCH.md)
- `.planning/REQUIREMENTS.md` (CODEGEN-01..06)

**Files scanned (Read with content extracted):**
- `src/mcp_test_framework/mcp_client.py` (211 lines, full)
- `src/mcp_test_framework/models.py` (135 lines, full)
- `src/mcp_test_framework/schema_validator.py` (206 lines, full)
- `src/mcp_test_framework/cli.py` (selected ranges: 1-200, 280-470, 600-768, 760-960)
- `src/mcp_test_framework/fixtures.py` (1-80)
- `src/mcp_test_framework/_runner.py` (725-825 for `_render_pre_run_digest`)
- `src/mcp_test_framework/ollama_judge.py` (1-80 + JudgeResult excerpt)
- `src/mcp_test_framework/__init__.py` (3 lines, full)
- `tests/framework/unit/test_schema_validator.py` (1-80)
- `tests/framework/unit/test_config_init.py` (1-80)
- `tests/framework/test_config_init_cli.py` (1-80)
- `tests/framework/unit/test_cli_errors.py` (1-60)
- `tests/framework/unit/test_ollama_judge.py` (1-39)
- `tests/framework/unit/test_runner_pre_run_digest.py` (1-60)
- `pyproject.toml` (80 lines, full)

**Pattern extraction date:** 2026-05-12

**Greenfield areas (Phase 17 introduces these to the codebase):**
- `@computed_field` / `@property` lazy-derived fields on Pydantic v2 BaseModels.
- AUTOGENERATED file header marker convention.
- `# codegen: degraded` comment convention.
- pyright as a verifier (currently no static-type-check tooling lives in the repo).
- A registry that's populated by generated code and consumed by hand-written code (`_REGISTRY` written by codegen, read by `_tool_factory.tool(name)`).
