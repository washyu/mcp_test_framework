# Phase 17: Schema-driven codegen surface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-12
**Phase:** 17-schema-driven-codegen-surface
**Areas discussed:** Codegen engine choice, Server-slug derivation, Undeclared `<Tool>Response` shape, CLI surface for `gen-sdet-classes`

---

## Codegen engine choice

### Q1: Which codegen engine for inputSchema/outputSchema -> Pydantic v2 classes?

| Option | Description | Selected |
|--------|-------------|----------|
| Hand-rolled walker | ~200-300 LOC in `src/mcp_test_framework/sdet/_codegen.py`. Reuses `jsonschema` (already a dep) for schema-validity checks only. Full control of import-stability + idempotence + "do not hand-edit" header. | ✓ |
| `datamodel-code-generator` | Mature OpenAPI-codegen-style library; emits Pydantic v2. +1 dev dep; CLI-first; output is JSONSchema/OpenAPI-shaped, would still need a post-processor. | |
| Hybrid: DMG behind a stable seam | DMG does the JSON-Schema -> Pydantic translation; our wrapper owns file layout/headers/slug paths. | |

**User's choice:** Hand-rolled walker (Recommended).
**Notes:** Trade-off accepted — homelab-mcp's surface (~70 tools, mostly flat scalar objects per the existing `_format_param_signature` mapping) is well within reach of a hand-rolled walker. Edge-case constructs (oneOf/anyOf/nullable/$ref/recursive) will be addressed by the next question (D-02 schema-coverage promise) rather than absorbed via DMG.

### Q2: Which JSON-Schema constructs does the walker translate faithfully? (multiSelect; anything not selected -> `Any` with `# codegen: degraded` comment)

| Option | Description | Selected |
|--------|-------------|----------|
| Core scalars + object/array | string/integer/number/boolean/array (with items)/object (with properties + required). | ✓ |
| Enums via `typing.Literal` | `{"enum": [...]}` -> `Literal[...]`. | |
| Nullable | oneOf/anyOf-with-null or `type: [X, null]` -> `X | None`. | |
| oneOf/anyOf non-null `Union` | `oneOf: [{type: integer}, {type: string}]` -> `int | str`. | |

**User's choice:** Core scalars + object/array only.
**Notes:** Conservative MVP scope. Enums, nullable, and unions all degrade to `typing.Any` with a `# codegen: degraded — <reason>` comment. Tests must pin the degradation path (walker does not crash, emits the comment, types to `Any`). Tighter coverage is a v1.4 follow-up if real homelab-mcp schemas drive it.

### Q3: How does `gen-sdet-classes` handle re-runs?

| Option | Description | Selected |
|--------|-------------|----------|
| Wipe-and-write `generated/<server_slug>/` | `rmtree` then fresh write every run. Header marker is informational only. Subclass in `tests/sdet/` is the extension path. | ✓ |
| Hash-stamp header + refuse if local edits found | Compute SHA256 in header; on regen, recompute; mismatch -> abort unless `--force`. | |
| Diff and only rewrite changed files | Per-file diff; preserves mtimes for unchanged files. | |

**User's choice:** Wipe-and-write (Recommended).
**Notes:** Idempotent by construction. No `--force` flag needed. Operators who hand-edit inside `generated/` lose changes silently — the header warned them. Extensions live in `tests/sdet/` via subclassing.

### Q4: Which static type checker verifies the generated classes (and runs as a test fixture)?

| Option | Description | Selected |
|--------|-------------|----------|
| pyright | Fast; works natively with Pydantic v2 (no plugin). Add `pyright>=1.1` to `[dependency-groups].dev`. | ✓ |
| mypy | Older, stricter; needs Pydantic mypy plugin + a config knob. | |
| Both | Belt-and-braces. Doubles dev dep weight + test runtime. | |

**User's choice:** pyright (Recommended).
**Notes:** Scoped via `pyrightconfig.json` (or `[tool.pyright]` in `pyproject.toml`) to `src/mcp_test_framework/sdet/generated/` only — prevents the v1.3 typecheck from blocking on pre-existing v1.0–v1.2 type-debt elsewhere.

---

## Server-slug derivation

### Q1: How is `<server_slug>` derived?

| Option | Description | Selected |
|--------|-------------|----------|
| Server name from MCP `initialize` handshake, slugified | Read `serverInfo.name` from the SDK's `ClientSession.initialize()` return, slugify. | ✓ |
| Explicit `mcp_server.slug` field in config | Operator sets the slug in config.yaml. | |
| Hybrid: handshake by default, config override | Handshake default; config override takes precedence if set. | |
| Derive from `mcp_server.command` | Slugify the command name. | |

**User's choice:** Server name from MCP `initialize` handshake, slugified (Recommended).
**Notes:** Authoritative (server self-identifies), stable across `mcp_server.command/args` changes, requires no extra config field. Slugify rule: lowercase → non-`[a-z0-9]` → underscore → collapse runs → strip. Empty / missing / collision = error loud. Implementation fallbacks (e.g., when `serverInfo.name` is empty) are planner-discretion.

---

## Undeclared `<Tool>Response` shape

### Q1: For tools with no `outputSchema`, what does `<Tool>Response` look like?

| Option | Description | Selected |
|--------|-------------|----------|
| Stub class: `class FooResponse(ToolResponse): pass` | Stable import name; forward-compat if the tool later gains a typed schema. | ✓ |
| Alias: `FooResponse = ToolResponse` | Saves a class def; breaks `from ... import FooResponse` if it later becomes a Pydantic class. | |
| No class generated; expose `ToolResponse` directly | Skip emission for undeclared tools; breaks the symmetry of CODEGEN-05 wrappers. | |

**User's choice:** Stub class (Recommended).
**Notes:** Forward-compat over LOC savings. Three lines per undeclared tool — modest cost for a stable import surface as tools gain schemas over time.

### Q2: How is the `ToolResponse` base implemented?

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic `BaseModel` with `@computed_field` properties | `raw: CallToolResult` field; `.is_error` / `.data` / `.text` as computed properties (lazy). Subclasses inherit accessors + add typed fields. | ✓ |
| Plain class with `@property` accessors | `__init__(raw)`; non-Pydantic. | |
| Pydantic `BaseModel`; `.data` is a real field populated at construction | Eager parse during `model_validate`. | |

**User's choice:** Pydantic `BaseModel` with `@computed_field` properties (Recommended).
**Notes:** Consistent with the framework's existing Pydantic-everywhere pattern (`Config`, `ValidationIssue`, `JudgeResult`). `model_config = ConfigDict(arbitrary_types_allowed=True)` so the `CallToolResult` field validates. Lazy evaluation of `.data` / `.text` / `.is_error` via `@property` semantics — no eager parsing at construction.

---

## CLI surface for `gen-sdet-classes`

### Q1: Which CLI subcommand shape for codegen?

| Option | Description | Selected |
|--------|-------------|----------|
| Flat: `mcp-test-framework gen-sdet-classes` | Matches REQUIREMENTS.md working name. Parallel to existing commands. | ✓ |
| Nested: `mcp-test-framework codegen sdet` | Typer subcommand group; leaves room for `codegen openapi` etc. | |
| Grouped: `mcp-test-framework sdet generate` | All SDET commands under one parent. | |

**User's choice:** Flat (Recommended).
**Notes:** Easy to grep, easy to type, parallel to `run` / `list-tools` / `config-init` / `version`. Honors Phase 13 SAFE-01..07 config precedence via the existing `_load_config(path)` helper. No `--output-dir` (location locked by CODEGEN-01); no `--force` (wipe-and-write makes it unnecessary).

### Q2: What's the SDET call-wrapper idiom?

| Option | Description | Selected |
|--------|-------------|----------|
| `tool("name")` only — stringly-typed | `from mcp_test_framework.sdet import tool; await tool("create_vm").call(CreateVmParams(...))`. Matches CODEGEN-05 spec verbatim. | ✓ |
| Attribute access only: `Tool.create_vm.call(params)` | Generated `Tool` namespace; IDE completion on tool names. | |
| Ship both, recommend `tool("name")` | Two surfaces with the canonical doc'd. | |

**User's choice:** `tool("name")` only (Recommended).
**Notes:** Single surface = lower test surface, simpler doc story, no redundant ergonomics. IDE completion still happens at the Params class — operators import `from mcp_test_framework.sdet.generated.<slug> import CreateVmParams` and pyright catches typos at construction. Tool names being stringly-typed at `tool("name")` is acceptable because the typed return is what test code asserts against.

---

## Claude's Discretion

The planner / researcher has authority on these (see CONTEXT.md §Implementation Decisions → Claude's Discretion):

- `PascalCase` slug helper details + unit test against the homelab-mcp tool-name set.
- One-file-per-tool layout under `generated/<slug>/` + a generated `__init__.py` re-exporter (strongly recommended; lock in planning).
- Where the `tool(name)` factory lives — probably `src/mcp_test_framework/sdet/__init__.py` with a per-server registry written into `generated/<slug>/__init__.py`.
- What `gen-sdet-classes` prints during execution — bounded, one-line-per-tool, matching Phase 16's pre-run-digest aesthetic.
- Fallback message shape when `serverInfo.name` is empty/missing.
- PyrightConfig scoping (probably a targeted `pyrightconfig.json` or `[tool.pyright]` block in `pyproject.toml` scoped to `src/.../sdet/generated/` only).
- Whether the walker emits `model_config = ConfigDict(extra="forbid")` on Params classes (recommended: yes for Params, no for Response).

## Deferred Ideas

Captured in CONTEXT.md §Deferred Ideas (cross-phase v1.3 candidates):

- Faithful enum / nullable / oneOf / anyOf translation — v1.4 candidates, reconsider if real schemas drive a need during Phase 19 dogfood.
- `$ref` resolution — out of scope; most MCP schemas are inline.
- `Tool.create_vm` attribute-access namespace as a second surface — v1.4 if SDETs ask.
- `--output-dir` / `--force` flags — not in v1.3.
- Multi-server codegen — anti-vision per PROJECT.md.

Out of scope at scoping (owned by other v1.3 phases):

- Documentation updates for codegen workflow → Phase 21.
- README scenario sample → Phase 21.
- `--sdet` flag, `mcp_session`, `tool(name)` runtime fixture, `ToolCallError` → Phase 18.
- Stateful yield-fixture cleanup contract + VM-lifecycle dogfood → Phase 19.
- `requires_homelab(...)` preflight → Phase 20.
