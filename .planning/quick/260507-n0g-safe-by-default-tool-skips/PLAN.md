---
quick_id: 260507-n0g
slug: safe-by-default-tool-skips
date: 2026-05-07
files_modified:
  - config.example.yaml
---

# Quick Task: Safe-by-default tool skips in config.example.yaml

## Problem

After Phase 07 multi-tool discovery + Phase 08 per-tool config registry, an
operator who copies `config.example.yaml` and runs the suite will execute
TEST-08 (`call_tool(name, tool_config.call_arguments)`) against **every**
discovered `homelab-mcp` tool — including destructive operations
(`delete_proxmox_vm`, `decommission_device`, `destroy_terraform_service`,
`control_vm`, `remove_server/vm`, `rollback_infrastructure_changes`,
`run_ansible_playbook`, `ssh_execute_command`, ...). With no per-tool
`call_arguments`, most calls fail with `isError=True`, but:

- Some tools may have side-effects even with empty args (e.g. `discover_and_map`
  writes to the homelab inventory).
- Operator coffee-spilled-on-keyboard / test-run-on-prod hazard is real.
- The `*_preview` tools couple to their destructive siblings — best to skip
  by default and let the operator opt them back in once they've read the docs.

## Approach

Phase 08's TOOLCFG-07 + TOOLCFG-06 already provide the mechanism: per-tool
`skip: true` with a non-empty `skip_reason`. The example YAML just needs to
ship safer defaults.

Add `skip: true` entries for **all 58 discovered homelab-mcp tools** EXCEPT:

1. **`list_keyring_credentials`** — already configured with `judges: [clarity]`;
   keep as-is. Pure read, no homelab-state side effects.
2. **`suggest_deployments`** — keep enabled, no skip. Read-only suggestion
   based on current inventory.
3. **`list_registered_servers`** — already has `skip: true` (upstream-fix-deferred
   disambiguation rubric); keep as-is.

So 55 new skip entries are added. Each entry's `skip_reason` is one of:

- `"destructive: <action>"` — for verbs like create / delete / destroy /
  remove / decommission / purge / deploy / install / control / manage /
  register / scale / run / execute / update / rollback / refresh / clone
- `"side effects on homelab inventory"` — for `*discover_and_map`, `ssh_discover`,
  `scan_infrastructure_drift`
- `"requires live homelab infrastructure"` — for read-only `get_*`, `list_*`,
  `search_*`, `analyze_*`, `check_*`, `validate_*`
- `"preview of destructive op; uncomment with caution"` — for `*_preview` tools

## Verification

- `MCPTF_CONFIG_FILE=config.example.yaml uv run python -c "from mcp_test_framework.config import Config; cfg = Config(); print(len(cfg.tools), '|', sum(1 for t in cfg.tools.values() if t.skip))"` returns `57 | 56` (57 entries total: 55 new + 2 existing skip + 1 judges-only [list_keyring_credentials, no skip]; 56 with `skip=True`).
- All `skip: true` entries have non-empty `skip_reason` (load-time validator
  enforces this — Pydantic raises if violated).
- Worktree's deterministic test subset still passes:
  `MCPTF_CONFIG_FILE=./config.yaml uv run pytest tests/test_tool_config.py tests/test_config_init_cli.py tests/unit/ tests/test_isolation.py -m "not live_homelab and not live_ollama"` exits 0.
- `MCPTF_CONFIG_FILE=config.example.yaml uv run python -c ...` does NOT raise
  ValidationError under post-Phase-08 `extra="forbid"`.

## Out of scope

- Modifying `homelab-mcp` upstream.
- Building a programmatic categorizer (`destructive_tools.py`); the example
  is hand-curated for the v1.0/v1.1 homelab-mcp tool set. New tools added
  upstream will surface the unknown-tool warning at session start (Phase 08
  D-14/D-18) — operators handle them on next config-init refresh.
