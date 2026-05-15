# Project Research Summary

**Project:** mcp_test_framework
**Domain:** Python pytest-based integration test framework for MCP servers, with Ollama LLM-as-judge for description quality
**Researched:** 2026-05-04
**Confidence:** HIGH on stack and architecture; MEDIUM on judge reliability and one config-precedence design choice

## Executive Summary

`mcp_test_framework` is a reusable Python library that drives an MCP server as a black-box subprocess (over stdio), runs deterministic schema and output-conformance checks against a target tool, and uses a local Ollama (`qwen3.6:latest`) instance as an LLM-as-judge for description quality. The MVP narrows to one server (`homelab-mcp`) and one tool (`list_registered_servers`) so the integration contract — pytest fixtures + MCP SDK + Ollama HTTP — can be validated end-to-end before generalization. Research confirms there is a real market gap: no existing Python-native, pytest-native, server-agnostic, judge-augmented MCP test framework exists today (the closest, MCP-Eval, is task/agent-oriented; mcp-server-tester and mcp-testing-framework are Node).

The recommended approach is the spec's stack with two surgical refinements: (1) replace `python-dotenv` + `pyyaml` + a hand-rolled config loader with **`pydantic-settings[yaml]`** (already a transitive dep of `mcp`), and (2) adopt **`typer`** for the CLI rather than raw `argparse` (also already transitive via `mcp[cli]`). Architecturally, the framework is a five-module core (`models`, `config`, `mcp_client`, `ollama_judge`, `schema_validator`) wired together by session-scoped `pytest-asyncio` fixtures, with a thin `cli.py` that wraps `pytest.main()`. The two integration risks (MCP stdio lifecycle and Ollama qwen3 structured-output reliability) drive a build order that proves both before any test cases are written.

The dominant risks are concentrated in five areas: (1) anyio cancel-scope errors on `stdio_client` teardown — mitigated by an `AsyncExitStack`-owned subprocess fixture with `loop_scope="session"`; (2) qwen3 thinking-token leakage corrupting `format: json` output — mitigated by belt-and-braces `think:false` + `/no_think` in the system prompt + post-parse `<think>` regex strip + `temperature: 0`; (3) pytest-asyncio 1.0 scope-mismatch enforcement — mitigated by pinning `>= 1.0` and setting `asyncio_default_fixture_loop_scope = "session"`; (4) Ollama cold-start exceeding default httpx 5s timeout — mitigated by explicit `httpx.Timeout(120, connect=10)` plus a warmup call and `keep_alive: "30m"`; (5) `CallToolResult` shape variance (`isError`, `content` vs `structuredContent`) — mitigated by checking `isError` first and accepting either content channel. Additionally, the **black-box rule should be mechanically enforced** by moving `homelab-mcp` to dev/optional dependencies so the framework package itself never imports it.

## Key Findings

### Recommended Stack

The spec's eight-package list is substantially correct for May 2026 — every choice is current, maintained, and Python 3.14-compatible. Two refinements simplify the codebase without breaking the spec: `pydantic-settings[yaml]` replaces `python-dotenv` + hand-rolled YAML overlay, and `typer` replaces unspecified CLI plumbing. Both are already transitive deps of `mcp`, so they're effectively free. Everything else (strict-mode `pytest-asyncio`, raw `httpx` to call Ollama, `jsonschema` Draft 2020-12, single-shot judge with `format: json`) stays as-is.

**Core technologies:**
- **Python 3.14.4** (pinned): native `asyncio.timeout`, PEP 695 generics, EOL 2030-10-31
- **uv 0.11.x**: project + venv + lockfile manager (already chosen)
- **mcp 1.27.0** (Python SDK): the only authoritative MCP client; `stdio_client` + `ClientSession` mandatory per spec
- **pytest 9.0.3 + pytest-asyncio 1.3.0**: strict mode default in 1.x; supports session-scoped event loops needed for long-lived `mcp_client` fixture
- **httpx 0.28.1**: async-first, `httpx.Timeout`-friendly; preferred over `aiohttp` for new 2026 code
- **pydantic 2.13 + pydantic-settings 2.14 [yaml]**: layered config (env → .env → YAML → CLI override) without a hand-rolled loader
- **jsonschema 4.26**: Draft 2020-12 (matches MCP's tool-schema dialect)
- **typer 0.25.1**: type-hint-driven CLI; auto-`--help`; transitive via `mcp[cli]`

**Critical version pins (must be explicit in `pyproject.toml`):**
- `pytest-asyncio >= 1.0` (1.0+ removed `event_loop` fixture and changed loop-scope semantics — old tutorials are broken)
- `jsonschema >= 4.18` (deprecated `RefResolver` in favor of `referencing`)
- `mcp >= 1.27` (consistent `CallToolResult` shape, modern `stdio_client` API)

Full detail: STACK.md.

### Expected Features

The MVP feature set in PROJECT.md and the spec is exactly the right scope for v1: it covers all table stakes the ecosystem expects (stdio transport, list/call tools, schema validation, structured judge output, pytest CLI passthrough, env+YAML config, graceful timeouts) **and** ships the project's two real differentiators (description-quality testing as a first-class category with three concrete rubrics, and a local-first Ollama judge). Nothing in the MVP scope is gold-plating; nothing critical is missing.

**Must have (table stakes — all in MVP):**
- stdio transport via official `mcp` SDK (`stdio_client` context manager only)
- Connect, list tools, get tool by name, call tool with arguments
- Schema structural validation (7 deterministic checks per spec)
- Tool invocation returning `CallToolResult`
- Pytest as the runner; CLI entry that exits non-zero on failure
- Configuration via env vars + optional YAML overlay
- Pass/fail with reasoning from the judge (`JudgeResult { passed, score, reasoning, raw_response }`)
- Constrained JSON judge output (`format: json` + `stream: false`)
- Categorical 1–5 rubric, threshold `>= 4`
- Graceful timeout/error handling for Ollama and the MCP subprocess
- README with setup + run instructions; `uv sync` clean install

**Should have (differentiators — also all in MVP):**
- Three description-quality rubrics: clarity, disambiguation, parameter-self-explanatoriness — **the headline differentiator; no other MCP tool tests this**
- Local LLM judge by default (Ollama) — zero API cost, offline-capable
- Black-box principle stated as an explicit constraint, mechanically enforced via dependency partitioning
- Three-category test framing (schema / description / output) — clear mental model competitors don't articulate

**Defer (post-MVP):**
- LLM-generated test inputs from schema/description/output (the "Plant Seed" — natural v2 headline)
- Pluggable judge backends (`Judge` Protocol seam declared in MVP for zero-cost prep)
- Generic conformance test pack (parametrizable for any MCP server)
- Multi-tool / multi-server runs (pure parametrization on existing fixtures)
- HTTP and SSE transports
- JSON / JUnit XML / Markdown / Allure output (pytest's `--junitxml` is one flag away)
- Best-of-N judge consensus (only if single-shot proves materially flaky)
- Snapshot/golden-file testing, property-based fuzzing from `inputSchema`
- Cost / latency / token-usage metrics

Full detail: FEATURES.md.

### Architecture Approach

The spec's module layout is fundamentally sound and should be adopted as-is, with six concrete refinements that don't break the spec: split `fixtures.py` from `conftest.py` so future test packages can reuse fixtures; introduce `judge_protocol.py` (a 5-line `Protocol`) so the post-MVP backend swap is a 1-file addition; pull `prompts.py` out of `ollama_judge.py` so prompts are reused across backends; add `models.py` for shared Pydantic models (breaks circular-import risk); use `loop_scope="session"` plus `AsyncExitStack` ownership of `stdio_client` (the only async lifecycle pattern that survives subprocess crash during teardown); and put `homelab-mcp` in `[project.optional-dependencies.dev]` (or PEP 735 `[dependency-groups.dev]`) — **not** runtime dependencies — so the black-box rule is mechanically enforced.

**Major components:**
1. **`cli.py` (Typer)** — parses framework flags, resolves config, dispatches to `pytest.main()` (run) or `McpTestClient` (list-tools); returns pytest exit code
2. **`config.py` + `models.py`** — `pydantic-settings`-based layered loader (env → .env → YAML → CLI overrides); produces frozen `Config` model used by all fixtures
3. **`mcp_client.py`** — async wrapper around `stdio_client` + `ClientSession`; subprocess lifecycle owned by `AsyncExitStack` *inside the fixture*, not the class
4. **`ollama_judge.py` + `prompts.py` + `judge_protocol.py`** — async `httpx.AsyncClient` POSTing `/api/chat` with `stream:false, format:json, temperature:0, think:false`; defensive JSON parsing with `<think>` strip; implements `Judge` Protocol for future backend swap
5. **`schema_validator.py`** — pure sync functions: `validate_tool_schema`, `validate_response_against_schema` (no I/O, no async)
6. **`fixtures.py` + `conftest.py`** — session-scoped `pytest-asyncio` fixtures (`config`, `mcp_client`, `judge`, `target_tool`); fail-fast on missing target tool

**Build order (risk-first):** models → config → schema_validator → prompts → mcp_client (smoke-test against `homelab-mcp` standalone first) → judge_protocol → ollama_judge (smoke-test against live Ollama first) → fixtures → conftest → tests → cli → README. The two smoke tests before fixtures de-risk the integration unknowns before any framework wiring depends on them.

Full detail: ARCHITECTURE.md.

### Critical Pitfalls

The pitfalls research identified 18 specific risks. The top 5 critical for MVP — these *will* hit the project if not addressed in foundation work:

1. **anyio cancel-scope violation on `stdio_client` teardown** ("Attempted to exit cancel scope in a different task") — the single most painful failure mode for MCP Python SDK consumers in 2025/26. **Avoid by:** owning `stdio_client` and `ClientSession` lifecycle in an `AsyncExitStack` *inside the session-scoped `mcp_client` fixture*, with `pytest-asyncio` configured for `asyncio_default_fixture_loop_scope = "session"` and every async test marked `@pytest.mark.asyncio(loop_scope="session")`.

2. **qwen3 thinking tokens corrupting `format: json` output** — even with `format: json`, qwen3 family models can leak `<think>...</think>` blocks or repetition loops, producing malformed JSON. **Avoid by:** belt-and-braces in the request — `think: false` in body + `/no_think` directive in the system prompt + post-parse regex strip of `<think>` blocks + `temperature: 0` + `num_predict: 256` cap. Surface raw response in `JudgeResult.raw_response` for diagnosability.

3. **pytest-asyncio 1.0 scope-mismatch enforcement** — pytest-asyncio 1.0 (May 2025) removed the `event_loop` fixture, tightened scope rules, and broke most pre-1.0 tutorials. Spec doesn't pin a version. **Avoid by:** pinning `pytest-asyncio >= 1.0` in `pyproject.toml`, setting `asyncio_mode = "strict"` and `asyncio_default_fixture_loop_scope = "session"` in `[tool.pytest.ini_options]`, and never copy-pasting `event_loop` fixtures from old StackOverflow answers.

4. **Ollama cold-start timeout exceeds default httpx 5s timeout** — if `qwen3.6:latest` has been idle >5min, first judge call must reload the model (13–60+s); default httpx timeout is 5s. Symptom: first run of the day always fails. **Avoid by:** explicit `timeout=httpx.Timeout(JUDGE_TIMEOUT_SECONDS, connect=10.0)` on the `AsyncClient`, `keep_alive: "30m"` in the request body, and a warmup call in the `judge` fixture setup so cold-start cost is paid in a known place.

5. **`CallToolResult` shape variance** (`isError` flag; `content` vs `structuredContent`; both vs either populated) — naive `len(result.content) > 0` assertions will fail against structured-only servers; "no exception = success" misses `isError: true`. **Avoid by:** always checking `result.isError` first; accepting *either* non-empty `content` or non-null `structuredContent` as a valid response (both empty = fail); using `isinstance(block, TextContent)` rather than `block.type == "text"` for typed dispatch.

(Other notable risks include Windows ProactorEventLoop subprocess cleanup races, judge verbosity bias and prompt-injection via tool descriptions, JSON Schema draft confusion, `uv.lock` drift, and accidental black-box coupling via "just for types" imports. Each has a concrete mitigation in PITFALLS.md.)

Full detail: PITFALLS.md.

## Implications for Roadmap

Based on combined research, the MVP naturally decomposes into 5 phases plus a Phase 0 bootstrap. The ordering is dictated by two constraints: (a) the two integration risks (MCP stdio, Ollama qwen3) must be smoke-tested before any framework wiring depends on them, and (b) deterministic checks should land before LLM-judge checks because they're cheaper to debug and provide context (schema) the judge prompts need.

### Phase 0: Bootstrap & Black-Box Guardrails

**Rationale:** Several pitfalls (uv lockfile drift, pytest-asyncio version drift, accidental `homelab-mcp` import coupling, Windows command resolution, config precedence ambiguity) can only be prevented by getting the project skeleton right *before* anyone writes code. This is a small phase but critical.
**Delivers:** `pyproject.toml` with pinned deps in correct groups (`homelab-mcp` in dev/optional, **not** runtime), `uv.lock` committed, `.gitignore` excluding `.env`, `pyproject.toml` `[tool.pytest.ini_options]` with `asyncio_mode = "strict"` and `asyncio_default_fixture_loop_scope = "session"`, lint rule forbidding `homelab_mcp` imports in `src/` and `tests/`, `.env.example` and `config.example.yaml` stubs, src-layout package skeleton.
**Avoids:** Pitfalls 8 (black-box coupling), 10 (pytest-asyncio version drift), 13 (config precedence — at least the structural setup), 14 (Windows path handling), 18 (uv lockfile drift).
**Open question to resolve:** **Config precedence direction.** The spec says "config file overrides env vars" but the Click/Typer ecosystem norm is "flags > env > file > defaults." `pydantic-settings`' default is env > YAML > defaults. **The roadmap must pick one and document it before Phase 1 starts.** Recommendation: align with ecosystem norm (flags > env > YAML > defaults) so users' shell-env overrides aren't silently shadowed by checked-in YAML.

### Phase 1: Core Models, Config Loader & Schema Validator

**Rationale:** Pure-data, no I/O, no async, no fixtures. Highest-leverage code with lowest test cost. Build the foundation everything else depends on.
**Delivers:** `models.py` (Pydantic `Config`, `OllamaConfig`, `McpServerConfig`, `JudgeResult`, `ValidationIssue`); `config.py` using `pydantic-settings[yaml]` with explicit precedence layering; `schema_validator.py` with the 7 spec'd structural checks plus auto-detect of JSON Schema draft via `jsonschema.validators.validator_for`; `prompts.py` with rubric strings and the system prompt template (delimited subject block for prompt-injection hardening).
**Uses:** `pydantic`, `pydantic-settings`, `jsonschema` (≥ 4.18, no `RefResolver`), `pyyaml` (transitively).
**Avoids:** Pitfalls 11 (JSON Schema draft confusion), 13 (config precedence — locked in here), 16 (jsonschema `RefResolver`), 6 (judge prompt-injection — the delimited subject block lands here in `prompts.py`).
**Test scope:** Unit tests only. No fixtures, no subprocesses, no HTTP.

### Phase 2: MCP Client Wrapper (Integration Risk #1)

**Rationale:** First of two "prove it works" steps. Smoke-test `stdio_client` against a real `homelab-mcp` subprocess in a throwaway script *before* writing fixtures around it.
**Delivers:** `mcp_client.py` with `McpTestClient` thin wrapper exposing `list_tools`, `get_tool`, `call_tool`; explicit `asyncio.timeout()` around every SDK call (10s for `initialize`, 30s for `call_tool`); stderr captured to logger via SDK's `errlog` parameter; defensive handling of `CallToolResult.isError` and content/structuredContent variance. Throwaway smoke script proves it works against `homelab-mcp` standalone.
**Uses:** `mcp` SDK (`stdio_client`, `ClientSession`, `StdioServerParameters`).
**Avoids:** Pitfalls 1 (anyio cancel-scope — `AsyncExitStack` discipline starts here, completed in Phase 4), 4 (Windows subprocess cleanup), 5 (server-termination undetected), 12 (`CallToolResult` shape variance).
**Test scope:** Integration smoke test, not pytest fixture-driven yet.

### Phase 3: Ollama Judge (Integration Risk #2)

**Rationale:** Second "prove it works" step. Smoke-test `/api/chat` against the live Ollama at `127.0.0.1` *before* fixtures depend on it. All the qwen3-specific belt-and-braces lives here.
**Delivers:** `judge_protocol.py` (the `Judge` Protocol — 5-line zero-cost seam for post-MVP backend swap); `ollama_judge.py` implementing `Judge` via `httpx.AsyncClient` with explicit `Timeout(120, connect=10)`, request body with `stream:false, format:json, think:false, temperature:0, num_predict:256, keep_alive:"30m"`, `/no_think` in system prompt, post-parse `<think>` regex strip, defensive JSON extraction (find first `{`...matching `}` if direct parse fails), validation that all 3 required `JudgeResult` fields are present and `1 <= score <= 5`; warmup call helper. Throwaway smoke script proves cold-start works.
**Uses:** `httpx`, `pydantic`, `prompts.py` from Phase 1, `judge_protocol.py`.
**Avoids:** Pitfalls 2 (qwen3 thinking-token leak), 6 (judge biases), 7 (Ollama cold-start timeout), 9 (streaming default), 17 (`format: json` repetition).
**Test scope:** Integration smoke test against live Ollama. Unit tests for the `<think>`-strip parser.

### Phase 4: Pytest Fixtures (Wire Everything Together)

**Rationale:** With both integrations proven, the remaining work is wiring them as session-scoped pytest-asyncio fixtures. This is where the `AsyncExitStack` ownership pattern, `loop_scope="session"`, and `_preflight` health-check fixture all land.
**Delivers:** `fixtures.py` with `config`, `mcp_client`, `judge`, `target_tool`, `_preflight` (Ollama reachable + model in `/api/tags` + MCP server binary on PATH) — all `pytest_asyncio.fixture(scope="session", loop_scope="session")`; `conftest.py` re-exporting fixtures and setting Windows `ProactorEventLoopPolicy` defensively. All four MVP test functions in Category 1, 3 description-rubric tests in Category 2, 3 output conformance tests in Category 3 — exactly the spec's test list — wired against `homelab-mcp` / `list_registered_servers`.
**Uses:** `pytest-asyncio >= 1.0`, all Phase 1–3 modules.
**Avoids:** Pitfalls 1 (anyio cancel-scope — `AsyncExitStack` completed here), 3 (session-fixture cascade), 4 (Windows subprocess cleanup).
**Test scope:** Full pytest run against `homelab-mcp`. Acceptance criteria 2, 3, 4, 6 from the spec verifiable here.

### Phase 5: CLI, README & Acceptance

**Rationale:** Last layer; everything below is proven. CLI is a thin Typer wrapper around `pytest.main()` with config resolution. README + clean-checkout test close out acceptance criteria 1 and 5.
**Delivers:** `cli.py` with `run`, `list-tools`, `version` subcommands using Typer; `mcp-test-framework run` resolves config, sets `MCP_TEST_FRAMEWORK_CONFIG_FILE` env var, calls `pytest.main(["tests"] + extras)`, returns exit code; `list-tools` connects directly to `McpTestClient`, prints tools without invoking pytest or Ollama; `version` prints package version. README documents `uv sync`, `.env`/YAML setup, run instructions, troubleshooting (Windows `taskkill /F /IM homelab-mcp.exe`), and config-precedence rule. KeyboardInterrupt trap at CLI top level for clean subprocess kill.
**Uses:** `typer`, `pytest.main()`.
**Avoids:** Pitfalls 15 (Ctrl+C subprocess leak), and reinforces 8 (black-box — `list-tools` must not import `homelab_mcp`).
**Test scope:** Manual acceptance — clean-clone install, exit-code check, cold-Ollama run, post-run `Get-Process homelab-mcp` check.

### Phase Ordering Rationale

- **Phase 0 first:** dependency partitioning, pytest-asyncio version pin, and config-precedence decision are foundation choices that downstream phases compound; deferring them creates expensive rework.
- **Phase 1 (pure data) before Phase 2 (subprocess) before Phase 3 (HTTP):** progressively higher I/O complexity. Phase 1 is unit-testable in isolation; Phase 2 needs `homelab-mcp` running; Phase 3 needs Ollama up.
- **Phases 2 and 3 each build a smoke script before the fixture layer (Phase 4) consumes them.** Discovers SDK/Ollama surprises in 30-line scripts, not in fixtures already wired against them.
- **Phase 4 (fixtures + tests) before Phase 5 (CLI):** so raw `pytest tests/` keeps working post-CLI for users who prefer it.
- **All phases honor the black-box rule** mechanically (Phase 0 dependency partition + lint rule) rather than as a code-review-only norm.

### Research Flags

Phases likely needing deeper research during planning (suggest `/gsd-research-phase`):

- **Phase 3 (Ollama Judge):** the qwen3-on-Ollama landscape is volatile; the specific Ollama version on the homelab plus the exact `qwen3.6:latest` digest may exhibit different behaviors than the documented issues. Worth a 30-minute live-spike against the actual instance before locking in the parser. Also worth re-checking whether passing a JSON Schema as `format` (per Ollama's structured-output upgrade path) is more reliable than `format: "json"`.
- **Phase 4 (Fixtures):** Windows ProactorEventLoop subprocess cleanup races have MEDIUM evidence in research — verify on the actual Windows 11 target machine specifically. Worth a quick research pass on whether pytest-asyncio 1.3.x has fixed any of the documented 0.x quirks before locking in the policy choice.

Phases with standard, well-documented patterns (skip phase research):

- **Phase 0 (Bootstrap):** standard `uv` + `pyproject.toml` + `pytest.ini_options` setup; thoroughly covered.
- **Phase 1 (Models, Config, Schema Validator):** `pydantic-settings` + `jsonschema` extensively documented.
- **Phase 2 (MCP Client):** the `stdio_client` + `ClientSession` + `AsyncExitStack` pattern is the only sane approach.
- **Phase 5 (CLI):** Typer-wraps-pytest is the Tavern/Schemathesis idiom; well-documented.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | All 8 packages verified via Context7 and PyPI metadata as of 2026-05-04; Python 3.14 compatibility confirmed for all (MEDIUM-HIGH on `mcp` 1.27 specifically since it classifies through 3.13, but pure-Python at the SDK layer). The two refinements (`pydantic-settings`, `typer`) are MEDIUM-confidence judgment calls that simplify but don't change behavior. |
| Features | **MEDIUM-HIGH** | Comprehensive ecosystem scan covered MCP-specific tooling, adjacent contract-testing tools, and LLM-eval frameworks. MEDIUM-HIGH not HIGH because the description-quality differentiator is novel — three specific rubrics are research-supported but ultimately a hypothesis that ships with the MVP. |
| Architecture | **HIGH** on component boundaries, build order, and lifecycle pattern; **MEDIUM** on judge abstraction shape | The `AsyncExitStack`-owned subprocess fixture, session-scoped `loop_scope`, and CLI-wraps-pytest patterns are all confirmed against multiple sources. The `Judge` Protocol shape is correct in direction; exact method signature may need a tweak when the second backend is implemented. |
| Pitfalls | **HIGH** for the top-5 critical ones | anyio cancel-scope, pytest-asyncio 1.0 scope changes, qwen3 thinking + JSON corruption, `CallToolResult` shape variance, Ollama cold-start are all backed by multiple GitHub issue reproducers. MEDIUM on Windows-specific edge cases. LOW on the exact phrasing of judge prompt-injection hardening — must be re-evaluated against the final rubrics. |

**Overall confidence:** **HIGH** — research is consistent across the four files, recommended stack and architecture are battle-tested patterns from comparable projects, and the critical pitfalls have concrete mitigations. Two MEDIUM-confidence items (judge reliability, config precedence) are flagged as decisions for the roadmap to resolve, not blockers to starting work.

### Gaps to Address

- **Config precedence direction** (spec says YAML>env, ecosystem norm is env>YAML, `pydantic-settings` default is env>YAML). **Resolve before Phase 1 starts** — pick one, document in README, write a `test_config_precedence` unit test. **Recommendation:** match ecosystem norm (flags > env > YAML > defaults).
- **Exact Ollama version + qwen3.6:latest digest on the homelab** — defensive parser layers are designed to be robust to version drift, but a live-spike during Phase 3 will validate. **Resolve during Phase 3 smoke test;** log version pin in README troubleshooting.
- **Judge prompt-injection hardening** — the delimited subject block pattern is research-validated, but exact delimiter strings and rubric phrasing should be tested against a known-injection synthetic tool description. **Resolve during Phase 3.**
- **Windows ProactorEventLoop subprocess cleanup on the actual Windows 11 target** — research has MEDIUM confidence; needs live verification. **Resolve during Phase 4.**
- **Whether to ship `Judge` Protocol seam in MVP or defer** — research recommends shipping it (5 LOC, zero MVP cost, prevents post-MVP refactor); spec leaves it implicit. **Resolve in roadmap creation** (recommendation: include in Phase 3).

## Sources

### Primary (HIGH confidence)

- **MCP / Anthropic official:** Context7 `/modelcontextprotocol/python-sdk`; MCP Python SDK README; MCP specification 2025-06-18 — Tools; SEP-1613.
- **pytest / pytest-asyncio (official):** Context7 `/pytest-dev/pytest-asyncio`; pytest-asyncio 1.3.0 docs; pytest invocation docs; pytest import mechanisms.
- **Stack libraries (official):** Context7 `/python-jsonschema/jsonschema`; Context7 `/pydantic/pydantic-settings`; Context7 `/ollama/ollama-python`; PyPI metadata for all 10 candidate packages (verified 2026-05-04).
- **MCP Python SDK pitfall issues:** modelcontextprotocol/python-sdk #396, #521, #577, #1452.
- **Ollama / qwen3 pitfall issues:** ollama/ollama #10929, #10976, #14645, #11032, #12917.

### Secondary (MEDIUM confidence)

- **MCP testing-tool ecosystem:** r-huijts/mcp-server-tester, L-Qun/mcp-testing-framework, pytest-mcp on PyPI, f/mcptools, Accenture/mcp-bench, FastMCP testing guide.
- **LLM-as-judge ecosystem:** DeepEval, Promptfoo, RAGAS, Langfuse, Confident AI, Patronus, W&B; "Justice or Prejudice" (arXiv 2410.02736); "JudgeDeceiver" (arXiv 2403.17710); "Smell-Aware Evaluation of MCP Server Descriptions" (arXiv 2602.18914).
- **Architectural precedents:** Tavern, Schemathesis; pytest-asyncio #944, #1175, #708; anyio #74.

### Project context

- `.planning/PROJECT.md`
- `docs/mcp_test_framework_mvp_spec.md`
- `.planning/research/STACK.md`
- `.planning/research/FEATURES.md`
- `.planning/research/ARCHITECTURE.md`
- `.planning/research/PITFALLS.md`

---
*Research completed: 2026-05-04*
*Ready for roadmap: yes*
