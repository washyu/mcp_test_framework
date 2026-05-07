# Phase 06: Per-session host-state isolation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 06-per-session-host-state-isolation
**Areas discussed:** ISOL-01 method, Config opt-out surface, ISOL-03 verification rigor, Tempdir fixture seam

---

## ISOL-01 method

### How should ISOL-01 (keyring-touch investigation) run?

| Option | Description | Selected |
|--------|-------------|----------|
| Empirical cmdkey diff (Recommended) | Snapshot `cmdkey /list \| findstr homelab` before and after a real isolated test run, diff. Direct evidence, zero source-reading, finishes in one task. | |
| Defensive null-backend ship | Skip the investigation, just ship `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` always. If any tool call fails, that IS the answer. Couples ISOL-04 to ISOL-02/03. | |
| PyPI README pass + cmdkey diff | Read public homelab-mcp PyPI README for documented keyring touchpoints (no source), THEN run the cmdkey diff for empirical confirmation. More thorough. | ✓ |

**User's choice:** PyPI README pass + cmdkey diff
**Notes:** Both pieces of evidence land in the recon doc. README provides documentation grounding; cmdkey diff provides empirical confirmation.

### What's the ISOL-01 deliverable, and where does it live?

| Option | Description | Selected |
|--------|-------------|----------|
| One-off recon doc + decision (Recommended) | ISOL-01 produces `06-keyring-recon.md` capturing PyPI README quotes, cmdkey diff, ship-or-defer decision. Runs once, before ISOL-02. Mirrors 260506-qxs spike. | ✓ |
| Permanent CI test | ISOL-01 ships as a pytest test that runs `cmdkey /list` (Windows-only) and asserts no diff. Continuous regression guard. Windows-only, brittle. | |
| Both — recon doc THEN regression test | Produce recon doc to make ship/defer call, then add permanent (skip-on-non-Windows) regression test as part of ISOL-03. More work but locks the answer permanently. | |

**User's choice:** One-off recon doc + decision
**Notes:** Investigation is one-time. Regression guard against keyring mutation is owned by ISOL-03's hash-equality on real-state files; if homelab-mcp mutates the keyring without touching the registry, ISOL-01's recon is the protection.

### More questions about ISOL-01, or move to next?

**User's choice:** Next area

---

## Config opt-out surface

### Should isolation be always-on, or expose a Config opt-out?

| Option | Description | Selected |
|--------|-------------|----------|
| Always-on, no toggle (Recommended) | Isolation runs unconditionally. No `isolate: false` escape hatch. Simpler API surface; aligns with "this is a usability bug" framing in the source todo. | ✓ |
| Opt-out via IsolationConfig | Ship `IsolationConfig { isolate: bool=True, extra_env: dict={} }` per FINDINGS §4. Default-on, settable to false via config. Adds API surface to maintain. | |
| Always-on + extra_env knob only | Isolation unconditional, but expose `mcp_server.extra_env: dict[str,str]={}` for power-user env injection. No on/off, but injection seam. | |

**User's choice:** Always-on, no toggle
**Notes:** No new public Config sub-model. Allowlist lives as a module-level constant at the spawn site.

### More questions about Config opt-out, or move to next?

**User's choice:** Next area

---

## ISOL-03 verification rigor

### How rigorously does the ISOL-03 test prove no real-state mutation?

| Option | Description | Selected |
|--------|-------------|----------|
| sha256 + tempdir positive (Recommended) | sha256 hash equality on the 3 real files before+after, plus positive assertion that the tempdir's `.homelab_mcp/` was created. Catches same-mtime overwrites; cross-platform clean. | ✓ |
| mtime diff only | Snapshot mtimes before+after, assert unchanged. Cheap; same-second overwrite slips past. | |
| sha256 + handle inspection | Hash check + Sysinternals handle.exe (Windows) / `/proc/<pid>/fd/` (POSIX) to assert subprocess never opened the real registry. Strongest signal; external tool dep on Windows. | |

**User's choice:** sha256 + tempdir positive
**Notes:** Strongest signal that doesn't need a Sysinternals dependency. The tempdir-creation positive guards against silent "tools just no-op'd" passes.

### What does the ISOL-03 test actually exercise as 'the run'?

| Option | Description | Selected |
|--------|-------------|----------|
| In-process: spawn one mcp_client + call all judged tools (Recommended) | Test acquires `mcp_client` fixture and invokes `call_tool` for each tool exercised by the suite. No subprocess-pytest indirection. | ✓ |
| Subprocess pytest invocation | Test shells out to `uv run pytest tests/` (excluding itself). Most realistic; self-recursion + cross-platform shell complexity. | |
| Smoke probe: just initialize() + list_tools() | Minimal verification of startup + discovery. Doesn't catch a tool whose CALL writes. | |

**User's choice:** In-process
**Notes:** The `mcp_client` fixture invocation IS the run-under-test; calling each judged tool covers the actual operations.

### How should the test behave when ~/.homelab_mcp/ doesn't exist on the test host?

| Option | Description | Selected |
|--------|-------------|----------|
| Skip with reason (Recommended) | `pytest.skip('No real ~/.homelab_mcp/ to compare against — vacuous on this host')`. Test runs on the developer machine that has the live install. | ✓ |
| Fail loudly | Treat absence as failure; forces explicit setup. Blocks fresh-CI runs. | |
| Synthesize a fake baseline | Write sentinel file before the run, hash it, assert post-run match. Works on any host; weaker proof. | |

**User's choice:** Skip with reason
**Notes:** The test's value lives where bleed-through bites — a developer machine with a real install. Skipping cleanly on a fresh CI box is acceptable.

### More questions about ISOL-03, or move to last area?

**User's choice:** Next area

---

## Tempdir fixture seam

### Where does the per-session tempdir fixture live, and how does mcp_client consume it?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate `_isolated_home` fixture (Recommended) | New `@pytest_asyncio.fixture(loop_scope='session', scope='session')` yielding a `TemporaryDirectory` path. `mcp_client` and ISOL-03 both depend on it. Clean separation; reusable by future Phase 07/08. | ✓ |
| Inlined into mcp_client | Tempdir created inside `mcp_client` body. ISOL-03 needs a side-channel to read tempdir path; couples test to fixture internals. | |
| Inlined + expose attribute on McpTestClient | Inline as above, stash tempdir path on returned `McpTestClient` instance. Avoids new fixture; adds test-only field to McpTestClient. | |

**User's choice:** Separate `_isolated_home` fixture
**Notes:** Single source of truth for the tempdir. Future Phase 07/08 fixtures depend on the same fixture — no duplicate creation.

### Should the standalone McpTestClient.__aenter__() path (used by CLI list-tools) also be isolated?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — both paths isolated (Recommended) | `McpTestClient.__aenter__()` gets the same env override (own short-lived tempdir; auto-cleaned on `__aexit__`). CLI `list-tools` runs against an isolated subprocess. Stronger DOC-05 story. | ✓ |
| Only the test fixture path | Isolation only in the pytest fixture. CLI continues against real env. "Tests are isolated, the CLI inspector is not" is awkward to document. | |

**User's choice:** Yes — both paths isolated
**Notes:** Consistent guarantee — "this framework never touches your real homelab-mcp state, period."

---

## Claude's Discretion

- **CD-01:** Exact module location of the env-allowlist constant (e.g., `mcp_client.py` top-level vs new `_isolation.py`). Pick whichever keeps the spawn-site comment block readable.
- **CD-02:** Windows tempdir cleanup-failure handling. Pick a reasonable trade-off; the success-criterion language ("No orphaned tempdirs after a clean run") is the bar.
- **CD-03:** Whether to also override `MCP_CONNECTION_NONBLOCKING`. Passthrough is the default under the `MCP_*` allowlist; flip to strip if it causes flakiness during ISOL-01 recon.
- **CD-04:** Order of work within the phase. Constraints: ISOL-01 → ISOL-02; ISOL-05 → ISOL-03; ISOL-06 last.

## Deferred Ideas

- Container/VM isolation (FINDINGS §3 trigger conditions).
- Per-tool isolation overrides → Phase 08.
- `extra_env` config knob → revisit when a real use case arrives.
- `MCP_CONNECTION_NONBLOCKING` semantics investigation (FINDINGS Q3).
- Spawned-PID survival regression test (FINDINGS Q7; v1.0 deferred-items carryover).
- `os.path.expanduser('~')` introspection inside the spawned subprocess for ISOL-06.
