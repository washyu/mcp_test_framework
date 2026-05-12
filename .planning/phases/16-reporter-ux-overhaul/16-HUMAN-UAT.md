---
status: partial
phase: 16-reporter-ux-overhaul
source: [16-VERIFICATION.md]
started: 2026-05-12T00:00:00Z
updated: 2026-05-12T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Per-judge reasoning surfaces in domain UI tail at runtime (UX-03 / SC-3)

expected: When a contract test fails because a judge returns score < 4, the FAIL row in the post-run rows shows the judge's reasoning text after the em-dash separator (`  <tool>  ✗ FAIL — clarity score 2/5: <reasoning>`). The reasoning should be intelligible to an operator (not raw JSON, not a traceback).

why_human: Requires a live `mcp-test-framework run` against a real Ollama judge or a contrived failing tool. Preflight requires `homelab-mcp` on PATH. Static evidence (failure_message field threaded from JUnit XML at `_runner.py:849`) confirms the wiring exists; the operator-facing reasoning quality / formatting is not statically verifiable.

result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
