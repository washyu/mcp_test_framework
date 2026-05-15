# Phase 18: SDET test surface + typed errors - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn the Phase 17 codegen seam into a runnable SDET surface. Three deliverables:

1. **`mcp_session` + `tool(name)` runtime fixtures** — exported from `mcp_test_framework.sdet`, importable from any SDET test file. `mcp_session` is the live MCP `ClientSession` driver; `tool(name)` returns a `ToolWrapper` whose `.call(params)` actually performs the wire call (closing the Phase 17 `NotImplementedError` seam at `_tool_factory.py:70-82`).
2. **`--sdet` flag on `run`** — opts the `tests/sdet/` discovery scope into the pytest invocation; composes with `-q`, `--explain`, `--debug`, `--raw`, `--with-framework`. Default `mcp-test-framework run` collects only `tests/contract/` (no behavior change).
3. **`ToolCallError` typed exception (UI-02)** — raised when `result.isError = True`; carries `.tool`, `.code`, `.message`, `.raw` fields; surfaces `.code` / `.message` into Phase 16's em-dash FAIL render (`✗ {tag} — [{code}] {message}`); dumps `.raw` into the `--debug` appendix.

**In scope:** SDET-01..04, UI-02 (5 requirements). The `mcp_session` fixture wiring, the `tool(name)` runtime body, the `--sdet` CLI flag + collection contract, scenario-aware pre-run digest rendering, `ToolCallError` definition + extraction policy + renderer hook-up.

**Out of scope (deliberate):**
- Stateful yield-fixture cleanup contract + dogfood VM-lifecycle scenario — Phase 19 (STATE-01..04, UI-01).
- `requires_homelab(...)` preflight + reachability checks — Phase 20.
- Authoring docs (`docs/SDET-AUTHORING.md`) + README parity — Phase 21.
- Attribute-access `Tool.create_vm.call(...)` ergonomic — Phase 17 D-09 locked stringly-typed only; v1.4 candidate.
- Multi-server SDET runs — anti-vision per PROJECT.md.
- Per-judge breakdown under `--debug` — Phase 16 D-11, deferred to v1.5.

**Hard dependencies (LOCKED — implement against):**
- Phase 17 CODEGEN-04 (`ToolResponse` base at `src/mcp_test_framework/sdet/response.py`) — `ToolWrapper.call()` constructs `self.response_cls(raw=result)` against this base.
- Phase 17 CODEGEN-05 seam at `src/mcp_test_framework/sdet/_tool_factory.py:36-115` — `_REGISTRIES`, `_ACTIVE_SLUG`, `ToolWrapper` class. Phase 18 fills `ToolWrapper.call()` body and writes the activation logic. The slot contract is locked here.
- Phase 17 CODEGEN-01..06 generated registry — every generated `__init__.py` exports `_REGISTRY: dict[str, tuple[type[BaseModel], type[ToolResponse]]]` keyed by tool name.
- Phase 04.1 cancel-scope invariant (`fixtures.py:324-410`) — no anyio CancelScope across the `yield` boundary; the existing `mcp_client` fixture's anyio-owner-task plumbing is the locked pattern. D-01 reuses it verbatim.
- Phase 13 SAFE-01..07 config precedence (`--config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud`). `--sdet` runs honor the same chain via the existing `_load_config(path)` helper.
- Phase 15 test-surface split — `tests/sdet/` joins `tests/contract/` and `tests/framework/` as a third scope; same opt-in pattern as `--with-framework`.
- Phase 16 renderer surface — `_render_per_tool_rows`, `_render_pre_run_digest`, `--explain` expansion, em-dash separator (U+2014). Phase 18 extends the XML parser to recognize `ToolCallError`-attached JUnit properties; it does NOT reshape the row vocabulary.
- Black-box rule — SDET tests import generated classes only; never reach into `homelab-mcp` source. The codegen-emitted classes ARE the wire contract.

</domain>

<decisions>
## Implementation Decisions

### Fixture surface

- **D-01: `mcp_session` is an alias / re-export of the existing session-scoped `mcp_client` fixture.** Re-exported from `src/mcp_test_framework/sdet/__init__.py` as `mcp_session` (with `__all__` updated). No duplicate `stdio_client` / `ClientSession` lifecycle is introduced. The Phase 04.1 cancel-scope-invariant anyio-owner-task plumbing at `fixtures.py:324-410` is preserved verbatim. One MCP connection serves both contract and SDET tests when both surfaces run in the same invocation (note: under D-04 they don't run in the same invocation, but `--with-framework` mixes SDET with framework self-tests that may also need it).

- **D-02: Registry activation lives inside the `mcp_session` fixture body.** The fixture wrapping `mcp_client` activation flow:
  1. Yields after the existing `mcp_client` fixture has constructed the live `ClientSession`.
  2. Reads `serverInfo.name` from the cached initialize result (or re-derives it from the live session — implementation detail).
  3. Slugifies via the Phase 17 `_slugs.py` helper (single source of truth for slug rules).
  4. `importlib.import_module(f"mcp_test_framework.sdet.generated.{slug}")`.
  5. Reads `_REGISTRY` from the module; sets `_REGISTRIES[slug] = _REGISTRY`, saves prior `_ACTIVE_SLUG`, sets `_ACTIVE_SLUG = slug`.
  6. Yields the live session.
  7. On teardown, restores prior `_ACTIVE_SLUG` and pops the registry entry. This is the only place that ever mutates `_ACTIVE_SLUG` in test code — module-level-state warning at `_tool_factory.py:25-26` is honored.

- **D-03: Missing generated module = fail loud at session start.** If `importlib.import_module(...)` raises `ModuleNotFoundError` during D-02 step 4, the fixture calls `pytest.exit` via the operator-tone helper at `fixtures.py:57-81` (`_pytest_exit_operator_tone`). Shape:
  ```
  Summary: No generated SDET classes found for server '<slug>' (from serverInfo.name='<actual_name>').
  Detail:
    The fixture tried to `import mcp_test_framework.sdet.generated.<slug>` and the module does not exist.
    This usually means `gen-sdet-classes` has not been run for this server, or the server's name changed.
  next: run `mcp-test-framework gen-sdet-classes` against this server first, then re-run with --sdet
  ```
  Mirrors Phase 13 SAFE-03 fail-loud semantics. `returncode=2` so CI can distinguish from test failures.

### `--sdet` CLI semantics

- **D-04: `--sdet` collects only `tests/sdet/` (SDET-only, not additive).** The flag SWAPS the operator-surface scope from `tests/contract/` to `tests/sdet/`. Operators wanting both run twice (or a CI orchestrator runs each). Rationale: matches the SDET-persona mental model ("I want to run my scenarios"); avoids interleaving two domains in one summary line; renderer doesn't have to bucket tools-with-contract-rubric-results alongside scenario-modules-with-per-step-results.

- **D-05: `--sdet --with-framework` = `tests/sdet/ + tests/framework/`.** Composition rule: `--sdet` chooses the operator-surface scope (contract vs sdet); `--with-framework` always adds `tests/framework/` on top. So:
  - (default) → `tests/contract/`
  - `--with-framework` → `tests/contract/ + tests/framework/`
  - `--sdet` → `tests/sdet/`
  - `--sdet --with-framework` → `tests/sdet/ + tests/framework/`
  Each flag's responsibility stays independent; the help text documents the four combinations explicitly.

- **D-06: Pre-run digest under `--sdet` is scenario-aware.** Reuse the Phase 16 `Running (N) / Skipping (M)` bucketing pattern from `_render_pre_run_digest`, but keyed on scenario MODULE names (e.g. `proxmox_vm_lifecycle`) instead of tool names. `--explain` expansion stays identical (one line per skipped scenario, sorted alphabetically, em-dash + reason). Implementation: a new builder analogous to `_compose_pre_run_skip_reasons` consumes pytest collection output instead of the discovery + tool-config state. Probably its own function (`_compose_scenario_digest`) rather than overloading the existing one — scenario state and tool state differ enough that one function carrying both becomes a switch-statement.

### `ToolCallError` extraction policy

- **D-07: `ToolCallError` is a plain `Exception` subclass.**
  ```python
  class ToolCallError(Exception):
      def __init__(
          self,
          *,
          tool: str,
          code: str | None,
          message: str,
          raw: CallToolResult,
      ) -> None:
          self.tool = tool
          self.code = code
          self.message = message
          self.raw = raw
          super().__init__(self._format_default())

      def _format_default(self) -> str:
          if self.code:
              return f"[{self.code}] {self.message}"
          return self.message
  ```
  Re-exported from `mcp_test_framework.sdet`. Plain Exception (not Pydantic BaseModel) because: (a) standard Python idiom for typed exceptions; (b) integrates with pytest's traceback machinery without surprises; (c) downstream `except ToolCallError as e:` works the way SDETs expect; (d) keeps the runtime overhead near zero. `.raw` is a `mcp.types.CallToolResult` (the live MCP type), not a Pydantic clone.

- **D-08: Field extraction follows a heuristic chain.** Inside `ToolWrapper.call`, when `result.isError = True`, populate the error:
  1. If `raw.structuredContent` is a dict, look for `code` and `message` string keys. Use what's present.
  2. Else, if `raw.content` is non-empty, attempt `json.loads(first_text_content.text)`; if it's a dict, look for `code` and `message` string keys. Use what's present.
  3. Else (or if any of the above fail or yield no keys), `.message = concatenated TextContent.text`, `.code = None`.

  **Strict key set.** Only `code` and `message` are recognized. No synonyms (`error`, `detail`, `reason`, `errorCode`). No recursive walk. Non-string values for `code` are coerced via `str(...)` (so a server returning `code: 404` becomes `"404"`); non-string `message` falls through to step 3.

- **D-09: `code` / `message` reach the renderer via `pytest_exception_interact`.** Live in `tests/sdet/conftest.py`. The hook:
  ```python
  def pytest_exception_interact(node, call, report):
      exc = call.excinfo.value if call.excinfo else None
      if isinstance(exc, ToolCallError):
          report.user_properties.append(("mcptf_error_code", exc.code or ""))
          report.user_properties.append(("mcptf_error_message", exc.message))
  ```
  pytest's JUnit XML writer surfaces `report.user_properties` as `<property name="..." value="..."/>` inside the `<testcase>` block. The Phase 16 XML parser at `_runner.py` learns to read these property names when present; if present, build the FAIL row's `failure_message` from `[code] message`; if absent, fall through to the existing `failure_message` extraction (the `<failure message="...">` attr that contract tests use today). Clean seam, no string-parsing brittleness, no impact on contract surface.

### Renderer surface (UI-02)

- **D-10: FAIL row format is `[code] message` (code in brackets first).** Renderer composes `failure_message = f"[{code}] {message}"` when `code` is non-empty, else just `message`. Renders as `  ✗ {scenario_tag} — [VM_NAME_TAKEN] name already in use`. Code-first lets operators scan a column of error codes when many scenarios fail; truncation at terminal width per existing Phase 14 row-width behavior. Falls back gracefully to `  ✗ {scenario_tag} — name already in use` when `.code` is `None`.

- **D-11: `--debug` appendix carries a structured per-failure block ABOVE pytest's raw output.** For each `ToolCallError` failure (detected via the same `user_properties` mechanism from D-09 OR a fresh parse of the JUnit XML), emit:
  ```
  --- ToolCallError dump ---
  tool: <name>
  code: <code or "(none)">
  message: <message>
  raw:
    <CallToolResult.model_dump_json(indent=2)>
  ---
  ```
  Block emits BEFORE pytest's raw stdout so operators get a parseable summary they can grep first; pytest's full traceback (and any other captured output) follows below.

### Claude's Discretion

The planner / researcher has authority on these — they were not surfaced in this discussion because they're implementation mechanics, not user-visible decisions:

- **`mcp_session` exposure shape.** Probably re-export `mcp_client` as-is (it's already a typed `McpTestClient`); a thin wrapper would only add value if SDET needs methods `McpTestClient` doesn't have. Default: bare re-export with a docstring noting the alias relationship.
- **`tool().call()` body — exact `model_dump` mode.** `params.model_dump(mode="python")` vs `mode="json"`. `mode="python"` keeps `datetime` and other rich types; `mode="json"` is the wire-safe shape. Default: `mode="json"` because MCP wire format expects JSON-serializable dicts. Pin a test against a Params class with a non-trivial field type.
- **JUnit property name keys.** Suggest `mcptf_error_code` / `mcptf_error_message` (project-scoped prefix, snake_case). Locked in plan.
- **Where the scenario-aware digest builder lives.** Probably a new function in `_runner.py` near `_compose_pre_run_skip_reasons` so the pre-run-digest call site can dispatch `if --sdet → scenario_builder else tool_builder`. Concrete shape is planner's call.
- **Sample SDET test shipped in this phase.** A small synthetic-server-backed sanity test in `tests/sdet/test_basic_call.py` so Phase 18 can be verified WITHOUT requiring live homelab-mcp. Phase 19 ships the real VM-lifecycle dogfood. Recommendation: yes, ship a minimum-viable `tests/sdet/test_basic_call.py` that exercises one tool through the wrapper end-to-end against the existing synthetic fixture server from Phase 17.
- **`--sdet --raw` composition.** `--raw` bypasses the domain UI per Phase 16; `--sdet` still controls the discovery scope. Probably: `--raw --sdet` runs pytest against `tests/sdet/` with no domain UI wrapping. Pin a test.
- **`--sdet` + `-q` digest.** `-q` suppresses the pre-run digest per Phase 16 D-08; the same gate applies under `--sdet`. No special case.
- **Preflight under `--sdet`.** The existing `_preflight` autouse fixture at `fixtures.py:128-280` does Ollama + MCP-handshake + tool-membership checks. SDET runs need MCP-handshake (yes, for `mcp_session`) but NOT Ollama (no judges run in SDET scope) NOT tool-membership (target_tool is contract-only). Planner decides whether to gate `_preflight` on `--sdet` mode or split it (probably split: a leaner `_sdet_preflight` that does MCP + the D-03 generated-module check).
- **Whether `tool(name)` accepts an `Awaitable` for params.** No — keep it sync `tool(name).call(params)` with `params: BaseModel`. Async-only on the `.call()` boundary (it's awaited inside an `@pytest.mark.asyncio` test).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements

- `.planning/REQUIREMENTS.md` §SDET-01..04 (lines 19–24) + §UI-02 (line 58) — the 5 locked requirements
- `.planning/ROADMAP.md` Phase 18 row (lines 53, 77–87) — goal, depends-on, 4 success criteria
- `.planning/PROJECT.md` — milestone v1.3 framing (Homelab Scenario Testing; operator + SDET dual persona)
- `.planning/STATE.md` — current position (Phase 17 complete 2026-05-13)

### Phase 17 carry-forward (the seam Phase 18 closes)

- `.planning/phases/17-schema-driven-codegen-surface/17-CONTEXT.md` — Phase 17 decisions, especially D-07 (`ToolResponse` shape) and D-09 (stringly-typed `tool("name").call(params)`)
- `src/mcp_test_framework/sdet/_tool_factory.py:36-115` — `ToolWrapper` Generic class, `tool(name)` factory, `_REGISTRIES`/`_ACTIVE_SLUG` slots; `.call()` body raises `NotImplementedError` with explicit Phase-18 reference (this is what Phase 18 fills)
- `src/mcp_test_framework/sdet/response.py` — `ToolResponse` base class; the `.raw` / `.data` / `.text` / `.is_error` accessors
- `src/mcp_test_framework/sdet/__init__.py` — current public re-exports (`ToolResponse` only); Phase 18 adds `mcp_session`, `tool`, `ToolCallError`
- `src/mcp_test_framework/sdet/_slugs.py` — slugify helper (single source of truth for serverInfo.name → slug rule); used by D-02 registry activation
- `src/mcp_test_framework/sdet/generated/homelab_mcp/__init__.py` — example of the `_REGISTRY` dict shape Phase 17 emits; Phase 18's fixture reads from this attribute

### Existing fixtures + cancel-scope invariant (LOCKED — do not modify)

- `src/mcp_test_framework/fixtures.py:57-81` — `_pytest_exit_operator_tone` helper (D-03 fail-loud uses this)
- `src/mcp_test_framework/fixtures.py:128-280` — `_preflight` autouse fixture; SDET inherits the same gates (with Claude's-discretion modifications for the SDET-only path)
- `src/mcp_test_framework/fixtures.py:324-410` — `mcp_client` session fixture; D-01 re-exports this as `mcp_session` (no duplication of anyio-owner-task plumbing)
- `src/mcp_test_framework/fixtures.py:89-100` — `config` fixture; transitively flows into `mcp_session`
- `.planning/phases/04.1-mcptestclient-session-teardown-fix/` — the cancel-scope invariant origin

### Phase 13 / 15 / 16 contracts preserved

- `.planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md` — SAFE-01..07 config precedence; the `--config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud` chain that `--sdet` inherits
- `.planning/phases/15-operator-vs-framework-test-surface-split/15-CONTEXT.md` — test-surface split contract; `tests/sdet/` follows the same opt-in pattern as `--with-framework`
- `.planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md` — em-dash failure-detail pattern, pre-run digest, `--explain` expansion, `--debug` appendix semantics; D-06 / D-09 / D-10 / D-11 build on these

### Renderer integration points (Phase 18 extends, does not reshape)

- `src/mcp_test_framework/_runner.py:728-840` — `_render_pre_run_digest` + `_render_skipped_tools_explain`; D-06 adds a scenario-aware variant alongside the existing tool-keyed code
- `src/mcp_test_framework/_runner.py:845-895` — `_render_per_tool_rows`; D-10 reuses the em-dash separator (U+2014 locked at line 537) — Phase 18 does NOT change row format, only feeds different `failure_message` content via the XML parser hookup in D-09
- `src/mcp_test_framework/cli.py:343-540` — `run` Typer command; D-04 / D-05 add `--sdet` flag alongside `--with-framework` / `--explain` / `--debug` / `--raw` / `-q`

### MCP protocol surface

- `mcp.types.CallToolResult` — `isError: bool`, `content: list[ContentBlock]`, `structuredContent: dict | None`; D-08's heuristic chain reads `structuredContent` first, then JSON-parses `content[0].text`
- `mcp.types.TextContent` — `text: str`; the typical content-block carrying tool error prose
- `mcp.ClientSession.call_tool(name, arguments)` — the underlying wire call `ToolWrapper.call` invokes; returns `CallToolResult`

### Seed material

- `.planning/seeds/SEED-014-programmatic-sdet-test-authoring.md` — original motivation, explicit user quote, SDET-persona framing, breadcrumbs into current code

### Memory references (persona + scope discipline)

- `feedback_phase_scope_intent.md` — Phase 18's title is "SDET test surface + typed errors"; the stateful yield-fixture work + dogfood are Phase 19 (STATE-01..04), preflight is Phase 20 (PREFLIGHT-01..02), docs are Phase 21
- `project_vibe_coded_persona.md` — operator + SDET both first-class users in v1.3; D-03 / D-10 / D-11 favor operator-readable error surfaces
- `project_output_ergonomics_at_scale.md` — homelab-mcp ≈ 70 tools; the scenario-aware digest in D-06 needs to behave at scenario-counts in the same range when tests/sdet/ grows

### Files affected by this phase (planner authoritative — this is a forward-look)

- `src/mcp_test_framework/sdet/__init__.py` — add `mcp_session`, `tool`, `ToolCallError` to re-exports + `__all__`
- `src/mcp_test_framework/sdet/_tool_factory.py` — fill `ToolWrapper.call()` body (replace `NotImplementedError`); leave slot contract + dispatch shape unchanged
- `src/mcp_test_framework/sdet/errors.py` (new) — `ToolCallError` definition (D-07) + the field-extraction helper (D-08)
- `src/mcp_test_framework/sdet/session.py` (new, OR added to `__init__.py`) — the `mcp_session` fixture wrapper with D-02 registry activation + D-03 fail-loud
- `src/mcp_test_framework/cli.py` — add `--sdet` flag to `run` (D-04, D-05); thread it through to discovery scope selection
- `src/mcp_test_framework/_runner.py` — extend XML parser to read `mcptf_error_code` / `mcptf_error_message` JUnit properties (D-09); add scenario-aware pre-run-digest builder (D-06); extend `--debug` appendix with ToolCallError structured block (D-11)
- `tests/sdet/__init__.py` (new) — marker package
- `tests/sdet/conftest.py` (new) — `pytest_exception_interact` hook (D-09)
- `tests/sdet/test_basic_call.py` (new) — sanity scenario exercising `tool().call()` end-to-end against the synthetic fixture server from Phase 17
- `tests/framework/unit/test_sdet_fixtures.py` (new) — pins D-01/D-02/D-03 (alias relationship, registry activation, fail-loud message shape)
- `tests/framework/unit/test_tool_call_error.py` (new) — pins D-07/D-08 (Exception shape, heuristic chain, key strictness)
- `tests/framework/unit/test_sdet_cli.py` (new) — pins D-04/D-05 (flag composition matrix); subprocess-based per existing Phase 14 test pattern
- `tests/framework/unit/test_sdet_renderer.py` (new) — pins D-06/D-09/D-10/D-11 (scenario digest, JUnit-property hook-up, FAIL row format, --debug appendix)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`McpTestClient` (already wrapped by the `mcp_client` fixture at `fixtures.py:324-410`)** — exposes the methods Phase 18 needs for `tool().call()`: the underlying `ClientSession` is reachable via the wrapper's internal `_session` attribute, and the wrapper already enforces `asyncio.timeout` semantics around every SDK call. D-01 aliases this fixture as `mcp_session`; the body of `ToolWrapper.call()` calls `await client._session.call_tool(name, params.model_dump(mode="json"))` (or whatever wrapper-public accessor the planner chooses).
- **`_pytest_exit_operator_tone` at `fixtures.py:57-81`** — the operator-tone error helper that mirrors `cli._emit_operator_error`. D-03 reuses this directly so the fail-loud message rendering stays consistent with Phase 13 SAFE-03 behavior.
- **Phase 17 `_slugs.py` slugify helper** — single source of truth for `serverInfo.name → slug`. D-02 imports this; never reimplements the rule.
- **`_load_config(path)` at `cli.py:171` (approx)** — Phase 13 SAFE-01..07 implementation. The `--sdet` path uses this identically; no new config-loading code.
- **Phase 16 em-dash separator at `_runner.py:537`** — U+2014, locked. D-10 reuses verbatim; renderer's row format is unchanged.

### Established Patterns

- **Session-scoped pytest-asyncio fixtures with `loop_scope="session"`** — `mcp_client` and `judge` use this. D-01 inherits by virtue of being a re-export. New SDET fixtures (if any) follow the same lock.
- **AsyncExitStack for resource lifecycle owned across yield** — see `_isolated_home`, `judge`. If the planner decides `mcp_session` needs to own any additional async resource, the pattern is locked.
- **No anyio CancelScope across yield (Phase 04.1 invariant)** — the `mcp_client` fixture's owner-task + `asyncio.Future`/`asyncio.Event` handoff is the only known-safe shape for session-scoped async resources that need anyio scopes. D-02's registry-activation logic is sync (`importlib.import_module` + dict mutation), so it does NOT introduce any new cancel scope — safe to inline in the fixture body around the yield.
- **`ConfigDict(extra="forbid")` on input shapes** — Pydantic v2 convention from the codebase. Generated Params classes already use this (Phase 17); D-07 `ToolCallError` is not Pydantic so the convention doesn't apply.
- **One module per concern** — `sdet/errors.py` for `ToolCallError`, `sdet/_tool_factory.py` for the factory, `sdet/response.py` for the base. Matches the Phase 17 module-narrowing convention.
- **Underscore-prefixed module names are internal** — `_tool_factory.py`, `_slugs.py`, `_codegen.py`. `errors.py` (operator-facing as `ToolCallError`) does NOT get the underscore; `session.py` (if separate from `__init__.py`) does NOT get the underscore either.
- **UTF-8 source + reconfigured stdout on Windows** — Phase 14 establishes the contract; D-10 / D-11 emit through the same reconfigured stdout.

### Integration Points

- **`cli.py:run` flag block (lines 349–418)** — `--sdet` registers alongside `--raw`, `--debug`, `-q/--quiet`, `--with-framework`, `--explain`. Help text mirrors the existing flags' tone (operator-domain language; explicit composition note).
- **`_runner.run_pytest_subprocess(...)` (used at `cli.py:486` for `--raw`)** — Phase 14 helper that builds the pytest argv. D-04 / D-05 add a `sdet: bool = False` kwarg; the helper computes the discovery-paths arg per the composition matrix.
- **`tests/conftest.py:pytest_generate_tests` + the discovery cache** — operates on contract scope; `tests/sdet/` does NOT use the same parametrize hook (SDET tests are hand-authored, not parametrized over discovered tools). The sdet-side conftest at `tests/sdet/conftest.py` is independent.
- **Phase 16 JUnit XML parser inside `_runner.py`** — the consumer for `pytest_exception_interact`'s `user_properties`. D-09 teaches it to recognize the project-scoped keys.

</code_context>

<specifics>
## Specific Ideas

- **`mcptf_error_code` / `mcptf_error_message` as JUnit `user_properties` keys.** Project-scoped prefix avoids collision with anything pytest emits natively or any other plugin's properties. Snake_case to match the rest of the codebase's property-style conventions.
- **`[code] message` em-dash row shape.** Brackets always visible (no whitespace collapse); operator scans the column of bracketed codes when many scenarios fail. Falls back to bare message when `.code is None`.
- **`--debug` appendix block lead-in `--- ToolCallError dump ---`.** Triple-dash fence + named dump type so operators (and future grep) can locate the block in mixed stdout. Match the rest of the appendix's section-separator aesthetic if Phase 16 established one; otherwise this introduces it.
- **Scenario-module bucketing in the digest.** Bucket key = the python module path stem under `tests/sdet/` (e.g. `tests/sdet/test_proxmox_vm_lifecycle.py` → `proxmox_vm_lifecycle`). Sorted alphabetically; `--explain` expansion lists one line per skipped scenario with its `pytest.mark.skip` reason.
- **Minimum viable SDET test for Phase 18 verification.** `tests/sdet/test_basic_call.py` exercising one synthetic-server tool through the wrapper end-to-end. Asserts: (1) `await tool("basic_tool").call(BasicToolParams(...))` returns a `BasicToolResponse` instance; (2) `.raw.isError` is False; (3) the typed `.data` accessor resolves through the CODEGEN-04 chain; (4) calling with invalid Params raises Pydantic ValidationError BEFORE the wire call. No live homelab-mcp dependency — synthetic fixture from Phase 17 is sufficient.
- **`ToolCallError` `__str__` is `[code] message` (or bare `message` when code is None).** Symmetric with the renderer's FAIL row format, so the repr in pytest tracebacks matches what operators see in the domain UI.

</specifics>

<deferred>
## Deferred Ideas

### Cross-phase tasks (v1.3 candidates)

- **Stateful yield-fixture cleanup contract + VM-lifecycle dogfood scenario.** Phase 19 (STATE-01..04 + UI-01).
- **`requires_homelab(...)` marker factory + reachability preflight.** Phase 20 (PREFLIGHT-01..02).
- **Authoring walkthrough + README scenario sample with renderer parity.** Phase 21 (DOC-SDET-01..03).

### v1.4+ candidates

- **Attribute-access `Tool.create_vm.call(...)` ergonomic.** Phase 17 D-09 locked stringly-typed only; v1.4 candidate if SDETs ask.
- **`pytest_exception_interact` enrichment for ALL framework exceptions, not just `ToolCallError`.** Other framework-internal exceptions could benefit from the same JUnit-property surface; out of scope for v1.3.
- **JSON-schema-key synonyms for `ToolCallError` extraction.** Strict `code`/`message` for v1.3 (D-08); add `error` / `detail` / `errorCode` synonym recognition only if real homelab-mcp responses force the conversation.
- **Multi-server SDET runs.** Anti-vision per PROJECT.md. Post-v2.0 if ever.
- **`--sdet --with-contract`** (additive surface). Was considered as Option C in the scope discussion; deferred. If operators report wanting both surfaces in one pass, revisit in v1.4.
- **Per-judge breakdown under `--debug`.** Phase 16 D-11; cohort with SEED-003 in v1.5.

### Out of scope at scoping

- **`tool(...)` lookup performance (sub-millisecond, large registries).** N=70 tools; dict lookup is constant; not worth optimizing.
- **Generated-file change detection.** Phase 17 D-04's pyright gate already enforces this at the type level; no Phase 18 work.
- **Custom pytest plugin packaging.** SEED-015; v1.4. v1.3 stays on the CLI-only delivery model.

</deferred>

---

*Phase: 18-sdet-test-surface-typed-errors*
*Context gathered: 2026-05-12*
