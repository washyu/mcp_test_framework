---
status: partial
phase: 02-mcp-client-wrapper
source: [02-VERIFICATION.md]
started: 2026-05-04
updated: 2026-05-04
---

## Current Test

[awaiting human testing on a machine with `homelab-mcp` installed]

## Tests

### 1. SC#1 — raw stdio_client lists target tool with non-empty schema
expected: `uv run pytest -m live_homelab tests/smoke/test_smoke_homelab_mcp.py::test_raw_stdio_lists_target_tool -v` exits 0; `cfg.target.tool_name` (default `list_registered_servers`) is present in the SDK's tool list and its `inputSchema` is a non-empty dict.
result: [pending]

### 2. SC#2 — wrapper `call_tool` returns non-error result with content
expected: `uv run pytest -m live_homelab tests/smoke/test_smoke_homelab_mcp.py::test_wrapper_call_tool_returns_non_error_with_content -v` exits 0; `result.isError` is false and at least one of `result.content` / `result.structuredContent` is non-empty.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
