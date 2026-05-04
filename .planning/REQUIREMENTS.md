# Requirements: mcp_test_framework

**Defined:** 2026-05-04
**Core Value:** A `pytest`-runnable test suite that exercises one MCP tool end-to-end (schema → call → judge) and exits non-zero on any failure — proving the framework's integration contract before adding breadth.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Project Setup

- [x] **SETUP-01**: Project uses `uv` for dependency management with a committed `uv.lock`; `uv sync` produces a clean install on a fresh checkout (Python 3.14)
- [x] **SETUP-02**: `pyproject.toml` configures `pytest-asyncio` with `asyncio_mode = "strict"` and `asyncio_default_fixture_loop_scope = "session"` to match the framework's session-scoped fixture pattern
- [x] **SETUP-03**: A lint rule (e.g. ruff `flake8-tidy-imports` ban or equivalent) prevents any code under `src/` and `tests/` from importing `homelab_mcp`, mechanically enforcing the black-box principle

### Core Modules

- [x] **CORE-01**: `config.py` + `models.py` load configuration with precedence `CLI flags > env vars > YAML > defaults` using `pydantic-settings[yaml]`; produces a frozen `Config` Pydantic model consumed by all fixtures
- [ ] **CORE-02**: `schema_validator.py` performs the 7 deterministic structural checks from the spec (non-empty name, non-empty description, valid `inputSchema`, `type=object`, `required` ⊆ `properties`, every property documented, every property typed) using `jsonschema >= 4.18` with auto-detected draft via `validator_for`; returns a list of `ValidationIssue` records (`severity`, `path`, `message`)
- [ ] **CORE-03**: `mcp_client.py` exposes an async `McpTestClient` wrapping the official `mcp` SDK's `stdio_client` + `ClientSession` with `list_tools`, `get_tool`, and `call_tool`; every SDK call is wrapped in `asyncio.timeout()`; defensive handling of `CallToolResult.isError` and the `content` vs `structuredContent` shape variance
- [ ] **CORE-04**: `ollama_judge.py` implements a `Judge` Protocol (defined in `judge_protocol.py`) by POSTing to Ollama `/api/chat` with `stream:false`, `format:json`, `temperature:0`, `think:false`, `num_predict:256`, `keep_alive:"30m"`; system prompt includes `/no_think` directive and a delimited subject block; response parser strips `<think>...</think>` blocks defensively before JSON parsing and validates the `JudgeResult` shape (`passed`, `score 1-5`, `reasoning`, `raw_response`)

### Test Cases — Schema Validation (Category 1, deterministic)

- [ ] **TEST-01**: `test_target_tool_exists` — the configured `TARGET_TOOL_NAME` is present in the server's tool list
- [ ] **TEST-02**: `test_tool_schema_is_structurally_valid` — `validate_tool_schema` returns no errors for the target tool
- [ ] **TEST-03**: `test_tool_has_description` — the target tool's description is non-empty and at least 20 characters
- [ ] **TEST-04**: `test_input_schema_properties_are_documented` — every input parameter has both a description and a type

### Test Cases — Description Quality (Category 2, LLM-judged, score >= 4)

- [ ] **TEST-05**: `test_description_clarity` — the judge scores whether the description clearly explains what the tool does
- [ ] **TEST-06**: `test_description_disambiguation` — the judge scores whether the description gives an LLM agent enough information to know when to call this tool versus a similarly-named alternative
- [ ] **TEST-07**: `test_parameters_are_self_explanatory` — the judge scores whether each parameter description is clear enough to call the tool without external documentation

### Test Cases — Output Conformance (Category 3, deterministic)

- [ ] **TEST-08**: `test_call_with_no_arguments_succeeds` — the target tool can be called with `{}` and returns a non-error result
- [ ] **TEST-09**: `test_response_has_expected_shape` — response is a valid `CallToolResult` with at least one content block (non-empty `content` OR non-null `structuredContent`)
- [ ] **TEST-10**: `test_response_content_is_parseable` — text content claiming to be JSON parses; structured content matches any declared output schema

### Pytest Fixtures

- [ ] **FIX-01**: Session-scoped `pytest-asyncio` fixtures (`config`, `mcp_client`, `judge`, `target_tool`) using `loop_scope="session"`; `mcp_client` owns the `stdio_client` + `ClientSession` lifecycle through `contextlib.AsyncExitStack`
- [ ] **FIX-02**: A `_preflight` fixture verifies Ollama is reachable, the configured model is in `/api/tags`, and the MCP server command resolves on PATH — failing fast with a clear diagnostic if any pre-condition is unmet
- [ ] **FIX-03**: The `target_tool` fixture fails the run early (not per-test) if the configured tool name is absent from the server's tool list

### CLI

- [ ] **CLI-01**: `mcp-test-framework run [-k EXPRESSION] [-v] [--config PATH]` resolves config, invokes `pytest.main()` against the test directory, and exits with pytest's exit code (the CI/CD entry point)
- [ ] **CLI-02**: `mcp-test-framework list-tools [--config PATH]` connects to the configured MCP server via stdio and prints all available tools with their descriptions — without invoking pytest or Ollama
- [ ] **CLI-03**: `mcp-test-framework version` prints the package version

### Operational

- [ ] **OPS-01**: Ollama timeouts and malformed JSON responses cause the affected test to fail with the raw response surfaced in the diagnostic; the run continues for other tests (does not crash the suite)
- [ ] **OPS-02**: Subprocess (MCP server) and HTTP (Ollama) operations have explicit `asyncio.timeout()` / `httpx.Timeout(120, connect=10)` boundaries — no operation can hang indefinitely
- [ ] **OPS-03**: KeyboardInterrupt at the CLI level cleanly tears down the MCP subprocess (no zombie `homelab-mcp.exe` on Windows)

### Documentation

- [ ] **DOCS-01**: README in repo root explains setup (`uv sync`), configuration (env vars + YAML, with precedence rule), how to run tests, and Windows-specific troubleshooting
- [x] **DOCS-02**: `.env.example` and `config.example.yaml` stub files enumerate every configurable setting with example values
- [ ] **DOCS-03**: Judge failures surface the model's `raw_response` in the test failure output so debugging the rubric or response format does not require re-running the suite

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### LLM-Generated Tests (the "Plant Seed")

- **GEN-01**: Judge model reads a tool's `inputSchema`, parameter descriptions, and declared output schema and generates diverse synthetic invocations (the natural next milestone)
- **GEN-02**: Generated invocations are stored as parameterized test cases that can be re-run deterministically

### Generalization

- **MULTI-01**: Multi-tool target selection (parameterize existing fixtures over a tool list)
- **MULTI-02**: Multi-server runs in a single invocation
- **TRANSPORT-01**: HTTP and SSE MCP transports
- **JUDGE-01**: Pluggable judge backends (OpenAI-compatible endpoints) using the v1 `Judge` Protocol — a 1-file addition

### Quality / Output

- **OUT-01**: JSON / JUnit XML output formats for CI dashboards (one pytest flag away)
- **JUDGE-02**: Best-of-N judge consensus with majority vote / median (only if single-shot proves materially flaky)
- **CONFORM-01**: Generic conformance test pack parametrizable for any MCP server (the "pytest-mcp" value prop)
- **PROP-01**: Property-based / snapshot testing from `inputSchema`

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multiple MCP servers in one run | Generalization deferred until single-server contract is proven |
| Multiple tool targets in one run | Same — framework seams should make this easy to add later |
| HTTP / SSE transports | stdio is sufficient to validate the integration contract |
| LLM-generated test inputs | Explicit Phase 2 ("Plant Seed"); judge-only for MVP |
| Best-of-N judge consensus | Single-shot with `score >= 4` for MVP; revisit only if flakiness materially affects signal |
| Stateful / destructive tool testing | Read-only tools only — out of MVP scope |
| Performance / load / security testing | Not the integration contract being validated |
| JSON / JUnit / Allure output formats | pytest default terminal output is enough for local CLI |
| Web UI / dashboard | CLI-only |
| Pluggable judge backends (OpenAI etc.) | Ollama-only for MVP; `Judge` Protocol seam ships in MVP to make post-MVP swap trivial |
| Reading / importing `homelab-mcp` source | It is a black-box subprocess under test — never imported by the framework |
| Calibration dataset for judge | No human-labeled gold set in MVP; future-work item |

## Traceability

Phase mappings populated by the roadmapper.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 1 | Complete |
| SETUP-02 | Phase 1 | Complete |
| SETUP-03 | Phase 1 | Complete |
| CORE-01 | Phase 1 | Complete |
| CORE-02 | Phase 1 | Pending |
| CORE-03 | Phase 2 | Pending |
| CORE-04 | Phase 3 | Pending |
| TEST-01 | Phase 4 | Pending |
| TEST-02 | Phase 4 | Pending |
| TEST-03 | Phase 4 | Pending |
| TEST-04 | Phase 4 | Pending |
| TEST-05 | Phase 4 | Pending |
| TEST-06 | Phase 4 | Pending |
| TEST-07 | Phase 4 | Pending |
| TEST-08 | Phase 4 | Pending |
| TEST-09 | Phase 4 | Pending |
| TEST-10 | Phase 4 | Pending |
| FIX-01 | Phase 4 | Pending |
| FIX-02 | Phase 4 | Pending |
| FIX-03 | Phase 4 | Pending |
| CLI-01 | Phase 5 | Pending |
| CLI-02 | Phase 5 | Pending |
| CLI-03 | Phase 5 | Pending |
| OPS-01 | Phase 3 | Pending |
| OPS-02 | Phase 3 | Pending |
| OPS-03 | Phase 5 | Pending |
| DOCS-01 | Phase 5 | Pending |
| DOCS-02 | Phase 1 | Complete |
| DOCS-03 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 29 total
- Mapped to phases: 29 ✓
- Unmapped: 0

**Phase distribution:**
- Phase 1 (Foundation & Pure-Data Core): 6 requirements (SETUP-01, SETUP-02, SETUP-03, CORE-01, CORE-02, DOCS-02)
- Phase 2 (MCP Client Wrapper): 1 requirement (CORE-03)
- Phase 3 (Ollama Judge): 4 requirements (CORE-04, OPS-01, OPS-02, DOCS-03)
- Phase 4 (Fixtures & Test Cases): 13 requirements (FIX-01, FIX-02, FIX-03, TEST-01..TEST-10)
- Phase 5 (CLI, README & Acceptance): 5 requirements (CLI-01, CLI-02, CLI-03, OPS-03, DOCS-01)

---
*Requirements defined: 2026-05-04*
*Last updated: 2026-05-04 after roadmap creation (29/29 mapped)*
