---
phase: 19-stateful-primitives-domain-ui-integration
plan: "02"
subsystem: config
tags: [config, pydantic, homelab, proxmox, dogfood-vmid-range, tdd]
dependency_graph:
  requires: []
  provides:
    - "HomelabProxmoxConfig (models.py) -- dogfood_vmid_range tuple[int,int]"
    - "HomelabConfig (models.py) -- proxmox: HomelabProxmoxConfig"
    - "Config.homelab field (config.py) -- wired via default_factory"
    - "examples/homelab-mcp.yaml homelab block"
  affects:
    - "Plan 19-04 (dogfood scenario) -- reads cfg.homelab.proxmox.dogfood_vmid_range for VMID allocation"
tech_stack:
  added: []
  patterns:
    - "Pydantic v2 frozen sub-model with extra=forbid (ToolConfig precedent, Phase 13 D-07)"
    - "field_validator mode=after for range bounds check"
    - "default_factory nesting: Config.homelab -> HomelabConfig -> HomelabProxmoxConfig"
key_files:
  created:
    - tests/framework/unit/test_homelab_config.py
  modified:
    - src/mcp_test_framework/models.py
    - src/mcp_test_framework/config.py
    - examples/homelab-mcp.yaml
decisions:
  - "HomelabProxmoxConfig uses extra=forbid (same as ToolConfig) so typos fail at load time"
  - "No env-routing (no AliasChoices) per Phase 13 D-07 -- homelab.* is YAML-only"
  - "_validate_dogfood_vmid_range enforces lo<=hi AND Proxmox bounds [100, 999999999]"
  - "homelab block placed in examples/homelab-mcp.yaml only, NOT config.example.yaml"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-13"
  tasks_completed: 2
  files_modified: 4
---

# Phase 19 Plan 02: Homelab Config Primitives (dogfood_vmid_range) Summary

**One-liner:** Two frozen Pydantic v2 sub-models (`HomelabProxmoxConfig`, `HomelabConfig`) with `extra="forbid"` and a `_validate_dogfood_vmid_range` validator, wired onto `Config.homelab` via `default_factory`, plus 9 regression-pin tests and a `examples/homelab-mcp.yaml` operator example.

## What Was Built

This plan delivers the `homelab.proxmox.dogfood_vmid_range` config knob that Plan 04's VM-lifecycle dogfood scenario needs. The VMID isolation range (default `[9990, 9999]`) is now configurable via YAML and validated at load time.

### New models in `src/mcp_test_framework/models.py`

**`HomelabProxmoxConfig`** — Proxmox-specific knobs for SDET dogfood scenarios:
- `dogfood_vmid_range: tuple[int, int]` with default `(9990, 9999)`
- `_validate_dogfood_vmid_range` validator enforcing `lo <= hi` and Proxmox VMID bounds `[100, 999999999]`
- `model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")`
- No `AliasChoices` (not env-routable, per Phase 13 D-07)

**`HomelabConfig`** — Container for homelab scenario config domains:
- `proxmox: HomelabProxmoxConfig = Field(default_factory=HomelabProxmoxConfig)`
- Same `frozen=True, extra="forbid"` pattern

### Config field in `src/mcp_test_framework/config.py`

Added `homelab: HomelabConfig = Field(default_factory=HomelabConfig)` after `mcp_server` field. Import added alphabetically (`HomelabConfig` before `McpServerConfig`). No `settings_customise_sources` change needed — the new field flows through the existing `init_kwargs → YAML → defaults` pipeline.

### Example config in `examples/homelab-mcp.yaml`

Added `homelab.proxmox.dogfood_vmid_range: [9990, 9999]` block after `version: 2` with operator-friendly comment. Block NOT added to `config.example.yaml` (generic starter template per CONTEXT.md PATTERNS).

### Test coverage in `tests/framework/unit/test_homelab_config.py`

9 tests covering:
1. `test_default_dogfood_vmid_range` — default `(9990, 9999)`
2. `test_override_dogfood_vmid_range` — override `(9200, 9209)`
3. `test_typo_field_rejected` — `dogfood_vmd_range` (missing `i`) raises `ValidationError`
4. `test_range_lo_greater_than_hi_rejected` — `(9999, 9990)` raises `ValidationError`
5. `test_homelab_config_default_proxmox` — `HomelabConfig().proxmox.dogfood_vmid_range == (9990, 9999)`
6. `test_homelab_proxmox_frozen` — mutation raises `ValidationError` or `TypeError`
7. `test_config_default_homelab` — `Config().homelab.proxmox.dogfood_vmid_range == (9990, 9999)`
8. `test_config_yaml_homelab_override` — YAML with `[9200, 9209]` loads correctly
9. `test_config_yaml_typo_rejected` — YAML with `dogfood_vmd_range` raises `ValidationError`

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (Task 1 — sub-models) | `06be76e` | test(19-02): 6 tests, ImportError |
| GREEN (Task 1) | `e029606` | feat(19-02): HomelabConfig + HomelabProxmoxConfig, 6/6 pass |
| RED (Task 2 — Config integration) | `40b60ec` | test(19-02): 3 new tests, 2 fail (no homelab field) |
| GREEN (Task 2) | `bc4539b` | feat(19-02): wire Config.homelab + example YAML, 9/9 pass |

## Test Results

```
uv run pytest tests/framework/unit/test_homelab_config.py -v
9 passed in 0.06s
```

All 9 tests pass. Existing unit tests unaffected:
```
uv run pytest tests/framework/unit/test_config.py -q
17 passed in 0.11s
```

## Pyright Analysis

| File | Before | After | Delta |
|------|--------|-------|-------|
| `src/mcp_test_framework/models.py` | 0 errors | 0 errors | 0 |
| `src/mcp_test_framework/config.py` | 1 error (pre-existing: `init_kwargs` on `PydanticBaseSettingsSource`) | 1 error (same) | 0 |

Zero new type errors introduced by this plan.

## Plan 04 Integration Point

Plan 04 (dogfood scenario) can now import `Config` and access:
```python
cfg.homelab.proxmox.dogfood_vmid_range  # tuple[int, int], e.g. (9990, 9999)
```
The operator overrides this in their `config.yaml` if their cluster reserves 9990-9999 for something else.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all fields are wired to real Pydantic sub-models with validators.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. The YAML config path is an existing trust boundary already covered by `Config.extra="forbid"`. The new `HomelabProxmoxConfig.extra="forbid"` adds defense-in-depth for the nested path. T-19-02-01 through T-19-02-04 (from plan threat model) are all mitigated as planned.

## Self-Check: PASSED

Files created/modified:
- `tests/framework/unit/test_homelab_config.py` — FOUND
- `src/mcp_test_framework/models.py` — FOUND (contains `class HomelabProxmoxConfig`, `class HomelabConfig`)
- `src/mcp_test_framework/config.py` — FOUND (contains `homelab: HomelabConfig`)
- `examples/homelab-mcp.yaml` — FOUND (contains `dogfood_vmid_range: [9990, 9999]`)

Commits:
- `06be76e` — FOUND (test(19-02): RED -- homelab config sub-model tests)
- `e029606` — FOUND (feat(19-02): GREEN -- add HomelabConfig + HomelabProxmoxConfig)
- `40b60ec` — FOUND (test(19-02): RED -- Config.homelab integration tests)
- `bc4539b` — FOUND (feat(19-02): GREEN -- wire Config.homelab + example YAML)
