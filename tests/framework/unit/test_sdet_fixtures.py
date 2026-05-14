"""Unit tests for mcp_test_framework.sdet.session (Phase 18 SDET-03/04).

Pins D-01/D-02/D-03 (Phase 18 CONTEXT.md):
  - D-01: mcp_session is a session-scoped pytest-asyncio fixture aliasing the
    framework-wide ``mcp_client`` fixture. No duplicate stdio_client /
    ClientSession lifecycle introduced.
  - D-02: registry activation lives in the fixture body. 5 steps: read
    ``serverInfo.name`` from the live client, slugify via ``_slugs.server_slug``,
    load ``<cfg.sdet.generated_root>/<slug>/__init__.py`` via
    ``importlib.util.spec_from_file_location`` (Phase 21.1 RELOC-02; was
    package-namespace ``importlib.import_module`` pre-21.1), read
    ``_REGISTRY``, install into ``_REGISTRIES[slug]`` + set
    ``_ACTIVE_SLUG`` + set ``_ACTIVE_CLIENT``. On teardown restore prior state
    and pop the registry entry.
  - D-03: missing generated package (slug dir / __init__.py absent under
    ``cfg.sdet.generated_root``) triggers
    ``_pytest_exit_operator_tone(returncode=2)`` with operator-readable
    message naming the slug, ``gen-sdet-classes``, and ``--sdet``.

The fixture body's mutations are SYNC (spec_from_file_location load + dict
mutation + attribute assignment); no anyio CancelScope is opened across the
yield (Phase 04.1 invariant preserved).
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from mcp_test_framework.sdet import _tool_factory as tf
from mcp_test_framework.sdet.response import ToolResponse


# --- Helpers --------------------------------------------------------------


class _FakeParams(BaseModel):
    name: str


class _FakeResponse(ToolResponse):
    pass


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Tests mutate module-level _tool_factory state; reset to prevent bleed."""
    saved_slug = tf._ACTIVE_SLUG
    saved_client = tf._ACTIVE_CLIENT
    saved_registries = dict(tf._REGISTRIES)
    yield
    tf._ACTIVE_SLUG = saved_slug
    tf._ACTIVE_CLIENT = saved_client
    tf._REGISTRIES.clear()
    tf._REGISTRIES.update(saved_registries)


def _make_fake_client(server_name: str = "homelab-mcp") -> MagicMock:
    """Build a MagicMock impersonating a session-scoped McpTestClient.

    The session.py fixture reads ``mcp_client.server_info.name`` (the public
    accessor added in Plan 18-03's Rule-3 deviation; see SUMMARY). The mock
    exposes ``server_info.name`` directly.
    """
    client = MagicMock()
    client.server_info = SimpleNamespace(name=server_name)
    return client


# Phase 21.1 RELOC-03: synthetic codegen harness for mock-based fixture tests.
# Lifted from tests/framework/unit/test_codegen_integration_mock.py to keep the
# test self-contained without importing private helpers from another test file.

from pathlib import Path  # noqa: E402

import yaml  # noqa: E402
from mcp.types import Tool  # noqa: E402

from mcp_test_framework.sdet._codegen import generate as _codegen_generate  # noqa: E402

_SYNTHETIC_SERVER_NAME = "synthetic-mcp"
_SYNTHETIC_SLUG = "synthetic_mcp"
_FIXED_TS = "2026-05-14T12:00:00+00:00"


def _synthetic_tools() -> list[Tool]:
    """Single-tool synthetic fixture -- minimal _REGISTRY for activation tests."""
    return [
        Tool(
            name="echo_message",
            description="Echo the message back.",
            inputSchema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
        ),
    ]


def _build_synthetic_slug_dir(tmp_path: Path) -> Path:
    """Run codegen into tmp_path; return tmp_path/<synthetic_slug>."""
    _codegen_generate(
        server_name=_SYNTHETIC_SERVER_NAME,
        server_version="0.0.0",
        tools=_synthetic_tools(),
        out_root=tmp_path,
        timestamp=_FIXED_TS,
    )
    slug_dir = tmp_path / _SYNTHETIC_SLUG
    assert slug_dir.is_dir(), f"codegen did not create {slug_dir}"
    return slug_dir


def _write_config_with_generated_root(tmp_path: Path, generated_root: Path) -> Path:
    """Write a minimal v2 config.yaml with sdet.generated_root pinned.

    Returns the YAML path; caller must monkeypatch MCPTF_CONFIG_FILE to it so
    the bare ``Config()`` call inside ``mcp_session`` picks it up.
    """
    yaml_path = tmp_path / "_test_config.yaml"
    yaml_path.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "mcp_server": {"command": "uvx", "args": ["x"], "timeout_seconds": 30},
                "sdet": {"generated_root": str(generated_root)},
            }
        ),
        encoding="utf-8",
    )
    return yaml_path


# --- D-01: fixture shape ---------------------------------------------------


def test_mcp_session_is_pytest_asyncio_session_scoped_fixture() -> None:
    """D-01: decorator must be @pytest_asyncio.fixture(loop_scope='session', scope='session')."""
    from mcp_test_framework.sdet.session import mcp_session

    # pytest >=8 / pytest_asyncio >=1: FixtureFunctionDefinition exposes the
    # FixtureFunctionMarker on `_fixture_function_marker` and the async loop
    # scope on `_loop_scope`.
    marker = getattr(mcp_session, "_fixture_function_marker", None)
    assert marker is not None, (
        "mcp_session must be a pytest fixture (missing _fixture_function_marker)"
    )
    assert marker.scope == "session", f"expected scope='session', got {marker.scope!r}"
    loop_scope = getattr(mcp_session, "_loop_scope", None)
    assert loop_scope == "session", f"expected loop_scope='session', got {loop_scope!r}"


def test_mcp_session_signature_depends_on_mcp_client() -> None:
    """D-01: the fixture parameter name is ``mcp_client`` (pytest dependency by name)."""
    from mcp_test_framework.sdet.session import mcp_session

    # pytest_asyncio wraps the fixture; FixtureFunctionDefinition exposes the
    # original via `_get_wrapped_function()`.
    func = _unwrap(mcp_session)
    sig = inspect.signature(func)
    assert "mcp_client" in sig.parameters, (
        f"mcp_session must depend on mcp_client (params: {list(sig.parameters)})"
    )


def test_mcp_session_module_imports_cleanly() -> None:
    """Smoke import — catches circular imports + missing dependencies."""
    from mcp_test_framework.sdet.session import mcp_session  # noqa: F401


# --- D-02: registry activation around yield -------------------------------


def _unwrap(fixture):
    """Get the underlying async generator function from a pytest-asyncio fixture."""
    get_wrapped = getattr(fixture, "_get_wrapped_function", None)
    if get_wrapped is not None:
        return get_wrapped()
    return getattr(fixture, "__wrapped__", fixture)


async def _run_fixture(mcp_session_func, client) -> tuple[object, dict]:
    """Drive the async generator fixture and capture state at yield time.

    Returns (yielded_value, state_snapshot_at_yield_time).
    """
    func = _unwrap(mcp_session_func)
    agen = func(client)
    yielded = await agen.__anext__()
    # Snapshot registries by deep-copying the dict so post-teardown asserts
    # against the yield-time state still see the activated synthetic slug.
    snapshot = {
        "_ACTIVE_SLUG": tf._ACTIVE_SLUG,
        "_ACTIVE_CLIENT": tf._ACTIVE_CLIENT,
        "_REGISTRIES_keys": set(tf._REGISTRIES.keys()),
        "_REGISTRIES_snapshot": dict(tf._REGISTRIES),
    }
    # finish teardown
    with pytest.raises(StopAsyncIteration):
        await agen.__anext__()
    return yielded, snapshot


@pytest.mark.asyncio
async def test_mcp_session_activates_registry_on_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-02 (Phase 21.1 RELOC-03 reworked): on entry, _ACTIVE_SLUG /
    _ACTIVE_CLIENT / _REGISTRIES[slug] are set against the spec-loaded
    synthetic package."""
    from mcp_test_framework.sdet.session import mcp_session

    slug_dir = _build_synthetic_slug_dir(tmp_path)
    yaml_path = _write_config_with_generated_root(tmp_path, tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(yaml_path))

    client = _make_fake_client(_SYNTHETIC_SERVER_NAME)
    yielded, snapshot = await _run_fixture(mcp_session, client)

    assert yielded is client, "fixture must yield the mcp_client argument"
    assert snapshot["_ACTIVE_SLUG"] == _SYNTHETIC_SLUG
    assert snapshot["_ACTIVE_CLIENT"] is client
    assert _SYNTHETIC_SLUG in snapshot["_REGISTRIES_keys"]
    # _REGISTRY identity: the spec-loaded package's _REGISTRY attr is what's
    # installed under the synthetic slug. Snapshot at yield-time confirms
    # the synthetic tool was registered before teardown popped the entry.
    registry = snapshot["_REGISTRIES_snapshot"].get(_SYNTHETIC_SLUG)
    assert registry is not None
    assert "echo_message" in registry
    # slug_dir is the directory the spec loader used; pinning it for clarity.
    assert slug_dir.is_dir()


@pytest.mark.asyncio
async def test_mcp_session_restores_prior_state_on_teardown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-02 step 7 (Phase 21.1 RELOC-03 reworked): teardown restores prior
    _ACTIVE_SLUG / _ACTIVE_CLIENT and pops the synthetic registry."""
    from mcp_test_framework.sdet.session import mcp_session

    _build_synthetic_slug_dir(tmp_path)
    yaml_path = _write_config_with_generated_root(tmp_path, tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(yaml_path))

    # Set non-default prior state
    prior_client_marker = MagicMock(name="prior_client")
    tf._ACTIVE_SLUG = "prior_slug"
    tf._ACTIVE_CLIENT = prior_client_marker
    tf._REGISTRIES["prior_slug"] = {"x": (_FakeParams, _FakeResponse)}

    client = _make_fake_client(_SYNTHETIC_SERVER_NAME)
    await _run_fixture(mcp_session, client)

    # After teardown: prior state restored, synthetic registry popped.
    assert tf._ACTIVE_SLUG == "prior_slug"
    assert tf._ACTIVE_CLIENT is prior_client_marker
    assert _SYNTHETIC_SLUG not in tf._REGISTRIES
    assert "prior_slug" in tf._REGISTRIES  # prior entry untouched


# --- D-03: fail-loud on ModuleNotFoundError --------------------------------


@pytest.mark.asyncio
async def test_mcp_session_fail_loud_on_missing_generated_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-03 (Phase 21.1 RELOC-03 reworked): missing slug dir under
    cfg.sdet.generated_root triggers pytest.exit(returncode=2) with
    operator-tone message naming the slug, gen-sdet-classes, and --sdet."""
    from mcp_test_framework.sdet.session import mcp_session

    # Point sdet.generated_root at an empty tmp_path; no slug dir exists.
    empty_root = tmp_path / "empty_root"
    empty_root.mkdir()
    yaml_path = _write_config_with_generated_root(tmp_path, empty_root)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(yaml_path))

    client = _make_fake_client("missing-server")
    func = _unwrap(mcp_session)
    agen = func(client)
    with pytest.raises(pytest.exit.Exception) as exc_info:
        await agen.__anext__()

    assert exc_info.value.returncode == 2
    message = str(exc_info.value)
    assert "No generated SDET classes" in message
    assert "missing_server" in message  # slug normalization
    assert "gen-sdet-classes" in message
    assert "--sdet" in message


# --- Phase 04.1 invariant guard -------------------------------------------


def test_session_module_opens_no_anyio_cancel_scope() -> None:
    """Phase 04.1: session.py must NOT open a new anyio cancel scope.

    Mirrors the plan's acceptance criterion:
      ``grep -cE "with anyio\\.|CancelScope" returns 0``.
    """
    import inspect as _inspect
    import re

    from mcp_test_framework.sdet import session as session_mod

    src = _inspect.getsource(session_mod)
    matches = re.findall(r"with anyio\.|CancelScope", src)
    assert matches == [], (
        f"session.py must not introduce anyio cancel scopes; found: {matches}"
    )


# --- Plan 18-04 public surface (__all__ contract) -------------------------


class TestPublicSurface:
    """Phase 18 Plan 18-04 -- canonical public import surface for SDET tests.

    Pins the four-symbol __all__ contract so future plans don't widen the
    surface speculatively. Symbols added here MUST also land in:
      - src/mcp_test_framework/sdet/__init__.py:__all__
      - docs/sdet.md (Phase 21 DOC-SDET)
    """

    def test_canonical_imports_resolve(self) -> None:
        """Plan 18-04: the four SDET symbols import from the package root."""
        from mcp_test_framework.sdet import (
            ToolCallError,
            ToolResponse,
            mcp_session,
            tool,
        )

        assert ToolCallError is not None
        assert ToolResponse is not None
        assert mcp_session is not None
        assert tool is not None

    def test_all_lists_exact_four_names(self) -> None:
        """Plan 18-04: __all__ is exactly the four-name set (no drift)."""
        from mcp_test_framework.sdet import __all__

        assert set(__all__) == {
            "ToolCallError",
            "ToolResponse",
            "mcp_session",
            "tool",
        }

    def test_all_is_alphabetical(self) -> None:
        """Plan 18-04: __all__ is alphabetically ordered for stable reads."""
        from mcp_test_framework.sdet import __all__

        assert list(__all__) == sorted(__all__)

    def test_internal_symbols_not_re_exported(self) -> None:
        """Plan 18-04: internal helpers / module-state slots / ToolWrapper
        are NOT re-exported through the package barrel."""
        import mcp_test_framework.sdet as sdet_pkg

        # These exist in sibling modules but must not be on the barrel.
        for name in (
            "_extract_code_message",  # errors.py internal helper
            "_REGISTRIES",  # _tool_factory.py module state
            "_ACTIVE_SLUG",  # _tool_factory.py module state
            "_ACTIVE_CLIENT",  # _tool_factory.py module state (Plan 18-02)
            "ToolWrapper",  # _tool_factory.py return type detail
            "server_slug",  # _slugs.py codegen helper
        ):
            assert not hasattr(sdet_pkg, name), (
                f"{name!r} must NOT be re-exported through "
                f"mcp_test_framework.sdet barrel"
            )

    def test_tool_call_error_is_plain_exception(self) -> None:
        """Plan 18-04 + Plan 18-01: re-exported ToolCallError is the typed
        exception (sanity: re-export points at the right symbol)."""
        from mcp_test_framework.sdet import ToolCallError
        from mcp_test_framework.sdet.errors import (
            ToolCallError as _ToolCallErrorDirect,
        )

        assert ToolCallError is _ToolCallErrorDirect
        assert issubclass(ToolCallError, Exception)
