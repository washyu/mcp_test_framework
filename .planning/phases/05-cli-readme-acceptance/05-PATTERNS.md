# Phase 5: CLI, README & Acceptance - Pattern Map

**Mapped:** 2026-05-06
**Files analyzed:** 5 (1 new, 4 modified/replaced)
**Analogs found:** 4 / 5 (one — `docs/EXTENDING.md` — has no in-repo analog; uses spec doc as structural model)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/cli.py` (NEW) | controller (CLI entry) | request-response (sync wrapper) + async lifecycle (`list-tools`) | `tests/smoke/test_smoke_homelab_mcp.py` (Config + AsyncExitStack body) AND `src/mcp_test_framework/fixtures.py` (owner-task lifecycle) | role-match (test surface vs CLI surface, same scaffold) |
| `pyproject.toml` (MODIFIED) | config | n/a | self (existing `[project.scripts]` commented block) | exact (uncomment in place) |
| `README.md` (REPLACED) | documentation | n/a | `docs/mcp_test_framework_mvp_spec.md` (project doc voice + section structure) | role-match (spec is authoritative; README is quickstart) |
| `docs/EXTENDING.md` (NEW) | documentation | n/a | `docs/mcp_test_framework_mvp_spec.md` (in-repo doc voice / section style); `src/mcp_test_framework/rubrics.py` + `src/mcp_test_framework/judge_protocol.py` for code samples | partial (doc voice + concrete code referents) |
| `.env.example` (VERIFY) | config | n/a | self (already exists, complete) | exact (no edits expected; sync-check against README table only) |

---

## Pattern Assignments

### `src/mcp_test_framework/cli.py` (NEW — Typer controller, request-response + async lifecycle)

**Two analogs feed this file:**
1. `tests/smoke/test_smoke_homelab_mcp.py` — for the `list-tools` body shape (Config + `AsyncExitStack` + `McpTestClient`).
2. `src/mcp_test_framework/fixtures.py` — for the cross-task teardown semantics (Phase 04.1 pattern); the smoke test uses the simpler `async with McpTestClient(...)` shape, which is the recommended shape for `list-tools` since the CLI body is a single task and pytest-asyncio's cross-task finalizer model does NOT apply.

#### Analog A: `tests/smoke/test_smoke_homelab_mcp.py`

**Imports pattern** (lines 21-31):
```python
from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp_test_framework.config import Config
from mcp_test_framework.mcp_client import McpTestClient
```

CLI adaptation: drop `pytest`, `ClientSession`, `StdioServerParameters`, `stdio_client` (don't need raw SDK — use `McpTestClient` only). Add `import json`, `import os`, `import shutil`, `import sys`, `import textwrap`, `from importlib import metadata`, `from pathlib import Path`, `import typer`.

**Core lifecycle pattern** (lines 62-74) — `McpTestClient` lifecycle inside `AsyncExitStack`, exactly the shape `list-tools` body should adopt:
```python
async def test_wrapper_call_tool_returns_non_error_with_content() -> None:
    """SC#2: McpTestClient.call_tool returns isError=False with content or structuredContent."""
    cfg = Config()
    async with McpTestClient(
        cfg.mcp_server.command,
        cfg.mcp_server.args,
        cfg.mcp_server.timeout_seconds,
    ) as client:
        result = await client.call_tool(cfg.target.tool_name, {})
```

**Adaptation for `list-tools`:** swap `client.call_tool(...)` → `client.list_tools()`, wrap entry in `asyncio.Runner` (3.11+) so the CLI controls the event loop directly:
```python
def list_tools(config: Path | None = None, json_out: bool = False) -> None:
    cfg = _load_config(config)
    with asyncio.Runner() as runner:
        tools = runner.run(_list_tools_async(cfg))
    _emit_tools(tools, as_json=json_out)
```
Where `_list_tools_async` is:
```python
async def _list_tools_async(cfg: Config) -> list[Tool]:
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

The `AsyncExitStack` is technically redundant with the single-context `async with McpTestClient(...)` form, BUT use it anyway: it future-proofs against adding a second resource (e.g., a logger handle), it explicitly mirrors the Phase 04.1 ownership lesson, and `__aexit__` semantics are identical.

#### Analog B: `src/mcp_test_framework/fixtures.py` `mcp_client` fixture (lines 175-259)

**This is the CAUTIONARY analog** — DO NOT copy the owner-task + `asyncio.Future` + `asyncio.Event` pattern into the CLI. That pattern exists ONLY because pytest-asyncio drives session fixture teardown from a different task than setup (lines 181-205 docstring). The CLI body runs end-to-end on a single task inside `asyncio.Runner.run(...)`, so the simpler `async with McpTestClient(...)` form (Analog A) is correct.

**What to copy from this analog:** the discipline of holding NO anyio cancel scopes across a yield/await boundary that crosses tasks. In the CLI this is automatic because there are no fixture yields — but the lesson informs the choice of `asyncio.Runner` (single owning task) over a top-level `asyncio.run()` followed by re-entry.

**Reference for the discipline** (lines 176-206):
```python
"""Long-lived McpTestClient session -- pure-asyncio driver + anyio owner task.

The fixture body holds NO anyio cancel scopes across the yield. That was
the failure mode of the prior owner-task + outer ``anyio.create_task_group``
rewrite ...

Fix shape: all anyio scopes (``stdio_client``, ``ClientSession``,
``anyio.fail_after``) live exclusively inside the owner task, which runs
as a stdlib ``asyncio.Task``."""
```

CLI invariant: `McpTestClient.__aenter__` and `__aexit__` happen on the same task (the one inside `asyncio.Runner.run`). KeyboardInterrupt raised at any await inside the runner unwinds that task's stack; `__aexit__` runs; `stdio_client._terminate_process_tree` (per `mcp_client.py:159-169`) kills the subprocess.

#### Config-loading helper (shared between `run` and `list-tools`)

**Analog:** `Config()` instantiation pattern from `tests/smoke/test_smoke_homelab_mcp.py:41` and `src/mcp_test_framework/config.py:172-194`.

**Pattern to apply** (CONTEXT D-discretion: `_load_config` helper):
```python
def _load_config(path: Path | None) -> Config:
    if path is not None:
        if not path.is_file():
            typer.echo(f"error: --config path not found: {path}", err=True)
            raise typer.Exit(code=2)
        os.environ["MCPTF_CONFIG_FILE"] = str(path)
    return Config()  # raises ValidationError on bad YAML/env -- propagate
```

Reference from `config.py` (line 182): `yaml_path = os.environ.get("MCPTF_CONFIG_FILE")` — confirms the env-var seam is what the loader reads.

**Why exit code 2:** matches Phase 4 `_preflight` discipline (`fixtures.py:108-111`) which also uses `pytest.exit(..., returncode=2)` for usage / config errors.

#### `run` command body — pytest delegation pattern

**No direct in-repo analog** (this is the first Python entry point). The pattern is dictated by D-cli-flags-3 + Phase 4 D-markers-3:
```python
import pytest as _pytest

@app.command()
def run(
    config: Path | None = typer.Option(None, "--config", help="YAML overlay path"),
    pytest_args: list[str] = typer.Argument(None, help="Args after `--` forwarded to pytest"),
) -> None:
    cfg = _load_config(config)  # bail early on config errors
    forwarded = list(pytest_args or [])
    raise typer.Exit(code=_pytest.main(["tests", *forwarded]))
```

**Inputs from analogs:**
- `tests/conftest.py` (registered via `pytest_plugins = ["mcp_test_framework.fixtures"]`) — confirms `pytest.main(["tests", ...])` finds the fixtures with no extra `-p` flag.
- `pyproject.toml` line 41: `addopts = "-m 'not live_homelab and not live_ollama'"` — stays untouched; pytest applies it automatically. **Do NOT pass an explicit `-m` flag.**

#### `version` command — `importlib.metadata` pattern

**Analog:** `src/mcp_test_framework/__init__.py:3` — package exposes `__version__ = "0.1.0"` as a fallback. Use `importlib.metadata.version(...)` as the primary source per CONTEXT discretion, fall back to the `__version__` constant on `PackageNotFoundError`:
```python
from importlib import metadata

@app.command()
def version() -> None:
    try:
        v = metadata.version("mvp-test-framework")  # distribution name, not module
    except metadata.PackageNotFoundError:
        from mcp_test_framework import __version__ as v
    typer.echo(v)
```

**Note the distribution-name discrepancy:** `pyproject.toml:2` says `name = "mvp-test-framework"` (M-V-P), but the package and script are `mcp-test-framework` (M-C-P). The `metadata.version` call MUST pass the distribution name (`mvp-test-framework`), not the script name. Comment this in the code.

#### `list-tools` text-output formatting pattern

**No in-repo analog** for terminal text-output; CONTEXT discretion locks `textwrap` + `shutil.get_terminal_size()`. Pattern:
```python
import shutil
import textwrap

def _format_tools_text(tools: list[Tool]) -> str:
    width = max(40, shutil.get_terminal_size((80, 20)).columns)
    sorted_tools = sorted(tools, key=lambda t: t.name)
    blocks: list[str] = []
    for t in sorted_tools:
        desc = textwrap.fill(t.description or "", width=width - 2,
                              initial_indent="  ", subsequent_indent="  ")
        blocks.append(f"{t.name}\n{desc}")
    return "\n\n".join(blocks)
```

#### `list-tools` JSON-output pattern

**Analog:** `src/mcp_test_framework/ollama_judge.py` likely uses `model_dump_json` for Pydantic objects; `Tool` from `mcp.types` is also a Pydantic model. Pattern:
```python
import json

def _format_tools_json(tools: list[Tool]) -> str:
    sorted_tools = sorted(tools, key=lambda t: t.name)
    payload = [
        {
            "name": t.name,
            "description": t.description,
            "inputSchema": t.inputSchema,
            "outputSchema": getattr(t, "outputSchema", None),
        }
        for t in sorted_tools
    ]
    return json.dumps(payload, indent=2, default=str) + "\n"
```

#### Typer app construction pattern

**No in-repo Typer analog** (first CLI). CONTEXT discretion specifies the shape:
```python
import typer

app = typer.Typer(
    name="mcp-test-framework",
    no_args_is_help=True,
    add_completion=False,
    help="Pytest framework for testing MCP servers end-to-end.",
)
```

Module footer (so `python -m mcp_test_framework.cli` also works):
```python
if __name__ == "__main__":  # pragma: no cover
    app()
```

#### Error handling pattern (CLI surface)

**Analog:** `fixtures.py` `_preflight` (lines 108-159) — single-line diagnostics naming the failed precondition + the configured value, using `pytest.exit(..., returncode=2)`. CLI equivalent: `typer.echo(..., err=True)` + `raise typer.Exit(code=2)`.

For `list-tools`, do NOT wrap the body in a top-level try/except. KeyboardInterrupt (Ctrl+C) propagates out of `asyncio.Runner.run(...)` → out of the Typer command → Python sets exit code 130 by default. **D-teardown-3:** no message printed.

For `Config()` ValidationErrors, let Pydantic's message print and Typer will surface a nonzero exit. CONTEXT discretion bullet 2: "Don't catch and re-wrap — Pydantic's own messages are good enough for MVP." Optionally wrap once in `_load_config` to translate to exit code 2 (see helper above).

---

### `pyproject.toml` (MODIFIED — config)

**Analog:** self (existing commented block at lines 14-16). Pattern: uncomment in place.

**Current** (lines 14-16):
```toml
# [project.scripts]
# Wired in Phase 5 -- intentionally commented out until the CLI module lands.
# mcp-test-framework = "mcp_test_framework.cli:app"
```

**Target:**
```toml
[project.scripts]
mcp-test-framework = "mcp_test_framework.cli:app"
```

**Constraints from analog:**
- The package name on the right of `=` is `mcp_test_framework` (underscore, the importable package), NOT `mvp-test-framework` (the distribution name on line 2).
- `:app` references the Typer instance; Typer apps are callable, so no `:main` wrapper needed (CONTEXT code-context line 156).
- Do NOT add new `dependencies` — Typer is already transitive via `mcp[cli]` (CONTEXT line 19).

**Validation step:** after editing, run `uv sync` once to refresh `uv.lock` metadata (regenerates the script shim under `.venv/Scripts/`). Confirm `uv run mcp-test-framework --help` resolves.

---

### `README.md` (REPLACED — documentation)

**Analogs (structural, not code):**

#### Analog A: `docs/mcp_test_framework_mvp_spec.md`

This is the authoritative project doc. Match its voice (declarative, sectioned with `##`, code blocks for commands, reference links at the bottom). Don't read its full body unless drafting parity sections — the README is quickstart, the spec is authoritative.

#### Analog B: existing `README.md` (full file, 12 lines)

Content (lines 1-12):
```markdown
# mcp_test_framework

A pytest-based Python framework for testing MCP (Model Context Protocol) servers.

The MVP targets the `homelab-mcp` server over stdio and validates one tool
(`list_registered_servers`) end-to-end through schema validation, an
Ollama-backed description-quality judge, and output conformance checks.

> Full setup, configuration, and usage docs land in Phase 5 (CLI / docs).
> See `.planning/PROJECT.md` and `docs/mcp_test_framework_mvp_spec.md` for the
> authoritative scope and design.
```

**Action:** keep the H1 (`# mcp_test_framework`) and the project-one-liner; replace everything below the project-one-liner with the Phase 5 quickstart content.

#### Required section structure (D-readme-1)

```markdown
# mcp_test_framework

[one-liner from current README]

## Prerequisites
- Python 3.14
- uv (https://docs.astral.sh/uv/)
- Ollama running at the configured base URL with the configured model
- `homelab-mcp` runnable via `uvx` (default) or on PATH

## Setup
\`\`\`bash
uv sync
\`\`\`

## Commands
### Run the test suite
\`\`\`bash
uv run mcp-test-framework run
uv run mcp-test-framework run --config ./config.yaml
uv run mcp-test-framework run -- -x --lf -k schema
\`\`\`

### List tools
\`\`\`bash
uv run mcp-test-framework list-tools
uv run mcp-test-framework list-tools --json
\`\`\`

### Version
\`\`\`bash
uv run mcp-test-framework version
\`\`\`

## Configuration

Precedence: **CLI flag > env var > `.env` > YAML overlay > default.**

| Env Var | Default | Purpose |
|---------|---------|---------|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server base URL |
| `OLLAMA_MODEL` | `qwen3.6:latest` | Ollama model name |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Per-request HTTP timeout |
| `MCP_SERVER_COMMAND` | `homelab-mcp` (default), `uvx` (in `.env.example`) | MCP server launcher |
| `MCP_SERVER_ARGS` | `[]` (default), `["homelab-mcp"]` (in `.env.example`) | JSON list of args |
| `MCP_SERVER_TIMEOUT_SECONDS` | `30` | Per-SDK-call timeout |
| `TARGET_TOOL_NAME` | `list_registered_servers` | Tool under test |
| `JUDGE_TIMEOUT_SECONDS` | `120` | Outer-budget cap on judge calls |
| `MCPTF_CONFIG_FILE` | unset | Path to YAML overlay |

Copy `.env.example` to `.env` and edit. See `.env.example` for the executable starter.

## Sample green run
[10-15 line excerpt of pytest output captured during execution]

## Troubleshooting (Windows)
- If a Ctrl+C leaves a `homelab-mcp.exe` behind: `taskkill /F /IM homelab-mcp.exe`
- This was the cancel-scope teardown bug fixed in Phase 04.1; should not recur.

## Further reading
- [`docs/mcp_test_framework_mvp_spec.md`](docs/mcp_test_framework_mvp_spec.md) — authoritative design
- [`docs/EXTENDING.md`](docs/EXTENDING.md) — add a new rubric, swap the judge backend
```

**Env-var table source:** `.env.example` (extracted above in `.env.example` analog). Cross-check before commit.

**Sample-pytest-output source:** captured during execution (D-readme-3). Plan/executor runs `uv run pytest tests/` with live markers active, captures stdout, pastes 10-15 lines.

---

### `docs/EXTENDING.md` (NEW — documentation)

**No in-repo doc analog** (the only doc is the spec). Use the spec's voice (declarative, code-fenced examples, file-path references) but keep total length to ~80-120 lines (D-readme-2 / discretion bullet 8).

**Code-sample analogs (these are referenced, not copied wholesale):**

#### Recipe 1: "Add a new description-quality rubric"

Reference `src/mcp_test_framework/rubrics.py` (full file, especially lines 44-95):

**Excerpt to pattern from** (lines 44-63):
```python
class Rubric(BaseModel):
    """Base rubric. Subclasses fill `dimension` and `dimension_criteria`."""

    model_config = ConfigDict(frozen=True)

    dimension: str
    dimension_criteria: str

    def __str__(self) -> str:
        return "\n\n".join(
            [
                _HARDENING_PREAMBLE,
                f"DIMENSION: {self.dimension}\n{self.dimension_criteria}",
                _SCORE_ANCHOR_TEMPLATE,
            ]
        )
```

**Concrete-subclass shape** (lines 66-74):
```python
class ClarityRubric(Rubric):
    dimension: str = "clarity"
    dimension_criteria: str = (
        "Does the description clearly explain WHAT the tool does..."
    )
```

**Recipe shape:** show user how to subclass `Rubric` in their own conftest, register a session-scoped fixture (mirror `fixtures.py:307-319`), and write `test_x(judge, target_tool, my_rubric)`.

**Fixture template to include in EXTENDING.md** (mirrors `fixtures.py:307-319`):
```python
import pytest
from mcp_test_framework.rubrics import Rubric


class SafetyRubric(Rubric):
    dimension: str = "safety"
    dimension_criteria: str = "Does the description name destructive side effects ..."


@pytest.fixture(scope="session")
def rubric_safety() -> SafetyRubric:
    return SafetyRubric()


async def test_safety(judge, target_tool, rubric_safety):
    result = await judge.judge(str(rubric_safety), target_tool.description)
    assert result.passed, result.reasoning
```

#### Recipe 2: "Swap the judge backend"

Reference `src/mcp_test_framework/judge_protocol.py` (full file, especially lines 46-61):

**Protocol excerpt** (lines 46-61):
```python
@runtime_checkable
class Judge(Protocol):
    """Pluggable LLM-judge seam (CORE-04, SEED-001 enabler)."""

    async def judge(
        self,
        rubric: str,
        subject: str,
        context: dict | None = None,
    ) -> JudgeResult: ...
```

**Recipe shape:** show user how to implement the Protocol in a class (any class with the matching async signature satisfies it), then override the `judge` fixture in their own conftest.

**Fixture-override template** (mirrors `fixtures.py:267-283`):
```python
import pytest_asyncio
from mcp_test_framework.judge_protocol import Judge
from mcp_test_framework.ollama_judge import JudgeResult


class MyJudge:
    async def judge(self, rubric: str, subject: str, context: dict | None = None) -> JudgeResult:
        # ... call your backend ...
        return JudgeResult(passed=True, score=4, reasoning="...", raw_response="...")


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def judge() -> Judge:  # noqa: overrides framework fixture by name
    return MyJudge()
```

**Pin the contract:** mention that `judge_protocol.py` notes (lines 30-37) `runtime_checkable` only checks attribute names, not signature shape. Users must match the signature.

---

### `.env.example` (VERIFY — config)

**Analog:** self (already exists, lines 1-23 above). No changes expected.

**Action:** diff the env-var table in the README draft against `.env.example`. If any var appears in one but not the other, reconcile. Specifically check:
- All 8 env vars in `.env.example` are documented in the README table (yes per draft above).
- The README's "Default" column matches the **Pydantic** default (from `models.py`, e.g., `MCP_SERVER_COMMAND` = `homelab-mcp` per `models.py:51`), NOT the `.env.example` example value (which is `uvx`). Document both per the table draft above.
- The precedence sentence in the README matches `config.py:6-7` ("CLI/init kwargs > env vars > .env > YAML overlay > defaults").

**No file edits expected** in Phase 5; this is verification only. If a drift is found, fix `.env.example` (the executable copy-paste form) and the README in the same commit.

---

## Shared Patterns

### Pattern 1: `Config()` is the single configuration entry point

**Source:** `src/mcp_test_framework/config.py:149-194` and consumers `tests/smoke/test_smoke_homelab_mcp.py:41,64` + `src/mcp_test_framework/fixtures.py:51-54`.

**Apply to:** every `cli.py` command that needs config (`run`, `list-tools`).

**Excerpt** (`fixtures.py:51-54`):
```python
@pytest.fixture(scope="session")
def config() -> Config:
    """Load env + YAML config once per session (Phase 1 precedence: CLI > env > YAML > default)."""
    return Config()
```

**CLI translation:** `_load_config(path)` helper sets `MCPTF_CONFIG_FILE` env var if `--config` was given, then calls `Config()`. Both `run` and `list-tools` go through the helper.

**Do NOT** re-implement YAML parsing or env layering in `cli.py`. `pydantic-settings` already does it.

### Pattern 2: `McpTestClient` is the only MCP entry point

**Source:** `src/mcp_test_framework/mcp_client.py:102-191`.

**Apply to:** the `list-tools` command.

**Excerpt** (`mcp_client.py:135-157`):
```python
async def __aenter__(self) -> "McpTestClient":
    if shutil.which(self._command) is None:
        raise FileNotFoundError(f"MCP server command not on PATH: {self._command!r}")
    params = StdioServerParameters(command=self._command, args=self._args)
    stack = AsyncExitStack()
    try:
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))
        async with asyncio.timeout(self._timeout_seconds):
            await session.initialize()
    except BaseException:
        await stack.aclose()
        raise
    self._stack = stack
    self._session = session
    return self
```

**CLI usage:** `async with McpTestClient(cfg.mcp_server.command, cfg.mcp_server.args, cfg.mcp_server.timeout_seconds) as client: tools = await client.list_tools()`. Black-box principle (PROJECT.md): do NOT import `homelab_mcp` directly.

### Pattern 3: Cross-task teardown discipline (Phase 04.1)

**Source:** `src/mcp_test_framework/fixtures.py:175-259`.

**Apply to:** the `list-tools` command body, but ONLY in the form of the simpler same-task pattern. `asyncio.Runner.run()` keeps `__aenter__` and `__aexit__` on the same task, so the owner-task + Future + Event scaffolding is NOT needed.

**Discipline excerpt** (`fixtures.py:181-205`, docstring):
```
all anyio scopes (``stdio_client``, ``ClientSession``, ``anyio.fail_after``)
live exclusively inside the owner task, which runs as a stdlib ``asyncio.Task``.
```

**CLI translation:** the Typer command function calls `asyncio.Runner` to drive a single coroutine that does the full `async with McpTestClient(...) as client: ...` lifecycle. KeyboardInterrupt → `__aexit__` runs in the same task → `stdio_client._terminate_process_tree` kills the subprocess → exit code 130.

### Pattern 4: Single-line CLI diagnostics on precondition failure

**Source:** `src/mcp_test_framework/fixtures.py:108-111, 124-128, 132-136, 147-151, 154-159`.

**Apply to:** `_load_config`'s "config path doesn't exist" branch and any other usage error before the async lifecycle starts.

**Excerpt** (`fixtures.py:108-111`):
```python
if shutil.which(config.mcp_server.command) is None:
    pytest.exit(
        f"MCP command {config.mcp_server.command!r} not found on PATH",
        returncode=2,
    )
```

**CLI translation:**
```python
typer.echo(f"error: --config path not found: {path}", err=True)
raise typer.Exit(code=2)
```

Format: lowercase `error:` prefix → name the failed precondition → include the offending value. Exit code 2 (usage error, matches Phase 4 / pytest convention).

### Pattern 5: Module docstring as a contract index

**Source:** every module under `src/mcp_test_framework/` (e.g., `mcp_client.py:1-30`, `fixtures.py:1-21`, `config.py:1-26`).

**Apply to:** `cli.py` top-of-file docstring.

**Pattern:** open with the spec section the module implements; list the decisions it embodies (D-cli-flags-1, D-cli-flags-2, D-cli-flags-3, D-list-1..4, D-teardown-1..3); name the most-important pitfall the file mitigates (Pitfall 1, owner-task discipline reused).

**Excerpt template** (mirrors `mcp_client.py:1-30`):
```python
"""Typer CLI surface (`run` / `list-tools` / `version`).

Implements the CLI from docs/mcp_test_framework_mvp_spec.md §CLI:

    run [--config PATH] [-- pytest args]   -- D-cli-flags-1..3
    list-tools [--config PATH] [--json]    -- D-list-1..4 / D-teardown-1..3
    version                                -- CLI-03

Per Phase 5 CONTEXT.md decisions:
- `_load_config(path)` helper sets MCPTF_CONFIG_FILE env var if --config given.
- `run` forwards everything after `--` to pytest.main(["tests", *forwarded]).
- `list-tools` body uses asyncio.Runner + AsyncExitStack-owned McpTestClient
  (Phase 04.1 same-task lifecycle -- avoids the cancel-scope teardown bug).
- version reads importlib.metadata.version("mvp-test-framework"), falls back
  to the package __version__ constant on PackageNotFoundError.
"""
```

---

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| `docs/EXTENDING.md` | documentation | No prior in-repo extension docs. Use spec doc voice + reference the `Rubric`/`Judge` Protocol files for code samples. |
| `cli.py` Typer app construction | controller | First Typer app in this repo. Use CONTEXT discretion lock (`no_args_is_help=True, add_completion=False`). |
| `cli.py` text-formatting helpers | utility | First terminal-formatting code in repo. Use stdlib `textwrap` + `shutil.get_terminal_size()` per CONTEXT discretion. |

---

## Metadata

**Analog search scope:**
- `src/mcp_test_framework/*.py` (all 8 modules read or scanned)
- `tests/smoke/test_smoke_homelab_mcp.py` (full file, lifecycle reference)
- `tests/conftest.py` and `tests/__init__.py` (registration verification)
- `pyproject.toml` (dependency + script entry verification)
- `.env.example` (env-var inventory)
- `docs/mcp_test_framework_mvp_spec.md` (referenced as voice anchor only — not read in full this pass; voice is well-understood from prior phases)

**Files scanned:** 9 source files + 4 tests/config files = 13 paths read or globbed.

**Pattern extraction date:** 2026-05-06.
