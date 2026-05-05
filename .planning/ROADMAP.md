# Roadmap: mcp_test_framework

## Overview

The MVP delivers a `pytest`-runnable test suite that exercises one MCP tool end-to-end (schema -> call -> judge) against `homelab-mcp`'s `list_registered_servers`. Build order is risk-first: pure data foundation locks down the bootstrap choices (uv, pytest-asyncio config, black-box lint rule, config precedence) before any I/O lands; then the two integration risks (MCP stdio subprocess, Ollama HTTP judge) each get a dedicated phase with a smoke step before any fixture depends on them; then fixtures wire everything into the 10 spec'd tests; finally the CLI + README close out the acceptance criteria. Granularity is coarse (5 phases) — the two integration risks justify staying split rather than merging into a single "core modules" phase.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Pure-Data Core** - Bootstrap project, lock pytest-asyncio config, ban black-box imports, build config loader and schema validator
 (completed 2026-05-04)
- [ ] **Phase 2: MCP Client Wrapper** - Async `McpTestClient` over stdio with subprocess lifecycle hardening; smoke-tested against live `homelab-mcp`
- [ ] **Phase 3: Ollama Judge** - `Judge` Protocol + `OllamaJudge` with qwen3 belt-and-braces (think:false, /no_think, <think> strip, cold-start timeouts); smoke-tested against live Ollama
- [ ] **Phase 4: Fixtures & Test Cases** - Session-scoped pytest-asyncio fixtures (AsyncExitStack-owned MCP client) plus all 10 spec'd tests against `homelab-mcp` / `list_registered_servers`
- [ ] **Phase 5: CLI, README & Acceptance** - Typer CLI (`run`, `list-tools`, `version`), KeyboardInterrupt cleanup, README, and clean-checkout acceptance verification

## Phase Details

### Phase 1: Foundation & Pure-Data Core
**Goal**: Project skeleton is correct, the black-box rule is mechanically enforced, and the I/O-free core (config + schema validator) is built and unit-tested before any subprocess or HTTP code lands.
**Depends on**: Nothing (first phase)
**Requirements**: SETUP-01, SETUP-02, SETUP-03, CORE-01, CORE-02, DOCS-02
**Success Criteria** (what must be TRUE):
  1. `uv sync` on a fresh checkout produces a clean install with `uv.lock` committed and Python 3.14 honored
  2. `pyproject.toml` configures `pytest-asyncio` with `asyncio_mode = "strict"` and `asyncio_default_fixture_loop_scope = "session"`
  3. The lint configuration causes `ruff check` to fail any `import homelab_mcp` (or `from homelab_mcp ...`) under `src/` or `tests/`
  4. `Config.load()` (or equivalent) resolves a setting with precedence `CLI flag > env var > YAML > default` and exposes a frozen Pydantic `Config` model — verified by a dedicated unit test
  5. `validate_tool_schema(tool)` returns the spec's 7 structural-issue checks against a synthetic tool with `severity`, `path`, and `message` populated; auto-detects the JSON Schema draft via `validator_for`
  6. `.env.example` and `config.example.yaml` enumerate every configurable setting with example values
**Plans**: 4 plans
  - [x] 01-01-PLAN.md — Project skeleton: pyproject.toml (deps, pytest-asyncio strict, ruff TID251), uv.lock, src/tests packages, .gitignore, delete main.py
  - [x] 01-02-PLAN.md — Config layer: models.py sub-models + frozen Config(BaseSettings) with CLI>env>.env>YAML>default precedence, tests, .env.example, config.example.yaml
  - [x] 01-03-PLAN.md — schema_validator.py: ValidationIssue + validate_tool_schema (7 structural checks, JSON-Pointer paths) and 12 unit tests
  - [x] 01-04-PLAN.md — Black-box belt-and-suspenders: tests/conftest.py sys.modules guard + ruff TID251 smoke test (fixture proves the rule fires)

### Phase 2: MCP Client Wrapper
**Goal**: Driving `homelab-mcp` over stdio works end-to-end via `McpTestClient`, with explicit timeouts and `CallToolResult` shape handling proven in a smoke script before any fixture depends on it.
**Depends on**: Phase 1
**Requirements**: CORE-03
**Success Criteria** (what must be TRUE):
  1. A throwaway smoke script connects to live `homelab-mcp` via `stdio_client`, calls `list_tools()`, and prints `list_registered_servers` along with its declared schema — without ever importing `homelab_mcp`
  2. `McpTestClient.call_tool("list_registered_servers", {})` returns a `CallToolResult` whose `isError` is false and whose `content` or `structuredContent` is non-empty
  3. Every SDK call (`initialize`, `list_tools`, `get_tool`, `call_tool`) is wrapped in `asyncio.timeout()` with explicit ceilings, and a manually-killed subprocess fails the call with a timeout error rather than hanging
  4. Server stderr is captured and surfaced via the SDK's `errlog` parameter to the framework logger
**Plans**: 3 plans
  - [x] 02-01-PLAN.md — Config layer extension: McpServerConfig.timeout_seconds (D-05) + .env.example + config.example.yaml + precedence test (D-07)
  - [x] 02-02-PLAN.md — McpTestClient (mcp_client.py) + ToolNotFoundError + _LoggerWriter + sync unit tests + pyproject live_homelab marker registration (D-03)
  - [ ] 02-03-PLAN.md — Permanent live-marker smoke pytest (tests/smoke/) covering both Phase 2 success criteria #1 and #2 (D-01, D-04)

### Phase 3: Ollama Judge
**Goal**: `OllamaJudge` reliably returns a validated `JudgeResult` from the live Ollama at `127.0.0.1:11434` even on cold start, even with qwen3 thinking quirks, and the `Judge` Protocol seam is in place for post-MVP backend swaps.
**Depends on**: Phase 2
**Requirements**: CORE-04, OPS-01, OPS-02, DOCS-03
**Success Criteria** (what must be TRUE):
  1. `judge_protocol.Judge` is defined as a `Protocol` with one async `judge(rubric, subject, context)` method that `OllamaJudge` implements; fixtures and tests will type-annotate against `Judge`, not the concrete class
  2. A throwaway smoke script against live Ollama returns a valid `JudgeResult` (`passed: bool`, `score: 1-5`, `reasoning: str`, `raw_response: str`) with `stream:false`, `format:json`, `think:false`, `temperature:0`, `num_predict:256`, `keep_alive:"30m"` — including after `ollama stop qwen3.6:latest` (cold-start path)
  3. The response parser strips `<think>...</think>` blocks defensively, falls back to a `passed=False` JudgeResult on parse failure with the raw response preserved, and validates `1 <= score <= 5` plus all 3 required fields
  4. Every Ollama HTTP call uses `httpx.Timeout(120, connect=10)` and every MCP subprocess call uses `asyncio.timeout()` — no operation can hang indefinitely (a manual `ollama stop` mid-run produces a clean timeout failure, not a hang)
  5. When the judge fails (timeout or malformed JSON), the affected test fails with the model's `raw_response` visible in the diagnostic and the run continues for other tests — does not crash the suite
**Plans**: TBD

### Phase 4: Fixtures & Test Cases
**Goal**: All four session-scoped pytest-asyncio fixtures are wired together with `AsyncExitStack`-owned subprocess lifecycle, and the spec's 10 test cases run against `homelab-mcp` / `list_registered_servers` with green output.
**Depends on**: Phase 3
**Requirements**: FIX-01, FIX-02, FIX-03, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07, TEST-08, TEST-09, TEST-10
**Success Criteria** (what must be TRUE):
  1. `pytest tests/` (no CLI yet) discovers and runs all 10 test functions in `test_homelab_list_registered_servers.py`; all four session-scoped fixtures (`config`, `mcp_client`, `judge`, `target_tool`) initialize once for the run and teardown cleanly with no `Attempted to exit cancel scope...` errors and no leftover `homelab-mcp.exe` process on Windows
  2. The `_preflight` fixture fails the run with a precise diagnostic if Ollama is unreachable, the configured model is missing from `/api/tags`, or the MCP server command is not on PATH — *before* any test starts
  3. The `target_tool` fixture fails the run early (not per-test) when `TARGET_TOOL_NAME` is absent from the server's tool list
  4. All 4 schema tests (Category 1) and all 3 output-conformance tests (Category 3) pass deterministically; all 3 description-quality tests (Category 2) pass with `score >= 4` against `list_registered_servers`'s description
  5. A green `pytest tests/` run completes against `homelab-mcp` with the expected pass count and zero ERRORs
**Plans**: TBD

### Phase 5: CLI, README & Acceptance
**Goal**: Users can install, configure, and run the framework against `homelab-mcp` via the `mcp-test-framework` CLI from a clean checkout, with all 6 spec acceptance criteria observable.
**Depends on**: Phase 4
**Requirements**: CLI-01, CLI-02, CLI-03, OPS-03, DOCS-01
**Success Criteria** (what must be TRUE):
  1. `mcp-test-framework run [-k EXPRESSION] [-v] [--config PATH]` resolves config, invokes `pytest.main()` against the test directory, and exits with pytest's exit code (0 on green, non-zero on any failure)
  2. `mcp-test-framework list-tools [--config PATH]` connects to the configured MCP server via stdio and prints all available tools with their descriptions — without invoking pytest or Ollama (no judge or test-runner dependency)
  3. `mcp-test-framework version` prints the package version
  4. KeyboardInterrupt at the CLI level cleanly tears down the MCP subprocess — `Get-Process homelab-mcp` after a Ctrl+C'd run returns no matches
  5. README in repo root explains setup (`uv sync`), configuration (env vars + YAML, with the explicit `CLI flag > env > YAML > default` precedence rule), how to run tests, and Windows-specific troubleshooting (`taskkill /F /IM homelab-mcp.exe`)
  6. From a clean `git clone`, `uv sync` then `uv run mcp-test-framework run` produces standard pytest terminal output and exits 0 against a healthy homelab-mcp + Ollama
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Pure-Data Core | 4/4 | Complete   | 2026-05-04 |
| 2. MCP Client Wrapper | 0/3 | Not started | - |
| 3. Ollama Judge | 0/TBD | Not started | - |
| 4. Fixtures & Test Cases | 0/TBD | Not started | - |
| 5. CLI, README & Acceptance | 0/TBD | Not started | - |
