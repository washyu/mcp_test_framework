# Phase 2: MCP Client Wrapper - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the async stdio MCP client wrapper that drives `homelab-mcp` end-to-end:

1. `src/mcp_test_framework/mcp_client.py` exposing `McpTestClient` with the spec's public interface (`__init__(command, args, timeout_seconds)`, `__aenter__`/`__aexit__`, async `list_tools`/`get_tool`/`call_tool`)
2. Lifecycle owned via `contextlib.AsyncExitStack` inside `McpTestClient.__aenter__` so `stdio_client` + `ClientSession` enter/exit happen in the same task (Pitfall 1 mitigation)
3. Every SDK call (`initialize`, `list_tools`, `call_tool`) wrapped in `asyncio.timeout(self._timeout_seconds)` — same uniform ceiling
4. Server stderr captured via the SDK's `errlog` parameter and routed to a stdlib logger
5. Defensive `CallToolResult` shape handling — `isError` and `content` vs `structuredContent` are passed through unchanged for callers (tests in Phase 4) to assert on
6. `McpServerConfig.timeout_seconds` field added to `models.py` so the ceiling is env/YAML configurable
7. A live smoke pytest test at `tests/smoke/test_smoke_homelab_mcp.py` gated behind a `live_homelab` marker that satisfies success criteria #1 and #2 against the real `homelab-mcp` binary

**Not in scope (other phases):** Pytest fixtures consuming `McpTestClient` (Phase 4 FIX-01), CLI `list-tools` (Phase 5 CLI-02), Ollama judge (Phase 3), the full 10 spec'd test cases (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Smoke harness lives as a permanent live-marker pytest test

- **D-01:** The Phase-2 smoke harness is a real pytest test at `tests/smoke/test_smoke_homelab_mcp.py` — NOT a throwaway script under `scripts/`. It is committed and re-runnable indefinitely as part of the project's live-integration smoke pack. Rationale: the hand-runnable diagnostic and the future Phase 5 `list-tools` CLI overlap; keeping a permanent live smoke test gives non-zero ongoing value vs deleting the script after verify.
- **D-02:** Marker convention: `@pytest.mark.live_homelab`. Any test using this marker requires the `homelab-mcp` binary on `PATH` and a reachable subprocess; missing → test fails fast inside the test body, not at collection.
- **D-03:** Default-skip mechanism: pure pytest `addopts`, no env var, no conftest hook. Locked into `[tool.pytest.ini_options]` in `pyproject.toml`:
  ```toml
  markers = [
    "live_homelab: requires live homelab-mcp on PATH",
  ]
  addopts = "-m 'not live_homelab'"
  ```
  - `uv run pytest` skips live tests (default for unit/CI runs)
  - `uv run pytest -m live_homelab` runs live tests only
  - `uv run pytest -m ''` overrides to run everything
- **D-04:** The smoke test must cover BOTH Phase 2 success criteria #1 and #2:
  - SC#1: a function that uses raw `stdio_client` + `ClientSession` directly, lists tools, and asserts `list_registered_servers` is present with a non-empty schema (matches roadmap wording "without ever importing homelab_mcp")
  - SC#2: a function that drives `McpTestClient` (the wrapper this phase is shipping), calls `call_tool("list_registered_servers", {})`, and asserts `not result.isError` and that `content` or `structuredContent` is non-empty
  Whether these are one or two test functions is a planner detail; both criteria must be falsifiable in the test file.

### Single timeout knob on McpServerConfig

- **D-05:** Add ONE new field to `McpServerConfig`:
  ```python
  timeout_seconds: int = Field(
      default=30,
      ge=1,
      validation_alias=AliasChoices("MCP_SERVER_TIMEOUT_SECONDS", "timeout_seconds"),
  )
  ```
  Mirrors `OllamaConfig.timeout_seconds` shape. Frozen sub-model + `populate_by_name=True` already locked at the class level — no new pattern.
- **D-06:** The same `timeout_seconds` ceiling wraps all three SDK call sites (`session.initialize`, `session.list_tools`, `session.call_tool`). 30s default is a ceiling, not a minimum — fast paths complete quickly; pathological hangs surface as `TimeoutError` after 30s rather than indefinitely. Per-call separate knobs are deferred (see Deferred Ideas).
- **D-07:** Documentation/examples updated to support D-05:
  - `.env.example` adds `MCP_SERVER_TIMEOUT_SECONDS=30`
  - `config.example.yaml` adds `mcp_server.timeout_seconds: 30` (next to `command` / `args`)
  - At least one Phase 1-style precedence test in `tests/unit/test_config.py` MUST exercise `MCP_SERVER_TIMEOUT_SECONDS` env routing through `_BareNameNestedEnvSource` — Phase 1 lesson "EnvSettingsSource does not walk sub-model validation_alias" applies; the new field needs the same coverage shape as `OLLAMA_TIMEOUT_SECONDS`.
- **D-08:** `McpTestClient.__init__` signature: `__init__(self, command: str, args: list[str], timeout_seconds: int)` — additive over the spec's `(command, args)` wording; smallest-diff change. Phase 4 fixture wires it as `McpTestClient(cfg.mcp_server.command, cfg.mcp_server.args, cfg.mcp_server.timeout_seconds)`.

### Claude's Discretion

The user passed on these areas — planner/executor has flexibility within the constraints below:

- **Error semantics on `CallToolResult.isError=true`:** Pass-through. `McpTestClient.call_tool()` returns the SDK's `CallToolResult` unchanged; tests in Phase 4 assert `not result.isError`. This matches the spec interface verbatim and keeps the wrapper a thin contract layer rather than a re-interpreting one.
- **Error semantics on `get_tool(name)` not found:** Raise a custom `ToolNotFoundError(tool_name, available=[...])` exception with the candidate name list in the message. Lives in `mcp_client.py` (domain-local, paralleling Phase 1's `ValidationIssue` in `schema_validator.py`). Phase 4's `target_tool` fixture (FIX-03) catches this for its early-fail diagnostic.
- **Stderr capture target:** Plumb the SDK's `errlog` parameter to a stdlib logger named `mcp_test_framework.mcp_client.stderr` at `WARNING` level. The wrapper does `logging.getLogger("mcp_test_framework.mcp_client.stderr")` once and writes lines with `.warning(...)`. No handlers attached by the wrapper — pytest's log capture (or the user's own logging config) decides where the lines surface. Default `uv run pytest` shows them on test failure via `-rA`-style summary; `--log-cli-level=WARNING` streams them live.
- **Subprocess cleanup belt:** `__aexit__` lets `AsyncExitStack` unwind the `stdio_client` + `ClientSession` in reverse order in the same task (the Pitfall 1 documented mitigation). **Trust the SDK's built-in cleanup** — `mcp 1.27.0`'s `stdio_client` does not expose the `Process` handle to callers (it lives inside an internal `anyio.create_task_group()`), and the SDK's `_terminate_process_tree` already does SIGTERM → 2s wait → SIGKILL escalation, with a Job Object on Windows for guaranteed child cleanup. **Revised after research (Phase 2):** the original 5-second `process.kill()` belt is not implementable against the public SDK surface and would duplicate cleanup the SDK already performs correctly. No additional belt is added. If the SDK ever leaks a subprocess in practice, file an upstream issue rather than reaching past the public API.
- **`get_tool` implementation:** Re-fetches via `list_tools()` each call — no in-process cache. Cost is one stdio round-trip; cache invalidation is harder than it's worth at MVP scale. Phase 4's session-scoped fixture means the round-trip happens once per test session anyway.
- **Phase 2 unit tests scope:** `tests/unit/test_mcp_client.py` covers the pure-data slices that are mock-friendly: `ToolNotFoundError` payload shape and at minimum one precedence test for the new `MCP_SERVER_TIMEOUT_SECONDS` env var (the latter belongs in `tests/unit/test_config.py` next to existing precedence tests). Live timeout/subprocess behavior is exercised by `tests/smoke/test_smoke_homelab_mcp.py` only — mocking `stdio_client` to assert "timeout fires" is high-cost / low-signal vs running the real binary.
- **`shutil.which` resolution (Pitfall 14):** `McpTestClient.__aenter__` resolves `command` via `shutil.which()` before passing to `stdio_client`. If `which` returns `None`, raise a precise `FileNotFoundError("MCP server command not on PATH: <name>")` so a missing binary surfaces with the right diagnostic instead of a cryptic asyncio `NotFoundError`. Windows-relevant; benign on POSIX.
- **No `homelab_mcp` import anywhere in this phase's deliverables:** Phase 1's two-layer guard (ruff TID251 + `tests/conftest.py` `sys.modules` scan) catches violations mechanically. No additional measures needed.

</decisions>

<specifics>
## Specific Ideas

- **"Permanent live smoke under `tests/smoke/` with marker — not throwaway"** was the user's explicit pick over the `scripts/throwaway` and `scripts/keep` options. The roadmap's "throwaway smoke script" wording is overridden by this decision; D-01 supersedes.
- **"Single `mcp_server.timeout_seconds` knob (recommended), uniform ceiling"** was the user's explicit pick over hardcoded constants and three separate fields.
- **30s is a ceiling, not a target.** Real `list_registered_servers` calls return in milliseconds; 30s is the "something is wrong" bound. Update the README in Phase 5 to say so.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner) MUST read these before planning Phase 2.**

### Phase 2 source-of-truth specs
- `docs/mcp_test_framework_mvp_spec.md` §`mcp_client.py` (lines ~119–137) — Public interface for `McpTestClient`. Locked. The only deviation from spec wording is D-08 (additive `timeout_seconds` parameter).
- `docs/mcp_test_framework_mvp_spec.md` §Configuration (lines ~99–115) — `config.yaml` shape. Phase 2 adds `mcp_server.timeout_seconds` to this.
- `docs/mcp_test_framework_mvp_spec.md` §Implementation Notes for Claude Code — restates "use `stdio_client` not `subprocess.Popen`" and "every SDK call wrapped in `asyncio.timeout()`".
- `.planning/REQUIREMENTS.md` §Core Modules CORE-03 — falsifiable acceptance items.
- `.planning/ROADMAP.md` §Phase 2 — Goal statement and the 4 success criteria the verifier will check.

### Project-wide constraints
- `.planning/PROJECT.md` §Constraints, §Key Decisions, §Out of Scope — Black-box principle (no `import homelab_mcp` anywhere — including for type hints), MCP transport stdio-only, async-everywhere with `asyncio.timeout`.
- `.planning/STATE.md` §Accumulated Context — Phase 1 lock-ins still valid: pytest-asyncio strict + session loop scope, `_BareNameNestedEnvSource` in `settings_customise_sources`, `AliasChoices`+`populate_by_name` pattern.
- `CLAUDE.md` §Tooling, §Architecture Notes, §Module Layout — restated invariants.

### Phase 1 prior decisions Phase 2 inherits
- `.planning/phases/01-foundation-pure-data-core/01-CONTEXT.md` — Especially the Config-shape decisions (frozen sub-models, `AliasChoices`+`populate_by_name`, `_BareNameNestedEnvSource` at position 1 of `settings_customise_sources`). `McpServerConfig.timeout_seconds` MUST follow the same pattern.
- `.planning/phases/01-foundation-pure-data-core/01-LEARNINGS.md` — "Lessons" section covers the silent-default-fallback pitfall: Phase 2's new env var `MCP_SERVER_TIMEOUT_SECONDS` must have a precedence test or it can silently fall back to the default with no exception trace.

### Pitfalls research (mandatory pre-implementation read)
- `.planning/research/PITFALLS.md` Pitfalls 1, 4, 5, 12, 14, 15 — anyio cancel-scope (drives `AsyncExitStack` ownership), Windows ProactorEventLoop subprocess cleanup (drives the 5s force-kill belt), undetected stdio termination (drives `asyncio.timeout` on every call), `CallToolResult` shape variance (drives the pass-through decision), Windows path resolution via `shutil.which` (drives the `which()` step in `__aenter__`), KeyboardInterrupt subprocess survival (Phase 5, but the cleanup primitives ship here).

### Stack research
- `.planning/research/STACK.md` — `mcp 1.27.0` SDK, official `stdio_client` + `ClientSession` API patterns. Already locked Phase 1.

### Seeds (informational, not Phase 2 deliverables)
- `.planning/seeds/SEED-001-agentic-tool-use-judge.md` — Trigger is `/gsd-discuss-phase 3`, NOT Phase 2. No action this phase.
- `.planning/seeds/SEED-002-tool-level-parallelism-xdist.md` — `McpTestClient`'s API (`list_tools`, `call_tool(name, ...)`) is naturally list-amenable; nothing in Phase 2 hardcodes single-tool execution. No action this phase, but Phase 4 fixture review should re-check.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mcp_test_framework/models.py` — Add `timeout_seconds: int` field to `McpServerConfig` following the `OllamaConfig.timeout_seconds` pattern verbatim. Frozen + `populate_by_name=True` + `AliasChoices(<env>, <field>)` already enforced by Phase 1 conventions.
- `src/mcp_test_framework/config.py` — `_BareNameNestedEnvSource` (Phase 1 D-08 / 01-LEARNINGS) already routes bare env names to sub-model fields via each field's `validation_alias` choices. The new `MCP_SERVER_TIMEOUT_SECONDS` env var picks this up automatically once the `AliasChoices` is added — no source-code change in `config.py` required, only `models.py`.
- `tests/conftest.py` — `pytest_configure` hook scans `sys.modules` for `homelab_mcp` at session start (Phase 1 01-04). Any accidental import of `homelab_mcp` from `mcp_client.py` fails the run mechanically; Phase 2 needs no additional guard.
- `pyproject.toml` — `[tool.ruff.lint.flake8-tidy-imports.banned-api]` already bans `homelab_mcp` and submodules under `src/` and `tests/`. Phase 2 only edits `pyproject.toml` to add the `live_homelab` marker registration and `addopts = "-m 'not live_homelab'"`.
- `tests/_fixtures/` (Phase 1 01-04) — convention for malformed-Python fixtures (`.py.txt`). Not directly used by Phase 2, but the cross-cutting location is established.

### Established Patterns (from Phase 1)
- Pydantic v2 `BaseModel` with `ConfigDict(frozen=True, populate_by_name=True)` for every cross-cutting model — applies to the new field's owning class.
- Per-field `validation_alias=AliasChoices(<bare env name>, <field name>)` — applies to `McpServerConfig.timeout_seconds`.
- Domain-local exceptions live in their owning module (`ToolNotFoundError` in `mcp_client.py`, paralleling `ValidationIssue` in `schema_validator.py`).
- All public APIs that touch I/O are async — `McpTestClient.list_tools/get_tool/call_tool` already follow this.
- Spec-verbatim bare env var names (no `MCPTF_` prefix) — `MCP_SERVER_TIMEOUT_SECONDS`, not `MCPTF_MCP_SERVER_TIMEOUT_SECONDS`.
- Custom env source means new env vars MUST get a precedence test or they silently default-fallback (01-LEARNINGS lesson).

### Integration Points
- `McpTestClient` is consumed by Phase 4 fixture FIX-01 (`mcp_client` session-scoped). Phase 2 ships the constructor that takes `(command, args, timeout_seconds)` — Phase 4 wires it as `McpTestClient(cfg.mcp_server.command, cfg.mcp_server.args, cfg.mcp_server.timeout_seconds)`.
- `ToolNotFoundError` raised by `McpTestClient.get_tool()` is caught by Phase 4's `target_tool` fixture (FIX-03), which fails the run early with the candidate-tool list.
- The `live_homelab` marker convention extends naturally to Phase 4 — every test in `tests/test_homelab_list_registered_servers.py` that hits live `homelab-mcp` (i.e., all 10) gets the same marker, with the same `addopts` skip behavior. Phase 4's CONTEXT will reaffirm this.
- The `mcp_test_framework.mcp_client.stderr` logger name is the agreed Phase 2 contract; Phase 5 README's troubleshooting section can document `--log-cli-level=WARNING` to see live MCP server stderr.

</code_context>

<deferred>
## Deferred Ideas

- **Per-call timeout knobs (init / list / call separately)** — Single `mcp_server.timeout_seconds` is the v1.0 shape (D-05). Reconsider if a real tool needs different ceilings — e.g., a long-running `call_tool` and a snappy `list_tools` where a single ceiling forces a bad trade-off.
- **Smoke script as throwaway `scripts/` entry** — Rejected per D-01. The live smoke pack is reusable beyond Phase 2. If a future "diagnostic / debugging" phase wants a hand-runnable raw script, it can re-add `scripts/` later without conflicting with the pytest-based smoke test.
- **`MCPTF_LIVE` env var gating** — Marker-only via `addopts` is the chosen v1.0 shape (D-03). Add an `MCPTF_LIVE=1` alternative in a future phase only if users complain about `-m 'not live_homelab'` ergonomics. Implementation would be a `pytest_collection_modifyitems` hook that auto-overrides the marker.
- **Custom CallToolResult validator wrapping** — Phase 2 returns SDK's `CallToolResult` unchanged. If Phase 4 reveals shape-handling cruft duplicated across tests (`if result.isError or not (result.content or result.structuredContent): ...`), factor a helper into `mcp_client.py` (e.g., `assert_successful(result: CallToolResult) -> None`) at that point — not before.
- **`McpTestClient(config: McpServerConfig)` constructor variant** — Spec interface is `(command, args)`; D-08 keeps it positional with the additive `timeout_seconds`. If Phase 4 reveals friction passing the three positional args from the fixture, add a classmethod `from_config(cfg: McpServerConfig) -> McpTestClient` rather than changing the existing signature.

</deferred>

---

*Phase: 02-mcp-client-wrapper*
*Context gathered: 2026-05-04*
