---
created: 2026-05-13T15:57:07.113Z
title: Fix _session_needs_preflight nodeid path mismatch
area: testing
files:
  - src/mcp_test_framework/fixtures.py:108-123
  - tests/framework/unit/ (target dir)
  - tests/contract/ (current expected scope)
  - tests/sdet/ (Phase 18 new scope — may need same treatment)
---

## Problem

`_session_needs_preflight` in `src/mcp_test_framework/fixtures.py:123` short-circuits the live-MCP preflight when *all* collected items are unit tests, using:

```python
if not item.nodeid.startswith("tests/unit/"):
    return True  # need preflight
```

But this project's unit tests don't live under `tests/unit/` — they live under `tests/framework/unit/`. So the startswith check NEVER matches, and the preflight fires for framework unit tests even though they don't touch the live MCP server. This forces operators to either:

- Set `MCPTF_CONFIG_FILE` to a config pointing at `uvx homelab-mcp` (so the preflight can succeed), or
- Run with `--noconftest` to bypass session fixtures entirely (loses other useful setup).

This was repeatedly hit during Phase 18 execution — documented as an out-of-scope deferral in plans 18-02 SUMMARY, 18-03 SUMMARY, and 18-08 SUMMARY. It's also why the Phase 18 verifier ran with `--noconftest`.

Phase 15 (operator-vs-framework-test-surface-split, v1.2) moved tests into `tests/framework/`, `tests/contract/`, etc. but the nodeid check in `fixtures.py` was never updated to match.

Phase 18 also introduces `tests/sdet/` which DOES need preflight (live MCP) — so the fix needs to think about scope, not just rename the prefix.

## Solution

Update the check at `fixtures.py:123` to recognize the current test layout. One-liner candidates:

```python
# Option A: explicit set of unit-test prefixes
UNIT_PREFIXES = ("tests/framework/unit/", "tests/framework/smoke/")
if not item.nodeid.startswith(UNIT_PREFIXES):
    return True

# Option B: invert — preflight required only when items live under known live-MCP scopes
LIVE_PREFIXES = ("tests/contract/", "tests/sdet/")
if item.nodeid.startswith(LIVE_PREFIXES):
    return True
return False  # all items are non-live, skip preflight
```

Option B is more aligned with Phase 18's `--sdet` scope discipline — the preflight gate keys on "does this item need a live MCP server?" rather than "is this item a unit test?". Phase 18's renderer also keys on `tests/contract/` vs `tests/sdet/` so the prefix list is already authoritative.

Independent of Phase 19 — this is a small, isolated infrastructure fix. Worth a `/gsd-quick` slot.

Acceptance check after fix:

```
uv run pytest tests/framework -q
# expect: no preflight invocation, no `homelab-mcp not on PATH` exit
```
