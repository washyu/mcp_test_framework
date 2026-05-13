"""Unit tests for mcp_test_framework.sdet._tool_factory (CODEGEN-05 seam).

Pins:
  - tool(name) returns a ToolWrapper with correct params_cls / response_cls
  - tool(name) error semantics: no-active-registry, unknown-name
  - ToolWrapper.call() raises NotImplementedError pointing at Phase 18
  - Module-level _REGISTRIES / _ACTIVE_SLUG slots are reset between tests
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from mcp_test_framework.sdet import _tool_factory as tf
from mcp_test_framework.sdet._tool_factory import ToolWrapper, tool
from mcp_test_framework.sdet.response import ToolResponse


# --- Fake classes for the registry ----------------------------------------


class _FakeParams(BaseModel):
    name: str


class _FakeResponse(ToolResponse):
    pass


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Tests mutate module-level state; reset on teardown to prevent bleed."""
    saved_active = tf._ACTIVE_SLUG
    saved_registries = dict(tf._REGISTRIES)
    yield
    tf._ACTIVE_SLUG = saved_active
    tf._REGISTRIES.clear()
    tf._REGISTRIES.update(saved_registries)


def test_imports_succeed() -> None:
    """Plain importability check -- catches import-cycle regressions."""
    from mcp_test_framework.sdet._tool_factory import (  # noqa: F401
        ToolWrapper,
        tool,
        _ACTIVE_SLUG,
        _REGISTRIES,
    )


def test_tool_raises_when_no_active_registry() -> None:
    """Phase 17: with no fixture activating a registry, tool(name) fails loud."""
    tf._ACTIVE_SLUG = None
    with pytest.raises(RuntimeError, match="mcp_session"):
        tool("create_vm")


def test_tool_returns_wrapper_for_registered_name() -> None:
    tf._ACTIVE_SLUG = "homelab_mcp"
    tf._REGISTRIES["homelab_mcp"] = {"create_vm": (_FakeParams, _FakeResponse)}
    wrapper = tool("create_vm")
    assert isinstance(wrapper, ToolWrapper)
    assert wrapper.name == "create_vm"
    assert wrapper.params_cls is _FakeParams
    assert wrapper.response_cls is _FakeResponse


def test_tool_raises_with_candidate_list_on_unknown_name() -> None:
    tf._ACTIVE_SLUG = "homelab_mcp"
    tf._REGISTRIES["homelab_mcp"] = {
        "create_vm": (_FakeParams, _FakeResponse),
        "delete_vm": (_FakeParams, _FakeResponse),
    }
    with pytest.raises(KeyError) as exc:
        tool("modify_vm")
    msg = str(exc.value)
    assert "modify_vm" in msg
    assert "create_vm" in msg
    assert "delete_vm" in msg
    assert "homelab_mcp" in msg
    assert "gen-sdet-classes" in msg  # next-step hint


@pytest.mark.asyncio
async def test_call_raises_not_implemented_with_phase18_reference() -> None:
    """Phase 17 ships only the seam: .call() must raise NotImplementedError
    naming the missing Phase 18 fixture."""
    tf._ACTIVE_SLUG = "homelab_mcp"
    tf._REGISTRIES["homelab_mcp"] = {"create_vm": (_FakeParams, _FakeResponse)}
    wrapper = tool("create_vm")
    with pytest.raises(NotImplementedError) as exc:
        await wrapper.call(_FakeParams(name="x"))
    msg = str(exc.value)
    assert "Phase 18" in msg
    assert "mcp_session" in msg


def test_tool_wrapper_is_generic() -> None:
    """Smoke-test: TypeVars exist and ToolWrapper is Generic so pyright sees
    `tool("name").call(Params)` returning the right Response subtype."""
    # Just check the class is subscriptable (Generic[P, R]).
    parameterized = ToolWrapper[_FakeParams, _FakeResponse]
    assert parameterized is not None


def test_state_resets_between_tests_part_a() -> None:
    """Pair with part_b: prove _reset_module_state fixture isolates state."""
    tf._ACTIVE_SLUG = "test_slug"
    tf._REGISTRIES["test_slug"] = {"x": (_FakeParams, _FakeResponse)}


def test_state_resets_between_tests_part_b() -> None:
    """Companion to part_a: at the start of this test, state should be clean."""
    assert (
        tf._ACTIVE_SLUG is None
        or tf._ACTIVE_SLUG != "test_slug"
        or "test_slug" not in tf._REGISTRIES
    )
