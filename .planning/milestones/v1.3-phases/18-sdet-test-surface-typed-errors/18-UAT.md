---
status: testing
phase: 18-sdet-test-surface-typed-errors
source:
  - 18-01-SUMMARY.md
  - 18-02-SUMMARY.md
  - 18-03-SUMMARY.md
  - 18-04-SUMMARY.md
  - 18-05-SUMMARY.md
  - 18-06-SUMMARY.md
  - 18-07-SUMMARY.md
  - 18-08-SUMMARY.md
started: 2026-05-15T00:00:00Z
updated: 2026-05-15T00:00:00Z
---

## Current Test

number: 1
name: gen-sdet-classes produces the generated module
expected: |
  Run `uv run mcp-test-framework gen-sdet-classes` against the configured MCP
  server (homelab-mcp via `config-v2-worktree.yaml` or your config file).
  The command exits 0 and creates `src/mcp_test_framework/sdet/generated/<slug>/`
  (slug derived from the server's `serverInfo.name`, e.g. `homelab_mcp`)
  containing per-tool Params/Response Python modules plus a `_REGISTRY` dict.
awaiting: user response

## Tests

### 1. gen-sdet-classes produces the generated module
expected: |
  Run `uv run mcp-test-framework gen-sdet-classes` against the configured
  MCP server. Exits 0. Creates `src/mcp_test_framework/sdet/generated/<slug>/`
  with per-tool Params/Response modules and a `_REGISTRY` dict.
  This is the prerequisite for every SDET test — without it, `mcp_session`
  fails loud with the Phase 18 D-03 message naming `gen-sdet-classes`
  and `--sdet`.
result: pending

### 2. Generated classes + barrel symbols both import cleanly
expected: |
  Run:
    uv run python -c "from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse; from mcp_test_framework.sdet.generated.homelab_mcp import _REGISTRY; print('OK', len(_REGISTRY))"
  Prints `OK <N>` where N is the tool count (e.g. ~70). Confirms Plan 18-04
  barrel + Phase 17 codegen produce a usable import surface.
result: pending

### 3. --sdet flag appears in `run --help`
expected: |
  Run `uv run mcp-test-framework run --help`.
  The help text lists a `--sdet` option (boolean), positioned near
  `--with-framework`, with text describing the composition matrix (swaps
  test scope to `tests/sdet/`; composes additively with `--with-framework`).
result: pending

### 4. `run --sdet` pre-run digest shows the SDET banner
expected: |
  Run `uv run mcp-test-framework run --sdet 2>&1 | head -30`
  (with MCPTF_CONFIG_FILE set or a discoverable config.yaml).
  Banner line reads `MCP Test Framework (SDET)` (not the operator banner).
  `Judges:` line reads `(none — SDET scope)` with em-dash U+2014. Scenario list
  is keyed on module stems alphabetized (e.g. `proxmox_vm_lifecycle_readme_sample`).
result: pending

### 5. Live SDET scenario renders with bare group header + nested rows
expected: |
  Run `uv run mcp-test-framework run --sdet 2>&1 | tail -40`.
  Output contains a bare group-header line (the module stem, no trailing colon,
  no glyph) followed by indented per-test rows with `✓` (pass), `✗` (fail), or
  `–` (skip) glyph and the test name — no "PASS"/"FAIL" word on the row itself.
  A `Result: N PASS / M FAIL / K SKIP` summary line appears at the end.
result: pending

### 6. ToolCallError formats FAIL row as `✗ <name> — [code] message`
expected: |
  When any SDET test fails via ToolCallError, the FAIL row shows
  `✗ <test_name> — [code] message` (em-dash U+2014, brackets around code)
  when a code is present, or `✗ <test_name> — message` (bare) when no code.
  This is the Phase 18 D-10 / Plan 18-06 contract. If everything passed,
  skip with reason "no failures to format".
result: pending

### 7. `--debug` appendix emits the ToolCallError dump block
expected: |
  When at least one ToolCallError fired in test 5/6, rerun with
  `--debug` appended and inspect the tail. Output contains a block
  `--- ToolCallError dump ---` listing `tool:`, `code:`, `message:`, and an
  indented `raw:` JSON (the full CallToolResult). The block appears BEFORE
  `--- raw pytest output ---`. Skip if no failures occurred.
result: pending

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0

## Gaps

[none yet]
