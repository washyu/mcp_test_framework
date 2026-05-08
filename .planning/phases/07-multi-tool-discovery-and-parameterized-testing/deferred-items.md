# Deferred Items — Phase 07

Items discovered during Phase 07 plan 01 execution that are out-of-scope for this plan's task surface.

## Pre-existing ruff I001 in `src/mcp_test_framework/rubrics.py`

**Discovered during:** Task 3 verification (`uv run ruff check src tests`).

**Issue:** `rubrics.py:13` triggers `I001 Import block is un-sorted or un-formatted`. The error pre-dates Phase 07 (verified by `git stash` of all phase 07 changes — error still present).

**Why deferred:** Out of scope. Phase 07 plan 01 modifies `models.py`, `fixtures.py`, `tests/conftest.py`, and renames `test_homelab_list_registered_servers.py` → `test_mcp_tool_contract.py`. The plan's `<action>` blocks explicitly do not touch `rubrics.py`. Per executor scope-boundary rule, pre-existing lint errors are not auto-fixed.

**Resolution path:** Single-line fix (`uv run ruff check --fix src/mcp_test_framework/rubrics.py`) or roll into Phase 08 / a future cleanup chore.
