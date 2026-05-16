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


# --- Config root integration tests ---

import textwrap

from mcp_test_framework.config import Config
from mcp_test_framework.models import TestCodeConfig

# Phase 21.1 RELOC-01: Config.sdet is REQUIRED. Tests in this file that
# construct Config(...) must supply an sdet stub (or set it in YAML).
_TEST_CODE_STUB = TestCodeConfig(generated_root="tests/sdet/_generated")


def test_config_default_homelab():
    # Pure-default Config (no YAML, no env). Confirms the new field
    # default_factory wires through the root model.
    cfg = Config(test_code=_TEST_CODE_STUB)
    assert cfg.homelab.proxmox.dogfood_vmid_range == (9990, 9999)


def test_config_yaml_homelab_override(tmp_path):
    path = tmp_path / "cfg.yaml"
    path.write_text(textwrap.dedent("""\
        version: 2
        homelab:
          proxmox:
            dogfood_vmid_range: [9200, 9209]
        sdet:
          generated_root: "tests/sdet/_generated"
    """))
    cfg = Config(yaml_file=str(path))
    assert cfg.homelab.proxmox.dogfood_vmid_range == (9200, 9209)


def test_config_yaml_typo_rejected(tmp_path):
    path = tmp_path / "cfg.yaml"
    path.write_text(textwrap.dedent("""\
        version: 2
        homelab:
          proxmox:
            dogfood_vmd_range: [1, 2]
        sdet:
          generated_root: "tests/sdet/_generated"
    """))
    with pytest.raises(ValidationError) as excinfo:
        Config(yaml_file=str(path))
    assert "dogfood_vmd_range" in str(excinfo.value) or "extra" in str(excinfo.value).lower()
