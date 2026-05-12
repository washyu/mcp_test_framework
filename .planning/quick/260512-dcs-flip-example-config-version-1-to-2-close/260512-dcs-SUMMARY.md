---
quick_id: 260512-dcs
slug: flip-example-config-version-1-to-2-close
status: complete
completed: 2026-05-12
commit: 814d743
closes: CLEAN-03 (v1.2-MILESTONE-AUDIT.md BLOCKER → satisfied)
files_changed:
  - examples/homelab-mcp.yaml (2 lines: precedence comment, version)
  - config.example.yaml (2 lines: comment, version)
---

# Quick Task 260512-dcs: Flip example configs to v2 — Summary

## Result

CLEAN-03 BLOCKER closed. Both static example configs now match the schema Phase 13 enforces.

## Changes

- `examples/homelab-mcp.yaml:3` — stripped `.env` from precedence comment (was `CLI > env > .env > YAML > defaults`, now `CLI > env > YAML > defaults`). Aligns with Phase 13 SAFE-05 (`.env` overlay dropped).
- `examples/homelab-mcp.yaml:19-20` — comment + `version: 1` → `version: 2`.
- `config.example.yaml:28-29` — comment + `version: 1` → `version: 2`.

## Verification

| Check | Expected | Actual |
|-------|----------|--------|
| `grep -c "version: 1" examples/homelab-mcp.yaml config.example.yaml` | 0 / 0 | 0 / 0 |
| `MCPTF_CONFIG_FILE=examples/homelab-mcp.yaml Config().version` | 2 | 2 |
| `MCPTF_CONFIG_FILE=config.example.yaml Config().version` | 2 | 2 |
| `grep "version: 2" cli.py:1095` (scaffold parity) | present | present (unchanged — already correct) |
| Live `mcp-test-framework config-init -o test-init.yaml` | emits `version: 2` | confirmed |

## Closes

`CLEAN-03 partial → satisfied` per [.planning/v1.2-MILESTONE-AUDIT.md](../../v1.2-MILESTONE-AUDIT.md). The only cross-phase integration BLOCKER in the v1.2 milestone audit. Milestone status flips from `gaps_found` to `tech_debt` (live-stack UATs in phases 13/14 remain as carry-forward).

## Commit

`814d743 docs(v1.2): migrate example configs to schema v2 (closes CLEAN-03 audit gap)`
