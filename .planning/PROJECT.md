# mcp_test_framework

## What This Is

A pytest-based Python framework for testing MCP (Model Context Protocol) servers. It connects to one MCP server over stdio, runs deterministic schema/output checks against a target tool, and uses a local Ollama-hosted LLM as a judge for description quality. v1.0 ships a CLI (`mcp-test-framework run|list-tools|version`) that drives `homelab-mcp`'s `list_keyring_credentials` (default; switchable to `list_registered_servers`) end-to-end against a live Ollama judge. The integration contract is proven; v2 generalization can now build on these seams.

## Core Value

A `pytest`-runnable test suite that exercises one MCP tool end-to-end (schema → call → judge) and exits non-zero on any failure — proving the framework's integration contract before adding breadth.

## Current State

**Shipped:** v1.0 MVP (2026-05-06)

- 7 phases, 22 plans, 29/29 requirements satisfied (audit passed)
- ~3,562 LOC Python under `src/mcp_test_framework/` + `tests/`
- Live green: `uv run mcp-test-framework run` → `67 passed, exit 0` against live `homelab-mcp` (via `uvx`) + Ollama `qwen3.6:latest` at `127.0.0.1:11434`
- Tested target: `homelab-mcp` / `list_keyring_credentials` (config-only switch from the original `list_registered_servers`, which surfaced a real description-quality gap the framework correctly caught)

## Long-term Vision

*Established 2026-05-07, post-v1.0 milestone, via `/gsd-explore` session.*

**The product:** First-hand validation that LLM agents can find, understand, and use your MCP tools — including with the imperfect inputs real agents produce. CI-friendly, local-first, exit-code-clean.

### Primary audience: CI engineers

CI engineers wiring this into their PR pipelines are the first-class user. **Secondary:** audit/QA teams needing history and comparable scoring across runs. **Deprioritized:** MCP server *authors* doing fast local iteration — supported, but not the design driver.

### What "first-hand validation" means

Other test frameworks measure proxies for agent-usability ("is this schema valid?", "does this function return X?"). This framework measures it directly by putting an LLM in the loop. It answers three questions an agent has to answer to succeed with a tool:

1. **Should I pick this tool right now?** — description quality / disambiguation
2. **Can I construct a valid call?** — schema clarity, parameter documentation
3. **Does the tool handle inputs real agents send — including imperfect ones?** — agent-realism / fuzz (lives inside the dynamic-rubrics milestone)

### Anti-vision (deliberately NOT building)

| Adjacent product | Why not |
|------------------|---------|
| Load tester | Different question (server throughput ≠ agent usability) |
| Generic JSON-RPC tester | MCP-specific by design — generalizing to OpenAPI/gRPC is a fork, not a feature |
| Production monitoring | Different lifecycle — we're shift-left; monitoring is shift-right |
| Security scanner | Black-box info envelope: can't tell whether a JSON value is sensitive without reading server source |
| Random adversarial fuzzer | Out of scope. *Agent-realistic-mistake* fuzz IS in scope (see #3 above) |

### Cost model: local-first, hosted opt-in via OpenAI-compatible API

The framework defaults to a **local LLM judge** on user-owned hardware (Ollama, llama.cpp, vLLM, LM Studio). **Test data never leaves the user's network** — a real value prop for security-conscious CI environments.

**OpenAI-compatible API is the unifier:** one backend implementation, configured via `base_url` + `api_key`, covers Ollama (OpenAI-compat mode), vLLM, LM Studio, LiteLLM proxy, real OpenAI, hosted Anthropic via gateway. Local → hosted is one config value. The framework deliberately does not carry per-provider SDK dependencies — the interface *is* OpenAI-compatible.

### Performance constraints

- **Wall-clock target per run:** ~5 minutes for a typical multi-tool run. Achieved via warm-up stage (amortize cold-start across the run) + process-parallel test execution.
- **Threading constraint:** `homelab-mcp` and many MCP servers are not thread-safe. Framework parallelizes at the **process level only** (`pytest-xdist` + per-worker isolated subprocess + tempdir). **Per-worker isolation (v1.1) is a hard prerequisite for parallelism (v1.2).**

### Protocol boundary

**MCP-only at the protocol-family level. All MCP transports eventually in scope.** stdio is v1.0; HTTP/SSE are future-work-not-anti-vision. Generalizing to OpenAPI/gRPC is a fork.

### Indicative milestone shape (post-v1.0)

| Milestone | Shape | Seeds activated |
|-----------|-------|-----------------|
| v1.1 | Multi-tool support + per-worker isolation + JUnit output | (none — sets prerequisite for SEED-002) |
| v1.2 | Performance + portability: xdist parallelism + warm-up stage + OpenAI-compat backend | SEED-002, SEED-005 |
| v1.3 | Dynamic rubrics (rubrics-as-data) including agent-realism input fuzz | SEED-003 |
| v1.4+ | Agentic tool-use judge — full realization of the vision | SEED-001 |
| Later | Stateful tool testing with setup/teardown | SEED-004 |

Indicative, not committed. `/gsd-new-milestone` formally scopes each milestone in turn.

## Requirements

### Validated

- ✓ `uv` + `uv.lock` + Python 3.14 clean install — v1.0 (SETUP-01)
- ✓ `pytest-asyncio` strict mode + session-scoped fixture loop — v1.0 (SETUP-02)
- ✓ Black-box rule mechanically enforced (`ruff TID251` + sys.modules guard + banned-imports test) — v1.0 (SETUP-03)
- ✓ Layered config with `CLI > env > YAML > defaults` precedence; frozen Pydantic `Config` — v1.0 (CORE-01)
- ✓ Schema validator with 7 deterministic structural checks via `Draft202012Validator` — v1.0 (CORE-02)
- ✓ Async `McpTestClient` over `stdio_client`/`ClientSession` with explicit timeouts and clean teardown (Phase 04.1 fix) — v1.0 (CORE-03)
- ✓ `OllamaJudge` with qwen3 belt-and-braces (`think:false`, `<think>` strip, brace-recovery fallback, `temperature:0`, `keep_alive:30m`) — v1.0 (CORE-04)
- ✓ All 10 spec'd tests pass deterministically (TEST-01..10) — v1.0
- ✓ Session-scoped fixtures with `AsyncExitStack` ownership, owner-task lifecycle, `_preflight` autouse gate — v1.0 (FIX-01..03)
- ✓ Typer CLI: `run`, `list-tools`, `version` — v1.0 (CLI-01..03)
- ✓ Ollama timeout/parse failures fail-soft with raw response surfaced — v1.0 (OPS-01, DOCS-03)
- ✓ Explicit `asyncio.timeout()` / `httpx.Timeout(120, connect=10)` boundaries — v1.0 (OPS-02)
- ✓ SIGINT clean teardown with exit code 130 (WR-05 fix; UAT test 8 verified live) — v1.0 (OPS-03)
- ✓ README + `docs/EXTENDING.md` + `.env.example` + `config.example.yaml` — v1.0 (DOCS-01, DOCS-02)
- ✓ Judge Protocol seam (`judge_protocol.Judge`) shipped — v1.0 (zero-cost JUDGE-01 enabler)

### Active

(None — next milestone requirements will be defined via `/gsd-new-milestone`.)

### Out of Scope

- Multiple MCP servers in one run — generalization deferred until single-server contract is proven (✓ proven in v1.0)
- Multiple tool targets in one run — same reason; framework seams should make this easy to add later
- HTTP and SSE MCP transports — stdio is sufficient to validate the contract (✓ validated)
- LLM as test input generator — explicit Phase 2 ("Plant Seed" below); judge-only for MVP
- Best-of-N judge consensus — single-shot at `score >= 4` proved adequate; revisit only if flaky in practice
- Stateful or destructive tool testing — read-only tools only
- Performance, load, or security testing — not the integration contract being validated
- JSON / JUnit output formats — pytest default terminal output is enough
- Web UI or dashboard — out of scope; CLI-only
- Pluggable judge backends (OpenAI-compatible, etc.) — Ollama-only for v1.0; `Judge` Protocol seam shipped to make swap trivial
- Reading or importing `homelab-mcp` source — black-box subprocess under test (mechanically enforced)

## Context

- **v1.0 shipped.** Solo project, local CLI; green CI = green local invocation. No GitHub Actions yet.
- **First customer + reusable framework.** `homelab-mcp` validated the contract. v2 work generalizes (multi-tool, multi-server, transports).
- **Authoritative spec preserved at** `docs/mcp_test_framework_mvp_spec.md`.
- **Black-box rule held throughout.** Framework never imports `homelab-mcp`; lint + runtime guards both ship.
- **Ollama judge dependency** lives at `127.0.0.1:11434` (homelab); `qwen3.6:latest` pulled.
- **Known follow-ups** (tracked in audit, not v1.0 blockers):
  - Upstream `homelab-mcp` `list_registered_servers` description fix (v2 territory)
  - Cross-platform automated SIGINT UAT scaffolding (v2 territory)
  - Open-source pre-flight scrub (homelab IP from README, homelab-specific captures from `.planning/`) — only triggers if/when the repo goes public

## Constraints

- **Tech stack**: Python 3.14, `uv` for dependency management — pinned in `.python-version` and `pyproject.toml`.
- **MCP transport**: stdio only via the official `mcp` SDK's `stdio_client` context manager — no raw `subprocess.Popen`.
- **Judge backend**: Ollama at `127.0.0.1:11434` with model `qwen3.6:latest`, called via `/api/chat` with `stream: false` and `format: json` for structured JSON output.
- **Async**: pytest-asyncio in strict mode with explicit `@pytest.mark.asyncio` markers. `asyncio.timeout` (3.11+) wraps any subprocess or HTTP operation that could hang.
- **Black box**: never import, read, or vendor `homelab-mcp` source — mechanically enforced via `ruff TID251` + `sys.modules` guard.
- **Pass threshold**: judge tests pass at `score >= 4` (1–5 rubric).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single MCP server, single tool for MVP | Validate the integration contract end-to-end before generalizing | ✓ Good — contract proven; v2 generalization unblocked |
| Ollama (qwen3.6:latest) as judge backend | Local, free, already running on homelab; no API key management | ✓ Good — cold-start belt-and-braces (think:false, /no_think, <think> strip, keep_alive:30m) made it reliable |
| Single-shot judge calls (no best-of-N) | Simpler MVP; revisit only if flakiness hurts signal | ✓ Good — `score >= 4` threshold + `temperature:0` proved adequate |
| stdio-only MCP transport for MVP | Sufficient to validate the contract | ✓ Good — no transport rewrite needed |
| Treat `homelab-mcp` as a black-box subprocess | Reusability requires zero coupling to a specific server | ✓ Good — mechanically enforced via ruff TID251 + sys.modules guard + banned-imports test |
| `uv` for dep management, Python 3.14 | Already scaffolded; `uv sync` is the documented install path | ✓ Good — `mcp 1.27.0` and all deps install cleanly on 3.14.3 |
| pytest-default output for MVP, no JSON/JUnit | Local CLI only — no CI dashboard yet to consume structured output | ✓ Good — terminal output sufficient |
| Config precedence `CLI > env > YAML > defaults` (overrides spec's "YAML > env" wording) | Ecosystem norm; user confirmed | ✓ Good — implemented via `pydantic-settings` `settings_customise_sources` + custom bare-name nested env source |
| `Judge` Protocol seam shipped in MVP | Zero-cost post-MVP backend-swap enabler (JUDGE-01) | ✓ Good — fixtures annotate against `Judge`, not `OllamaJudge`; swap is now a 1-file addition |
| Phase 04.1 owner-task + anyio.Event fixture rewrite | Fix `RuntimeError: Attempted to exit cancel scope in a different task` at session-scoped teardown | ✓ Good — `pytest tests/` exits 0; CLI SIGINT path inherits same lifecycle |
| Phase 5 default target switched to `list_keyring_credentials` | Framework correctly caught a real description-quality gap on `list_registered_servers`; config-only swap preserves rubric integrity | ✓ Good — proved framework signal; upstream fix tracked for v2 |
| WR-05: explicit SIGINT handler returning exit code 130 | Code review found Typer/Click swallowing the signal; observed UAT confirmed clean teardown + exit 130 | ✓ Good — supersedes the OPS-03 PARTIAL PASS override |

## Plant Seed: LLM-Generated Test Cases (Post-MVP)

After MVP green, the natural next milestone is **LLM-driven test input generation**: have the judge model read a tool's `inputSchema`, parameter descriptions, and declared output schema, and generate diverse synthetic invocations to broaden coverage beyond the hand-written `{}` call. The MVP framework seams (stateless `OllamaJudge` behind `Judge` Protocol, schema-aware `McpTestClient`, fixture-based test discovery) accommodate this without rewrites.

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
*Last updated: 2026-05-07 — v1.0 milestone close + Long-term Vision pass via `/gsd-explore`*
