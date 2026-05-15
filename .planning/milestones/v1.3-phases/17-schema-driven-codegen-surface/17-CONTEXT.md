# Phase 17: Schema-driven codegen surface - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a single command — `mcp-test-framework gen-sdet-classes` — that introspects the configured MCP server via `list_tools` and writes importable, typed Python classes for every tool into `src/mcp_test_framework/sdet/generated/<server_slug>/`. The generated surface is what Phases 18–21 build on:

- `<PascalCaseToolName>Params` — Pydantic v2 model from the tool's `inputSchema`
- `<PascalCaseToolName>Response` — Pydantic v2 model from `outputSchema` when declared; a stub subclass of `ToolResponse` when undeclared
- `ToolResponse` base — uniform `.raw` / `.data` / `.text` / `.is_error` surface so test code does not branch on whether the response is typed
- Typed call wrappers via `tool("name").call(params)` (stringly-typed name → typed Params in → typed Response out)

**In scope:** CODEGEN-01..06 (6 requirements). The codegen walker, the `ToolResponse` base + computed-field properties, idempotent file emission, the stable import surface, the pyright verification path, and the `gen-sdet-classes` Typer command.

**Out of scope (deliberate):**
- The `--sdet` flag on `run`, `mcp_session` / `tool(name)` runtime fixtures, `ToolCallError`. Those are Phase 18.
- Stateful yield-fixture patterns + dogfood VM-lifecycle scenario. Those are Phase 19.
- `requires_homelab(...)` preflight + reachability checks. Phase 20.
- Authoring docs + README scenario parity. Phase 21.
- Faithful translation of `oneOf` / `anyOf` / `enum` / nullable JSON-Schema constructs (see D-02 — these degrade to `typing.Any` in v1.3; tighter coverage is a v1.4 follow-up).
- Multi-server codegen. One server per `gen-sdet-classes` invocation, per the configured MCP server. Multi-server is anti-vision per PROJECT.md.
- Hand-edit-detection / partial-overwrite safety (see D-03 — wipe-and-write is the supported pattern; subclass in `tests/sdet/` for extensions).

**Hard dependencies (LOCKED — implement against):**
- Phase 13 SAFE-01..07 config precedence (`--config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud`). `gen-sdet-classes` honors the same precedence — it needs `cfg.mcp_server.command/args` to spawn the server.
- Phase 02 `McpTestClient` (`src/mcp_test_framework/mcp_client.py`) — `gen-sdet-classes` opens a session via `McpTestClient`, reads `serverInfo` from the initialize handshake, calls `list_tools()`, then closes. No reuse of the session-scoped fixture from `fixtures.py`.
- Phase 12 operator-first hygiene — docs and scaffolds stay generic; homelab-mcp is one example, not the framework's identity.
- Black-box rule — codegen reads only the MCP wire-protocol surface (`Tool.inputSchema` / `Tool.outputSchema` / `Tool.description`). Never imports homelab-mcp source.

</domain>

<decisions>
## Implementation Decisions

### Codegen engine

- **D-01: Hand-rolled walker in `src/mcp_test_framework/sdet/_codegen.py` (~200–300 LOC).** Walks a JSON Schema, emits Pydantic v2 BaseModel source. No `datamodel-code-generator` dep. Reuses `jsonschema` (already a project dep, used by `schema_validator.py`) for schema-validity checks only — not for translation. Full control of the import-stability contract, the "do not hand-edit" header, the `# codegen: degraded` comments, and the file layout.

- **D-02: Schema-coverage promise is intentionally narrow for v1.3.** The walker faithfully translates:
  - `type: "string" | "integer" | "number" | "boolean"` → `str | int | float | bool`
  - `type: "object"` with `properties` + `required` → nested `BaseModel` with `Field(default=...)` for non-required and `...` (Ellipsis) for required
  - `type: "array"` with scalar `items` → `list[<scalar>]`

  Anything else — `enum`, `oneOf`, `anyOf`, `$ref`, nullable (`["X", "null"]` or `anyOf` with null), recursive schemas — degrades to `typing.Any` with a literal `# codegen: degraded — <reason>` comment on the line above the field. Tests pin the degradation path: the walker must not crash, must emit the comment, must type to `Any`. Tighter coverage (Literal-enums, `X | None` for nullable, `X | Y` for non-null unions) is a v1.4 follow-up if real homelab-mcp schemas drive it.

- **D-03: Regen is wipe-and-write.** `gen-sdet-classes` does `shutil.rmtree(generated/<server_slug>/, ignore_errors=True)` then writes fresh files. No mtime preservation, no per-file diff. Idempotent by construction. The "do not hand-edit" header is informational only — operators who edited inside `generated/` lose their changes silently (the header warned them). The supported extension path is subclassing in `tests/sdet/`, not in-place edits.

- **D-04: pyright is the static-type-check verifier.** Add `pyright>=1.1` to `[dependency-groups].dev` in `pyproject.toml`. A test in `tests/framework/unit/test_codegen_typecheck.py` (or similar) generates classes against a synthetic fixture server, runs `pyright` as a subprocess against `src/mcp_test_framework/sdet/generated/<fixture_slug>/`, and asserts exit 0. No `mypy` plugin gymnastics; no Pydantic-mypy compat layer to maintain. pyright handles Pydantic v2 natively.

### Server-slug derivation

- **D-05: `<server_slug>` is slugified `serverInfo.name` from the MCP `initialize` handshake.** Slugify rule: lowercase → non-`[a-z0-9]` to underscore → collapse runs of underscores → strip leading/trailing underscores. Authoritative (server self-identifies), stable across `mcp_server.command/args` changes, requires no extra config field. If `serverInfo.name` is empty / missing / produces an empty slug after normalization, error loud and point at the planner-discretion fallback (see Claude's Discretion below). Collisions between two servers with the same name are operator-error and likewise error loud.

### Undeclared `<Tool>Response` shape

- **D-06: Stub class for tools with no `outputSchema`.** Emit `class FooResponse(ToolResponse): pass` (three lines, including the docstring). Stable import name even when a tool later gains a typed schema — `from ...generated.<slug>.foo import FooResponse` keeps working; the class body just gains fields on the next regen. Forward-compat over LOC savings.

- **D-07: `ToolResponse` base is a Pydantic v2 BaseModel with `@computed_field` properties.** Location: `src/mcp_test_framework/sdet/response.py`, re-exported from `src/mcp_test_framework/sdet/__init__.py`. Shape:
  ```python
  class ToolResponse(BaseModel):
      model_config = ConfigDict(arbitrary_types_allowed=True)
      raw: CallToolResult

      @computed_field
      @property
      def is_error(self) -> bool: ...        # mirrors raw.isError

      @computed_field
      @property
      def data(self) -> dict | None: ...     # CODEGEN-04 fallback chain

      @computed_field
      @property
      def text(self) -> str: ...             # concatenated TextContent.text
  ```
  `.data` parsing order is locked by CODEGEN-04: `structuredContent` → JSON-parse of first `TextContent` → `{"text": <concat>}` fallback. Lazy evaluation via `@property` (not eager-parsed at construction) — subclasses can override or add typed fields without rebuilding the base accessors.

### CLI surface

- **D-08: Flat Typer subcommand `mcp-test-framework gen-sdet-classes`.** Registered in `src/mcp_test_framework/cli.py` next to `run` / `list-tools` / `config-init` / `version`. Honors the Phase 13 SAFE-01..07 config-precedence chain via the existing `_load_config(path)` helper. No `--output-dir` override — the generated location is locked by CODEGEN-01. No `--force` flag — wipe-and-write makes it unnecessary.

- **D-09: Call-wrapper idiom is stringly-typed `tool("name").call(params)` only.** No attribute-access namespace (`Tool.create_vm.call(...)`); no dual-surface "ship both" hedge. The IDE-completion benefit lives at the Params class — operators import `from mcp_test_framework.sdet.generated.<slug> import CreateVmParams` and pyright catches typos at construction. Tool names being stringly-typed at the `tool("name")` boundary is acceptable because the wrapper's typed return is what downstream test code asserts against. Single surface = lower test surface, simpler doc story, no redundant ergonomics to maintain.

### Claude's Discretion

The planner / researcher has authority on these — they were not surfaced in this discussion because they're implementation mechanics, not user-visible decisions:

- **`PascalCase` slug helper.** `list_registered_servers` → `ListRegisteredServers`. Reuse or extend the slugify logic; pin a unit test against the exact set of tool names homelab-mcp surfaces.
- **One file per tool vs one file per server.** Recommend one file per tool (`generated/<slug>/<tool_name>.py`) plus a generated `__init__.py` that re-exports everything. Better grep-ability + pyright incremental rebuild. Locked in planning.
- **Where the `tool(name)` factory lives.** Probably `src/mcp_test_framework/sdet/__init__.py` (so `from mcp_test_framework.sdet import tool` works), with the factory looking up the generated wrapper class via a registry the codegen writes into `generated/<slug>/__init__.py`. Concrete shape is planner's call.
- **What `gen-sdet-classes` prints during execution.** Suggest a one-line-per-tool digest matching Phase 16's `_render_pre_run_digest` aesthetic. Bounded height, sorted alphabetically. Not a UX overhaul phase — keep it minimal.
- **Fallback when `serverInfo.name` is empty/missing.** Suggest: error with a clear message naming the served command, and document that operators can pin a name via the MCP server config (this is server-side, not framework-side — framework can't fix a server that doesn't self-identify).
- **Pyright config.** A targeted `pyrightconfig.json` (or `[tool.pyright]` in pyproject.toml) scoped to `src/mcp_test_framework/sdet/generated/` so the test does not type-check the whole codebase. Strict mode for the generated dir; ignore everything else.
- **Whether the walker emits `model_config = ConfigDict(extra="forbid")` on Params classes.** Catches typo'd kwargs at construction. Probably yes for Params (loud-fail on operator typos); not for Response (we don't control what the server returns). Planner decides + pins in test.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements

- `.planning/REQUIREMENTS.md` §CODEGEN-01..06 (lines 28–35) — the 6 locked requirements
- `.planning/REQUIREMENTS.md` §"Open Design Questions for Phase Planning" (lines 99–106) — six open questions; this CONTEXT.md resolves D-05 (slug derivation), D-06 (stub vs alias → stub), D-08 (CLI shape → flat), D-09 (wrapper idiom → tool("name") only). Generated-file location is locked in REQUIREMENTS.md itself (`src/mcp_test_framework/sdet/generated/<server_slug>/`).
- `.planning/ROADMAP.md` Phase 17 row (lines 52, 60–69) — goal, depends-on, 4 success criteria
- `.planning/PROJECT.md` — milestone v1.3 framing (Homelab Scenario Testing; operator + SDET dual persona)
- `.planning/STATE.md` — current position (v1.3 roadmap approved 2026-05-12; no phases started)

### v1.3 seed material — primary design spec for this phase

- `.planning/seeds/SEED-014-programmatic-sdet-test-authoring.md` — full motivation; explicit user quote ("I would like to test create_vm but I don't want to generate random VMs"); breadcrumbs to current code; the SDET persona framing; CLI surface options the seed considered
- `.planning/seeds/SEED-004-stateful-tool-testing.md` — pairs naturally; consumed by Phase 19 (the response classes Phase 17 generates flow through Phase 19's module-scope fixtures)

### Existing code Phase 17 must integrate with (LOCKED — do not modify)

- `src/mcp_test_framework/mcp_client.py:106-210` (`McpTestClient`) — async stdio client; Phase 17's `gen-sdet-classes` uses this to open a session, read `serverInfo` from `initialize`, call `list_tools()`, close. The session-scoped fixture in `fixtures.py` is NOT reused — codegen is a one-shot CLI invocation.
- `src/mcp_test_framework/schema_validator.py:34-50` (`Draft202012Validator`, `ValidationIssue`) — the existing jsonschema integration. Phase 17 reuses `Draft202012Validator` for schema-validity sanity checks before translation (refuse to translate a schema that doesn't validate as a JSON Schema document); does NOT use `ValidationIssue` (that's the contract test's error surface, not codegen's).
- `src/mcp_test_framework/cli.py:53-871` (Typer `app`) — where `gen-sdet-classes` registers as a flat subcommand alongside `run` / `list-tools` / `config-init` / `version`. Reuses `_load_config(path)` for SAFE-01..07 config precedence.
- `src/mcp_test_framework/cli.py:901-950` (`_format_param_signature`) — informational reference for JSON-Schema-scalar → Python-type mapping. The walker uses a similar but more thorough mapping; this function is the existing baseline.
- `src/mcp_test_framework/config.py` (`Config`, `MCPServerConfig`) — the Config Pydantic model; `gen-sdet-classes` reads `cfg.mcp_server.command/args/timeout_seconds` (the same fields `cli.py:run` and `list-tools` use).
- `pyproject.toml:7-15` — project deps; `gen-sdet-classes` adds NO runtime deps (Pydantic + jsonschema are present). `pyright>=1.1` adds to `[dependency-groups].dev`.

### v1.2 contracts preserved by this phase (must honor)

- Phase 13 SAFE-01..07 config precedence — `gen-sdet-classes` is subject to `--config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud`. No `.env`, no env-overlay. (`.planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md`)
- Phase 14 / 16 domain-UI surface stays untouched — `gen-sdet-classes` prints its own one-shot output; the `_runner.py` rendering machinery is not invoked. (`.planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md`)
- Phase 15 test-surface split — Phase 17 tests live under `tests/framework/unit/test_codegen_*.py` (framework self-tests); the generated module under `src/.../sdet/generated/` is production code, not test code, even though it's only consumed by tests. (`.planning/phases/15-operator-vs-framework-test-surface-split/15-CONTEXT.md`)
- Black-box rule — `ruff TID251` ban on `homelab_mcp` imports + the `sys.modules` guard in `tests/conftest.py`. Phase 17 generates code that reads MCP wire-protocol surface, never SUT source.

### MCP protocol surface

- `mcp.types.Tool` — has `name`, `description`, `inputSchema` (dict), `outputSchema` (dict | None). The codegen walker consumes these.
- `mcp.types.CallToolResult` — has `isError: bool`, `content: list[ContentBlock]`, optional `structuredContent: dict | None`. `ToolResponse.raw` wraps an instance; `.data` / `.text` / `.is_error` derive from it per CODEGEN-04.
- `ClientSession.initialize()` return value — exposes `serverInfo.name` and `serverInfo.version`. D-05 reads `serverInfo.name`.

### Memory references (operator + SDET-persona context)

- `project_vibe_coded_persona.md` — the operator-persona reframe; codegen-emitted files must remain readable to a non-author operator. Comments matter; the "do not hand-edit" header must be clear.
- `project_output_ergonomics_at_scale.md` — homelab-mcp ≈ 70 tools; generating ~210 files (Params + Response + wrapper per tool) means file-system hygiene matters. One file per tool with a generated `__init__.py` that re-exports = grep-able + IDE-completable + pyright-incremental-friendly.
- `feedback_phase_scope_intent.md` — title = scope; Phase 17 is "Schema-driven codegen surface", not "the SDET runtime". `--sdet` flag, `mcp_session`, `tool(name)` runtime behavior, `ToolCallError` all live in Phase 18. Don't let sub-agents drag those into 17.
- `feedback_scaffold_completeness.md` — generated files must be runnable as imported; no "complete this yourself" placeholders.

### Files affected by this phase (planner authoritative — this is a forward-look)

- `src/mcp_test_framework/sdet/__init__.py` (new) — re-exports `ToolResponse`, `tool` factory
- `src/mcp_test_framework/sdet/response.py` (new) — `ToolResponse` Pydantic BaseModel + `@computed_field` properties (D-07)
- `src/mcp_test_framework/sdet/_codegen.py` (new) — the walker (D-01), schema-coverage rules (D-02), slug helper (D-05), file emitter (D-03)
- `src/mcp_test_framework/sdet/_tool_factory.py` (new) — the `tool(name)` factory + per-server registry the generator writes into `generated/<slug>/__init__.py` (D-09)
- `src/mcp_test_framework/sdet/generated/.gitkeep` (new) — placeholder so the dir ships in source control
- `src/mcp_test_framework/cli.py` — adds the `gen-sdet-classes` Typer command (D-08); reuses `_load_config`
- `pyproject.toml` — adds `pyright>=1.1` to `[dependency-groups].dev`; optionally adds a `[tool.pyright]` scoped config
- `tests/framework/unit/test_codegen_walker.py` (new) — pins schema-coverage promises + degradation behavior
- `tests/framework/unit/test_codegen_emitter.py` (new) — pins file layout, header marker, idempotence
- `tests/framework/unit/test_codegen_typecheck.py` (new) — runs pyright against a fixture-generated module
- `tests/framework/unit/test_tool_response.py` (new) — pins `.data` / `.text` / `.is_error` CODEGEN-04 fallback chain
- `tests/framework/unit/test_gen_sdet_classes_cli.py` (new) — pins the `mcp-test-framework gen-sdet-classes` command shape

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`McpTestClient` at `src/mcp_test_framework/mcp_client.py:106-210`** — async stdio client with `__aenter__` / `__aexit__` lifecycle, `asyncio.timeout` wrapping every SDK call, `shutil.which` pre-flight for friendlier missing-binary errors. `gen-sdet-classes` opens a fresh `McpTestClient(cmd, args, timeout)` (NOT the session-scoped fixture from `fixtures.py`), calls `initialize()` to read `serverInfo`, then `list_tools()`. One-shot — no fixture reuse.
- **`Draft202012Validator` (jsonschema) — already imported at `schema_validator.py:34`** — used by the contract test to sanity-check tool `inputSchema`. Phase 17 reuses it as a pre-flight: refuse to translate a schema that itself isn't a valid JSON Schema document (loud error naming the tool).
- **`_format_param_signature` at `cli.py:901-950`** — existing JSON-Schema-scalar → Python-type mapper. Informational only; the walker reimplements this with required/optional/default semantics + Pydantic v2 emission, but the scalar mapping table can be lifted verbatim.
- **`Config._load_config` precedence chain (`cli.py:171-280` approx)** — Phase 13's SAFE-01..07 implementation; `gen-sdet-classes` reuses the same loader so `--config` / `MCPTF_CONFIG_FILE` / `./config.yaml` precedence is automatic.

### Established Patterns

- **Pydantic v2 BaseModel everywhere.** `Config`, `MCPServerConfig`, `JudgeConfig`, `ValidationIssue`, `JudgeResult`, `RubricResult` are all Pydantic. `ToolResponse` + generated `Params` / `Response` continue the pattern. `model_config = ConfigDict(...)` for per-class settings.
- **`ConfigDict(extra="forbid")` for input shapes.** `Config` uses this so typo'd config keys surface as Pydantic errors. Apply to generated `Params` classes (defensive: catches operator typos at test-construction time). Do NOT apply to `Response` subclasses — we don't control server output shape.
- **One module per concern.** Codebase has `schema_validator.py`, `ollama_judge.py`, `mcp_client.py`, `judge_protocol.py` — narrow modules. Phase 17 follows: `sdet/response.py` (base), `sdet/_codegen.py` (walker + emitter), `sdet/_tool_factory.py` (wrapper factory). `__init__.py` is the public-API curator.
- **Underscore-prefixed module names are internal.** `_runner.py`, `_isolation.py`, `_reporter.py` are framework-internal. The walker (`_codegen.py`) and factory (`_tool_factory.py`) get the underscore prefix; `response.py` (operator-facing as `ToolResponse`) does not.
- **`from __future__ import annotations`** at top of every src module. Generated files inherit the convention — keeps forward-ref edge cases tractable.
- **UTF-8 source encoding.** Phase 14 reconfigures stdout on Windows; generated files use plain ASCII identifiers + UTF-8 docstrings.

### Integration Points

- `cli.py:run` flow already opens a `McpTestClient` for `_discover_tools_for_run(cfg)` — `gen-sdet-classes` follows the same pattern but doesn't reuse the function (it needs `serverInfo` + the raw `Tool` objects, not just names).
- The Typer `app` instance at `cli.py:53` is the registration point for the new subcommand. Position alphabetically among existing commands so `mcp-test-framework --help` reads cleanly.
- pytest's discovery for `tests/framework/` is the locked Phase 15 surface — new codegen tests land there, not under `tests/contract/`.
- The `_load_config` helper at `cli.py:171` handles SAFE-01..07 — `gen-sdet-classes` reuses it; no new config-loading code.

</code_context>

<specifics>
## Specific Ideas

- **One file per tool inside `generated/<slug>/`** is the strong default — `create_vm.py`, `list_registered_servers.py`, etc. Plus a generated `__init__.py` that re-exports `CreateVmParams`, `CreateVmResponse`, etc. Better grep-ability + faster pyright incremental rebuild than a single mega-file.
- **Header marker shape** — every generated file starts with:
  ```python
  # AUTOGENERATED by mcp-test-framework gen-sdet-classes — DO NOT HAND-EDIT.
  # Source: <server_slug> (serverInfo.name="<actual_name>", version="<version>")
  # Regenerated: <ISO timestamp>
  # Extend by subclassing in tests/sdet/, not by editing this file.
  ```
- **`# codegen: degraded` comment shape** — directly above the field, e.g.:
  ```python
      # codegen: degraded — oneOf not in v1.3 coverage; got Any
      target_id: typing.Any
  ```
  Easy to grep, easy for an operator to see exactly which fields lost typing fidelity.
- **homelab-mcp is the canonical test fixture.** Where the test fixtures need a "realistic" server, use a small synthetic server with 3–5 tools exercising the supported constructs (scalar params, required + optional, nested object, array of scalars) + 1–2 tools exercising the degradation path (enum, oneOf). Don't make pyright tests depend on live homelab-mcp — synthetic = fast + deterministic.
- **PyrightConfig scoping** — generated dir only; rest of the codebase out of scope for the typecheck test. Prevents a v1.3 typecheck from blocking on pre-existing v1.0–v1.2 lacuna.
- **Slug example** — `serverInfo.name = "homelab-mcp"` → `homelab_mcp`. `serverInfo.name = "My Server v2.0"` → `my_server_v2_0`. Document the rule next to the slug helper.

</specifics>

<deferred>
## Deferred Ideas

### Cross-phase tasks (v1.3 candidates)

- **Faithful enum translation** (`enum: [a, b, c]` → `Literal["a", "b", "c"]`). v1.4 candidate; reconsider if real homelab-mcp tools surface enum-heavy schemas during Phase 19's VM-lifecycle dogfood.
- **Faithful nullable translation** (`["X", "null"]` or `anyOf` with null → `X | None`). Same window — v1.4 unless dogfood demands it.
- **`oneOf` / `anyOf` non-null → `Union[X, Y]`.** v1.4 candidate. Loses discriminator info even when faithfully translated.
- **`$ref` resolution.** Out of scope. Most MCP tool schemas are inline.
- **`Tool.create_vm` attribute-access namespace as a second surface.** Out for v1.3 (D-09). Could land as an additive ergonomic in v1.4 if SDETs ask for it.
- **`--output-dir` / `--force` flags on `gen-sdet-classes`.** Not in v1.3 — locked location + wipe-and-write removes the need. Revisit if multi-server or shared-fixtures use cases arise.
- **Multi-server codegen.** Anti-vision per PROJECT.md. Post-v2.0 if ever.

### Out of scope at scoping

- **Documentation updates** for the codegen workflow — Phase 21 owns docs.
- **README scenario sample showing codegen → write a test → run.** Phase 21 owns.
- **`--sdet` flag, `mcp_session`, `tool(name)` runtime, `ToolCallError`.** Phase 18.
- **Stateful yield-fixture cleanup contract + VM-lifecycle dogfood.** Phase 19.
- **`requires_homelab(...)` preflight.** Phase 20.

</deferred>

---

*Phase: 17-schema-driven-codegen-surface*
*Context gathered: 2026-05-12*
