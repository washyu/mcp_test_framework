---
quick_id: 260512-dcs
slug: flip-example-config-version-1-to-2-close
created: 2026-05-12
description: Flip example config files to schema v2 to close CLEAN-03 BLOCKER from v1.2 milestone audit
closes: CLEAN-03 (partial → satisfied)
source_audit: .planning/v1.2-MILESTONE-AUDIT.md
files_modified:
  - examples/homelab-mcp.yaml
  - config.example.yaml
must_haves:
  truths:
    - "examples/homelab-mcp.yaml line 20 reads `version: 2` (matches Phase 13 schema enforcement)"
    - "examples/homelab-mcp.yaml line 3 has no `.env` token in the precedence comment"
    - "config.example.yaml line 29 reads `version: 2`"
    - "config.example.yaml line 28 comment matches v2 (no `accepts version 1` wording)"
    - "Loading examples/homelab-mcp.yaml via Config() succeeds with version=2"
    - "Loading config.example.yaml via Config() succeeds with version=2"
    - "config-init scaffold output still ends with `version: 2` (no regression in cli.py:1095)"
---

# Quick Task 260512-dcs: Flip example configs to v2

## Objective

Phase 13 raised the accepted config schema to `version: 2` and emits a LOCKED migration error on v1 loads. Two operator-facing example files were not migrated, breaking the cross-phase contract:

- `examples/homelab-mcp.yaml:20` — `version: 1`
- `examples/homelab-mcp.yaml:3` — stale `.env` in precedence comment (contradicts Phase 13 SAFE-05)
- `config.example.yaml:29` — `version: 1`
- `config.example.yaml:28` — stale comment "This release accepts version 1"

[README.md:326](../../README.md#L326) points operators at `examples/homelab-mcp.yaml` as the "complete worked reference," so a fresh operator copying it hits SAFE-06 as their first impression of v1.2.

## Tasks

### Task 1: Migrate `examples/homelab-mcp.yaml` to v2

- Line 3: strip `.env` from precedence comment (`CLI > env > .env > YAML > defaults` → `CLI > env > YAML > defaults`).
- Line 20: `version: 1` → `version: 2`.
- Acceptance: `uv run python -c "from mcp_test_framework.config import _load_config; c = _load_config('examples/homelab-mcp.yaml'); print(c.version)"` prints `2` cleanly (no SAFE-06 error).

### Task 2: Migrate `config.example.yaml` to v2

- Line 28: comment `# Schema version. This release accepts version 1.` → `# Schema version. This release accepts version 2.`
- Line 29: `version: 1` → `version: 2`.
- Acceptance: `uv run python -c "from mcp_test_framework.config import _load_config; c = _load_config('config.example.yaml'); print(c.version)"` prints `2` cleanly.

### Task 3: Verify config-init scaffold parity

- `grep -n 'version: 2' src/mcp_test_framework/cli.py` returns the existing `cli.py:1095` literal (no change needed — already correct).
- `grep -c 'version: 1' examples/homelab-mcp.yaml config.example.yaml src/mcp_test_framework/cli.py` returns `0` for all three (eradication gate).
- `MCPTF_CONFIG_FILE=examples/homelab-mcp.yaml uv run python -c "from mcp_test_framework.config import Config; c = Config(); assert c.version == 2"` exits 0.

## Commits

Single squashed commit (mechanical change, no separable atomic steps):
`docs(v1.2): migrate example configs to schema v2 (closes CLEAN-03 audit gap)`

## Closes

`CLEAN-03` (partial → satisfied) per `.planning/v1.2-MILESTONE-AUDIT.md` BLOCKER.
