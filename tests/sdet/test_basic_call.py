"""Phase 18 SDET sanity: tool().call() end-to-end via mcp_session.

Per Phase 18 CONTEXT.md (Claude's Discretion) -- a minimum-viable scenario
exercising one tool through the SDET wrapper. This is the verification
harness that proves the whole Phase 18 surface composes end-to-end:

  1. The mcp_session fixture activates the homelab_mcp registry (D-02).
  2. tool("list_registered_servers") resolves through _ACTIVE_SLUG /
     _REGISTRIES (Phase 17 dispatch).
  3. .call(params) makes a real MCP wire call (D-08 + D-07 wiring from
     Plan 18-02).
  4. The response is constructed via CODEGEN-04's uniform .raw / .data /
     .text / .is_error contract.

Phase 19 will ship the real VM-lifecycle dogfood scenario; Phase 18's
sanity is a single tool call that doesn't require homelab-mcp's stateful
subsystems (Proxmox/Ansible/etc).

The chosen tool MUST be:
  - In the generated homelab_mcp registry.
  - Constructible with no required params (so the test runs without
    homelab-specific setup).
  - Read-only / idempotent (no side effects on real infrastructure).

Picked: list_registered_servers -- exists in the registry, all params
optional (only `active_only: bool = True`), read-only.

For the negative-path test (Pydantic validates BEFORE the wire) we switch
to a tool with a known-typed required field so we can demonstrate
ValidationError at construction time without touching the wire.

# tool: get_proxmox_vm_status chosen for known-typed field vmid:int
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_test_framework.sdet import ToolResponse, mcp_session, tool  # noqa: F401


@pytest.mark.asyncio(loop_scope="session")
async def test_basic_tool_round_trip(mcp_session) -> None:
    """SDET-01/03/04 + CODEGEN-05: tool().call() returns a typed response."""
    wrapper = tool("list_registered_servers")
    # Construct params with no required fields (verified against generated class --
    # only `active_only: bool = True` is defined, defaulted).
    params = wrapper.params_cls()
    response = await wrapper.call(params)
    # CODEGEN-04 uniform surface.
    assert isinstance(response, ToolResponse)
    assert isinstance(response, wrapper.response_cls)
    assert response.is_error is False


@pytest.mark.asyncio(loop_scope="session")
async def test_invalid_params_caught_before_wire(mcp_session) -> None:
    """SDET-04 + CODEGEN-02: Pydantic validation fires at Params construction.

    Constructing the Params class with a type-violating field raises
    Pydantic's ValidationError SYNCHRONOUSLY -- before any await touches
    the wire. This is the contract that lets SDETs trust the typed surface.

    We use get_proxmox_vm_status because ListRegisteredServersParams only
    defines an optional bool field; we need a non-trivial typed required
    field (vmid: int) to demonstrate the validation gate without
    accidentally accepting coerced input.
    """
    wrapper = tool("get_proxmox_vm_status")
    # vmid is `int` (required); passing a string that is not coercible to int
    # raises ValidationError at construction. We never reach .call().
    with pytest.raises((ValidationError, TypeError)):
        wrapper.params_cls(node="pve", vmid="not an int")  # type: ignore[arg-type]
