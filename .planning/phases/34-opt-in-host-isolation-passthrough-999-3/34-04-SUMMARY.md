---
phase: 34-opt-in-host-isolation-passthrough-999-3
plan: 04
subsystem: spawn-site-wiring
tags: [spawn-site, fixture-plumbing, seed-022, mcp-client, library-mode]
requires:
  - _build_subprocess_env dispatcher (plan 34-03)
  - Config.host_isolation field (plan 34-01)
provides:
  - "_isolated_home(mcp_config) -> Path | None (passthrough short-circuit)"
  - "McpTestClient.__init__(..., *, host_isolation='strict')"
  - "_plugin._discover_tools_live threads host_isolation=cfg.host_isolation"
affects:
  - src/mcp_test_framework/fixtures.py
  - src/mcp_test_framework/mcp_client.py
  - src/mcp_test_framework/_plugin.py
  - tests/framework/unit/test_isolated_home_passthrough.py (new)
  - tests/framework/unit/test_mcp_client_host_isolation.py (new)
  - tests/framework/unit/test_plugin_host_isolation_wiring.py (new)
tech-stack:
  added: []
  patterns:
    - "Caller-passes-data primitive (framework-primitive contract): McpTestClient takes Literal[str] mode, never a Config"
    - "Keyword-only param via `*,` marker to preserve positional-arg semantics for existing callers"
    - "Passthrough short-circuit: yield None before AsyncExitStack entry -- no tempdir allocated, no cleanup machinery engaged"
    - "TDD RED/GREEN gate sequence -- one RED + one GREEN per task"
key-files:
  created:
    - tests/framework/unit/test_isolated_home_passthrough.py
    - tests/framework/unit/test_mcp_client_host_isolation.py
    - tests/framework/unit/test_plugin_host_isolation_wiring.py
  modified:
    - src/mcp_test_framework/fixtures.py
    - src/mcp_test_framework/mcp_client.py
    - src/mcp_test_framework/_plugin.py
decisions:
  - "D-06 implemented: _isolated_home short-circuits under passthrough -- yields None without entering tempfile.TemporaryDirectory"
  - "D-07 implemented: both spawn sites (fixtures.py:446, mcp_client.py) route through _build_subprocess_env(mode, isolated_home)"
  - "D-08 implemented: McpTestClient takes host_isolation as a Literal[str] kw-only param; no Config import in mcp_client.py"
  - "RESEARCH Open Question 5 path (a) selected: caller-passes-data over Config-in-constructor"
metrics:
  duration: ~25 minutes
  tasks_completed: 3
  files_created: 3
  files_modified: 3
  tests_added: 11
  framework_tests_passing: 778
completed: 2026-05-27
---

# Phase 34 Plan 04: Wire dispatcher into spawn sites + extend McpTestClient

**One-liner:** Plumbed the plan-34-03 `_build_subprocess_env` dispatcher into both spawn sites (`fixtures.py:446` and `mcp_client.py.__aenter__`), short-circuited `_isolated_home` under passthrough so no tempdir is allocated, extended `McpTestClient.__init__` with a keyword-only `host_isolation` parameter (default `'strict'`), and threaded `cfg.host_isolation` through `_plugin._discover_tools_live` so library-mode tool discovery honors the operator's mode choice.

## Outcome

Wave 2 ships the spawn-site wiring that completes the opt-in passthrough seam:

- Default `host_isolation='strict'` preserves v1.0-v1.4 behavior byte-for-byte across every persona (CLI, library-mode, framework self-tests).
- Operator who flips `host_isolation: passthrough` in their `config.yaml` now sees: (a) the spawned MCP subprocess inherits their full `os.environ` (HOME, USERPROFILE, keyring backend, secrets) and (b) the per-session `_isolated_home` tempdir is never allocated in passthrough mode.
- Framework-primitive contract preserved: `mcp_client.py` does NOT import `config.py`; the caller (fixture body, CLI command, `_plugin._discover_tools_live`) passes plain `Literal[str]` data.

The live UAT verification (Phase 30 UAT-1 Proxmox credential repro) is integration-level and deferred to a smoke test in plan 34-08; this plan plumbs the wiring and pins it via static-source + signature contract checks.

## Final `_isolated_home` Fixture (verbatim)

```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def _isolated_home(mcp_config: Config):
    """Per-session tempdir owning the HOME/USERPROFILE redirect target.

    Single source of truth for the isolation tempdir. Verification tests
    that read the redirected ``.homelab_mcp/`` subdirectory depend on this
    fixture directly rather than reaching into ``mcp_client`` internals.
    Future fixtures that need isolation guarantees depend on the same
    fixture -- no duplicate tempdir creation.

    Mode branching:
      - ``host_isolation='strict'`` (default): allocate a TemporaryDirectory
        and yield its Path. v1.0-v1.4 behavior preserved verbatim.
      - ``host_isolation='passthrough'``: short-circuit; yield ``None``
        without engaging the tempdir machinery. Passthrough disables the
        HOME redirect this tempdir was supporting, so allocating it would
        be dead state.

    Lifecycle (strict branch) owned via ``AsyncExitStack`` -- cleanup is
    automatic on session exit. ``tempfile.TemporaryDirectory`` is a SYNC
    context manager, so we use ``stack.enter_context`` (not
    ``enter_async_context``). This is safe with respect to the
    "no anyio cancel scope across the yield" invariant because
    ``TemporaryDirectory`` is stdlib sync -- it opens no anyio cancel scope.

    Tempdir prefix ``mcp-test-fw-`` so orphaned tempdirs (should cleanup
    ever fail) are debuggable from ``dir %TEMP%`` output.
    """
    if mcp_config.host_isolation == 'passthrough':
        yield None
        return
    async with AsyncExitStack() as stack:
        tmpdir = stack.enter_context(
            tempfile.TemporaryDirectory(prefix="mcp-test-fw-")
        )
        yield Path(tmpdir)
```

## Final `McpTestClient.__init__` Signature (verbatim)

```python
def __init__(
    self,
    command: str,
    args: list[str],
    timeout_seconds: int,
    *,
    host_isolation: Literal['strict', 'passthrough'] = 'strict',
) -> None:
    self._command = command
    self._args = list(args)  # defensive copy
    self._timeout_seconds = timeout_seconds
    # Stored as plain data (not a Config object) so this primitive stays
    # caller-passes-data and never imports the config module.
    self._host_isolation = host_isolation
    self._stack: AsyncExitStack | None = None
    self._session: ClientSession | None = None
```

The `*,` keyword-only marker is load-bearing: it prevents `host_isolation` from accidentally landing as a positional 4th arg (which would change existing callers' positional semantics).

## `_plugin.py` Call-Site Update

One `McpTestClient(...)` call site in `_plugin.py`:

| Line | Function              | Change                                              |
| ---- | --------------------- | --------------------------------------------------- |
| 148  | `_discover_tools_live` | Appended `host_isolation=cfg.host_isolation` kwarg  |

## Acceptance Criteria

All plan-level `<verification>` and `<success_criteria>` checks pass:

| Check                                                                 | Result |
| --------------------------------------------------------------------- | ------ |
| `_build_isolated_env` legacy call sites in `fixtures.py`              | 0 (was 1; replaced by dispatcher) |
| `_build_isolated_env` legacy call sites in `mcp_client.py`            | 0 (was 1; replaced by dispatcher) |
| `from mcp_test_framework.config` import in `mcp_client.py`            | 0 (framework-primitive invariant) |
| `host_isolation=cfg.host_isolation` occurrences in `_plugin.py`       | 1 (matches 1 `McpTestClient(` call site) |
| `_build_subprocess_env(mcp_config.host_isolation` in `fixtures.py`    | 1 at line 446 |
| `_isolated_home(mcp_config: Config)` signature in `fixtures.py`       | present (line 364) |
| `yield None` short-circuit branch in `fixtures.py`                    | present |
| Bare-Config fallback audit comment at `fixtures.py:111`               | present |
| `uv run pytest tests/framework/ -x`                                   | 778 passed, 2 skipped, 18 deselected, 1 xfailed |
| `tests/framework/unit/test_no_planning_ids_in_src.py` planning-ID gate | passes |
| `uv run mcp-contracts --help` smoke                                   | clean output, no errors |

## Tasks Completed

| Task | Name                                                                                 | RED Commit | GREEN Commit | Files                                       |
| ---- | ------------------------------------------------------------------------------------ | ---------- | ------------ | ------------------------------------------- |
| 1    | Wire `_isolated_home` short-circuit + `mcp_client` dispatcher + audit comment        | 9ee2655    | 5c13c27      | `src/mcp_test_framework/fixtures.py`        |
| 2    | Extend `McpTestClient.__init__` with `host_isolation` + route `__aenter__`           | b5019a7    | 40f3672      | `src/mcp_test_framework/mcp_client.py`      |
| 3    | Thread `cfg.host_isolation` from `_plugin._discover_tools_live`                      | a1f737c    | 7cdd89c      | `src/mcp_test_framework/_plugin.py`         |

## Commits (chronological)

| Hash       | Type | Message                                                                                |
| ---------- | ---- | -------------------------------------------------------------------------------------- |
| `9ee2655`  | test | add failing pins for `_isolated_home` short-circuit + dispatcher routing (RED)         |
| `5c13c27`  | feat | wire fixtures dispatcher routing + passthrough short-circuit (GREEN)                   |
| `b5019a7`  | test | add failing pins for `McpTestClient host_isolation` kw-only param (RED)                |
| `40f3672`  | feat | extend `McpTestClient.__init__` with `host_isolation` kw-only param (GREEN)            |
| `a1f737c`  | test | add failing pin for `_plugin.py` `host_isolation` wiring (RED)                         |
| `7cdd89c`  | feat | thread `cfg.host_isolation` through library-mode tool discovery (GREEN)                |

## TDD Gate Compliance

Per-task discipline observed for all three tasks: a `test(34-04): ...` commit lands before each `feat(34-04): ...` commit, with the RED commit's failure verified before implementation. Gate sequence valid for every task:

- Task 1: `test(...)` 9ee2655 → `feat(...)` 5c13c27 (RED → GREEN)
- Task 2: `test(...)` b5019a7 → `feat(...)` 40f3672 (RED → GREEN)
- Task 3: `test(...)` a1f737c → `feat(...)` 7cdd89c (RED → GREEN)

REFACTOR gate skipped for all three tasks -- code landed in its final shape.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed `ISOL-05` and `D-06` planning-ID tokens from source comments**

- **Found during:** Task 1 (writing the audit comment + the `_isolated_home` docstring)
- **Issue:** The plan asked for an `ISOL-05 audit:` comment at `fixtures.py:111` and a `D-06` reference in the `_isolated_home` docstring. The repo's planning-ID leak gate at `tests/framework/unit/test_no_planning_ids_in_src.py` uses locked regex `(CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB|RELOC)-\d+|\bD-\d+\b` -- both `ISOL-05` and `D-06` would have tripped the gate.
- **Fix:** Reworded the audit comment to start with `# Audit:` (planning-ID-free); reworded `_isolated_home`'s mode-branch docstring to describe the behavior ("`host_isolation='passthrough'`: short-circuit") rather than citing `D-06`. The planning IDs remain in PLAN.md / this SUMMARY.md / commit messages.
- **Files modified:** `src/mcp_test_framework/fixtures.py` (lines 111-112 and the `_isolated_home` docstring).
- **Commit:** Folded into `5c13c27` (Task 1 GREEN) rather than a separate fix commit; caught and fixed before the GREEN commit landed.
- **Why Rule 1 not Rule 4:** Identical pattern to plan 34-03's deviation -- a pre-existing regression gate that the planned wording would have broken. The gate's locked-regex policy (D-04 hard zero, no allowlist) is unambiguous, no architectural decision needed.

## Authentication Gates

None.

## Threat Flags

None. The four threat-register entries (T-34-04-01..04) are all mitigated as planned:

- T-34-04-01 (passthrough leaks operator credentials): explicit operator opt-in, documented in plan 34-08; not a defect.
- T-34-04-02 (library-mode call site forgets to thread mode): pinned by `test_plugin_passes_host_isolation_to_mcp_client` which counts `McpTestClient(` vs `host_isolation=cfg.host_isolation` occurrences.
- T-34-04-03 (Config blob in McpTestClient): pinned by `test_mcp_client_module_does_not_import_config`.
- T-34-04-04 (orphan tempdir under passthrough): pinned by `test_isolated_home_passthrough_yields_none` which proves the `AsyncExitStack` branch is bypassed.

## Known Stubs

None. The wiring is complete end-to-end; downstream plans (34-05 xdist clamp, 34-06 docs, 34-07 config-init scaffold, 34-08 docs + live UAT) consume this surface without re-touching it.

## Verification Results

- `uv run pytest tests/framework/ -x` -> 778 passed, 2 skipped, 18 deselected, 1 xfailed. No regressions; 11 new tests added (5 in `test_isolated_home_passthrough.py`, 5 in `test_mcp_client_host_isolation.py`, 1 in `test_plugin_host_isolation_wiring.py`).
- `uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py -x` -> 1 passed. Planning-ID gate green.
- `uv run mcp-contracts --help` -> clean output (default-strict CLI smoke unaffected).

## Self-Check: PASSED

- Created files exist:
  - `tests/framework/unit/test_isolated_home_passthrough.py` -- FOUND
  - `tests/framework/unit/test_mcp_client_host_isolation.py` -- FOUND
  - `tests/framework/unit/test_plugin_host_isolation_wiring.py` -- FOUND
- Modified files exist:
  - `src/mcp_test_framework/fixtures.py` -- FOUND
  - `src/mcp_test_framework/mcp_client.py` -- FOUND
  - `src/mcp_test_framework/_plugin.py` -- FOUND
- Commits exist (`git log --oneline`):
  - `9ee2655` -- FOUND
  - `5c13c27` -- FOUND
  - `b5019a7` -- FOUND
  - `40f3672` -- FOUND
  - `a1f737c` -- FOUND
  - `7cdd89c` -- FOUND
