---
status: partial
phase: 13-config-safety-opt-in-tool-selection
source: [13-VERIFICATION.md]
started: 2026-05-10T00:00:00Z
updated: 2026-05-10T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. End-to-end run with a real MCP server (homelab-mcp via uvx) and a v2 config opting in 1-2 tools
expected: Listed tools parametrize as contract tests; unlisted/skipped tools render in the per-tool summary with the correct SAFE-01 reason strings ("not selected in config" vs operator's curated skip_reason).
result: [pending]

### 2. Operator follows MIGRATION-v1-to-v2.md to port a real v1 config
expected: Port completes (re-run config-init, port call_arguments/judges/skip_reason, drop target: block, drop .env reliance); resulting v2 config loads cleanly; only opted-in tools run; operator finds the doc clear and actionable.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
