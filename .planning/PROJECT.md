# mcp_test_framework

## What This Is

A pytest-based Python framework for testing MCP (Model Context Protocol) servers. It connects to one MCP server over stdio, runs deterministic schema/output checks against a target tool, and uses a local Ollama-hosted LLM as a judge for description quality. The MVP targets `homelab-mcp` and its `list_registered_servers` tool to validate the integration contract end-to-end before generalizing.

## Core Value

A `pytest`-runnable test suite that exercises one MCP tool end-to-end (schema → call → judge) and exits non-zero on any failure — proving the framework's integration contract before adding breadth.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Connect to an MCP server over stdio via the official `mcp` Python SDK
- [ ] List tools and select a configured target tool by name
- [ ] Validate the target tool's declared schema (name, description, inputSchema, properties)
- [ ] Judge the tool's description quality with Ollama (clarity, disambiguation, parameter docs) at `score >= 4`
- [ ] Call the tool with `{}` and verify the response is a well-formed `CallToolResult`
- [ ] Verify response content parses (JSON-as-text or structured content matching declared output schema)
- [ ] Load configuration from environment variables, optionally overlaid by a YAML config file
- [ ] CLI entry point (`mcp-test-framework run`) that wraps pytest and exits with pytest's exit code
- [ ] CLI `list-tools` subcommand that prints the configured server's tool surface
- [ ] Graceful handling of Ollama timeouts and malformed JSON responses (test fails, run continues)
- [ ] README explaining setup, configuration, and how to run tests

### Out of Scope

- Multiple MCP servers in one run — generalization deferred until single-server contract is proven
- Multiple tool targets in one run — same reason; framework seams should make this easy to add later
- HTTP and SSE MCP transports — stdio is sufficient to validate the contract
- LLM as test input generator — explicit Phase 2 ("Plant Seed" below); judge-only for MVP
- Best-of-N judge consensus / retry-on-flake — single shot for MVP, threshold `score >= 4`; revisit if flaky
- Stateful or destructive tool testing — read-only tools only
- Performance, load, or security testing — not the integration contract being validated
- JSON / JUnit output formats — pytest default terminal output is enough for MVP
- Web UI or dashboard — out of scope; CLI-only
- Pluggable judge backends (OpenAI-compatible, etc.) — Ollama-only for MVP
- Reading or importing `homelab-mcp` source — it is a black-box subprocess under test

## Context

- **Reusable framework, single first customer.** Long-term goal is a generalized MCP test framework. `homelab-mcp` is the first real target and proves the contract works.
- **Solo project, local CLI for now.** Single user (you), `uv run` on your own machine. No GitHub Actions or self-hosted runner yet — green CI = green local invocation.
- **Authoritative spec exists.** `docs/mcp_test_framework_mvp_spec.md` already describes module layout, public interfaces, dependency list, and acceptance criteria. Treat it as the source of truth for technical decisions.
- **Greenfield code, scaffolded only.** `pyproject.toml`, `main.py` stub, `.python-version` (3.14) exist. No `src/`, no tests, no implementation yet.
- **Black-box principle.** The framework never imports or reads `homelab-mcp` source — it is a subprocess under test. Only the SDK's `stdio_client` context manager launches it.
- **Ollama is already running** at `127.0.0.1:11434` with `qwen3.6:latest` pulled. No need to provision it.
- **Python 3.14** pinned via `.python-version` and `pyproject.toml` (`requires-python >= 3.14`).

## Constraints

- **Tech stack**: Python 3.14, `uv` for dependency management — pinned in `.python-version` and `pyproject.toml`.
- **MCP transport**: stdio only via the official `mcp` SDK's `stdio_client` context manager — no raw `subprocess.Popen`.
- **Judge backend**: Ollama at `127.0.0.1:11434` with model `qwen3.6:latest`, called via `/api/chat` with `stream: false` and `format: json` for structured JSON output.
- **Async**: pytest-asyncio in strict mode with explicit `@pytest.mark.asyncio` markers. `asyncio.timeout` (3.11+) wraps any subprocess or HTTP operation that could hang.
- **Black box**: never import, read, or vendor `homelab-mcp` source — it is a subprocess under test.
- **Pass threshold**: judge tests pass at `score >= 4` (1–5 rubric).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single MCP server, single tool for MVP | Validate the integration contract end-to-end before generalizing — narrow scope reduces unknowns | — Pending |
| Ollama (qwen3.6:latest) as judge backend | Already running on homelab at 127.0.0.1:11434; local, free, no API key management | — Pending |
| Single-shot judge calls (no best-of-N) | Simpler MVP; revisit only if flakiness materially affects the test signal | — Pending |
| stdio-only MCP transport for MVP | Sufficient to validate the contract; HTTP/SSE add complexity without de-risking the core integration | — Pending |
| Treat `homelab-mcp` as a black-box subprocess | Framework reusability requires no coupling to a specific server's internals | — Pending |
| `uv` for dep management, Python 3.14 | Already scaffolded that way; `uv sync` is the documented install path | — Pending |
| pytest-default output for MVP, no JSON/JUnit | Local CLI only — no CI dashboard yet to consume structured output | — Pending |

## Plant Seed: LLM-Generated Test Cases (Post-MVP)

After MVP green, the natural next milestone is **LLM-driven test input generation**: have the judge model read a tool's `inputSchema`, parameter descriptions, and declared output schema, and generate diverse synthetic invocations to broaden coverage beyond the hand-written `{}` call. This is explicitly out of scope for MVP (judge-only) but is the primary post-MVP direction. The MVP framework seams (stateless `OllamaJudge`, schema-aware `McpTestClient`, fixture-based test discovery) should accommodate this without rewrites.

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-04 after initialization*
