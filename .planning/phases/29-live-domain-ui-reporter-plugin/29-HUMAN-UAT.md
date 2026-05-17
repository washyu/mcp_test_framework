---
status: partial
phase: 29-live-domain-ui-reporter-plugin
source: [29-VERIFICATION.md]
started: 2026-05-17T00:00:00Z
updated: 2026-05-17T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live-TTY `mcp-contracts run` smoke (CR-01 fix verification)
expected: Run `mcp-contracts run --config <fixture pointing at a real or stub MCP server with at least one tool>` from a real terminal. Header appears before pytest collection finishes; per-tool rows appear as tests complete (or at least before the final `Result:` line); `Result:` summary appears at session end. Banner is NOT swallowed and is NOT duplicated.
result: [pending]
why_human: Stream-stdout vs. capture-stdout behavior under a real TTY (not the captured-output mode all framework tests use) is the exact seam CR-01 fixed; no automated test exercises `mcp-contracts run` against a real subprocess with `stdout=None` inherited. Plan 03 SUMMARY explicitly notes this smoke was not attempted.

### 2. `pytest --mcp-domain-ui -n auto` xdist smoke (REPORTER-02 SC4)
expected: Install pytest-xdist (`uv add --dev pytest-xdist`) and run `pytest --mcp-domain-ui -n auto` against a payload with `[<tool>]`-parametrized tests across multiple workers. The `MCP Test Framework` banner appears EXACTLY ONCE (controller-only emission); per-tool rows aggregate test results from all workers; worker-side raw output is not multiplexed into the per-tool render.
result: [pending]
why_human: `test_xdist_master_only_emission` is gated with `pytest.importorskip('xdist')` and SKIPS in the dev environment. The duck-typed `hasattr(config, 'workerinput')` probe is in place at two code sites and the design is sound, but the operator-facing assumption A3 (controller forwards events; banner count==1) is unverified at runtime.

### 3. REQUIREMENTS.md REPORTER-02 doc sync decision
expected: Open `.planning/REQUIREMENTS.md` line 53 and line 128. Either flip `[ ]` → `[x]` for REPORTER-02 AND update the traceability row `REPORTER-02 | Phase 29 | Pending` → `Complete`, OR explicitly hold REPORTER-02 open pending the xdist smoke above (record the decision).
result: [pending]
why_human: Traceability table out-of-date. Code-wise REPORTER-02 is satisfied (separate pytest11 key, worker no-op, `-p no:` disable verified). The choice is documentation timing — close now, or hold pending xdist UAT.

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
