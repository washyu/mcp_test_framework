"""Contract pins for the ``_isolated_home`` fixture's passthrough short-circuit
and the ``mcp_client`` fixture's dispatcher routing.

Three load-bearing invariants from Phase 34 CONTEXT.md:

1. ``_isolated_home`` takes ``mcp_config: Config`` as a dependency and branches
   on ``mcp_config.host_isolation``. Under ``'passthrough'``, it yields ``None``
   WITHOUT entering the tempfile.TemporaryDirectory context manager (no
   tempdir allocated, no cleanup machinery engaged -- the tempdir's sole
   consumer was the HOME redirect that passthrough disables).
2. Under ``host_isolation='strict'`` (default), the fixture yields a ``Path``
   exactly as it did in v1.0-v1.4.
3. The ``mcp_client`` fixture wires ``_build_subprocess_env(mcp_config.host_isolation,
   _isolated_home)`` instead of the legacy ``_build_isolated_env(_isolated_home)``
   direct call. Verified by grep at the file level (no live MCP needed).
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from mcp_test_framework.config import Config
from mcp_test_framework.fixtures import _isolated_home as _isolated_home_fixture
from mcp_test_framework.models import McpServerConfig, OllamaConfig, TestCodeConfig


def _build_concrete_config(host_isolation: str = "strict") -> Config:
    """Construct a Config without YAML I/O."""
    return Config(
        ollama=OllamaConfig(),
        mcp_server=McpServerConfig(command="true", args=[]),
        test_code=TestCodeConfig(generated_root="tests/test_code/_generated"),
        tools={},
        host_isolation=host_isolation,  # type: ignore[arg-type]
    )


def _unwrap(fixture):
    """Unwrap a pytest fixture object to the underlying async generator function."""
    return fixture._get_wrapped_function()  # type: ignore[attr-defined]


def test_isolated_home_takes_mcp_config_dependency() -> None:
    """The fixture signature must accept ``mcp_config`` so it can branch on mode."""
    fn = _unwrap(_isolated_home_fixture)
    sig = inspect.signature(fn)
    assert "mcp_config" in sig.parameters, (
        "_isolated_home must take mcp_config as a parameter so it can branch "
        "on mcp_config.host_isolation. Current signature: "
        f"{sig!r}"
    )


@pytest.mark.asyncio
async def test_isolated_home_passthrough_yields_none() -> None:
    """Under passthrough mode the fixture yields ``None`` and skips tempdir alloc."""
    fn = _unwrap(_isolated_home_fixture)
    cfg = _build_concrete_config(host_isolation="passthrough")

    agen = fn(mcp_config=cfg)
    try:
        value = await agen.__anext__()
        assert value is None, (
            "Under host_isolation='passthrough', _isolated_home must yield None "
            "(short-circuit -- no tempdir allocated). Got: "
            f"{value!r}"
        )
    finally:
        # Drain generator so the AsyncExitStack inside (if any) closes cleanly.
        with pytest.raises(StopAsyncIteration):
            await agen.__anext__()


@pytest.mark.asyncio
async def test_isolated_home_strict_yields_path() -> None:
    """Under strict mode (default) the fixture yields a real Path."""
    fn = _unwrap(_isolated_home_fixture)
    cfg = _build_concrete_config(host_isolation="strict")

    agen = fn(mcp_config=cfg)
    try:
        value = await agen.__anext__()
        assert isinstance(value, Path), (
            "Under host_isolation='strict', _isolated_home must yield a Path. "
            f"Got: {value!r} (type={type(value).__name__})"
        )
        assert value.exists(), (
            "The yielded Path must point at a real tempdir that exists on disk."
        )
    finally:
        with pytest.raises(StopAsyncIteration):
            await agen.__anext__()


def test_mcp_client_fixture_routes_through_dispatcher() -> None:
    """The ``mcp_client`` fixture's spawn site calls ``_build_subprocess_env``
    with the mode and the (possibly-None) isolated_home Path -- NOT the legacy
    ``_build_isolated_env`` direct call.
    """
    src = Path(__file__).resolve().parents[3] / "src" / "mcp_test_framework" / "fixtures.py"
    text = src.read_text(encoding="utf-8")
    assert "_build_subprocess_env(mcp_config.host_isolation" in text, (
        "mcp_client fixture body must route through "
        "_build_subprocess_env(mcp_config.host_isolation, _isolated_home). "
        "Direct call to _build_isolated_env in this file is the legacy path."
    )
    assert "_build_isolated_env(" not in text, (
        "fixtures.py must not call _build_isolated_env directly anymore; "
        "the dispatcher in _isolation.py is the only entry point."
    )


def test_fixtures_imports_dispatcher_not_legacy_builder() -> None:
    """The import line must reference ``_build_subprocess_env`` (not the legacy
    ``_build_isolated_env``).
    """
    src = Path(__file__).resolve().parents[3] / "src" / "mcp_test_framework" / "fixtures.py"
    text = src.read_text(encoding="utf-8")
    assert "from mcp_test_framework._isolation import _build_subprocess_env" in text, (
        "fixtures.py must import _build_subprocess_env from the isolation "
        "primitive module."
    )
