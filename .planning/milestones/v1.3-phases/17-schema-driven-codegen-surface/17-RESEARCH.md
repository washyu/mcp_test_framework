# Phase 17: Schema-driven codegen surface — Research

**Researched:** 2026-05-12
**Domain:** JSON-Schema → Pydantic v2 codegen, idempotent file emission, CLI ergonomics for a multi-tool generated import surface
**Confidence:** HIGH (engine + emission strategy locked by CONTEXT.md; library/version facts verified live; remaining unknowns are mechanics already inside Claude's Discretion)

## Summary

CONTEXT.md has already locked the major decisions for this phase: hand-rolled walker in `_codegen.py` (D-01), narrow schema coverage with `Any`-degrade fallback (D-02), wipe-and-write idempotency (D-03), pyright as the static verifier (D-04), `serverInfo.name`-slugified output directory (D-05), stub `<Tool>Response` subclasses for undeclared schemas (D-06), Pydantic `@computed_field`-based `ToolResponse` base (D-07), flat Typer subcommand (D-08), stringly-typed `tool("name").call(...)` wrapper (D-09). Research's job here is to (a) confirm those decisions are technically sound against the current ecosystem, (b) surface concrete patterns for the Claude's-Discretion items (PascalCase helper, one-file-per-tool layout, `tool()` factory location, digest format, `serverInfo.name` empty-fallback, pyright config scoping, `extra="forbid"` on Params), and (c) catalogue pitfalls that show up specifically in the JSON-Schema-to-Pydantic codegen and "70-tool fan-out" sub-domains.

All locked decisions are sound. The codegen walker is well-sized at ~200–300 LOC because D-02 deliberately punts on the JSON-Schema constructs (`oneOf`/`anyOf`/`enum`/`$ref`/recursion) that make general-purpose generators (`datamodel-code-generator`) earn their keep. The MCP SDK's `Tool.inputSchema` is a plain `dict` and `Tool.outputSchema` is `dict | None` — the walker reads them directly. `CallToolResult` has exactly the fields CODEGEN-04 references (`isError: bool`, `content: list[...]`, `structuredContent: dict | None`) — `[VERIFIED: uv run python -c "from mcp.types import CallToolResult; print(CallToolResult.model_fields)"]`.

**Primary recommendation:** Implement the codegen as a self-contained `sdet/_codegen.py` module that walks `Tool.inputSchema` / `Tool.outputSchema` and emits one file per tool under `generated/<server_slug>/`, plus a generated `__init__.py` that re-exports every `Params` and `Response` class and registers per-tool wrapper info in a module-level `_REGISTRY: dict[str, type[ToolResponse]]` consumed by the `tool(name)` factory. Use Python's standard library only (`textwrap`, `re`, `keyword`, `shutil`, `pathlib`) — no new runtime deps. Add `pyright>=1.1.409` to `[dependency-groups].dev` and a `[tool.pyright]` block in `pyproject.toml` scoped to `src/mcp_test_framework/sdet/generated/` in strict mode.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: Hand-rolled walker in `src/mcp_test_framework/sdet/_codegen.py` (~200–300 LOC).**
Walks JSON Schema, emits Pydantic v2 BaseModel source. No `datamodel-code-generator` dep. Reuses `jsonschema` (already a project dep, used by `schema_validator.py`) for schema-validity checks only — not for translation. Full control of import-stability, "do not hand-edit" header, `# codegen: degraded` comments, and file layout.

**D-02: Schema-coverage promise is intentionally narrow for v1.3.** The walker faithfully translates:
- `type: "string" | "integer" | "number" | "boolean"` → `str | int | float | bool`
- `type: "object"` with `properties` + `required` → nested `BaseModel` with `Field(default=...)` for non-required and `...` (Ellipsis) for required
- `type: "array"` with scalar `items` → `list[<scalar>]`

Anything else (`enum`, `oneOf`, `anyOf`, `$ref`, nullable, recursive) degrades to `typing.Any` with a `# codegen: degraded — <reason>` comment on the line above the field. Tests pin the degradation path.

**D-03: Regen is wipe-and-write.** `gen-sdet-classes` does `shutil.rmtree(generated/<server_slug>/, ignore_errors=True)` then writes fresh files. No mtime preservation, no per-file diff. Idempotent by construction. Header is informational only — operators who edited inside `generated/` lose their changes silently. Supported extension path: subclassing in `tests/sdet/`.

**D-04: pyright is the static-type-check verifier.** Add `pyright>=1.1` to `[dependency-groups].dev`. A test in `tests/framework/unit/test_codegen_typecheck.py` generates classes against a synthetic fixture server, runs `pyright` as a subprocess against `src/mcp_test_framework/sdet/generated/<fixture_slug>/`, and asserts exit 0. No `mypy` plugin gymnastics; pyright handles Pydantic v2 natively via `@dataclass_transform` (PEP 681).

**D-05: `<server_slug>` is slugified `serverInfo.name` from the MCP `initialize` handshake.** Slugify rule: lowercase → non-`[a-z0-9]` to underscore → collapse runs of underscores → strip leading/trailing underscores. If `serverInfo.name` is empty/missing/produces empty slug after normalization, error loud. Collisions between two servers with the same name are operator-error.

**D-06: Stub class for tools with no `outputSchema`.** Emit `class FooResponse(ToolResponse): pass` (three lines including docstring). Stable import name even when a tool later gains a typed schema.

**D-07: `ToolResponse` base is a Pydantic v2 BaseModel with `@computed_field` properties.** Location: `src/mcp_test_framework/sdet/response.py`, re-exported from `src/mcp_test_framework/sdet/__init__.py`. Shape:
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
`.data` parsing order is locked by CODEGEN-04: `structuredContent` → JSON-parse of first `TextContent` → `{"text": <concat>}` fallback. Lazy evaluation via `@property` (not eager-parsed at construction).

**D-08: Flat Typer subcommand `mcp-test-framework gen-sdet-classes`.** Registered in `src/mcp_test_framework/cli.py` next to `run` / `list-tools` / `config-init` / `version`. Honors the Phase 13 SAFE-01..07 config-precedence chain via the existing `_load_config(path)` helper. No `--output-dir` override. No `--force` flag.

**D-09: Call-wrapper idiom is stringly-typed `tool("name").call(params)` only.** No attribute-access namespace; no dual-surface "ship both" hedge. IDE-completion benefit lives at the Params class. Single surface = lower test surface.

### Claude's Discretion

Implementation mechanics owned by the planner / researcher:

- **`PascalCase` slug helper.** `list_registered_servers` → `ListRegisteredServers`. Pin a unit test against the exact set of tool names homelab-mcp surfaces.
- **One file per tool vs one file per server.** Recommend one file per tool (`generated/<slug>/<tool_name>.py`) plus a generated `__init__.py` re-exporter. Better grep-ability + pyright incremental rebuild. Locked in planning.
- **Where the `tool(name)` factory lives.** Probably `src/mcp_test_framework/sdet/__init__.py` (so `from mcp_test_framework.sdet import tool` works), with the factory looking up the generated wrapper class via a registry the codegen writes into `generated/<slug>/__init__.py`. Concrete shape is planner's call.
- **What `gen-sdet-classes` prints during execution.** One-line-per-tool digest matching Phase 16's `_render_pre_run_digest` aesthetic. Bounded height, sorted alphabetically. Not a UX overhaul phase.
- **Fallback when `serverInfo.name` is empty/missing.** Error with a clear message naming the served command; document that operators can pin a name via the MCP server config.
- **Pyright config.** A targeted `pyrightconfig.json` (or `[tool.pyright]` in pyproject.toml) scoped to `src/mcp_test_framework/sdet/generated/`. Strict mode for the generated dir.
- **Whether the walker emits `model_config = ConfigDict(extra="forbid")` on Params classes.** Probably yes for Params (loud-fail on operator typos); not for Response.

### Deferred Ideas (OUT OF SCOPE)

**Cross-phase v1.3 candidates:**
- Faithful enum translation (`enum: [a, b, c]` → `Literal[...]`) — v1.4 candidate
- Faithful nullable translation (`["X", "null"]` → `X | None`) — v1.4
- `oneOf` / `anyOf` non-null → `Union[X, Y]` — v1.4
- `$ref` resolution — out of scope
- `Tool.create_vm` attribute-access namespace as a second surface — v1.4 if SDETs ask
- `--output-dir` / `--force` flags on `gen-sdet-classes` — not in v1.3
- Multi-server codegen — anti-vision per PROJECT.md

**Out of scope at scoping (other v1.3 phases):**
- Documentation updates → Phase 21
- README scenario sample → Phase 21
- `--sdet` flag, `mcp_session`, `tool(name)` runtime, `ToolCallError` → Phase 18
- Stateful yield-fixture cleanup + VM-lifecycle dogfood → Phase 19
- `requires_homelab(...)` preflight → Phase 20
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CODEGEN-01 | `mcp-test-framework gen-sdet-classes` introspects via `list_tools` and writes to `src/mcp_test_framework/sdet/generated/<server_slug>/`. Idempotent. | "CLI surface" + "Architecture Patterns" + "Idempotency / Determinism" sections below; reuses existing `_load_config` + `McpTestClient`. |
| CODEGEN-02 | Param classes generated as Pydantic models from each tool's `inputSchema`. Class name: `<PascalCaseToolName>Params`. | "Walker design" + "PascalCase helper" + "Identifier sanitization" sections; reuses `_format_param_signature`'s scalar map as starting table. |
| CODEGEN-03 | Response classes for every tool. `outputSchema` declared → Pydantic model; undeclared → `class FooResponse(ToolResponse): pass`. Class name: `<PascalCaseToolName>Response`. | D-06 (stub class). Emission pattern in "File template" section. |
| CODEGEN-04 | `ToolResponse` base provides uniform `.raw` / `.data` / `.text` / `.is_error`. `.data` fallback chain: `structuredContent` → JSON-parse of first `TextContent` → `{"text": <concat>}`. | D-07 + verified `CallToolResult` shape (`isError: bool`, `content: list[...]`, `structuredContent: dict | None`). "Code Examples" section gives the full `@computed_field` body. |
| CODEGEN-05 | Typed call wrapper: `tool("name").call(params: <Params>) -> <Response>`. Validates params (Pydantic) before wire call; parses response into typed class. | "Call-wrapper plumbing" section. Registry pattern keyed by tool name; wrapper constructs the response via `<Response>(raw=call_tool_result)`. |
| CODEGEN-06 | Generated files contain a leading "do not hand-edit" comment marker. | "Header marker shape" — locked in CONTEXT.md §Specifics. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| MCP handshake + `list_tools()` for codegen input | Backend / SDK (mcp `ClientSession`) | — | Black-box rule: codegen reads only the MCP wire-protocol surface. `McpTestClient` already wraps the SDK; codegen is its caller. |
| JSON-Schema → Pydantic source translation | Library / framework code (`sdet/_codegen.py`) | — | Pure data; no I/O. Walker takes a `dict` and returns a `str`. |
| File emission + wipe-and-write | Library / framework code (`sdet/_codegen.py`) | OS (`shutil.rmtree`, `pathlib.Path.write_text`) | OS owns filesystem; walker owns content and layout. |
| Pydantic runtime validation of operator-constructed params | Pydantic v2 (`BaseModel.__init__`) | — | Free with the generated class. Locked by D-09 — validation happens at `CreateVmParams(...)` construction, not at the `tool(...).call(...)` boundary. |
| `tool("name")` factory + per-server registry | Library / framework code (`sdet/__init__.py` + generated `generated/<slug>/__init__.py`) | — | Registry written by codegen; factory dispatches by name. Phase 18 owns the *runtime* `mcp_session` consumed by the wrapper; Phase 17 only ships the dispatch shape. |
| Static-type verification | Tooling (pyright subprocess) | Test code (`tests/framework/unit/test_codegen_typecheck.py`) | Test code drives the subprocess; pyright owns the analysis. |
| CLI command registration | Typer (`cli.py:app`) | Library helpers (`_load_config`, `McpTestClient`) | Typer is the existing entry point; new command piggybacks on locked Phase 13 helpers. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.14.x | Runtime | Pinned; `keyword.iskeyword`, `re`, `pathlib`, `shutil` all stdlib. |
| `mcp[cli]` | >=1.27 (already pinned) | `Tool` / `CallToolResult` / `ClientSession` types | Already a project dep; provides `Tool.inputSchema` (dict), `Tool.outputSchema` (dict\|None), and the `CallToolResult` shape codegen consumes. `[VERIFIED: uv run python -c "from mcp.types import CallToolResult, Tool; print(list(CallToolResult.model_fields.keys()), list(Tool.model_fields.keys()))"]` returns `['meta', 'content', 'structuredContent', 'isError']` and `['name', 'title', 'description', 'inputSchema', 'outputSchema', 'icons', 'annotations', 'meta', 'execution']`. |
| `pydantic` | >=2.13,<3 (already pinned) | Generated `BaseModel` classes + `@computed_field` on `ToolResponse` | Already pinned; supports `dataclass_transform` (PEP 681) which is what makes pyright understand generated classes natively without a plugin. |
| `jsonschema` | >=4.26 (already pinned) | Pre-flight check that an `inputSchema` is itself a valid JSON Schema document | Already used by `schema_validator.py` via `Draft202012Validator` + `validator_for`. Reused as a pre-flight guard only — not for translation. |
| `typer` (transitive via `mcp[cli]`) | bundled | `gen-sdet-classes` Typer command | Existing convention — `cli.py` already declares 4 commands via `@app.command(...)`. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pyright` | >=1.1.409 (latest 2026-04-23) `[VERIFIED: PyPI 2026-05-12]` | Static type-check verifier in `tests/framework/unit/test_codegen_typecheck.py` | New dev dep under `[dependency-groups].dev`. Strict mode scoped to `src/mcp_test_framework/sdet/generated/` only via `[tool.pyright]` in `pyproject.toml`. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled walker (D-01) | `datamodel-code-generator` 0.57.0 `[VERIFIED: PyPI 2026-05-07]` | DMG handles `$ref` / `oneOf` / `anyOf` / `enum` / nullable faithfully out of the box. But D-02 explicitly punts on those — DMG's strength is unused. It also imposes its own emission style (forward-ref handling, casing, formatter integration) and would still need a wrapping post-processor to honor the "do not hand-edit" header, slug-derived paths, and the `# codegen: degraded` convention. Net: +1 dev dep, +1 layer of indirection, no faithfulness gain at v1.3 scope. **Skipped per D-01.** |
| `pyright` (D-04) | `mypy` + `pydantic.mypy` plugin | Plugin pinning becomes a separate maintenance surface; plugin compatibility lags pydantic minor releases. pyright handles Pydantic v2 natively via `@dataclass_transform` (PEP 681) with no plugin — `[CITED: docs.pydantic.dev/latest/integrations/visual_studio_code/, peps.python.org/pep-0681/]`. **Skipped per D-04.** |
| stdlib `re` for slug + PascalCase | `python-slugify` | Two functions (~10 lines each) don't justify a runtime dep. Pure-stdlib keeps the runtime surface clean (no new direct deps for `gen-sdet-classes`). |
| Per-tool subprocess pyright in test | Single pyright invocation against `generated/<slug>/` | Single invocation is faster and the failure surface is the same. **Use single invocation.** |

**Installation:**

```bash
# Add pyright to dev deps. No new runtime deps.
uv add --dev "pyright>=1.1.409"
```

In `pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "pytest>=9.0",
    "pytest-asyncio>=1.3",
    "pytest-timeout>=2.4",
    "ruff>=0.8",
    "pyright>=1.1.409",   # NEW — Phase 17 D-04
]

[tool.pyright]
# Phase 17 D-04: scope the typecheck to generated SDET classes only.
# Prevents a v1.3 typecheck from blocking on pre-existing v1.0–v1.2 type debt.
include = ["src/mcp_test_framework/sdet/generated"]
strict = ["src/mcp_test_framework/sdet/generated"]
reportMissingTypeStubs = false
pythonVersion = "3.14"
```

**Version verification (2026-05-12):**

| Package | Pinned | Latest | Action |
|---------|--------|--------|--------|
| `mcp` | >=1.27 | 1.27.0 (project venv) `[VERIFIED: uv pip show mcp]` | No change. |
| `pydantic` | >=2.13,<3 | 2.13.x | No change. |
| `jsonschema` | >=4.26 | 4.26.x | No change. |
| `pyright` | (new) | 1.1.409 (2026-04-23) `[VERIFIED: curl pypi.org/pypi/pyright/json]` | Add. |
| `datamodel-code-generator` | (rejected) | 0.57.0 (2026-05-07) `[VERIFIED: curl pypi.org/pypi/datamodel-code-generator/json]` | Do not add. |

## Architecture Patterns

### System Architecture Diagram

```
                                      gen-sdet-classes (Typer command)
                                              │
                            (--config PATH > MCPTF_CONFIG_FILE > ./config.yaml)
                                              │
                                              ▼
                                      _load_config(path)
                                              │
                                              ▼
                          asyncio.Runner + AsyncExitStack-owned McpTestClient
                                              │
                                ┌─────────────┴──────────────┐
                                ▼                            ▼
                  ClientSession.initialize()         ClientSession.list_tools()
                       (serverInfo.name)                  (list[Tool])
                                │                            │
                                ▼                            │
                       slugify → <server_slug>               │
                                │                            │
                                └─────────────┬──────────────┘
                                              ▼
                          shutil.rmtree(generated/<server_slug>/, ignore_errors=True)
                                              │
                                              ▼
                          for tool in sorted(tools, key=name):
                            ├─ _codegen.translate_tool(tool) ──┐
                            │                                  │
                            │   inputSchema  ──► <Tool>Params  │
                            │   outputSchema ──► <Tool>Response (or stub if absent)
                            │   ToolResponse base re-exported from sdet.response
                            │                                  │
                            └─ write generated/<slug>/<tool_name>.py
                                              │
                                              ▼
                          write generated/<slug>/__init__.py (re-exports + registry)
                                              │
                                              ▼
                          stdout: one-line-per-tool digest (Phase 16 aesthetic)
                                              │
                                              ▼
                                       exit 0 / exit 2
```

**At test-run time (Phase 18 consumer of Phase 17 output):**
```
operator's test file
        │
        ├─ from mcp_test_framework.sdet.generated.<slug> import CreateVmParams
        ├─ from mcp_test_framework.sdet import tool, mcp_session  # Phase 18
        │
        ▼
   tool("create_vm").call(CreateVmParams(...))
        │
        │  Pydantic validates params at CreateVmParams(...) construction
        ▼
   _REGISTRY["create_vm"]: CreateVmResponse  ◄── written by codegen
        │
        ▼
   await session.call_tool("create_vm", params.model_dump())
        │
        ▼
   CreateVmResponse(raw=call_tool_result)  ──► test code asserts .data / .text / .is_error
```

### Recommended Project Structure

```
src/mcp_test_framework/sdet/
├── __init__.py              # Public surface: re-exports ToolResponse, tool()
├── response.py              # ToolResponse base (D-07) + @computed_field properties
├── _codegen.py              # Walker (D-01) + slugify + PascalCase helpers + file emitter
├── _tool_factory.py         # tool(name) factory + registry lookup
└── generated/
    ├── .gitkeep             # placeholder so dir ships in source control
    └── <server_slug>/       # written by gen-sdet-classes (wipe-and-write)
        ├── __init__.py      # re-exports every <Tool>Params / <Tool>Response + _REGISTRY
        ├── create_vm.py     # CreateVmParams + CreateVmResponse for create_vm tool
        ├── delete_vm.py     # ...
        └── list_registered_servers.py
tests/framework/unit/
├── test_codegen_walker.py         # pins schema-coverage promises + degradation behavior
├── test_codegen_emitter.py        # pins file layout, header marker, idempotence
├── test_codegen_typecheck.py      # runs pyright against a fixture-generated module
├── test_tool_response.py          # pins .data / .text / .is_error CODEGEN-04 fallback chain
└── test_gen_sdet_classes_cli.py   # pins the CLI command shape
```

### Pattern 1: Walker — schema dispatch by `type`

**What:** Single recursive function `_emit_field(name, schema, required) -> tuple[type_str, default_str, degrade_comment | None]`. Switches on `schema.get("type")` for the four supported scalars + `"object"` + `"array"`. Anything else returns `("Any", "...", "# codegen: degraded — <reason>")`.

**When to use:** Per-property inside the walker. The Params class assembly loop calls `_emit_field` for each property; the Response model walks `outputSchema.properties` the same way.

**Example:**
```python
# Source: hand-rolled per D-01 / D-02
_SCALAR_MAP = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
}

def _emit_field(name: str, schema: dict, *, required: bool) -> FieldSpec:
    jtype = schema.get("type")
    # Degradation cases (D-02) — anything not in the supported set goes to Any.
    if "enum" in schema:
        return FieldSpec(py_type="typing.Any", default="...", degrade="enum not in v1.3 coverage")
    if any(k in schema for k in ("oneOf", "anyOf", "$ref")):
        return FieldSpec(py_type="typing.Any", default="...", degrade=f"{next(iter(k for k in ('oneOf','anyOf','$ref') if k in schema))} not in v1.3 coverage")
    if isinstance(jtype, list):  # ["X", "null"] nullable form
        return FieldSpec(py_type="typing.Any", default="...", degrade="multi-type / nullable not in v1.3 coverage")

    if jtype in _SCALAR_MAP:
        return FieldSpec(py_type=_SCALAR_MAP[jtype], default=_required_or_default(schema, required))
    if jtype == "array":
        items = schema.get("items") or {}
        if items.get("type") in _SCALAR_MAP:
            return FieldSpec(py_type=f"list[{_SCALAR_MAP[items['type']]}]", default=_required_or_default(schema, required))
        return FieldSpec(py_type="typing.Any", default="...", degrade="array with non-scalar items not in v1.3 coverage")
    if jtype == "object":
        # Nested model — emit a separate inner BaseModel and reference by name.
        # See "Nested object handling" below for the recursion + naming rule.
        ...
    return FieldSpec(py_type="typing.Any", default="...", degrade=f"unknown type: {jtype!r}")
```

### Pattern 2: PascalCase + identifier sanitization

**What:** Convert tool name (snake_case, kebab-case, or arbitrary) → PascalCase class identifier. Guard against Python keywords and non-identifier characters.

**When to use:** Once per tool — generates `<PascalCaseToolName>Params` / `<PascalCaseToolName>Response` and the per-tool file name.

**Example:**
```python
# Source: hand-rolled, locked under Claude's Discretion
import keyword
import re

_NON_IDENT = re.compile(r"[^a-zA-Z0-9_]+")

def _pascal_case(tool_name: str) -> str:
    """Convert a tool name to a PascalCase class identifier.

    >>> _pascal_case("create_vm")
    'CreateVm'
    >>> _pascal_case("list-registered-servers")
    'ListRegisteredServers'
    >>> _pascal_case("class")          # Python keyword
    'Class_'
    >>> _pascal_case("2nd_attempt")    # starts with digit
    '_2ndAttempt'
    """
    parts = [p for p in _NON_IDENT.split(tool_name) if p]
    if not parts:
        raise ValueError(f"tool name {tool_name!r} has no identifier characters")
    pascal = "".join(p[:1].upper() + p[1:] for p in parts)
    if pascal[0].isdigit():
        pascal = "_" + pascal
    if keyword.iskeyword(pascal) or keyword.iskeyword(pascal.lower()):
        pascal = pascal + "_"
    return pascal


def _module_name(tool_name: str) -> str:
    """Convert a tool name to a snake_case module name.

    >>> _module_name("create_vm")
    'create_vm'
    >>> _module_name("list-registered-servers")
    'list_registered_servers'
    >>> _module_name("import")
    'import_'
    """
    name = _NON_IDENT.sub("_", tool_name).strip("_").lower()
    if not name:
        raise ValueError(f"tool name {tool_name!r} has no identifier characters")
    if name[0].isdigit():
        name = "_" + name
    if keyword.iskeyword(name):
        name = name + "_"
    return name
```

**Pin a unit test against the homelab-mcp tool-name set:** Capture the ~70 tool names from a live `list-tools` run as a fixture once, assert `_pascal_case` and `_module_name` produce stable, non-colliding results across the set. This is the planner-discretion test mentioned in CONTEXT.md.

### Pattern 3: File template (per-tool file)

**What:** Each `generated/<slug>/<tool_name>.py` follows the same five-zone structure: header → imports → optional nested models → Params class → Response class.

**When to use:** Every tool file.

**Example:**
```python
# AUTOGENERATED by mcp-test-framework gen-sdet-classes — DO NOT HAND-EDIT.
# Source: homelab_mcp (serverInfo.name="homelab-mcp", version="0.5.2")
# Regenerated: 2026-05-12T14:23:01Z
# Extend by subclassing in tests/sdet/, not by editing this file.
from __future__ import annotations

import typing
from pydantic import BaseModel, ConfigDict, Field

from mcp_test_framework.sdet.response import ToolResponse


class CreateVmParams(BaseModel):
    """Params for the `create_vm` tool.

    Generated from inputSchema. Constructing this model validates the
    schema's required / type / default rules before the wire call.
    """
    model_config = ConfigDict(extra="forbid")   # operator-typo guard (Claude's Discretion → recommend yes)

    name: str = Field(..., description="VM name")
    cpus: int = Field(2, description="vCPU count")
    # codegen: degraded — enum not in v1.3 coverage
    os_type: typing.Any = Field(..., description="OS family")


class CreateVmResponse(ToolResponse):
    """Typed response for the `create_vm` tool.

    Fields below are derived from outputSchema. Inherits .raw / .data /
    .text / .is_error from ToolResponse (CODEGEN-04).
    """
    pass   # outputSchema undeclared → stub (D-06)
```

**For tools with a typed outputSchema**, the `Response` class body has its own fields (instead of `pass`) but does NOT carry `extra="forbid"` — Claude's Discretion recommendation: lenient on responses (we don't control server output), strict on params (catch operator typos at construction).

### Pattern 4: Generated `__init__.py` (per-server)

**What:** Re-exports every `<Tool>Params` / `<Tool>Response` + a `_REGISTRY` dict the `tool(name)` factory dispatches against.

**When to use:** Exactly one per server slug. Written last in the emit loop so it sees the full tool set.

**Example:**
```python
# AUTOGENERATED by mcp-test-framework gen-sdet-classes — DO NOT HAND-EDIT.
# Source: homelab_mcp (serverInfo.name="homelab-mcp", version="0.5.2")
# Regenerated: 2026-05-12T14:23:01Z
from __future__ import annotations

from mcp_test_framework.sdet.response import ToolResponse

from .create_vm import CreateVmParams, CreateVmResponse
from .delete_vm import DeleteVmParams, DeleteVmResponse
from .list_registered_servers import ListRegisteredServersParams, ListRegisteredServersResponse
# ... 70+ tools

__all__ = [
    "CreateVmParams", "CreateVmResponse",
    "DeleteVmParams", "DeleteVmResponse",
    "ListRegisteredServersParams", "ListRegisteredServersResponse",
    # ...
]

# Phase 17 CODEGEN-05: tool(name) factory dispatches against this.
# Phase 18 will consume _REGISTRY through `mcp_test_framework.sdet._tool_factory`.
_REGISTRY: dict[str, tuple[type, type[ToolResponse]]] = {
    "create_vm": (CreateVmParams, CreateVmResponse),
    "delete_vm": (DeleteVmParams, DeleteVmResponse),
    "list_registered_servers": (ListRegisteredServersParams, ListRegisteredServersResponse),
    # ...
}
```

### Pattern 5: Call-wrapper plumbing (CODEGEN-05)

**What:** `tool("name").call(params)` plumbs the typed Pydantic model through `ClientSession.call_tool(name, arguments)` and wraps the result in the typed `Response` class.

**When to use:** Phase 17 ships the *codegen-side* hook only (registry + Response class). The async session that owns `call_tool` is Phase 18's `mcp_session` fixture. **Phase 17 must not start a session on its own at test-runtime** — that's the cross-phase boundary.

**Recommended Phase 17 surface (lives in `src/mcp_test_framework/sdet/_tool_factory.py`):**
```python
# Source: hand-rolled per D-09
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from mcp_test_framework.sdet.response import ToolResponse

# These are set by Phase 18 when the fixture initializes; Phase 17 only
# ships the dispatch shape so generated classes are import-clean.
_REGISTRIES: dict[str, dict[str, tuple[type[BaseModel], type[ToolResponse]]]] = {}
_ACTIVE_SLUG: str | None = None

P = TypeVar("P", bound=BaseModel)
R = TypeVar("R", bound=ToolResponse)


class ToolWrapper(Generic[P, R]):
    """Returned by tool(name). Phase 17 ships the shape; Phase 18 wires .call().

    Phase 17 contract:
      - constructed by tool(name) with the registered (params_cls, response_cls)
      - .call(params) IS NOT YET wired (Phase 18 owns the session)
      - .params_cls and .response_cls are exposed for introspection
    """
    def __init__(self, name: str, params_cls: type[P], response_cls: type[R]) -> None:
        self.name = name
        self.params_cls = params_cls
        self.response_cls = response_cls

    async def call(self, params: P) -> R:
        # Phase 18 fills in the body; Phase 17 ships a NotImplementedError
        # placeholder so generated classes are importable and pyright clean,
        # but a Phase-17-only test running `tool(...).call(...)` would fail
        # by design — Phase 18's session fixture is the missing piece.
        raise NotImplementedError(
            "tool().call() requires Phase 18's mcp_session fixture. "
            "Phase 17 only ships the codegen surface."
        )


def tool(name: str) -> ToolWrapper:
    """Look up the typed wrapper for an MCP tool.

    Phase 17 contract: returns a ToolWrapper whose params_cls and response_cls
    were registered by `gen-sdet-classes`. Phase 18 wires the .call() body.
    """
    if _ACTIVE_SLUG is None:
        raise RuntimeError(
            "no MCP server registry is active. "
            "did you forget `mcp_session` fixture? (Phase 18)"
        )
    registry = _REGISTRIES[_ACTIVE_SLUG]
    if name not in registry:
        raise KeyError(
            f"tool {name!r} not in generated registry for server {_ACTIVE_SLUG!r}. "
            f"available: {sorted(registry.keys())}"
        )
    params_cls, response_cls = registry[name]
    return ToolWrapper(name, params_cls, response_cls)
```

**This sketches the Phase-17→Phase-18 seam.** Phase 17's tests assert the wrapper is constructible and raises `NotImplementedError` on `.call(...)` with a clear message; Phase 18 fills in the body. The planner may choose to delay the entire `_tool_factory.py` module to Phase 18 — but having it Phase-17-shipped means generated `__init__.py`s have a stable import target now, and Phase 18 changes only the `.call(...)` body. Recommendation: ship the wrapper now to lock the seam.

### Anti-Patterns to Avoid

- **`eval()` / `exec()` to "compile and re-emit" Python source.** Always write text directly. The walker emits strings; idempotency relies on stable string output. `ast.unparse` introduces ordering surprises across Python minor releases.
- **Caching schemas in `generated/<slug>/.cache.json` to skip unchanged tools.** Defeats wipe-and-write D-03. Per-tool emission is fast; the bottleneck is the MCP handshake, which happens once per invocation regardless.
- **Running `ruff format` over generated files as part of `gen-sdet-classes`.** Idempotency relies on deterministic emission. Ruff version drift in the operator's env would silently change generated content. **Emit pre-formatted output directly.** (Generated files still pass `ruff check` because the emitted style is conservative — line length under 100, no trailing whitespace, sorted imports.)
- **Tool-name-as-module-name without sanitization.** A tool named `import` or `2fa-verify` produces invalid Python module names. Use `_module_name()` (Pattern 2).
- **Inheriting `pass`-stub `Response` from a non-Pydantic base.** Subclasses inherit `model_config`; if `ToolResponse` were not a Pydantic model, the stub couldn't gain typed fields later without a breaking schema migration. D-07 (Pydantic base) is the right call.
- **Emitting `tool_name: str = "..."` as a field default in Params.** The MCP wire protocol expects `arguments` to be a dict of *just* the inputSchema properties — never echo the tool name into the model.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Verifying that `inputSchema` itself is a valid JSON Schema document | Custom recursive schema validator | Existing `Draft202012Validator.check_schema` (via `validator_for(schema, default=Draft202012Validator)`) — same pattern as `schema_validator.py:124` | Already a transitive dep; battle-tested; failure surface is a clean `SchemaError` to wrap in a degrade-or-fail decision. |
| Pydantic v2 model dumping for the wire call | Hand-rolled `dict(params)` walk | `params.model_dump(mode="python")` | Handles `Field(alias=...)`, exclude-none semantics, nested model unfolding, and serializer overrides for free. |
| Sorting the registry / tool list for deterministic emission | Custom comparator | `sorted(tools, key=lambda t: t.name)` | Python's `sorted` is stable; tool names are ASCII-only after `_module_name` sanitization. |
| Locating the resolved config file | Re-implementing precedence in the new command | Existing `cli._load_config(path)` (Phase 13 SAFE-01..07) | LOCKED — touching it would re-litigate Phase 13. The new command is a one-liner: `cfg = _load_config(config)`. |
| Spawning the MCP server for the codegen handshake | `subprocess.Popen` or a new `asyncio.create_subprocess_exec` path | Existing `McpTestClient` with `AsyncExitStack` + `asyncio.Runner` | LOCKED — same pattern as `cli.list_tools` (lines 663-664). Reuses the friendly-error mapping (FileNotFoundError → operator error) already proven in `cli._discover_tools_for_run`. |
| Scalar-type mapping JSON-Schema → Python | New table | Lift the table from `cli._format_param_signature` (lines 918-925), extend it | Existing baseline; tested under `tests/framework/unit/test_list_tools_format.py`. The walker needs `required`/`default` semantics on top, but the type table is the same. |
| PEP 681 dataclass-transform plumbing for pyright | Wiring `@dataclass_transform` on a custom metaclass | Pydantic v2 ships this natively — pyright sees generated `BaseModel` subclasses correctly | `[CITED: peps.python.org/pep-0681, github.com/microsoft/pyright/discussions/1782]`. |

**Key insight:** Phase 17's job is the *narrow* JSON-Schema-to-Pydantic translation locked by D-02, plus the file-emission/idempotency/CLI plumbing locked by D-03/D-08. Every other surface (config loading, MCP handshake, schema-validity check, scalar type map, type-checker integration) already exists in the repo or in a transitive dep. The walker should be the only meaningfully-new code.

## Runtime State Inventory

Not applicable — Phase 17 is greenfield. No rename, refactor, or migration. The only "state" that exists *after* this phase is the contents of `src/mcp_test_framework/sdet/generated/` which is wiped and rewritten by every `gen-sdet-classes` run (D-03). All other files Phase 17 creates are net-new (`sdet/__init__.py`, `sdet/response.py`, `sdet/_codegen.py`, `sdet/_tool_factory.py`, the new CLI command, the test files).

The one "state" question worth flagging: should `generated/.gitkeep` ship in source control, and should `generated/<slug>/` be in `.gitignore`? **Recommendation:** ship `.gitkeep`, do NOT gitignore `generated/<slug>/`. The generated files are part of the import surface; committing them gives operators a working `tests/sdet/` after a fresh `git clone` without forcing them to run `gen-sdet-classes` first. Operators who want to refresh re-run the command. Phase 21 docs will spell this out.

## Common Pitfalls

### Pitfall 1: Generated files break under `from __future__ import annotations` if the Response class references a typed field that hasn't been resolved

**What goes wrong:** Pydantic 2.10 introduced a known regression: `from __future__ import annotations` plus a `BaseModel` with forward references (including nested models or unresolved class names) raises `PydanticUserError: Model is not fully defined`. `[CITED: github.com/pydantic/pydantic/issues/11004]`

**Why it happens:** Pydantic v2 evaluates annotations at class creation time when `from __future__ import annotations` makes everything a string. Self-referential or forward-referential models need `model_rebuild()`.

**How to avoid:**
1. **D-02 already eliminates the worst case** — no `$ref` or recursive schemas means no forward references between generated classes.
2. **Emit each `<Tool>Params` / `<Tool>Response` as a self-contained class** with all dependencies resolved at definition time. If a property needs a nested object, emit the nested model *above* the parent in the same file.
3. **Smoke-test by importing every generated file in `tests/framework/unit/test_codegen_emitter.py`** — `from mcp_test_framework.sdet.generated.<slug>.create_vm import CreateVmParams; CreateVmParams.model_json_schema()`. If a forward-ref ever sneaks in (e.g. a future v1.4 enum/union expansion), this test catches it before pyright does.

**Warning signs:** `PydanticUserError: Class CreateVmParams is not fully defined; you should define ..., then call CreateVmParams.model_rebuild()`.

### Pitfall 2: Tool names that aren't valid Python identifiers crash on import

**What goes wrong:** A tool named `2nd-attempt`, `import`, or `os.getcwd` slug-collides or produces an invalid module name. Importing the generated `<slug>/__init__.py` raises `SyntaxError`.

**Why it happens:** MCP only constrains tool names to be non-empty strings (the wire protocol doesn't restrict character set). Tool authors using kebab-case or numeric prefixes are not violating spec.

**How to avoid:**
1. `_module_name()` sanitizes (lowercase, non-`[a-z0-9_]` → `_`, leading-digit guard, keyword guard with `_` suffix).
2. `_pascal_case()` applies parallel sanitization for class names.
3. **Test the homelab-mcp tool-name set** as a fixture (see Pattern 2 testing guidance). Add 4–5 adversarial synthetic names (`import`, `2fa-verify`, `class`, `os.path.join`, `__init__`) to the unit test for `_pascal_case` / `_module_name`.

**Warning signs:** `ModuleNotFoundError: No module named 'mcp_test_framework.sdet.generated.foo.2nd_attempt'` at test-collection time.

### Pitfall 3: `extra="forbid"` on Params blocks legitimate Pydantic kwargs

**What goes wrong:** Operator does `CreateVmParams(name="x", cpu=2)` — typo'd `cpu` instead of `cpus`. With `extra="forbid"`, Pydantic raises `ValidationError: Extra inputs are not permitted [type=extra_forbidden]` — *good*. But the same `extra="forbid"` would also reject Pydantic's own special kwargs if you ever added a `model_validate` round-trip with extra metadata. Stay aware.

**Why it happens:** `extra="forbid"` is on the model_config, which applies to *all* construction paths.

**How to avoid:**
1. Only set `extra="forbid"` on Params, not Response (D-07/D-06).
2. If a future phase needs to round-trip params through a wire serializer that adds metadata, route through `model_dump()` (which strips metadata) before constructing the next Pydantic stage.

**Warning signs:** `ValidationError: Extra inputs are not permitted` for a kwarg the operator believes is valid.

### Pitfall 4: pyright runs against the whole codebase and fails on pre-existing v1.0–v1.2 type debt

**What goes wrong:** A naive `pyright` invocation in the typecheck test walks all of `src/` and surfaces unrelated type errors from `_runner.py` / `ollama_judge.py` / etc.

**Why it happens:** pyright's default include-set is the project root.

**How to avoid:**
1. Scope via `[tool.pyright]` in `pyproject.toml`:
   ```toml
   [tool.pyright]
   include = ["src/mcp_test_framework/sdet/generated"]
   strict = ["src/mcp_test_framework/sdet/generated"]
   pythonVersion = "3.14"
   ```
2. The test invokes pyright as a subprocess with explicit path argument: `subprocess.run(["pyright", "src/mcp_test_framework/sdet/generated/<fixture_slug>/"], check=False)` — does not inherit ambient include-set surprises.
3. Use a **synthetic fixture server** for the typecheck test, not live homelab-mcp. The test fixture emits a deterministic 3–5 tool set covering the supported constructs + 1 degraded path. Live homelab-mcp drift is not allowed to break the type-check gate.

**Warning signs:** pyright surfaces errors in files outside `generated/` — config is wrong.

### Pitfall 5: Wipe-and-write races with editor watchers / pyright daemon

**What goes wrong:** Operator runs `gen-sdet-classes` while VSCode + pyright-language-server is watching `generated/`. The `rmtree` followed by fresh writes can momentarily produce a half-state where some `from X import Y` lines in `__init__.py` point at not-yet-rewritten files.

**Why it happens:** Filesystem operations aren't atomic across multiple file writes.

**How to avoid:**
1. **Write order:** emit all per-tool files first, *then* emit `__init__.py` last. The `__init__.py` is the last thing to land, so any partial state has `__init__.py` referencing the *old* (already-deleted) set, not a partial new set. With `shutil.rmtree(...) ; mkdir(...) ; <files> ; __init__.py`, the window is: empty dir → all-files-present-no-init → fully-present. An import during the middle stage fails with `ModuleNotFoundError: No module named '<slug>'` — clean failure, no half-imports.
2. **Alternative (planner's call):** write to `generated/<slug>.tmp/` then `os.replace` (atomic on POSIX, near-atomic on Windows NTFS) at the end. Adds complexity; the ordering trick above is simpler and adequate for the operator-runs-codegen-then-runs-tests workflow.

**Warning signs:** Sporadic `ImportError` only when an editor is actively running pyright in the background — a strong signal of a race.

### Pitfall 6: `serverInfo.name` is set to a generic placeholder

**What goes wrong:** Some MCP servers ship with `serverInfo.name = "mcp-server"` or even an empty string. Two different servers slug to the same `mcp_server` and collide.

**Why it happens:** Server authors don't always set a descriptive name.

**How to avoid:**
1. D-05 explicitly errors loud on empty/missing/collision — implement that as a clean operator error message:
   ```
   gen-sdet-classes: server identification failed

   the configured MCP server reports serverInfo.name=<empty string>.
   gen-sdet-classes needs a non-empty name to choose an output directory.

   command: <cfg.mcp_server.command> <args>

   fix: ask the server author to set a name in their server's
   `ServerInfo(name="...", version="...")` initialization, or pin a slug
   via your MCP server's own configuration (this cannot be set framework-side).
   ```
2. Document this in Phase 21's authoring docs.

**Warning signs:** Collision shows up at slugify time, before any files are written. Loud fail with the colliding command name in the message.

### Pitfall 7: `CallToolResult.content` is heterogeneous; `.text` accumulation must handle non-text blocks

**What goes wrong:** `.text` is defined as "concatenated `TextContent.text`". But `CallToolResult.content` is `list[TextContent | ImageContent | AudioContent | ResourceLink | EmbeddedResource]` `[VERIFIED: uv run python -c "..."]`. Naive concatenation crashes on `ImageContent` (no `.text` attr).

**Why it happens:** MCP responses can mix media. The `ToolResponse.text` accessor needs to filter.

**How to avoid:** Filter on `isinstance(block, TextContent)` (or `getattr(block, "type", None) == "text"`):
```python
@computed_field
@property
def text(self) -> str:
    return "".join(
        b.text for b in self.raw.content
        if isinstance(b, TextContent)
    )
```
Pin in `tests/framework/unit/test_tool_response.py` — fixture with mixed content blocks.

**Warning signs:** `AttributeError: 'ImageContent' object has no attribute 'text'` at test runtime.

### Pitfall 8: `.data` JSON-parse fallback masks server errors

**What goes wrong:** CODEGEN-04 fallback chain: `structuredContent` → JSON-parse of first `TextContent` → `{"text": <concat>}`. A server that returns `isError=True` with an error message in `TextContent` would have its error message JSON-parsed (and likely succeed if it looks like JSON, or fall through to `{"text": "<error msg>"}`). Either way, the operator's `.data["..."]` access succeeds against an error payload — a false negative.

**Why it happens:** `.data` doesn't branch on `.is_error`.

**How to avoid:**
1. CODEGEN-04 spec is silent on this — Phase 17 implements the literal fallback chain. The *typed error* surfacing (`ToolCallError` raised when `isError=True`) is Phase 18 (UI-02 in REQUIREMENTS.md).
2. Document in `ToolResponse.data` docstring: "*does not* check `is_error`. Test code that needs to distinguish error payloads should check `.is_error` first or use Phase 18's `tool().call()` which raises `ToolCallError` on `isError=True`."
3. Pin a test in `test_tool_response.py` that an error-payload `CallToolResult` still produces a non-None `.data` (the spec'd behavior — Phase 17 does not change this).

**Warning signs:** None — this is intentional. Surfacing the issue here so the Phase 17 reviewer doesn't add an unsanctioned `if self.is_error: return None` to `.data`.

## Code Examples

### Example 1: ToolResponse base (`src/mcp_test_framework/sdet/response.py`)

```python
"""ToolResponse base — uniform .raw / .data / .text / .is_error per CODEGEN-04.

Location locked by Phase 17 CONTEXT D-07. Pydantic v2 BaseModel with
@computed_field properties (lazy evaluation). Subclasses inherit the
accessors and may add typed fields (Phase 17 codegen) or be stubs
(class FooResponse(ToolResponse): pass, D-06).
"""
from __future__ import annotations

import json
from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, ConfigDict, computed_field


class ToolResponse(BaseModel):
    """Uniform response surface for every MCP tool, regardless of outputSchema.

    Subclasses generated by `gen-sdet-classes` either add typed fields
    (when outputSchema is declared) or are stubs (when undeclared).
    """

    # arbitrary_types_allowed: CallToolResult is a Pydantic model from `mcp`
    # but the v2 type-check insists on this for "external" Pydantic models.
    model_config = ConfigDict(arbitrary_types_allowed=True)

    raw: CallToolResult

    @computed_field
    @property
    def is_error(self) -> bool:
        """Mirror of raw.isError (CODEGEN-04)."""
        return self.raw.isError

    @computed_field
    @property
    def text(self) -> str:
        """Concatenated TextContent.text across all content blocks.

        Non-TextContent blocks (Image/Audio/ResourceLink/EmbeddedResource)
        are silently skipped — see Pitfall 7 in 17-RESEARCH.md.
        """
        return "".join(
            b.text for b in self.raw.content
            if isinstance(b, TextContent)
        )

    @computed_field
    @property
    def data(self) -> dict[str, Any] | None:
        """Best-effort dict view per CODEGEN-04 fallback chain.

        Order:
          1. raw.structuredContent if present
          2. JSON-parse of first TextContent.text (silently swallows ParseError)
          3. {"text": <concatenated text>} if any text content exists
          4. None

        Note: does NOT check is_error. Phase 18's tool().call() raises
        ToolCallError on isError=True; .data here returns whatever payload
        the server sent.
        """
        if self.raw.structuredContent is not None:
            return self.raw.structuredContent
        # Look for first TextContent and try to JSON-parse.
        for block in self.raw.content:
            if isinstance(block, TextContent):
                try:
                    parsed = json.loads(block.text)
                except (json.JSONDecodeError, ValueError):
                    parsed = None
                if isinstance(parsed, dict):
                    return parsed
                break  # only try the first TextContent (CODEGEN-04 spec)
        # Fallback to {"text": <concat>} if any text exists.
        concat = self.text
        if concat:
            return {"text": concat}
        return None
```

### Example 2: Walker entry point (`src/mcp_test_framework/sdet/_codegen.py` excerpt)

```python
"""JSON-Schema → Pydantic v2 source emission. Hand-rolled per Phase 17 D-01.

Coverage promise per D-02:
  - string / integer / number / boolean → scalars
  - object (with properties + required) → nested BaseModel
  - array (with scalar items) → list[<scalar>]
Anything else → typing.Any with a "# codegen: degraded — <reason>" comment.
"""
from __future__ import annotations

import datetime as _dt
import shutil
import textwrap
from dataclasses import dataclass
from pathlib import Path

from jsonschema.validators import Draft202012Validator, validator_for
from mcp.types import Tool

from mcp_test_framework.sdet._slugs import pascal_case, module_name, server_slug


HEADER = """\
# AUTOGENERATED by mcp-test-framework gen-sdet-classes -- DO NOT HAND-EDIT.
# Source: {slug} (serverInfo.name={server_name!r}, version={server_version!r})
# Regenerated: {timestamp}
# Extend by subclassing in tests/sdet/, not by editing this file.
"""


@dataclass(frozen=True)
class FieldSpec:
    py_type: str
    default: str        # "..." for required, repr(default) otherwise
    degrade: str | None  # "# codegen: degraded — <reason>" comment text, or None


def generate(
    *,
    server_name: str,
    server_version: str,
    tools: list[Tool],
    out_root: Path,
) -> dict[str, int]:
    """Wipe-and-write generated/<server_slug>/. Returns counts for the digest.

    Phase 17 D-03: shutil.rmtree(target) -> mkdir -> write per-tool files
    -> write __init__.py last (so partial-write race fails clean, not half-imported).
    """
    slug = server_slug(server_name)  # raises if empty/invalid
    target = out_root / slug
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)

    timestamp = _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds")
    counts = {"tools": 0, "degraded_fields": 0}

    sorted_tools = sorted(tools, key=lambda t: t.name)
    registry_entries: list[tuple[str, str]] = []   # (tool_name, class_basename)

    for tool in sorted_tools:
        rendered, degraded_n = _render_tool_file(
            tool=tool, slug=slug, server_name=server_name,
            server_version=server_version, timestamp=timestamp,
        )
        (target / f"{module_name(tool.name)}.py").write_text(rendered, encoding="utf-8")
        counts["tools"] += 1
        counts["degraded_fields"] += degraded_n
        registry_entries.append((tool.name, pascal_case(tool.name)))

    # Write __init__.py LAST so partial states fail clean (Pitfall 5).
    (target / "__init__.py").write_text(
        _render_init(slug, server_name, server_version, timestamp, registry_entries),
        encoding="utf-8",
    )
    return counts
```

### Example 3: CLI command (`src/mcp_test_framework/cli.py` addition)

```python
@app.command("gen-sdet-classes")
def gen_sdet_classes(
    config: Path | None = typer.Option(
        None,
        "--config",
        help=(
            "Path to a YAML config (overrides MCPTF_CONFIG_FILE and "
            "./config.yaml autodiscovery)."
        ),
    ),
) -> None:
    """Generate typed Pydantic Params/Response classes for every tool the MCP server advertises (CODEGEN-01).

    Writes to src/mcp_test_framework/sdet/generated/<server_slug>/.
    Wipe-and-write: rerunning replaces the directory wholesale.
    Honors --config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud
    (Phase 13 SAFE-01..07).
    """
    cfg = _load_config(config)  # SAFE-03 applies — fail-loud is correct here
    assert cfg is not None
    try:
        with asyncio.Runner() as runner:
            counts = runner.run(_run_codegen(cfg))
    except KeyboardInterrupt:
        raise typer.Exit(code=130)
    except FileNotFoundError as exc:
        # Mirror list-tools failure-mode parity (cli.py:list_tools FileNotFoundError branch).
        _emit_operator_error(
            summary=f"MCP server command not found: {cfg.mcp_server.command!r}",
            detail=[f"the launch attempt raised: {exc}"],
            next_step=(
                "update mcp_server.command/args in your config.yaml so "
                "the launch command resolves on PATH"
            ),
        )
    # Render the one-line-per-tool digest (Phase 16 aesthetic).
    _render_codegen_digest(counts)


async def _run_codegen(cfg: Config) -> dict[str, int]:
    """Open one-shot McpTestClient, read serverInfo + tools, hand to walker."""
    async with AsyncExitStack() as stack:
        client = await stack.enter_async_context(
            McpTestClient(
                cfg.mcp_server.command,
                cfg.mcp_server.args,
                cfg.mcp_server.timeout_seconds,
            )
        )
        # client._session.initialize() already ran in __aenter__.
        # We need serverInfo back out — access via the SDK's stored
        # `_initialize_result` attr OR re-call initialize (planner choice).
        # See Open Question #1.
        server_info = client._session._initialize_result.serverInfo  # type: ignore[attr-defined]
        tools = await client.list_tools()
    from mcp_test_framework.sdet import _codegen
    from pathlib import Path
    out_root = Path(__file__).parent / "sdet" / "generated"
    return _codegen.generate(
        server_name=server_info.name,
        server_version=server_info.version,
        tools=tools,
        out_root=out_root,
    )
```

### Example 4: CLI digest output (matching Phase 16 `_render_pre_run_digest` aesthetic)

```
========================================
MCP Test Framework — gen-sdet-classes
========================================
MCP server:  homelab-mcp
Server:      homelab-mcp v0.5.2
Target:      src/mcp_test_framework/sdet/generated/homelab_mcp/
Tools:       72 generated
Degraded:    14 fields (use grep "codegen: degraded" for details)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic-mypy plugin | Native pyright via `@dataclass_transform` (PEP 681) | PEP 681 ratified 2022; widely adopted by 2023 | No plugin to pin; pyright handles Pydantic v2 BaseModel natively in strict mode. `[CITED: peps.python.org/pep-0681, docs.pydantic.dev/latest/integrations/visual_studio_code/]` |
| Hand-rolled `subprocess.Popen` MCP launches | `mcp` SDK's `stdio_client` context manager | MCP SDK 1.x | Already in use via `McpTestClient`; codegen reuses it. |
| `dataclasses` for typed shapes | Pydantic v2 BaseModel for runtime + static validation | Pydantic v2 released 2023 | The framework's existing convention; codegen continues it. |
| `python-dotenv` for layered config | `pydantic-settings` (built-in dotenv + yaml + env-var sources) | pydantic-settings 2.x | Already in use via `Config(BaseSettings)`; `gen-sdet-classes` inherits via `_load_config`. |

**Deprecated/outdated:** None Phase 17 needs to avoid. The Pydantic v1 → v2 migration is fully done in this repo (verified — `extra="forbid"`, `model_config = ConfigDict(...)`, `@field_validator(..., mode="after")` patterns throughout `config.py` / `models.py`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ClientSession._initialize_result.serverInfo` is the accessible path for `serverInfo.name` after `__aenter__` | Example 3 / Open Question #1 | If the attribute is private/renamed, codegen can't read `serverInfo.name` without a second `initialize()` call. **Mitigation:** Open Question #1 — planner should verify via `dir(client._session)` and prefer a public path if one exists, else add a public accessor to `McpTestClient`. `[ASSUMED]` based on common SDK patterns; not verified in this session against the 1.27.0 source. |
| A2 | Generated files without `$ref` / forward refs are safe under `from __future__ import annotations` in Pydantic 2.13 | Pitfall 1, Pattern 3 | The known Pydantic 2.10 regression `[CITED: github.com/pydantic/pydantic/issues/11004]` was about forward-refs; D-02's no-`$ref` rule eliminates the forward-ref case. **Mitigation:** the import-everything smoke test in Pitfall 1's "How to avoid" catches any future regression. |
| A3 | pyright in strict mode, scoped to `generated/`, will accept the emitted Pydantic v2 classes with zero errors | D-04, Pitfall 4 | pyright might flag the `@computed_field @property` chain or specific Field default patterns. **Mitigation:** wave-0 smoke test running pyright against a small fixture-generated module *before* the full walker is implemented surfaces this early. `[ASSUMED]` based on Pydantic+pyright native support; pin via the typecheck test in v1.3. |
| A4 | The `homelab-mcp` tool set produces no slug/PascalCase collisions under the proposed sanitization | Pattern 2 | If two tools differ only in non-identifier chars, they'd collide. **Mitigation:** unit test capturing the live tool-name set asserts no collisions. `[ASSUMED]` based on typical naming conventions; cheap to verify. |

## Open Questions

1. **How does codegen read `serverInfo.name` from the open `McpTestClient`?**
   - What we know: `ClientSession.initialize()` returns an `InitializeResult` with `.serverInfo.name` and `.serverInfo.version`. `McpTestClient.__aenter__` calls `session.initialize()` (line 171 of `mcp_client.py`) but does NOT store the result.
   - What's unclear: whether `mcp.ClientSession` retains the result on `._initialize_result` (used in Example 3 with a `# type: ignore`) or whether codegen needs a second `initialize()` call.
   - Recommendation: **add a public accessor to `McpTestClient`** as a one-line Phase 17 change: capture `self._initialize_result = await session.initialize()` in `__aenter__` and expose `server_info` as a property. Avoids the private-attr access in `_run_codegen`. Tested by an existing or new `test_mcp_client.py` case.

2. **Where exactly does the `tool(name)` factory's per-server registry get registered at test runtime?**
   - What we know: Phase 18 owns the runtime side. Phase 17 ships the generated `_REGISTRY` dict in `generated/<slug>/__init__.py`.
   - What's unclear: whether `tool(name)` discovers the registry implicitly (auto-import the single `<slug>/` directory under `generated/`) or whether Phase 18's `mcp_session` fixture explicitly registers it.
   - Recommendation: Phase 17 ships the registry in the generated `__init__.py` as a public constant `_REGISTRY: dict[str, tuple[type, type[ToolResponse]]]`. The mechanism by which the factory finds it — auto-discovery vs explicit registration — is Phase 18's call. Phase 17 documents the constant's name as the stable seam.

3. **Should the test fixture for the pyright typecheck mock the MCP server, or use a deterministic synthetic schema fixture?**
   - What we know: Live homelab-mcp drift cannot be allowed to break the gate.
   - What's unclear: whether to spin up a fake stdio MCP server (heavy) or feed synthetic `Tool` objects directly into `_codegen.generate(...)` (light).
   - Recommendation: feed synthetic `Tool` objects directly. The walker is the unit under test; the wire path isn't. Plan a separate `test_gen_sdet_classes_cli.py` that DOES exercise the full path against a minimal synthetic stdio server (homelab-mcp is too heavy a dep; perhaps a fixture server in `tests/_fixtures/`).

4. **Should the digest's "Degraded: N fields" count include a sample of which tools have the most degraded fields?**
   - What we know: bounded height per CONTEXT.md §Specifics + Phase 16 aesthetic.
   - What's unclear: whether the operator wants a single number or a sorted top-3.
   - Recommendation: single number + `grep "codegen: degraded" generated/<slug>/` hint. Matches the `--explain`-as-expansion convention of Phase 16. Operator-facing nicety is fine to defer to v1.4 if homelab-mcp's degraded count is small.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | Runtime | ✓ | 3.14 (pinned) | — |
| `uv` | Project mgmt | ✓ (project already uses it) | — | — |
| `mcp` Python SDK | Phase 17 codegen handshake | ✓ | 1.27.0 (in venv) `[VERIFIED: uv pip show mcp]` | — |
| `pydantic` v2 | Generated class base | ✓ | 2.13.x (pinned in pyproject) | — |
| `jsonschema` | Pre-flight check | ✓ | 4.26+ (pinned) | — |
| `typer` (via `mcp[cli]`) | CLI registration | ✓ | bundled with mcp[cli] | — |
| `pyright` | NEW — typecheck test | ✗ (not yet in dev deps) | 1.1.409 (latest 2026-04-23) | None — D-04 requires it. Add to `[dependency-groups].dev`. |
| MCP server binary (e.g. `homelab-mcp`) | Integration tests | ✓ (operator-supplied via PATH) | per operator | If absent, `gen-sdet-classes` errors via existing `FileNotFoundError` → operator-error mapping. Unit tests use synthetic Tool fixtures and do not need a live server. |

**Missing dependencies with no fallback:** `pyright` — must be added to `[dependency-groups].dev` as part of Phase 17 Plan 0 or Plan 1 (Wave 0).

**Missing dependencies with fallback:** None.

## Project Constraints (from CLAUDE.md)

These project directives constrain Phase 17 implementation:

- **Python 3.14 + uv** — Python pinned in `.python-version`, deps via `uv`. Don't introduce alternative package managers.
- **MCP transport stdio-only** — `gen-sdet-classes` uses `McpTestClient` (which wraps `mcp.client.stdio.stdio_client`). No raw `subprocess.Popen`.
- **Black-box rule** — Codegen reads only the MCP wire-protocol surface (`Tool.inputSchema`, `Tool.outputSchema`, `Tool.description`, `serverInfo.name`). NEVER import from homelab-mcp source. Ruff's `TID251` + `tests/conftest.py`'s `sys.modules` guard enforce this.
- **Async + `asyncio.timeout`** — Codegen handshake runs via `asyncio.Runner` + `AsyncExitStack`-owned `McpTestClient` (Phase 4.1 same-task lifecycle pattern). `McpTestClient` already wraps every SDK call in `asyncio.timeout(self._timeout_seconds)`.
- **Pydantic v2 everywhere** — Existing pattern; generated classes continue it. `model_config = ConfigDict(...)` for per-class settings.
- **`extra="forbid"` for input shapes** — Apply to generated `Params` (D-07 + Claude's Discretion recommend); NOT to `Response`.
- **One module per concern** — Codebase has narrow modules; Phase 17 follows: `sdet/response.py` (base), `sdet/_codegen.py` (walker), `sdet/_tool_factory.py` (factory). Underscore-prefixed = framework-internal.
- **`from __future__ import annotations`** — Top of every src module. Generated files inherit the convention.
- **UTF-8 source, ASCII identifiers** — Generated files use plain ASCII identifiers (`_module_name()` strips non-`[a-z0-9_]`); docstrings can use UTF-8.
- **Test surface split (Phase 15)** — Phase 17 tests live under `tests/framework/unit/test_codegen_*.py`. The generated module under `src/.../sdet/generated/` is production code, not test code.
- **CONTEXT.md Phase 13 SAFE-01..07 config precedence** — `gen-sdet-classes` is subject to `--config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud`. Reuse `_load_config(path)`.
- **GSD workflow** — File-modifying tools must be entered through a GSD command; phase work via `/gsd-execute-phase`.

## Sources

### Primary (HIGH confidence)

- **Local verification:**
  - `uv pip show mcp` → mcp 1.27.0 in venv
  - `uv run python -c "from mcp.types import CallToolResult, Tool; print(...)"` → confirmed `CallToolResult.model_fields` = `['meta', 'content', 'structuredContent', 'isError']` and `Tool.model_fields` includes `inputSchema`, `outputSchema`
  - `curl https://pypi.org/pypi/pyright/json` → latest 1.1.409, released 2026-04-23
  - `curl https://pypi.org/pypi/datamodel-code-generator/json` → latest 0.57.0, released 2026-05-07
- **Existing codebase:**
  - `src/mcp_test_framework/mcp_client.py:106-210` — McpTestClient lifecycle pattern
  - `src/mcp_test_framework/schema_validator.py:34, 124` — Draft202012Validator + validator_for pattern
  - `src/mcp_test_framework/cli.py:171, 283, 610, 901` — _load_config, _discover_tools_for_run, list_tools, _format_param_signature
  - `src/mcp_test_framework/config.py` — Pydantic settings + frozen + extra="forbid" patterns
  - `src/mcp_test_framework/_runner.py:732` — _render_pre_run_digest aesthetic (Phase 16)
- **Pydantic v2 docs:** https://docs.pydantic.dev/latest/concepts/fields/ — `@computed_field` + `@property` for pyright strict-mode type inference
- **PEP 681:** https://peps.python.org/pep-0681/ — `dataclass_transform` (the mechanism pyright uses to understand Pydantic v2)

### Secondary (MEDIUM confidence)

- https://docs.pydantic.dev/latest/integrations/visual_studio_code/ — VS Code + pyright + Pydantic v2 native support (no plugin)
- https://docs.pydantic.dev/latest/concepts/forward_annotations/ — `from __future__ import annotations` + `model_rebuild()` semantics
- https://github.com/microsoft/pyright/discussions/1782 — confirmation pyright handles dataclass-like libraries natively
- https://github.com/pydantic/pydantic/issues/11004 — known regression in Pydantic 2.10+ with `from __future__ import annotations` (resolved in subsequent patches; Phase 17 pins to 2.13)

### Tertiary (LOW confidence)

- Assumption A1 — `ClientSession._initialize_result` attribute name. Open Question #1 flags planner-side verification.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every version verified live against PyPI/venv; no new runtime deps
- Architecture: HIGH — locked by CONTEXT.md D-01..D-09; research only confirms technical soundness and surfaces mechanics
- Pitfalls: HIGH — drawn from Pydantic v2 known regressions (cited), Python identifier rules (stdlib `keyword`), MCP type definitions (verified), and the existing codebase patterns
- Open questions: MEDIUM — three of four have clear recommendations; #1 requires a small live SDK inspection during planning

**Research date:** 2026-05-12
**Valid until:** 2026-06-11 (30 days; the stack is stable — pydantic 2.13, mcp 1.27, pyright 1.1.409 are all current releases)
