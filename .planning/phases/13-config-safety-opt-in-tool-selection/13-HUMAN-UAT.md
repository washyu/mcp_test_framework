---
status: complete
phase: 13-config-safety-opt-in-tool-selection
source: [13-VERIFICATION.md]
started: 2026-05-10T00:00:00Z
updated: 2026-05-11T19:55:00Z
---

## Current Test

[testing complete]

## Tests

### 1. End-to-end run with a real MCP server (homelab-mcp via uvx) and a v2 config opting in 1-2 tools
expected: Listed tools parametrize as contract tests; unlisted/skipped tools render in the per-tool summary with the correct SAFE-01 reason strings ("not selected in config" vs operator's curated skip_reason).
result: pass
notes: |
  User confirmed SAFE-01 opt-in semantics: opted-in tool ran as contract test, skip:true+custom skip_reason rendered the operator's reason, unlisted tools rendered "not selected in config". Separately observed pytest parametrize-id leak in `Running:` line (entries like `path0`, `NOTSET`, `None`, `""`, numeric edge cases) — origin: `_extract_tool_name` in `src/mcp_test_framework/_runner.py` only handles `[<tool_name>]`-shaped ids. NOT a Phase 13 gap; already logged as Phase 14 UAT follow-up #2 and overlaps with Phase 15 (operator vs framework test surface split). Worth a smaller Phase 14 follow-up plan to harden the extractor as a stopgap.

### 2. Operator follows MIGRATION-v1-to-v2.md to port a real v1 config
expected: Port completes (re-run config-init, port call_arguments/judges/skip_reason, drop target: block, drop .env reliance); resulting v2 config loads cleanly; only opted-in tools run; operator finds the doc clear and actionable.
result: pass

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
