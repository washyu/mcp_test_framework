---
phase: 17-schema-driven-codegen-surface
plan: 04
subsystem: cli-codegen-entry
tags: [cli, typer, gen-sdet-classes, integration, codegen-01]
requirements: [CODEGEN-01]
status: complete
dependency_graph:
  requires:
    - "17-01 (ToolResponse base — emitted by codegen)"
    - "17-02 (translate_tool + generate file emitter)"
    - "17-03 (tool factory + _REGISTRIES seam — generated/<slug>/__init__.py emits _REGISTRY entries)"
  provides:
    - "mcp-test-framework gen-sdet-classes Typer subcommand (CODEGEN-01 operator entry point)"
    - "_run_codegen_handshake helper: one-shot McpTestClient + serverInfo capture"
    - "src/mcp_test_framework/sdet/generated/ directory (with .gitkeep)"
  affects:
    - "Phase 17 Plan 05 (pyright typecheck consumes this command's output)"
    - "Phase 18 mcp_session fixture (will import from generated/<slug>/ produced by this command)"
tech-stack:
  added: []
  patterns:
    - "Class-level monkey-patch of ClientSession.initialize for InitializeResult capture (LOCKED-file workaround)"
    - "asyncio.Runner + AsyncExitStack-owned McpTestClient (Phase 04.1 same-task lifecycle reused)"
    - "FileNotFoundError mirror of cli.list_tools (cli.py:672-690) for operator-tone errors"
    - "Phase 16 aesthetic one-line-per-section digest"
key-files:
  created:
    - "src/mcp_test_framework/sdet/generated/.gitkeep"
    - "tests/framework/unit/test_gen_sdet_classes_cli.py"
    - ".planning/phases/17-schema-driven-codegen-surface/deferred-items.md"
  modified:
    - "src/mcp_test_framework/cli.py (gen-sdet-classes command + _run_codegen_handshake helper)"
decisions:
  - "Class-level monkey-patch of ClientSession.initialize replaces plan's stated `session._initialize_result` access (mcp 1.27 does NOT cache the InitializeResult on the session); honors LOCKED mcp_client.py"
  - "Test E2E uses FastMCP-based stub server invoked via sys.executable to keep the test self-contained and reachable in CI"
  - "Live-homelab smoke test gated by @pytest.mark.live_homelab marker (matches Plan 08 / config-init convention)"
metrics:
  duration: "≈25 minutes (TDD RED → GREEN, 1 Rule 3 deviation for SDK-attribute correction)"
  completed: "2026-05-12"
  tasks: 2
  files_created: 3
  files_modified: 1
  tests_added: 6
---

# Phase 17 Plan 04: gen-sdet-classes CLI Subcommand Summary

Wires the `mcp-test-framework gen-sdet-classes` Typer subcommand as the operator
entry point for CODEGEN-01. Loads config via the Phase 13 precedence chain,
opens a one-shot `McpTestClient` to read `serverInfo` and `list_tools()`, hands
off to `_codegen.generate(...)` from Plan 17-02, then renders a Phase 16
aesthetic digest. Single integration plan of Wave 2 (depends on Plans 17-01,
17-02, 17-03).

## CLI Surface

```
mcp-test-framework gen-sdet-classes [--config PATH]
```

Exit codes:
- `0` — success (`generated/<slug>/` populated with per-tool files + `__init__.py`)
- `2` — config error (`--config` not found, SAFE-03 missing-config, ValidationError on config), MCP server command not on PATH, empty `serverInfo.name`, `SchemaValidityError` from the walker
- `130` — SIGINT during MCP handshake / list_tools

## Stdout Digest (Phase 16 Aesthetic)

```
gen-sdet-classes: wrote SDET classes for <server-name>

  server:    <server-name> v<version>
  slug:      <server_slug>
  target:    src/mcp_test_framework/sdet/generated/<server_slug>/
  tools:     <N> generated
  degraded:  <M> fields (grep "codegen: degraded" for details)
```

## Architecture: LOCKED-mcp_client.py Workaround (Rule 3 Deviation)

The plan's `<interfaces>` block called for accessing serverInfo via
`client._session._initialize_result.serverInfo` with a `# type: ignore` comment,
documented as PATTERNS.md option (a). **Reality check at execute time**: mcp
1.27.0's `ClientSession` does NOT cache `InitializeResult` on the session
(verified via `inspect.getsource(ClientSession.initialize)` — it only stores
`_server_capabilities = result.capabilities`, not the full result). The plan's
stated approach would raise `AttributeError` immediately.

**Chosen workaround** (in `_run_codegen_handshake`, Rule 3 — blocking issue):
class-level monkey-patch of `ClientSession.initialize` for the duration of
`McpTestClient.__aenter__`. The patched method delegates to the real one and
stores the `InitializeResult` in a local-dict holder; the unpatch happens in a
`finally` block so the patch is scoped to a single `async with` and reverted
unconditionally even on exception.

```python
holder: dict[str, object] = {}
original_initialize = ClientSession.initialize

async def _capturing_initialize(self):
    result = await original_initialize(self)
    holder["result"] = result
    return result

ClientSession.initialize = _capturing_initialize
try:
    async with AsyncExitStack() as stack:
        client = await stack.enter_async_context(McpTestClient(...))
        init_result = holder["result"]
        server_info = init_result.serverInfo
        tools = await client.list_tools()
finally:
    ClientSession.initialize = original_initialize
```

Why not option (b) "additive accessor on `McpTestClient`"? `mcp_client.py` is
LOCKED per CONTEXT.md line 121 ("Hard dependencies"). Phase 18 may need a
richer accessor; deferring its design avoids two competing accessor patterns.

Why not re-invoking `session.initialize()` after the framework already
initialized? Re-sending the MCP `initialize` request after one has succeeded is
not protocol-spec compliant; behavior is server-implementation-dependent.

The defensive `RuntimeError` ("InitializeResult was not captured") fires if a
future mcp release stops invoking `initialize()` during the session ctor — at
which point Plan 17-05's typecheck pass should surface the contract change.

## Stub-Server E2E Test (Reference Fixture)

`tests/framework/unit/test_gen_sdet_classes_cli.py::test_e2e_emits_generated_dir_for_stub_server`
ships a FastMCP-based stub server inline as a multi-line string, writes it to
`tmp_path/stub_server.py`, points the config's `mcp_server.command` at
`sys.executable` with `args=[stub_path]`, then invokes `gen-sdet-classes`
through the Typer CliRunner. The test asserts:
- `generated/stub_server_for_codegen_test/` directory exists
- `create_thing.py`, `delete_thing.py`, `__init__.py` all present
- Generated file contains the CODEGEN-06 `AUTOGENERATED ... DO NOT HAND-EDIT` header
- `CreateThingParams(BaseModel)` and `CreateThingResponse(ToolResponse)` classes are emitted
- `__init__.py` contains the `_REGISTRY` mapping with `(CreateThingParams, CreateThingResponse)` tuple
- Stdout digest emits `gen-sdet-classes: wrote SDET classes for` and `tools:     2 generated`

Reference stub source (embedded in test file as `_STUB_SERVER_SOURCE`):

```python
from mcp.server.fastmcp import FastMCP
app = FastMCP("stub-server-for-codegen-test")

@app.tool()
def create_thing(name: str, quantity: int = 1) -> dict:
    """Create a thing."""
    return {"id": f"thing-{name}", "qty": quantity}

@app.tool()
def delete_thing(thing_id: str) -> dict:
    """Delete a thing."""
    return {"deleted": thing_id}

if __name__ == "__main__":
    app.run()
```

The test cleans up `generated/stub_server_for_codegen_test/` in a `try/finally`
so the repo's `git status` stays clean after the run.

## Test Coverage

| Test | Purpose |
|------|---------|
| `test_help_lists_flags` | --help advertises `gen-sdet-classes` and `--config`; no `--output-dir` / `--force` (D-08) |
| `test_no_config_safe03_fails_loud` | SAFE-03: no config sources discoverable → exit 2 |
| `test_config_path_not_found_fails_loud` | `--config /path/missing.yaml` → exit 2 |
| `test_mcp_command_not_on_path_operator_error` | FileNotFoundError → operator-tone error + exit 2 |
| `test_e2e_emits_generated_dir_for_stub_server` | Full pipeline against FastMCP stub server |
| `test_live_homelab_emit_smoke` (gated) | Live UAT against actual homelab-mcp |

All 5 non-live tests pass on the worktree base after merging Plans 17-01, 17-02, 17-03.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan's `_initialize_result` SDK attribute does not exist on mcp 1.27**

- **Found during:** Task 1 implementation (pre-flight SDK inspection)
- **Issue:** Plan's `<interfaces>` block and PATTERNS.md option (a) both assume `client._session._initialize_result.serverInfo` is accessible. Verified via `inspect.getsource` that mcp 1.27.0's `ClientSession.initialize` does NOT cache the result — only `_server_capabilities` is stored.
- **Fix:** Replaced with class-level monkey-patch of `ClientSession.initialize` that captures the `InitializeResult` in a local holder for the duration of `McpTestClient.__aenter__`, with unconditional revert in `finally`. Defensive `RuntimeError` fires if the SDK contract changes (e.g., mcp 2.x stops calling `initialize()` during session ctor).
- **Files modified:** `src/mcp_test_framework/cli.py` (`_run_codegen_handshake` helper)
- **Commit:** `ad49cf9` (feat 17-04 implementation)

## Deferred Issues

6 pre-existing test failures on the worktree base (verified by stashing my
changes and re-running them on the unmodified base commit):

- `tests/framework/unit/test_cli_errors.py::test_cli_errors_static_call_sites_no_banned_tokens`
- `tests/framework/unit/test_doc_scrub.py::test_doc_invocations_consistently_pair_with_config[path0]`
- `tests/framework/unit/test_migration_doc.py::test_migration_doc_exists`
- `tests/framework/unit/test_migration_doc.py::test_migration_doc_pins_v2_keywords`
- `tests/framework/unit/test_migration_doc.py::test_migration_doc_uses_ascii_dashes_not_emdash`
- `tests/framework/unit/test_migration_doc.py::test_migration_doc_does_not_leak_planning_ids`

Root cause: `repo_root` path-resolution bug when tests run from a git worktree
subdirectory (computes `tests/src/mcp_test_framework/cli.py` and
`tests/docs/MIGRATION-v1-to-v2.md` which don't exist). Triaged separately in
`.planning/phases/17-schema-driven-codegen-surface/deferred-items.md`. Out of
scope per Rule 3 SCOPE BOUNDARY (not caused by Plan 17-04 changes).

## Commits

- `22c7787` — `test(17-04): add failing tests for gen-sdet-classes CLI command` (RED)
- `ad49cf9` — `feat(17-04): wire gen-sdet-classes Typer subcommand (CODEGEN-01)` (GREEN)

## Self-Check: PASSED

- File `src/mcp_test_framework/sdet/generated/.gitkeep`: FOUND
- File `tests/framework/unit/test_gen_sdet_classes_cli.py`: FOUND
- File `src/mcp_test_framework/cli.py` contains `@app.command("gen-sdet-classes")`: FOUND
- Commit `22c7787` (RED): FOUND
- Commit `ad49cf9` (GREEN): FOUND
- All 5 non-live tests pass: VERIFIED
- `mcp-test-framework gen-sdet-classes --help` exits 0 with `gen-sdet-classes` + `--config` in stdout: VERIFIED
- `mcp-test-framework --help` lists `gen-sdet-classes` among subcommands: VERIFIED
- `git ls-files src/mcp_test_framework/sdet/generated/` shows only `.gitkeep`: VERIFIED
- `mcp_client.py` unmodified (LOCKED constraint honored): VERIFIED
