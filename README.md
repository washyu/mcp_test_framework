# mcp_test_framework

A pytest-based Python framework for testing MCP (Model Context Protocol) servers.

The MVP targets the `homelab-mcp` server over stdio and validates one tool
(`list_registered_servers`) end-to-end through schema validation, an
Ollama-backed description-quality judge, and output conformance checks.

## Prerequisites

- Python 3.14
- [`uv`](https://docs.astral.sh/uv/) (project, venv, and lockfile manager)
- [Ollama](https://ollama.com/) running at the configured base URL with the configured
  model (defaults: `http://127.0.0.1:11434`, model `qwen3.6:latest`)
- `homelab-mcp` runnable via `uvx` (the `.env.example` default) or installed on `PATH`

## Setup

```bash
git clone <repo-url>
cd mvp_test_framework
cp .env.example .env   # edit if your Ollama / MCP server differs
uv sync
```

`uv sync` installs the runtime + dev dependencies and registers the
`mcp-test-framework` console script under `.venv/Scripts/` (Windows) or
`.venv/bin/` (Unix).

## Commands

### Run the test suite

```bash
uv run mcp-test-framework run
uv run mcp-test-framework run --config ./config.yaml
uv run mcp-test-framework run -- -x --lf -k schema
```

`run` invokes pytest against the `tests/` directory and exits with pytest's exit
code (0 on green). Anything after the `--` separator is forwarded verbatim to
`pytest.main()` -- use it to pass `-k`, `-x`, `--lf`, or any other pytest flag.
The `-m 'not live_homelab and not live_ollama'` `addopts` contract from
`pyproject.toml` stays in effect; gate live tests with environment variables or
markers as documented in the spec.

### List MCP server tools

```bash
uv run mcp-test-framework list-tools
uv run mcp-test-framework list-tools --json
```

Default output is indented blocks (tool name on one line, the full wrapped
description indented beneath). `--json` emits a JSON array of full MCP tool
records (`name`, `description`, `inputSchema`, `outputSchema`) sorted
alphabetically by name. `list-tools` does **not** invoke pytest or the LLM
judge -- it is a quick discovery surface for whatever the server exposes.

### Show the version

```bash
uv run mcp-test-framework version
```

## Configuration

Precedence: **CLI flag > env var > `.env` > YAML overlay > default**.

| Env Var | Default | Purpose |
|---------|---------|---------|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server base URL. |
| `OLLAMA_MODEL` | `qwen3.6:latest` | Ollama model name used by the judge. |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Per-request HTTP timeout for Ollama calls. |
| `MCP_SERVER_COMMAND` | `homelab-mcp` | MCP server launcher binary. `.env.example` ships `uvx` for zero-install. |
| `MCP_SERVER_ARGS` | `[]` (JSON list) | Args passed to the launcher. `.env.example` ships `["homelab-mcp"]` to pair with `uvx`. |
| `MCP_SERVER_TIMEOUT_SECONDS` | `30` | Per-SDK-call timeout for stdio operations. |
| `TARGET_TOOL_NAME` | `list_registered_servers` | Tool under test. |
| `JUDGE_TIMEOUT_SECONDS` | `120` | Outer-budget cap on judge calls. |
| `MCPTF_CONFIG_FILE` | unset | Optional path to a YAML config overlay (sits below env in precedence). |

Copy `.env.example` to `.env` and edit. The same vars can be set in your shell,
in a YAML overlay pointed at by `MCPTF_CONFIG_FILE` (or `--config`), or in
PowerShell with `$env:VAR = "..."` before invoking the CLI.

## Sample green run

```text
<!-- TODO Plan 05: replace this block with a captured 10-15 line excerpt of `uv run mcp-test-framework run` output against live homelab-mcp + Ollama -->
============================= test session starts ==============================
platform win32 -- Python 3.14.x, pytest-9.x, pluggy-1.x
rootdir: C:\Users\you\projects\mvp_test_framework
configfile: pyproject.toml
plugins: asyncio-1.x
asyncio: mode=strict
collected 10 items

tests/test_homelab_list_registered_servers.py ..........                 [100%]

============================== 10 passed in X.XXs ==============================
```

Captured from a real green run; replace if your output drifts.

## Troubleshooting (Windows)

- If a Ctrl+C leaves a `homelab-mcp.exe` process behind:
  `taskkill /F /IM homelab-mcp.exe`. This was the cancel-scope teardown bug
  fixed in Phase 04.1; it should not recur in normal operation. The CLI's
  `list-tools` and `run` paths both unwind the MCP subprocess in the same task
  that started it (see `src/mcp_test_framework/fixtures.py` and
  `src/mcp_test_framework/cli.py`).
- If `uv run mcp-test-framework` fails with "command not found" after editing
  `pyproject.toml`: re-run `uv sync` to regenerate the script shim under
  `.venv/Scripts/`.
- If `homelab-mcp` is not on `PATH` and you see `[WinError 2]`: confirm
  `MCP_SERVER_COMMAND` and `MCP_SERVER_ARGS` in your `.env` (the default uses
  `uvx homelab-mcp` -- which requires `uvx` from `uv` to be available).

## Further reading

- [`docs/mcp_test_framework_mvp_spec.md`](docs/mcp_test_framework_mvp_spec.md) -- authoritative design spec
- [`docs/EXTENDING.md`](docs/EXTENDING.md) -- add a new rubric, swap the judge backend
- [`.planning/PROJECT.md`](.planning/PROJECT.md) -- project mission, constraints, key decisions
