# mcp_test_framework MVP Specification

## Goal

Build a minimum viable Python framework that connects to a single MCP server, targets a single tool, and runs three categories of automated tests against it. The framework uses a local Ollama-hosted LLM as a judge for description quality, while schema validation and output conformance are deterministic checks.

The MVP is intentionally narrow so the integration contract between framework, MCP server, and LLM can be validated end to end before generalizing.

## Target Outcomes

- A `pytest`-runnable test suite that exercises one MCP tool
- A reusable framework layer (client wrappers, judge, fixtures) that future test cases can build on
- CLI entry point suitable for CI/CD pipelines (exits non-zero on test failure, prints pytest default output)
- Configuration via environment variables and an optional YAML or TOML config file
- All dependencies installable via `uv` in a single project folder

## Out of Scope for MVP

- Multiple MCP server connections in one run
- Multiple tool targets in one run (framework should be designed so this is easy to add later, but the MVP hardcodes one tool)
- HTTP or SSE MCP transports (stdio only)
- LLM as test input generator (only as judge in MVP)
- Stateful or destructive tool testing (read-only tools only)
- Performance, load, or security testing
- JSON or JUnit output formats (pytest default terminal output is fine for MVP)
- Web UI or dashboard

## Architecture

### Component Diagram

```
+-------------------+      stdio       +------------------+
|  pytest test     | <--------------> |  MCP server      |
|  cases           |                  |  (homelab_mcp)   |
+-------------------+                  +------------------+
         |
         | uses
         v
+-------------------+      HTTP        +------------------+
|  Framework        | <--------------> |  Ollama          |
|  - MCP client     |                  |  (127.0.0.1) |
|  - Ollama judge   |                  |  qwen3.6:latest  |
|  - Fixtures       |                  +------------------+
+-------------------+
```

### Module Layout

The test tree splits the operator-relevant SUT-contract surface (`tests/contract/`) from framework self-tests (`tests/framework/`); the runner collects `tests/contract/` by default and adds `tests/framework/` only when invoked with `--with-framework`.

```
mcp_test_framework/
├── pyproject.toml
├── README.md
├── .env.example
├── config.example.yaml
├── src/
│   └── mcp_test_framework/
│       ├── __init__.py
│       ├── cli.py                  # CLI entry point
│       ├── config.py               # Config loading (env vars + YAML)
│       ├── mcp_client.py           # Stdio MCP client wrapper
│       ├── ollama_judge.py         # Ollama client + judge functions
│       ├── schema_validator.py     # MCP schema structural checks
│       └── fixtures.py             # Pytest fixtures
└── tests/
    ├── conftest.py                                    # session-scoped fixtures (applies to both subtrees)
    ├── contract/
    │   └── test_mcp_tool_contract.py                  # operator-relevant SUT-contract surface
    └── framework/                                     # framework self-tests (config, runner, snippets, banned imports, smoke)
        ├── test_banned_imports.py
        ├── test_isolation.py
        ├── test_readme_snippets.py
        ├── test_runner_*.py
        ├── test_config_init_cli.py
        ├── test_tool_config.py
        ├── unit/                                      # 20 unit self-tests
        ├── smoke/                                     # 3 live-marker smoke tests (homelab-mcp + Ollama)
        ├── _fixtures/                                 # banned-imports negative fixture
        └── fixtures/                                  # JUnit XML parser fixtures
```

### Dependencies

- `mcp` (official Python MCP SDK, used for stdio client)
- `pytest` (test runner)
- `pytest-asyncio` (MCP client is async)
- `httpx` (Ollama HTTP client, async-compatible)
- `pydantic` (config models and response validation)
- `pyyaml` (config file parsing)
- `python-dotenv` (env file loading)
- `jsonschema` (validating responses against declared output schemas, if present)
- `homelab-mcp` (PyPI package, the system under test)

Use `uv` to manage the venv and lockfile.

## Configuration

### Environment Variables

```
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.6:latest
MCP_SERVER_COMMAND=homelab-mcp
MCP_SERVER_ARGS=
TARGET_TOOL_NAME=list_registered_servers
JUDGE_TIMEOUT_SECONDS=120
```

### Config File (optional, overrides env vars)

`config.yaml`:

```yaml
ollama:
  base_url: http://127.0.0.1:11434
  model: qwen3.6:latest
  timeout_seconds: 120

mcp_server:
  command: homelab-mcp
  args: []

target:
  tool_name: list_registered_servers
```

The `config.py` module loads env vars first, then overlays values from `config.yaml` if present. CLI flags override both.

## Component Specifications

### `mcp_client.py`

Async wrapper around the official `mcp` SDK's stdio client.

Public interface:

```python
class McpTestClient:
    def __init__(self, command: str, args: list[str]): ...

    async def __aenter__(self) -> "McpTestClient": ...
    async def __aexit__(self, *args) -> None: ...

    async def list_tools(self) -> list[Tool]: ...
    async def get_tool(self, name: str) -> Tool: ...
    async def call_tool(self, name: str, arguments: dict) -> CallToolResult: ...
```

The client launches the MCP server as a subprocess over stdio, performs the MCP handshake, and exposes tool listing and invocation. It must handle subprocess cleanup on exit.

### `ollama_judge.py`

Async wrapper around the Ollama `/api/chat` endpoint.

Public interface:

```python
class OllamaJudge:
    def __init__(self, base_url: str, model: str, timeout_seconds: int): ...

    async def judge(
        self,
        rubric: str,
        subject: str,
        context: dict | None = None,
    ) -> JudgeResult: ...
```

`JudgeResult` is a Pydantic model:

```python
class JudgeResult(BaseModel):
    passed: bool
    score: int  # 1-5
    reasoning: str
    raw_response: str
```

The judge sends a prompt that asks the model to evaluate `subject` against `rubric` and return a structured JSON response. The judge parses the JSON, validates with Pydantic, and falls back to a failure result with the raw response on parse error.

System prompt template:

```
You are a strict technical evaluator. Evaluate the provided subject against the
rubric. Respond with ONLY a JSON object matching this schema:

{
  "passed": boolean,
  "score": integer between 1 and 5,
  "reasoning": "brief explanation"
}

Do not include any text outside the JSON.
```

### `schema_validator.py`

Deterministic structural checks on a tool's declared schema. No LLM involved.

Public interface:

```python
def validate_tool_schema(tool: Tool) -> list[ValidationIssue]: ...
def validate_response_against_schema(response: Any, schema: dict) -> list[ValidationIssue]: ...
```

Checks performed by `validate_tool_schema`:

1. Tool has a non-empty `name`
2. Tool has a non-empty `description`
3. Tool has an `inputSchema` that is a valid JSON Schema document
4. `inputSchema.type` is `"object"`
5. All declared `required` fields exist in `properties`
6. Every property has a `description`
7. Every property has a `type` or `oneOf` or `anyOf`

`ValidationIssue` is a Pydantic model with `severity` (error or warning), `path`, and `message`.

### `fixtures.py` and `conftest.py`

Pytest fixtures that provide:

- `mcp_client`: session-scoped, an open `McpTestClient` connected to the configured MCP server
- `judge`: session-scoped, an `OllamaJudge` instance
- `target_tool`: session-scoped, the `Tool` object for the configured target tool name (fails the run early if the tool does not exist on the server)
- `config`: session-scoped, the loaded config object

### `cli.py`

Thin wrapper around `pytest`. Parses framework-specific flags (config path, override env vars), then invokes pytest with appropriate args.

```
mcp-test-framework run [--config PATH] [-k EXPRESSION] [-v]
mcp-test-framework list-tools
mcp-test-framework version
```

`run` is the CI/CD entry point. Exits with pytest's exit code.

`list-tools` connects to the configured MCP server and prints all available tools and their descriptions. Useful for picking a target.

## Test Cases (MVP)

The MVP's SUT-contract tests live in `tests/contract/test_mcp_tool_contract.py` (parametrized across the operator's enabled tool list); framework self-tests (config validation, runner internals, snippet correctness, isolation, banned imports, smoke) live under `tests/framework/`.

### Category 1: Schema Validation (deterministic, no LLM)

- `test_target_tool_exists`: configured target tool is present in the server's tool list
- `test_tool_schema_is_structurally_valid`: schema validator returns no errors
- `test_tool_has_description`: description is non-empty and at least 20 characters
- `test_input_schema_properties_are_documented`: every input parameter has a description and a type

### Category 2: Description Quality (Ollama judge)

Each test sends a different rubric to the judge with the tool's name, description, and input schema as context.

- `test_description_clarity`: rubric asks the model to score whether the description clearly explains what the tool does
- `test_description_disambiguation`: rubric asks whether the description gives enough information for an LLM agent to know when to call this tool versus a similarly-named alternative
- `test_parameters_are_self_explanatory`: rubric asks whether each parameter description is clear enough to call the tool without external documentation

Pass threshold for MVP: `score >= 4`.

### Category 3: Output Conformance (deterministic plus optional LLM)

- `test_call_with_no_arguments_succeeds`: tool can be called with `{}` and returns a non-error result (this assumes `list_registered_servers` takes no required arguments, which is true based on the homelab_mcp tool surface)
- `test_response_has_expected_shape`: response is a valid `CallToolResult` with at least one content block
- `test_response_content_is_parseable`: if the content is text claiming to be JSON, it parses; if it is structured content, it matches any declared output schema

## Acceptance Criteria

The MVP is complete when all of the following are true:

1. `uv sync` installs all dependencies cleanly in a fresh checkout
2. `uv run mcp-test-framework list-tools` connects to homelab_mcp via stdio and prints the tool list, including `list_registered_servers`
3. `uv run mcp-test-framework run` executes all test cases, calling out to Ollama on `127.0.0.1:11434` for judge tests
4. The full run produces standard pytest terminal output, exits 0 on success and non-zero on any failure
5. A README in the repo root explains setup, configuration, and how to run tests
6. The Ollama judge gracefully handles model timeouts and malformed JSON responses without crashing the test run

## Implementation Notes for Claude Code

- Use `pytest-asyncio` strict mode and explicit `@pytest.mark.asyncio` markers
- Use `asyncio.timeout` (3.11+) for any async operation that could hang on subprocess or HTTP
- The MCP SDK's stdio client requires the server to be launched as a subprocess; do not use `subprocess.Popen` directly, use the SDK's `stdio_client` context manager
- Ollama's `/api/chat` endpoint streams by default; pass `stream: false` in the request body to get a single response
- When sending JSON to the Ollama judge, set `format: json` in the request body to enable structured output mode (Ollama will constrain generation to valid JSON)
- Do not log Ollama responses verbosely by default; gate behind a `--verbose` flag or `LOG_LEVEL=DEBUG`
- The framework should not import or read homelab_mcp source code at any point; treat it as a black box subprocess

## Future Work (Post-MVP, Not in Scope)

- Multi-tool test target selection
- HTTP and SSE MCP transports
- LLM-driven test input generation
- Stateful tool testing with setup and teardown
- JSON and JUnit output formats for CI dashboards
- Pluggable judge backends (OpenAI-compatible endpoints, not just Ollama)
- Generic conformance test pack that works against any MCP server
- Performance and load testing modes
- Security testing (parameter injection, auth boundary checks)
