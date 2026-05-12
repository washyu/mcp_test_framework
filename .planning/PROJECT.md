# mcp_test_framework

## What This Is

A pytest-based Python framework for testing MCP (Model Context Protocol) servers. It connects to one MCP server over stdio, discovers and exercises every tool the server advertises (modulo a configurable skip-list), runs deterministic schema/output checks per tool, and uses a local Ollama-hosted LLM as a judge for description quality. v1.0 proved the integration contract on a single tool; v1.1 generalized to N-tools-per-run with per-session host-state isolation, declarative per-tool config, and JUnit XML output for CI ingestion. The CLI (`mcp-test-framework run|list-tools|config-init|version`) drives `homelab-mcp` end-to-end against a live Ollama judge.

## Core Value

A `pytest`-runnable test suite that exercises one MCP tool end-to-end (schema → call → judge) and exits non-zero on any failure — proving the framework's integration contract before adding breadth.

## Current State

**Shipped:** v1.2 Operator-First Design (2026-05-12)

- 18 phases shipped (v1.0 + v1.1 + v1.2), 69 plans, 85/85 requirements satisfied across all three milestones (29 + 25 + 31)
- v1.2 carry-forward debt: live-stack UAT pair (Phases 13 & 14 — needs `homelab-mcp` on PATH), Phase 16 D-11 `--debug` per-judge breakdown deferred to v1.3
- ~7,700+ LOC Python (post-v1.2 — +37,100 / −1,928 across 168 files in v1.2 alone, including doc churn and test additions)
- v1.2 generalizations: operator-domain UI replaces pytest framing; `tools:` is an opt-in allowlist; config schema bumped to `version: 2`; `tests/contract/` vs `tests/framework/` split; `--raw` escape hatch preserves the pytest framing for maintainers
- Live green: `uv run mcp-test-framework run` against live `homelab-mcp` (via `uvx`) + Ollama at `127.0.0.1:11434`
- Default operator path: `mcp-test-framework config-init -o config.yaml` → edit allowlist → `mcp-test-framework run` (pre-run digest → opt-in tools execute → post-run domain UI)

## Current Milestone: Planning v1.3

No phases scoped yet. `/gsd-new-milestone` will frame v1.3 scope.

**Strong v1.3 candidates carried forward:**

- **D-11 — `--debug` per-judge breakdown block.** Phase 16 deferred this rung intentionally; surfaces per-judge raw responses inside the `--debug` ladder.
- **SEED-002 — Tool-level parallelism via `pytest-xdist`** with read/write resource markers.
- **SEED-005 — OpenAI-compat judge backend** (pluggable judge plumbing).
- **SEED-001 — Replace rubric-style judge with agent tool-use loop**.
- 15 plant-seed items total — see `.planning/seeds/` and Deferred section below.

**Pre-committed cohort theme:** "performance + portability" — xdist parallelism, alternative judge backends, warm-up stage. Awaits scoping pass.

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
- ✓ Doc & persona foundation: planning-artifact IDs stripped, `config.example.yaml` split (placeholder template + `examples/homelab-mcp.yaml` worked reference), `config-init` scaffold complete, "Testing an MCP server you didn't write" persona — v1.2 (CLEAN-01..06, PERSONA-01..03)
- ✓ Config safety + opt-in tool selection: `tools:` allowlist, `--config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud` precedence, schema `version: 1 → 2` migration with LOCKED error message, `.env` + env-overlay dropped — v1.2 (SAFE-01..07, TOOLCFG-06 None/[]/subset semantics)
- ✓ Hybrid runner with domain UI: `cli.py:run` wraps pytest subprocess, internal JUnit XML capture, MCP-domain UI in `_runner.py`, `-q` / default / `--explain` / `--debug` verbosity ladder, `--raw` maintainer escape hatch — v1.2 (RUNNER-01..06)
- ✓ Operator vs framework test surface split: `tests/contract/` (operator) + `tests/framework/` (self-tests); runner default scope `tests/contract/`; banned-imports under `tests/framework/` — v1.2 (SURFACE-01..04)
- ✓ Reporter UX overhaul: 8-line pre-run digest replaces pytest "N collected M deselected" framing; `--explain` grep-able skip rationale at N=70; post-run per-tool aggregation with per-judge reasoning on FAIL rows; D-12 height-bounded digest — v1.2 (UX-01..05)

### Active

(Defining for v1.3 — requirements scoped via `/gsd-new-milestone` after v1.2 close 2026-05-12.)

### Out of Scope

- Multiple MCP servers in one run — generalization deferred until single-server contract is proven (✓ proven in v1.0; multi-tool-per-server proven in v1.1)
- ~~Multiple tool targets in one run~~ — **shipped in v1.1** (MULTI-01..04: discovery + parameterized testing)
- ~~JSON / JUnit output formats~~ — **shipped in v1.1** (OUTPUT-01..03)
- ~~Pluggable judge backends (OpenAI-compatible, etc.)~~ — Ollama-only for v1.0/v1.1/v1.2; SEED-005 carries to v1.3 cohort
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
| Phase 12 — merged CLEAN + PERSONA into one phase | Both doc-heavy and small; separate phases would have been overhead for near-trivial work. Foundational hygiene lands first so downstream phases operate on clean docs | ✓ Good — 9 plans / 6 must-haves delivered; downstream phases never had to scrub artifact IDs |
| Phase 13 — drop `.env` + env-overlay entirely | Real-world repro 2026-05-08: explicit `--config PATH` silently overridden by `.env`. Env-overlay was a footgun, not an ergonomic | ✓ Good — destructive-default class of bugs eliminated; debug session `dotenv-example-invisible` becomes moot |
| Phase 13 — schema `version: 1 → 2` with LOCKED migration error | Inverting `tools:` to allowlist is a breaking change; loud error citing `config-init` is the correct migration UX | ✓ Good — fresh operators get the right scaffold; existing operators get an actionable path |
| Phase 14 before Phase 15 (RUNNER before SURFACE split) | Runner contract drives what the folder split needs to support; reversing would have made the split speculative | ✓ Good — `tests/contract/` scope baked into `_build_pytest_args` defaults cleanly |
| Phase 14 — hybrid runner via subprocess (not `pytest.main()`) | Subprocess isolation lets the wrapper capture JUnit XML via tempfile without coupling to pytest's in-process state; `--raw` escape hatch trivially bypasses | ✓ Good — operator path and maintainer path share the same config gate, diverge only on output rendering |
| Phase 16 — D-13 verbosity ladder invariant ("each rung adds, none reshapes") | Composing `-q --debug` is allowed and renders "summary, then appendix"; prevents flag-pair combinatoric ambiguity | ✓ Good — orthogonal flags pass unit tests across all 4 combinations |
| Phase 16 — D-11 per-judge breakdown deferred to v1.3 | Plan 16-01 found D-11 had no clear UI shape yet; deferring kept Phase 16 ship-shape without churning the unproven debug surface | — Pending — carries into v1.3 cohort |
| Phase 16 — plan 16-05 inline gap closure (digest judges union) | Live UAT exposed `judges: (none configured)` lying about runtime behavior; TOOLCFG-06 None default must expand to RUBRIC_IDS at the digest layer | ✓ Good — 25 LOC fix + 3 regression tests; restored truth between digest and runtime |
| v1.2 close — CLEAN-03 closed via `/gsd-quick` (not gap-closure phase) | 3-line patch (example configs to v2). Audit had documented it; a full phase for mechanical work would have been overhead | ✓ Good — audit→quick-fix loop demonstrates the milestone-audit value (caught what per-phase verification missed) |

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
*Last updated: 2026-05-12 — v1.2 Operator-First Design milestone complete. All 5 phases (12–16) shipped, all 31 requirements satisfied (1 cross-phase BLOCKER caught by milestone audit and closed via quick task 260512-dcs). Carry-forward debt: live-stack UAT pair in Phases 13 & 14 (needs `homelab-mcp` on PATH); Phase 16 D-11 deferred to v1.3 per CONTEXT decision. Next: `/gsd-new-milestone` to scope v1.3 (performance + portability cohort).*
