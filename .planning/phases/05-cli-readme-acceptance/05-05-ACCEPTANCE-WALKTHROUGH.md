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

**Status:** PARTIAL PASS — natural-exit teardown verified clean (no zombie subprocess); SIGINT path **not** directly UAT-tested in this session due to interrupt-window narrowness. Inference from shared code path + Phase 04.1 evidence carries the SIGINT case. Documented here as an explicit acceptance trade-off, not a teardown defect.

### What was directly observed (verbatim user capture, PowerShell)

The user attempted the manual Ctrl+C UAT against `uv run mcp-test-framework list-tools` and reported the following:

- `uv run mcp-test-framework list-tools` runs to completion in well under a second on the warm `uvx` cache. The full tool list (≈55 tools, ending at `validate_infrastructure_changes`) prints to stdout before Ctrl+C can be delivered.
- `Get-Process homelab-mcp` immediately after the natural exit returns **empty output** — no zombie subprocess.
- The user could not interrupt mid-execution; the cold-start window was too narrow to reliably hit even with `uvx --refresh` warming behavior.

That is: the natural-exit teardown path through `asyncio.Runner` + `AsyncExitStack` works as designed (the documented OPS-03 contract — "no leftover `homelab-mcp.exe` after the CLI returns" — holds for the only path the human verifier could observe end-to-end).

### Why we treat the SIGINT path as covered (inference, not direct UAT)

OPS-03's spec text and ROADMAP SC#4 wording are: "KeyboardInterrupt at the CLI level cleanly tears down the MCP subprocess (no zombie `homelab-mcp.exe` on Windows)." The verbatim Ctrl+C UAT was the chosen verification strategy in CONTEXT.md `<decisions>` D-teardown-2. This session could not deliver SIGINT inside the runtime window, so the direct UAT did not happen. We carry the SIGINT path on the strength of three pieces of evidence:

1. **Shared teardown code path.** `list-tools` (Plan 05-03) uses the same `asyncio.Runner` + `AsyncExitStack`-owned `McpTestClient` lifecycle pattern that Phase 04.1 hardened for the test-fixture path (D-teardown-1 reuses Phase 04.1's owner-task discipline verbatim). Both natural exit and `KeyboardInterrupt`-driven exit unwind through the same `__aexit__` path on the same task (the cancel-scope-different-task bug is the ONLY way teardown fails here, and Phase 04.1 eliminated it).
2. **Phase 04.1 fixture-side SIGINT evidence.** `tests/smoke/test_mcp_client_teardown_regression.py` (added 04.1-01) exercises the full `mcp_client` lifecycle including teardown; `04.1-01-SUMMARY.md` recorded "EXIT_CODE=0, 10 passed in 14.95s, no leftover homelab-mcp.exe". The CLI surface has been re-confirmed clean on natural exit in this session, so the only thing not directly observed today is whether `KeyboardInterrupt` (vs natural completion) reaches the same `__aexit__` — and Python's runtime guarantees that for `asyncio.Runner` (3.11+) + `AsyncExitStack` ownership.
3. **CONTEXT.md `<deferred>` already flagged automated cross-platform SIGINT testing as out of scope.** The deferred list explicitly says: "Automated regression test for OPS-03. Phase 5 verifies via manual UAT (subprocess teardown after Ctrl+C). An automated test would spawn the CLI, send SIGINT cross-platform, then assert no `homelab-mcp.exe` matches via `Get-Process` / `pgrep`. Defer until OPS-03 regresses or until CI lands and has stable cross-platform process-enumeration." The interrupt-window narrowness this session encountered is exactly the cross-platform-flakiness reason the auto-test was deferred. A reliable SIGINT UAT here would require either (a) introducing artificial latency in `list-tools` (rejected — would change the behavior under test), or (b) building the cross-platform process-enumeration scaffolding the deferred item describes.

### Verbatim capture

```powershell
uv run mcp-test-framework list-tools
# (...prints ~55 tools alphabetically; final tool: validate_infrastructure_changes)
# (Ctrl+C attempted but command had already exited cleanly)
Get-Process homelab-mcp -ErrorAction SilentlyContinue
# (empty output -- no rows)
```

No zombie `homelab-mcp.exe` after the natural exit. No custom "Interrupted before tools could be listed" message printed at any point (D-teardown-3 honored — this constraint is enforced by code shape regardless of which exit path runs, since Plan 05-03's body has no try/except wrapping the runner).

### OPS-03 outcome

**Verdict:** PARTIAL PASS (◐). Natural-exit teardown directly verified clean on Windows 11. SIGINT path covered by inference from (a) shared code path with the natural-exit case and (b) Phase 04.1's fixture-side teardown evidence. Re-running the SIGINT UAT remains valuable when a slower cold-start window (or a deliberately latent test build) is available, and the deferred item "Automated regression test for OPS-03" remains the durable path to closing this gap. No code change in this plan is required to act on this finding.

---

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

---

## Final acceptance summary

| SC# | Criterion | Status | Captured in section |
|-----|-----------|--------|---------------------|
| SC#1 | `run` resolves config, invokes `pytest.main()`, exits with pytest's exit code (CLI-01) | PASS | `## SC#1 / SC#6` (after target-tool switch to `list_keyring_credentials`) |
| SC#2 | `list-tools` connects via stdio + prints tools (text + `--json`) (CLI-02) | PASS | `## SC#2` |
| SC#3 | `version` prints the package version (CLI-03) | PASS | `## SC#3` |
| SC#4 | KeyboardInterrupt cleanly tears down MCP subprocess (OPS-03) | ◐ PARTIAL — natural-exit teardown verified clean (no zombie); SIGINT path inferred from shared code path + Phase 04.1 evidence (interrupt-window narrowness blocked direct UAT) | `## OPS-03 (SC#4)` |
| SC#5 | README documents setup, configuration, run, troubleshooting (DOCS-01) | PASS | `## SC#5` |
| SC#6 | Clean-clone walkthrough produces standard pytest output and exits 0 | PASS — with documented finding: original default `list_registered_servers` reproducibly failed `test_description_disambiguation` (`score=3 < 4`); switched documented default to `list_keyring_credentials` (chore commit `6d1974a`); upstream homelab-mcp description fix tracked | `## SC#1 / SC#6` + `## SC#6 Note` |

**Milestone v1.0 acceptance:** 5 of 6 Phase 5 success criteria captured PASS live; SC#4 (OPS-03) recorded PARTIAL with explicit evidence trail (natural-exit clean + Phase 04.1 inference) and a documented deferred path to direct SIGINT UAT once cross-platform process-enumeration scaffolding lands. The framework's value proposition was demonstrated end-to-end during SC#6 — the qwen3.6 judge surfaced a real description-quality gap in `homelab-mcp`'s `list_registered_servers` description with substantive reasoning, exactly the failure mode the framework exists to catch. Ready for `/gsd-verify-work`.

Captured: 2026-05-06 by washyu (manual UAT) + Claude Code execute-phase (artifact authoring)
