---
status: complete
phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
source:
  - 31-01-SUMMARY.md
  - 31-02-SUMMARY.md
  - 31-03-SUMMARY.md
  - 31-04-SUMMARY.md
  - 31-05-SUMMARY.md
  - 31-06-SUMMARY.md
started: 2026-05-28T00:00:00Z
updated: 2026-05-28T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Legacy `sdet:` config key is rejected
expected: A config.yaml with a top-level `sdet:` block is rejected at load time with an operator-tone error that names `test_code:` as the correct key (no silent alias resolution).
result: pass

### 2. `MCPTF_CONFIG_FILE` env var no longer loads config
expected: Setting `MCPTF_CONFIG_FILE=/path/to/config.yaml` and running pytest does NOT load config from that path. With no other config source you get a fail-loud "no config" error (not a silent run), plus a loud `[mcp-contracts]`-prefixed deprecation warning pointing you at the `mcp_config_file` ini key or `mcp-contracts run --config`.
result: pass

### 3. `version: 1` config is rejected cleanly (no migration verbiage)
expected: A config.yaml declaring `version: 1` is rejected with a generic operator-tone error that points you at `mcp-contracts config-init` to generate a current scaffold. No "migrate v1 to v2" wording and no reference to a MIGRATION doc.
result: pass

### 4. Migration doc is gone; docs reference `version: 2` directly
expected: `docs/MIGRATION-v1-to-v2.md` no longer exists. README, `docs/ERROR-STYLE.md`, and `docs/LIBRARY-MODE.md` talk about `version: 2` directly with no "migration from v1" callout or cross-reference.
result: pass

### 5. Framework test baseline is green with no stale migration-message tests
expected: `uv run pytest tests/framework/` passes. No self-test is still pinned to the old v1-rejection migration-message text (those were deleted or relaxed to assert only an operator-tone error shape).
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
