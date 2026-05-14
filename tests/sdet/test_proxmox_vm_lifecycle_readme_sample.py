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
from pathlib import Path

import pytest
import pytest_asyncio

from mcp_test_framework.config import Config
from mcp_test_framework.sdet import ToolCallError, mcp_session, tool  # noqa: F401

# Phase 21.1 RELOC-03: classes are loaded on-demand from cfg.sdet.generated_root
# via the same loader the framework's mcp_session fixture uses. The README's
# worked example shows the recommended SDET pattern of importing from the
# operator's own test-tree package layout (e.g. ``tests.sdet._generated.homelab_mcp``);
# this file uses the spec-loader directly so it does not depend on a particular
# operator package layout being set up at conftest time.
import importlib.util as _importlib_util
import sys as _sys

from mcp_test_framework.sdet._slugs import server_slug as _server_slug

# Phase 21.1 RELOC-03: live-only -- requires cfg.sdet.generated_root populated
# by a prior `gen-sdet-classes` run AND reachable Proxmox + homelab-mcp.
pytestmark = pytest.mark.live_homelab


def _load_generated_homelab_mcp():
    """Load homelab_mcp generated classes from cfg.sdet.generated_root at import time.

    Caller must have already run ``mcp-test-framework gen-sdet-classes`` against
    a configured homelab-mcp server; otherwise raises FileNotFoundError pointing
    at the configured root.
    """
    cfg = Config()
    generated_root = cfg.sdet.generated_root
    if not generated_root.is_absolute():
        generated_root = Path.cwd() / generated_root
    slug = _server_slug("homelab-mcp")
    slug_dir = generated_root / slug
    init_py = slug_dir / "__init__.py"
    if not init_py.is_file():
        raise FileNotFoundError(
            f"Generated homelab_mcp package not found at {init_py}. "
            f"Run `mcp-test-framework gen-sdet-classes` against homelab-mcp first."
        )
    pkg_name = f"_readme_sample_homelab_mcp_{slug}"
    for k in [k for k in list(_sys.modules) if k == pkg_name or k.startswith(pkg_name + ".")]:
        del _sys.modules[k]
    spec = _importlib_util.spec_from_file_location(
        pkg_name, init_py, submodule_search_locations=[str(slug_dir)],
    )
    assert spec is not None and spec.loader is not None
    pkg = _importlib_util.module_from_spec(spec)
    _sys.modules[pkg_name] = pkg
    spec.loader.exec_module(pkg)
    return pkg


# Skip the whole module cleanly if classes can't be loaded -- e.g. no config
# in CWD, or `gen-sdet-classes` has not been run for homelab-mcp yet. Pairs
# with the ``live_homelab`` marker so CI sessions without the marker simply
# deselect the tests; environments that opt in but lack the regen get an
# actionable skip rather than a collection error.
try:
    _homelab_mcp = _load_generated_homelab_mcp()
except Exception as _load_exc:  # noqa: BLE001
    pytest.skip(
        f"homelab_mcp generated classes not available at "
        f"cfg.sdet.generated_root: {_load_exc}",
        allow_module_level=True,
    )

CreateProxmoxVmParams = _homelab_mcp.CreateProxmoxVmParams
CreateProxmoxVmResponse = _homelab_mcp.CreateProxmoxVmResponse
DeleteProxmoxVmParams = _homelab_mcp.DeleteProxmoxVmParams
ListProxmoxResourcesParams = _homelab_mcp.ListProxmoxResourcesParams

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
