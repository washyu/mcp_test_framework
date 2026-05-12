---
status: complete
phase: 16-reporter-ux-overhaul
source: [16-VERIFICATION.md]
started: 2026-05-12T00:00:00Z
updated: 2026-05-12T00:00:00Z
---

## Current Test

[complete]

## Tests

### 1. Per-judge reasoning surfaces in domain UI tail at runtime (UX-03 / SC-3)

expected: When a contract test fails because a judge returns score < 4, the FAIL row in the post-run rows shows the judge's reasoning text after the em-dash separator (`  <tool>  ✗ FAIL — clarity score 2/5: <reasoning>`). The reasoning should be intelligible to an operator (not raw JSON, not a traceback).

why_human: Requires a live `mcp-test-framework run` against a real Ollama judge or a contrived failing tool. Preflight requires `homelab-mcp` on PATH. Static evidence (failure_message field threaded from JUnit XML at `_runner.py:849`) confirms the wiring exists; the operator-facing reasoning quality / formatting is not statically verifiable.

result: pass

evidence: Operator ran `uv run mcp-test-framework run --config .\config.yaml` on 2026-05-12 against live `uvx homelab-mcp` + Ollama (`qwen3:0.6b`). Both selected tools (`list_keyring_credentials`, `suggest_deployments`) produced FAIL rows of the form `✗ FAIL — AssertionError: clarity score 2 < 4. reasoning="..."` — judge name (clarity), score (2), and full reasoning text intelligibly surfaced after the em-dash. Format meets UX-03 / SC-3 acceptance.

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

### G-1 (new — found during live UAT, not in scope of UX-03 test) — Digest `Judges:` line reports `(none configured)` when judges actually ran

source: same live-UAT run that confirmed UX-03 above

observed: Pre-run digest emitted `Judges:      (none configured)` for a config with `tools: {list_keyring_credentials: {}, suggest_deployments: {}}` — but the subsequent test run failed both tools on clarity-rubric assertions, proving all three rubrics fired. The digest's `Judges:` line contradicts what the runner actually executed.

root_cause: `cli.py:512-516` does not honor the `judges: None` → "run all rubrics" semantic established by `models.py:98` + `TOOLCFG-06` + contract gates at `test_mcp_tool_contract.py:124,154,185`.

resolution: Tracked as a new gap in `16-VERIFICATION.md` (frontmatter `gaps_remaining[0]`). Will be addressed by gap-closure plan 16-05.
