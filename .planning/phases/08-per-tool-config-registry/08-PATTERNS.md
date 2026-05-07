# Phase 08: Per-tool config registry - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 9 (3 source modifies, 1 source add, 2 test modifies, 1 test possibly modifies, 1 example yaml, 1 changelog optional)
**Analogs found:** 9 / 9 (every target file has a strong, in-tree analog cited by CONTEXT.md)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/models.py` (ADD `ToolConfig`) | model (pydantic sub-model) | transform / validation | `models.py` `OllamaConfig` / `McpServerConfig` / `TargetConfig` (lines 27-89) | exact — same module, same role, same shape |
| `src/mcp_test_framework/config.py` (ADD `version`, `tools` fields) | config | transform / validation | `config.py` `Config` (lines 149-194) | exact — extending the same class |
| `src/mcp_test_framework/rubrics.py` (ADD `id: ClassVar[str]` + resolver) | model (rubric registry) | transform / lookup | `rubrics.py` `Rubric` + 3 subclasses (lines 44-95) | exact — same module, additive class field |
| `src/mcp_test_framework/cli.py` (ADD `config-init` subcommand) | CLI command | request-response (subprocess + stdout) | `cli.py` `list-tools` (lines 134-205) | exact — same Typer app, same async-subprocess pattern |
| `src/mcp_test_framework/fixtures.py` (per-test judge guards via fixture/decorator/inline) | test fixture | event-driven (test-entry guard) | `fixtures.py` `target_tool` (lines 353-368) + `_preflight` `pytest.exit` (lines 115-123) | role-match — guard + fixture-request idiom |
| `tests/test_mcp_tool_contract.py` (TEST-08/09/10 thread `call_arguments`; TEST-05/06/07 judge guards) | test (integration) | request-response | TEST-05 / TEST-08 in-place (lines 99-181) | exact — modifying the same test bodies |
| `tests/conftest.py` (lift `_discover_tools` for CLI reuse — CD-08) | test config | event-driven (collection) | `conftest.py` `_discover_tools` + `_resolve_tool_names` (lines 68-121) | exact — moving existing helper |
| `config.example.yaml` (add `version: 1` + worked `tools:` block) | example config | n/a (data) | existing `config.example.yaml` (1-21) | exact — appending to same file |
| `docs/CHANGELOG.md` (Phase 08 entry, if convention) | docs | n/a | n/a — confirm convention with planner | n/a |

---

## Pattern Assignments

### `src/mcp_test_framework/models.py` — ADD `ToolConfig` (model, transform/validation)

**Analog:** `src/mcp_test_framework/models.py` `TargetConfig` (lines 67-89) — closest match because it (a) lives in the same module, (b) uses an `Optional[str]` field with a `field_validator(mode="before")`, mirroring what `judges` and `skip_reason` will need, (c) carries the locked `ConfigDict(frozen=True, populate_by_name=True)` shape.

**Imports / module header pattern** (models.py lines 20-24):
```python
from __future__ import annotations

from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator
```
Phase 08 will additionally need: `from typing import Any, ClassVar` (only if rubric `id` lands here — see CD-03), and `model_validator` for the cross-field check (D-16: `skip=True` ⇒ non-empty `skip_reason`).

**Sub-model class shape to mirror** (models.py lines 47-64, `McpServerConfig`):
```python
class McpServerConfig(BaseModel):
    """MCP server subprocess configuration."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    command: str = Field(
        default="homelab-mcp",
        validation_alias=AliasChoices("MCP_SERVER_COMMAND", "command"),
    )
    args: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("MCP_SERVER_ARGS", "args"),
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        validation_alias=AliasChoices("MCP_SERVER_TIMEOUT_SECONDS", "timeout_seconds"),
    )
```
**Mirror for `ToolConfig` per D-04, D-05, D-19:**
- `model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")` — note the added `extra="forbid"` (D-05/D-15).
- Fields are plain (NO `validation_alias=AliasChoices(...)`) per D-19 — env routing is intentionally not extended to `tools.*`.
- Field declaration order = D-04 order: `skip`, `skip_reason`, `call_arguments`, `judges`, `setup`, `depends_on`.

**Field validator pattern** (models.py lines 77-89, `TargetConfig._empty_to_none`):
```python
@field_validator("tool_name", mode="before")
@classmethod
def _empty_to_none(cls, v):
    """Empty string from env -> None (Phase 07 D-02 'empty equivalent to None').

    The project's custom _BareNameNestedEnvSource (config.py:91-146) reads
    an env var as present when membership-check passes, regardless of value.
    TARGET_TOOL_NAME='' would land as '' (not None) without this coercion.
    See 07-RESEARCH §Pitfall 2.
    """
    if isinstance(v, str) and v.strip() == "":
        return None
    return v
```
**Mirror for `ToolConfig.judges` (D-17):** `@field_validator("judges", mode="after")` resolves each string against the rubric-ID set; raises `ValueError` listing valid IDs. `mode="after"` because we want post-coercion list[str] inspection.

**Cross-field validator (`model_validator`) pattern — NOT currently in `models.py` but needed for D-16.** Use Pydantic 2 idiom:
```python
from pydantic import model_validator

@model_validator(mode="after")
def _skip_requires_reason(self) -> "ToolConfig":
    if self.skip and not (self.skip_reason and self.skip_reason.strip()):
        raise ValueError("skip=True requires non-empty skip_reason")
    return self
```
(No in-tree analog for `model_validator`; this is the canonical Pydantic 2 shape.)

---

### `src/mcp_test_framework/config.py` — ADD `version: int = 1` and `tools: dict[str, ToolConfig] = {}` (config, transform/validation)

**Analog:** `src/mcp_test_framework/config.py` `Config` class (lines 149-194). Direct in-place extension.

**Top-level `Config` shape to extend** (config.py lines 149-169):
```python
class Config(BaseSettings):
    """Top-level configuration. Frozen for safe session-scoped sharing across async tests."""

    # NOTE: nested-env delimiter intentionally NOT set -- bare env names (per CONTEXT.md
    # lock) are routed to sub-model fields via the custom _BareNameNestedEnvSource below,
    # which honors the validation_alias choices on each sub-model field.
    # See plan-checker iter 1 BLOCKER #1 (resolved Option A) in 01-02-PLAN.md.
    model_config = SettingsConfigDict(
        frozen=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    mcp_server: McpServerConfig = Field(default_factory=McpServerConfig)
    target: TargetConfig = Field(default_factory=TargetConfig)

    # JUDGE_TIMEOUT_SECONDS routes here without an explicit alias because
    # pydantic-settings uppercases top-level field names by default.
    judge_timeout_seconds: int = 120
```

**Two field additions (D-01, D-02):**
- `version: int = 1` — top-level. CD-01 picks: `Field(default=1, ge=1, le=1)` (terse) OR `field_validator("version")` raising the clearer "config version N not supported by this build, expected 1" message. Recommend the explicit validator for diagnostics.
- `tools: dict[str, ToolConfig] = Field(default_factory=dict)` — empty dict is the no-op default. Use `default_factory=dict` (NOT `default={}`) to follow the existing `args: list[str] = Field(default_factory=list, ...)` idiom on `McpServerConfig` (config.py:56-59 — same lesson, mutable defaults).

**`extra="ignore" → "forbid"` decision (CD-02 / D-15):** flip line 160. The `_BareNameNestedEnvSource` (config.py:91-146) does NOT need to change — it iterates `settings_cls.model_fields` and walks fields whose annotation is a `BaseModel` subclass; `tools: dict[str, ToolConfig]` is annotated as `dict`, not `BaseModel`, so the source naturally skips it (D-19 honored automatically).

**Import additions:** add `ToolConfig` to the existing `from mcp_test_framework.models import (...)` block (config.py lines 45-49):
```python
from mcp_test_framework.models import (
    McpServerConfig,
    OllamaConfig,
    TargetConfig,
    ToolConfig,  # NEW (Phase 08 D-01)
)
```

---

### `src/mcp_test_framework/rubrics.py` — ADD `id: ClassVar[str]` + module-level resolver (model, lookup)

**Analog:** existing `Rubric` base + `ClarityRubric` / `DisambiguationRubric` / `ParametersRubric` (lines 44-95).

**Subclass shape to extend** (rubrics.py lines 66-95):
```python
class ClarityRubric(Rubric):
    dimension: str = "clarity"
    dimension_criteria: str = (
        "Does the description clearly explain WHAT the tool does to an LLM "
        ...
    )


class DisambiguationRubric(Rubric):
    dimension: str = "disambiguation"
    dimension_criteria: str = (
        "Does the description help an LLM agent decide WHEN to call this "
        ...
    )


class ParametersRubric(Rubric):
    dimension: str = "parameters_self_explanatory"
    dimension_criteria: str = (
        "For each parameter in the inputSchema (provided as the SUBJECT), "
        ...
    )
```
**Mirror per D-10 + TOOLCFG-04:** add `id: ClassVar[str] = "<id>"` to each subclass (and a typed default on the base if desired). Locked IDs:
- `ClarityRubric.id = "clarity"`
- `DisambiguationRubric.id = "disambiguation"`
- `ParametersRubric.id = "parameters"`

**ClassVar import addition** (currently only `BaseModel, ConfigDict` imported on line 15):
```python
from typing import ClassVar
```
`ClassVar` is required so Pydantic v2 does NOT treat the field as a model field (Pydantic 2 idiom — class-level constants must be `ClassVar` to avoid being declared as instance fields on a `BaseModel`).

**Module-level resolver (CD-03 — recommend in-place over a new module):**
```python
RUBRIC_IDS: frozenset[str] = frozenset({
    ClarityRubric.id,
    DisambiguationRubric.id,
    ParametersRubric.id,
})


def resolve_rubric_id(rubric_id: str) -> type[Rubric]:
    """Map a string ID -> rubric class. Raises ValueError for unknown IDs."""
    for cls in (ClarityRubric, DisambiguationRubric, ParametersRubric):
        if cls.id == rubric_id:
            return cls
    raise ValueError(
        f"unknown rubric id {rubric_id!r}; valid: {sorted(RUBRIC_IDS)!r}"
    )
```
The `ToolConfig.judges` validator (D-17) imports `RUBRIC_IDS` from `rubrics` to validate.

---

### `src/mcp_test_framework/cli.py` — ADD `config-init` subcommand (CLI command, request-response)

**Analog:** `cli.py` `list_tools` command (lines 134-205). Same data flow: `_load_config` → `asyncio.Runner` → `AsyncExitStack`-owned `McpTestClient` → format → stdout. D-24 mandates this exact reuse path.

**Subcommand registration + signature** (cli.py lines 134-176):
```python
@app.command("list-tools")
def list_tools(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Path to a YAML config overlay (sets MCPTF_CONFIG_FILE).",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit tools as a JSON array of full MCP tool records.",
    ),
) -> None:
    """List all tools exposed by the configured MCP server (CLI-02)."""
    cfg = _load_config(config)
    try:
        with asyncio.Runner() as runner:
            tools = runner.run(_list_tools_async(cfg))
    except KeyboardInterrupt:
        raise typer.Exit(code=130)
    if as_json:
        typer.echo(_format_tools_json(tools), nl=False)
    else:
        typer.echo(_format_tools_text(tools))
```
**Mirror for `config_init` per D-21..D-24:**
- Decorator: `@app.command("config-init")` (kebab-case to match existing `list-tools`).
- Signature: `config: Path | None = typer.Option(None, "--config", ...)`, `output: Path | None = typer.Option(None, "--output", "-o", ...)`, `force: bool = typer.Option(False, "--force", ...)`.
- Body: `_load_config(config)` → `with asyncio.Runner() as runner: tools = runner.run(_list_tools_async(cfg))` (REUSE — do not open-code) → format YAML scaffold → write stdout or to `output`.
- `KeyboardInterrupt` → `typer.Exit(code=130)` (preserves the existing SIGINT contract).

**Async helper to reuse verbatim** (cli.py lines 188-205, `_list_tools_async`):
```python
async def _list_tools_async(cfg: Config) -> list[Tool]:
    """Drive the MCP client lifecycle on a single task."""
    async with AsyncExitStack() as stack:
        client = await stack.enter_async_context(
            McpTestClient(
                cfg.mcp_server.command,
                cfg.mcp_server.args,
                cfg.mcp_server.timeout_seconds,
            )
        )
        return await client.list_tools()
```
**`config-init` reuses this directly** — D-24 explicit. Do NOT add a sibling `_discover_tools_async`; `_list_tools_async` already returns full `Tool` records (the YAML scaffold may want descriptions in comments — CD-06).

**Output-mode error pattern** (cli.py lines 79-89, `_load_config`):
```python
if path is not None:
    if not path.is_file():
        typer.echo(f"error: --config path not found: {path}", err=True)
        raise typer.Exit(code=2)
    os.environ["MCPTF_CONFIG_FILE"] = str(path)
    try:
        return Config()
    except Exception:
        os.environ.pop("MCPTF_CONFIG_FILE", None)
        raise
```
**Mirror for `--output PATH` without `--force` when file exists (D-23):**
```python
if output is not None and output.exists() and not force:
    typer.echo(
        f"error: refusing to overwrite existing file: {output} (use --force)",
        err=True,
    )
    raise typer.Exit(code=2)
```

**Discovery-failure hint pattern (D-23 — mirrors 260507-j6i)** — see "Shared Patterns > MCP discovery hint" below.

---

### `src/mcp_test_framework/fixtures.py` — per-test judge guards (CD-05) and `tool_config` fixture (test fixture, event-driven)

**Analog 1 — per-tool fixture shape** (fixtures.py lines 353-368, `target_tool`):
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def target_tool(
    request: pytest.FixtureRequest,
    mcp_client: McpTestClient,
    _preflight,
):
    """Resolve target tool by name (parametrized indirectly via tests/conftest.py)."""
    return await mcp_client.get_tool(request.param)
```
**Mirror for new `tool_config` fixture (test-scope OK; no async needed):**
```python
@pytest.fixture
def tool_config(config: Config, target_tool) -> ToolConfig:
    """Per-test resolution: config.tools.get(<tool name>, ToolConfig())."""
    return config.tools.get(target_tool.name, ToolConfig())
```
This is the seam test bodies request to read `tool_config.call_arguments` (D-11) and to gate on `tool_config.skip` / `tool_config.judges`.

**Analog 2 — sync rubric fixtures** (fixtures.py lines 376-388):
```python
@pytest.fixture(scope="session")
def rubric_clarity() -> ClarityRubric:
    return ClarityRubric()
```
Plain `@pytest.fixture` (no `pytest_asyncio`) since `ToolConfig` construction is sync. Default function scope is intentional — the fixture must reflect the per-test parametrized `target_tool.name`.

**Analog 3 — `pytest.skip(reason=...)` channel.** No existing in-tree call to `pytest.skip`, but the closest cousin is `pytest.exit(...returncode=2)` from `_preflight` (fixtures.py lines 115-123):
```python
pytest.exit(
    f"MCP command {config.mcp_server.command!r} not found on PATH"
    f"\n\nHint: ...",
    returncode=2,
)
```
**Mirror per D-08, D-09, CD-05.** Three viable shapes (CD-05 is planner's call):

1. **Inline at top of test body** (shortest):
   ```python
   async def test_description_clarity(judge, target_tool, rubric_clarity, tool_config):
       if tool_config.skip:
           pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
       if tool_config.judges is not None and "clarity" not in tool_config.judges:
           pytest.skip(reason=f"judge 'clarity' not selected for tool {target_tool.name!r}")
       ...
   ```
2. **Decorator** `@requires_judge("clarity")` — wraps the test, calls `pytest.skip` early. Cleanest if Phase 09's reporter wants a marker handle.
3. **Fixture `_judge_gate`** that requests `tool_config` + a rubric-id via parametrize and `pytest.skip`s in the fixture body.

**No-anyio-cancel-scope-across-yield invariant (Phase 04.1):** every `pytest.skip(...)` MUST fire BEFORE awaiting any session-scoped async fixture's body work. Inline-at-top satisfies this trivially; decorator must skip pre-`await`; fixture must skip in the synchronous setup phase.

---

### `tests/test_mcp_tool_contract.py` — thread `call_arguments` (D-11) + judge guards (D-08/D-09)

**Analog (TEST-08 current shape, lines 170-181):**
```python
async def test_empty_args_call_returns_non_error(
    mcp_client: McpTestClient,
    target_tool,
) -> None:
    """TEST-08: call_tool with {} returns isError=False.

    Per Phase 07 D-06: tools whose inputSchema.required is non-empty produce
    isError=True and fail this test visibly. Phase 08 (TOOLCFG-07) ships the
    user-facing skip mechanism; Phase 07 ships no auto-skip.
    """
    result = await mcp_client.call_tool(target_tool.name, {})
    assert not result.isError, f"call_tool returned isError=True: {result!r}"
```
**Mirror per D-11 (TEST-08, TEST-09, TEST-10 all):**
```python
async def test_empty_args_call_returns_non_error(
    mcp_client: McpTestClient,
    target_tool,
    tool_config: ToolConfig,
) -> None:
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    result = await mcp_client.call_tool(target_tool.name, tool_config.call_arguments)
    assert not result.isError, f"call_tool returned isError=True: {result!r}"
```
Three identical edits at TEST-08, TEST-09, TEST-10 — each gains a `tool_config` fixture request + the same skip-guard prefix + replaces `{}` with `tool_config.call_arguments`.

**Analog (TEST-05 current shape, lines 99-119):**
```python
async def test_description_clarity(
    judge: Judge,
    target_tool,
    rubric_clarity,
) -> None:
    result = await judge.judge(
        str(rubric_clarity),
        subject=target_tool.description,
        context={
            "tool_name": target_tool.name,
            "inputSchema": target_tool.inputSchema,
        },
    )
    assert result.score >= 4, ...
```
**Mirror per D-08:** add `tool_config: ToolConfig` to the signature and a 2-line skip guard at the top:
```python
async def test_description_clarity(
    judge: Judge,
    target_tool,
    rubric_clarity,
    tool_config: ToolConfig,
) -> None:
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    if tool_config.judges is not None and "clarity" not in tool_config.judges:
        pytest.skip(reason=f"judge 'clarity' not selected for tool {target_tool.name!r}")
    result = await judge.judge(...)
    ...
```
Three identical guards on TEST-05 (`"clarity"`), TEST-06 (`"disambiguation"`), TEST-07 (`"parameters"`). If the planner picks decorator-based gating (CD-05), the `tool_config` request still happens in the signature but the skip body lives in the decorator — pick ONE placement and apply uniformly to all six tests.

**Module-level pytestmark stays unchanged** (line 48: `pytestmark = [pytest.mark.asyncio(loop_scope="session")]`) — new fixture requests inherit the loop-scope contract.

---

### `tests/conftest.py` — possibly lift `_discover_tools` for CLI reuse (test config, event-driven)

**Analog (current location, conftest.py lines 65-81):**
```python
_DISCOVERED_TOOL_NAMES: Optional[list[str]] = None


async def _discover_tools(config: Config) -> list[str]:
    """Brief MCP handshake -> list_tools -> tool names. Mirrors fixtures.py:142-148."""
    async with McpTestClient(
        config.mcp_server.command,
        config.mcp_server.args,
        config.mcp_server.timeout_seconds,
    ) as client:
        tools = await client.list_tools()
    return [t.name for t in tools]
```
**CD-08 decision points for the planner:**
1. **Lift unchanged** to `src/mcp_test_framework/_discovery.py` (or similar private module) and re-import from `tests/conftest.py`. CLI's `config-init` imports the same helper.
2. **Don't lift** — `cli.py`'s `_list_tools_async` already does this (returns full `Tool` records, not just names). `config-init` simply uses `_list_tools_async` and projects `[t.name for t in tools]` itself. Recommend **option 2** — `_list_tools_async` already exists, returns richer data the YAML scaffold needs (descriptions for comments per CD-06), and avoids creating a new module just for one helper. The conftest helper stays put.

If option 1 is chosen: the new module needs the same imports (`McpTestClient`, `Config`) and zero pytest-specific code so CLI can import without dragging pytest into the runtime path.

---

### `config.example.yaml` — add `version: 1` + worked `tools:` block

**Analog (current full file, 21 lines):**
```yaml
# config.example.yaml -- copy to config.yaml and set MCPTF_CONFIG_FILE=./config.yaml.
# YAML overlay sits BELOW env in precedence: CLI > env > .env > YAML > defaults.

ollama:
  base_url: http://127.0.0.1:11434
  model: qwen3.6:latest
  timeout_seconds: 120

# Default invocation uses uvx for zero-install. To use a globally-installed
# binary, set command: homelab-mcp and args: [].
mcp_server:
  command: uvx
  args: [homelab-mcp]
  timeout_seconds: 30

target:
  tool_name: list_keyring_credentials

judge_timeout_seconds: 120
```
**Append (per D-01, D-02, <specifics>):**
```yaml
# Phase 08 schema version. Only `1` is accepted by this release.
version: 1

# Per-tool config registry (TOOLCFG-01..07).
# Keys MUST match tool names returned by `mcp-test-framework list-tools`.
tools:
  example_skipped_tool:
    skip: true
    skip_reason: "Requires real keyring; run `mcp-test-framework run -k 'not example_skipped_tool'` to bypass."
  example_judge_subset:
    # Run only the clarity rubric on this tool's description.
    judges: [clarity]
  example_with_args:
    # Provide required arguments so TEST-08/09/10 exercise a non-empty call.
    call_arguments:
      query: "ping"
```
Order/structure follows the existing top-down ordering (most-frequently-edited fields first); commented hints follow the `# Default invocation uses uvx...` precedent already in the file.

---

### `docs/CHANGELOG.md` — Phase 08 entry (if convention exists)

No analog confirmed in this pass. **Planner action:** check `git log` for Phase 06/07 CHANGELOG entries. If a convention exists, follow it; otherwise defer to Phase 10 DOC-04. (No code excerpt to extract.)

---

## Shared Patterns

### `ConfigDict(frozen=True, populate_by_name=True[, extra="forbid"])` on every sub-model
**Source:** `models.py:30, 50, 70` (existing) — every sub-model in this codebase carries this exact triplet.
**Apply to:** `ToolConfig` — adds `extra="forbid"` per D-05.
**Excerpt:** `model_config = ConfigDict(frozen=True, populate_by_name=True)`

### MCP discovery hint string (260507-j6i — keep in sync across spawn sites)
**Source:** `fixtures.py:117-123` AND `tests/conftest.py:113-119` (two copies kept in sync today).
**Apply to:** `cli.py` `config-init` discovery-failure path (D-23).
**Excerpt (canonical):**
```python
msg += (
    f"\n\nHint: {config.mcp_server.command!r} was not found on PATH. "
    "If you intended to use a different command, point "
    "MCPTF_CONFIG_FILE at a config.yaml that defines "
    "mcp_server.command (e.g. `command: uvx, args: [homelab-mcp]`). "
    "The repo ships `config.example.yaml` you can copy and edit."
)
```
**Three-copy hazard:** Phase 08 makes this the third in-tree copy. Planner consideration: extract to a constant in (e.g.) `mcp_client.py` next to the `FileNotFoundError` raise site (line 144-146). Out of scope unless planner prefers; if not, the comment `# Keep in sync with src/mcp_test_framework/fixtures.py:_preflight` MUST be added on the new copy in `cli.py`.

### `AsyncExitStack`-owned `McpTestClient` for ad-hoc spawn sites
**Source:** `cli.py:197-205` (`_list_tools_async`) and `mcp_client.py:147-177` (`__aenter__` body).
**Apply to:** `config-init` REUSES `_list_tools_async` verbatim (D-24 — does NOT open-code `stdio_client`).
**Excerpt:**
```python
async with AsyncExitStack() as stack:
    client = await stack.enter_async_context(
        McpTestClient(
            cfg.mcp_server.command,
            cfg.mcp_server.args,
            cfg.mcp_server.timeout_seconds,
        )
    )
    return await client.list_tools()
```

### `_load_config(config: Path | None) -> Config` shared CLI loader
**Source:** `cli.py:64-89`.
**Apply to:** `config-init` MUST call `_load_config(config)` first (so the CLI surface is uniform with `run` / `list-tools` and so a bad `--config PATH` exits 2 the same way).

### `typer.Exit(code=2)` for CLI configuration / preflight errors; `code=130` for SIGINT
**Source:** `cli.py:82, 171` and `fixtures.py:115` (`pytest.exit(returncode=2)`).
**Apply to:** `config-init` — `code=2` for "refuse to overwrite without --force" and discovery failure; `code=130` for `KeyboardInterrupt` reraise.

### `loop_scope="session"` on async tests + fixtures (Phase 04.1 invariant)
**Source:** `test_mcp_tool_contract.py:48` (`pytestmark = [pytest.mark.asyncio(loop_scope="session")]`) and `fixtures.py:235, 353` (`@pytest_asyncio.fixture(loop_scope="session", scope="session")`).
**Apply to:** any new async fixture for D-08/D-09 guards. The new `tool_config` fixture is sync (`@pytest.fixture`) and inherits no loop scope — fine.

### `pytest.skip(reason=...)` BEFORE any async resource work (Phase 04.1 cancel-scope invariant)
**Source:** principle documented in `fixtures.py:213-215` and elsewhere; no in-tree `pytest.skip` call yet.
**Apply to:** every D-08/D-09 guard. Skip MUST happen before `await judge.judge(...)` or `await mcp_client.call_tool(...)` so no anyio scope is opened on a task that will then unwind.

### `extra="forbid"` for typo defense at load time
**Source:** new in this phase on `ToolConfig` (D-05/D-15). Top-level `Config` flip from `extra="ignore"` to `extra="forbid"` is CD-02 — recommend tighten.
**Apply to:** `ToolConfig` (mandatory) and top-level `Config` (CD-02 — verify no existing fixtures or `config.example.yaml` keys would be rejected).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `docs/CHANGELOG.md` | docs | n/a | Existence of changelog convention not verified in this pass. Planner: check for prior Phase 06/07 entries; if absent, defer to Phase 10 DOC-04. |
| `model_validator(mode="after")` for `ToolConfig._skip_requires_reason` (D-16) | model validator | validation | No `model_validator` (cross-field) usage exists in `models.py` today — only `field_validator`. Pydantic 2 idiom is canonical; no in-tree analog needed. |
| `pytest.skip(reason=...)` test-body call | test guard | event-driven | Codebase has `pytest.exit(returncode=2)` (preflight abort) but no `pytest.skip` calls. Phase 08 introduces this idiom. Pytest's documented pattern is canonical. |

---

## Metadata

**Analog search scope:**
- `src/mcp_test_framework/{models,config,rubrics,cli,fixtures,mcp_client}.py` — existing seams cited by CONTEXT.md `<code_context>`
- `tests/{conftest,test_mcp_tool_contract}.py` — existing test surface and discovery hook
- `config.example.yaml` — existing example config

**Files scanned:** 9 files read in full or in targeted ranges (models.py 1-89, config.py 1-194, rubrics.py 1-95, cli.py 1-256, fixtures.py 100-160 + 340-388, mcp_client.py 100-200, conftest.py 1-137, test_mcp_tool_contract.py 1-234, config.example.yaml 1-21).

**Pattern extraction date:** 2026-05-07
