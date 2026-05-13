"""Phase 19: regression pins for the new homelab.* config sub-models.

Covers the default value, override, extra-key rejection (typo), range
invariant (lo <= hi), nested-default access, and the frozen=True
contract. No env-routing tests -- homelab.* is not env-routable
(mirrors ToolConfig per Phase 13 D-07).
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_test_framework.models import HomelabConfig, HomelabProxmoxConfig


def test_default_dogfood_vmid_range():
    cfg = HomelabProxmoxConfig()
    assert cfg.dogfood_vmid_range == (9990, 9999)


def test_override_dogfood_vmid_range():
    cfg = HomelabProxmoxConfig(dogfood_vmid_range=(9200, 9209))
    assert cfg.dogfood_vmid_range == (9200, 9209)


def test_typo_field_rejected():
    with pytest.raises(ValidationError) as excinfo:
        HomelabProxmoxConfig(dogfood_vmd_range=(1, 2))  # type: ignore[call-arg]
    assert "dogfood_vmd_range" in str(excinfo.value)


def test_range_lo_greater_than_hi_rejected():
    with pytest.raises(ValidationError) as excinfo:
        HomelabProxmoxConfig(dogfood_vmid_range=(9999, 9990))
    assert "dogfood_vmid_range" in str(excinfo.value)


def test_homelab_config_default_proxmox():
    cfg = HomelabConfig()
    assert cfg.proxmox.dogfood_vmid_range == (9990, 9999)


def test_homelab_proxmox_frozen():
    cfg = HomelabProxmoxConfig()
    with pytest.raises((ValidationError, TypeError)):
        cfg.dogfood_vmid_range = (1, 2)  # type: ignore[misc]
