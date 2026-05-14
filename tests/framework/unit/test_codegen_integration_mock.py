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

Does NOT touch src/mcp_test_framework/sdet/generated/homelab_mcp/ -- that
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
    assert set(Params.model_fields) == {"message"}, list(Params.model_fields)
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
    # annotation may be `list[float]` or equivalent -- verify via repr containment.
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
    assert set(Params.model_fields) == {"host", "timeout_ms"}, list(Params.model_fields)
    assert Params.model_fields["host"].is_required()
    assert Params.model_fields["host"].annotation is str
    timeout_field = Params.model_fields["timeout_ms"]
    assert not timeout_field.is_required()
    assert timeout_field.default == 1000
    assert timeout_field.annotation is int


def test_ping_with_timeout_response_typed_fields(generated: Path) -> None:
    """outputSchema declared with `ok: bool` + `elapsed_ms: int` -> typed Response.

    The synthetic outputSchema does not mark these fields as required, so the
    codegen emits them as ``Optional[bool]`` / ``Optional[int]`` (annotation
    ``bool | None`` / ``int | None``) with default ``None``. We assert via
    repr-containment so the test is robust to Pydantic v2's runtime
    representation of optional generics across minor versions -- matching the
    same idiom used for the ``list[float]`` field in
    ``test_add_numbers_params_array_and_default``.
    """
    mod = _load_generated_module(generated, "ping_with_timeout")
    Response = mod.PingWithTimeoutResponse
    assert ToolResponse in Response.__mro__
    # The typed output fields are present on the Response Pydantic model.
    assert "ok" in Response.model_fields
    assert "elapsed_ms" in Response.model_fields
    ok_ann = Response.model_fields["ok"].annotation
    elapsed_ann = Response.model_fields["elapsed_ms"].annotation
    # outputSchema fields aren't in `required` -> codegen emits Optional[T];
    # accept either bare T (future codegen change) or Optional[T] (current).
    assert "bool" in repr(ok_ann), repr(ok_ann)
    assert "int" in repr(elapsed_ann), repr(elapsed_ann)


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


# --- Test 7: degradation counter increments on unsupported schema shapes ---

def test_generate_counts_reports_degraded_fields(tmp_path: Path) -> None:
    """A schema with an enum field must increment ``degraded_fields``.

    The ``generated`` fixture already locks the *clean* direction (every test
    that uses it asserts ``degraded_fields == 0`` on a synthetic fixture
    hand-crafted to avoid degradation triggers). This test locks the *inverse*
    direction: feed codegen a known-degraded shape (enum, per D-02 / _codegen.py
    line 212) and confirm the counter actually increments. Without this test
    a regression that silently stopped incrementing ``degraded_fields`` would
    pass every other test in this module."""
    degraded_tool = Tool(
        name="enum_tool",
        description="One enum field.",
        inputSchema={
            "type": "object",
            "properties": {"mode": {"type": "string", "enum": ["a", "b"]}},
            "required": ["mode"],
        },
        outputSchema=None,
    )
    counts = generate(
        server_name=_SYNTHETIC_SERVER_NAME,
        server_version=_SYNTHETIC_SERVER_VERSION,
        tools=[degraded_tool],
        out_root=tmp_path,
        timestamp=_FIXED_TS,
    )
    assert counts == {"tools": 1, "degraded_fields": 1}
