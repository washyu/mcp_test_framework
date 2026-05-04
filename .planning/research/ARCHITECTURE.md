# Architecture Research

**Domain:** Python pytest framework that drives a stdio MCP subprocess + an HTTP LLM judge
**Researched:** 2026-05-04
**Confidence:** HIGH (component boundaries, build order, lifecycle pattern); MEDIUM (judge abstraction shape — confirmed direction, exact protocol pinned at MVP+1)

## TL;DR — Spec Validation

**The spec's Module Layout in `docs/mcp_test_framework_mvp_spec.md` §Module Layout is fundamentally sound and should be adopted as-is for MVP.** Six concrete refinements are recommended (none break the spec):

1. Split `fixtures.py` so `conftest.py` re-exports from it — keeps fixtures importable by future test packages and keeps pytest discovery happy.
2. Introduce a tiny `judge_protocol.py` (a `Protocol` / ABC) that `OllamaJudge` implements — zero MVP cost, makes the post-MVP OpenAI-compatible swap a 1-file addition.
3. Fold `prompts.py` (system prompt, rubric templates) out of `ollama_judge.py` — keeps the swap-backend seam clean (the prompts are reused across backends).
4. Add `models.py` (Pydantic `Config`, `JudgeResult`, `ValidationIssue`) — keeps schemas in one place, breaks the otherwise-real circular import risk between `config.py`/`fixtures.py`/`ollama_judge.py`.
5. Use `loop_scope="session"` on async fixtures (pytest-asyncio 0.21+ pattern) and own the `stdio_client` via an `AsyncExitStack` inside the `mcp_client` fixture — this is the only async lifecycle pattern that survives subprocess crash during teardown cleanly.
6. Black-box enforcement: do not list `homelab-mcp` in `[project.dependencies]`. List it in `[project.optional-dependencies.dev]` (or `[dependency-groups.dev]` in PEP 735 form) so the framework package itself never imports it. Spec currently puts it in `dependencies` — this is the one place I'd push back.

## Standard Architecture

### System Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                              CLI Layer                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  cli.py  (Click or Typer)                                         │  │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────┐                    │  │
│  │  │  run     │  │  list-tools  │  │ version  │                    │  │
│  │  └────┬─────┘  └──────┬───────┘  └──────────┘                    │  │
│  │       │ pytest.main() │ direct McpTestClient                      │  │
│  └───────┼───────────────┼───────────────────────────────────────────┘  │
│          ▼               ▼                                              │
├──────────────────────────────────────────────────────────────────────── │
│                           Fixture Layer                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  conftest.py → re-exports from fixtures.py                        │  │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────────┐  ┌──────────────┐   │  │
│  │  │ config  │  │mcp_client│  │   judge     │  │ target_tool  │   │  │
│  │  │(session)│  │(session, │  │ (session)   │  │  (session)   │   │  │
│  │  │         │  │AsyncExit │  │             │  │              │   │  │
│  │  │         │  │ Stack)   │  │             │  │              │   │  │
│  │  └────┬────┘  └────┬─────┘  └──────┬──────┘  └──────┬───────┘   │  │
│  └───────┼────────────┼───────────────┼────────────────┼────────────┘  │
│          ▼            ▼               ▼                ▼                │
├──────────────────────────────────────────────────────────────────────── │
│                          Framework Core                                  │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  config.py │  │mcp_client.py│  │ollama_judge  │  │ schema_      │  │
│  │            │  │             │  │     .py      │  │ validator.py │  │
│  │ env→YAML→  │  │ wraps       │  │ wraps Ollama │  │ deterministic│  │
│  │ CLI flags  │  │ stdio_client│  │ /api/chat    │  │ JSON Schema  │  │
│  └─────┬──────┘  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  │
│        │                │                 │                 │           │
│        ▼                ▼                 ▼                 ▼           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  models.py    (Pydantic: Config, JudgeResult, ValidationIssue)   │  │
│  │  prompts.py   (rubric + system-prompt templates)                 │  │
│  │  judge_protocol.py  (Judge ABC/Protocol — post-MVP seam)         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
            │                                  │
            │ stdio (mcp SDK)                  │ HTTP (httpx)
            ▼                                  ▼
   ┌────────────────────┐              ┌────────────────────┐
   │  homelab-mcp       │              │  Ollama            │
   │  subprocess        │              │  127.0.0.1     │
   │  (BLACK BOX —      │              │  qwen3.6:latest    │
   │  never imported)   │              │  /api/chat         │
   └────────────────────┘              └────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Owns / Talks to |
|-----------|---------------|-----------------|
| `cli.py` | Parse framework flags, resolve config, dispatch to `pytest.main()` (run) or `McpTestClient` (list-tools). Returns pytest exit code. | Config; pytest; (read-only) McpTestClient |
| `config.py` | Load env (via `python-dotenv` if present) → overlay YAML → overlay CLI flags. Returns frozen Pydantic `Config`. | Pydantic models; YAML; env |
| `mcp_client.py` | Async wrapper around `stdio_client` + `ClientSession`. Owns subprocess lifecycle through `AsyncExitStack`. | `mcp` SDK only |
| `ollama_judge.py` | Async HTTP client (`httpx.AsyncClient`) → POSTs `/api/chat` with `stream:false, format:json`. Parses + validates JSON → `JudgeResult`. | `httpx`; `prompts.py`; `models.py` |
| `schema_validator.py` | Pure functions: `validate_tool_schema`, `validate_response_against_schema`. No I/O, no async. | `jsonschema`; `models.py` |
| `fixtures.py` | Defines session-scoped pytest-asyncio fixtures: `config`, `mcp_client`, `judge`, `target_tool`. Fail-fast if target tool missing. | All four core modules |
| `conftest.py` | Re-exports fixtures + sets `asyncio_mode=strict` config. | `fixtures.py` |
| `models.py` | Pydantic models: `Config`, `OllamaConfig`, `McpServerConfig`, `JudgeResult`, `ValidationIssue`. Single source of schema truth. | Pydantic only |
| `prompts.py` | Rubric strings + system-prompt template. Pure data. | Nothing |
| `judge_protocol.py` *(post-MVP seam)* | `Judge(Protocol)` with one method: `judge(rubric, subject, context) -> JudgeResult`. | `models.py` |
| `tests/test_homelab_*.py` | Black-box test cases. Imports only fixtures + models — never `homelab-mcp`. | Fixtures, models |

## Recommended Project Structure

```
mvp_test_framework/
├── pyproject.toml               # uv-managed; homelab-mcp in dev group, NOT runtime deps
├── README.md
├── .env.example
├── config.example.yaml
├── src/
│   └── mcp_test_framework/
│       ├── __init__.py          # exports Config, JudgeResult, ValidationIssue
│       ├── cli.py               # Click/Typer entry point: run, list-tools, version
│       ├── config.py            # env → YAML → flags resolver → Config
│       ├── models.py            # Pydantic: Config, JudgeResult, ValidationIssue
│       ├── prompts.py           # rubric + system-prompt templates (pure data)
│       ├── judge_protocol.py    # Judge Protocol (post-MVP seam, zero-cost now)
│       ├── mcp_client.py        # McpTestClient (AsyncExitStack-owned)
│       ├── ollama_judge.py      # OllamaJudge implements Judge
│       ├── schema_validator.py  # pure validation functions
│       └── fixtures.py          # session-scoped async fixtures
└── tests/
    ├── conftest.py              # `from mcp_test_framework.fixtures import *`
    └── test_homelab_list_registered_servers.py
```

### Structure Rationale

- **`src/` layout (not flat):** Prevents accidental imports of `tests/` from production code, makes the `homelab-mcp` black-box rule mechanically enforceable (anyone trying `from homelab_mcp import …` in `src/` will fail at install time because it isn't a runtime dep), and avoids pytest's flat-layout sys.path quirks documented at [pytest import mechanisms](https://docs.pytest.org/en/stable/explanation/pythonpath.html).
- **`fixtures.py` separate from `conftest.py`:** `conftest.py` is auto-discovered by pytest but cannot be imported as a regular module from another package without breaking discovery. Keeping the actual fixture definitions in `fixtures.py` and re-exporting from `conftest.py` lets future test packages (multi-tool MVP+1) reuse them without duplication.
- **`models.py` extracted:** Without it, `config.py`, `ollama_judge.py`, and `schema_validator.py` all want to define or import each other's Pydantic models — a circular-import minefield. Pulling them into `models.py` is a 30-LOC change that pays for itself the first time the import graph bites.
- **`prompts.py` extracted:** When the post-MVP `OpenAICompatibleJudge` lands, the rubrics are reused verbatim. Keeping them in `ollama_judge.py` would force a refactor at the worst time (when the seam is being exercised for the first time).
- **`judge_protocol.py` (zero-MVP-cost seam):** A 5-line `Protocol` declaration that the MVP doesn't need but post-MVP requires. Adding it now means the post-MVP swap is "implement `Judge`, register in fixture" — no refactor.

## Architectural Patterns

### Pattern 1: AsyncExitStack-owned subprocess fixture (the critical one)

**What:** The `mcp_client` fixture uses `contextlib.AsyncExitStack` to enter the nested `stdio_client` + `ClientSession` context managers, yields, then unwinds them in reverse on teardown. This is the only pattern that survives a subprocess crash during teardown without leaking child processes or raising exit-on-exit errors.

**When to use:** Any session-scoped async fixture that owns more than one async context manager (which is exactly our case: `stdio_client` yields streams, `ClientSession` wraps them — two managers, both must be unwound in order).

**Trade-offs:**
- ✅ Cleanup in reverse order is automatic.
- ✅ If the subprocess dies, `__aexit__` on `stdio_client` swallows the resulting exceptions correctly (pre-2024 hand-rolled patterns did not).
- ✅ Same task enters and exits all contexts — avoids the "Attempted to exit cancel scope in a different task" trap documented in [pytest-asyncio #1191](https://github.com/pytest-dev/pytest-asyncio/issues/1191).
- ⚠️ Must use `loop_scope="session"` on the fixture decorator (pytest-asyncio 0.21+) so setup and teardown run in the same loop.

**Example:**
```python
import pytest_asyncio
from contextlib import AsyncExitStack
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def mcp_client(config):
    params = StdioServerParameters(
        command=config.mcp_server.command,
        args=config.mcp_server.args,
    )
    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        yield McpTestClient(session)   # thin wrapper exposing list_tools/call_tool
    # AsyncExitStack unwinds: closes session, then terminates subprocess
```

### Pattern 2: Pydantic Config with layered loaders (env → YAML → flags)

**What:** `config.py` exposes one function: `load_config(yaml_path: Path | None, overrides: dict) -> Config`. It builds a dict from env vars, deep-merges YAML on top if present, then deep-merges CLI overrides last. The Pydantic `Config` model validates the final dict.

**When to use:** Any tool with three config sources. This is the standard precedence rule across Click/Typer ecosystems: **flags > env > file > defaults** (per the [Typer/Click idiom](https://medium.com/@Modexa/command-line-upgraded-8-typer-click-tricks-077984133801)). Note the spec's wording "config file overrides env vars" inverts this — recommend matching the ecosystem norm: file overrides defaults, env overrides file, flags override env. Surface this discrepancy to the user; treat it as a config-precedence design question for the roadmap, not a research conclusion.

**Trade-offs:**
- ✅ Pydantic gives free validation, type coercion, and helpful errors.
- ✅ One immutable `Config` object flows through all fixtures — no surprise re-reads from env mid-run.
- ⚠️ The spec's stated precedence (YAML > env) is unusual. Validate which order the user actually wants before locking in.

**Example:**
```python
def load_config(yaml_path: Path | None, cli_overrides: dict) -> Config:
    data = _load_env()                                  # baseline from env
    if yaml_path:
        data = deep_merge(data, _load_yaml(yaml_path))  # YAML overlays env
    data = deep_merge(data, cli_overrides)              # flags win
    return Config.model_validate(data)
```

### Pattern 3: CLI-wraps-pytest via `pytest.main()` (Tavern/Schemathesis idiom)

**What:** `cli.py` is a thin Click or Typer app. `mcp-test-framework run` resolves config, sets `os.environ["MCP_TEST_FRAMEWORK_CONFIG"]` (or writes to a known path) so `conftest.py` can pick it up, then calls `pytest.main([...])` and returns its exit code. `pytest.main()` returns the exit code instead of raising `SystemExit`, which is exactly what a CLI wrapper wants.

**When to use:** Any pytest-based framework that wants a domain CLI. Tavern, Schemathesis, and pytest-bdd all use this pattern. Schemathesis additionally supports running tests purely through pytest (no CLI), which the user gets for free here.

**Trade-offs:**
- ✅ Users can still run raw `pytest` and get full pytest features.
- ✅ Exit code propagates correctly to CI.
- ⚠️ Passing config from CLI into pytest fixtures is awkward — the cleanest path is an env var the fixture reads, not module globals (which break under pytest-xdist).

**Example:**
```python
import click, pytest

@click.command()
@click.option("--config", type=click.Path(exists=True), default=None)
@click.option("-k", "expression", default=None)
@click.option("-v", "verbose", is_flag=True)
def run(config, expression, verbose):
    if config:
        os.environ["MCP_TEST_FRAMEWORK_CONFIG_FILE"] = str(config)
    args = ["tests"]
    if expression: args += ["-k", expression]
    if verbose: args += ["-v"]
    raise SystemExit(pytest.main(args))
```

### Pattern 4: Judge Protocol seam (post-MVP-ready, MVP-cheap)

**What:** Define a `Judge` Protocol with one method. `OllamaJudge` is the MVP implementation. The `judge` fixture returns `Judge` (the Protocol type), not `OllamaJudge` (the concrete class). When OpenAI-compatible support arrives, it's a new file (`openai_judge.py`) and a config-driven dispatch in the fixture — no test-file changes.

**When to use:** Any MVP where the spec explicitly calls out a future swap (the spec lists "Pluggable judge backends" in Future Work). The cost now is ~10 LOC; the cost later (with no seam) is a refactor across `fixtures.py` and every test that imports the concrete type.

**Trade-offs:**
- ✅ Tests typed against the Protocol stay valid across backend swaps.
- ✅ Mocking in unit tests becomes trivial (`class FakeJudge: ...`).
- ⚠️ Adds one file to the MVP. Almost zero cognitive cost given how small it is.

**Example:**
```python
# judge_protocol.py
from typing import Protocol
from .models import JudgeResult

class Judge(Protocol):
    async def judge(self, rubric: str, subject: str, context: dict | None = None) -> JudgeResult: ...
```

### Pattern 5: Black-box enforcement via dependency partitioning

**What:** Put `homelab-mcp` in `[dependency-groups.dev]` (PEP 735) or `[project.optional-dependencies.dev]`, *not* `[project.dependencies]`. The framework package itself never lists it as a runtime dep. The `MCP_SERVER_COMMAND=homelab-mcp` env var is just a string the framework launches as a subprocess — there's no Python-level coupling.

**When to use:** Whenever the spec says "treat X as a black box." This is the only mechanical enforcement; otherwise it's a code-review-only rule that erodes over time.

**Trade-offs:**
- ✅ A future `from homelab_mcp import …` in `src/` will fail at install time when someone publishes the framework as a package.
- ✅ Documents the contract: framework + server are separately versioned, separately installed.
- ⚠️ Local dev still needs `homelab-mcp` installed (in the dev group) so the subprocess can be launched. This is fine — it's installed in the venv, not imported by the framework.

## Data Flow

### Config → Fixture → Test (startup)

```
1. CLI parses flags                                    cli.py
2. CLI calls load_config(yaml_path, overrides)         config.py
3. load_config: env → merge(YAML) → merge(flags)       config.py
4. Returns frozen Pydantic Config                      models.py
5. CLI sets MCP_TEST_FRAMEWORK_CONFIG_FILE env var     cli.py
6. CLI calls pytest.main(["tests"])                    cli.py
7. pytest discovers conftest.py → fixtures.py
8. config fixture (session) re-runs load_config()      fixtures.py
9. mcp_client fixture (session, async):
     - opens AsyncExitStack
     - enters stdio_client(params) → spawns subprocess
     - enters ClientSession(read, write)
     - awaits session.initialize()
     - yields McpTestClient(session)
10. judge fixture (session): builds OllamaJudge        fixtures.py
11. target_tool fixture (session, async):
     - tools = await mcp_client.list_tools()
     - asserts target name in tools (fail fast)
     - returns the matching Tool
12. Test functions run, depending on the above
```

### MCP request/response (per-call)

```
test                       McpTestClient            ClientSession           subprocess
  │                              │                       │                       │
  │ await call_tool("X", {})     │                       │                       │
  │─────────────────────────────►│                       │                       │
  │                              │ session.call_tool(...)│                       │
  │                              │──────────────────────►│ JSON-RPC over stdin   │
  │                              │                       │──────────────────────►│
  │                              │                       │ JSON-RPC over stdout  │
  │                              │                       │◄──────────────────────│
  │                              │ CallToolResult        │                       │
  │                              │◄──────────────────────│                       │
  │ CallToolResult               │                       │                       │
  │◄─────────────────────────────│                       │                       │
  │                              │                       │                       │
  │ wrapped in asyncio.timeout(N) at client boundary                            │
```

### Judge request/response (per rubric)

```
test                        OllamaJudge                Ollama HTTP
  │                              │                          │
  │ judge.judge(rubric, subject, │                          │
  │             context={tool})  │                          │
  │─────────────────────────────►│                          │
  │                              │ build prompt from         │
  │                              │ prompts.SYSTEM + rubric   │
  │                              │ POST /api/chat            │
  │                              │ {model, messages,         │
  │                              │  stream:false,            │
  │                              │  format:json}             │
  │                              │─────────────────────────►│
  │                              │                          │
  │                              │  asyncio.timeout(120)     │
  │                              │                          │
  │                              │  response (JSON)          │
  │                              │◄─────────────────────────│
  │                              │ JudgeResult.model_validate│
  │                              │ on parse error → fail-    │
  │                              │ closed JudgeResult        │
  │ JudgeResult                  │                          │
  │◄─────────────────────────────│                          │
```

### Key Data Flows (numbered)

1. **Config flow:** CLI flags → env → YAML → Pydantic `Config` → all fixtures (immutable for the run).
2. **MCP flow:** Test → `McpTestClient.call_tool` → `ClientSession.call_tool` → JSON-RPC over stdio → subprocess → response. Wrapped in `asyncio.timeout` at the client boundary.
3. **Judge flow:** Test → `Judge.judge` → `httpx.AsyncClient.post(/api/chat)` → JSON parse → Pydantic `JudgeResult`. Parse failures degrade to `JudgeResult(passed=False, score=0, reasoning="parse_error", raw_response=...)` — the test fails, the run continues.
4. **Schema flow:** Test → `validate_tool_schema(target_tool)` → list of `ValidationIssue`. Pure, sync, no I/O.
5. **Teardown flow:** pytest session ends → `mcp_client` fixture's `AsyncExitStack` unwinds → `ClientSession` closes → `stdio_client` terminates subprocess → fixture returns.

## Build Order / Dependency DAG

The module dependency graph is acyclic when laid out like this. Build bottom-up:

```
Layer 0  (no dependencies)
  models.py            ── Pydantic models
  prompts.py           ── string templates
  judge_protocol.py    ── Protocol declaration

Layer 1  (depend on Layer 0 only)
  config.py            ── needs models.Config
  schema_validator.py  ── needs models.ValidationIssue
  ollama_judge.py      ── needs models.JudgeResult, prompts, judge_protocol
  mcp_client.py        ── needs nothing from project (just mcp SDK)

Layer 2  (depend on Layer 1)
  fixtures.py          ── wires everything together
  cli.py               ── needs config, mcp_client (for list-tools)

Layer 3  (depend on Layer 2)
  conftest.py          ── re-exports fixtures
  tests/test_*.py      ── consumes fixtures only
```

### Suggested implementation order

1. **`pyproject.toml`** — declare deps; `homelab-mcp` in dev group only.
2. **`models.py`** — define `Config`, `OllamaConfig`, `McpServerConfig`, `JudgeResult`, `ValidationIssue`. Trivially testable.
3. **`config.py`** — env+YAML+overrides loader. Unit-testable with no fixtures.
4. **`schema_validator.py`** — pure functions, write with unit tests against synthetic `Tool` dicts.
5. **`prompts.py`** — copy rubric strings from spec.
6. **`mcp_client.py`** — start here for the integration risk. Smoke-test against `homelab-mcp` directly with a one-off async script before building fixtures.
7. **`judge_protocol.py`** — 5 lines.
8. **`ollama_judge.py`** — smoke-test against the live Ollama at `127.0.0.1` before fixtures.
9. **`fixtures.py`** — now everything plugs in. This is where the AsyncExitStack pattern lives.
10. **`conftest.py`** — re-exports + `asyncio_mode=strict`.
11. **`tests/test_homelab_list_registered_servers.py`** — write all 10 test functions.
12. **`cli.py`** — last; wraps everything.
13. **`README.md`** — last; documents the result.

**Critical path / risk-first ordering:** Steps 6 and 8 are the integration-risk steps. Build a throwaway smoke script for each before building fixtures — if `stdio_client` doesn't behave as documented or Ollama's `format:json` mode isn't pinning output, you want to discover that before you've written fixtures around it. This maps cleanly to a "Phase 1: prove the two integrations" milestone before "Phase 2: wire the framework."

## Scaling Considerations

This is a single-user local CLI for an MVP. "Scale" here is about feature growth, not load. Sketched for completeness:

| Scale | Architecture Adjustments |
|-------|--------------------------|
| MVP (1 server, 1 tool) | Current architecture. No changes. |
| Multi-tool, 1 server | Promote `target_tool` from session-scoped to parametrized; add `tools_under_test: list[str]` to config. Test files become `test_<server>_<tool>.py` — one per tool. Fixture changes only. |
| Multi-server | Promote `mcp_client` from session to "session per server" via `pytest.fixture(params=...)`. `Config` grows a `servers: list[McpServerConfig]`. Test discovery needs a per-server marker. |
| Pluggable judge | `judge` fixture dispatches on `config.judge.backend`. Adds `openai_judge.py` implementing `Judge`. No test changes. |
| LLM-driven test generation (Plant Seed) | New module `test_generator.py` (consumes `Judge` + `target_tool`) → emits parametrized `arguments` dicts. Existing test functions become `pytest.mark.parametrize("arguments", generated_inputs)`. |

### Scaling Priorities (the "what breaks first" list)

1. **First friction point: hardcoded test filename.** `test_homelab_list_registered_servers.py` mentions both server and tool. Adding tool #2 means a new file with mostly-duplicated content. Mitigation: when going to multi-tool, collapse to `test_tool_contract.py` parametrized by tool name. Don't pre-build this for MVP.
2. **Second friction point: session-scoped `target_tool`.** Single-target only. Same mitigation as above — parametrize.
3. **Third friction point: judge backend hardcoded in fixture.** Mitigated by the `Judge` Protocol seam if added now (Pattern 4).

## Anti-Patterns

### Anti-Pattern 1: Using `subprocess.Popen` directly instead of `stdio_client`

**What people do:** Reach for `subprocess.Popen` because they're more familiar with it than the MCP SDK's context manager.
**Why it's wrong:** You re-implement the JSON-RPC framing, miss the SDK's handshake handling, and own subprocess cleanup yourself. Crashes leak processes.
**Do this instead:** Always go through `mcp.client.stdio.stdio_client` as documented. This is also a spec-level constraint.

### Anti-Pattern 2: Making fixtures function-scoped "to be safe"

**What people do:** Default to function-scoped async fixtures because session-scoped feels risky.
**Why it's wrong:** Each test re-launches `homelab-mcp` (slow), re-handshakes MCP, and re-creates the `httpx.AsyncClient`. With pytest-asyncio 1.x and the `AsyncExitStack` pattern, session scope is safe and dramatically faster.
**Do this instead:** Session scope with `loop_scope="session"`. Use `pytest_asyncio.fixture`, not `pytest.fixture`, for async fixtures.

### Anti-Pattern 3: Letting tests import server internals "just for one assertion"

**What people do:** `from homelab_mcp.servers import REGISTRY` in a test to check what should have been listed.
**Why it's wrong:** Couples the framework to one server's internals. Defeats the entire reusability premise.
**Do this instead:** Assert against the *contract* — what `list_tools()` returned, what `call_tool` produced. The dependency partition (Pattern 5) makes this a hard fail at install time when the framework is packaged.

### Anti-Pattern 4: Mutating `os.environ` from test code

**What people do:** Tests `monkeypatch.setenv(...)` to override config mid-run.
**Why it's wrong:** Defeats the point of an immutable session-scoped `Config`. Causes order-dependent test failures.
**Do this instead:** Pass overrides as fixture parameters or pytest CLI options. Config is loaded once.

### Anti-Pattern 5: Async fixture that creates a `TaskGroup` straddling `yield`

**What people do:** `async with anyio.create_task_group() as tg: ... yield ...`
**Why it's wrong:** The setup task and the teardown task are different tasks under pytest-asyncio in some configurations, leading to "Attempted to exit cancel scope in a different task" — see [pytest-asyncio #1191](https://github.com/pytest-dev/pytest-asyncio/issues/1191) and [anyio #74](https://github.com/agronholm/anyio/issues/74).
**Do this instead:** Use `AsyncExitStack` (works correctly across the yield) or keep the task group inside a single async function below the fixture.

### Anti-Pattern 6: Verbose Ollama response logging by default

**What people do:** `print(response.text)` in the judge.
**Why it's wrong:** A few thousand-token completions per test fills the terminal and obscures the failure summary.
**Do this instead:** Gate behind `--verbose` or `LOG_LEVEL=DEBUG` (already noted in the spec's implementation notes — preserve it).

## Integration Points

### External Services

| Service | Integration Pattern | Notes / Gotchas |
|---------|---------------------|-----------------|
| `homelab-mcp` subprocess | `stdio_client` context manager via official `mcp` SDK | Black-box; never imported. Ensure dev group install in `uv sync --dev` before running tests. |
| Ollama HTTP `/api/chat` | `httpx.AsyncClient` with `stream:false, format:json` | Wrap every call in `asyncio.timeout(config.judge.timeout_seconds)`. Network is `127.0.0.1` — connection refused is a config error, not a test failure; surface it clearly. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `cli` ↔ `config` | direct call (`load_config`) | One-way; CLI never reads env directly. |
| `cli` ↔ `pytest` | `pytest.main(args)`; env var passes config path | Don't share Python objects across this boundary; pytest reloads the world. |
| `fixtures` ↔ `mcp_client` | `AsyncExitStack` ownership in fixture | Fixture is the only owner; tests never construct `McpTestClient` directly. |
| `fixtures` ↔ `judge` | Returns `Judge` (Protocol), not `OllamaJudge` | Enables backend swap without test changes. |
| `tests` ↔ `homelab-mcp` | **None.** Only via `mcp_client` over stdio. | Black-box rule. Mechanically enforced via dep partition (Pattern 5). |
| `schema_validator` ↔ everything else | pure functions, no shared state | Easiest module to unit test in isolation. |

## Where the Seams Should Be Flexible (Post-MVP)

Per the milestone context, these seams need to stay open for later. None require MVP work beyond what's listed above:

1. **Multi-tool.** `target_tool` fixture parametrizes over `config.target_tools: list[str]`. MVP keeps `tool_name: str`; expanding to a list is additive.
2. **Multi-server.** `mcp_client` fixture parametrizes over `config.mcp_servers: list[McpServerConfig]`. MVP keeps `mcp_server: McpServerConfig`; expanding is additive (no fixture-shape change).
3. **Pluggable judge.** `Judge` Protocol declared in MVP (Pattern 4). New backend = new file + one-line dispatch.
4. **LLM-driven test generation.** Generator consumes `Judge` and `Tool`, emits `pytest.mark.parametrize` data. The session-scoped `judge` and `target_tool` fixtures are exactly the inputs needed.
5. **HTTP/SSE MCP transports.** `McpTestClient` already wraps `ClientSession`; only the streams change. Add a transport selector to `Config` and a factory inside `mcp_client.py`.
6. **Structured output formats (JSON/JUnit).** Pure pytest plugin concern (`--junit-xml`, `pytest-json-report`). No framework changes.

## Sources

### High-confidence (official docs, verified)
- [pytest-asyncio Fixtures (1.3.0)](https://pytest-asyncio.readthedocs.io/en/stable/reference/fixtures/) — `loop_scope` parameter, scope-matching rules.
- [pytest-asyncio Concepts (1.3.0)](https://pytest-asyncio.readthedocs.io/en/stable/concepts.html) — strict mode and event loop scoping.
- [MCP Python SDK README](https://github.com/modelcontextprotocol/python-sdk) — canonical `stdio_client` + `ClientSession` nesting pattern.
- [pytest invocation docs](https://docs.pytest.org/en/stable/how-to/usage.html) — `pytest.main()` returns exit code, does not raise.
- [pytest configuration](https://docs.pytest.org/en/stable/reference/customize.html) — `PYTEST_ADDOPTS`, configfile precedence.
- [pytest plugin discovery](https://docs.pytest.org/en/stable/how-to/writing_plugins.html) — `pytest11` entry points, conftest auto-discovery.
- [pytest import mechanisms](https://docs.pytest.org/en/stable/explanation/pythonpath.html) — src-layout vs flat-layout consequences.

### Medium-confidence (community + maintainer discussions)
- [pytest-asyncio session-scope issue #944](https://github.com/pytest-dev/pytest-asyncio/issues/944) — known session-scope pitfalls, why `loop_scope` matters.
- [pytest-asyncio cancel-scope task error #1191](https://github.com/pytest-dev/pytest-asyncio/issues/1191) — anti-pattern: task groups straddling fixture yield.
- [anyio task-group teardown #74](https://github.com/agronholm/anyio/issues/74) — fixture finalization gotchas with task groups.
- [FastMCP testing guide](https://gofastmcp.com/development/tests) — alternative in-process pattern; confirms subprocess pattern is correct for stdio.
- [Tavern README](https://github.com/taverntesting/tavern) — CLI-wraps-pytest precedent.
- [Schemathesis pytest tutorial](https://schemathesis.readthedocs.io/en/stable/tutorials/pytest/) — same pattern, different domain.
- [Typer/Click config precedence idiom](https://medium.com/@Modexa/command-line-upgraded-8-typer-click-tricks-077984133801) — flags > env > file > defaults.

### Low-confidence (informational only)
- [Real Python MCP client guide](https://realpython.com/python-mcp-client/) — corroborating example only.
- [Practical MCP guide (DEV)](https://dev.to/m_sea_bass/practical-guide-to-mcp-model-context-protocol-in-python-ijd) — corroborating example only.

---
*Architecture research for: Python pytest framework testing MCP servers via stdio + Ollama judge*
*Researched: 2026-05-04*
