# Stack Research — MCP Test Framework

**Domain:** Python pytest-based integration test framework for MCP servers, with Ollama LLM-as-judge
**Researched:** 2026-05-04
**Python target:** 3.14 (pinned in `.python-version` and `pyproject.toml`)
**Overall confidence:** HIGH for core stack, MEDIUM for two judgement-call swaps (config, CLI)

## TL;DR — Validation of the Spec

The spec's eight-package list (`mcp`, `pytest`, `pytest-asyncio`, `httpx`, `pydantic`, `pyyaml`, `python-dotenv`, `jsonschema`) is **substantially correct for May 2026** — every choice is current, maintained, and Python 3.14-compatible. Two refinements are recommended:

1. **Replace `python-dotenv` + `pyyaml` + a hand-rolled config loader with `pydantic-settings` (with the `[yaml]` extra).** It already ships with first-class `YamlConfigSettingsSource`, env precedence, and `.env` support — exactly the layered config the spec describes — and `pydantic-settings` is *already* a transitive dependency of `mcp`. This eliminates `python-dotenv` as a direct dep, keeps `pyyaml` (still needed by the YAML source), and removes a non-trivial slice of `config.py` you'd otherwise hand-write.
2. **Adopt `typer` for the CLI rather than raw `argparse`.** The spec doesn't pick a CLI lib. `typer` is *already* a transitive dependency of `mcp` (under its `[cli]` extra), is the de facto modern Python CLI library in 2026, and aligns naturally with type hints + Pydantic models you already use elsewhere. See "CLI" section below for the full rationale vs Click.

Everything else in the spec — strict-mode `pytest-asyncio`, raw `httpx` to call Ollama (not the `ollama` Python client), `jsonschema` Draft 2020-12, single-shot judge with `format: json` — is the correct 2026 choice and should be kept as-is.

## Recommended Stack

### Core Technologies

| Technology | Version (latest as of May 2026) | Purpose | Why Recommended |
|------------|---------------------------------|---------|-----------------|
| **Python** | 3.14.4 | Runtime | Pinned by project; full release, EOL 2030-10-31; native `asyncio.timeout` (3.11+), PEP 695 generics, faster interp |
| **uv** | 0.11.x | Project + venv + lockfile manager | Already chosen by project; 10–100× faster than pip, deterministic `uv.lock`, single-binary, `uv run` wraps the CLI cleanly |
| **mcp** (Python SDK) | 1.27.0 | Official MCP client over stdio | The only authoritative MCP client for Python; spec mandates `stdio_client` context manager (no raw `subprocess.Popen`); session model (`ClientSession`) handles MCP handshake, tool listing, and `call_tool` natively |
| **pytest** | 9.0.3 | Test runner | The pytest 9.x line is the current major; full 3.14 classifier; project's spec hard-requires pytest as the test surface |
| **pytest-asyncio** | 1.3.0 | Async test integration | The 1.x stable line; **strict mode is now the default** (matches spec); requires explicit `@pytest.mark.asyncio` and `@pytest_asyncio.fixture` (matches spec's reuse model); supports session-scoped event loops needed for the long-lived `mcp_client` fixture |
| **httpx** | 0.28.1 | Async HTTP client to Ollama | Async-first, `httpx.Timeout`-friendly, already a transitive dep of `mcp`; preferred over `aiohttp` for new code in 2026 (cleaner API, sync+async parity, better timeout primitives) |
| **pydantic** | 2.13.3 | Data models (`JudgeResult`, `ValidationIssue`, config) | v2 is the only supported line; classifies 3.14; required by `mcp` (`>=2.11,<3`) so already pinned in deptree; gives you `BaseModel.model_validate_json` for cheap, safe parsing of Ollama's JSON output |
| **pydantic-settings** | 2.14.0 | Layered config (env → .env → YAML → CLI override) | **Replaces `python-dotenv` + hand-rolled YAML overlay.** Built-in `YamlConfigSettingsSource`, dotenv loader, env-var loader, and explicit `settings_customise_sources` precedence — exactly the precedence the spec describes ("env first, YAML overlays, CLI overrides"). Already a transitive dep of `mcp`. |
| **jsonschema** | 4.26.0 | Validate MCP tool `inputSchema`/`outputSchema` and tool responses | The reference Python implementation; ship Draft 2020-12 (`Draft202012Validator`) which is what MCP tool schemas use; `iter_errors()` gives you all errors at once (perfect for the spec's `validate_tool_schema → list[ValidationIssue]`); already a transitive dep of `mcp` |
| **PyYAML** | 6.0.3 | YAML parsing (under `pydantic-settings[yaml]`) | Universal, stable; only included because `YamlConfigSettingsSource` requires it. Use `yaml.safe_load` semantics (`pydantic-settings` does this for you). |
| **typer** | 0.25.1 | CLI framework (`mcp-test-framework run/list-tools/version`) | Click-based but type-hint-driven — your handlers are plain typed functions; pydantic-friendly; auto-generates `--help`; already a transitive dep of `mcp` (under `[cli]` extra). See "CLI" section. |

### Supporting Libraries (transitive — do not declare directly)

These come in via `mcp` and `pydantic-settings`. Listed for awareness, not for pinning:

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

```bash
# All declared dependencies for the MVP
uv add \
  "mcp>=1.27" \
  "pytest>=9.0" \
  "pytest-asyncio>=1.3" \
  "httpx>=0.28" \
  "pydantic>=2.13,<3" \
  "pydantic-settings[yaml]>=2.14" \
  "jsonschema>=4.26" \
  "typer>=0.25"

# The system-under-test (per spec)
uv add "homelab-mcp>=1.7"

# Dev / lint
uv add --dev "ruff>=0.8"
```

Notes:
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

The spec describes `mcp-test-framework run [--config PATH] [-k EXPRESSION] [-v]`, `list-tools`, and `version`. Three commands, a handful of flags, all of which need to forward to pytest cleanly.

- **argparse** — works, no deps. Verbose for 3 subcommands; you'll hand-write `subparsers` boilerplate. Shipping the version of pytest invocation that handles `-k`, `-v`, *and* arbitrary pytest passthrough means a manual `parser.parse_known_args()` + forwarding step.
- **Click** (8.3.3) — battle-tested, decorator-based, mature. Excellent. Slightly more verbose than typer.
- **Typer** (0.25.1) — Click underneath, but command signatures are plain typed functions. `def run(config: Path | None = None, k: str | None = None, verbose: bool = False)` becomes a complete CLI command. Auto-rendered `--help`. Already a transitive dep of `mcp`'s `[cli]` extra.

**Recommendation: Typer.** With three small commands, the typer boilerplate is essentially zero and the type hints serve double duty as both CLI definition and signature documentation. Click is a perfectly fine alternative if you'd rather avoid the implicit "this type hint becomes a CLI flag" magic. **Avoid argparse** — for three subcommands with passthrough you'll hand-write more code than typer + click combined.

## Pytest-asyncio Configuration (specific to this project)

Add to `pyproject.toml` to silence the `asyncio_default_fixture_loop_scope` deprecation warning and to lock in the spec's strict mode:

```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "session"
testpaths = ["tests"]
```

**Why session-scoped:** the spec's `mcp_client`, `judge`, and `target_tool` fixtures are session-scoped (one MCP subprocess for the whole run, one Ollama HTTP client). Without `asyncio_default_fixture_loop_scope = "session"` you'll either get a deprecation warning (current behavior) or, in a future pytest-asyncio version when the default flips to `"function"`, your session-scoped async fixtures will be re-created per test — defeating the whole point.

## Ollama Judge Call: Confirmed `format: json` Is Correct

Per Ollama's `/api/chat` contract (verified via official docs):

```json
{
  "model": "qwen3.6:latest",
  "messages": [
    {"role": "system", "content": "<judge prompt>"},
    {"role": "user", "content": "<rubric + subject>"}
  ],
  "stream": false,
  "format": "json",
  "options": {"temperature": 0}
}
```

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

---
*Stack research for: Python MCP-server integration test framework with Ollama LLM-as-judge*
*Researched: 2026-05-04*
