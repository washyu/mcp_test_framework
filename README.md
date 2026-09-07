# mcp_test_framework

Pytest-native MCP contract testing — for any MCP server, configured via one ini line.

## Quickstart

```bash
uv add mcp-contracts
uv sync
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
mcp_config_file = "./config.yaml"
```

```bash
uv run pytest
```

## Library mode (recommended)

Library mode is the recommended way to run `mcp-contracts`. Declare one line in
your `pyproject.toml`, write a minimal `config.yaml`, and every `pytest`
invocation automatically collects and runs contract tests alongside your own
tests. No separate test runner. No wrapper script.

### Add one line to pyproject.toml

```toml
[tool.pytest.ini_options]
mcp_config_file = "./config.yaml"
```

### Write a minimal config.yaml

```yaml
mcp_server:
  command: uvx
  args: [your-mcp-server]

tools:
  your_tool_name: {}
```

For a complete config surface, see [`config.example.yaml`](config.example.yaml).
Generate a starter config for your server with
`uv run mcp-contracts config-init -o config.yaml`.

### Run pytest

```bash
uv run pytest
```

The plugin injects parametrized contract tests as virtual nodeids:

```
<mcp-contracts>::test_input_schema_present[your_tool_name]
<mcp-contracts>::test_description_quality_clarity[your_tool_name]
<mcp-contracts>::test_description_quality_disambiguation[your_tool_name]
<mcp-contracts>::test_description_quality_parameters[your_tool_name]
<mcp-contracts>::test_output_conformance[your_tool_name]
```

These virtual nodes are synthesized by the plugin — not files on disk in your
project tree. They appear alongside your existing tests in the same `pytest`
run. Use `-m mcp_contract` to select only the injected contract tests, or
`-m "not mcp_contract"` to exclude them.

For full depth on the plugin — auto-discovery wiring, marker surface, fixture
surface, reporter opt-in — see
[`docs/LIBRARY-MODE.md`](docs/LIBRARY-MODE.md).

### Domain UI reporter (opt-in)

To enable the domain-language output format alongside pytest's native output:

```bash
uv run pytest --mcp-domain-ui
```

Produces per-tool rows and a `Result:` summary line after the run. Uses
TTY auto-detection by default; pass `--mcp-domain-ui=force` to enable
unconditionally. See [`docs/LIBRARY-MODE.md`](docs/LIBRARY-MODE.md) for
the full reporter documentation.

### Codegen CLI

Generate typed `Params` and `Response` classes from your MCP server's live
schemas — used when writing test-code scenarios:

```bash
uv run mcp-contracts gen-test-classes
```

Reads the same `pyproject.toml` ini value as pytest. See
[`docs/LIBRARY-MODE.md`](docs/LIBRARY-MODE.md) for the `test_code.generated_root`
requirement and [`docs/TEST-CODE-AUTHORING.md`](docs/TEST-CODE-AUTHORING.md) for
the full test-code-author walkthrough.

## Sample green run

```text
========================================
MCP Test Framework
========================================
MCP server:  uvx homelab-mcp
Discovered:  58 tools
Running:      2  (list_keyring_credentials, suggest_deployments)
Skipping:    56  (use --explain to list)
Judges:      clarity, disambiguation, parameters
Test plan:   20 contract cases

passing:
  list_keyring_credentials  ✓ PASS
  suggest_deployments       ✓ PASS

Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s
```

The first nine lines are the **pre-run digest** -- the wrapper computes the
running / skipping counts from `cfg.tools` and the live tool list returned by
the MCP server, then prints the digest before pytest's subprocess starts. The
two `✓ PASS` rows are the **post-run** per-tool view, one row per tool that
actually ran, sorted FAIL → SKIP → PASS within each verdict bucket. The final
`Result:` line is the parametrized-case summary parsed back out of the
internal JUnit XML.

Skipped tools (`Skipping: 56` in the example) are absent from the per-tool
row block under the default surface -- their counts roll into the `Result:`
line's `SKIP` segment at the parametrized-case level (56 tools × 10 cases =
560 SKIP cases). Pass `--explain` to see each skipped tool with its reason
between the digest and the pytest subprocess. Pass `--debug` to append raw
pytest output and failure tracebacks after the per-tool rows.

If you enable a tool whose declared description does not satisfy the
description-quality rubrics, the test fails with the judge's reasoning
surfaced after an em-dash on the FAIL row, e.g.:

```
list_registered_servers  ✗ FAIL — clarity score 2/5: description is too terse for an agent to disambiguate from related tools
```

The same reasoning is recorded in the JUnit XML's `<failure message="…">`.
Either tweak the tool's description upstream, or skip the tool in your config
(per the "Per-tool configuration" section above).

## test-code scenarios

Beyond the contract pass, test-code authors write stateful scenarios under
`tests/test_code/` -- create resources, verify shape, tear down. Each scenario
module renders as a per-tool group with nested rows under the same domain UI
the contract pass uses. The sample below runs against a live Proxmox cluster
(gated by `MCPTF_DOGFOOD_PROXMOX_HOST`) and is shown here mid-failure: the
upstream `homelab-mcp` `manage_proxmox_vm`-family `inputSchema` reports
`type: "string"` on optional fields and defaults them to `null` in the same
schema -- the framework surfaces that contract bug as a real test failure
instead of masking it (framework primitives; test-code author owns safety).
The `_CpuBumpManageVmParams(extra="allow")` workaround pattern is documented
in [`docs/TEST-CODE-AUTHORING.md`](docs/TEST-CODE-AUTHORING.md). Run scenarios
with `mcp-contracts run --test-code`.

<!-- mirrors live runner output — re-run the framework and refresh this block when the operator-facing output format changes; see docs/TEST-CODE-AUTHORING.md for the test-code mode digest contract -->

```python
# tests/test_code/test_proxmox_vm_lifecycle.py
"""test-code sample: 2-test VM-lifecycle scenario against a live Proxmox cluster.

Requires MCPTF_DOGFOOD_PROXMOX_HOST. See docs/TEST-CODE-AUTHORING.md for the
full walkthrough (module-scope fixtures, cross-file ordering, conditional skip
recipe, inputSchema workaround).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import pytest
import pytest_asyncio

from mcp_test_framework.test_code import ToolCallError, mcp_session, tool
from tests.test_code._generated.homelab_mcp import (
    CreateProxmoxVmParams,
    CreateProxmoxVmResponse,
    DeleteProxmoxVmParams,
)


@dataclass
class ProxmoxVmLifecycleState:
    created: CreateProxmoxVmResponse


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def proxmox_vm_lifecycle(mcp_session):
    host = os.environ["MCPTF_DOGFOOD_PROXMOX_HOST"]
    node = os.environ.get("MCPTF_DOGFOOD_PROXMOX_NODE", "pve")
    vmid = 9990  # pick a free VMID in your range; see docs/TEST-CODE-AUTHORING.md

    created = await tool("create_proxmox_vm").call(
        CreateProxmoxVmParams(host=host, name="mcptf-sample", node=node, vmid=vmid, cores=1)
    )
    state = ProxmoxVmLifecycleState(created=created)
    try:
        yield state
    finally:
        try:
            await tool("delete_proxmox_vm").call(
                DeleteProxmoxVmParams(node=node, vmid=vmid, host=host)
            )
        except ToolCallError:
            pass  # teardown is best-effort


@pytest.mark.asyncio(loop_scope="session")
async def test_create_returns_pending_vm(proxmox_vm_lifecycle):
    state = proxmox_vm_lifecycle
    assert state.created.is_error is False
    assert isinstance((state.created.data or {}).get("vmid"), int)


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_returns_ok(proxmox_vm_lifecycle):
    vmid = (proxmox_vm_lifecycle.created.data or {}).get("vmid")
    node = os.environ.get("MCPTF_DOGFOOD_PROXMOX_NODE", "pve")
    host = os.environ["MCPTF_DOGFOOD_PROXMOX_HOST"]
    result = await tool("delete_proxmox_vm").call(
        DeleteProxmoxVmParams(node=node, vmid=vmid, host=host)
    )
    assert result.is_error is False
```

```text
========================================
MCP Test Framework (test-code)
========================================
MCP server:  uvx homelab-mcp
Discovered:  1 scenarios
Running:      1  (proxmox_vm_lifecycle)
Skipping:     0  (use --explain to list)
Judges:      (none — test-code scope)

skipped:
  analyze_network_topology                 – SKIP — not selected in config
  bulk_discover_and_map                    – SKIP — not selected in config
  check_ansible_service                    – SKIP — not selected in config
  check_service_requirements               – SKIP — not selected in config
  clone_proxmox_vm                         – SKIP — not selected in config
  control_vm                               – SKIP — not selected in config
  create_infrastructure_backup             – SKIP — not selected in config
  create_proxmox_lxc                       – SKIP — not selected in config
  create_proxmox_vm                        – SKIP — not selected in config
  decommission_device                      – SKIP — not selected in config
  decommission_device_preview              – SKIP — not selected in config
  delete_proxmox_vm                        – SKIP — not selected in config
  delete_proxmox_vm_preview                – SKIP — not selected in config
  deploy_infrastructure                    – SKIP — not selected in config
  deploy_vm                                – SKIP — not selected in config
  destroy_terraform_service                – SKIP — not selected in config
  destroy_terraform_service_preview        – SKIP — not selected in config
  discover_and_map                         – SKIP — not selected in config
  get_device_changes                       – SKIP — not selected in config
  get_network_sitemap                      – SKIP — not selected in config
  get_proxmox_node_status                  – SKIP — not selected in config
  get_proxmox_script_info                  – SKIP — not selected in config
  get_proxmox_vm_status                    – SKIP — not selected in config
  get_service_info                         – SKIP — not selected in config
  get_service_status                       – SKIP — not selected in config
  get_vm_logs                              – SKIP — not selected in config
  get_vm_status                            – SKIP — not selected in config
  install_service                          – SKIP — not selected in config
  list_available_services                  – SKIP — not selected in config
  list_keyring_credentials                 – SKIP — not selected in config
  list_proxmox_resources                   – SKIP — not selected in config
  list_registered_servers                  – SKIP — not selected in config
  list_vms                                 – SKIP — not selected in config
  manage_proxmox_vm                        – SKIP — not selected in config
  plan_terraform_service                   – SKIP — not selected in config
  purge_devices                            – SKIP — not selected in config
  purge_devices_preview                    – SKIP — not selected in config
  purge_failed_discoveries                 – SKIP — not selected in config
  refresh_terraform_service                – SKIP — not selected in config
  register_server                          – SKIP — not selected in config
  remove_device                            – SKIP — not selected in config
  remove_device_preview                    – SKIP — not selected in config
  remove_vm                                – SKIP — not selected in config
  remove_vm_preview                        – SKIP — not selected in config
  rollback_infrastructure_changes          – SKIP — not selected in config
  rollback_infrastructure_changes_preview  – SKIP — not selected in config
  run_ansible_playbook                     – SKIP — not selected in config
  scale_services                           – SKIP — not selected in config
  scan_infrastructure_drift                – SKIP — not selected in config
  search_proxmox_scripts                   – SKIP — not selected in config
  ssh_discover                             – SKIP — not selected in config
  ssh_execute_command                      – SKIP — not selected in config
  start_interactive_shell                  – SKIP — not selected in config
  suggest_deployments                      – SKIP — not selected in config
  update_device_config                     – SKIP — not selected in config
  update_device_fingerprint                – SKIP — not selected in config
  update_device_fingerprint_preview        – SKIP — not selected in config
  validate_infrastructure_changes          – SKIP — not selected in config
proxmox_vm_lifecycle
  ✗ create_returns_pending_vm — failed on setup with "mcp_test_framework.test_code.ToolCallError: Input validation error: None is not of type 'string'"
  ✗ delete_returns_ok — failed on setup with "mcp_test_framework.test_code.ToolCallError: Input validation error: None is not of type 'string'"

Result: 0 PASS / 2 FAIL / 58 SKIP  in 6.2s
```

The two `✗` rows above are the framework doing its job: a real upstream
contract bug surfaced as a failing test, with the `ToolCallError` reason
quoted verbatim on the row. See
[`docs/TEST-CODE-AUTHORING.md`](docs/TEST-CODE-AUTHORING.md) for the full
authoring walkthrough -- module-scope fixtures, cross-file ordering, the
conditional skip recipe for scenarios that require live infrastructure, and
the `_CpuBumpManageVmParams(extra='allow')` workaround for the inputSchema
bug shown above.

Default `mcp-contracts run` collects only `tests/contract/`; the
`--test-code` flag opts the test-code scope into the run. See the
[Appendix: CLI usage](#appendix-cli-usage) section below for full flag composition.

### Codegen-driven smoke scenarios for required-field tools

For tools like `create_proxmox_vm` that declare required input fields, add an
`examples:` block to `config.yaml`, run `mcp-contracts gen-test-classes`, and
the framework emits `tests/test_code/_generated/<server>/<tool>_call_smoke.py`
— a typed smoke scenario that calls the tool with your supplied arguments under
the existing `mcp_session` fixture. No hand-authoring required for the basic
call-and-assert pattern.

```yaml
# config.yaml
tools:
  create_proxmox_vm:
    skip_buckets: ["output"]   # drop the empty-args output bucket
    examples:
      - vmid: 9001
        name: smoke-test-vm
        node: pve1
        host: pve1
```

The `skip_buckets` + `examples:` pairing is the operator's call — the framework
does not auto-pair these fields (operator decides). See the
[Skipping individual test buckets per tool](#skipping-individual-test-buckets-per-tool)
section below for the `skip_buckets` walkthrough and
[`docs/LIBRARY-MODE.md`](docs/LIBRARY-MODE.md#codegen-driven-smoke-scenarios-for-required-field-tools)
for the full `examples:` field reference.

## Configuration

Precedence: **CLI flag > env var > `.env` > YAML overlay > default**.

Library-mode operators set the config path via `[tool.pytest.ini_options]
mcp_config_file = "./config.yaml"` in `pyproject.toml`. CLI operators pass
`--config PATH` to `mcp-contracts run`.

| Env Var | Default | Purpose |
|---------|---------|---------|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server base URL. |
| `OLLAMA_MODEL` | `qwen3.6:latest` | Ollama model name used by the judge. |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Per-request HTTP timeout for Ollama calls. |
| `MCP_SERVER_COMMAND` | `homelab-mcp` | MCP server launcher binary. |
| `MCP_SERVER_ARGS` | `[]` (JSON list) | Args passed to the launcher (JSON list). |
| `MCP_SERVER_TIMEOUT_SECONDS` | `30` | Per-SDK-call timeout for stdio operations. |
| `JUDGE_TIMEOUT_SECONDS` | `120` | Outer-budget cap on judge calls. |

Configure the framework via `config.yaml` — generate a starter with
`mcp-contracts config-init -o config.yaml` and pass it via
`--config config.yaml`. Env vars are reserved for CI-secret passthrough only
(see `.env.example`); they no longer override config values. The framework
does not auto-discover a `config.yaml` in the current directory; the path
must be explicit (via `--config` for the CLI or
`[tool.pytest.ini_options] mcp_config_file = PATH` for library mode).

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

Replace the placeholder tool names below with the names from your `mcp-contracts list-tools` output.

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

### Skipping individual test buckets per tool

Some tools have required input fields and cannot satisfy the output-bucket
tests (which call the tool with no arguments by default). Use `skip_buckets`
on the per-tool entry to opt out of named test buckets while keeping the
others enabled. Valid test buckets are `schema`, `judge`, and `output`.
(The English word "bucket" also appears in the runner's per-tool result
aggregation — those are *result buckets*; the values here are *test
buckets*.)

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

The third per-tool knob, `call_arguments: {key: value}`, lets you pass fixed arguments to the tool's `call_tool` invocation -- useful when the tool requires non-empty input. See `config.example.yaml` for shape.

For a complete real-server config, see [`config.example.yaml`](config.example.yaml).

## Host isolation: strict vs passthrough

By default (`host_isolation: strict`), the framework spawns the MCP subprocess
with an isolated environment — narrow `PATH`/`SYSTEMROOT` allowlist, a per-session
tempdir as `HOME`/`USERPROFILE`, and a null keyring backend — so test runs are
reproducible and your real credentials never leak into a subprocess under test.

Canonical worked example where you need the opposite: an operator has Proxmox
credentials in their keyring (`uvx homelab-mcp credentials list` confirms),
wants to drive `homelab-mcp create_proxmox_vm` against their cluster, but under
strict mode the spawned subprocess sees `No Proxmox credentials found` because
the null keyring backend hides them. Opt into passthrough:

```yaml
# config.yaml
host_isolation: passthrough  # operator's real env reaches the MCP subprocess
```

Same scenario, before / after:

```text
# host_isolation: strict (default)
create_proxmox_vm  ✗ FAIL — No Proxmox credentials found

# host_isolation: passthrough
create_proxmox_vm  ✓ PASS — VM created (vmid=9001)
```

Passthrough is incompatible with pytest-xdist parallelism. When you also pass
`-n N`, the plugin clamps to a single worker at session start and emits:

```text
xdist worker count clamped to 1

host_isolation=passthrough serializes subprocess spawns so the operator's
credentials remain a single-owner resource.

next: switch to host_isolation=strict for parallel xdist runs
```

**Locks (read before opting in):**

- **Operator owns safety.** The framework does not reason about which tools or
  env vars are "dangerous"; passthrough hands the subprocess your full
  environment and you choose which scenarios to run.
- **No keyring faking.** The framework will not synthesize credentials or
  virtualize the keyring; passthrough delegates fully to your real host env.
- **xdist trade-off.** Strict preserves `-n N`; passthrough clamps to 1.

## Appendix: CLI usage

The `mcp-contracts` CLI provides a self-contained test runner that does not
require the `[tool.pytest.ini_options]` ini route. All CLI commands continue
to ship in v1.4 and are not deprecated.

### Run against the example homelab-mcp stack

If you want to try the framework against the example `homelab-mcp` server:

#### Prerequisites

- Python 3.12 or newer
- [`uv`](https://docs.astral.sh/uv/) (project, venv, and lockfile manager)
- [Ollama](https://ollama.com/) running at the configured base URL with the configured
  model (defaults: `http://127.0.0.1:11434`, model `qwen3.6:latest`)
- `homelab-mcp` runnable via `uvx`, or installed on `PATH`

#### Setup

```bash
git clone <repo-url>
cd mvp_test_framework
uv sync
```

`uv sync` installs the runtime + dev dependencies and registers the
`mcp-contracts` console script under `.venv/Scripts/` (Windows) or
`.venv/bin/` (Unix).

**Legacy script alias:** the legacy console-script was removed in v1.5.
Invoking it now prints an operator-tone message to stderr pointing at
`mcp-contracts` and exits non-zero — every subcommand and every flag
is unchanged, only the script name moved. Use `mcp-contracts` directly
for all invocations.

### Run the test suite

```bash
uv run mcp-contracts run --config config.yaml
uv run mcp-contracts run --config ./config.yaml
uv run mcp-contracts run --config config.yaml -- -x --lf -k schema
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

#### Run output shape

Default `run` output is split into a **pre-run digest** (emitted before pytest's
subprocess starts) and a **post-run** block of per-tool rows + a `Result:`
summary line. The pre-run digest shows the MCP server command, the discovered
tool count, the running / skipping tool counts, the active judges, and the
total contract test-plan size. The `Skipping (N)` count carries a
`(use --explain to list)` hint -- pass `--explain` to expand it inline.

Canonical small-N example:

```
========================================
MCP Test Framework
========================================
MCP server:  uvx homelab-mcp
Discovered:  58 tools
Running:      2  (list_keyring_credentials, suggest_deployments)
Skipping:    56  (use --explain to list)
Judges:      clarity, disambiguation, parameters
Test plan:   20 contract cases

passing:
  list_keyring_credentials  ✓ PASS
  suggest_deployments       ✓ PASS

Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s
```

Flags that reshape this output:

| Flag | Effect |
|------|--------|
| `--explain` | Expands the pre-run digest's `Skipping (N) (use --explain to list)` hint into one alphabetically-sorted line per skipped tool with its reason. Renders inline between the digest and the pytest subprocess. Wrapper-owned; never forwarded to pytest. Ignored under `--raw` and under `-q` / `--quiet`. |
| `-q` / `--quiet` | Suppresses the pre-run digest, the `--explain` expansion (if also passed), and the per-tool rows. Emits only the final `Result: N PASS / M FAIL [/ S SKIP]  in T.Ts` line (the `SKIP` segment is omitted entirely when zero skips; double space before `in` is literal). Mirrors v1.1's quiet-mode parity for CI consumers that want a single-line summary. |
| `--raw` | Bypasses the domain UI entirely and streams pytest's native output. `--explain` is a no-op under `--raw` (the wrapper-side renderer is skipped). All flags after `--` still forward to pytest verbatim. |
| `--debug` | Appends raw pytest output and failure tracebacks after the per-tool rows + summary. Compatible with `--explain` -- both surfaces render. |
| `--with-framework` | Also collects `tests/framework/`. The digest's `Test plan:` line gains a `+ framework self-tests` continuation. Under `--explain`, the `Skipping (N):` block lists tool-side skips only (framework tests have no per-tool skip semantics). |

##### `--explain` example

`--explain` drops the `(use --explain to list)` hint and renders the list
inline between the digest and the pytest subprocess:

```
$ mcp-contracts run --config config.yaml --explain
========================================
MCP Test Framework
========================================
MCP server:  uvx homelab-mcp
Discovered:  58 tools
Running:      2  (list_keyring_credentials, suggest_deployments)
Skipping:    56
Judges:      clarity, disambiguation, parameters
Test plan:   20 contract cases

Skipping (56):
  bulk_update_inventory       — explicit skip in config
  delete_server               — explicit skip in config
  ... (52 more, alphabetical) ...
  zone_reset                  — not selected in config

(pytest subprocess runs here, then per-tool rows + Result: line)
```

Skip reasons come from your `tools.<name>.skip_reason` if set; otherwise the
framework emits one of two defaults: `"not selected in config"` for tools not
listed under `tools:` at all, or `"explicit skip in config"` for tools with
`skip: true` but no `skip_reason`. Output is grep-able (one tool per line) and
scales to homelab-mcp's full ~70-tool surface.

### List MCP server tools

```bash
uv run mcp-contracts list-tools --config config.yaml
uv run mcp-contracts list-tools --config config.yaml --json
```

Default output is indented blocks (tool name on one line, the full wrapped
description indented beneath). `--json` emits a JSON array of full MCP tool
records (`name`, `description`, `inputSchema`, `outputSchema`) sorted
alphabetically by name. `list-tools` does **not** invoke pytest or the LLM
judge -- it is a quick discovery surface for whatever the server exposes.

### Show the version

```bash
uv run mcp-contracts version
```

### Testing an MCP server you didn't write

The framework treats your MCP server as a black box — you don't need to read
its source. `mcp-contracts list-tools` shows you the tools the server
exposes and their parameter shapes; `mcp-contracts config-init` scaffolds
a config file populated with the actual tools you have. Designed for operators
testing servers they didn't author.

The full walkthrough lives in [`docs/EXTENDING.md`](docs/EXTENDING.md#testing-an-mcp-server-you-didnt-write).

### Isolation guarantee

Test runs do not mutate `~/.homelab_mcp/` real-state files. The framework spawns the MCP subprocess with `HOME` and `USERPROFILE` overridden to a per-session temporary directory, so the server reads/writes its state inside the tempdir and never touches your real-state files.

```bash
uv run pytest tests/framework/test_isolation.py -v
```

The test in `tests/framework/test_isolation.py` computes sha256 hashes of `~/.homelab_mcp/credential_registry.json`, `~/.homelab_mcp/known_hosts`, and `~/.homelab_mcp/migration_state.json` before and after a full session and asserts byte-identical equality. Test runs also route the OS keyring through a null backend, so credentials are not read or written.

### CI integration

Run the suite in CI with `--junit-xml=` and ingest the result with a JUnit-aware action. The snippet below runs the default unit slice (live markers excluded by `pyproject.toml`'s `addopts`).

```yaml
# .github/workflows/test.yml -- GitHub Actions starter.
# On Jenkins / GitLab CI / CircleCI, translate the `runs-on` / `uses` /
# `with` keys to the equivalent runner + action concepts. The CLI invocation
# (`uv run mcp-contracts run --config config.yaml --junit-xml=results.xml`) is portable.
name: tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: "3.12"
      - run: uv sync
      # Default addopts in pyproject.toml excludes live_homelab + live_ollama markers.
      - run: uv run mcp-contracts run --config config.yaml --junit-xml=results.xml
      - name: Publish test report
        if: always()
        uses: dorny/test-reporter@v2
        with:
          name: pytest
          path: results.xml
          reporter: java-junit
```

The snippet pins actions with major-version tags (`@v5`, `@v6`, `@v2`); operators who need SHA-pinning are graduating beyond this starter. The default `addopts` in `pyproject.toml` excludes the `live_homelab` and `live_ollama` markers -- to exercise live tests in CI, add a separate job that opts in to those markers explicitly.

### Troubleshooting (Windows)

- If a Ctrl+C leaves a `homelab-mcp.exe` process behind:
  `taskkill /F /IM homelab-mcp.exe`. This was the cancel-scope teardown bug
  fixed in an earlier release; it should not recur in normal operation. The CLI's
  `list-tools` and `run` paths both unwind the MCP subprocess in the same task
  that started it (see `src/mcp_test_framework/fixtures.py` and
  `src/mcp_test_framework/cli.py`).
- If `uv run mcp-contracts` fails with "command not found" after editing
  `pyproject.toml`: re-run `uv sync` to regenerate the script shim under
  `.venv/Scripts/`.
- If `homelab-mcp` is not on `PATH` and you see `[WinError 2]`: confirm
  `mcp_server.command` and `mcp_server.args` in your `config.yaml` (e.g.
  `command: uvx, args: [homelab-mcp]` — which requires `uvx` from `uv` to
  be available).

## Links

- [Library mode reference](docs/LIBRARY-MODE.md) — plugin auto-discovery, `mcp_config_file` ini value, fixture surface, reporter, codegen CLI
- [Test-code authoring](docs/TEST-CODE-AUTHORING.md) — module-scope fixtures, codegen regen, cross-file ordering, conditional skip recipe, `ToolCallError` surface
- [Extending the framework](docs/EXTENDING.md) — add a new rubric, swap the judge backend, bootstrap flow for a new MCP server
- [Error tone style](docs/ERROR-STYLE.md) — operator-facing error message conventions
- [`config.example.yaml`](config.example.yaml) — starter template with placeholder names and three pattern variations
- [`examples/homelab-mcp.yaml`](examples/homelab-mcp.yaml) — complete worked example for the homelab-mcp server
