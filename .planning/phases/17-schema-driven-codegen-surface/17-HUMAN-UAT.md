---
status: partial
phase: 17-schema-driven-codegen-surface
source: [17-VERIFICATION.md]
started: 2026-05-13
updated: 2026-05-13
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live `gen-sdet-classes` against real homelab-mcp
expected: Operator runs `mcp-test-framework gen-sdet-classes` against live homelab-mcp with a real `config.yaml`, then inspects `src/mcp_test_framework/sdet/generated/homelab_mcp/`. Every advertised tool produces a `<tool>.py` file with PascalCase Params + Response classes; `__init__.py` re-exports + `_REGISTRY` populated; stdout digest shows server name + version + slug + tool count + degraded count; rerunning produces byte-identical output modulo the Regenerated timestamp line.
result: [pending]

### 2. Pyright strict against the live-generated tree
expected: Operator runs `uv run pyright src/mcp_test_framework/sdet/generated/homelab_mcp/` after the live codegen run. Exit 0 — every Params/Response class type-checks clean under strict mode, including degraded `typing.Any` fields. Real homelab-mcp schemas surface enum/oneOf/anyOf/nested-object combinations the synthetic 5-tool fixture doesn't model.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
