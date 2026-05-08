# Phase 06: Per-session host-state isolation - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Make `mcp_test_framework` test runs (and the `list-tools` CLI inspector) stop mutating the user's real `~/.homelab_mcp/` directory and OS keyring. The framework spawns the MCP subprocess inside a per-session tempdir with `HOME` / `USERPROFILE` redirected, so `os.path.expanduser('~')` inside the subprocess resolves to the tempdir on Windows and POSIX alike. ISOL-01 (keyring-touch investigation) is the gating first task — its outcome decides whether ISOL-04 ships in v1.1 or is documented as deferred.

**In scope (per ROADMAP.md and REQUIREMENTS.md):** ISOL-01..ISOL-07.

**Explicitly NOT in scope:** container/VM isolation, multi-server orchestration, HTTP/SSE transport, multi-tool discovery (Phase 07), per-tool config registry (Phase 08), JUnit output (Phase 09).

</domain>

<decisions>
## Implementation Decisions

### ISOL-01 — Keyring-touch investigation method
- **D-01:** Investigation runs as a one-off recon task **before** ISOL-02 lands. Method: read the public homelab-mcp PyPI README for documented keyring touchpoints (no source-read), then snapshot `cmdkey /list | findstr homelab` before/after a real test invocation and diff. Both pieces of evidence land in a short FINDINGS-style document.
- **D-02:** Recon output: `.planning/phases/06-per-session-host-state-isolation/06-keyring-recon.md` capturing (a) PyPI README quotes, (b) cmdkey diff result, (c) explicit ship-or-defer call for ISOL-04. Mirrors the [260506-qxs spike](.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md) pattern.
- **D-03:** ISOL-01 is **not** a permanent CI test. Investigation is one-time; the regression guard against keyring mutation is owned by ISOL-03's hash-equality assertion on real-state files. (Keyring entries are not in those files — if `homelab-mcp` mutates the keyring at runtime, the only way that escapes ISOL-03 is if it doesn't also touch the registry. ISOL-01's recon is the protection against that case.)
- **D-04:** If ISOL-01 finds keyring is touched → ISOL-04 ships with `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` injected into the spawned env. If not touched → ISOL-04 is documented as "not needed for v1.1's tool surface; revisit if v1.x adds tools that touch credentials" and the trigger condition is recorded in `06-keyring-recon.md`.

### Configuration surface
- **D-05:** Isolation is **always-on, no toggle**. There is no `IsolationConfig.isolate: bool` flag, no `--no-isolation` CLI escape hatch. The framework's contract is "test runs do not mutate your real homelab-mcp state, period." Users who want to test against real state must fork or not use this framework.
- **D-06:** No new public Config sub-model is added for isolation. Specifically: do **not** add `IsolationConfig` or `extra_env` per the FINDINGS §4 sketch — it's API surface we'd be committing to maintain for v1.1.
- **D-07:** The env passthrough allowlist (`PATH`, `SYSTEMROOT`, `LANG`, `USERNAME`, `MCP_*` per ISOL-07, plus `HOME` / `USERPROFILE` / `TEMP` / `TMP` / `TMPDIR` overrides per FINDINGS §3) lives as a module-level constant at the spawn site (`src/mcp_test_framework/fixtures.py` and `src/mcp_test_framework/mcp_client.py`). Documented inline with a comment block citing FINDINGS §3 + ISOL-07.

### ISOL-03 — Verification test rigor
- **D-08:** Verification is **sha256-of-real-files + tempdir-positive-assertion**. The test:
  1. Captures sha256 of `~/.homelab_mcp/credential_registry.json`, `~/.homelab_mcp/known_hosts`, `~/.homelab_mcp/migration_state.json` before the run.
  2. Acquires the `mcp_client` fixture and explicitly calls `call_tool` for each tool exercised by the rest of the suite (`list_keyring_credentials`, `list_registered_servers` at v1.1 surface).
  3. Re-hashes the 3 real files; asserts every hash is unchanged.
  4. Asserts the per-session tempdir's `<tempdir>/.homelab_mcp/` directory exists (proves redirection actually happened — guards against the "tools just no-op'd" silent pass).
- **D-09:** Hashes (not mtimes). mtime-only would miss same-second overwrites with identical content. Cross-platform clean — no Sysinternals dependency on Windows, no `/proc/<pid>/fd/` POSIX-specific lookup.
- **D-10:** Test scope: **in-process**, not a recursive `uv run pytest` subprocess. The test's own `mcp_client` fixture invocation is the run-under-test; calling each judged tool covers the actual operations the framework triggers. No self-recursion pattern.
- **D-11:** Behavior when `~/.homelab_mcp/` doesn't exist on the host (fresh CI runner): `pytest.skip("No real ~/.homelab_mcp/ to compare against — ISOL-03 vacuous on this host")`. The test's value lives on a developer machine that has the real install — exactly where bleed-through bites. Skipping cleanly on a fresh CI box is acceptable.

### Tempdir fixture seam
- **D-12:** New `_isolated_home` session-scoped fixture: `@pytest_asyncio.fixture(loop_scope="session", scope="session") async def _isolated_home() -> Path` that yields a `tempfile.TemporaryDirectory` path, owned via `AsyncExitStack`. Lives in `src/mcp_test_framework/fixtures.py`.
- **D-13:** `mcp_client` fixture takes `_isolated_home` as a dependency and threads it into `StdioServerParameters(env={...})`. The ISOL-03 test also depends on `_isolated_home` directly so it can read the tempdir path without reaching into `mcp_client` internals.
- **D-14:** The `_isolated_home` fixture is the **single source of truth** for the per-session tempdir path. Future Phase 07/08 fixtures that need isolation guarantees depend on the same fixture — no duplicate tempdir creation.
- **D-15:** Cleanup is automatic via context-manager exit. The phase success criterion "no orphaned tempdirs after a clean run" is enforced by `tempfile.TemporaryDirectory`'s own `__aexit__`. Windows cleanup-failure handling (un-deletable handles) is **Claude's discretion** — see below.

### CLI path coverage
- **D-16:** The standalone `McpTestClient.__aenter__()` path ([mcp_client.py:135](src/mcp_test_framework/mcp_client.py:135)) — used by `mcp-test-framework list-tools` — also gets isolation. It creates its own short-lived tempdir on entry and tears it down on exit. Same env-override + allowlist as the fixture path.
- **D-17:** Consequence for DOC-05: README's "Isolation guarantee" section can state unconditionally that "this framework never touches your real homelab-mcp state," not the awkward split "test runs are isolated; the CLI inspector isn't."

### Claude's Discretion
- **CD-01:** Exact module location of the env-allowlist constant (e.g., `mcp_client.py` top-level vs new `_isolation.py`). Pick whichever keeps the spawn-site comment block readable.
- **CD-02:** Windows tempdir cleanup-failure handling. `tempfile.TemporaryDirectory` on Windows can warn-not-fail when a child still holds a handle. Pick a reasonable trade-off (suppress warning if subprocess is confirmed-exited; surface it as a test failure if orphaned files actually remain). The success-criterion language ("No orphaned tempdirs exist on disk after a clean run") is the bar.
- **CD-03:** Whether to also override `MCP_CONNECTION_NONBLOCKING` (currently set in user env per [FINDINGS §2 / raw/env_scan.txt](.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md)). It matches the `MCP_*` allowlist so passthrough is the default; flip to strip if it causes flakiness during ISOL-01 recon.
- **CD-04:** Order of work within the phase: ISOL-01 recon must precede ISOL-02 wiring (gating). ISOL-05 (fixture lifecycle) must land before ISOL-03 (test). ISOL-06 (cross-platform smoke) is the last gate. Planner picks the exact plan-cut.

### Folded Todos
- **2026-05-07-v1-1-isolate-test-runs-from-user-state.md** (`resolves_phase: 6`, `area: testing`)
  - **Original problem:** "Framework currently spawns homelab-mcp as a subprocess for each test session via stdio_client. The subprocess appears to be sharing state with the user's real homelab-mcp instance — user reported (2026-05-06) that they cannot use homelab-mcp normally because tests bring up an instance, tear it down, and seem to clear any running instance / mutate registry state at the start of the run."
  - **Fit:** This is the source todo for Phase 06 itself. The acceptance criterion ("Test runs MUST NOT mutate any user-visible state on the host") maps 1:1 to ISOL-03's success criterion. The "investigation precedes design" note maps to ISOL-01 → ISOL-02 ordering captured in CD-04. The four isolation strategies are already filtered: strategy 1 (HOME override + tempdir) is locked, strategies 2/3 (CLI flag, cwd-redirect) ruled out by FINDINGS, strategy 4 (container) deferred.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 06 row + "Phase 06: Per-session host-state isolation" details (goal, depends-on, requirements, 5 success criteria)
- `.planning/REQUIREMENTS.md` §"ISOL — Per-session host-state isolation" — ISOL-01..ISOL-07 acceptance criteria and traceability table
- `.planning/PROJECT.md` §"Current Milestone: v1.1" — anti-scope, performance constraints, parallelism prerequisite

### Investigation foundation (mandatory pre-read for ISOL-01 and ISOL-02)
- `.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md` — full host-state surface inventory; §1 (state homelab-mcp creates/mutates), §2 (isolation knobs available — confirms no CLI flag exists), §3 (recommended HOME-override strategy + keyring caveat), §4 (effort estimate per component), §5 (open questions Q1–Q7)
- `.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/keyring.txt` — list of ~20 keyring entries scoped to homelab-mcp targets (input to ISOL-01)
- `.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/help.txt` — homelab-mcp `--help` output, confirms zero isolation flags exist (do not re-fetch)

### Source todo
- `.planning/todos/pending/2026-05-07-v1-1-isolate-test-runs-from-user-state.md` — original user complaint + acceptance criterion + investigation strategies (1–4)

### Project rules
- `CLAUDE.md` §"Architecture Notes" — MCP transport is stdio only via `stdio_client`; framework treats homelab-mcp as a black box (no source reading); `asyncio.timeout` around subprocess/HTTP operations; session-scoped fixtures
- `docs/mcp_test_framework_mvp_spec.md` — authoritative MVP design doc

### Implementation seams (existing code to modify)
- `src/mcp_test_framework/fixtures.py` — `mcp_client` session fixture at line 175; `_owner_task` spawn at line 207 with `StdioServerParameters(command, args)` — env override goes here
- `src/mcp_test_framework/mcp_client.py` — `McpTestClient.__aenter__` at line 135; standalone spawn for CLI `list-tools` — env override goes here too (D-16)
- `src/mcp_test_framework/models.py` — `McpServerConfig` at line 45; **no new fields added per D-06** (allowlist is module constant, not Config field)
- `src/mcp_test_framework/cli.py` — CLI commands; `list-tools` consumes `McpTestClient.__aenter__` (D-16 affects this path)

### v1.0 lifecycle pattern to preserve (do NOT regress)
- `.planning/phases/04.1-*` — Phase 04.1 owner-task + anyio.Event fixture rewrite (referenced in PROJECT.md Key Decisions). Any change to `_owner_task` body must preserve the "no anyio cancel scope across the yield" invariant — see [fixtures.py:179-205](src/mcp_test_framework/fixtures.py:179) docstring.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`mcp_client` session fixture pattern** ([fixtures.py:175](src/mcp_test_framework/fixtures.py:175)) — `_isolated_home` follows the same `loop_scope="session", scope="session"` shape. Established loop-scoping convention is honored.
- **`AsyncExitStack` ownership pattern** ([mcp_client.py:144](src/mcp_test_framework/mcp_client.py:144) and the owner-task body) — the new `_isolated_home` fixture wraps `tempfile.TemporaryDirectory` in an `AsyncExitStack` so cleanup is uniform with the rest of the lifecycle.
- **`AliasChoices` env-var pattern** ([models.py:30-42](src/mcp_test_framework/models.py:30)) — established but **not used** for the env-allowlist (per D-06, allowlist is a module-level constant; no new Config fields).
- **`asyncio.timeout`/`anyio.fail_after` pattern** ([mcp_client.py:150](src/mcp_test_framework/mcp_client.py:150), [fixtures.py:223](src/mcp_test_framework/fixtures.py:223)) — wrap any new I/O (e.g., temp-dir creation if it ever blocks; reading hashes in ISOL-03).

### Established Patterns
- **Black-box rule** mechanically enforced via `ruff TID251` + `sys.modules` guard (PROJECT.md). Reading homelab-mcp source is a hard fail. ISOL-01's PyPI README pass is the only documentation-side info source allowed.
- **`StdioServerParameters` is the env injection seam** — the `mcp` SDK accepts an `env=` kwarg that gets passed to `anyio.open_process`. There is no other place in the framework where env can be controlled for the subprocess.
- **No anyio cancel scope across the yield** ([fixtures.py:179-205](src/mcp_test_framework/fixtures.py:179) docstring + Phase 04.1 history). The `_isolated_home` fixture must respect this — its `tempfile.TemporaryDirectory` (or its `AsyncExitStack`) cannot span the yield in a way that pins the scope to one task.
- **Pure-asyncio driver + anyio owner task** ([fixtures.py:215-237](src/mcp_test_framework/fixtures.py:215)) — env override happens BEFORE `_owner_task` is created, by building the `params` object on line 207 with `env=` populated.

### Integration Points
- **Spawn site #1** — [fixtures.py:207-210](src/mcp_test_framework/fixtures.py:207): `StdioServerParameters(command=config.mcp_server.command, args=config.mcp_server.args)` becomes `StdioServerParameters(command=..., args=..., env=_build_isolated_env(isolated_home))`. The helper `_build_isolated_env(path)` lives in the same module (or a sibling `_isolation.py` per CD-01) and consumes the module-level allowlist constant.
- **Spawn site #2** — [mcp_client.py:143](src/mcp_test_framework/mcp_client.py:143): same change shape, but with a per-instance short-lived tempdir (D-16) since this path is not session-scoped.
- **ISOL-03 test location** — new file under `tests/`, e.g., `tests/test_isolation.py`. Depends on `_isolated_home` AND `mcp_client` fixtures (the latter triggers the spawn-under-test).
- **CLI list-tools** ([cli.py](src/mcp_test_framework/cli.py)) — no changes to user-facing flags; the isolation just kicks in via the updated `McpTestClient.__aenter__`. README's `list-tools` doc gets an isolation note (DOC-05 / Phase 10).

</code_context>

<specifics>
## Specific Ideas

- **Recon doc shape:** mirrors `260506-qxs/FINDINGS.md` — sections 1 (PyPI README quotes / docs evidence), 2 (cmdkey before/after diff), 3 (ship-or-defer decision with explicit trigger conditions for the deferred path).
- **ISOL-03 file list is currently the v1.1 surface only** (`credential_registry.json`, `known_hosts`, `migration_state.json`). When v1.x adds tools that touch other paths under `~/.homelab_mcp/`, the test's file list updates additively. Glob over the directory? Not for v1.1 — explicit list keeps the test's claim narrow and auditable.
- **Tempdir prefix:** use a recognizable prefix like `mcp-test-fw-` so an orphaned tempdir (should ISOL-05 cleanup ever fail) is debuggable from `dir %TEMP%` output.
- **DOC-05 wording (forward-looking, Phase 10):** "Test runs and `mcp-test-framework list-tools` do not mutate your real homelab-mcp state. Verified by `tests/test_isolation.py::test_real_state_unchanged`."

</specifics>

<deferred>
## Deferred Ideas

- **Container/VM isolation** — out of scope for v1.1 ([FINDINGS §3](.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md)). Trigger: ISOL-01 finds homelab-mcp ignores `HOME` AND `PYTHON_KEYRING_BACKEND`, OR future tools require network isolation.
- **Per-tool isolation overrides** (e.g., a tool that legitimately needs to read the user's real keyring during a specific test) — defer to Phase 08 (per-tool config registry) where it can be expressed as a config field.
- **`extra_env` config knob** for power-user env injection — explicitly NOT shipped in v1.1 (D-06). Revisit if a real use case arrives (likely a future phase that expands the testable tool surface).
- **`MCP_CONNECTION_NONBLOCKING=true` semantics investigation** — open question Q3 in [FINDINGS §5](.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md). Passing through under the `MCP_*` allowlist is fine for v1.1; document semantics if it affects test flakiness.
- **Spawned-PID survival regression test** — open question Q7 in FINDINGS §5 ("are there homelab-mcp PIDs that survive past AsyncExitStack unwind?"). Carries forward from v1.0 deferred-items list (cross-platform SIGINT UAT scaffolding). Distinct from this phase's filesystem isolation guarantee.
- **`os.path.expanduser('~')` introspection inside the spawned subprocess** — would prove ISOL-06 directly, but the homelab-mcp tool surface doesn't expose a "where am I" probe. Defer with the trigger "if a future tool exposes path/env introspection, adopt as a stronger ISOL-06 signal."

### Reviewed Todos (not folded)
None — the only matched todo (`2026-05-07-v1-1-isolate-test-runs-from-user-state.md`) was folded.

</deferred>

---

*Phase: 06-per-session-host-state-isolation*
*Context gathered: 2026-05-07*
