# Phase 2: MCP Client Wrapper - Discussion Log

**Discussion date:** 2026-05-04
**Phase goal:** Driving `homelab-mcp` over stdio works end-to-end via `McpTestClient`, with explicit timeouts and `CallToolResult` shape handling proven in a smoke script before any fixture depends on it.

This log is a human-reference audit trail. The canonical artifact for downstream agents is `02-CONTEXT.md`.

---

## Gray Areas Presented

Four phase-specific gray areas surfaced during analysis (driven by Phase 1 prior decisions, the `mcp_client.py` spec interface, and `.planning/research/PITFALLS.md`):

1. **Smoke script home & lifecycle** — where the live-`homelab-mcp` script lives and whether it survives Phase 2.
2. **Timeout configuration shape** — hardcoded module constants vs new `McpServerConfig` field(s).
3. **Error semantics on `isError` / missing tool** — pass-through vs raise.
4. **Stderr capture target** — stdlib logger vs `sys.stderr` vs file.

User selected: **#1 (smoke script home & lifecycle)** and **#2 (timeout configuration shape)**.
User passed (Claude's discretion): **#3 (error semantics)** and **#4 (stderr capture target)**.

---

## Area 1 — Smoke script home & lifecycle

### Q1: Where does the Phase 2 smoke script live, and what happens to it after Phase 2 is verified?

**Options presented:**
- `scripts/smoke_phase02_mcp.py` — keep (committed permanent diagnostic)
- `scripts/smoke_phase02_mcp.py` — delete after verify (true throwaway, matches roadmap wording)
- `tests/smoke/test_smoke_homelab_mcp.py` — permanent live-marker pytest test, skipped by default

**User selection:** `tests/smoke/test_smoke_homelab_mcp.py` with `@pytest.mark.live_homelab`, skipped by default.

**Captured as:** D-01, D-02, D-04.

**Notes:**
- Roadmap wording ("throwaway smoke script") is intentionally overridden — the live pack has reusable value beyond Phase 2.
- Test functions must collectively cover both Phase 2 success criteria #1 (raw `stdio_client`) and #2 (`McpTestClient.call_tool` round-trip). Whether one test or two is a planner detail.

### Q2: How does `live_homelab` get skipped by default?

**Options presented:**
- pyproject `addopts = "-m 'not live_homelab'"` (pure-pytest, no env var)
- conftest.py `pytest_collection_modifyitems` hook keyed off `MCPTF_LIVE=1` env var

**User selection:** pyproject `addopts` mechanism.

**Captured as:** D-03.

**Notes:**
- `MCPTF_LIVE` route deferred — see Deferred Ideas in CONTEXT.md.
- Same marker pattern will extend to Phase 4 (which is entirely live tests).

---

## Area 2 — Timeout configuration shape

### Q3: How should the per-call timeout ceilings be expressed?

**Options presented:**
- Three hardcoded module-level constants in `mcp_client.py` (zero new config surface)
- Single `McpServerConfig.timeout_seconds` knob (Recommended) — mirrors `OllamaConfig.timeout_seconds`
- Three separate fields (`init_timeout_seconds` / `list_timeout_seconds` / `call_timeout_seconds`)

**User selection:** Single `McpServerConfig.timeout_seconds` (Recommended).

**Captured as:** D-05, D-06, D-07, D-08.

**Notes:**
- Same 30s ceiling applies to `initialize`, `list_tools`, `call_tool` — ceiling, not target.
- New env var `MCP_SERVER_TIMEOUT_SECONDS` requires a precedence test in `tests/unit/test_config.py` per the Phase 1 lesson "EnvSettingsSource does not walk sub-model `validation_alias`" — silent default-fallback would otherwise be invisible.
- `McpTestClient.__init__` signature evolves additively from spec's `(command, args)` to `(command, args, timeout_seconds)`.
- Per-call separate knobs deferred — see Deferred Ideas in CONTEXT.md.

---

## Claude's Discretion (areas the user passed on)

Captured directly into CONTEXT.md `<decisions>` § "Claude's Discretion":

- **Error semantics on `isError=true`:** Pass-through `CallToolResult`; tests assert.
- **Error semantics on `get_tool` not found:** Custom `ToolNotFoundError` with candidate list.
- **Stderr capture target:** Stdlib logger `mcp_test_framework.mcp_client.stderr` at WARNING level, no handlers attached by the wrapper.
- **Subprocess cleanup belt:** `AsyncExitStack` ownership inside `McpTestClient` (Pitfall 1) + 5s defensive force-kill in `__aexit__` (Pitfall 4).
- **`get_tool` impl:** Re-fetches via `list_tools`; no cache.
- **`shutil.which` resolution:** In `__aenter__` to surface clean `FileNotFoundError` on Windows when binary missing (Pitfall 14).
- **Phase 2 unit tests scope:** `ToolNotFoundError` payload + `MCP_SERVER_TIMEOUT_SECONDS` precedence test. Live behavior covered by smoke test only.

---

## Scope Creep Captured

None during this discussion. Both selected gray areas remained in-scope for "HOW to implement CORE-03 + the four success criteria."

---

## Deferred Ideas

Recorded in CONTEXT.md `<deferred>`:

- Per-call timeout knobs (`init`/`list`/`call` separately).
- Smoke script as throwaway `scripts/` entry (rejected; available if future phases want it).
- `MCPTF_LIVE` env var gating (alternative to `addopts`).
- Custom `CallToolResult` validator wrapping helper.
- `McpTestClient.from_config(cfg)` classmethod variant.

---

*Discussion log generated: 2026-05-04*
