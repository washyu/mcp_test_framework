---
phase: 06-per-session-host-state-isolation
plan: 02
subsystem: testing
tags: [isolation, fixtures, subprocess, env, keyring, phase-06]

# Dependency graph
requires:
  - phase: 06-01
    provides: "SHIP: ISOL-04 decision (PYTHON_KEYRING_BACKEND=keyring.backends.null.Null) recorded in 06-keyring-recon.md §3"
provides:
  - "src/mcp_test_framework/_isolation.py — module-level allowlist constants (D-07) + _build_isolated_env(Path) -> dict[str, str]"
  - "_isolated_home session fixture (loop_scope/scope='session', AsyncExitStack-owned tempfile.TemporaryDirectory(prefix='mcp-test-fw-')) — single source of truth for the per-session HOME redirect target (D-12 / D-14)"
  - "mcp_client fixture now threads env=_build_isolated_env(_isolated_home) into StdioServerParameters at the spawn site (ISOL-02 / ISOL-07)"
  - "McpTestClient.__aenter__ now creates a per-instance tempdir (prefix='mcp-test-fw-cli-') and passes env=_build_isolated_env(...) into StdioServerParameters — CLI list-tools and _preflight handshake paths are ALSO isolated (D-16 / D-17)"
affects: [06-03, 07, 08, 10]

# Tech tracking
tech-stack:
  added: []   # no new third-party deps; tempfile + pathlib are stdlib
  patterns:
    - "Underscore-private isolation module (_isolation.py) parallel to _owner_task / _preflight naming convention — no public Config surface added (D-06)"
    - "Allowlist as module-level tuple constants (not Config sub-model) — D-07; documented inline with FINDINGS §3 + ISOL-07 + DOC-07 widening warning"
    - "AsyncExitStack-owned sync tempfile.TemporaryDirectory via stack.enter_context — safe with respect to Phase 04.1 'no anyio cancel scope across the yield' invariant because TemporaryDirectory opens no anyio cancel scope"
    - "Reverse-order unwind ordering: tempdir registered with stack BEFORE stdio_client so subprocess closes first, then tempdir deletes (Windows handle-safety + POSIX correctness)"
    - "Distinct tempdir prefix per spawn path: 'mcp-test-fw-' (session fixture) vs 'mcp-test-fw-cli-' (CLI/preflight) for orphan-debug visibility in `dir %TEMP%`"

key-files:
  created:
    - "src/mcp_test_framework/_isolation.py — 97 lines: module docstring (D-05/D-06/D-07 + ISOL-04 SHIP rationale + caveat Q1 + DOC-07 widening warning), 4 module-level constants (_PASSTHROUGH_ALLOWLIST, _MCP_PREFIX, _HOME_OVERRIDES, _KEYRING_OVERRIDES), 1 function (_build_isolated_env)"
    - ".planning/phases/06-per-session-host-state-isolation/06-02-SUMMARY.md"
  modified:
    - "src/mcp_test_framework/fixtures.py — +tempfile/Path/_build_isolated_env imports; new _isolated_home fixture (lines 173-208); mcp_client signature gains _isolated_home: Path (line 213); StdioServerParameters at line 244 receives env=_build_isolated_env(_isolated_home) at line 248"
    - "src/mcp_test_framework/mcp_client.py — +tempfile/Path/_build_isolated_env imports; __aenter__ at line 139 now creates a per-instance tempdir (line 156-160) registered with the AsyncExitStack BEFORE stdio_client; StdioServerParameters at line 161-165 receives env=_build_isolated_env(isolated_home)"

key-decisions:
  - "ISOL-04 SHIPped per Plan 06-01: PYTHON_KEYRING_BACKEND=keyring.backends.null.Null injected via _KEYRING_OVERRIDES module-level constant in _isolation.py. Caveat (recon §3 Q1) inherited by Plan 06-03 — only short-circuits the Python keyring library, not direct Win32 CredWrite calls; ISOL-03 will need a cmdkey /list snapshot to cover the residual surface."
  - "Allowlist module shape per CD-01: a NEW module (_isolation.py) rather than top-level helpers in mcp_client.py. Rationale: schema_validator.py established the single-purpose pure-data module convention; _isolation.py mirrors that shape (no class, module-level constants, from __future__ import annotations, no third-party imports beyond stdlib). Future Phase 07/08/10 maintainers find isolation surface in one obvious place."
  - "Tempdir prefix divergence: session fixture uses 'mcp-test-fw-' (D-14 single source of truth) while McpTestClient.__aenter__ uses 'mcp-test-fw-cli-' (D-16 per-instance). The distinct prefix ensures `dir %TEMP%` filtering can tell session-orphan from CLI-orphan during debug, and the D-14 single-source rule remains satisfied because there is exactly ONE 'mcp-test-fw-' (no -cli suffix) call in fixtures.py."

patterns-established:
  - "Phase 04.1 invariant preservation pattern: env construction lives on the synchronous setup path BEFORE _owner_task is created (line 244 in fixtures.py — params block). The _owner_task body and the 'NO anyio cancel scopes across the yield' docstring at lines 214-243 are byte-identical to the pre-edit version. Future modifications to the spawn env must not move the env build into the owner task."
  - "Reverse-order tempdir/subprocess unwind via AsyncExitStack: register tempdir BEFORE stdio_client so subprocess (with any open file handles in the redirected HOME) closes first, then tempdir deletes. Verified: in mcp_client.py __aenter__, stack.enter_context (line 157) precedes stack.enter_async_context(stdio_client(...)) (line 166)."
  - "Inline decision-traceability comments at code change sites: each new env= kwarg carries a comment naming the requirements/decisions it satisfies (e.g., 'ISOL-02 / ISOL-07 -- Phase 06 (D-14: shared tempdir)' in fixtures.py line 247; 'ISOL-02 / D-16 / D-17' in mcp_client.py line 164). Verifier and future phase planners can grep for D-NN tokens to find honor sites."

requirements-completed: [ISOL-02, ISOL-04, ISOL-05, ISOL-07]

# Metrics
duration: 4min
completed: 2026-05-07
---

# Phase 06 Plan 02: Per-Session Host-State Isolation Wiring Summary

**Allowlist + HOME-redirect env wired into both MCP subprocess spawn paths (session fixture and CLI __aenter__) via new _isolation.py module + _isolated_home session fixture; PYTHON_KEYRING_BACKEND=keyring.backends.null.Null shipped per Plan 06-01.**

## Performance

- **Duration:** ~4 min (start 2026-05-07T08:37:44Z; end 2026-05-07T08:41:38Z)
- **Started:** 2026-05-07T08:37:44Z
- **Completed:** 2026-05-07T08:41:38Z
- **Tasks:** 3
- **Files modified:** 2 (fixtures.py, mcp_client.py); 1 created (_isolation.py); 1 SUMMARY.md created

## Accomplishments

- **ISOL-02, ISOL-05, ISOL-07 implemented in one coherent vertical slice.** New `_isolation.py` module owns the env-allowlist constant + `_build_isolated_env(Path) -> dict[str, str]` helper. The `mcp_client` fixture and `McpTestClient.__aenter__` both now thread the allowlist-plus-HOME-redirect dict into `StdioServerParameters(env=...)` — the subprocess sees ONLY allowlisted vars (PATH, SYSTEMROOT, LANG, USERNAME, MCP_*) plus HOME/USERPROFILE/TEMP/TMP/TMPDIR pointing at a per-session (or per-instance) tempdir.
- **ISOL-04 shipped per Plan 06-01's SHIP decision.** A fourth module-level constant `_KEYRING_OVERRIDES = {"PYTHON_KEYRING_BACKEND": "keyring.backends.null.Null"}` is applied inside `_build_isolated_env` after the home overrides. Smoke-tested: `_build_isolated_env(Path('/tmp/foo'))` returns a dict containing the expected key with the expected value.
- **Phase 04.1 invariant preserved end-to-end.** The "no anyio cancel scope across the yield" docstring at fixtures.py:214-243 is byte-identical, and the `_owner_task` body lines 254-277 are byte-identical to the pre-edit version. Env construction stays on the synchronous setup path at line 244 (BEFORE `_owner_task` is defined). The `_isolated_home` fixture uses `stack.enter_context` (sync ctx mgr — `tempfile.TemporaryDirectory` opens no anyio cancel scope) so it does not regress the invariant.
- **CLI path also isolated (D-16/D-17).** `McpTestClient.__aenter__` now creates a per-instance `tempfile.TemporaryDirectory(prefix="mcp-test-fw-cli-")` registered with the existing `AsyncExitStack` BEFORE `stdio_client`, ensuring reverse-order unwind tears down the subprocess first then deletes the tempdir. Phase 10 DOC-05 can now claim unconditional README isolation coverage — no awkward "tests isolated; CLI inspector not" carve-out.
- **Tests still green; lint clean.** `uv run pytest tests/unit -q` → 56/56 passed. `uv run ruff check src/mcp_test_framework/_isolation.py src/mcp_test_framework/fixtures.py src/mcp_test_framework/mcp_client.py` → All checks passed. Cross-file import smoke (`import mcp_test_framework.fixtures, mcp_test_framework.mcp_client, mcp_test_framework._isolation`) succeeds.

## Final Allowlist Contents (one-line summary)

`_PASSTHROUGH_ALLOWLIST=(PATH, SYSTEMROOT, LANG, USERNAME)` + `_MCP_PREFIX="MCP_"` + `_HOME_OVERRIDES=(HOME, USERPROFILE, TEMP, TMP, TMPDIR) -> str(isolated_home)` + `_KEYRING_OVERRIDES={"PYTHON_KEYRING_BACKEND": "keyring.backends.null.Null"}` (ISOL-04 SHIPped).

## ISOL-04 Disposition

**SHIPped.** `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` is injected into `_build_isolated_env`'s return dict via the `_KEYRING_OVERRIDES` module-level constant in `src/mcp_test_framework/_isolation.py` (lines 64-67 source; applied at the function body's `env.update(_KEYRING_OVERRIDES)` call). No DEFER trigger comments are required.

**Caveat inherited by Plan 06-03 (recon §3 Q1):** This only short-circuits the Python `keyring` library's backend chain. Direct Win32 `CredWrite` / libsecret calls via `ctypes` would bypass it. The `_isolation.py` module docstring documents this caveat explicitly. Plan 06-03's ISOL-03 verification should include a `cmdkey /list` (or platform-equivalent) snapshot to cover the residual surface.

## Phase 04.1 Invariant Preservation (citation)

The "no anyio cancel scope across the yield" docstring at `src/mcp_test_framework/fixtures.py:214-243` is byte-identical to the pre-edit version (verified by grep: 2 hits in the file — one in the new `_isolated_home` fixture's docstring referencing the invariant by name, and one in the original `mcp_client` docstring stating the invariant verbatim). The `_owner_task` body (lines 254-277, including the `with anyio.fail_after(...)` block) is unchanged. Env construction happens at line 244 in `params = StdioServerParameters(...)`, on the synchronous setup path BEFORE `loop = asyncio.get_running_loop()` and the `asyncio.create_task(_owner_task(), name="mcp_client_owner")` call.

## Post-Edit Line Numbers (for Plan 06-03 structural references)

| Symbol | File | Line |
|---|---|---|
| `async def _isolated_home() -> Path:` | `src/mcp_test_framework/fixtures.py` | 178 |
| `async def mcp_client(config: Config, _preflight, _isolated_home: Path):` | `src/mcp_test_framework/fixtures.py` | 213 |
| `params = StdioServerParameters(` (mcp_client fixture spawn) | `src/mcp_test_framework/fixtures.py` | 244 |
| `env=_build_isolated_env(_isolated_home),` (mcp_client fixture) | `src/mcp_test_framework/fixtures.py` | 248 |
| `async def __aenter__(self) -> "McpTestClient":` | `src/mcp_test_framework/mcp_client.py` | 139 |
| `isolated_home = Path(` (CLI path tempdir) | `src/mcp_test_framework/mcp_client.py` | 156 |
| `params = StdioServerParameters(` (__aenter__ spawn) | `src/mcp_test_framework/mcp_client.py` | 161 |
| `env=_build_isolated_env(isolated_home),` (__aenter__) | `src/mcp_test_framework/mcp_client.py` | 164 |

## Task Commits

Each task was committed atomically:

1. **Task 1: Create _isolation.py with allowlist constants and _build_isolated_env()** — `8e9c083` (feat)
2. **Task 2: Add _isolated_home fixture and inject env into mcp_client spawn** — `702bcf7` (feat)
3. **Task 3: Inject env into McpTestClient.__aenter__ (D-16/D-17 CLI path)** — `d4fd8de` (feat)

**Plan metadata:** _(pending — final commit will include this SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md)_

## Files Created/Modified

- `src/mcp_test_framework/_isolation.py` — NEW. Module-level allowlist constants + `_build_isolated_env()`. 97 lines. No class, no public API surface.
- `src/mcp_test_framework/fixtures.py` — MODIFIED. Added `tempfile`/`Path`/`_build_isolated_env` imports; new session-scoped `_isolated_home` fixture; `mcp_client` signature now takes `_isolated_home: Path`; `StdioServerParameters` receives `env=_build_isolated_env(_isolated_home)`. Phase 04.1 docstring + `_owner_task` body unchanged.
- `src/mcp_test_framework/mcp_client.py` — MODIFIED. Added `tempfile`/`Path`/`_build_isolated_env` imports; `__aenter__` creates per-instance `tempfile.TemporaryDirectory(prefix="mcp-test-fw-cli-")` registered with the AsyncExitStack BEFORE `stdio_client`; `StdioServerParameters` receives `env=_build_isolated_env(isolated_home)`. `__aexit__`, `_wrap`, `list_tools`, `get_tool`, `call_tool`, `_LoggerWriter`, `ToolNotFoundError` unchanged. The "NO 5s force-kill belt" docstring + `__aexit__` body preserved verbatim (grep count == 2, same as pre-edit).

## Decisions Made

- **CD-01 (allowlist module shape):** Created a NEW underscore-private module `_isolation.py` rather than embedding helpers in `mcp_client.py`. Rationale: `schema_validator.py` established the single-purpose pure-data module convention in this codebase (no class, module-level constants, `from __future__ import annotations`, stdlib-only imports). `_isolation.py` mirrors that shape, gives Phase 07/08/10 maintainers one obvious place to find isolation surface, and is consistent with the framework's existing layering. Both `fixtures.py` and `mcp_client.py` import the helper from a single canonical location.
- **Tempdir prefix split (session vs CLI):** Session fixture uses prefix `"mcp-test-fw-"`; CLI/preflight `__aenter__` path uses `"mcp-test-fw-cli-"`. The distinct prefix preserves the D-14 single-source-of-truth rule (there is exactly one `tempfile.TemporaryDirectory(prefix="mcp-test-fw-")` call — no -cli suffix — in fixtures.py) while making orphan-debug filtering trivial in `dir %TEMP%`.
- **Inline-comment decision tagging:** Each env= kwarg site carries a one-line comment naming the requirements/decisions it satisfies (e.g., `ISOL-02 / ISOL-07 -- Phase 06 (D-14: shared tempdir)`, `ISOL-02 / D-16 / D-17`). This is a deliberate readability choice: the verifier and future planners can grep for `D-NN` tokens to find honor sites in code.

## Deviations from Plan

None - plan executed exactly as written.

The PLAN.md provided pseudo-code for the `params` block in fixtures.py with the `env=` comment as an inline trailing comment. During Task 2 the trailing-comment form exceeded ruff's 100-char line limit (E501), so the comment was lifted onto its own line above the `env=` argument. This is a cosmetic line-break adjustment driven by the project's lint config, not a behavioral deviation — the resulting AST is identical.

## Issues Encountered

- **E501 line-too-long on first env= comment placement.** Resolved by lifting the inline comment onto its own line above the `env=` argument. No semantic change. Detected and fixed within Task 2 before commit.
- **CLI smoke result expected per acceptance criteria:** `uv run mcp-test-framework list-tools` exits with `FileNotFoundError: MCP server command not on PATH: 'homelab-mcp'` because the homelab-mcp binary is not installed in this dev worktree. The acceptance criterion explicitly accepted this outcome ("either succeeds OR fails with the friendly `MCP server command not on PATH` error — NOT with a tempdir/import error"). The friendly path was reached, confirming the import wiring is clean and the per-instance tempdir code is reachable. Runtime end-to-end smoke against a live homelab-mcp binary is owned by Plan 06-03's ISOL-03 verification.

## User Setup Required

None — pure code change; no external service configuration required. The injected env (`PYTHON_KEYRING_BACKEND=keyring.backends.null.Null`) is set automatically per spawn and requires no developer action.

## Next Phase Readiness

- **Plan 06-03 (ISOL-03 verification) unblocked.** Plan 06-03 can consume `_isolated_home` as a fixture parameter to read the redirected `.homelab_mcp/` subdirectory directly (D-13/D-14), and its structural-shape assertions can rely on the line numbers documented in the "Post-Edit Line Numbers" table above.
- **Recon §3 Q1 caveat (cmdkey/Win32 bypass) is inherited by Plan 06-03.** ISOL-03's verification surface should include a `cmdkey /list` (or platform-equivalent) snapshot in addition to the redirected-HOME hash assertions, per the recommendation in 06-01-SUMMARY.md "Caveats Affecting ISOL-03 Test Design" §1.
- **Phase 10 DOC-05 unblocked for unconditional claim.** Both spawn paths (session fixture + CLI `list-tools`) are now isolated, so the README's "Isolation guarantee" section can state plainly that the framework never touches real homelab-mcp state — no carve-out needed (D-17 honored).

## Threat Flags

None. The threat surface introduced by this plan (env crossing the framework→subprocess boundary, tempdir as HOME) is fully covered by the threat register in 06-02-PLAN.md (T-06-05 through T-06-10). No new endpoints, auth paths, or trust boundaries were introduced beyond the planned scope.

## Self-Check: PASSED

**Files exist:**
- `src/mcp_test_framework/_isolation.py` — FOUND
- `src/mcp_test_framework/fixtures.py` (modified) — FOUND
- `src/mcp_test_framework/mcp_client.py` (modified) — FOUND
- `.planning/phases/06-per-session-host-state-isolation/06-02-SUMMARY.md` — being written now

**Commits exist (`git log --oneline -5` confirms):**
- `8e9c083` Task 1 — FOUND
- `702bcf7` Task 2 — FOUND
- `d4fd8de` Task 3 — FOUND

**Verification commands replayed:**
- `uv run python -c "from mcp_test_framework._isolation import _build_isolated_env; ..."` → OK
- `uv run pytest tests/unit -q` → 56 passed
- `uv run ruff check src/mcp_test_framework/_isolation.py src/mcp_test_framework/fixtures.py src/mcp_test_framework/mcp_client.py` → All checks passed
- `uv run python -c "import mcp_test_framework.fixtures, mcp_test_framework.mcp_client, mcp_test_framework._isolation; print('OK')"` → OK
- Phase 04.1 docstring grep (`anyio cancel scope`): 3 hits — line 190 (new fixture's docstring referencing the invariant), line 216 (preserved original docstring), line 255 (preserved owner-task comment).

---
*Phase: 06-per-session-host-state-isolation*
*Completed: 2026-05-07*
