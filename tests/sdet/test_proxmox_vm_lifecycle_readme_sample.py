"""Temporary scenario used to snapshot README's '## SDET scenarios' sample output. Deleted after snapshot capture (Phase 21 Plan 02 Task 4).

Trimmed copy of the Phase 19-04 dogfood scenario: create + delete only.
The modify step is OMITTED per Phase 21 D-16 -- the upstream
manage_proxmox_vm inputSchema bug (Phase 19-04 Finding 2) makes that
test path unreliable for the README's "green run" sample. Discussion of
the _CpuBumpManageVmParams workaround lives exclusively in
docs/SDET-AUTHORING.md.

Pinned conventions:
  - VMID range: read from the homelab.proxmox config block
    (dogfood_vmid_range, default [9990, 9999]).
  - Name prefix: mcptf-dogfood-readme-<ISO8601 UTC seconds> (distinct
    from the Phase 19-04 dogfood prefix so a concurrent dogfood sweep
    does not touch this scenario's strands).
  - Best-effort teardown sweeps any stranded mcptf-dogfood-readme-* in
    the configured range from prior crashed runs via
    list_proxmox_resources; sweep failures logged, never raise.
  - Black-box rule: imports only from mcp_test_framework.* -- never
    from homelab-mcp source.

Live-environment requirements:
  - homelab-mcp reachable via the configured `mcp_server.command`.
  - Proxmox reachable from the host running homelab-mcp.
  - Operator's Proxmox credentials registered in homelab-mcp.
  - MCPTF_DOGFOOD_PROXMOX_HOST set to a reachable Proxmox host name.
  - MCPTF_DOGFOOD_PROXMOX_NODE defaults to "pve" (override if your
    cluster uses a different node name).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from mcp_test_framework.config import Config
from mcp_test_framework.sdet import ToolCallError, mcp_session, tool  # noqa: F401
from mcp_test_framework.sdet.generated.homelab_mcp import (
    CreateProxmoxVmParams,
    CreateProxmoxVmResponse,
    DeleteProxmoxVmParams,
    ListProxmoxResourcesParams,
)

_log = logging.getLogger(__name__)


@dataclass
class ProxmoxVmLifecycleReadmeState:
    """Typed module-scope state for the README-sample VM lifecycle scenario."""
    created: CreateProxmoxVmResponse


def _require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(
            f"{name} must be set for the README-sample VM lifecycle scenario "
            f"(used to address a reachable Proxmox host)."
        )
    return v


async def _list_readme_dogfood_vms_in_range(
    host: str,
    node: str,
    lo: int,
    hi: int,
) -> list[dict]:
    """Return README-prefixed dogfood VMs whose vmid falls within [lo, hi].

    Distinct prefix (`mcptf-dogfood-readme-`) so this temp scenario does
    not touch the Phase 19-04 dogfood's strands.
    """
    try:
        result = await tool("list_proxmox_resources").call(
            ListProxmoxResourcesParams(host=host, resource_type="vm")  # type: ignore[arg-type]
        )
    except ToolCallError as e:
        _log.warning("list_proxmox_resources failed during README sample sweep: %s", e)
        return []
    vms = []
    data = result.data or {}
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
        if name.startswith("mcptf-dogfood-readme-") and lo <= vmid <= hi:
            vms.append({"vmid": vmid, "name": name})
    return vms


async def _sweep_readme_strands(host: str, node: str, lo: int, hi: int) -> None:
    """Best-effort cleanup of prior-crash strands from this temp scenario."""
    for vm in await _list_readme_dogfood_vms_in_range(host, node, lo, hi):
        try:
            await tool("delete_proxmox_vm").call(
                DeleteProxmoxVmParams(node=node, vmid=vm["vmid"], host=host)
            )
            _log.info("swept README strand: vmid=%s name=%s", vm["vmid"], vm["name"])
        except ToolCallError as e:
            _log.warning("sweep delete of vmid=%s failed: %s", vm["vmid"], e)


async def _next_free_readme_vmid(host: str, node: str, lo: int, hi: int) -> int:
    """Pick the lowest VMID in [lo, hi] not in use by a README dogfood VM."""
    in_use = {vm["vmid"] for vm in await _list_readme_dogfood_vms_in_range(host, node, lo, hi)}
    for candidate in range(lo, hi + 1):
        if candidate not in in_use:
            return candidate
    raise RuntimeError(
        f"dogfood_vmid_range [{lo}, {hi}] exhausted -- all {hi - lo + 1} "
        f"VMIDs are currently in use by mcptf-dogfood-readme-* VMs."
    )


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def proxmox_vm_lifecycle_readme(mcp_session):
    """Module-scope yield fixture: create VM, yields state, delete VM in finalizer."""
    cfg = Config()
    lo, hi = cfg.homelab.proxmox.dogfood_vmid_range
    host = _require_env("MCPTF_DOGFOOD_PROXMOX_HOST")
    node = os.environ.get("MCPTF_DOGFOOD_PROXMOX_NODE", "pve")

    await _sweep_readme_strands(host, node, lo, hi)
    vmid = await _next_free_readme_vmid(host, node, lo, hi)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"mcptf-dogfood-readme-{timestamp}"

    created = await tool("create_proxmox_vm").call(
        CreateProxmoxVmParams(
            host=host,
            name=name,
            node=node,
            vmid=vmid,
            cores=1,
        )
    )
    state = ProxmoxVmLifecycleReadmeState(created=created)
    try:
        yield state
    finally:
        try:
            await tool("delete_proxmox_vm").call(
                DeleteProxmoxVmParams(node=node, vmid=vmid, host=host)
            )
        except ToolCallError as e:
            _log.warning("teardown delete of vmid=%s failed: %s", vmid, e)


@pytest.mark.asyncio(loop_scope="session")
async def test_create_returns_pending_vm(proxmox_vm_lifecycle_readme):
    state: ProxmoxVmLifecycleReadmeState = proxmox_vm_lifecycle_readme
    assert state.created.is_error is False
    data = state.created.data or {}
    vmid = data.get("vmid")
    assert isinstance(vmid, int), f"vmid not an int in response: {data!r}"


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_returns_ok(proxmox_vm_lifecycle_readme):
    state: ProxmoxVmLifecycleReadmeState = proxmox_vm_lifecycle_readme
    vmid = (state.created.data or {}).get("vmid")
    node = os.environ.get("MCPTF_DOGFOOD_PROXMOX_NODE", "pve")
    host = _require_env("MCPTF_DOGFOOD_PROXMOX_HOST")
    result = await tool("delete_proxmox_vm").call(
        DeleteProxmoxVmParams(node=node, vmid=vmid, host=host)  # type: ignore[arg-type]
    )
    assert result.is_error is False
