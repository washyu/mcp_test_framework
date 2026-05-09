# mcp_test_framework

## What This Is

A pytest-based Python framework for testing MCP (Model Context Protocol) servers. It connects to one MCP server over stdio, discovers and exercises every tool the server advertises (modulo a configurable skip-list), runs deterministic schema/output checks per tool, and uses a local Ollama-hosted LLM as a judge for description quality. v1.0 proved the integration contract on a single tool; v1.1 generalized to N-tools-per-run with per-session host-state isolation, declarative per-tool config, and JUnit XML output for CI ingestion. The CLI (`mcp-test-framework run|list-tools|config-init|version`) drives `homelab-mcp` end-to-end against a live Ollama judge.

## Core Value

A `pytest`-runnable test suite that exercises one MCP tool end-to-end (schema → call → judge) and exits non-zero on any failure — proving the framework's integration contract before adding breadth.

## Current State

**Shipped:** v1.1 Multi-Tool + Isolation + JUnit (2026-05-08)

- 13 phases shipped (v1.0 + v1.1), 39 plans, 54/54 requirements satisfied across both milestones (29 + 25; audit-clean)
- ~5,784 LOC Python under `src/mcp_test_framework/` + `tests/`
- v1.1 generalizations: multi-tool discovery via `pytest_generate_tests`, per-session `HOME`/`USERPROFILE` redirect + null keyring backend (sha256-verified zero state mutation), `tools.<name>` config registry with `extra="forbid"` + `version: 1`, JUnit XML emit + `_reporter.py` per-tool summary plugin
- Live green: `uv run mcp-test-framework run` against live `homelab-mcp` (via `uvx`) + Ollama `qwen3.6:latest` at `127.0.0.1:11434`
- Default target tools: `list_keyring_credentials` + `suggest_deployments` (per-tool config drives the rest of homelab-mcp's surface to skip-by-default)

## Current Milestone: v1.2 Operator-First Design

**Goal:** Reshape the framework around an operator who didn't write the MCP server they're testing — make config safe by default, output legible, examples generic, and the test surface operator-vs-framework-split.

**Target features:**

- Doc & example cleanup (strip 18 planning-artifact IDs, generic `config.example.yaml`, new `examples/homelab-mcp.yaml`, self-contained `config-init` scaffold) — SEED-009
- Vibe-coded persona reframe ("black-box" as user-facing feature, not test-discipline rule) — SEED-007
- Config safety + opt-in tool selection (`tools:` as allowlist, auto-discover cwd/config.yaml, fail-loud, fix `MCPTF_CONFIG_FILE` typo silent-drop, drop `.env` + env-overlay entirely, schema `version: 2` migration) — SEED-006
- Operator vs framework test surface split (`tests/contract/` vs `tests/framework/`) — SEED-010
- Hybrid runner with domain UI (wrap `pytest.main()`, render MCP-domain UI from JUnit XML) — SEED-011
- Reporter UX overhaul (pre-run digest + `--explain` flag, scales at N=70) — SEED-008

**Pre-committed v1.3 cohort (deferred):** SEED-002 (xdist parallelism), SEED-005 (OpenAI-compat backend), warm-up stage — "performance + portability" ships separately.

**Key decisions locked at scoping:**
- Drop `.env` + env-overlay entirely. Config sources = YAML + CLI flags only. Env vars become CI-secret passthrough only (e.g., API keys), not a config source. Real-world repro 2026-05-08: explicit `--config PATH` silently overridden by `.env`.
- Bump config schema `version: 1 → 2` with loud migration error. Configs that relied on implicit-discovery (no `tools:` block → run everything) break with a clear message; `mcp-test-framework config-init` is the recovery action.
- No automated planning-artifact regression guard. Manual hygiene during v1.2 cleanup; rely on review after.
- Hybrid runner (SEED-011) decided BEFORE folder split (SEED-010) — runner contract drives the split.

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
- ✓ Per-session host-state isolation: `HOME`/`USERPROFILE` redirect to per-session tempdir, env-passthrough allowlist, `PYTHON_KEYRING_BACKEND=null` — v1.1 (ISOL-01..07)
- ✓ Multi-tool discovery + parameterized testing via `pytest_generate_tests` — v1.1 (MULTI-01..04)
- ✓ Per-tool config registry: `tools.<name>` blocks with `skip` / `call_arguments` / `judges` / forward-compat `setup:` `depends_on:` reservations — v1.1 (TOOLCFG-01..07)
- ✓ JUnit XML output (`--junit-xml=PATH`) + per-tool reporting via `_reporter.py` plugin — v1.1 (OUTPUT-01..03)
- ✓ v1.1 documentation: README sections (Per-tool config, Isolation guarantee, CI integration) + EXTENDING.md walkthroughs (add a tool target, env passthrough allowlist) — v1.1 (DOC-04..07)

### Active

(Defining for v1.2 Operator-First Design — requirements being scoped via `/gsd-new-milestone` 2026-05-08; will populate after REQUIREMENTS.md is written.)

### Out of Scope

- Multiple MCP servers in one run — generalization deferred until single-server contract is proven (✓ proven in v1.0; multi-tool-per-server proven in v1.1)
- ~~Multiple tool targets in one run~~ — **shipped in v1.1** (MULTI-01..04: discovery + parameterized testing)
- ~~JSON / JUnit output formats~~ — **shipped in v1.1** (OUTPUT-01..03)
- ~~Pluggable judge backends (OpenAI-compatible, etc.)~~ — Ollama-only for v1.0/v1.1; SEED-005 plants the OpenAI-compat backend for v1.2
- HTTP and SSE MCP transports — stdio is sufficient to validate the contract (✓ validated)
- LLM as test input generator — explicit Phase 2 ("Plant Seed" below); judge-only for MVP
- Best-of-N judge consensus — single-shot at `score >= 4` proved adequate; revisit only if flaky in practice
- Stateful or destructive tool testing — read-only tools only (SEED-004 plants this for v1.5+)
- Performance, load, or security testing — not the integration contract being validated
- Web UI or dashboard — out of scope; CLI-only
- Reading or importing `homelab-mcp` source — black-box subprocess under test (mechanically enforced via `ruff TID251` + `sys.modules` guard)

## Context

- **v1.0 + v1.1 shipped.** Solo project, local CLI; green CI = green local invocation. No GitHub Actions yet (CI snippet documented in README for downstream users).
- **First customer + reusable framework.** `homelab-mcp` validated the integration contract (v1.0) and the multi-tool surface (v1.1). v1.2+ work targets performance/portability and broader judge backends.
- **Authoritative spec preserved at** `docs/mcp_test_framework_mvp_spec.md`.
- **Black-box rule held throughout v1.0 + v1.1.** Framework never imports `homelab-mcp`; lint (`ruff TID251`) + runtime guard (`sys.modules`) + banned-imports test all ship.
- **Ollama judge dependency** lives at `127.0.0.1:11434` (homelab); `qwen3.6:latest` pulled.
- **v1.1 close state** (audit-clean, 25/25 reqs Complete) carries forward:
  - 5 dormant SEEDs (SEED-001..005) tracking deferred features for v1.2+
  - 2 docs-polish nits in EXTENDING.md (line-range citation, "five entries" framing) — see STATE.md `## Deferred Items`
- **v1.0 follow-ups still tracked** (not blockers):
  - Upstream `homelab-mcp` `list_registered_servers` description fix
  - Cross-platform automated SIGINT UAT scaffolding
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
| Phase 06 ISOL-04 SHIP (`PYTHON_KEYRING_BACKEND=null`) | homelab-mcp PyPI README v1.7.0 confirmed OS keyring is the sole credential store — gating decision triggered SHIP not DEFER | ✓ Good — empirical sha256 verification on Windows 11 dev host: 3/3 hashes byte-identical pre/post run |
| Phase 06 D-09 sha256 verification (not mtimes) | mtimes are insufficient — touch-without-content-change still updates mtime; sha256 catches genuine writes | ✓ Good — strengthening kept ROADMAP/code in sync after Phase 11 W-5 fix |
| WR-04 Branch B: `USERNAME` only in `_PASSTHROUGH_ALLOWLIST` (POSIX `USER` excluded) | v1.1's tool surface needs Windows-only auth context; adding POSIX `USER` would broaden the allowlist without a justifying use case. Documented as Branch B in EXTENDING.md | ✓ Good — keeps allowlist minimal; reversible if a v1.2 tool needs POSIX `USER` |
| Phase 07 — `pytest_generate_tests` + indirect parametrize over discovered tools (no codegen) | Live discovery from server keeps test list always-accurate; indirect parametrize fits pytest-asyncio's strict-mode fixture model | ✓ Good — `<test>[<tool>]` IDs flow naturally to terminal + JUnit |
| Phase 08 — `extra="forbid"` + `version: 1` on `tools.<name>` config blocks | Typos must surface as Pydantic errors at config load, not silent test omissions | ✓ Good — forward-compat `setup:`/`depends_on:` reservations don't break the strict shape |
| Phase 09 — `_reporter.py` as a pytest plugin (not CLI post-processor) | Plugin model uses live `terminalreporter` events; post-processor would re-parse pytest output. Plugin keeps the contract testable in-process | ✓ Good — 29 unit tests + 3 live tests pin OUTPUT-01..03 |
| Phase 11 — gap-closure phase as last v1.1 phase | Milestone audit (W-1, W-3, W-4, W-5, W-6) surfaced paper-only drift before archive — closing in-milestone keeps audit-clean state | ✓ Good — 25/25 requirements Complete at archive |

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
*Last updated: 2026-05-08 — v1.2 Operator-First Design scoping started via `/gsd-new-milestone`; six cohorts (SEED-006..009 + new SEED-010/011) frame the milestone. v1.1 milestone close summary preserved above (54/54 requirements satisfied across v1.0+v1.1).*
