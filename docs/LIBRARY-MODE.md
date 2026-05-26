# Library Mode — pytest-native MCP contract testing

Library mode is the recommended way to run `mcp-contracts`. You declare one
ini value in your `pyproject.toml`, write a minimal `config.yaml` for your MCP
server, and every `pytest` invocation automatically collects and runs the
framework's contract tests alongside your own tests. No separate test runner.
No wrapper script. The same `pytest` command you already use picks up the
injected contract-test surface.

This document covers the operator-facing API surface: the `mcp_config_file`
ini value, the plugin's auto-discovery wiring, the injected virtual test nodes,
the marker surface, the fixture surface, the optional domain-UI reporter, and
the `gen-test-classes` codegen CLI. For the test-code-author surface
(`mcp_session`, `tool()`, `ToolCallError`, scenario authoring conventions),
see [`docs/TEST-CODE-AUTHORING.md`](TEST-CODE-AUTHORING.md).

## Prerequisites

- `mcp-contracts` installed in your project environment (`uv add mcp-contracts`,
  then `uv sync`).
- A reachable MCP server whose command you know (e.g. `uvx homelab-mcp`).
- A `config.yaml` in your project root that names your server command and the
  tools you want to exercise. Generate a starter with
  `uv run mcp-contracts config-init -o config.yaml`. See
  `docs/EXTENDING.md` for the bootstrap flow and full config field reference.
- Ollama running at the configured base URL with the configured model (defaults:
  `http://127.0.0.1:11434`, model `qwen3.6:latest`) — required for the
  description-quality judge tests. Schema and output tests run without it.

## Quickstart (90 seconds)

```bash
uv add mcp-contracts
uv sync
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
mcp_config_file = "./config.yaml"
```

Write a minimal `config.yaml`:

```yaml
mcp_server:
  command: uvx
  args: [your-mcp-server]

tools:
  your_tool_name: {}
```

```bash
uv run pytest
```

Expected collection output:

```
<mcp-contracts>::test_input_schema_present[your_tool_name]
<mcp-contracts>::test_description_quality_clarity[your_tool_name]
<mcp-contracts>::test_description_quality_disambiguation[your_tool_name]
<mcp-contracts>::test_description_quality_parameters[your_tool_name]
<mcp-contracts>::test_output_conformance[your_tool_name]
```

## What library mode IS

- A pytest plugin (`mcp_test_framework._plugin`) auto-loaded via
  `[project.entry-points.pytest11]` — no additional configuration needed
  once `mcp-contracts` is in your environment.
- Reads one ini value (`mcp_config_file`) from your `pyproject.toml`,
  `pytest.ini`, `setup.cfg`, or any pytest-config surface.
- Injects parametrized contract tests as virtual nodeids of the form
  `<mcp-contracts>::test_<name>[<tool>]` — one set of tests per tool
  you list in your `config.yaml`.
- Plays nicely with your existing tests, fixtures, markers, and CI pipelines —
  the injected tests appear as an additional collection node, not a separate
  run.

## What library mode IS NOT

- Not a separate test runner — library mode IS pytest. Your normal `pytest`
  invocation is the entry point; nothing additional to install or invoke.
- Not a separate config language — it reads the same YAML config as the
  `mcp-contracts run` CLI.
- Not opinionated about your project layout — `mcp_config_file` resolves
  relative to your `pyproject.toml` location, not the working directory.

## The `mcp_config_file` ini value

Declare the config path once in your `pyproject.toml`:

```toml
[tool.pytest.ini_options]
mcp_config_file = "./config.yaml"
```

The plugin resolves the path relative to the directory containing your
`pyproject.toml`. Non-absolute paths are the norm; the resolution anchor
(the ini file's directory) is stable regardless of which directory you
invoke `pytest` from.

Resolution priority table:

| Source | Priority | Notes |
|--------|----------|-------|
| `pytest -o "mcp_config_file=./other.yaml"` | Highest | Useful for CI matrix runs targeting different configs |
| `[tool.pytest.ini_options] mcp_config_file = ...` | Default | Standard everyday use |
| Unset | N/A | Plugin silently no-ops — opt-out by omission; no warning emitted |

When the ini value is unset, the plugin emits no tests and does not modify
your collection in any way. You opt in by setting the ini value; you opt out
by removing it. There is no config-discovery or auto-detect behavior.

## Plugin auto-discovery

The framework declares the plugin entry point in its own `pyproject.toml`:

```toml
[project.entry-points.pytest11]
mcp_test_framework = "mcp_test_framework._plugin"
```

Once `mcp-contracts` is installed in your project's environment, pytest
auto-discovers and loads this entry point. You do NOT need to add
`pytest_plugins = [...]` to your `conftest.py` or `pyproject.toml`.
The plugin is present and active the moment you run `uv sync` and the
package appears in site-packages.

To disable the plugin entirely (while keeping the package installed),
pass `-p no:mcp_test_framework` to pytest. To keep the contract fixture
surface active but disable only the reporter plugin, pass
`-p no:mcp_test_framework_reporter` — see the reporter section below.

## Injected test surface

When `mcp_config_file` is set, the plugin injects a virtual `<mcp-contracts>`
collection node into pytest's collection tree. Each tool listed in your
`config.yaml` gets one set of parametrized contract tests:

```
<mcp-contracts>::test_input_schema_present[list_keyring_credentials]
<mcp-contracts>::test_description_quality_clarity[list_keyring_credentials]
<mcp-contracts>::test_description_quality_disambiguation[list_keyring_credentials]
<mcp-contracts>::test_description_quality_parameters[list_keyring_credentials]
<mcp-contracts>::test_output_conformance[list_keyring_credentials]
```

These virtual nodes are NOT files on disk in your project tree — they are
synthesized by the plugin from the contract-test module inside the installed
package. To find the source:

```bash
python -c "import mcp_test_framework.contracts._tests as t; print(t.__file__)"
```

To run only the injected contract tests:

```bash
pytest -m mcp_contract
```

To run everything EXCEPT the injected contract tests:

```bash
pytest -m "not mcp_contract"
```

To target one specific tool's contract tests:

```bash
pytest -k "list_keyring_credentials"
```

Note: because the virtual nodeid uses `<mcp-contracts>` with an angle-bracket
character, using `-k` with a substring match is simpler than using the full
nodeid. The `-k` filter treats the angle bracket as part of the name.

### Skipping individual test buckets per tool

Same `tools.<name>.skip_buckets` field as the CLI surface — works
identically in library mode. Use it when a tool has required input
fields and cannot satisfy the output-bucket tests. Valid test buckets
are `schema`, `judge`, and `output`. (The English word "bucket" also
appears in the runner's per-tool result aggregation — those are
*result buckets*; the values here are *test buckets*.)

Example: `create_proxmox_vm` requires VM name, node, cores, memory, etc.,
so the empty-args output check cannot succeed. Keep the schema and judge
signal while dropping the output bucket:

```yaml
tools:
  create_proxmox_vm:
    skip_buckets: ["output"]
```

Run with `--explain` to verify which (tool, bucket) cells were filtered out
at collection time:

```text
Skipping (0):

Bucket-skipped tools (1):
  create_proxmox_vm:
    bucket=output: skipped via tools.create_proxmox_vm.skip_buckets
```

The pre-run digest summarizes the same counts:

```text
Running:      1  (create_proxmox_vm)
Skipping:      0  (use --explain to list)
Bucket skips:  1  (use --explain to list)
```

The three output-bucket tests for `create_proxmox_vm` are absent from
`pytest --collect-only` — they are not collected, not rendered as
runtime-SKIPPED rows. Setting both `skip: true` and a non-empty
`skip_buckets` for the same tool is rejected at config load (the two
levers express redundant intent).

## Markers

| Marker | Auto-applied | Purpose |
|--------|--------------|---------|
| `mcp_contract` | Yes — every injected contract test | Use `pytest -m mcp_contract` to select only contract tests, or `-m "not mcp_contract"` to exclude them |
| `live_homelab` | No — operator opt-in | Applied to tests that require a live MCP server on the network; deselected by the framework's default `addopts` |
| `live_ollama` | No — operator opt-in | Applied to tests that require a reachable Ollama instance; deselected by the framework's default `addopts` |

The `mcp_contract` marker is registered by the plugin on load. You can use it
in your `pyproject.toml` `addopts` to deselect contract tests in specific CI
jobs:

```toml
[tool.pytest.ini_options]
addopts = "-m 'not mcp_contract'"
```

A framework-internal marker `parity` is used exclusively by the framework's
own test suite and is intentionally not part of the operator-facing surface.

## Fixture surface

All public fixtures exposed by the plugin are prefixed with `mcp_`:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mcp_config` | session | Parsed `Config` object loaded from `mcp_config_file` |
| `mcp_client` | session | Async `McpTestClient` connected to the configured MCP server over stdio |
| `mcp_judge` | session | `OllamaJudge` instance pointed at the configured Ollama endpoint |
| `mcp_target_tool` | function | The tool name currently under test — varies per parametrized test node |
| `mcp_rubric_clarity` | session | Judge rubric for description clarity (1–5 scale; pass threshold: 4) |
| `mcp_rubric_disambiguation` | session | Judge rubric for description disambiguation |
| `mcp_rubric_parameters` | session | Judge rubric for parameter documentation quality |

Unprefixed compatibility aliases (`config`, `judge`, `client`, `target_tool`)
continue to work in v1.4 with a `DeprecationWarning`. The aliases are removed
in v1.5. Update your `conftest.py` fixture imports to use the `mcp_` prefix
before upgrading to v1.5.

## Reporter plugin (`--mcp-domain-ui`)

The domain-UI reporter is a separate plugin loaded via its own entry-point key.
It is OFF by default. To enable it:

```bash
pytest                          # default — pytest native output only
pytest --mcp-domain-ui          # auto-detect: domain UI if TTY, off in CI
pytest --mcp-domain-ui=force    # domain UI regardless of TTY detection
pytest --mcp-domain-ui=off      # explicitly off (same as default)
```

When enabled, the reporter renders per-tool rows and a `Result:` summary line
after the test run using the same domain-language output as `mcp-contracts run`.
In TTY auto-detect mode, the reporter activates when the standard output is a
terminal and deactivates in CI environments (no TTY, `CI=true`, or a detected
CI environment variable). Use `force` to enable it unconditionally — useful
for local runs where you pipe output to a log file.

The reporter plugin is loaded under a separate entry-point key so you can
disable it while keeping the contract fixture surface active:

```bash
pytest -p no:mcp_test_framework_reporter
```

This keeps the `mcp_*` fixtures, the injected `<mcp-contracts>` tests, and
all markers working — only the domain-UI rendering after the run is suppressed.

Under `mcp-contracts run` (CLI mode), the reporter is always active (`force`
equivalent) because the CLI controls the subprocess and the output surface.

## Codegen CLI (`gen-test-classes`)

The `gen-test-classes` command generates typed `Params` and `Response` classes
from your MCP server's live `inputSchema` / `outputSchema`. It reads the SAME
`pyproject.toml` ini value that pytest uses, so no separate config argument is
needed for everyday use:

```bash
uv run mcp-contracts gen-test-classes
```

The command resolves `mcp_config_file` from your `pyproject.toml` and connects
to the MCP server to discover its current tool schemas. Override the config
path for a one-off run:

```bash
uv run mcp-contracts gen-test-classes --config ./other-config.yaml
```

The config file MUST declare `test_code.generated_root` — the directory where
generated classes are written. There is no smart default for this path; the
framework refuses to silently invent a location to write Python code into:

```yaml
test_code:
  generated_root: "tests/test_code/_generated"
```

Regenerate whenever the MCP server's declared tool schemas change upstream.
The generator overwrites only the `<generated_root>/<server_slug>/` tree.
Every generated file carries a `do not hand-edit` header; subclass generated
classes in your own scenario files rather than editing generated source.

See [`docs/TEST-CODE-AUTHORING.md`](TEST-CODE-AUTHORING.md) for the full
import patterns, the typed `Params` / `Response` attribute surface, and the
scenario authoring walkthrough that builds on generated classes.

## Error tone

Operator-facing errors from the framework follow the conventions in
[`docs/ERROR-STYLE.md`](ERROR-STYLE.md): operator terms only, one-line
summary followed by a detail block, and an actionable `next:` step at the
end of every error.

Common library-mode error scenarios:

- **`mcp_config_file` points at a path that does not exist:**
  The plugin emits `mcp_config_file points at '<path>' which does not exist`
  and fails the test session at collection time. Check the path is relative
  to your `pyproject.toml` directory, not the current working directory.

- **`tools:` allowlist is empty (no tools declared in config):**
  The plugin emits no contract tests and no warning — an empty allowlist is
  a legitimate opt-out state. If you expect tests and see none, check that
  your `config.yaml` has at least one entry under `tools:`.

- **`test_code.generated_root` not set in config:**
  `gen-test-classes` fails loud with a message naming the missing field and
  the `config-init` command to generate a starter config that includes it.
  There is no implicit fallback path.

## Running the parity gate locally

The framework ships a CLI/library parity test at
`tests/framework/parity/test_cli_vs_pytest_route.py`. This test drives both
`mcp-contracts run` (CLI route) and raw `pytest` with `mcp_config_file` set
(library route) against the same `config.test.yaml`, parses both JUnit XML
outputs, and asserts that the per-tool pass/fail outcomes are identical.

The parity test is deselected by default via the `live_homelab` and
`live_ollama` markers (the same `addopts` filter that gates all live tests).
Running it requires a populated `tools:` section in `config.test.yaml` (or an
alternate config path), plus a reachable `homelab-mcp` server and Ollama
instance. To run it explicitly:

```bash
pytest -m "parity and live_homelab and live_ollama" tests/framework/parity/
```

Pass `-o "mcp_config_file=./my-populated-config.yaml"` to point at a config
that has at least one tool enabled — `config.test.yaml` ships with an empty
`tools: {}` by default to keep the framework's own CI from requiring live
infrastructure.

## Test-code scenarios (test-code-author surface)

Library mode and CLI mode share the same test-code surface: `mcp_session`,
`tool()`, `ToolCallError`, and the generated `Params` / `Response` classes.
Nothing in the library-mode delivery is specific to test-code authoring.

For the complete test-code-author walkthrough — module-scope yield fixtures,
cross-file ordering, the conditional skip recipe, the `ToolCallError` surface,
and the `inputSchema` workaround pattern — see
[`docs/TEST-CODE-AUTHORING.md`](TEST-CODE-AUTHORING.md).
