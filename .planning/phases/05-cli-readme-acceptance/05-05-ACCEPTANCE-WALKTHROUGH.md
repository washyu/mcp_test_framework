# Phase 5 Acceptance Walkthrough

**Captured:** 2026-05-06
**Executor:** Claude Code execute-phase (sequential, main worktree)
**Host:** Windows 11 Home 10.0.26200, PowerShell, Python 3.14.3
**Live services:** homelab-mcp via `uvx homelab-mcp` (cold-start each invocation), Ollama at http://127.0.0.1:11434, model `qwen3.6:latest`

## Pre-flight

### Ollama reachability + model presence

```powershell
curl.exe -s http://127.0.0.1:11434/api/tags | findstr qwen3.6
# preflight-ollama-exit=0
```

Output (single JSON line) contained `"name":"qwen3.6:latest"` along with five other models (qwen3-coder-next, nomic-embed-text, deepseek-r1, gpt-oss, phi4). Ollama reachable, target model loaded.

### `uvx homelab-mcp --help` invocable

```powershell
uvx homelab-mcp --help
```

Output (first 15 lines):

```text
usage: python.exe <home>\AppData\Local\uv\cache\archive-v0\VOAyoI199Rl6EAPPV0hE1\Scripts\homelab-mcp
       [-h] [--version] [--http] [--host HOST] [--port PORT] [--no-auth]
       [--api-key API_KEY] [--ssl-cert SSL_CERT] [--ssl-key SSL_KEY]
       {credentials} ...

Homelab MCP Server - AI-powered homelab infrastructure management

positional arguments:
  {credentials}
    credentials        Manage stored credentials

options:
  -h, --help           show this help message and exit
  --version            show program's version number and exit
  --http               Run in HTTP mode instead of stdio mode
```

`uvx homelab-mcp` resolves and prints help. (The `Select-Object -First 15` pipeline closing produced exit code -1, which is the truncation signal, not a homelab-mcp failure.)

---

## SC#1 / SC#6: `mcp-test-framework run` against live homelab-mcp + Ollama

### `uv sync` (clean install)

```powershell
cd <home>\projects\mvp_test_framework
uv sync
# uv-sync-exit=0
```

```text
Resolved 46 packages in 0.76ms
Checked 46 packages in 3ms
```

uv-sync-exit=0.

### Live test run (with `TARGET_TOOL_NAME=list_keyring_credentials`)

After the SC#6 disambiguation finding (see "## SC#6 Note" below) the documented
default target tool was switched from `list_registered_servers` to
`list_keyring_credentials`. The live re-run with the new default produces a
fully green pytest exit:

```powershell
uv run mcp-test-framework run 2>&1 | Tee-Object -FilePath "$env:TEMP\plan05-run-output-keyring.txt"
# run-exit=0
```

Output (verbatim):

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

============================== warnings summary ===============================
.venv\Lib\site-packages\_pytest\config\__init__.py:1309
  <home>\projects\mvp_test_framework\.venv\Lib\site-packages\_pytest\config\__init__.py:1309: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; anyio
    self._mark_plugins_for_rewrite(hook, disable_autoload)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 67 passed, 5 deselected, 1 warning in 22.02s =================
run-exit=0
```

**run-exit=0**, 67 passed, 5 deselected (the live-marker smoke tests gated by
`-m 'not live_homelab and not live_ollama'`), 0 failed. The
`test_description_disambiguation` test that previously failed against
`list_registered_servers` now passes against `list_keyring_credentials`'s
description (see Phase 04.1 `04.1-RUN-list_keyring.txt` for an earlier 10/10
green confirmation against the same tool).

### SC#1 / SC#6 status

- **SC#1 (CLI-01):** PASS — `mcp-test-framework run` correctly resolves config,
  invokes `pytest.main()`, forwards args via `--`, and exits with pytest's exit
  code (0 on the green run above).
- **SC#6 (clean-clone exits 0):** PASS — `uv sync && uv run mcp-test-framework
  run` produces standard pytest terminal output and exits 0 against live
  homelab-mcp + Ollama with the documented default tool
  (`list_keyring_credentials`).

## SC#6 Note: target-tool switch

The first SC#1/SC#6 walkthrough attempt (with the original Phase 04 default
`TARGET_TOOL_NAME=list_registered_servers`) reproducibly failed
`test_description_disambiguation` with `score=3 < 4` from the qwen3.6:latest
judge at `temperature=0`. The judge's reasoning was substantive:

> "The description clearly states the tool's function (listing servers) and
> key output details (SSH credentials, status). However, it lacks specific
> disambiguation criteria to distinguish it from similar tools (e.g.,
> 'list_all_servers' vs 'list_active_servers' or 'get_server_details'). It
> describes *what* the tool does but not *when* to choose it over alternatives,
> which is the core requirement of the disambiguation dimension."

That is the framework's value proposition working as designed: catching a
real description-quality gap with reasoned criticism.

**Resolution (user decision):** switch the documented default from
`list_registered_servers` to `list_keyring_credentials`, which previously passed
the same rubric in Phase 04.1 (see
`.planning/phases/04.1-mcp-client-teardown-fix/04.1-RUN-list_keyring.txt` —
10/10 PASSED at `score >= 4`). The tests are tool-agnostic — they read
`TARGET_TOOL_NAME` from config via the `target_tool` fixture — so the switch
is a one-line change in `.env.example` + `config.example.yaml` (chore commit
`6d1974a`). The pre-existing test filename
`tests/test_homelab_list_registered_servers.py` is a Phase 04 artifact and
stays as-is.

**Tracked upstream:** The `list_registered_servers` description gap (no
disambiguation hint about when to pick it over other listing tools) is a
homelab-mcp doc fix to track. Once that lands, switching the default back is
a single edit; the framework will catch the description-quality regression
automatically on the next live run.

---

## SC#2: `mcp-test-framework list-tools` (text + --json)

### Text output

```powershell
uv run mcp-test-framework list-tools 2>&1 | Tee-Object -FilePath "$env:TEMP\plan05-list-tools-text.txt"
# list-tools-text-exit=0
```

Output excerpt (homelab-mcp init logs to stderr, then 58 tools alphabetically):

```text
INFO:homelab_mcp.resource_manager:Initializing ResourceManager
INFO:homelab_mcp.resource_manager:ResourceManager initialized successfully
INFO:homelab_mcp.server:Server lifespan started -- ResourceManager ready
INFO:mcp.server.lowlevel.server:Processing request of type ListToolsRequest
INFO:homelab_mcp.server:Shutting down ResourceManager...
INFO:homelab_mcp.resource_manager:Shutting down ResourceManager
INFO:homelab_mcp.resource_manager:ResourceManager shut down
INFO:homelab_mcp.server:ResourceManager shutdown complete
analyze_network_topology
  Analyze the network topology and provide insights about the discovered
  devices

bulk_discover_and_map
  Discover multiple devices via SSH and store them in the network site map
  database

check_ansible_service
  Check the status of an Ansible-managed service deployment
[...]
list_registered_servers
  List all registered servers with their SSH credentials and connection status
[...]
validate_infrastructure_changes
  Validate infrastructure changes before applying them
list-tools-text-exit=0
```

- 58 tools printed alphabetically by name
- Each tool name on its own line, full description wrapped + indented two spaces beneath
- `list_registered_servers` (the target tool under test) appears in the list with its declared description
- list-tools-text-exit=0
- Subprocess teardown clean (final stderr line before stdout is `ResourceManager shutdown complete`)

### JSON output

```powershell
uv run mcp-test-framework list-tools --json 2>&1 | Tee-Object -FilePath "$env:TEMP\plan05-list-tools-json.txt"
# list-tools-json-exit=0
```

Output is a JSON array (64.8 KB). First record:

```json
{
  "name": "analyze_network_topology",
  "description": "Analyze the network topology and provide insights about the discovered devices",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  },
  "outputSchema": null
}
```

### ConvertFrom-Json verification

```powershell
$raw = & uv run mcp-test-framework list-tools --json 2>$null
$jsonText = ($raw -join "`n").Substring(($raw -join "`n").IndexOf("["))
$tools = $jsonText | ConvertFrom-Json
$first = $tools | Select-Object -First 1
```

Output:

```text
JSON_PARSE_OK
tool_count=58
first_name=analyze_network_topology
first_keys=name,description,inputSchema,outputSchema
```

- JSON parses via `ConvertFrom-Json` without error
- 58 tools (matches text-output count)
- First record has exactly the four required keys: `name`, `description`, `inputSchema`, `outputSchema`

### SC#2 status

PASS. Both text and JSON outputs work; JSON parses cleanly via `ConvertFrom-Json`; alphabetical ordering preserved across both modes; full MCP tool record (4 keys) emitted in JSON mode.

---

## SC#3: `mcp-test-framework version`

```powershell
uv run mcp-test-framework version 2>&1
# version-exit=0
```

Output:

```text
0.1.0
version-exit=0
```

- version-exit=0
- stdout matches `^[0-9]+\.[0-9]+\.[0-9]+$` (exactly `0.1.0` plus newline)

### SC#3 status

PASS.

---

## OPS-03 (SC#4)

**RESERVED — to be filled in by Task 3 (manual UAT).**

This section will capture:

- Pre-condition `Get-Process homelab-mcp` empty output
- 3 separate Ctrl+C attempts on `uv run mcp-test-framework list-tools` with their exit codes
- 3 separate post-Ctrl+C `Get-Process homelab-mcp` outputs (must be empty)
- Summary line: `OPS-03: 3/3 attempts passed -- no zombie homelab-mcp.exe after Ctrl+C`

---

## SC#5: README documents setup, configuration, run, troubleshooting

Plan 04 verified the README content via grep + the `.planning/phases/05-cli-readme-acceptance/05-04-SYNC-CHECK.txt` artifact (8 OK env-var rows + MCPTF_CONFIG_FILE OK + precedence OK + 0 MISSING). Plan 05's contribution is replacing the `<!-- TODO Plan 05 -->` placeholder in `## Sample green run` with a real captured excerpt from the live run above.

After this plan's edit, README.md `## Sample green run` contains a 13-line excerpt of the actual live green run output:

- Test session header with platform / Python / pytest / pluggy versions
- Plugins line (anyio, asyncio)
- asyncio mode + scope config
- Collection line (72 items / 5 deselected / 67 selected)
- Per-file dot progress markers across 6 test modules (all dots, no F)
- Final summary line `67 passed, 5 deselected, 1 warning in 22.02s` (contains `passed in`)

The README structure from Plan 04 is preserved; only the placeholder block was replaced. Confirmed: `grep -c "TODO Plan 05" README.md` returns 0.

### SC#5 status

PASS.
