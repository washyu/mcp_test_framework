---
phase: 20-preflight-conditional-skip
plan: 04
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/sdet/test_proxmox_vm_lifecycle.py
  - tests/sdet/test_basic_call.py
autonomous: true
requirements:
  - CLEANUP-DOGFOOD-01
must_haves:
  truths:
    - "tests/sdet/test_proxmox_vm_lifecycle.py does not exist after this plan runs"
    - "tests/sdet/test_basic_call.py does not exist after this plan runs"
    - "tests/sdet/__init__.py and tests/sdet/conftest.py still exist (framework infrastructure preserved)"
    - "Running `uv run pytest tests/framework/` does not collect any tests from tests/sdet/ (because the SDET scope is opt-in via --sdet; this is unchanged)"
    - "`uv run pytest --collect-only tests/sdet/` collects zero tests"
  artifacts:
    - path: "tests/sdet/__init__.py"
      provides: "Empty package marker (preserved — frame infrastructure)"
    - path: "tests/sdet/conftest.py"
      provides: "JUnit user_properties hook for ToolCallError (preserved — framework infrastructure)"
  key_links:
    - from: "tests/sdet/"
      to: "tests/framework/"
      via: "SUT-specific scenarios live in operator UATs only; framework self-tests live under tests/framework/"
      pattern: "tests/sdet/test_.*\\.py"
---

<objective>
Implement CONTEXT.md D-04 (delete `tests/sdet/test_proxmox_vm_lifecycle.py` outright) and D-06 (remove `tests/sdet/test_basic_call.py` — same logic as D-04, strengthens the framework-self-tests-don't-touch-SUT boundary). Preserve framework infrastructure (`__init__.py`, `conftest.py`).

Purpose: Restore alignment between the shipped test suite and the framework-primitives principle. SUT-specific scenarios belong to operator UATs and a future hello-world MCP CI fixture — not to the project's own test suite.
Output: Two test files removed from `tests/sdet/`. Framework infrastructure files preserved.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/20-preflight-conditional-skip/20-CONTEXT.md
@tests/sdet/__init__.py
@tests/sdet/conftest.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Delete tests/sdet/test_proxmox_vm_lifecycle.py and tests/sdet/test_basic_call.py</name>
  <files>tests/sdet/test_proxmox_vm_lifecycle.py, tests/sdet/test_basic_call.py</files>
  <read_first>
    - tests/sdet/test_proxmox_vm_lifecycle.py (read once to confirm what's being deleted — verify it's the Phase 19 Proxmox dogfood)
    - tests/sdet/test_basic_call.py (read once to confirm it's the read-only `list_registered_servers` sanity test that requires a live MCP)
    - tests/sdet/conftest.py (DO NOT modify — confirm this is the JUnit user_properties hook that stays)
    - tests/sdet/__init__.py (DO NOT modify — confirm it's the empty package marker)
    - .planning/phases/20-preflight-conditional-skip/20-CONTEXT.md (D-04, D-06)
  </read_first>
  <action>
This task deletes TWO files from `tests/sdet/`. No archive, no `@pytest.mark.skip` decorator, no comment-out. Files are removed from the working tree.

**D-04 (locked):** Delete `tests/sdet/test_proxmox_vm_lifecycle.py` — the Phase 19 dogfood. The architectural patterns it demonstrated (module-scope yield fixture, ScenarioState dataclass, cleanup-on-failure, VMID isolation) survive in Phase 19's CONTEXT.md and SUMMARY artifacts for Phase 21 docs to lift into `docs/SDET-AUTHORING.md`.

**D-06 disposition decision (planner-locked):** Delete `tests/sdet/test_basic_call.py` as well. Rationale per CONTEXT.md D-06 option (c): "by the same logic as D-04, it's exercising a specific MCP server. Defers the 'hello-world MCP' work to surface this kind of sanity check in CI." This is the cleanest disposition — after this plan, `tests/sdet/` contains only framework infrastructure (`__init__.py`, `conftest.py`) and is ready to host operator-authored SUT-specific scenarios per the SDET persona.

**Files to PRESERVE (do not touch):**
- `tests/sdet/__init__.py` — empty package marker
- `tests/sdet/conftest.py` — Phase 18 JUnit user_properties hook (still needed for any future SDET tests an operator authors)

**Execution steps:**

1. Confirm via read that `tests/sdet/test_proxmox_vm_lifecycle.py` exists and is the Phase 19 dogfood (contains `create_proxmox_vm` / `manage_proxmox_vm` / `delete_proxmox_vm` references).
2. Confirm via read that `tests/sdet/test_basic_call.py` exists and is the read-only `list_registered_servers` sanity test (contains `tool("list_registered_servers")`).
3. Delete `tests/sdet/test_proxmox_vm_lifecycle.py` using a filesystem delete (PowerShell `Remove-Item` or `git rm` if the file is tracked).
4. Delete `tests/sdet/test_basic_call.py` using the same approach.
5. Verify `tests/sdet/__init__.py` and `tests/sdet/conftest.py` still exist and are byte-identical to their pre-task state.

Use `git rm tests/sdet/test_proxmox_vm_lifecycle.py tests/sdet/test_basic_call.py` if both files are tracked (preferred — stages the deletion); otherwise plain filesystem deletion. Do NOT touch any file outside `tests/sdet/`.
  </action>
  <verify>
    <automated>powershell -NoProfile -Command "$proxmox_gone = -not (Test-Path 'tests/sdet/test_proxmox_vm_lifecycle.py'); $basic_gone = -not (Test-Path 'tests/sdet/test_basic_call.py'); $init_present = Test-Path 'tests/sdet/__init__.py'; $conftest_present = Test-Path 'tests/sdet/conftest.py'; $collect = (& uv run pytest --collect-only tests/sdet/ 2>&1 | Out-String); $ok = $proxmox_gone -and $basic_gone -and $init_present -and $conftest_present; Write-Host \"proxmox_gone=$proxmox_gone basic_gone=$basic_gone init_present=$init_present conftest_present=$conftest_present\"; if(-not $ok){ exit 1 }; exit 0"</automated>
  </verify>
  <acceptance_criteria>
    - `Test-Path 'tests/sdet/test_proxmox_vm_lifecycle.py'` returns `False`.
    - `Test-Path 'tests/sdet/test_basic_call.py'` returns `False`.
    - `Test-Path 'tests/sdet/__init__.py'` returns `True`.
    - `Test-Path 'tests/sdet/conftest.py'` returns `True`.
    - `tests/sdet/conftest.py` file content is byte-identical to its pre-task state (a quick way: confirm the file still contains the string `"ToolCallError -> JUnit user_properties hook"` from its docstring and the function `def pytest_exception_interact(node, call, report):`).
    - `uv run pytest --collect-only tests/sdet/` reports `0 tests collected` (or exits gracefully — what matters is that no test items are listed from `tests/sdet/`; if `--sdet` flag is required for collection, the result may be "no tests ran" or similar, which also satisfies the invariant).
    - `git status` shows both deleted files staged for commit (if working in a git tree).
  </acceptance_criteria>
  <done>Both SUT-specific test files removed; framework infrastructure (`__init__.py`, `conftest.py`) preserved unchanged; `tests/sdet/` collects zero tests; no other paths in the repo touched.</done>
</task>

</tasks>

<verification>
After this plan: `tests/sdet/` contains only `__init__.py` and `conftest.py`. Running `uv run pytest tests/framework/` is unaffected. Running `uv run pytest --sdet` against a live MCP collects zero SDET tests (the directory has no test files but the discovery scope still resolves cleanly).
</verification>

<success_criteria>
- D-04 satisfied: the Phase 19 Proxmox dogfood is gone from the working tree.
- D-06 satisfied: `test_basic_call.py` removed per option (c) — the cleanest disposition, fully consistent with the framework-self-tests-don't-touch-SUT boundary.
- Framework infrastructure preserved: future SDET-authored scenarios can land in `tests/sdet/` without re-creating `__init__.py` or the JUnit hook.
</success_criteria>

<output>
After completion, create `.planning/phases/20-preflight-conditional-skip/20-04-SUMMARY.md`. Document the D-06 disposition choice (option c) in the SUMMARY for downstream Phase 21 doc work — Phase 21 may want to mention the deferred hello-world MCP CI fixture as the place where this kind of sanity check will land.
</output>
