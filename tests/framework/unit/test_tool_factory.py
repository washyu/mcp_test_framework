"""Unit tests for mcp_test_framework.sdet._tool_factory (CODEGEN-05 seam).

Pins:
  - tool(name) returns a ToolWrapper with correct params_cls / response_cls
  - tool(name) error semantics: no-active-registry, unknown-name
  - ToolWrapper.call() raises RuntimeError when _ACTIVE_CLIENT is unset
    (mcp_session fixture not entered) -- Phase 18 SDET-03.
  - Module-level _REGISTRIES / _ACTIVE_SLUG / _ACTIVE_CLIENT slots are reset
    between tests.
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


class _FakeParamsWithOptional(BaseModel):
    """Phase 24: fixture for exclude_unset semantics tests.

    Mirrors the upstream shape that triggered the homelab-mcp inputSchema bug:
    one required field + one optional field with `None` default. The framework's
    `tool().call()` must NOT emit `cdrom: null` on the wire when the SDET never
    set it (`exclude_unset=True`); but if the SDET explicitly writes
    `cdrom=None`, the wrapper must put `null` on the wire (SEED-022: user
    intent, not value, is the discriminator).
    """

    name: str
    cdrom: str | None = None


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Tests mutate module-level state; reset on teardown to prevent bleed."""
    saved_active = tf._ACTIVE_SLUG
    saved_registries = dict(tf._REGISTRIES)
    saved_client = tf._ACTIVE_CLIENT
    yield
    tf._ACTIVE_SLUG = saved_active
    tf._REGISTRIES.clear()
    tf._REGISTRIES.update(saved_registries)
    tf._ACTIVE_CLIENT = saved_client


def test_imports_succeed() -> None:
    """Plain importability check -- catches import-cycle regressions."""
    from mcp_test_framework.sdet._tool_factory import (  # noqa: F401
        ToolWrapper,
        tool,
        _ACTIVE_SLUG,
        _ACTIVE_CLIENT,
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
async def test_call_raises_runtime_error_when_no_active_client() -> None:
    """Phase 18 SDET-03: .call() must raise RuntimeError when _ACTIVE_CLIENT is None,
    naming the missing `mcp_session` fixture so the operator can fix it."""
    tf._ACTIVE_SLUG = "homelab_mcp"
    tf._REGISTRIES["homelab_mcp"] = {"create_vm": (_FakeParams, _FakeResponse)}
    tf._ACTIVE_CLIENT = None
    wrapper = tool("create_vm")
    with pytest.raises(RuntimeError) as exc:
        await wrapper.call(_FakeParams(name="x"))
    msg = str(exc.value)
    assert "no active MCP client" in msg
    assert "mcp_session" in msg
    assert "tests/sdet/" in msg


@pytest.mark.asyncio
async def test_call_success_path_returns_response_cls() -> None:
    """Phase 18 SDET-03: with _ACTIVE_CLIENT set and result.isError=False,
    .call() must return an instance of self.response_cls wrapping the result."""
    from mcp.types import CallToolResult, TextContent

    tf._ACTIVE_SLUG = "homelab_mcp"
    tf._REGISTRIES["homelab_mcp"] = {"create_vm": (_FakeParams, _FakeResponse)}

    fake_result = CallToolResult(
        content=[TextContent(type="text", text="ok")],
        isError=False,
    )

    class _StubClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        async def call_tool(self, name: str, arguments: dict):
            self.calls.append((name, arguments))
            return fake_result

    stub = _StubClient()
    tf._ACTIVE_CLIENT = stub  # type: ignore[assignment]
    wrapper = tool("create_vm")
    out = await wrapper.call(_FakeParams(name="hello"))
    assert isinstance(out, _FakeResponse)
    assert out.raw is fake_result
    # call_tool was awaited with the tool name + the JSON-serialized params.
    assert stub.calls == [("create_vm", {"name": "hello"})]


@pytest.mark.asyncio
async def test_call_error_path_raises_tool_call_error() -> None:
    """Phase 18 SDET-03/UI-02: result.isError=True raises ToolCallError with
    .tool/.code/.message/.raw populated via _extract_code_message."""
    from mcp.types import CallToolResult

    from mcp_test_framework.sdet.errors import ToolCallError

    tf._ACTIVE_SLUG = "homelab_mcp"
    tf._REGISTRIES["homelab_mcp"] = {"create_vm": (_FakeParams, _FakeResponse)}

    fake_result = CallToolResult(
        content=[],
        isError=True,
        structuredContent={"code": "X", "message": "Y"},
    )

    class _StubClient:
        async def call_tool(self, name: str, arguments: dict):
            return fake_result

    tf._ACTIVE_CLIENT = _StubClient()  # type: ignore[assignment]
    wrapper = tool("create_vm")
    with pytest.raises(ToolCallError) as exc:
        await wrapper.call(_FakeParams(name="x"))
    err = exc.value
    assert err.tool == "create_vm"
    assert err.code == "X"
    assert err.message == "Y"
    assert err.raw is fake_result


@pytest.mark.asyncio
async def test_call_serializes_params_with_mode_json_and_exclude_unset() -> None:
    """Phase 18 CONTEXT D-08 + 18-PATTERNS: params.model_dump must be called
    with mode='json' (wire-safe). Spies on a Pydantic subclass that records
    the kwargs passed to model_dump (Pydantic blocks instance-attr override,
    so we use a subclass override instead). Phase 24 SERIALIZER-01: ALSO
    assert exclude_unset=True so the chosen implementation choice is locked
    alongside mode='json'."""
    from mcp.types import CallToolResult, TextContent

    captured_kwargs: dict = {}

    class _SpyParams(BaseModel):
        name: str

        def model_dump(self, **kwargs):  # type: ignore[override]
            captured_kwargs.update(kwargs)
            return super().model_dump(**kwargs)

    tf._ACTIVE_SLUG = "homelab_mcp"
    tf._REGISTRIES["homelab_mcp"] = {"create_vm": (_SpyParams, _FakeResponse)}

    fake_result = CallToolResult(
        content=[TextContent(type="text", text="ok")],
        isError=False,
    )

    class _StubClient:
        async def call_tool(self, name: str, arguments: dict):
            return fake_result

    tf._ACTIVE_CLIENT = _StubClient()  # type: ignore[assignment]
    wrapper = tool("create_vm")
    await wrapper.call(_SpyParams(name="x"))
    assert captured_kwargs.get("mode") == "json", (
        f"expected model_dump(mode='json'); got kwargs={captured_kwargs!r}"
    )
    assert captured_kwargs.get("exclude_unset") is True, (
        f"expected model_dump(exclude_unset=True) -- Phase 24 SERIALIZER-01; "
        f"got kwargs={captured_kwargs!r}"
    )


@pytest.mark.asyncio
async def test_call_omits_unset_optional_field_from_wire_arguments() -> None:
    """Phase 24 SERIALIZER-01: optional Pydantic field the SDET never set must NOT
    appear in the `arguments` dict the wrapper passes to McpTestClient.call_tool.

    This is the contract that resolves the framework-side contribution to the
    homelab-mcp inputSchema bug (`Input validation error: None is not of type
    'string'`). SEED-022 preserved: see the explicit-None test below for the
    user-intent escape hatch.
    """
    from mcp.types import CallToolResult, TextContent

    tf._ACTIVE_SLUG = "homelab_mcp"
    tf._REGISTRIES["homelab_mcp"] = {
        "create_vm": (_FakeParamsWithOptional, _FakeResponse)
    }

    fake_result = CallToolResult(
        content=[TextContent(type="text", text="ok")],
        isError=False,
    )

    class _StubClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        async def call_tool(self, name: str, arguments: dict):
            self.calls.append((name, arguments))
            return fake_result

    stub = _StubClient()
    tf._ACTIVE_CLIENT = stub  # type: ignore[assignment]
    wrapper = tool("create_vm")
    # cdrom NOT passed -- SDET did not set it.
    await wrapper.call(_FakeParamsWithOptional(name="x"))
    assert len(stub.calls) == 1
    sent_args = stub.calls[0][1]
    assert "cdrom" not in sent_args, (
        f"expected unset optional `cdrom` to be omitted from wire arguments; "
        f"got {sent_args!r}"
    )
    assert sent_args == {"name": "x"}


@pytest.mark.asyncio
async def test_call_serializes_explicit_none_to_wire_null() -> None:
    """Phase 24 SERIALIZER-01 / SEED-022: when the SDET EXPLICITLY passes
    `field=None`, the wrapper must still put `null` on the wire. This is the
    user-intent escape hatch -- an SDET testing the server's null-handling path
    sets the attribute explicitly and the framework respects that.
    """
    from mcp.types import CallToolResult, TextContent

    tf._ACTIVE_SLUG = "homelab_mcp"
    tf._REGISTRIES["homelab_mcp"] = {
        "create_vm": (_FakeParamsWithOptional, _FakeResponse)
    }

    fake_result = CallToolResult(
        content=[TextContent(type="text", text="ok")],
        isError=False,
    )

    class _StubClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        async def call_tool(self, name: str, arguments: dict):
            self.calls.append((name, arguments))
            return fake_result

    stub = _StubClient()
    tf._ACTIVE_CLIENT = stub  # type: ignore[assignment]
    wrapper = tool("create_vm")
    # cdrom EXPLICITLY set to None -- SDET wants null on the wire.
    await wrapper.call(_FakeParamsWithOptional(name="x", cdrom=None))
    assert len(stub.calls) == 1
    sent_args = stub.calls[0][1]
    assert "cdrom" in sent_args, (
        f"expected explicit `cdrom=None` to be PRESENT on wire; got {sent_args!r}"
    )
    assert sent_args["cdrom"] is None
    assert sent_args == {"name": "x", "cdrom": None}


@pytest.mark.asyncio
async def test_call_serializes_explicit_value_unchanged() -> None:
    """Phase 24 SERIALIZER-01: optional field set to a real value passes through
    unchanged -- regression against an over-aggressive future change."""
    from mcp.types import CallToolResult, TextContent

    tf._ACTIVE_SLUG = "homelab_mcp"
    tf._REGISTRIES["homelab_mcp"] = {
        "create_vm": (_FakeParamsWithOptional, _FakeResponse)
    }

    fake_result = CallToolResult(
        content=[TextContent(type="text", text="ok")],
        isError=False,
    )

    class _StubClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        async def call_tool(self, name: str, arguments: dict):
            self.calls.append((name, arguments))
            return fake_result

    stub = _StubClient()
    tf._ACTIVE_CLIENT = stub  # type: ignore[assignment]
    wrapper = tool("create_vm")
    await wrapper.call(_FakeParamsWithOptional(name="x", cdrom="/iso/local.iso"))
    assert len(stub.calls) == 1
    sent_args = stub.calls[0][1]
    assert sent_args == {"name": "x", "cdrom": "/iso/local.iso"}


def test_active_client_module_attribute_defaults_to_none() -> None:
    """Phase 18 SDET-03: the _ACTIVE_CLIENT module attribute exists and is None
    by default (only the mcp_session fixture mutates it at runtime)."""
    # Cannot inspect the live value because the autouse reset fixture saves
    # whatever is current; instead, import a fresh handle and assert the
    # attribute is the literal None set at module load.
    import importlib

    import mcp_test_framework.sdet._tool_factory as tf_fresh

    # The attribute exists.
    assert hasattr(tf_fresh, "_ACTIVE_CLIENT")
    # And its default is None per the module-level slot declaration.
    # Re-reading the module source: confirm the slot still defaults to None
    # by checking the bytecode-level constant on a freshly imported clone
    # (importlib.reload would clobber the autouse-fixture save; we just
    # read the source-level default via inspect).
    import inspect

    src = inspect.getsource(tf_fresh)
    assert "_ACTIVE_CLIENT" in src
    assert '_ACTIVE_CLIENT: "McpTestClient | None" = None' in src
    _ = importlib  # silence unused import (kept for clarity of intent)


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
