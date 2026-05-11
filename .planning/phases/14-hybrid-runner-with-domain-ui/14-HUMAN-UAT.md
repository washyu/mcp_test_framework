---
status: partial
phase: 14-hybrid-runner-with-domain-ui
source: [14-VERIFICATION.md]
started: 2026-05-11
updated: 2026-05-11
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live smoke suite against real homelab-mcp + Ollama

command: `MCPTF_CONFIG_FILE=$(pwd)/config-v2-worktree.yaml uv run pytest tests/test_runner_live_smoke.py -m live_homelab --no-header`
expected: All 3 live smoke tests pass — domain header strings present, `--junit-xml=PATH` populated, `--raw` emits pytest framing.
why_human: `tests/test_runner_live_smoke.py` spawns a real `uv run mcp-test-framework run` subprocess against a reachable MCP server + Ollama. Marker `live_homelab` is skipped by default; the verifier agent could not exercise it.
result: [pending]

### 2. End-to-end live run against configured homelab-mcp

command: `uv run mcp-test-framework run`
expected:
  - Output begins with header lines: `========================================`, `MCP Test Framework`, `MCP server:`, `Discovered:`, `Running:`, `Skipping:`, `Judges:`, `Test plan:`
  - Per-tool rows in FAIL → SKIP → PASS order with em-dash (U+2014) separator on detail lines
  - Ends with `Result: N PASS / M FAIL [/ K SKIP]  in T.Ts`
  - No `=== test session starts ===` framing, no `[<tool>]` parametrize-id suffixes leak
  - Exit codes: 0 (all pass), 1 (failures), 2 (config), 130 (Ctrl+C)
why_human: End-to-end visual verification against the live SUT; cannot be programmatically asserted without a real server.
result: [pending]

### 3. Verbosity ladder transitions (`-q`, `--debug`, `-q --debug`, `--raw`)

command: `uv run mcp-test-framework run -q` then `--debug` then `-q --debug` then `--raw`
expected:
  - `-q`: prints only `Result: ...` summary line
  - `--debug`: appends `--- raw pytest output ---` then captured stdout/stderr AFTER the domain UI
  - `-q --debug`: summary line then debug appendix (no header section)
  - `--raw`: full pytest framing (no domain UI), but `_load_config` pre-flight still runs
why_human: Operator-perceptible verbosity composition; unit tests pin the helpers but the live layered output is a visual contract.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
