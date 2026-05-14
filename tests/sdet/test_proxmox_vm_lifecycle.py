"""SDET dogfood: VM lifecycle scenario against live Proxmox.

Exercises Phase 17 generated Proxmox Params + Response classes through
Phase 18 mcp_session + tool() + ToolCallError surfaces. Module-scope
yield fixture creates a VM, yields a typed scenario state, and deletes
the VM in its finalizer -- proving the cleanup-on-failure contract is
real end-to-end against real infrastructure.

Pinned conventions:
  - VMID range: read from the homelab.proxmox config block
    (dogfood_vmid_range, default [9990, 9999]).
  - Name prefix: mcptf-dogfood-<ISO8601 UTC seconds> (e.g.
    mcptf-dogfood-20260513T223045Z).
  - Best-effort teardown sweeps any stranded mcptf-dogfood-* in the
    configured range from prior crashed runs via list_proxmox_resources;
    sweep failures logged, never raise.
  - Black-box rule: imports only from mcp_test_framework.* -- never
    from homelab-mcp source.

Cross-file scenario ordering recipe:
  See .planning/recipes/pytest-order.md for the worked two-file example
  using @pytest.mark.order(N). Single-file scenarios (like this one)
  rely on pytest's file-order collection -- no marker needed. The
  framework does NOT ship pytest-order as a dependency.

Live-environment requirements:
  - homelab-mcp reachable via the configured `mcp_server.command`.
  - Proxmox reachable from the host running homelab-mcp.
  - Operator's Proxmox credentials registered in homelab-mcp.
  - MCPTF_DOGFOOD_PROXMOX_HOST set to a reachable Proxmox host name.
  - MCPTF_DOGFOOD_PROXMOX_NODE defaults to "pve" (override if your
    cluster uses a different node name).
  On an unreachable Proxmox the scenario fails LOUD with ToolCallError.
  A subsequent phase introduces `requires_homelab` for clean SKIPs;
  this scenario fails fast in the interim.

# tool: create_proxmox_vm (D-01 -- live VM creation)
# tool: manage_proxmox_vm (D-02 -- CPU 1 -> 2 modify step, NO substitute)
# tool: delete_proxmox_vm (D-01 -- live VM teardown)
# tool: get_proxmox_vm_status (D-02 -- verification re-read)
# tool: list_proxmox_resources (D-03 -- stranded-VM sweep enumeration)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from pydantic import ConfigDict

from mcp_test_framework.config import Config
from mcp_test_framework.sdet import ToolCallError, mcp_session, tool  # noqa: F401
from mcp_test_framework.sdet.generated.homelab_mcp import (
    CreateProxmoxVmParams,
    CreateProxmoxVmResponse,
    DeleteProxmoxVmParams,
    GetProxmoxVmStatusParams,
    ListProxmoxResourcesParams,
    ManageProxmoxVmParams,
    ManageProxmoxVmResponse,
)

_log = logging.getLogger(__name__)


@dataclass
class ProxmoxVmLifecycleState:
    """Typed module-scope state for the VM lifecycle scenario.

    One dataclass per scenario module -- the framework ships no
    abstract base class; each scenario owns its state shape.
    """
    created: CreateProxmoxVmResponse
    modified: ManageProxmoxVmResponse | None = None


def _require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(
            f"{name} must be set for the VM lifecycle dogfood "
            f"(used to address a reachable Proxmox host)."
        )
    return v


async def _list_dogfood_vms_in_range(
    host: str,
    node: str,
    lo: int,
    hi: int,
) -> list[dict]:
    """Return a list of VM dicts whose name starts with `mcptf-dogfood-`
    and whose vmid falls within [lo, hi]. Defensive against schema
    drift -- returns [] on any structural surprise.

    Uses list_proxmox_resources (Proxmox-cluster enumeration). The
    managed-inventory VM lister (keyed by device_id, Docker/LXD) is NOT
    used here -- it cannot enumerate Proxmox-cluster VMs.

    TODO(phase-20): When Phase 20 preflight ships reachability + capability
    detection, this helper can short-circuit when list_proxmox_resources
    is unavailable rather than silently returning []. For now the no-op
    fallback is intentional fail-soft for the sweep.
    """
    try:
        result = await tool("list_proxmox_resources").call(
            ListProxmoxResourcesParams(host=host, resource_type="vm")  # type: ignore[arg-type]
        )
    except ToolCallError as e:
        _log.warning("list_proxmox_resources failed during dogfood sweep: %s", e)
        return []
    vms = []
    data = result.data or {}
    # Defensive: try several common Proxmox-payload shapes.
    candidates = (
        data.get("vms")
        or data.get("resources")
        or data.get("data")
        or (data if isinstance(data, list) else [])
    )
    for vm in candidates or []:
        if not isinstance(vm, dict):
            continue
        name = (vm.get("name") or "").strip()
        try:
            vmid = int(vm.get("vmid") or vm.get("id") or 0)
        except (TypeError, ValueError):
            continue
        if name.startswith("mcptf-dogfood-") and lo <= vmid <= hi:
            vms.append({"vmid": vmid, "name": name})
    return vms


async def _sweep_strands(host: str, node: str, lo: int, hi: int) -> None:
    """Best-effort cleanup of prior-crash strands.

    Iterates dogfood-named VMs in [lo, hi] (via list_proxmox_resources)
    and issues delete_proxmox_vm for each. Failures are logged and
    ignored -- a stranded strand is not worth failing setup over.
    """
    for vm in await _list_dogfood_vms_in_range(host, node, lo, hi):
        try:
            await tool("delete_proxmox_vm").call(
                DeleteProxmoxVmParams(node=node, vmid=vm["vmid"], host=host)
            )
            _log.info("swept strand: vmid=%s name=%s", vm["vmid"], vm["name"])
        except ToolCallError as e:
            _log.warning("sweep delete of vmid=%s failed: %s", vm["vmid"], e)


async def _next_free_dogfood_vmid(host: str, node: str, lo: int, hi: int) -> int:
    """Pick the lowest VMID in [lo, hi] not currently in use by a
    dogfood VM. Raises RuntimeError if the range is exhausted.

    If list_proxmox_resources is unavailable (returns []), this walks
    the range starting at `lo`. create_proxmox_vm will reject collisions
    and the caller can retry with the next VMID -- this stub-friendly
    behaviour is the documented Phase 19 fallback.
    """
    in_use = {vm["vmid"] for vm in await _list_dogfood_vms_in_range(host, node, lo, hi)}
    for candidate in range(lo, hi + 1):
        if candidate not in in_use:
            return candidate
    raise RuntimeError(
        f"dogfood_vmid_range [{lo}, {hi}] exhausted -- all {hi - lo + 1} "
        f"VMIDs are currently in use by mcptf-dogfood-* VMs. Manually "
        f"clean up via your Proxmox UI or widen the configured range."
    )


# Local subclass for the CPU-bump action payload. The generated
# ManageProxmoxVmParams has extra="forbid"; we permit extras strictly
# to carry the action payload, NOT to silently substitute attributes
# (see plan 19-04 Interfaces section: D-02 mandates CPU-cores bump only).
class _CpuBumpManageVmParams(ManageProxmoxVmParams):
    model_config = ConfigDict(extra="allow")


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def proxmox_vm_lifecycle(mcp_session):
    """Module-scope yield fixture: create VM, yields ProxmoxVmLifecycleState, delete VM.

    Per Phase 04.1 cancel-scope invariant: standard try/yield/finally,
    NO anyio CancelScope across the yield. await tool(...).call(...)
    rides inside mcp_session's already-active session loop.
    """
    cfg = Config()
    lo, hi = cfg.homelab.proxmox.dogfood_vmid_range
    host = _require_env("MCPTF_DOGFOOD_PROXMOX_HOST")
    node = os.environ.get("MCPTF_DOGFOOD_PROXMOX_NODE", "pve")

    await _sweep_strands(host, node, lo, hi)
    vmid = await _next_free_dogfood_vmid(host, node, lo, hi)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"mcptf-dogfood-{timestamp}"

    created = await tool("create_proxmox_vm").call(
        CreateProxmoxVmParams(
            host=host,
            name=name,
            node=node,
            vmid=vmid,
            cores=1,
        )
    )
    state = ProxmoxVmLifecycleState(created=created)
    try:
        yield state
    finally:
        try:
            await tool("delete_proxmox_vm").call(
                DeleteProxmoxVmParams(node=node, vmid=vmid, host=host)
            )
        except ToolCallError as e:
            # Success-path delete already deleted the VM, or some other
            # transient issue. Cleanup is best-effort; never re-raise.
            _log.warning("teardown delete of vmid=%s failed: %s", vmid, e)


@pytest.mark.asyncio(loop_scope="session")
async def test_create_returns_pending_vm(proxmox_vm_lifecycle):
    state: ProxmoxVmLifecycleState = proxmox_vm_lifecycle
    assert state.created.is_error is False
    data = state.created.data or {}
    assert data.get("vmid") is not None, f"vmid missing from response: {data!r}"


@pytest.mark.asyncio(loop_scope="session")
async def test_modify_accepts_cpu_increase(proxmox_vm_lifecycle):
    state: ProxmoxVmLifecycleState = proxmox_vm_lifecycle
    vmid = (state.created.data or {}).get("vmid")
    node = os.environ.get("MCPTF_DOGFOOD_PROXMOX_NODE", "pve")
    host = _require_env("MCPTF_DOGFOOD_PROXMOX_HOST")
    # D-02: CPU cores 1 -> 2. First-cut action shape per plan Interfaces;
    # if rejected at smoke-test time, the executor consults the live
    # manage_proxmox_vm inputSchema and adjusts -- NOT substitutes a
    # different attribute (see Task 2 checkpoint).
    state.modified = await tool("manage_proxmox_vm").call(
        _CpuBumpManageVmParams(
            action={"type": "config", "cores": 2},  # type: ignore[arg-type]
            node=node,
            vmid=vmid,  # type: ignore[arg-type]
            host=host,
        )
    )
    assert state.modified is not None
    assert state.modified.is_error is False
    status = await tool("get_proxmox_vm_status").call(
        GetProxmoxVmStatusParams(node=node, vmid=vmid, host=host)  # type: ignore[arg-type]
    )
    status_data = status.data or {}
    # Field-name flexibility (cpus vs cores varies by Proxmox version);
    # NOT attribute substitution -- both fields encode CPU count.
    assert status_data.get("cpus") == 2 or status_data.get("cores") == 2, (
        f"expected cpus/cores=2 after modify, got: {status_data!r}"
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_returns_ok(proxmox_vm_lifecycle):
    state: ProxmoxVmLifecycleState = proxmox_vm_lifecycle
    vmid = (state.created.data or {}).get("vmid")
    node = os.environ.get("MCPTF_DOGFOOD_PROXMOX_NODE", "pve")
    host = _require_env("MCPTF_DOGFOOD_PROXMOX_HOST")
    result = await tool("delete_proxmox_vm").call(
        DeleteProxmoxVmParams(node=node, vmid=vmid, host=host)  # type: ignore[arg-type]
    )
    assert result.is_error is False
