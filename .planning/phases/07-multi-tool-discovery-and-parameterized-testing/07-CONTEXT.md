# Phase 07: Multi-tool discovery & parameterized testing - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Generalize the v1.0 single-tool test loop to N-tools-per-run. The framework discovers tools from the live MCP server at session/collection time and parametrizes the existing 10 test cases (TEST-01..TEST-10) over the discovered tool list via `pytest.mark.parametrize` (no codegen). Per-tool failures attribute via test IDs `test_<name>[<tool_name>]` — both pytest terminal output and Phase 09 JUnit XML.

**In scope (per ROADMAP.md and REQUIREMENTS.md):** MULTI-01..MULTI-04.

**Explicitly NOT in scope:**
- Per-tool config registry (skip-list, `call_arguments`, judge subset) — Phase 08 (TOOLCFG-01..07).
- JUnit XML emission / `--junit-xml` flag — Phase 09 (OUTPUT-01..03). MULTI-03 specifies the *ID format* only; emission lives in Phase 09.
- Process-parallel execution / xdist — v1.2 (SEED-002).
- Warm-up stage / cold-start amortization — v1.2.
- Starter-config generator (`config-init` / `discover --emit-config`) — deferred to Phase 08 once TOOLCFG-01 schema is locked. Phase 07 relies on the existing v1.0 `mcp-test-framework list-tools` CLI as the inventory / verify affordance.

</domain>

<decisions>
## Implementation Decisions

### Default behavior when `target.tool_name` is unset

- **D-01:** When `target.tool_name` is unset (or empty/None), the framework **discovers and tests every tool the server advertises**. This is the new default; matches MULTI-04's intent. Existing v1.0 users with `TARGET_TOOL_NAME` set in `.env` / `config.yaml` keep their single-tool behavior unchanged — backward compat is preserved by the existence of the config field, not by the default value.
- **D-02:** The `Config.target.tool_name` field type changes from `str` to `str | None`. Default flips from `"list_registered_servers"` to `None`. `AliasChoices("TARGET_TOOL_NAME", "tool_name")` stays unchanged. Empty string is treated equivalently to None at parametrize time.

### Verify-before-running affordance

- **D-03:** The v1.0 `mcp-test-framework list-tools` CLI command is the verify step — user runs it to inspect the tool inventory before running. **No new CLI code in Phase 07.**
- **D-04:** A starter-config generator (e.g., `config-init` subcommand that emits a `tools:` YAML block ready for the user to delete entries / set `skip: true`) is **deferred to Phase 08** so it lands on top of TOOLCFG-01's locked schema rather than committing Phase 07 to a per-tool config shape ahead of its scoping phase. Captured under "Deferred Ideas" below.

### Test ID convention

- **D-05:** Test IDs **always** render as `<test_name>[<tool_name>]`, including when `target.tool_name` is set explicitly (single-item parametrize list). This is one code path, uniform IDs across pytest terminal output and Phase 09 JUnit XML, easier CI-dashboard filtering. Cost: v1.0's bare test IDs (e.g., `test_schema_passes_structural_checks`) become bracketed (`test_schema_passes_structural_checks[list_keyring_credentials]`) — acceptable since v1.0 is shipped and v1.1 explicitly generalizes the surface.

### Behavior for tools with non-empty `inputSchema.required`

- **D-06:** TEST-08, TEST-09, TEST-10 continue to call `call_tool` with `{}` (the v1.0 contract). Tools whose `inputSchema.required` is non-empty will produce `isError=True` and **fail TEST-08 visibly** for that tool. The failure IS the signal — Phase 08 (TOOLCFG-01's `call_arguments`) is the user-facing fix. Phase 07 ships **no auto-skip logic** for required-args tools — that overlaps with Phase 08's skip mechanism (TOOLCFG-07) and would paper over the failure that Phase 08 then resolves.
- **D-07:** Same fail-visibly stance applies to TEST-10 (`test_text_content_parses_as_json`) for tools whose successful output is non-JSON prose: TEST-10 fails for that tool; user reads the failure and decides whether to skip via Phase 08 or accept the signal.

### Runtime envelope / blast radius

- **D-08:** v1.1 **accepts the slow runtime** of running 10 tests × N tools × 3 LLM-judge calls. No default cap, no warning, no `target.allow_all_tools` opt-in flag. Rationale: a cap is a de-facto skip mechanism, which is Phase 08's territory (TOOLCFG-01 / TOOLCFG-07). Adding it in Phase 07 inverts phase ordering. Process-parallel execution (xdist) and warm-up are explicit v1.2 work per PROJECT.md. The "per-worker isolation (v1.1) is a hard prerequisite for parallelism (v1.2)" sequencing already holds.
- **D-09:** Expected-runtime documentation is owned by Phase 10 (DOC-04 / DOC-05) — README's "Per-tool configuration" + "Isolation guarantee" sections add a sentence on multi-tool runtime expectations. Not Phase 07's surface.

### Discovery seam (technical — locked here so research/planner aligns)

- **D-10:** Tool discovery happens at **collection time** via a sync `pytest_generate_tests` (or equivalent collection-hook) that runs `asyncio.run(...)` on a brief MCP session — mirroring the existing `_preflight` pattern at [fixtures.py:142-154](src/mcp_test_framework/fixtures.py:142). The brief session must use a per-discovery `tempfile.TemporaryDirectory` + `_build_isolated_env` so it cannot leak state to `~/.homelab_mcp/` (Phase 06 ISOL-03 invariant must hold for the new spawn site).
- **D-11:** The brief discovery session is a **new spawn site** (third one, after `fixtures.py`'s `_owner_task` and `mcp_client.py`'s `__aenter__`). It MUST inject `_build_isolated_env(<discovery tempdir>)` into `StdioServerParameters(env=...)` per the Phase 06 isolation contract. Researcher / planner: budget for ISOL-03's hash-equality test to **also exercise this new spawn path** (or document why the existing `_preflight` spawn already covers it).
- **D-12:** Discovery result is cached so the long-lived `mcp_client` session-fixture does NOT double-spawn for re-discovery. Cache lives module-level (or via `pytest.StashKey`); session-fixture reads the same list of tool names and resolves each via `mcp_client.get_tool(name)`.

### Test-signature shape (technical — locked here so plans line up)

- **D-13:** **Indirect parametrize** via the `target_tool` fixture. The fixture body takes `request.param` (a tool-name string) and returns `await mcp_client.get_tool(request.param)`. Test bodies (TEST-01..TEST-10) keep their `target_tool` parameter unchanged — diff size is minimized to the fixture + test-module-level parametrize markers. Tests do NOT shift to taking a raw `tool_name: str` parameter.
- **D-14:** Test-module-level parametrize: each `pytestmark` list at the top of `tests/test_homelab_list_registered_servers.py` (the renamed/repurposed module) gains a `pytest.mark.parametrize("target_tool", <discovered tool names>, indirect=True, ids=<tool-name list>)` marker. Researcher / planner picks the cleanest place to express the parametrize: module-level `pytestmark` if it applies uniformly to all 10 tests; per-test decoration if any test needs to opt out. Default: module-level uniform.

### `_preflight` adjustment

- **D-15:** When `target.tool_name` is unset (None), `_preflight` drops the "target tool membership" assertion at [fixtures.py:156-162](src/mcp_test_framework/fixtures.py:156). The MCP handshake check + Ollama checks remain unchanged. When `target.tool_name` is set, the membership check stays in place.
- **D-16:** `_preflight`'s `list_tools()` result and the discovery hook's `list_tools()` result should agree (same server, same handshake protocol). It is acceptable for both to call `list_tools()` independently — they run in different brief sessions and the cost is one extra subprocess spawn per session. Optimization (sharing the result via stash) is **Claude's discretion** — see CD section.

### Test-module shape

- **D-17:** The existing test module `tests/test_homelab_list_registered_servers.py` is **renamed** to a tool-agnostic name (e.g. `tests/test_mcp_tool_contract.py`). The "homelab" / "list_registered_servers" specificity in the filename was a v1.0 single-target artifact and contradicts the multi-tool surface. Rename happens in this phase; Phase 10 docs reference the new name.

### Claude's Discretion

- **CD-01:** Whether the discovery hook caches via a module-level dict, `pytest.StashKey`, or `pytest.Config.cache`. Pick whichever keeps the collection-time code readable and survives re-collection cleanly.
- **CD-02:** Whether to share `list_tools()` between `_preflight` and the discovery hook (e.g., preflight populates the cache; hook reads it). The savings are one subprocess spawn per session; not a v1.1 perf concern. Pick simpler.
- **CD-03:** Where exactly to place the `pytest.mark.parametrize` invocation — module-level `pytestmark` augment, a per-test decorator stack, or a `pytest_generate_tests` hook in `conftest.py`. Hook approach gives the most flexibility (tool list known at collection time, no import-time eager spawn). Decision: planner picks the seam that keeps the collection-time spawn under one place.
- **CD-04:** New module name for the renamed test file. `test_mcp_tool_contract.py` is suggested but not locked.
- **CD-05:** Whether the discovery hook needs to handle `target.tool_name` being set: if set, it can short-circuit and emit a single-item parametrize list `[target.tool_name]` without spawning at collection time (since `_preflight` already validates membership). Tradeoff: less code if the hook always spawns; less collection-time work if the hook short-circuits. Planner's call.
- **CD-06:** Order of plans within the phase: discovery seam (parametrize wiring) and `target_tool` fixture rewrite must land together to avoid a transient broken state. Planner picks the exact plan-cut.

### Folded Todos

None — no pending todos matched Phase 07's scope at discussion time. (The v1.1 isolation todo was folded into Phase 06.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 07 row + "Phase 07: Multi-tool discovery & parameterized testing" details (goal, depends-on Phase 06, requirements, 4 success criteria)
- `.planning/REQUIREMENTS.md` §"MULTI — Multi-tool discovery and parameterized testing" — MULTI-01..MULTI-04 acceptance criteria and traceability table
- `.planning/PROJECT.md` §"Current Milestone: v1.1" — anti-scope (xdist, warm-up, OpenAI-compat are v1.2; rubrics-as-data is v1.3); §"Performance constraints" — per-worker isolation prerequisite for v1.2 parallelism

### Predecessor phase (must read before touching spawn paths)
- `.planning/phases/06-per-session-host-state-isolation/06-CONTEXT.md` — D-12..D-17 (`_isolated_home` fixture, env injection at every spawn site, single source of truth)
- `.planning/phases/06-per-session-host-state-isolation/06-VERIFICATION.md` — ISOL-03 hash-equality test as the regression guard the new discovery spawn must not break
- `src/mcp_test_framework/_isolation.py` — `_build_isolated_env(home: Path) -> dict[str, str]`. Any new spawn site MUST call this; the env-allowlist constant lives here.

### Project rules (unchanged from v1.0; binding for this phase)
- `CLAUDE.md` §"Architecture Notes" — MCP transport is stdio only via `stdio_client`; framework treats homelab-mcp as a black box (no source reading; ruff TID251 + sys.modules guard); session-scoped fixtures; `asyncio.timeout` around subprocess/HTTP
- `tests/conftest.py` — `pytest_plugins = ["mcp_test_framework.fixtures"]` registration + the `pytest_configure` sys.modules black-box guard. Discovery hook lands here or in fixtures.py.
- `docs/mcp_test_framework_mvp_spec.md` — authoritative MVP design doc (test categories, judge contract, schema-validator contract — unchanged for v1.1)

### Implementation seams (existing code to modify)
- `src/mcp_test_framework/fixtures.py` — `_preflight` at line 86 (membership check at 156-162 conditional on `target.tool_name`); `mcp_client` session-fixture at line 213; `target_tool` fixture at line 331 (becomes indirect-parametrize aware); discovery hook may live here or in conftest.py
- `src/mcp_test_framework/models.py` — `TargetConfig.tool_name` at line 70 (type `str` → `str | None`; default → `None`)
- `src/mcp_test_framework/mcp_client.py` — `McpTestClient.__aenter__` standalone-spawn path; brief discovery session may reuse this entry point (with explicit per-call tempdir + `_build_isolated_env`) rather than open-coding a new `stdio_client` block
- `tests/test_homelab_list_registered_servers.py` — entire module: rename + parametrize markers + `target_tool` fixture-driven indirection
- `tests/conftest.py` — `pytest_generate_tests` collection hook (CD-01 / CD-03) may land here

### Phase 04.1 lifecycle invariant (do NOT regress)
- `.planning/phases/04.1-*` — Phase 04.1 owner-task + anyio.Event fixture rewrite. The `_owner_task` body MUST preserve the "no anyio cancel scope across the yield" invariant. The discovery hook is `asyncio.run(...)` from a sync collection hook — it runs and tears down its own loop fully *before* the long-lived `mcp_client` fixture's owner-task starts, so it does not interact with that invariant. Verify this in research before writing the plan.

### v1.0 architecture context
- `.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md` — host-state surface inventory (still relevant for any new spawn path)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_preflight` brief-session pattern** ([fixtures.py:142-154](src/mcp_test_framework/fixtures.py:142)) — a brief `McpTestClient` context manager + `list_tools()` call. The discovery hook is a near-clone — same shape, same env-isolation contract, but called from a sync collection hook via `asyncio.run` rather than from an async session fixture.
- **`McpTestClient.__aenter__`** ([mcp_client.py:135](src/mcp_test_framework/mcp_client.py:135)) — already isolation-aware as of Phase 06 (D-16). Discovery may reuse this entry point unchanged; only the caller's tempdir lifecycle is new.
- **`_build_isolated_env`** ([_isolation.py](src/mcp_test_framework/_isolation.py)) — the single source of truth for env injection. Discovery spawn MUST call this with its own discovery tempdir.
- **`target_tool` fixture** ([fixtures.py:330-338](src/mcp_test_framework/fixtures.py:330)) — currently resolves `config.target.tool_name` directly. Becomes indirect-parametrize-aware: takes `request.param` (the parametrized tool name) and resolves via `mcp_client.get_tool(...)`. Unchanged for tests that depend on it — diff is internal.
- **`pytestmark` pattern** ([test_homelab_list_registered_servers.py:43](tests/test_homelab_list_registered_servers.py:43)) — module-level `[pytest.mark.asyncio(loop_scope="session")]` is the seam where parametrize markers join.

### Established Patterns
- **Black-box rule** mechanically enforced via `ruff TID251` + `sys.modules` guard ([conftest.py:32-42](tests/conftest.py:32)). Discovery hook code MUST NOT import any `homelab_mcp` symbol; tools are read by name from `list_tools()` only.
- **Session-scoped async fixtures with explicit `loop_scope="session"`** matches `asyncio_default_fixture_loop_scope = "session"` in `pyproject.toml`. The discovery hook's `asyncio.run(...)` runs a separate, short-lived loop — it must complete + tear down before any session-scoped fixture's loop starts.
- **`StdioServerParameters(env=...)` is the single env-injection seam** for the spawned MCP subprocess. Three spawn sites now: `_preflight`, `mcp_client._owner_task`, and the new discovery-hook spawn — every one must build params via `_build_isolated_env`.
- **No anyio cancel scope across the yield** ([fixtures.py:179-205](src/mcp_test_framework/fixtures.py:179) docstring + Phase 04.1 history). Discovery hook does not interact with this — it owns its own loop and tears down completely before the fixture loop starts.

### Integration Points
- **Discovery hook** — new code in `tests/conftest.py` or `src/mcp_test_framework/fixtures.py`. Sync function (`pytest_generate_tests` or `pytest_collection_modifyitems`) that calls `asyncio.run(_discover_tools(config))` and stashes the tool-name list for `target_tool`'s indirect parametrize.
- **`Config.target.tool_name = None` semantics** — `_preflight` membership-check branch drops; discovery-hook short-circuit branch (CD-05) may emit a single-item parametrize list when set; `target_tool` fixture's `request.param` is the source of truth at test-collection time.
- **Test module rename** — `tests/test_homelab_list_registered_servers.py` → `tests/test_mcp_tool_contract.py` (or planner's equivalent name). All 10 test bodies stay; only the parametrize plumbing is new.

</code_context>

<specifics>
## Specific Ideas

- **`list-tools` CLI is the verify step.** When a user wants to know what will run, they invoke `mcp-test-framework list-tools`; the output is the parametrize input. No new flag, no new subcommand in Phase 07.
- **Discovery cache is per-collection.** If pytest is run twice (e.g. `--collect-only` then a real run in the same shell), each invocation does its own discovery — no cross-process cache. Mirrors v1.0 `_preflight` re-runs.
- **Test ID rendering.** Use the bare tool name as the parametrize id (e.g. `test_schema_passes_structural_checks[list_keyring_credentials]`) — not a slugified or numbered form. Pytest accepts arbitrary strings as ids; tool names are already shell- and JUnit-XML-safe.
- **Fail-visibly applies to TEST-08 specifically.** TEST-09 (content/structuredContent presence) and TEST-10 (JSON parse) cascade naturally from TEST-08's failure mode — if call_tool returns isError=True, content may still exist as an error-message TextContent block, so TEST-09 may pass while TEST-08 fails. That's expected and informative; no special handling.

</specifics>

<deferred>
## Deferred Ideas

- **Starter-config generator** (e.g. `mcp-test-framework config-init` that emits a `tools:` YAML block with one entry per discovered tool, ready for the user to delete or `skip: true`) — **Phase 08 territory**. Lands on top of TOOLCFG-01's locked schema. Trigger: as soon as TOOLCFG-01 is in scope.
- **Up-front runtime estimate at collection time** — printing "Discovered N tools → ~M minutes estimated" to terminal at session start. Considered, not shipped in Phase 07 (D-08). Trigger: post-v1.2 if user feedback says discovery surprises are common; or fold into the docs Phase (DOC-04 prose).
- **Soft cap on tool count** with explicit `target.allow_all_tools=true` opt-in — considered, not shipped in Phase 07 (D-08). Adds a config field that overlaps Phase 08. Trigger: explicit user incident where a runaway run blocks CI.
- **Auto-skip output-conformance tests when `inputSchema.required` is non-empty** — considered, not shipped (D-06). Phase 08 skip-list is the user-facing path. Trigger: if real homelab-mcp run reveals so many failures that Phase 08 transition is impractical, revisit as a v1.1.x patch.
- **Process-parallel execution (xdist)** — explicit v1.2 (SEED-002). Per-worker isolation (Phase 06) is the prerequisite already on the books.
- **Warm-up / cold-start amortization** — explicit v1.2 work; co-shipped with xdist.
- **Sharing `list_tools()` between `_preflight` and the discovery hook** — Claude's discretion (CD-02). Single optimization point if the double-spawn is observable.

### Reviewed Todos (not folded)

None — no pending todos matched Phase 07's scope. (The v1.1 isolation todo was folded into Phase 06.)

</deferred>

---

*Phase: 07-multi-tool-discovery-and-parameterized-testing*
*Context gathered: 2026-05-07*
