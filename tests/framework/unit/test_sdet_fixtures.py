"""Unit tests for mcp_test_framework.sdet.session (Phase 18 SDET-03/04).

Pins D-01/D-02/D-03 (Phase 18 CONTEXT.md):
  - D-01: mcp_session is a session-scoped pytest-asyncio fixture aliasing the
    framework-wide ``mcp_client`` fixture. No duplicate stdio_client /
    ClientSession lifecycle introduced.
  - D-02: registry activation lives in the fixture body. 5 steps: read
    ``serverInfo.name`` from the live client, slugify via ``_slugs.server_slug``,
    ``importlib.import_module(f"mcp_test_framework.sdet.generated.{slug}")``,
    read ``_REGISTRY``, install into ``_REGISTRIES[slug]`` + set
    ``_ACTIVE_SLUG`` + set ``_ACTIVE_CLIENT``. On teardown restore prior state
    and pop the registry entry.
  - D-03: ModuleNotFoundError -> ``_pytest_exit_operator_tone(returncode=2)``
    with operator-readable message naming the slug, ``gen-sdet-classes``, and
    ``--sdet``.

The fixture body's mutations are SYNC (importlib.import_module + dict mutation
+ attribute assignment); no anyio CancelScope is opened across the yield
(Phase 04.1 invariant preserved).
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


# --- D-01: fixture shape ---------------------------------------------------


def test_mcp_session_is_pytest_asyncio_session_scoped_fixture() -> None:
    """D-01: decorator must be @pytest_asyncio.fixture(loop_scope='session', scope='session')."""
    from mcp_test_framework.sdet.session import mcp_session

    marker = getattr(mcp_session, "_pytestfixturefunction", None)
    assert marker is not None, (
        "mcp_session must be a pytest fixture (missing _pytestfixturefunction)"
    )
    assert marker.scope == "session", f"expected scope='session', got {marker.scope!r}"


def test_mcp_session_signature_depends_on_mcp_client() -> None:
    """D-01: the fixture parameter name is ``mcp_client`` (pytest dependency by name)."""
    from mcp_test_framework.sdet.session import mcp_session

    # pytest_asyncio wraps the fixture; the original is on __wrapped__ or directly inspectable.
    func = getattr(mcp_session, "__wrapped__", mcp_session)
    sig = inspect.signature(func)
    assert "mcp_client" in sig.parameters, (
        f"mcp_session must depend on mcp_client (params: {list(sig.parameters)})"
    )


def test_mcp_session_module_imports_cleanly() -> None:
    """Smoke import — catches circular imports + missing dependencies."""
    from mcp_test_framework.sdet.session import mcp_session  # noqa: F401


# --- D-02: registry activation around yield -------------------------------


async def _run_fixture(mcp_session_func, client) -> tuple[object, dict]:
    """Drive the async generator fixture and capture state at yield time.

    Returns (yielded_value, state_snapshot_at_yield_time).
    """
    func = getattr(mcp_session_func, "__wrapped__", mcp_session_func)
    agen = func(client)
    yielded = await agen.__anext__()
    snapshot = {
        "_ACTIVE_SLUG": tf._ACTIVE_SLUG,
        "_ACTIVE_CLIENT": tf._ACTIVE_CLIENT,
        "_REGISTRIES_keys": set(tf._REGISTRIES.keys()),
        "homelab_mcp_registry": tf._REGISTRIES.get("homelab_mcp"),
    }
    # finish teardown
    with pytest.raises(StopAsyncIteration):
        await agen.__anext__()
    return yielded, snapshot


@pytest.mark.asyncio
async def test_mcp_session_activates_registry_on_entry() -> None:
    """D-02: on entry, _ACTIVE_SLUG / _ACTIVE_CLIENT / _REGISTRIES[slug] are set."""
    from mcp_test_framework.sdet.generated import homelab_mcp as gen_mod
    from mcp_test_framework.sdet.session import mcp_session

    client = _make_fake_client("homelab-mcp")
    yielded, snapshot = await _run_fixture(mcp_session, client)

    assert yielded is client, "fixture must yield the mcp_client argument"
    assert snapshot["_ACTIVE_SLUG"] == "homelab_mcp"
    assert snapshot["_ACTIVE_CLIENT"] is client
    assert "homelab_mcp" in snapshot["_REGISTRIES_keys"]
    assert snapshot["homelab_mcp_registry"] is gen_mod._REGISTRY


@pytest.mark.asyncio
async def test_mcp_session_restores_prior_state_on_teardown() -> None:
    """D-02 step 7: teardown restores prior _ACTIVE_SLUG/_ACTIVE_CLIENT and pops registry."""
    from mcp_test_framework.sdet.session import mcp_session

    # Set non-default prior state
    prior_client_marker = MagicMock(name="prior_client")
    tf._ACTIVE_SLUG = "prior_slug"
    tf._ACTIVE_CLIENT = prior_client_marker
    tf._REGISTRIES["prior_slug"] = {"x": (_FakeParams, _FakeResponse)}

    client = _make_fake_client("homelab-mcp")
    await _run_fixture(mcp_session, client)

    # After teardown: prior state restored, homelab_mcp registry popped.
    assert tf._ACTIVE_SLUG == "prior_slug"
    assert tf._ACTIVE_CLIENT is prior_client_marker
    assert "homelab_mcp" not in tf._REGISTRIES
    assert "prior_slug" in tf._REGISTRIES  # prior entry untouched


# --- D-03: fail-loud on ModuleNotFoundError --------------------------------


@pytest.mark.asyncio
async def test_mcp_session_fail_loud_on_missing_generated_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-03: ModuleNotFoundError triggers pytest.exit(returncode=2) with operator message."""
    from mcp_test_framework.sdet import session as session_mod
    from mcp_test_framework.sdet.session import mcp_session

    # Force importlib.import_module to raise ModuleNotFoundError
    def _raise(_name: str):
        raise ModuleNotFoundError(f"No module named {_name!r}")

    monkeypatch.setattr(session_mod.importlib, "import_module", _raise)

    client = _make_fake_client("unknown-server")
    func = getattr(mcp_session, "__wrapped__", mcp_session)
    agen = func(client)
    with pytest.raises(pytest.exit.Exception) as exc_info:
        await agen.__anext__()

    # pytest.exit raises pytest.exit.Exception with returncode + reason; verify shape.
    assert exc_info.value.returncode == 2
    message = str(exc_info.value)
    assert "No generated SDET classes" in message
    assert "unknown_server" in message  # slug normalization
    assert "gen-sdet-classes" in message
    assert "--sdet" in message


# --- Phase 04.1 invariant guard -------------------------------------------


def test_session_module_opens_no_anyio_cancel_scope() -> None:
    """Phase 04.1: session.py source must NOT introduce a new anyio CancelScope."""
    import inspect as _inspect

    from mcp_test_framework.sdet import session as session_mod

    src = _inspect.getsource(session_mod)
    assert "CancelScope" not in src, "session.py must not introduce anyio.CancelScope"
    assert "anyio.fail_after" not in src, "session.py must not introduce anyio.fail_after"
    # `with anyio.` would indicate a new cancel scope context manager.
    assert "with anyio." not in src, "session.py must not open new anyio cancel scopes"
