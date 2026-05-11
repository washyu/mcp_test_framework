# mcp_test_framework

A pytest-based Python framework for testing MCP (Model Context Protocol) servers.

The MVP targets the `homelab-mcp` server over stdio and validates one tool
(`list_keyring_credentials` by default) end-to-end through schema validation, an
Ollama-backed description-quality judge, and output conformance checks.

## Testing an MCP server you didn't write

The framework treats your MCP server as a black box — you don't need to read
its source. `mcp-test-framework list-tools` shows you the tools the server
exposes and their parameter shapes; `mcp-test-framework config-init` scaffolds
a config file populated with the actual tools you have. Designed for operators
testing servers they didn't author.

The full walkthrough lives in [`docs/EXTENDING.md`](docs/EXTENDING.md#testing-an-mcp-server-you-didnt-write).

## Prerequisites

- Python 3.14
- [`uv`](https://docs.astral.sh/uv/) (project, venv, and lockfile manager)
- [Ollama](https://ollama.com/) running at the configured base URL with the configured
  model (defaults: `http://127.0.0.1:11434`, model `qwen3.6:latest`)
- `homelab-mcp` runnable via `uvx`, or installed on `PATH`

## Setup

```bash
git clone <repo-url>
cd mvp_test_framework
uv sync
```

`uv sync` installs the runtime + dev dependencies and registers the
`mcp-test-framework` console script under `.venv/Scripts/` (Windows) or
`.venv/bin/` (Unix).

## Commands

### Run the test suite

```bash
uv run mcp-test-framework run --config config.yaml
uv run mcp-test-framework run --config ./config.yaml
uv run mcp-test-framework run --config config.yaml -- -x --lf -k schema
```

`run` invokes pytest against `tests/contract/` (the operator-relevant SUT-contract
surface) by default and exits with pytest's exit code (0 on green). Pass
`--with-framework` to also collect `tests/framework/` (the framework's own
self-tests -- config validation, runner internals, snippet checks, banned
imports). Anything after the `--` separator is forwarded verbatim to pytest --
use it to pass `-k`, `-x`, `--lf`, or any other pytest flag.
The `-m 'not live_homelab and not live_ollama'` `addopts` contract from
`pyproject.toml` stays in effect; gate live tests with environment variables or
markers as documented in the spec.

### List MCP server tools

```bash
uv run mcp-test-framework list-tools --config config.yaml
uv run mcp-test-framework list-tools --config config.yaml --json
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
| `MCP_SERVER_COMMAND` | `homelab-mcp` | MCP server launcher binary. |
| `MCP_SERVER_ARGS` | `[]` (JSON list) | Args passed to the launcher (JSON list). |
| `MCP_SERVER_TIMEOUT_SECONDS` | `30` | Per-SDK-call timeout for stdio operations. |
| `JUDGE_TIMEOUT_SECONDS` | `120` | Outer-budget cap on judge calls. |
| `MCPTF_CONFIG_FILE` | unset | Optional path to a YAML config overlay (sits below env in precedence). |

Configure the framework via `config.yaml` — generate a starter with
`mcp-test-framework config-init -o config.yaml` and pass it via
`--config config.yaml`. Env vars are reserved for CI-secret passthrough only
(see `.env.example`); they no longer override config values. The framework
does not auto-discover a `config.yaml` in the current directory; the path
must be explicit (via `--config` or the `MCPTF_CONFIG_FILE` env var).

## Per-tool configuration

Per-tool config lives under the top-level `tools:` key in your YAML overlay. Under this release's schema, a tool with **no entry runs by default** (no skip, all rubrics, empty `call_arguments`).

> **Heads-up on opt-in scaffolds.** The schema this release ships is opt-out: omitting a tool means it runs. The `config-init` scaffold takes the opposite stance and emits `skip: true` for every discovered tool, so a freshly-generated config is opt-in by construction. Operators are expected to review each entry and remove the skip line for tools they want to exercise. A future release is likely to invert the schema default to opt-in everywhere; until then, expect this asymmetry between "manual config" and "scaffolded config".

| Field | Default | Purpose |
|-------|---------|---------|
| `skip` | `false` | If `true`, the tool's tests are skipped via `pytest.skip(reason=skip_reason)`. Requires a non-empty `skip_reason`. |
| `skip_reason` | `null` | Human-readable reason surfaced in pytest output and JUnit XML when `skip: true`. |
| `call_arguments` | `{}` | Fixed `dict[str, Any]` passed to the tool's `call_tool` invocation. |
| `judges` | `null` (all rubrics) | Optional `list[str]` of rubric IDs (`clarity`, `disambiguation`, `parameters`). `[]` means "no rubrics for this tool". |
| `setup` | `null` | Reserved for stateful testing in a future release; no runtime effect today. |
| `depends_on` | `null` | Reserved for stateful testing in a future release; no runtime effect today. |

The `setup` and `depends_on` fields are typed in the model but have no runtime semantics in v1.1; future versions will activate them additively.

Replace the placeholder tool names below with the names from your `mcp-test-framework list-tools` output.

### Block A: skip-with-reason

```yaml
# config.yaml -- per-tool config overlay
tools:
  <safe_read_tool_a>:
    skip: true
    skip_reason: "Tool performs writes; we only exercise read-only tools in CI."
```

### Block B: judges subset

```yaml
# config.yaml -- per-tool config overlay
tools:
  <safe_read_tool_b>:
    judges: [clarity]
```

The third per-tool knob, `call_arguments: {key: value}`, lets you pass fixed arguments to the tool's `call_tool` invocation -- useful when the tool requires non-empty input. See `config.example.yaml` for shape.

For a complete real-server config, see [`config.example.yaml`](config.example.yaml).

## Sample green run

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: <home>\projects\mvp_test_framework
configfile: pyproject.toml
plugins: anyio-4.13.0, asyncio-1.3.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=session, asyncio_default_test_loop_scope=function
collected 72 items / 5 deselected / 67 selected

tests\smoke\test_mcp_client_teardown_regression.py .                     [  1%]
tests\test_homelab_list_registered_servers.py ..........                 [ 16%]
tests\unit\test_banned_imports.py ...                                    [ 20%]
tests\unit\test_config.py ............                                   [ 38%]
tests\unit\test_mcp_client.py .....                                      [ 46%]
tests\unit\test_ollama_judge.py ...............                          [ 68%]
tests\unit\test_rubrics.py .........                                     [ 82%]
tests\unit\test_schema_validator.py ............                         [100%]

================ 67 passed, 5 deselected, 1 warning in 22.02s =================
```

Captured verbatim from a real local run on Windows 11 against live `homelab-mcp`
+ Ollama, against a representative tool surface from the connected server.
The summary line says "67 passed in 22.02s" once you mentally fold over the
deselect/warning tokens -- pytest formats the wall-clock as `... in N.NNs`.
The 5 deselected tests are the live-marker smoke tests in `tests/framework/smoke/` gated
behind `-m 'not live_homelab and not live_ollama'`. The single warning is
pytest's standard `PytestAssertRewriteWarning` for `anyio` (already imported by
the time pytest tries to instrument it) and is unrelated to test outcomes.

If you enable a tool whose declared description does not satisfy the
description-quality rubrics, the test fails with the judge's reasoning
recorded in the JUnit XML and printed in the summary. Either tweak the
tool's description upstream, or skip the tool in your config (per the
"Per-tool configuration" section above).

## Isolation guarantee

Test runs do not mutate `~/.homelab_mcp/` real-state files. The framework spawns the MCP subprocess with `HOME` and `USERPROFILE` overridden to a per-session temporary directory, so the server reads/writes its state inside the tempdir and never touches your real-state files.

```bash
uv run pytest tests/framework/test_isolation.py -v
```

The test in `tests/framework/test_isolation.py` computes sha256 hashes of `~/.homelab_mcp/credential_registry.json`, `~/.homelab_mcp/known_hosts`, and `~/.homelab_mcp/migration_state.json` before and after a full session and asserts byte-identical equality. Test runs also route the OS keyring through a null backend, so credentials are not read or written.

## CI integration

Run the suite in CI with `--junit-xml=` and ingest the result with a JUnit-aware action. The snippet below runs the default unit slice (live markers excluded by `pyproject.toml`'s `addopts`).

```yaml
# .github/workflows/test.yml -- GitHub Actions starter.
# On Jenkins / GitLab CI / CircleCI, translate the `runs-on` / `uses` /
# `with` keys to the equivalent runner + action concepts. The CLI invocation
# (`uv run mcp-test-framework run --config config.yaml --junit-xml=results.xml`) is portable.
name: tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: "3.14"
      - run: uv sync
      # Default addopts in pyproject.toml excludes live_homelab + live_ollama markers.
      - run: uv run mcp-test-framework run --config config.yaml --junit-xml=results.xml
      - name: Publish test report
        if: always()
        uses: dorny/test-reporter@v2
        with:
          name: pytest
          path: results.xml
          reporter: java-junit
```

The snippet pins actions with major-version tags (`@v5`, `@v6`, `@v2`); operators who need SHA-pinning are graduating beyond this starter. The default `addopts` in `pyproject.toml` excludes the `live_homelab` and `live_ollama` markers -- to exercise live tests in CI, add a separate job that opts in to those markers explicitly.

## Troubleshooting (Windows)

- If a Ctrl+C leaves a `homelab-mcp.exe` process behind:
  `taskkill /F /IM homelab-mcp.exe`. This was the cancel-scope teardown bug
  fixed in an earlier release; it should not recur in normal operation. The CLI's
  `list-tools` and `run` paths both unwind the MCP subprocess in the same task
  that started it (see `src/mcp_test_framework/fixtures.py` and
  `src/mcp_test_framework/cli.py`).
- If `uv run mcp-test-framework` fails with "command not found" after editing
  `pyproject.toml`: re-run `uv sync` to regenerate the script shim under
  `.venv/Scripts/`.
- If `homelab-mcp` is not on `PATH` and you see `[WinError 2]`: confirm
  `mcp_server.command` and `mcp_server.args` in your `config.yaml` (e.g.
  `command: uvx, args: [homelab-mcp]` — which requires `uvx` from `uv` to
  be available).

## Further reading

- [`docs/mcp_test_framework_mvp_spec.md`](docs/mcp_test_framework_mvp_spec.md) -- authoritative design spec
- [`docs/EXTENDING.md`](docs/EXTENDING.md) -- add a new rubric, swap the judge backend
- [`.planning/PROJECT.md`](.planning/PROJECT.md) -- project mission, constraints, key decisions
- [`docs/EXTENDING.md#add-a-new-mcp-tool-target`](docs/EXTENDING.md#add-a-new-mcp-tool-target) -- add a new MCP tool target via per-tool config (no code changes)
- [`config.example.yaml`](config.example.yaml) — starter template with placeholder names and three pattern variations.
- [`examples/homelab-mcp.yaml`](examples/homelab-mcp.yaml) — complete worked example for the homelab-mcp server.
