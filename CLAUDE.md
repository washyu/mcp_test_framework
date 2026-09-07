# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

v1.5 shipped on 2026-05-28 (six milestones, phases 01 to 35). The framework lives under `src/mcp_test_framework/` with self-tests under `tests/`; planning artifacts live in `.planning/` (`STATE.md`, `ROADMAP.md`, `PROJECT.md`). **The original design document is `docs/mcp_test_framework_mvp_spec.md`; current operator-facing docs are `README.md` and `docs/`.**

## What This Project Is

`mcp_test_framework` is a `pytest`-based framework for testing MCP (Model Context Protocol) servers. The MVP targets a single MCP server (`homelab-mcp`) over stdio and a single tool (`list_registered_servers`), running three categories of tests:

1. **Schema validation**: deterministic structural checks on the tool's declared schema
2. **Description quality**: uses a local Ollama-hosted LLM (`qwen3.6:latest` at `127.0.0.1:11434`) as a judge with a 1 to 5 rubric (pass threshold: `score >= 4`)
3. **Output conformance**: deterministic checks on `CallToolResult` shape, optionally judged

The framework is deliberately narrow for the MVP. See the "Out of Scope" and "Future Work" sections of the spec before suggesting generalizations.

v1.3 introduced a **test-code author** persona as a second first-class user alongside the operator. The public-API surface uses the `test_code` naming as of v1.4; the legacy `sdet` surface was retired in v1.5 and its entry points now hard-reject with a migration pointer. The operator runs the contract pass (schema + description + output checks); the test-code author writes stateful scenarios under `tests/test_code/` that exercise the MCP server end-to-end. Both personas share the same CLI surface: the test-code author uses the `--test-code` flag, the `mcp_test_framework.test_code` import surface (`mcp_session`, `tool()`, `ToolCallError`), and the `tests/test_code/` discovery scope. See [`docs/TEST-CODE-AUTHORING.md`](docs/TEST-CODE-AUTHORING.md) for the authoring walkthrough. <!-- noqa: sdet-rename-shim -->

## Tooling

- Python **3.12** (pinned in `.python-version` and `requires-python` in `pyproject.toml`)
- Dependency management: **`uv`** (single project folder, lockfile-driven)
- Test runner: `pytest` with `pytest-asyncio` in strict mode

Commands:

```
uv sync                                     # install deps
uv run mcp-contracts list-tools        # connect via stdio, print tool list
uv run mcp-contracts run               # CI entry point: runs pytest, exits with pytest's code
uv run pytest tests/path::test_name         # run a single test
```

The legacy `uv run mcp-test-framework` console script no longer runs the framework.
As of v1.5 it hard-rejects with an operator-tone message pointing at `mcp-contracts` and exits non-zero;
it is kept only as that pointer and is slated for clean deletion in v1.6.

## Architecture Notes (must-read before changing the framework)

- **MCP transport is stdio only.** The MCP SDK's `stdio_client` context manager launches the server as a subprocess; do **not** use `subprocess.Popen` directly.
- **The framework treats `homelab-mcp` as a black box.** Never import from or read its source code: it is a subprocess under test.
- **Ollama specifics:** call `/api/chat` with `stream: false` and `format: json` to get a single structured JSON response. The judge falls back to a failure result with the raw response on parse error rather than crashing the run.
- **Config precedence:** env vars → `config.yaml` overlay → CLI flags (highest). See spec §Configuration for the full env var list.
- **Async:** use `asyncio.timeout` (3.11+) around any subprocess or HTTP operation that could hang. All MCP client methods are async; tests use explicit `@pytest.mark.asyncio` markers.
- **Fixtures are session-scoped** (`mcp_client`, `judge`, `target_tool`, `config`). The `target_tool` fixture must fail the run early if the configured tool is absent from the server.

## Module Layout (per spec)

```
src/mcp_test_framework/
  cli.py              # pytest wrapper with framework-specific flags
  config.py           # env + YAML loader, Pydantic-modeled
  mcp_client.py       # async stdio MCP client wrapper (McpTestClient)
  ollama_judge.py     # OllamaJudge → JudgeResult{passed, score 1-5, reasoning, raw_response}
  schema_validator.py # deterministic JSON Schema checks → ValidationIssue list
  fixtures.py         # session-scoped pytest fixtures
tests/
  conftest.py
  test_homelab_list_registered_servers.py
```

<!-- GSD:project-start source:PROJECT.md -->
## Project

**mcp_test_framework**

A pytest-based Python framework for testing MCP (Model Context Protocol) servers. It connects to one MCP server over stdio, runs deterministic schema/output checks against a target tool, and uses a local Ollama-hosted LLM as a judge for description quality. The MVP targets `homelab-mcp` and its `list_registered_servers` tool to validate the integration contract end-to-end before generalizing.

**Core Value:** A `pytest`-runnable test suite that exercises one MCP tool end-to-end (schema → call → judge) and exits non-zero on any failure — proving the framework's integration contract before adding breadth.

### Constraints

- **Tech stack**: Python 3.12, `uv` for dependency management — pinned in `.python-version` and `pyproject.toml`.
- **MCP transport**: stdio only via the official `mcp` SDK's `stdio_client` context manager — no raw `subprocess.Popen`.
- **Judge backend**: Ollama at `127.0.0.1:11434` with model `qwen3.6:latest`, called via `/api/chat` with `stream: false` and `format: json` for structured JSON output.
- **Async**: pytest-asyncio in strict mode with explicit `@pytest.mark.asyncio` markers. `asyncio.timeout` (3.11+) wraps any subprocess or HTTP operation that could hang.
- **Black box**: never import, read, or vendor `homelab-mcp` source — it is a subprocess under test.
- **Pass threshold**: judge tests pass at `score >= 4` (1–5 rubric).
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## TL;DR — Validation of the Spec
## Recommended Stack
### Core Technologies
| Technology | Version (latest as of May 2026) | Purpose | Why Recommended |
|------------|---------------------------------|---------|-----------------|
| **Python** | 3.12 (pinned) | Runtime | Pinned by project; EOL 2028-10; native `asyncio.timeout` (3.11+), PEP 695 generics |
| **uv** | 0.11.x | Project + venv + lockfile manager | Already chosen by project; 10–100× faster than pip, deterministic `uv.lock`, single-binary, `uv run` wraps the CLI cleanly |
| **mcp** (Python SDK) | 1.27.0 | Official MCP client over stdio | The only authoritative MCP client for Python; spec mandates `stdio_client` context manager (no raw `subprocess.Popen`); session model (`ClientSession`) handles MCP handshake, tool listing, and `call_tool` natively |
| **pytest** | 9.0.3 | Test runner | The pytest 9.x line is the current major; full 3.14 classifier; project's spec hard-requires pytest as the test surface |
| **pytest-asyncio** | 1.3.0 | Async test integration | The 1.x stable line; **strict mode is now the default** (matches spec); requires explicit `@pytest.mark.asyncio` and `@pytest_asyncio.fixture` (matches spec's reuse model); supports session-scoped event loops needed for the long-lived `mcp_client` fixture |
| **httpx** | 0.28.1 | Async HTTP client to Ollama | Async-first, `httpx.Timeout`-friendly, already a transitive dep of `mcp`; preferred over `aiohttp` for new code in 2026 (cleaner API, sync+async parity, better timeout primitives) |
| **pydantic** | 2.13.3 | Data models (`JudgeResult`, `ValidationIssue`, config) | v2 is the only supported line; classifies 3.14; required by `mcp` (`>=2.11,<3`) so already pinned in deptree; gives you `BaseModel.model_validate_json` for cheap, safe parsing of Ollama's JSON output |
| **pydantic-settings** | 2.14.0 | Layered config (env → .env → YAML → CLI override) | **Replaces `python-dotenv` + hand-rolled YAML overlay.** Built-in `YamlConfigSettingsSource`, dotenv loader, env-var loader, and explicit `settings_customise_sources` precedence — exactly the precedence the spec describes ("env first, YAML overlays, CLI overrides"). Already a transitive dep of `mcp`. |
| **jsonschema** | 4.26.0 | Validate MCP tool `inputSchema`/`outputSchema` and tool responses | The reference Python implementation; ship Draft 2020-12 (`Draft202012Validator`) which is what MCP tool schemas use; `iter_errors()` gives you all errors at once (perfect for the spec's `validate_tool_schema → list[ValidationIssue]`); already a transitive dep of `mcp` |
| **PyYAML** | 6.0.3 | YAML parsing (under `pydantic-settings[yaml]`) | Universal, stable; only included because `YamlConfigSettingsSource` requires it. Use `yaml.safe_load` semantics (`pydantic-settings` does this for you). |
| **typer** | 0.25.1 | CLI framework (`mcp-contracts run/list-tools/version`) | Click-based but type-hint-driven — your handlers are plain typed functions; pydantic-friendly; auto-generates `--help`; already a transitive dep of `mcp` (under `[cli]` extra). See "CLI" section. |
### Supporting Libraries (transitive — do not declare directly)
| Library | Why it's there | Action |
|---------|---------------|--------|
| `anyio>=4.5` | `mcp`'s async runtime abstraction (powers `stdio_client`) | Don't declare directly. If you ever want trio support, use `pytest-asyncio`'s anyio integration; but for MVP stick to plain asyncio. |
| `httpx-sse`, `sse-starlette`, `starlette`, `uvicorn`, `python-multipart` | `mcp`'s server-side / SSE transport plumbing | Ignored — stdio-only is the MVP scope. |
| `typing-extensions`, `typing-inspection` | Pydantic v2 runtime needs | No action. |
| `pyjwt[crypto]`, `pywin32` | Auth / Windows compat in `mcp` | No action. |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| `ruff` | Linter + formatter | The 2026 standard for Python lint+format; replaces black + isort + flake8. Add as `[tool.uv]`-managed dev dep. |
| `mypy` *or* `pyright` | Optional type checker | Not strictly required for MVP; `pyright` ships as a binary, faster on watch mode. Defer to Phase 2 if at all. |
## Installation
# All declared dependencies for the MVP
# The system-under-test (per spec)
# Dev / lint
- `pydantic-settings[yaml]` pulls `pyyaml` automatically — **do not declare `pyyaml` directly.**
- **Drop `python-dotenv` from the spec's dep list** — `pydantic-settings` has a built-in dotenv source.
- Lower bounds (`>=`) are intentional — `uv.lock` will pin exact versions for reproducibility.
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `httpx` for Ollama calls | `ollama` (official Python client, v0.6.2) | If you want auto-typed `ChatResponse`, function-calling helpers, and Pydantic-schema-as-`format=` shorthand. **Skipped for MVP** because: (1) spec explicitly says "Ollama via `/api/chat`" and one HTTP `POST` is trivial in `httpx`, (2) keeps the judge backend swappable later (post-MVP "pluggable judge backends"), (3) avoids one more dep. Reconsider if you adopt the official client's structured-output ergonomics. |
| `httpx` async client | `aiohttp` 3.x | Only if you already have an `aiohttp`-based codebase. For new 2026 code, `httpx` wins on API ergonomics and sync/async parity. |
| `pydantic-settings` + YAML | Hand-rolled `config.py` (env vars + `yaml.safe_load` overlay) | If you have an unusual precedence rule or want zero Pydantic in your config layer. The spec's described precedence ("env first, YAML overlays, CLI overrides") is precisely what `pydantic-settings` ships out of the box, so hand-rolling is strictly more code and more bugs. |
| `typer` | `click` (8.3.3) | If you're allergic to magic decorator-and-type-hint frameworks and prefer explicit `@click.option(...)` everywhere. Click is the foundation `typer` is built on; both are fine. Typer wins on signal-to-noise for short CLIs like this (3 commands). |
| `typer` | `argparse` (stdlib) | If you want zero CLI deps. For this project: not worth the verbosity — `mcp` already pulls `typer` transitively under `[cli]`, so it's effectively free. |
| `jsonschema` | `fastjsonschema` (2.21.2), `jsonschema-rs` (0.46.4) | If schema validation becomes a hot path. `fastjsonschema` compiles schemas to Python code; `jsonschema-rs` is a Rust binding. Neither is justified at MVP scale (one schema, validated once per test run). `jsonschema` is also already a transitive dep of `mcp`. |
| `pytest-asyncio` strict | `anyio` pytest plugin | If you target `trio` *and* `asyncio`. You don't — Ollama's HTTP layer and `mcp`'s `stdio_client` are both used over asyncio in this project. Stick with `pytest-asyncio` strict. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `python-dotenv` as a direct dep | Redundant — `pydantic-settings` has a built-in dotenv source with the same precedence semantics; declaring it directly creates two ways to load `.env` and risks drift between them | `pydantic-settings`'s `model_config = SettingsConfigDict(env_file=".env")` |
| Raw `subprocess.Popen` to launch the MCP server | Bypasses MCP handshake, session lifecycle, and stdio framing; spec explicitly forbids this | `mcp.client.stdio.stdio_client` context manager + `ClientSession` |
| `requests` (sync) for Ollama | Sync HTTP inside an async test will block the event loop; Ollama judge calls can take 30s+ and would freeze concurrent fixtures | `httpx.AsyncClient` |
| `pytest-asyncio` `auto` mode | Spec mandates strict mode; auto mode collides with other async plugins and obscures which tests are actually async | `asyncio_mode = "strict"` (which is now the default in 1.x) |
| `unittest`-style `IsolatedAsyncioTestCase` | Doesn't compose with pytest fixtures; loses the `mcp_client`/`judge`/`target_tool` session-scoped fixture story | `pytest-asyncio` markers |
| `pyyaml` declared at top level | Indirect through `pydantic-settings[yaml]`; declaring twice can cause version conflicts later | Use the `[yaml]` extra |
| Pydantic v1 | EOL; doesn't classify 3.14; `mcp` requires `pydantic>=2.11,<3` | Pydantic v2 (already required by `mcp`) |
| `aiohttp.ClientSession` for Ollama | Heavier API surface, weaker timeout primitives, no sync parity for ad-hoc scripts | `httpx.AsyncClient` |
| `setuptools` / `setup.py` | Project already uses `pyproject.toml` + `uv`; mixing build backends is a footgun | `hatchling` (pyproject default with `uv init`) or whatever `uv init` produced — leave as-is |
## CLI: Typer vs Click vs argparse
- **argparse** — works, no deps. Verbose for 3 subcommands; you'll hand-write `subparsers` boilerplate. Shipping the version of pytest invocation that handles `-k`, `-v`, *and* arbitrary pytest passthrough means a manual `parser.parse_known_args()` + forwarding step.
- **Click** (8.3.3) — battle-tested, decorator-based, mature. Excellent. Slightly more verbose than typer.
- **Typer** (0.25.1) — Click underneath, but command signatures are plain typed functions. `def run(config: Path | None = None, k: str | None = None, verbose: bool = False)` becomes a complete CLI command. Auto-rendered `--help`. Already a transitive dep of `mcp`'s `[cli]` extra.
## Pytest-asyncio Configuration (specific to this project)
## Ollama Judge Call: Confirmed `format: json` Is Correct
- `stream: false` — single response object (matches spec).
- `format: "json"` — Ollama-side JSON-mode constraint; the model is grammar-forced to produce valid JSON. Combined with Pydantic `JudgeResult.model_validate_json(response["message"]["content"])` this gives you robust structured output. The spec's "fall back to a failure result with the raw response on parse error" pattern is correct because even with `format: json` the model can produce a JSON object with the *wrong shape* (e.g., `score: "high"` instead of `score: 4`).
- **Optional upgrade (future):** Ollama also accepts a JSON Schema as the value of `format`. You can pass `JudgeResult.model_json_schema()` to constrain not just "valid JSON" but "exact shape." Recommended deferred to a Plant-Seed milestone — for MVP, `"json"` + Pydantic-validate is simpler and matches the spec verbatim.
- `options.temperature: 0` (strongly recommended addition to spec) — judges should be near-deterministic; temperature 0 reduces flakiness without affecting the rubric's integrity.
## Version Compatibility
| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `mcp 1.27.0` | Python 3.10–3.14 | Classifies through 3.13 only; PyPI `requires-python = ">=3.10"`. No known 3.14 issues; widely used on 3.13 with no breaking interp changes between 3.13 and 3.14 that touch this codepath. **Confidence: MEDIUM** that 3.14 is fully smoke-tested upstream. Mitigation: `uv sync` will surface any C-ext build issues immediately, and `mcp` is pure-Python at the SDK layer. |
| `pydantic 2.13` | `pydantic-core 2.x` (auto), Python 3.9–3.14 | 3.14 explicitly classified. |
| `pytest 9.0` + `pytest-asyncio 1.3` | Python 3.10–3.14 | Both classify 3.14. `pytest-asyncio` 1.x is the only line compatible with `pytest>=9`. |
| `httpx 0.28` | Python 3.8+ | No 3.14 classifier (httpx skips classifiers) but is the de facto async client and runs on 3.14 in production. Confidence: HIGH on real-world compat. |
| `jsonschema 4.26` | Python 3.10+ | Use `Draft202012Validator` to match MCP's tool schema dialect. |
| `pydantic-settings 2.14` | Pydantic 2.11+, Python 3.10+ | The `[yaml]` extra requires `pyyaml`. Pin source order via `settings_customise_sources` to make CLI > env > YAML > defaults explicit. |
## Confidence Assessment
| Choice | Level | Source(s) |
|--------|-------|-----------|
| `mcp` SDK as the only sane stdio client | HIGH | Context7 `/modelcontextprotocol/python-sdk`, official PyPI metadata |
| `pytest-asyncio` strict mode | HIGH | Context7 `/pytest-dev/pytest-asyncio` (configuration.md, concepts.md) — confirms strict is default in 1.x |
| `httpx` for Ollama (vs `ollama` client) | HIGH for "either works"; MEDIUM on the recommendation to prefer raw `httpx` | Spec mandates `/api/chat` HTTP semantics directly; both libs are current |
| `format: "json"` on `/api/chat` | HIGH | Context7 Ollama Python docs + PyPI `ollama` package; matches spec verbatim |
| `jsonschema` Draft202012Validator | HIGH | Context7 `/python-jsonschema/jsonschema` |
| `pydantic-settings` over hand-rolled config | MEDIUM (this is a recommendation that *changes* the spec; the spec's hand-rolled approach also works) | Context7 `/pydantic/pydantic-settings`, PyPI metadata |
| `typer` over argparse / Click | MEDIUM (judgment call; all three are viable) | PyPI metadata, transitive-dep observation in `mcp`'s `[cli]` extra |
| Python 3.14 ready for all libs | MEDIUM-HIGH | PyPI classifiers verified for all libs except `mcp` (classifies 3.13) and `httpx` (no classifiers); both are pure-Python and 3.14-safe in practice |
| `uv` 0.11.x | HIGH | PyPI metadata, project already uses it |
## Sources
- Context7 `/modelcontextprotocol/python-sdk` (v1.12.4 indexed, latest 1.27.0 on PyPI) — `stdio_client`, `ClientSession`, `list_tools`, `call_tool` patterns; confirmed stdio-context-manager API
- Context7 `/pytest-dev/pytest-asyncio` — `asyncio_mode` defaults, `asyncio_default_fixture_loop_scope` deprecation behavior, strict-mode requirements
- Context7 `/python-jsonschema/jsonschema` — `Draft202012Validator`, `iter_errors` patterns
- Context7 `/pydantic/pydantic-settings` — `YamlConfigSettingsSource`, `env_file`, `settings_customise_sources` precedence
- Context7 `/ollama/ollama-python` — `/api/chat` contract, `format` parameter, structured-output patterns
- PyPI metadata (https://pypi.org/pypi/{mcp,pytest,pytest-asyncio,httpx,pydantic,pydantic-settings,jsonschema,pyyaml,python-dotenv,typer,click,ollama,uv,homelab-mcp,fastjsonschema,jsonschema-rs}/json) — current versions, `requires-python`, `requires-dist`, classifiers (verified 2026-05-04)
- https://endoflife.date/api/python.json — Python 3.14.4 latest, EOL 2030-10-31
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
