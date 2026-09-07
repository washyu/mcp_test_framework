"""Pyright strict-mode typecheck gate for generated SDET classes (D-04).

This test drives `_codegen.generate(...)` against a synthetic 5-tool fixture
(scalars + array + object + 2 degraded paths), then runs pyright as a
subprocess against the resulting generated/<slug>/ directory and asserts
exit code 0. This is the verification capstone for CODEGEN-02/03/04 + D-02's
degradation strategy (`typing.Any` is pyright-clean by design).

The fixture is SYNTHETIC (not live homelab-mcp) so the gate is deterministic
and doesn't drift with real-world server changes.

If pyright is not on PATH (e.g. fresh CI without dev deps), the tests skip
cleanly per RESEARCH guidance.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from mcp.types import Tool

from mcp_test_framework.test_code import _codegen


def _pyright_available() -> bool:
    """Detect pyright availability via `python -m pyright --version`."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pyright", "--version"],
            capture_output=True, text=True, check=False, timeout=30,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


_HAS_PYRIGHT = _pyright_available()


def _synthetic_tools() -> list[Tool]:
    """6-tool synthetic fixture exercising the D-02 coverage matrix + the
    Gap-1 / 17-HUMAN-UAT shape.

    1. simple_tool   -- scalars (str + int with default)
    2. array_tool    -- array of scalar (list[str])
    3. object_tool   -- nested object (degrades to dict[str, Any] in v1.3)
    4. enum_tool     -- enum (degrades to typing.Any)
    5. oneof_tool    -- oneOf (degrades to typing.Any)
    6. basic_tool    -- zero params (Gap-1 regression: pre-Plan-17-06 emitter
                        produced orphaned `import typing` and `Field` imports
                        that pyright strict rejected with reportUnusedImport).
    """
    return [
        Tool(
            name="simple_tool",
            description="A tool with scalar params.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Item name"},
                    "count": {"type": "integer", "default": 1},
                },
                "required": ["name"],
            },
            outputSchema=None,
        ),
        Tool(
            name="array_tool",
            description="A tool with an array param.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["tags"],
            },
            outputSchema=None,
        ),
        Tool(
            name="object_tool",
            description="A tool with a nested object param.",
            inputSchema={
                "type": "object",
                "properties": {
                    "config": {"type": "object", "properties": {"k": {"type": "string"}}},
                },
                "required": [],
            },
            outputSchema=None,
        ),
        Tool(
            name="enum_tool",
            description="A tool with an enum param (degrades).",
            inputSchema={
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["a", "b", "c"]},
                },
                "required": ["kind"],
            },
            outputSchema=None,
        ),
        Tool(
            name="oneof_tool",
            description="A tool with a oneOf param (degrades).",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {"oneOf": [{"type": "string"}, {"type": "integer"}]},
                },
                "required": [],
            },
            outputSchema=None,
        ),
        Tool(
            name="basic_tool",
            description="A tool with zero params (the Gap-1 / 17-HUMAN-UAT shape). Live homelab-mcp tools like list_registered_servers produced 29 reportUnusedImport pyright errors because the emitter unconditionally wrote `import typing` and `Field` even when neither was referenced. This fixture pins the gate against that shape.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
            outputSchema=None,
        ),
    ]


def _run_pyright(generated_root: Path) -> subprocess.CompletedProcess:
    """Invoke pyright as a subprocess against the generated dir."""
    return subprocess.run(
        [sys.executable, "-m", "pyright", "--pythonversion", "3.12", str(generated_root)],
        capture_output=True, text=True, check=False, timeout=120,
    )


@pytest.mark.skipif(not _HAS_PYRIGHT, reason="pyright not installed (run `uv sync` to install dev deps)")
def test_synthetic_generated_passes_pyright_strict(tmp_path: Path) -> None:
    """The generated SDET classes for the synthetic fixture pyright-check clean.

    Drives _codegen.generate(...) against 5 synthetic tools (scalars +
    array + object + 2 degraded paths), then runs pyright against the
    resulting directory in strict mode. Asserts exit 0.
    """
    out_root = tmp_path / "generated_typecheck"
    counts = _codegen.generate(
        server_name="synth-server",
        server_version="0.0.1",
        tools=_synthetic_tools(),
        out_root=out_root,
        timestamp="2026-05-12T00:00:00+00:00",
    )
    assert counts["tools"] == 6
    # 3 degradations: enum_tool.kind (enum) + oneof_tool.target (oneOf) +
    # object_tool.config (nested object with `properties` -- per _codegen.py
    # _emit_field: nested-object-with-properties degrades in v1.3, while a
    # bare {"type":"object"} with no properties translates to dict[str, Any]).
    # The plan's behavior comment counted "2 degraded paths" anticipating only
    # the enum + oneOf cases; the actual walker (Plan 17-02) also degrades
    # nested objects with declared properties. Test asserts true behavior.
    assert counts["degraded_fields"] == 3

    generated_slug_dir = out_root / "synth_server"
    assert generated_slug_dir.is_dir()

    result = _run_pyright(generated_slug_dir)
    assert result.returncode == 0, (
        f"pyright failed with exit {result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}\n"
    )


@pytest.mark.skipif(not _HAS_PYRIGHT, reason="pyright not installed")
def test_pyright_rejects_deliberately_broken_generated_file(tmp_path: Path) -> None:
    """Negative-coverage check: prove the pyright gate is a REAL gate, not
    a no-op. Mutate one generated file to introduce a type error, then
    assert pyright fails.
    """
    out_root = tmp_path / "generated_typecheck_broken"
    _codegen.generate(
        server_name="synth-server",
        server_version="0.0.1",
        tools=_synthetic_tools(),
        out_root=out_root,
        timestamp="2026-05-12T00:00:00+00:00",
    )
    target = out_root / "synth_server" / "simple_tool.py"
    text = target.read_text(encoding="utf-8")
    # Inject a type error: instantiate the model with wrong-typed kwargs at
    # module top level so pyright sees it during the file walk.
    text += "\n_typecheck_violation: int = SimpleToolParams(name='x').name  # str -> int = error\n"
    target.write_text(text, encoding="utf-8")

    result = _run_pyright(out_root / "synth_server")
    assert result.returncode != 0, (
        f"pyright unexpectedly passed despite a deliberate type error; "
        f"the gate is not enforcing strict mode.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
