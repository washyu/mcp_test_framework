---
phase: 12
plan: 03
subsystem: docs/config
tags: [config, examples, docs, clean-02, clean-03]
requires: [12-01]
provides:
  - examples/homelab-mcp.yaml (worked v1.1 reference, history preserved via --follow)
  - config.example.yaml as 3-pattern hand-curated TEMPLATE (placeholder names, no target:)
  - tests/unit/test_config_example.py Wave-0 regression guard (10 tests)
affects:
  - operators copying config.example.yaml see template, not homelab specifics
  - Plan 01's deferred test_examples_homelab_mcp_yaml_exists now PASSES (was SKIPPED)
tech-stack:
  added: []
  patterns:
    - "atomic git mv + recreate in same commit (history preserved via --follow)"
    - "Wave-0 regression guard pattern: pyyaml + regex banned-token grep + structural assertions"
key-files:
  created:
    - examples/homelab-mcp.yaml
    - tests/unit/test_config_example.py
  modified:
    - config.example.yaml (full rewrite: 242 -> 59 lines, placeholder template)
decisions:
  - "Pattern A entry uses judges-only (clarity, disambiguation, parameters) to demonstrate minimal opt-in without call_arguments — D-13 says 'minimal opt-in' but lets the planner pick the exact rubrics"
  - "Pattern C destructive_tool_c skip_reason = 'destructive: writes to production inventory' — concrete, operator-recognisable example of the SAFE-by-default posture (Phase 13 lock-in target)"
  - "Used PyYAML safe_load for parser-validation in tests (already a transitive dep of pydantic-settings[yaml]); did not add a direct dep"
metrics:
  duration: ~5min
  completed: 2026-05-09
---

# Phase 12 Plan 03: Split config.example.yaml into placeholder template + worked example - Summary

## One-liner

Split `config.example.yaml` into a 3-pattern hand-curated placeholder TEMPLATE at the repo root and a bytes-faithful worked reference at `examples/homelab-mcp.yaml`, with `git --follow` history preserved and a 10-test Wave-0 regression guard pinning the contract.

## What Shipped

**Task 1 (commit `dfdbaf4`):** Atomic `git mv config.example.yaml -> examples/homelab-mcp.yaml` followed by immediate rewrite of `config.example.yaml` as a 3-pattern placeholder template. The rewrite drops the `target:` block (D-03), uses three placeholder tool names (`<safe_read_tool_a>`, `<safe_read_tool_b>`, `<destructive_tool_c>` per D-13), references `mcp-test-framework config-init -o config.yaml` and `examples/homelab-mcp.yaml` (D-14), and contains zero spec IDs (CLEAN-01 verified via grep).

**Task 2 (commit `446f346`):** `tests/unit/test_config_example.py` — 10 unit tests pinning the 3-pattern shape, parseability, banned-token absence, link contract, and per-pattern entry semantics. Plan 01's previously-skipped `test_examples_homelab_mcp_yaml_exists` now PASSES because Task 1 landed the file.

## Verification Evidence

```
$ git log --follow --format='%H %s' examples/homelab-mcp.yaml | head -3
dfdbaf4347c4938995d0a1c683215b79c23c36c7 feat(12-03): split config.example.yaml ...
464e934ca7f54ac82e39194f1ccc55a99460477b fix(quick/260507-n0g): unset target.tool_name ...
0d8337b6b6694921a86a6f7adf60ca8f94ba6e02 fix(quick/260507-n0g): safe-by-default tool skips ...
```
Rename history preserved (5 commits visible across the move boundary).

```
$ wc -l config.example.yaml
59 config.example.yaml
```
59 lines — within the 50-80 plan range; v1.1 was 242 lines.

```
$ uv run pytest tests/unit/test_config_example.py tests/unit/test_examples_dir.py -x
============================= 14 passed in 0.07s ==============================
```

```
$ uv run pytest tests/unit/ -x --timeout=30
============================= 81 passed in 0.71s ==============================
```
No regressions across the full unit-test surface.

```
$ grep -c '<safe_read_tool_a>' config.example.yaml  # -> 1
$ grep -c '<safe_read_tool_b>' config.example.yaml  # -> 1
$ grep -c '<destructive_tool_c>' config.example.yaml  # -> 1
$ grep -cE '^target:' config.example.yaml  # -> 0
$ grep -c 'config-init' config.example.yaml  # -> 1
$ grep -c 'examples/homelab-mcp.yaml' config.example.yaml  # -> 1
$ grep -cE '(Phase [0-9]|Plan [0-9]-[0-9]|TOOLCFG-|ISOL-|OUTPUT-|D-[0-9]+|[0-9]{6}-[a-z0-9]{3})' config.example.yaml  # -> 0
```
All success-criteria proofs pass.

```
$ grep -c 'TOOLCFG-' examples/homelab-mcp.yaml  # -> 2
```
v1.1 spec IDs preserved in the worked example (Open Question 1 — `examples/` is reference material, not primary docs).

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Atomic git mv + rewrite config.example.yaml | `dfdbaf4` | `config.example.yaml` (rewritten), `examples/homelab-mcp.yaml` (created via mv) |
| 2 | Wave-0 regression guard test | `446f346` | `tests/unit/test_config_example.py` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test count: plan acceptance_criteria says "nine test functions" but plan body lists ten**

- **Found during:** Task 2 verification
- **Issue:** The plan's `<acceptance_criteria>` for Task 2 says "tests/unit/test_config_example.py exists with nine test functions" but the literal test code in the `<action>` block defines ten test functions (`test_config_example_yaml_exists`, `test_config_example_yaml_parses`, `test_config_example_has_three_placeholder_tools`, `test_config_example_no_target_block`, `test_config_example_links_config_init_and_examples`, `test_config_example_no_banned_tokens`, `test_config_example_has_three_pattern_comments`, `test_config_example_pattern_a_has_judges`, `test_config_example_pattern_b_has_call_arguments`, `test_config_example_pattern_c_has_skip_with_reason`).
- **Fix:** Followed the literal `<action>` block (10 tests) rather than the off-by-one count in `<acceptance_criteria>`. The behavior block also enumerates the same 10 behaviours via the three pattern-shape tests (a/b/c), so 10 is the intended count.
- **Files modified:** none (matches plan body verbatim)
- **Commit:** `446f346`

### Other deviations

None — the rest of the plan executed exactly as written.

## CLAUDE.md Compliance

- Did NOT import or read `homelab-mcp` source — the worked example file at `examples/homelab-mcp.yaml` was moved bytes-identically via `git mv` from the existing `config.example.yaml` (which was already in-tree).
- Used `uv run pytest` per project tooling convention.
- Test file uses pure-sync pyyaml-based assertions; no `@pytest.mark.asyncio` markers added (matches `pytest-asyncio` strict-mode rule from CLAUDE.md).
- All YAML scalars JSON-quoted where the value would otherwise be ambiguous (Pitfall 2 from research) — `base_url`, `model`, `command`, `args` items, `skip_reason`.

## Threat Model Compliance

| Threat ID | Disposition | Status |
|-----------|-------------|--------|
| T-12-06 (Tampering — config.example.yaml) | mitigate | DONE — `test_config_example_has_three_placeholder_tools` blocks reintroduction of homelab-specific tool names |
| T-12-07 (Information Disclosure — examples/homelab-mcp.yaml) | accept | N/A — bytes-identical move; no new disclosure |
| T-12-08 (Elevation of Privilege — config.example.yaml) | mitigate | DONE — placeholder names like `<safe_read_tool_a>` cannot match any real MCP tool, so wholesale-copy results in zero tools running. Pattern C entry models the opt-out posture. |

## Self-Check: PASSED

- File `config.example.yaml` exists: FOUND
- File `examples/homelab-mcp.yaml` exists: FOUND
- File `tests/unit/test_config_example.py` exists: FOUND
- Commit `dfdbaf4` exists: FOUND (`feat(12-03): split config.example.yaml ...`)
- Commit `446f346` exists: FOUND (`test(12-03): add Wave-0 regression guard ...`)
- All 14 plan-relevant tests pass: VERIFIED (`pytest tests/unit/test_config_example.py tests/unit/test_examples_dir.py`)
- Full unit-test surface still green: VERIFIED (81 passed)
