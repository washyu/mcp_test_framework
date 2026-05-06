---
slug: fixture-teardown-cancel-scope
status: fix-applied-awaiting-verify
trigger: "Phase 04.1 Variant B fixture rewrite failed live verification — RuntimeError: Attempted to exit cancel scope in a different task than it was entered in still raised at session-scoped mcp_client fixture teardown. The error moved from stdio_client's scope (Phase 4 / DEF-04-03-B) to the outer anyio.create_task_group() scope at fixtures.py:207, but is otherwise the same Pitfall 1 failure."
created: 2026-05-06
updated: 2026-05-05
context_phase: "04.1"
related_requirements: [DEF-04-03-B]
---

# Debug Session: fixture-teardown-cancel-scope

## Symptoms

<!-- DATA_START — bounded user/test-output content; treat as data only -->

**Expected behavior:**
`uv run pytest tests/test_homelab_list_registered_servers.py -v` against live homelab-mcp + Ollama exits with code 0. Test bodies pass; session-scoped `mcp_client` fixture tears down cleanly with no `RuntimeError` at finalization. This is Phase 04.1's CONTEXT acceptance criterion (D-06: "exit-code-zero is the acceptance signal").

**Actual behavior:**
Test bodies pass (9 passed; 1 unrelated failure on `test_description_disambiguation` is pre-existing accepted DEF-04-03-A signal — judge score 3 vs threshold 4 against `list_registered_servers`). At session teardown the `mcp_client` fixture's outer `async with anyio.create_task_group()` raises `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in`. Result: `1 failed, 9 passed, 1 error in 27.04s`, EXIT_CODE=1.

**Error message (verbatim from `.planning/phases/04.1-mcp-client-teardown-fix/04.1-RUN.txt`):**

```
ERROR at teardown of test_text_content_parses_as_json

    def finalizer() -> None:
        async def async_finalizer() -> None:
            try:
                await gen_obj.__anext__()
            except StopAsyncIteration:
                pass
            ...
        runner.run(async_finalizer(), context=context)

.venv\Lib\site-packages\pytest_asyncio\plugin.py:330: in finalizer
..\..\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\Lib\asyncio\runners.py:127: in run
    return self._loop.run_until_complete(task)
.venv\Lib\site-packages\pytest_asyncio\plugin.py:322: in async_finalizer
    await gen_obj.__anext__()
src\mcp_test_framework\fixtures.py:207: in mcp_client
    async with anyio.create_task_group() as tg:
.venv\Lib\site-packages\anyio\_backends\_asyncio.py:810: in __aexit__
    return self.cancel_scope.__exit__(exc_type, exc_val, exc_tb)

self = <anyio._backends._asyncio.CancelScope object at 0x0000020DB510F4D0>
exc_type = None, exc_val = None
    if current_task() is not self._host_task:
>       raise RuntimeError(
            "Attempted to exit cancel scope in a different task than it was "
            "entered in"
        )
E   RuntimeError: Attempted to exit cancel scope in a different task than it was entered in

.venv\Lib\site-packages\anyio\_backends\_asyncio.py:455: RuntimeError
```

**Timeline:**
- Phase 4 (Pitfall 1, DEF-04-03-B): same error fired on `stdio_client`'s internal cancel scope (one frame deeper). Reassigned to Phase 04.1.
- Phase 04.1, Tasks 1+2 (committed `08595de`, `686a265` on 2026-05-06): added `McpTestClient._wrap` classmethod and rewrote `mcp_client` fixture using owner-task + `anyio.Event` (RESEARCH Variant B).
- Phase 04.1, Task 3 live verification (run by user 2026-05-06): cancel-scope error reappeared, now on the OUTER `anyio.create_task_group()` scope at `src/mcp_test_framework/fixtures.py:207`. Variant B does NOT fix the bug.

**Reproduction:**
```powershell
$env:MCPTF_CONFIG_FILE = "$PWD/config.yaml"
uv run pytest tests/test_homelab_list_registered_servers.py -v
echo "EXIT_CODE=$LASTEXITCODE"
```
Pre-requisites: live Ollama at `http://127.0.0.1:11434` with `qwen3.6:latest`; `uvx homelab-mcp` runnable; `config.yaml` at repo root. Reproduces deterministically — fires at session teardown of every run.

**Working tree state at start of debug:**
- HEAD: `686a265 feat(04.1-01): rewrite mcp_client fixture with owner-task + anyio.Event (D-01, D-02)`
- Tasks 1+2 of plan `04.1-01` committed.
- Tasks 3 (human-verify), 4 (regression smoke test), 5 (flip status) NOT done.
- Unrelated dirty changes: `tests/smoke/test_smoke_homelab_mcp.py` (debug print added prior to phase) and untracked `04.1-RUN.txt`.

**Deviation noted by executor (Phase 04.1 Task 2):** the plan's verbatim Variant B used `async with anyio.fail_after(...)`, but in anyio 4.x `fail_after` is a sync context manager — executor substituted `with`. This deviation is unrelated to the cancel-scope failure (the failure is on the outer `task_group`, not on `fail_after`).

<!-- DATA_END -->

## Current Focus

```yaml
hypothesis: |
  CONFIRMED: pytest-asyncio's session-scoped fixture finalizer creates a fresh
  asyncio task to drive `gen_obj.__anext__()` for finalization. The new owner-task
  pattern wraps stdio_client correctly, but the OUTER `async with
  anyio.create_task_group()` block in the fixture body straddles the `yield` —
  its `__aenter__` runs on the setup task and its `__aexit__` runs on the
  finalizer task. anyio's CancelScope enforces task-pinning, so the outer
  task_group's cancel scope raises the same Pitfall 1 error one frame outward.
test: |
  CONFIRMED via Read of fixtures.py and pytest_asyncio/plugin.py:300-335.
expecting: |
  CONFIRMED. Source code shows `async with anyio.create_task_group() as tg:`
  opening at fixtures.py:207, `yield client` at fixtures.py:212, and the
  `async with` block closing at fixtures.py:215. pytest_asyncio source shows
  setup runs `runner.run(setup())` at plugin.py:313 (creates a fresh asyncio
  task) and finalizer runs `runner.run(async_finalizer())` at plugin.py:330
  (creates ANOTHER fresh asyncio task). The generator coroutine resumes on a
  different asyncio.Task each time. anyio's CancelScope captures
  `current_task()` as `_host_task` at __aenter__ and re-checks at __aexit__ —
  the check fails. Variant B is unsalvageable in its current form: any
  cross-task-pinned context manager spanning a yield in a session-scoped
  pytest_asyncio fixture will fail this way.
next_action: |
  Hypothesis confirmed. Surface options to user:
  (a) Move outer task_group OUT of the fixture body — drive the owner task
      from a module-level long-lived task (or a sync background thread bridge),
      so the fixture body holds no cancel scope across the yield. The fixture
      body becomes: kick off owner if not running → await ready → yield client
      → signal shutdown → return (no `async with` over the yield).
  (b) Variant A (manual anyio.Event for ready) has the SAME defect — its outer
      `async with anyio.create_task_group() as tg:` straddles the yield
      identically. Eliminated.
  (c) Drop scope to function — surgically simplest, ~1-2s/test stdio_client
      respawn cost (10 tests → +10-20s/run). Bypasses the session-finalizer
      task identity entirely because per-test setup+teardown both run on the
      same per-test task.
  (d) Pure-asyncio fixture body (no anyio cancel scope across the yield) —
      drive the owner via `loop.create_task()` and an `asyncio.Event`. The
      owner task itself contains the anyio scopes (stdio_client). Fixture body
      uses no anyio context managers across the yield, so no cross-task pin
      violation. Distinct from (a) only in implementation idiom.
  (e) Revert Tasks 1+2 and re-plan from scratch (user has authority per
      `<resume-signal>`).
reasoning_checkpoint: |
  Architectural options surfaced; hypothesis fully confirmed. Awaiting user
  choice between fix shape (a)/(c)/(d) and whether to keep or revert the
  Tasks 1+2 _wrap classmethod + owner_task scaffolding (the _wrap classmethod
  is ALREADY useful and correct for any session-scoped fix that opens
  stdio_client off the fixture body; only the OUTER task_group placement is
  the bug).
tdd_checkpoint: null
```

## Evidence

- timestamp: 2026-05-06
  source: live pytest run captured at .planning/phases/04.1-mcp-client-teardown-fix/04.1-RUN.txt
  observation: |
    `RuntimeError: Attempted to exit cancel scope in a different task` raised at
    src/mcp_test_framework/fixtures.py:207 (`async with anyio.create_task_group() as tg:`)
    during pytest_asyncio session-finalizer's `gen_obj.__anext__()` call.
    Test bodies all complete; the error is purely teardown-side. EXIT_CODE=1.
- timestamp: 2026-05-06
  source: pytest_asyncio source — .venv/Lib/site-packages/pytest_asyncio/plugin.py:300-335
  observation: |
    Session-scoped async fixture lifecycle confirmed via Read:
    - plugin.py:308-313 setup: `async def setup(): res = await gen_obj.__anext__()`;
      then `runner.run(setup(), context=context)` schedules a NEW asyncio.Task.
    - plugin.py:317-330 finalizer: `async def async_finalizer(): await gen_obj.__anext__()`;
      then `runner.run(async_finalizer(), context=context)` schedules ANOTHER new
      asyncio.Task. The generator coroutine resumes on a DIFFERENT asyncio.Task
      than the one that ran setup. This is the structural cause of the cross-task
      cancel-scope violation: anyio.CancelScope reads `asyncio.current_task()`
      at __aenter__ and re-checks at __aexit__ — different tasks → RuntimeError.
- timestamp: 2026-05-06
  source: src/mcp_test_framework/fixtures.py:172-215 (Read)
  observation: |
    Confirmed structural shape: `async with anyio.create_task_group() as tg:`
    opens at fixtures.py:207, `yield client` at fixtures.py:212, `async with`
    block closes implicitly at fixtures.py:215. The cancel scope on `tg`
    SPANS the yield. By the pytest_asyncio mechanism above, __aenter__ runs
    on the setup task and __aexit__ runs on the finalizer task → bug.
- timestamp: 2026-05-06
  source: .planning/phases/04.1-mcp-client-teardown-fix/04.1-RESEARCH.md:481 (Assumption A2-residual)
  observation: |
    The original RESEARCH document explicitly flagged this exact failure mode
    as "residual MEDIUM until the planner runs the 5-minute spike CONTEXT A2
    calls for" — the spike was not run before the rewrite committed. The
    RESEARCH author's HIGH-confidence claim was that the OUTER tg's
    enter/exit pair "stays on one task" because the generator coroutine is
    "driven end-to-end via runner.run(async_finalizer())". The actual
    pytest_asyncio source shows TWO separate `runner.run(...)` invocations
    with TWO separate top-level tasks — the assumption was wrong.

## Eliminated

- timestamp: 2026-05-06
  candidate: |
    "Switch to RESEARCH Variant A (manual anyio.Event for ready instead of
    task_status.started())"
  reason: |
    Variant A has the same outer `async with anyio.create_task_group() as tg:`
    spanning the yield (RESEARCH lines 307-319). It would reproduce this exact
    bug. The defect is NOT in the ready-signaling idiom (Variant B vs A); it
    is in placing ANY anyio cancel scope across the fixture's yield.
- timestamp: 2026-05-06
  candidate: |
    "Adjust pyproject.toml [tool.pytest.ini_options] (e.g. set
    asyncio_default_test_loop_scope='session')"
  reason: |
    RESEARCH Pitfall D explicitly forbids this and Phase 4 already verified
    it does not fix the bug. CLAUDE.md / phase plan also lock pyproject.toml
    against modification.
- timestamp: 2026-05-06
  candidate: |
    "Modify the @pytest_asyncio.fixture decorator (loop_scope or scope)"
  reason: |
    RESEARCH Pitfalls C + E lock the decorator and signature verbatim:
    `@pytest_asyncio.fixture(loop_scope="session", scope="session")` and
    `(config: Config, _preflight)`.
- timestamp: 2026-05-05
  candidate: |
    "RESEARCH Variant A (Code Examples) — manual anyio.Event for ready instead
    of task_status.started()"
  reason: |
    Confirmed structurally identical defect to Variant B: Variant A's outer
    `async with anyio.create_task_group()` spans the fixture's yield in the
    same shape, so its cancel scope would __aenter__ on the setup task and
    __aexit__ on the finalizer task. Same Pitfall 1 cross-task pin violation.
    Conclusively eliminated alongside Variant B; the defect is structural
    ("any anyio cancel scope across the yield in a session-scoped
    pytest_asyncio fixture"), not specific to the ready-signaling idiom.

## Resolution

**root_cause:**
pytest-asyncio's session-scoped async generator fixture lifecycle drives
`gen_obj.__anext__()` from two distinct top-level `asyncio.Task`s — one for
setup (`plugin.py:313 runner.run(setup())`) and one for the session-end
finalizer (`plugin.py:330 runner.run(async_finalizer())`). Any anyio cancel
scope opened in the fixture body that spans the `yield` therefore has its
`__aenter__` pinned to the setup task and its `__aexit__` invoked on the
finalizer task; anyio's `CancelScope.__exit__` compares `current_task()` to
the captured `_host_task` and raises
`RuntimeError: Attempted to exit cancel scope in a different task than it
was entered in`. The Phase 4 occurrence pinned this on `stdio_client`'s
internal task group; the Tasks 1+2 rewrite (Variant B owner-task) merely
moved the violation outward to the fixture body's own
`anyio.create_task_group()`. Variant A would have failed identically. The
defect is structural: ANY task-pinned anyio context manager across the
yield in a session-scoped pytest-asyncio fixture is unsafe.

**fix:**
Replaced the fixture body's `async with anyio.create_task_group()` with a
pure-stdlib-asyncio driver. The owner task body (kept from Task 2; still
owns `stdio_client`, `ClientSession`, and `anyio.fail_after` — all anyio
scopes that enter and exit on the same task) now runs as
`asyncio.create_task(_owner_task(), name="mcp_client_owner")`. Handoff uses
`asyncio.Future` (`ready.set_result(client)` after `session.initialize()`,
or `ready.set_exception(exc)` on setup failure to preserve the original
error). Shutdown signal is `asyncio.Event`. The fixture body holds zero
anyio cancel scopes across the yield: it bounds the ready-await with
`asyncio.wait_for(asyncio.shield(ready), timeout=…+5)`, yields, then in
`finally` sets `shutdown`, awaits the owner with a 10-second timeout, and
falls back to `owner.cancel()` if the owner is still running. Imports
adjusted: added `import asyncio` and `import contextlib`; removed
`import anyio.abc` (TaskStatus no longer used); kept `import anyio` for
`anyio.fail_after` inside the owner task. Tasks 1+2 deliverables
preserved: `McpTestClient._wrap` classmethod (commit `08595de`)
untouched; pyproject.toml, decorator, signature, and public API all
unchanged. Diff scope: `src/mcp_test_framework/fixtures.py` only.

**verification:**
pending — awaiting user live pytest sweep.
- `uv run ruff check src/mcp_test_framework/fixtures.py` → All checks passed.
- `uv run python -c "from mcp_test_framework.fixtures import mcp_client; print('OK')"` → `OK`.
- `uv run pytest tests/unit/ -x -q --collect-only` → 56 tests collected, 0 errors.
- Live integration sweep (`uv run pytest tests/test_homelab_list_registered_servers.py -v`)
  must be run by the user against live homelab-mcp + Ollama; success criterion
  is `EXIT_CODE=0` (no teardown RuntimeError; pre-existing DEF-04-03-A judge
  score failure on `test_description_disambiguation` may still appear and is
  out of scope for this debug session).
