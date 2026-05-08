# Phase 06: Per-session host-state isolation - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 6 (3 source modifications, 1 new test, 1 new recon doc, 1 optional new module)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/fixtures.py` (MOD: new `_isolated_home` fixture + thread into `mcp_client`) | fixture / lifecycle owner | session-scoped resource lifecycle | `fixtures.py::judge` (existing `AsyncExitStack` fixture, line 267-283) | exact role-match |
| `src/mcp_test_framework/fixtures.py` (MOD: `StdioServerParameters` env-injection at line 207-210) | fixture spawn-site | request-response (subprocess spawn) | `fixtures.py::mcp_client::_owner_task` (line 207-237, the same function being modified) | self — preserve invariant |
| `src/mcp_test_framework/mcp_client.py` (MOD: `__aenter__` env-injection at line 143) | client lifecycle | request-response (subprocess spawn) | same file, `__aenter__` body lines 135-157 | self — preserve invariant |
| `src/mcp_test_framework/_isolation.py` (NEW, optional per CD-01) | utility / module-level constant + helper | pure-data (env dict construction) | `src/mcp_test_framework/schema_validator.py` (single-purpose pure-data module pattern) | role-match |
| `tests/test_isolation.py` (NEW — ISOL-03 verification) | integration test | file-I/O (sha256 hashing) + MCP call | `tests/test_homelab_list_registered_servers.py` (live integration, fixture-driven) | exact |
| `.planning/phases/06-per-session-host-state-isolation/06-keyring-recon.md` (NEW — ISOL-01 recon doc) | documentation / FINDINGS-style | n/a | `.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md` | exact (called out in D-02) |

---

## Pattern Assignments

### `src/mcp_test_framework/fixtures.py` — new `_isolated_home` session fixture

**Analog:** `src/mcp_test_framework/fixtures.py::judge` (lines 267-283) — existing session-scoped `AsyncExitStack`-owned async fixture. Closest shape match: same `loop_scope="session", scope="session"` decorator, same `async with AsyncExitStack() as stack: ... yield instance` body, same single-resource lifecycle.

**Decorator + signature pattern** (lines 267-268):
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def judge(config: Config, _preflight) -> Judge:
```

**`AsyncExitStack`-owned resource pattern** (lines 275-283):
```python
async with AsyncExitStack() as stack:
    instance = await stack.enter_async_context(
        OllamaJudge(
            config.ollama.base_url,
            config.ollama.model,
            config.ollama.timeout_seconds,
        )
    )
    yield instance
```

**Apply to `_isolated_home`:** wrap `tempfile.TemporaryDirectory(prefix="mcp-test-fw-")` in the stack. `TemporaryDirectory` is a sync context manager, so use `stack.enter_context(...)` (not `enter_async_context`). The yielded value is `Path(tmpdir.name)`. Lifecycle parity with `judge` — single source of truth (D-14), automatic cleanup (D-15), no anyio cancel scopes spanning the yield (Phase 04.1 invariant; safe here because `TemporaryDirectory` is stdlib sync).

**Convention from `_preflight` (lines 82-83):** session-scoped fixtures use both `loop_scope="session"` and `scope="session"` because the project locks `asyncio_default_fixture_loop_scope = "session"` in pyproject.toml (per docstring lines 5-7). Honor this exactly — don't introduce a function-scoped tempdir.

**Tempdir prefix convention** (per CONTEXT.md `<specifics>`): use prefix `"mcp-test-fw-"` so an orphaned tempdir is debuggable from `dir %TEMP%` output.

---

### `src/mcp_test_framework/fixtures.py` — `mcp_client` env-injection at the spawn site

**Analog:** the same function — `mcp_client` fixture body lines 175-259. The injection point is line 207-210; the surrounding owner-task body (lines 215-237) MUST be preserved verbatim except for the new `env=` kwarg.

**Existing spawn pattern to modify** (lines 207-210):
```python
params = StdioServerParameters(
    command=config.mcp_server.command,
    args=config.mcp_server.args,
)
```

**Target shape:**
```python
params = StdioServerParameters(
    command=config.mcp_server.command,
    args=config.mcp_server.args,
    env=_build_isolated_env(_isolated_home),  # ISOL-02 / ISOL-07
)
```

**MUST-PRESERVE invariant** (docstring lines 179-205, "no anyio cancel scope across the yield"): `_isolated_home` is consumed BEFORE `_owner_task` is created — its dependency injection happens at fixture-parameter resolution, NOT inside the owner task. The `params` object construction stays on the synchronous setup path (line 207, currently outside `_owner_task`). Do NOT move env construction into `_owner_task` — that would introduce a per-task coupling that breaks the Phase 04.1 fix.

**Fixture parameter signature change** (line 176):
```python
# Before:
async def mcp_client(config: Config, _preflight):
# After:
async def mcp_client(config: Config, _preflight, _isolated_home):
```

`_preflight` runs first (autouse), then `_isolated_home`, then `mcp_client` consumes both. Matches the dependency style of `target_tool` at line 292 (`mcp_client: McpTestClient, _preflight`).

---

### `src/mcp_test_framework/mcp_client.py` — `__aenter__` env-injection (D-16, CLI path)

**Analog:** the same file — `McpTestClient.__aenter__` body lines 135-157. This is the standalone path used by `mcp-test-framework list-tools` and by the `_preflight` brief handshake (fixtures.py line 140-144).

**Existing spawn pattern** (line 143):
```python
params = StdioServerParameters(command=self._command, args=self._args)
```

**Target shape (per D-16):** create a per-instance short-lived tempdir on entry, tear it down on exit. The `AsyncExitStack` already owns the lifecycle (line 144) — register the `TemporaryDirectory` with the stack:

```python
params_stack = AsyncExitStack()  # rename existing 'stack' if needed for clarity
try:
    isolated_home = Path(
        stack.enter_context(tempfile.TemporaryDirectory(prefix="mcp-test-fw-cli-"))
    )
    params = StdioServerParameters(
        command=self._command,
        args=self._args,
        env=_build_isolated_env(isolated_home),
    )
    read, write = await stack.enter_async_context(stdio_client(params))
    ...
```

**Existing `AsyncExitStack` reverse-order pattern to copy** (lines 144-157):
```python
stack = AsyncExitStack()
try:
    read, write = await stack.enter_async_context(
        stdio_client(params)
    )
    session = await stack.enter_async_context(ClientSession(read, write))
    async with asyncio.timeout(self._timeout_seconds):
        await session.initialize()
except BaseException:
    await stack.aclose()
    raise
self._stack = stack
self._session = session
```

The new tempdir registers BEFORE `stdio_client` so reverse-order unwind tears down the subprocess first, then deletes the tempdir — correct ordering on Windows (closed file handles before rmdir attempt) and POSIX. Matches the documented Pitfall-1 mitigation in the existing docstring (line 160-164).

**Prefix differentiation:** CLI path uses `"mcp-test-fw-cli-"`, session fixture uses `"mcp-test-fw-"` — orphan diagnosis distinguishes the source.

---

### `src/mcp_test_framework/_isolation.py` (NEW, CD-01 — Claude's discretion)

**Analog:** `src/mcp_test_framework/schema_validator.py` (existing single-purpose pure-data module). Pattern: small focused module, module-level constants + 1-2 functions, no class, no I/O. Same shape recommended for `_isolation.py`.

**Recommendation:** put the env allowlist and `_build_isolated_env(path)` helper in `_isolation.py` rather than at the top of `mcp_client.py`. Reasoning:
- Imported by both `fixtures.py` and `mcp_client.py` — a module avoids circular-import risk
- Single source of truth (D-14 spirit — one tempdir owner, one env builder)
- Underscore-prefixed module name signals "internal API; not part of the public Config surface" (consistent with D-06)

**Module-level constant pattern** (allowlist cited from CONTEXT D-07 + FINDINGS §3):
```python
"""Per-session host-state isolation env construction (Phase 06).

Allowlist + override semantics per:
- .planning/quick/260506-qxs.../FINDINGS.md §3 (HOME/USERPROFILE redirect)
- .planning/REQUIREMENTS.md ISOL-07 (passthrough allowlist)
- .planning/phases/06-.../06-CONTEXT.md D-07 (no Config field, module-level constant)

DO NOT widen this allowlist without updating ISOL-07 documentation
(EXTENDING.md per DOC-07).
"""
from __future__ import annotations

import os
from pathlib import Path

# ISOL-07: passthrough allowlist — exact list per CONTEXT D-07.
_PASSTHROUGH_ALLOWLIST: tuple[str, ...] = (
    "PATH",
    "SYSTEMROOT",   # Windows DLL resolution
    "LANG",
    "USERNAME",
)

# All MCP_* vars pass through (CD-03: includes MCP_CONNECTION_NONBLOCKING).
_MCP_PREFIX = "MCP_"

# Variables we OVERRIDE to redirect ~/.homelab_mcp/ writes (FINDINGS §3).
_HOME_OVERRIDES: tuple[str, ...] = (
    "HOME",         # POSIX
    "USERPROFILE",  # Windows
    "TEMP",
    "TMP",
    "TMPDIR",
)


def _build_isolated_env(isolated_home: Path) -> dict[str, str]:
    """Return env dict for StdioServerParameters spawning into an isolated home.

    Replaces full os.environ inheritance with allowlist + overrides:
    1. Pass-through PATH, SYSTEMROOT, LANG, USERNAME (ISOL-07).
    2. Pass-through any MCP_* var (CD-03 — includes MCP_CONNECTION_NONBLOCKING).
    3. Override HOME/USERPROFILE/TEMP/TMP/TMPDIR -> isolated_home so
       os.path.expanduser('~') inside the spawned subprocess resolves to
       the tempdir on Windows and POSIX alike (ISOL-02 / ISOL-06).

    The returned dict is the COMPLETE env passed to StdioServerParameters —
    NOT a delta on top of os.environ. Anything not in this dict is invisible
    to the subprocess (intentional; that is the isolation guarantee).
    """
    env: dict[str, str] = {}
    for name in _PASSTHROUGH_ALLOWLIST:
        if (value := os.environ.get(name)) is not None:
            env[name] = value
    for name, value in os.environ.items():
        if name.startswith(_MCP_PREFIX):
            env[name] = value
    home_str = str(isolated_home)
    for name in _HOME_OVERRIDES:
        env[name] = home_str
    return env
```

**Convention compliance:**
- `from __future__ import annotations` — matches every other source module (fixtures.py:22, mcp_client.py:31, schema_validator.py likely)
- Module docstring with cross-references to FINDINGS / REQUIREMENTS / CONTEXT — matches mcp_client.py:1-30 docstring style
- Underscore-prefixed names for internal-only — matches `_owner_task`, `_preflight`, `_LoggerWriter`, `_log` conventions
- No public class — pure-data style matches `schema_validator.py`'s `validate_tool_schema` function

---

### `tests/test_isolation.py` (NEW — ISOL-03 verification)

**Analog:** `tests/test_homelab_list_registered_servers.py` (full file, especially lines 1-43 for module setup and lines 165-182 for fixture-driven `mcp_client.call_tool` shape). Same role (live integration test driving the real subprocess), same fixture story (`mcp_client`, `target_tool`, `config`).

**Module preamble pattern** (lines 1-43 of analog):
```python
"""[Test module docstring explaining what's being verified, links to REQ-IDs]"""
from __future__ import annotations

import pytest

# UNMARKED per D-markers-1; preflight is the gate (D-preflight-1..4).
# loop_scope="session" required so fixtures + tests share the session loop.
pytestmark = [pytest.mark.asyncio(loop_scope="session")]
```

**Apply to `test_isolation.py`:** UNMARKED (consistent with existing integration tests; the live-integration smoke tests use `pytest.mark.live_homelab` ONLY because they're explicitly opt-in — the standard `tests/test_*.py` pattern is unmarked + preflight-gated). `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` is required.

**Fixture-driven test body pattern** (analog lines 165-171):
```python
async def test_empty_args_call_returns_non_error(
    mcp_client: McpTestClient,
    config: Config,
) -> None:
    """TEST-08: call_tool with {} returns isError=False."""
    result = await mcp_client.call_tool(config.target.tool_name, {})
    assert not result.isError, f"call_tool returned isError=True: {result!r}"
```

**Apply to ISOL-03:** test depends on `_isolated_home`, `mcp_client`, `config`. Per D-08 the test:
1. Computes sha256 of the 3 real files BEFORE invoking any tool (or skips per D-11 if `~/.homelab_mcp/` is missing).
2. Calls `await mcp_client.call_tool(config.target.tool_name, {})` for each tool exercised at v1.1 surface (`list_keyring_credentials`, `list_registered_servers`).
3. Re-hashes; asserts equality with original.
4. Asserts `(_isolated_home / ".homelab_mcp").exists()` — proves redirection happened (D-08 step 4, guards "tools just no-op'd" silent pass).

**Skip pattern** (per D-11) — analog for skip semantics: pytest stdlib `pytest.skip(...)`. No live precedent in this test file but the existing `_preflight` uses `pytest.exit(...)` for hard fails; `pytest.skip(...)` is correct here per D-11 wording.

```python
import hashlib
from pathlib import Path

REAL_FILES = (
    Path.home() / ".homelab_mcp" / "credential_registry.json",
    Path.home() / ".homelab_mcp" / "known_hosts",
    Path.home() / ".homelab_mcp" / "migration_state.json",
)

def _sha256_of(p: Path) -> str | None:
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


async def test_real_state_unchanged(
    _isolated_home: Path,
    mcp_client,
    config: Config,
) -> None:
    """ISOL-03: real ~/.homelab_mcp/ files unchanged after a session run."""
    real_root = Path.home() / ".homelab_mcp"
    if not real_root.exists():
        pytest.skip(
            "No real ~/.homelab_mcp/ to compare against — "
            "ISOL-03 vacuous on this host"
        )
    before = {p: _sha256_of(p) for p in REAL_FILES}

    # Drive the v1.1 tool surface (D-10 in-process, no recursive pytest).
    for tool_name in ("list_keyring_credentials", config.target.tool_name):
        await mcp_client.call_tool(tool_name, {})

    after = {p: _sha256_of(p) for p in REAL_FILES}
    assert before == after, (
        f"Real ~/.homelab_mcp/ mutated. "
        f"before={before!r} after={after!r}"
    )
    # Positive: tempdir actually got the writes (guards no-op silent pass).
    assert (_isolated_home / ".homelab_mcp").exists(), (
        f"Tempdir {_isolated_home}/.homelab_mcp/ was not created — "
        f"redirection did not take effect; tools may have no-op'd silently."
    )
```

**Black-box compliance** (CLAUDE.md hard rule, conftest.py:32-42 sys.modules guard): the test reads its OWN `~/.homelab_mcp/` files via stdlib `pathlib`/`hashlib` only. NO import from `homelab_mcp`. The conftest sys.modules guard will fail the run if any import slips in.

---

### `.planning/phases/06-per-session-host-state-isolation/06-keyring-recon.md` (NEW — ISOL-01)

**Analog:** `.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md` — explicitly called out in CONTEXT D-02 as the template.

**Section structure to mirror** (FINDINGS.md headings):
1. `## 1. State homelab-mcp creates/mutates` → adapt to: `## 1. PyPI README evidence — documented keyring touchpoints` (per D-01 method: read PyPI README, no source-read)
2. `## 2. Isolation knobs available` → adapt to: `## 2. cmdkey before/after diff` (the empirical evidence per D-01)
3. `## 3. Recommended isolation strategy` → adapt to: `## 3. Decision: ship ISOL-04 in v1.1, or defer with trigger` (per D-02 + D-04)
4. `## 4. Effort estimate` → omit (recon, not implementation)
5. `## 5. Open questions` → keep — list any residual unknowns

**Front-matter pattern** (FINDINGS.md lines 1-6):
```markdown
# [Title] — RECON

**Date:** YYYY-MM-DD
**Scope:** [one-sentence scope statement]
**Method:** [list of evidence sources, citing the explicit "no source read" constraint per D-01]
```

**Evidence-table pattern** (FINDINGS.md §1 first table) — apply to §2 cmdkey diff: columns `Target | Before | After | Delta`, rows = each `homelab-mcp`-scoped credential entry from `raw/keyring.txt`.

**Decision-with-trigger pattern** (FINDINGS.md §3 last paragraph "Trigger condition that would escalate") — apply to §3 of recon doc per D-04: explicit ship-or-defer call AND the trigger condition that would re-open the deferred path.

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** every existing source module (`fixtures.py:22`, `mcp_client.py:31`, `tests/test_homelab_list_registered_servers.py:29`).
**Apply to:** all new `.py` files in this phase (`_isolation.py`, `tests/test_isolation.py`).

### Module-level docstring linking to REQ-IDs and CONTEXT decisions
**Source:** `mcp_client.py:1-30`, `fixtures.py:1-21`.
**Apply to:** `_isolation.py` (cite ISOL-07, FINDINGS §3, CONTEXT D-07), `tests/test_isolation.py` (cite ISOL-03, CONTEXT D-08..D-11).

### `AsyncExitStack` ownership for any async resource
**Source:** `mcp_client.py:144-157` (stdio + session), `fixtures.py:275-283` (judge).
**Apply to:** `_isolated_home` fixture (wrap `tempfile.TemporaryDirectory` in `AsyncExitStack`). For sync resources like `TemporaryDirectory`, use `stack.enter_context(...)` rather than `enter_async_context(...)`.

### `asyncio.timeout` / `anyio.fail_after` around any I/O that could hang
**Source:** `mcp_client.py:150,173,189` (`asyncio.timeout(self._timeout_seconds)`); `fixtures.py:223` (`with anyio.fail_after(...)`).
**Apply to:** any new I/O in this phase. `tempfile.TemporaryDirectory()` creation does not block on real filesystems and does not need a timeout. The ISOL-03 sha256 reads are sub-millisecond and do not need one. If a future addition introduces blocking I/O (e.g., reading from a network mount), wrap it.

### Black-box rule (mechanically enforced)
**Source:** `tests/conftest.py:17-42` (sys.modules guard) + `pyproject.toml` ruff `TID251` config.
**Apply to:** never `import homelab_mcp` or `from homelab_mcp...` from any new file. ISOL-01 recon doc reads the PyPI README only (D-01); ISOL-03 test uses stdlib `pathlib`/`hashlib` only.

### Session-scoped pytest-asyncio fixture decorator
**Source:** `fixtures.py:82,175,267,291` — every async fixture in the file uses `@pytest_asyncio.fixture(loop_scope="session", scope="session")` (or `autouse=True` variant).
**Apply to:** `_isolated_home` (D-12 explicitly specifies this exact decorator combination).

### `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` at module top of integration tests
**Source:** `tests/test_homelab_list_registered_servers.py:43`, `tests/smoke/test_smoke_homelab_mcp.py:33-36`.
**Apply to:** `tests/test_isolation.py` — required so the test loop matches the fixture loop scope. Without it, the session fixture's loop and the test's loop diverge and produce a `RuntimeError: Task ... attached to a different loop` failure.

### Tempdir prefix for orphan diagnosis
**Source:** CONTEXT.md `<specifics>` section explicitly recommends prefix `"mcp-test-fw-"`.
**Apply to:** `_isolated_home` fixture uses `prefix="mcp-test-fw-"`. CLI path (`McpTestClient.__aenter__`) uses `prefix="mcp-test-fw-cli-"` to differentiate orphan source.

### CD-02 — Windows tempdir cleanup-failure handling (Claude's discretion)
**Source:** no existing analog. Python `tempfile.TemporaryDirectory` on Windows raises `PermissionError` warnings if a child handle is still open at cleanup; `ignore_cleanup_errors=True` (Python 3.12+) suppresses but masks orphan bugs.
**Recommendation for planner:** trust the existing `mcp_client` owner-task teardown (fixtures.py:253-259) — by the time `_isolated_home` cleanup runs in reverse-order, the subprocess has already been awaited or cancelled. If flaky on Windows CI, add `ignore_cleanup_errors=True` AND a follow-up assertion that the tempdir directory is gone after fixture exit. The phase success criterion ("No orphaned tempdirs exist on disk after a clean run") is the bar.

---

## No Analog Found

None. Every new file in this phase has a strong analog in the existing codebase or the documented FINDINGS template.

---

## Metadata

**Analog search scope:**
- `src/mcp_test_framework/*.py` (full module surface)
- `tests/**/*.py` (existing integration + smoke + unit tests)
- `tests/conftest.py` (project conftest)
- `.planning/quick/260506-qxs.../FINDINGS.md` (recon template explicitly cited in D-02)

**Files scanned:** 8 source/test files + 1 recon doc + 4 spec/context docs read end-to-end (CONTEXT.md, REQUIREMENTS.md, ROADMAP.md, FINDINGS.md).

**Pattern extraction date:** 2026-05-07
