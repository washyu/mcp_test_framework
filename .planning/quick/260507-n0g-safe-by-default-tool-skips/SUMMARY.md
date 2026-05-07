---
quick_id: 260507-n0g
slug: safe-by-default-tool-skips
status: complete
date: 2026-05-07
files_modified:
  - config.example.yaml
commits:
  - 0d8337b fix(quick/260507-n0g): safe-by-default tool skips in config.example.yaml
---

## What changed

`config.example.yaml` now ships safe-by-default. 55 new `skip: true` entries
cover every discovered `homelab-mcp` tool except two:

- **`list_keyring_credentials`** — kept enabled with the pre-existing
  `judges: [clarity]` setting (read-only, low-risk, useful as the canonical
  judge-subset demo).
- **`suggest_deployments`** — has NO entry; uses `ToolConfig()` defaults via
  the TOOLCFG-06 missing-key path (read-only inventory suggestion).

The pre-existing `list_registered_servers` skip (upstream-fix-deferred
disambiguation rubric) is unchanged.

## Skip-reason buckets

| Bucket | Count | Examples |
|--------|-------|----------|
| destructive: modifies homelab infrastructure | 26 | `delete_proxmox_vm`, `destroy_terraform_service`, `control_vm`, `run_ansible_playbook`, `ssh_execute_command` |
| side effects on homelab inventory | 4 | `discover_and_map`, `bulk_discover_and_map`, `ssh_discover`, `scan_infrastructure_drift` |
| preview of destructive op; uncomment with caution | 8 | `delete_proxmox_vm_preview`, `decommission_device_preview`, ... |
| requires live homelab infrastructure | 17 | `get_proxmox_node_status`, `list_vms`, `analyze_network_topology`, `validate_infrastructure_changes` |
| Pre-existing v1.0 skip (unchanged) | 1 | `list_registered_servers` |
| **Total `skip: true`** | **56** | |

## Verification

```
$ MCPTF_CONFIG_FILE=config.example.yaml uv run python -c "..."
tools entries: 57
skip=True:     56
no-skip:       ['list_keyring_credentials']
OK
```

```
$ MCPTF_CONFIG_FILE=./config.yaml uv run pytest \
    tests/test_tool_config.py tests/test_config_init_cli.py \
    tests/unit/ tests/test_isolation.py \
    -m "not live_homelab and not live_ollama"
78 passed, 7 deselected in 7.51s
```

- All 56 `skip: true` entries pass Phase 08's `_skip_requires_reason` validator
  (D-16) — each has a non-empty `skip_reason`.
- `extra="forbid"` (CD-02) accepts the file unchanged.
- No regression in the Phase 08 deterministic test subset.

## Why no programmatic categorizer?

A `destructive_tools.py` allow-list would couple us to the homelab-mcp
upstream. Per Phase 08 D-14/D-18, when homelab-mcp adds a new tool, the
unknown-tool warning surfaces it at session start — operators handle it on
the next `mcp-test-framework config-init` refresh. Hand-curating in the
example file keeps the upstream contract clean.

## Operator opt-in flow

1. Copy `config.example.yaml` -> `config.yaml`; set `MCPTF_CONFIG_FILE=./config.yaml`.
2. Run `uv run pytest`. Only `list_keyring_credentials` and `suggest_deployments`
   exercise the full TEST-01..10 surface; everything else SKIPS with a
   readable reason in the pytest output.
3. To opt a tool back in, delete its `skip: true` block (and the `skip_reason`
   line below it). The tool falls back to `ToolConfig()` defaults via the
   missing-key path. Add `call_arguments: {...}` if the tool needs required
   parameters.

## Self-Check: PASSED

- [x] All 55 new skip entries carry a non-empty skip_reason
- [x] Two intended-enabled tools confirmed: `list_keyring_credentials` (judges:[clarity]), `suggest_deployments` (default ToolConfig)
- [x] `extra="forbid"` accepts the example file
- [x] Deterministic test subset (78 tests) still passes
- [x] One atomic commit with full context in the message
