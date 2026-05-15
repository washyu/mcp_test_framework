---
phase: 20-preflight-conditional-skip
plan: 05
type: execute
wave: 2
depends_on:
  - 20-01-requirements-scrub-PLAN
files_modified:
  - tests/framework/unit/test_codegen_integration_mock.py
autonomous: true
requirements:
  - CODEGEN-COVERAGE-01
must_haves:
  truths:
    - "A new test file under tests/framework/unit/ feeds a hand-crafted synthetic tool list through the codegen pipeline"
    - "The synthetic input covers: required scalar string, optional scalar with default, array-of-scalar, integer-with-default, outputSchema-declared, outputSchema-omitted"
    - "Tests run via `uv run pytest tests/framework/unit/test_codegen_integration_mock.py` and all pass"
    - "Tests do NOT touch src/mcp_test_framework/sdet/generated/homelab_mcp/ (committed artifacts stay)"
    - "Tests do NOT require a live MCP server or any subprocess spawn"
    - "Generated Params classes have expected field names, types, and required/optional flags"
    - "Generated Response classes inherit ToolResponse and expose .raw / .data / .text / .is_error"
    - "Generated __init__.py _REGISTRY dict maps tool names to (ParamsClass, ResponseClass) tuples"
    - "Generated modules import cleanly via importlib.import_module without errors"
  artifacts:
    - path: "tests/framework/unit/test_codegen_integration_mock.py"
      provides: "Mock-fixture-driven integration coverage of the codegen pipeline"
      min_lines: 150
      contains: "from mcp_test_framework.sdet._codegen import generate"
  key_links:
    - from: "tests/framework/unit/test_codegen_integration_mock.py"
      to: "src/mcp_test_framework/sdet/_codegen.py:generate"
      via: "direct function call against tmp_path output dir"
      pattern: "generate\\(server_name="
    - from: "tests/framework/unit/test_codegen_integration_mock.py"
      to: "src/mcp_test_framework/sdet/response.py:ToolResponse"
      via: "assert ToolResponse in <ResponseClass>.__mro__"
      pattern: "ToolResponse in.*__mro__|ToolResponse, .*__bases__"
---

<objective>
Add mock-fixture-driven codegen integration tests under `tests/framework/unit/`. The tests feed a hand-crafted synthetic tool list (covering the codegen pipeline's branches) through `mcp_test_framework.sdet._codegen.generate(...)` into a `tmp_path` output directory, then use `importlib.import_module` to introspect the generated artifacts and assert they have the correct shape.

Purpose: Replace the PREFLIGHT-01/02 coverage that was killed by the Phase 20 reframe. Pure-data, CI-safe, no live MCP, no subprocess. Catches future codegen drift by pinning the integration boundary between synthetic tool input and generated module artifacts.
Output: One new test file under `tests/framework/unit/`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/REQUIREMENTS.md
@.planning/phases/20-preflight-conditional-skip/20-CONTEXT.md
@src/mcp_test_framework/_codegen.py
@src/mcp_test_framework/sdet/_codegen.py
@src/mcp_test_framework/sdet/response.py
@src/mcp_test_framework/sdet/_slugs.py
@tests/framework/unit/test_codegen_emitter.py
@tests/framework/unit/test_gen_sdet_classes_cli.py

<interfaces>
<!-- Key contracts the executor needs. Use these directly — no codebase exploration. -->

From src/mcp_test_framework/sdet/_codegen.py:

```python
def generate(
    *,
    server_name: str,          # e.g. "synthetic-test-server"
    server_version: str,       # e.g. "0.0.1"
    tools: list[Tool],         # mcp.types.Tool instances
    out_root: Path,            # output root — generated tree goes under out_root/<slug>/
    timestamp: str,            # ISO-8601 string; held fixed for idempotence
) -> dict[str, int]:
    """Returns {"tools": N, "degraded_fields": M}. Writes per-tool .py files
    plus __init__.py under out_root/<server_slug>/."""
```

The server_slug derivation lives in `src/mcp_test_framework/sdet/_slugs.py:server_slug(server_name)`.
For `server_name="synthetic-test-server"`, the slug is `synthetic_test_server` (hyphens → underscores).

From src/mcp_test_framework/sdet/response.py:

```python
class ToolResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    raw: CallToolResult
    @computed_field @property
    def is_error(self) -> bool: ...
    @computed_field @property
    def text(self) -> str: ...
    @computed_field @property
    def data(self) -> dict[str, Any] | None: ...
```

From mcp.types (the official MCP SDK):

```python
class Tool(BaseModel):
    name: str
    description: str | None
    inputSchema: dict
    outputSchema: dict | None
```

From the existing test_codegen_emitter.py:

```python
from mcp.types import Tool
from mcp_test_framework.sdet._codegen import generate

def _t(name: str, *, input_schema: dict | None = None, output_schema: dict | None = None) -> Tool:
    return Tool(
        name=name,
        description=f"Test tool {name}",
        inputSchema=input_schema if input_schema is not None else {"type": "object", "properties": {}, "required": []},
        outputSchema=output_schema,
    )

_FIXED_TS = "2026-05-12T14:23:01+00:00"
```

The generated `<slug>/__init__.py` _REGISTRY annotation is:
```python
_REGISTRY: dict[str, tuple[type[BaseModel], type[ToolResponse]]] = {
    "<tool_name>": (<ToolName>Params, <ToolName>Response),
    ...
}
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Write tests/framework/unit/test_codegen_integration_mock.py with synthetic-tool-list fixture and importlib-driven assertions</name>
  <files>tests/framework/unit/test_codegen_integration_mock.py</files>
  <read_first>
    - tests/framework/unit/test_codegen_emitter.py (locked style — pure-data, no live MCP; the `_t(...)` helper pattern is the model to follow)
    - tests/framework/unit/test_gen_sdet_classes_cli.py (existing CLI-level codegen test; lines 119-183 show the tmp_path + importlib introspection pattern, though that test spawns a subprocess — we are NOT doing that, we call `generate(...)` directly)
    - src/mcp_test_framework/sdet/_codegen.py (lines 1-80 for module docstring + HEADER_TEMPLATE; lines 472-560 for the translate_tool surface — confirms what `generate` produces)
    - src/mcp_test_framework/sdet/response.py (full — ToolResponse contract: raw, .data, .text, .is_error)
    - src/mcp_test_framework/sdet/_slugs.py (server_slug / module_name / pascal_case derivations; needed to predict generated paths and class names)
    - .planning/phases/20-preflight-conditional-skip/20-CONTEXT.md (D-07, D-08, D-09, D-10 and the <specifics> "Synthetic tool fixture sketch")
  </read_first>
  <behavior>
The test file MUST exercise these scenarios via the synthetic tool list:

- Test 1: `echo_message` (required scalar string, outputSchema declared) — assert Params has `message: str` required; Response inherits ToolResponse.
- Test 2: `add_numbers` (required array-of-number, optional string with default, outputSchema OMITTED) — assert Params has `numbers: list[float]` required AND `label: str` optional with default "sum"; Response is a stub inheriting ToolResponse with no extra typed fields beyond `raw`.
- Test 3: `ping_with_timeout` (required scalar string, optional integer with default, outputSchema declared with boolean + integer) — assert Params has `host: str` required AND `timeout_ms: int` optional with default 1000; Response has `ok: bool` and `elapsed_ms: int` typed fields.
- Test 4: `_REGISTRY` shape — assert the generated `__init__.py` defines a `_REGISTRY` dict with exactly three entries; each value is a 2-tuple of (Params class, Response class); each Response class is a subclass of `ToolResponse`.
- Test 5: Module importability — assert `importlib.import_module("<slug>")` succeeds without raising; assert each per-tool module imports without raising; assert no module emits orphan import warnings (smoke check — running `importlib.import_module` is sufficient).
- Test 6: ToolResponse contract on every Response class — assert each Response class has the `raw`, `data`, `text`, `is_error` attributes accessible (via `hasattr` or `model_fields` + `model_computed_fields` introspection).
- Test 7: Counts return value — assert `generate(...)` returns `{"tools": 3, "degraded_fields": 0}` for the synthetic fixture (no degradations expected; if a future change adds a degradation path the test fails loudly).
  </behavior>
  <action>
Create `tests/framework/unit/test_codegen_integration_mock.py` with this content (you may adjust formatting/imports but the structural contract below is non-negotiable):

```python
"""Mock-fixture-driven integration tests for the codegen pipeline (Phase 20).

Replaces the PREFLIGHT-01/02 coverage killed by the Phase 20 reframe (see
.planning/phases/20-preflight-conditional-skip/20-CONTEXT.md D-07..D-10).

Drives a hand-crafted synthetic tool list through
mcp_test_framework.sdet._codegen.generate(...) into a tmp_path output dir,
then uses importlib to load the generated modules and asserts:

  1. <ToolName>Params Pydantic class shape (fields, types, required/optional).
  2. <ToolName>Response inherits ToolResponse with .raw/.data/.text/.is_error.
  3. _REGISTRY in __init__.py maps tool names to (Params, Response) tuples.
  4. Generated modules import cleanly via importlib.import_module.

CI-safe: pure-data, no live MCP, no subprocess. Locks the codegen contract
against silent regressions.

Does NOT touch src/mcp_test_framework/sdet/generated/homelab_mcp/ — that
tree contains committed artifacts regenerated externally via
`mcp-test-framework gen-sdet-classes` against a live homelab-mcp.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from mcp.types import Tool

from mcp_test_framework.sdet._codegen import generate
from mcp_test_framework.sdet.response import ToolResponse


# --- Synthetic tool fixture ------------------------------------------------
# Three tools covering the codegen branches:
#   - required scalar string
#   - optional string with default
#   - required array-of-number
#   - optional integer with default
#   - outputSchema declared (with typed fields)
#   - outputSchema omitted (exercises D-06 stub Response path)

_SYNTHETIC_SERVER_NAME = "synthetic-test-server"
_SYNTHETIC_SERVER_VERSION = "0.0.1"
_SYNTHETIC_SLUG = "synthetic_test_server"  # server_slug() derivation
_FIXED_TS = "2026-05-13T00:00:00+00:00"


def _synthetic_tools() -> list[Tool]:
    return [
        Tool(
            name="echo_message",
            description="Echo a string back unchanged.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
                "required": ["message"],
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "echoed": {"type": "string"},
                },
            },
        ),
        Tool(
            name="add_numbers",
            description="Sum a list of numbers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "numbers": {"type": "array", "items": {"type": "number"}},
                    "label": {"type": "string", "default": "sum"},
                },
                "required": ["numbers"],
            },
            outputSchema=None,  # exercises the D-06 stub Response path
        ),
        Tool(
            name="ping_with_timeout",
            description="Pretend to ping with optional timeout.",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "timeout_ms": {"type": "integer", "default": 1000},
                },
                "required": ["host"],
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "elapsed_ms": {"type": "integer"},
                },
            },
        ),
    ]


# --- Importlib helper ------------------------------------------------------

def _load_generated_module(slug_dir: Path, module_name: str) -> ModuleType:
    """Load a generated module from `slug_dir/<module_name>.py` without
    permanently polluting sys.modules with a non-package path.

    Uses importlib.util.spec_from_file_location -- the standard pattern for
    loading source from a temp directory. We register the module under a
    unique synthetic package prefix so re-runs in the same pytest session
    don't collide (Pitfall: pytest's sys.modules cache survives across
    tests in the same process).
    """
    fq_name = f"_phase20_mock_{slug_dir.name}_{module_name}"
    if fq_name in sys.modules:
        del sys.modules[fq_name]
    spec = importlib.util.spec_from_file_location(
        fq_name, slug_dir / f"{module_name}.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[fq_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_generated_init(slug_dir: Path) -> ModuleType:
    """Load slug_dir/__init__.py. Because __init__.py uses RELATIVE imports
    (`from .echo_message import ...`), it can't be loaded standalone via
    spec_from_file_location -- we need to register it as a package with
    submodule_search_locations pointing at the slug_dir, then have the
    relative imports resolve via the per-tool .py files in the same dir.
    """
    pkg_name = f"_phase20_mock_pkg_{slug_dir.name}"
    # Clean up any prior registration from earlier tests in the same session.
    for k in [k for k in list(sys.modules) if k == pkg_name or k.startswith(pkg_name + ".")]:
        del sys.modules[k]
    spec = importlib.util.spec_from_file_location(
        pkg_name,
        slug_dir / "__init__.py",
        submodule_search_locations=[str(slug_dir)],
    )
    assert spec is not None and spec.loader is not None
    pkg = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name] = pkg
    spec.loader.exec_module(pkg)
    return pkg


# --- Shared fixture: run codegen once per test -----------------------------

@pytest.fixture
def generated(tmp_path: Path) -> Path:
    """Run codegen into tmp_path; return the slug subdirectory."""
    counts = generate(
        server_name=_SYNTHETIC_SERVER_NAME,
        server_version=_SYNTHETIC_SERVER_VERSION,
        tools=_synthetic_tools(),
        out_root=tmp_path,
        timestamp=_FIXED_TS,
    )
    assert counts == {"tools": 3, "degraded_fields": 0}, counts
    slug_dir = tmp_path / _SYNTHETIC_SLUG
    assert slug_dir.is_dir(), f"expected {slug_dir} to exist; got {list(tmp_path.iterdir())}"
    return slug_dir


# --- Test 1: echo_message Params + Response shape --------------------------

def test_echo_message_params_class_shape(generated: Path) -> None:
    """Required scalar string field; outputSchema declared."""
    mod = _load_generated_module(generated, "echo_message")
    Params = mod.EchoMessageParams
    assert "message" in Params.model_fields, list(Params.model_fields)
    field = Params.model_fields["message"]
    assert field.annotation is str
    assert field.is_required()


def test_echo_message_response_inherits_tool_response(generated: Path) -> None:
    mod = _load_generated_module(generated, "echo_message")
    Response = mod.EchoMessageResponse
    assert ToolResponse in Response.__mro__
    # CODEGEN-04 surface: raw / data / text / is_error all accessible on the class.
    assert "raw" in Response.model_fields
    # is_error / text / data are computed_field properties; presence in model_computed_fields.
    assert {"is_error", "text", "data"}.issubset(set(Response.model_computed_fields))


# --- Test 2: add_numbers (array + optional-with-default + outputSchema omitted)

def test_add_numbers_params_array_and_default(generated: Path) -> None:
    mod = _load_generated_module(generated, "add_numbers")
    Params = mod.AddNumbersParams
    assert "numbers" in Params.model_fields
    assert "label" in Params.model_fields
    numbers_field = Params.model_fields["numbers"]
    # list[float] -- json-schema "number" maps to float per _SCALAR_MAP in _codegen.py
    assert numbers_field.is_required()
    # annotation may be `list[float]` or equivalent — verify via repr containment.
    assert "float" in repr(numbers_field.annotation), repr(numbers_field.annotation)
    label_field = Params.model_fields["label"]
    assert not label_field.is_required()
    assert label_field.default == "sum"


def test_add_numbers_response_is_stub_inheriting_tool_response(generated: Path) -> None:
    """outputSchema omitted -> D-06 stub Response: inherits ToolResponse,
    no extra typed fields beyond `raw` (inherited from ToolResponse)."""
    mod = _load_generated_module(generated, "add_numbers")
    Response = mod.AddNumbersResponse
    assert ToolResponse in Response.__mro__
    # Stub: model_fields should be EXACTLY the inherited fields from ToolResponse.
    # ToolResponse defines exactly one declared field: `raw`.
    declared_fields = set(Response.model_fields)
    assert declared_fields == {"raw"}, declared_fields


# --- Test 3: ping_with_timeout (int-with-default + typed output) -----------

def test_ping_with_timeout_params_int_default(generated: Path) -> None:
    mod = _load_generated_module(generated, "ping_with_timeout")
    Params = mod.PingWithTimeoutParams
    assert Params.model_fields["host"].is_required()
    assert Params.model_fields["host"].annotation is str
    timeout_field = Params.model_fields["timeout_ms"]
    assert not timeout_field.is_required()
    assert timeout_field.default == 1000
    assert timeout_field.annotation is int


def test_ping_with_timeout_response_typed_fields(generated: Path) -> None:
    """outputSchema declared with `ok: bool` + `elapsed_ms: int` -> typed Response."""
    mod = _load_generated_module(generated, "ping_with_timeout")
    Response = mod.PingWithTimeoutResponse
    assert ToolResponse in Response.__mro__
    # The typed output fields are present on the Response Pydantic model.
    assert "ok" in Response.model_fields
    assert "elapsed_ms" in Response.model_fields
    assert Response.model_fields["ok"].annotation is bool
    assert Response.model_fields["elapsed_ms"].annotation is int


# --- Test 4: _REGISTRY shape -----------------------------------------------

def test_registry_dict_shape(generated: Path) -> None:
    pkg = _load_generated_init(generated)
    registry = pkg._REGISTRY
    assert isinstance(registry, dict)
    assert set(registry.keys()) == {"echo_message", "add_numbers", "ping_with_timeout"}, list(registry.keys())
    for name, entry in registry.items():
        assert isinstance(entry, tuple), (name, entry)
        assert len(entry) == 2, (name, entry)
        params_cls, response_cls = entry
        # Params is a Pydantic BaseModel subclass.
        from pydantic import BaseModel
        assert issubclass(params_cls, BaseModel), (name, params_cls)
        # Response is a ToolResponse subclass.
        assert issubclass(response_cls, ToolResponse), (name, response_cls)


# --- Test 5: Module importability ------------------------------------------

def test_all_generated_modules_import_cleanly(generated: Path) -> None:
    """Loading each per-tool module + the package __init__.py raises nothing."""
    for tool_name in ("echo_message", "add_numbers", "ping_with_timeout"):
        mod = _load_generated_module(generated, tool_name)
        assert mod is not None
    pkg = _load_generated_init(generated)
    assert pkg is not None


# --- Test 6: ToolResponse contract on every Response class -----------------

def test_every_response_class_exposes_tool_response_surface(generated: Path) -> None:
    """Every generated Response class -- typed OR stub -- exposes the
    uniform CODEGEN-04 surface inherited from ToolResponse."""
    pkg = _load_generated_init(generated)
    for tool_name, (_, response_cls) in pkg._REGISTRY.items():
        # raw is a declared field on ToolResponse base.
        assert "raw" in response_cls.model_fields, tool_name
        # is_error / text / data are computed_field properties.
        computed = set(response_cls.model_computed_fields)
        assert {"is_error", "text", "data"}.issubset(computed), (tool_name, computed)


# --- Test 7: counts return value pinned ------------------------------------

def test_generate_counts_no_degraded_fields(tmp_path: Path) -> None:
    """The synthetic fixture is hand-crafted to use ONLY codegen-supported
    JSON Schema shapes. If a future change degrades any of these fields,
    this test fails loudly -- and the new degradation should be either
    fixed in _codegen.py or added to the synthetic fixture's known-degraded
    set with an explicit assertion."""
    counts = generate(
        server_name=_SYNTHETIC_SERVER_NAME,
        server_version=_SYNTHETIC_SERVER_VERSION,
        tools=_synthetic_tools(),
        out_root=tmp_path,
        timestamp=_FIXED_TS,
    )
    assert counts == {"tools": 3, "degraded_fields": 0}
```

**Notes on implementation:**

1. The `_load_generated_init` helper uses `submodule_search_locations` because the generated `__init__.py` uses RELATIVE imports (e.g. `from .echo_message import ...`). Loading it as a standalone file via plain `spec_from_file_location` would fail with `ImportError: attempted relative import with no known parent package`.

2. The synthetic slug is `synthetic_test_server` — this is the `server_slug("synthetic-test-server")` output (hyphens become underscores). If the slug derivation changes, this test will fail at the `slug_dir.is_dir()` check inside the `generated` fixture, which is the correct loud-fail behavior.

3. `_FIXED_TS` is held fixed across all tests to match the existing `test_codegen_emitter.py` idiom. Idempotence is already covered by `test_codegen_emitter.py:test_emitter_is_idempotent_with_fixed_timestamp` — Plan 20-05 does not re-test idempotence.

4. The test file uses `tmp_path` only — it NEVER writes to `src/mcp_test_framework/sdet/generated/` (D-10).

5. The `pytest.fixture generated` runs the codegen once per test (function-scoped). Codegen is fast (no subprocess, no live MCP, ~milliseconds for 3 tools) — function scope keeps each test isolated and matches the locked style in `test_codegen_emitter.py`.

6. The annotation check `numbers_field.annotation` for `list[float]` is fuzzed via `"float" in repr(...)` because Pydantic v2's runtime representation of generic types can vary across minor versions. The robust assertion is "the field is required and references float somewhere" — exact-type equality would be brittle.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_codegen_integration_mock.py -v</automated>
  </verify>
  <acceptance_criteria>
    - File `tests/framework/unit/test_codegen_integration_mock.py` exists.
    - File contains imports: `from mcp_test_framework.sdet._codegen import generate` AND `from mcp_test_framework.sdet.response import ToolResponse`.
    - File contains the literal string `_SYNTHETIC_SLUG = "synthetic_test_server"`.
    - File defines at least 7 test functions (one for each of the behaviors listed above): `test_echo_message_params_class_shape`, `test_echo_message_response_inherits_tool_response`, `test_add_numbers_params_array_and_default`, `test_add_numbers_response_is_stub_inheriting_tool_response`, `test_ping_with_timeout_params_int_default`, `test_ping_with_timeout_response_typed_fields`, `test_registry_dict_shape`, `test_all_generated_modules_import_cleanly`, `test_every_response_class_exposes_tool_response_surface`, `test_generate_counts_no_degraded_fields` (at least 7 of these 10 must be present).
    - `uv run pytest tests/framework/unit/test_codegen_integration_mock.py -v` reports all tests passing (`PASSED`), zero failures, zero errors. Exit code 0.
    - `grep -c 'sdet/generated/homelab_mcp' tests/framework/unit/test_codegen_integration_mock.py` returns `0` (D-10: the test does not touch the committed homelab_mcp artifacts).
    - `grep -c 'subprocess\|Popen\|stdio_client' tests/framework/unit/test_codegen_integration_mock.py` returns `0` (no live MCP, no subprocess — pure data).
    - The new test file does NOT modify any existing file under `src/` or `tests/`.
  </acceptance_criteria>
  <done>One new test file under `tests/framework/unit/` exercises the codegen pipeline via a synthetic 3-tool fixture, asserts Params/Response/registry/import contract end-to-end, all tests pass, zero live-MCP or subprocess dependencies, and the existing `sdet/generated/homelab_mcp/` committed artifacts are untouched.</done>
</task>

</tasks>

<verification>
After this plan:
- `uv run pytest tests/framework/unit/test_codegen_integration_mock.py` exits 0 with all tests passing.
- `uv run pytest tests/framework/unit/` (the whole unit-test directory) still passes — the new file integrates cleanly with existing codegen tests.
- The committed `src/mcp_test_framework/sdet/generated/homelab_mcp/` artifacts are byte-identical to their pre-task state.
</verification>

<success_criteria>
- CODEGEN-COVERAGE-01 satisfied: mock-fixture-driven unit tests verify the codegen pipeline shape end-to-end.
- The tests are CI-runnable without operator infrastructure (no live MCP, no Proxmox, no Ollama).
- Future codegen drift in `_codegen.py:generate` or `response.py:ToolResponse` is caught at this test surface before it reaches `gen-sdet-classes` against a real SUT.
- D-07 (location), D-08 (synthetic-fixture shape), D-09 (assertion contract), D-10 (don't touch committed generated/) all honored.
</success_criteria>

<output>
After completion, create `.planning/phases/20-preflight-conditional-skip/20-05-SUMMARY.md`. Note any deviations from the planned assertion list (e.g., if `model_computed_fields` introspection had to use a different attribute name on the running Pydantic version) so future regressions can be traced.
</output>
