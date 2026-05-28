---
phase: quick-260513-chh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/mcp_test_framework/fixtures.py
  - tests/framework/unit/test_session_needs_preflight.py
  - .planning/todos/pending/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md
  - .planning/todos/completed/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md
autonomous: true
requirements: []
must_haves:
  truths:
    - "Running `uv run pytest tests/framework/unit -q` does NOT trigger the live-MCP preflight"
    - "Running `uv run pytest tests/contract` still triggers the preflight (live-MCP scope)"
    - "Running `uv run pytest tests/sdet` still triggers the preflight (live-MCP scope)"
    - "`_session_needs_preflight` returns True if ANY collected item lives under tests/contract/ or tests/sdet/, False otherwise"
    - "Direct unit test pins the new behavior for both live and non-live nodeids"
    - "Todo file is moved from pending/ to completed/ at the end of the plan"
  artifacts:
    - path: "src/mcp_test_framework/fixtures.py"
      provides: "Updated _session_needs_preflight using LIVE_PREFIXES allowlist (Option B from the todo)"
      contains: "LIVE_PREFIXES"
    - path: "tests/framework/unit/test_session_needs_preflight.py"
      provides: "Regression unit test pinning the new live-prefix predicate"
      contains: "def test_"
    - path: ".planning/todos/completed/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md"
      provides: "Closed todo moved from pending/ to completed/"
  key_links:
    - from: "src/mcp_test_framework/fixtures.py::_session_needs_preflight"
      to: "tests/framework/unit/test_session_needs_preflight.py"
      via: "direct function import + fake item objects with nodeid attribute"
      pattern: "from mcp_test_framework.fixtures import _session_needs_preflight"
---

<objective>
Fix the nodeid path mismatch in `_session_needs_preflight` so framework unit tests no longer trigger the live-MCP preflight.

Purpose: After Phase 15's `tests/` reorg, the prefix check `tests/unit/` never matches the current layout (`tests/framework/unit/`), so the preflight always fires — forcing `--noconftest` workarounds or requiring `MCPTF_CONFIG_FILE` to point at a real `homelab-mcp`. The fix follows the todo's Option B: gate preflight on the live-MCP scopes (`tests/contract/`, `tests/sdet/`) rather than on a stale unit-test prefix.

Output:
- Updated `_session_needs_preflight` in `src/mcp_test_framework/fixtures.py`
- New regression test at `tests/framework/unit/test_session_needs_preflight.py`
- Closed todo file (moved pending/ -> completed/)
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/todos/pending/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md
@src/mcp_test_framework/fixtures.py

<interfaces>
<!-- Current function under fix (src/mcp_test_framework/fixtures.py:108-125) -->

```python
def _session_needs_preflight(request: pytest.FixtureRequest) -> bool:
    """Skip preflight if every collected test lives under tests/unit/. ..."""
    items = getattr(request.session, "items", []) or []
    if not items:
        return False
    for item in items:
        # item.nodeid uses forward slashes on every platform pytest supports
        if not item.nodeid.startswith("tests/unit/"):
            return True
    return False
```

<!-- Current pytest layout (confirmed via Glob): -->
- tests/framework/unit/   (pure-data unit tests; ~35 files; MUST NOT trigger preflight)
- tests/framework/smoke/  (framework smoke; no live MCP; MUST NOT trigger preflight)
- tests/framework/        (e.g. test_runner_renderer.py; no live MCP; MUST NOT trigger preflight)
- tests/contract/         (live MCP contract tests; MUST trigger preflight)
- tests/sdet/             (Phase 18 SDET scaffolding; live MCP; MUST trigger preflight)

<!-- Phase 18 renderer / discovery code keys on `tests/contract/` and `tests/sdet/` as the
     authoritative live-MCP scope list. Aligning the preflight predicate to the same
     list (Option B from the todo) keeps a single source of truth. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Invert _session_needs_preflight to a live-scope allowlist + add regression test</name>
  <files>src/mcp_test_framework/fixtures.py, tests/framework/unit/test_session_needs_preflight.py</files>
  <behavior>
    Pin _session_needs_preflight with a direct unit test BEFORE editing the production code (RED -> GREEN). Test cases (all using fake objects with a `.nodeid` str attribute; no pytest session needed beyond a SimpleNamespace stub for `request.session.items`):

    - Test 1: empty items list -> returns False (no items -> nothing to preflight for).
    - Test 2: only `tests/framework/unit/test_foo.py::test_x` items -> returns False (current bug: returns True; this test fails against current code, passes after fix).
    - Test 3: only `tests/framework/smoke/test_foo.py::test_x` items -> returns False.
    - Test 4: only `tests/framework/test_runner_renderer.py::test_x` items -> returns False.
    - Test 5: one item under `tests/contract/test_homelab.py::test_y` -> returns True.
    - Test 6: one item under `tests/sdet/test_scenario.py::test_z` -> returns True.
    - Test 7: mixed — N unit items + one `tests/contract/` item -> returns True (live scope wins).
    - Test 8: mixed — N unit items + one `tests/sdet/` item -> returns True.
    - Test 9 (defensive): a legacy `tests/unit/test_old.py::test_x` nodeid is NOT a live prefix -> returns False (documents that the old prefix is genuinely retired, not silently re-honored).

    Use `types.SimpleNamespace` to fake `request.session.items` with objects exposing only `.nodeid`. Do NOT import pytest fixtures.
  </behavior>
  <action>
    1. Create `tests/framework/unit/test_session_needs_preflight.py` with the 9 cases above. Import via `from mcp_test_framework.fixtures import _session_needs_preflight`. Build a tiny helper:

       ```python
       from types import SimpleNamespace
       def _fake_request(*nodeids: str) -> SimpleNamespace:
           items = [SimpleNamespace(nodeid=n) for n in nodeids]
           return SimpleNamespace(session=SimpleNamespace(items=items))
       ```

       Use plain `def test_...` functions (no asyncio marker). Each test calls `_session_needs_preflight(_fake_request(...))` and asserts True/False.

       Verify RED by running the new tests once against the unmodified production code: `uv run pytest tests/framework/unit/test_session_needs_preflight.py -q` — at least Test 2/3/4 MUST fail (they expect False, current code returns True). This is the RED checkpoint; do not commit yet.

    2. Edit `src/mcp_test_framework/fixtures.py` `_session_needs_preflight` (lines ~108-125) to use the Option B allowlist:

       ```python
       # Live-MCP scopes: items under these prefixes call the real homelab-mcp /
       # Ollama stack and require the preflight gate. Anything else (framework
       # unit/smoke, runner self-tests) must skip preflight so they run on a
       # machine with no homelab-mcp / Ollama configured.
       #
       # Kept in sync with the Phase 18 renderer's scope discrimination
       # (tests/contract vs tests/sdet) — single source of truth for live scopes.
       _LIVE_PREFIXES: tuple[str, ...] = ("tests/contract/", "tests/sdet/")


       def _session_needs_preflight(request: pytest.FixtureRequest) -> bool:
           """Return True iff any collected item is under a live-MCP scope.

           Live-MCP scopes (tests/contract/, tests/sdet/) call into the real
           homelab-mcp subprocess and Ollama HTTP API; everything else
           (tests/framework/...) is pure-data and must not be gated by the
           autouse preflight fixture. Pre-Phase 15 this keyed on
           ``tests/unit/`` which no longer exists in the current layout.
           """
           items = getattr(request.session, "items", []) or []
           if not items:
               return False
           for item in items:
               # item.nodeid uses forward slashes on every platform pytest supports.
               if item.nodeid.startswith(_LIVE_PREFIXES):
                   return True
           return False
       ```

       Also update the in-file docstring on `_preflight` (around lines 145-147) that mentions "only `tests/unit/` items are collected" to instead say "no items under live-MCP scopes (tests/contract/, tests/sdet/) are collected".

    3. Re-run the new test file: `uv run pytest tests/framework/unit/test_session_needs_preflight.py -q` — all 9 tests MUST pass (GREEN).

    4. Run the broader framework unit suite to confirm no other regression: `uv run pytest tests/framework/unit -q -p no:cacheprovider`. It must NOT exit with `homelab-mcp not on PATH` / `returncode=2` from the autouse preflight on a machine without homelab-mcp.

    Note: this fix does not touch `tests/conftest.py` or its `pytest_generate_tests` hook — only the autouse preflight predicate. Indirect parametrization for `target_tool` still operates as before for contract tests.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_session_needs_preflight.py -q</automated>
    <automated>uv run pytest tests/framework/unit -q -p no:cacheprovider --no-header 2>&1 | grep -v "MCP command" || true ; uv run pytest tests/framework/unit -q -p no:cacheprovider --no-header --co | grep -c "test session starts"</automated>
  </verify>
  <done>
    - All 9 new tests in `tests/framework/unit/test_session_needs_preflight.py` pass.
    - `uv run pytest tests/framework/unit -q` does NOT exit with returncode=2 from the preflight on a machine without `homelab-mcp` on PATH.
    - `src/mcp_test_framework/fixtures.py` defines module-level `_LIVE_PREFIXES = ("tests/contract/", "tests/sdet/")` and `_session_needs_preflight` returns True iff any item's nodeid starts with one of them.
    - The `tests/unit/` reference in the prior docstrings is replaced with the new live-scopes wording.
  </done>
</task>

<task type="auto">
  <name>Task 2: Close the todo</name>
  <files>.planning/todos/pending/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md, .planning/todos/completed/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md</files>
  <action>
    Move the todo file from `.planning/todos/pending/` to `.planning/todos/completed/` (per GSD todo-closure pattern). On Windows PowerShell: `git mv` is preferred so history is preserved.

    ```powershell
    git mv .planning/todos/pending/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md .planning/todos/completed/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md
    ```

    If the `.planning/todos/completed/` directory does not exist yet, create it first (`mkdir`). Do NOT edit the todo body — the closure is the move itself.
  </action>
  <verify>
    <automated>test -f .planning/todos/completed/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md && ! test -f .planning/todos/pending/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md</automated>
  </verify>
  <done>
    - Todo file exists under `.planning/todos/completed/` and is absent from `.planning/todos/pending/`.
    - `git status` shows the move as a rename (or delete+add) ready to commit.
  </done>
</task>

</tasks>

<verification>
End-to-end acceptance (matches the todo's Acceptance check):

```
uv run pytest tests/framework -q
```

Expectations:
- No preflight invocation (no `homelab-mcp not on PATH` exit, no `returncode=2`).
- Tests pass or fail on their own merits (any failure must be pre-existing, NOT preflight-related).
- The new `test_session_needs_preflight.py` file is collected and all 9 of its cases pass.

Conversely, on a machine with `MCPTF_CONFIG_FILE` configured for live homelab-mcp:

```
uv run pytest tests/contract -q   # preflight DOES fire (returncode=2 if env absent)
uv run pytest tests/sdet -q       # preflight DOES fire
```

This second pair is a behavior-preservation check, not a CI gate for this quick task.
</verification>

<success_criteria>
- [ ] `_session_needs_preflight` returns False for any combination of `tests/framework/...` nodeids and True iff any nodeid starts with `tests/contract/` or `tests/sdet/`.
- [ ] `tests/framework/unit/test_session_needs_preflight.py` exists and all 9 cases pass.
- [ ] `uv run pytest tests/framework -q` runs without triggering the preflight gate on a machine without `homelab-mcp`.
- [ ] Todo file moved from `.planning/todos/pending/` to `.planning/todos/completed/`.
- [ ] No edits to `tests/conftest.py`, `tests/contract/`, or `tests/sdet/` (out of scope for this fix).
</success_criteria>

<output>
After completion, create `.planning/quick/260513-chh-fix-session-needs-preflight-nodeid-path-/260513-chh-SUMMARY.md` documenting:
- The before/after of `_session_needs_preflight` (old `tests/unit/` check vs new `_LIVE_PREFIXES` allowlist).
- The 9 regression-test cases pinned in `tests/framework/unit/test_session_needs_preflight.py`.
- Confirmation that `uv run pytest tests/framework -q` no longer triggers preflight.
- Note that this closes the deferral repeatedly logged in Phase 18 plans 18-02, 18-03, and 18-08 SUMMARYs.
</output>
