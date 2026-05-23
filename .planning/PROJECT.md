# mcp_test_framework

## What This Is

A pytest-based Python framework for testing MCP (Model Context Protocol) servers. It connects to one MCP server over stdio, discovers and exercises every tool the server advertises (modulo a configurable allowlist), runs deterministic schema/output checks per tool, and uses a local Ollama-hosted LLM as a judge for description quality. v1.3 added the **SDET persona** as a second first-class user — alongside the operator's auto-graded contract pass, an SDET can author intentional stateful scenarios (`create → modify → delete` with cleanup-on-failure) against the same MCP server, with typed Pydantic params/response classes generated from the server's live `inputSchema`/`outputSchema`. The CLI (`mcp-test-framework run|run --sdet|list-tools|gen-sdet-classes|config-init|version`) drives `homelab-mcp` end-to-end against a live Ollama judge.

## Core Value

A `pytest`-runnable test suite that exercises every MCP tool end-to-end (schema → call → judge) for the operator persona AND lets an SDET author typed scenario tests against the same MCP server for stateful coverage — exits non-zero on any failure, no `homelab-mcp`-specific code in the framework's `src/` tree (SEED-022).

## Current Milestone: Planning v1.5

v1.4 Library Mode Delivery shipped 2026-05-22. v1.5 not yet scoped — run `/gsd-new-milestone` to begin questioning → research → requirements → roadmap.

**Carry-forward debt expected to fold into v1.5 scoping:**
- Drop v1.4-introduced deprecation shims (sdet package shim, `--sdet` / `gen-sdet-classes` CLI shims, `cfg.sdet.*` alias, `MCPTF_CONFIG_FILE` env-var route, unprefixed fixture aliases, `mcp-test-framework` console-script alias).
- Promote backlog 999.1 (per-bucket skip), 999.2 (codegen-driven parameter tests), 999.3 (opt-in host isolation), 999.4 (drop v1-schema support), 999.5 (framework self-test env pollution) as scope allows.
- Phase 16 D-11 `--debug` per-judge breakdown block still dormant (cohort with SEED-003 dynamic rubrics).
- xdist parallelism (SEED-002), OpenAI-compat judge backend (SEED-005), URL-style judge kwarg sugar — all deferred at v1.4 scoping with the rationale that they land cleaner on a now-stable library-mode API.

## Current State

**Shipped:** v1.4 Library Mode Delivery (2026-05-22)

- 33 phases shipped (v1.0 + v1.1 + v1.2 + v1.3 + v1.4), 138 plans across five milestones, 142/144 requirements satisfied (29 + 25 + 31 + 29 + 28; LIB-05 + CFG-02 removed-by-decision at Phase 27 D-01)
- v1.4 delivered: framework is now an importable pytest plugin shipped as `mcp-contracts`. Operator adds the wheel to `pyproject.toml`, sets one line in `[tool.pytest.ini_options] mcp_config_file = "./config.yaml"`, and parametrized contract tests appear in their own `pytest` collection. Public API surface renamed (`sdet` → `test_code`) and locked. PyPI dist name corrected (`mvp-test-framework` → `mcp-contracts`); py.typed markers ship; wheel-introspection CI gate live. Domain UI available behind opt-in `--mcp-domain-ui` reporter plugin driven by live `pytest_runtest_logreport` events. Codegen output path is operator-owned (no smart default; pre-handshake site-packages guard). CLI demoted to README appendix; `docs/LIBRARY-MODE.md` is the primary reference. Framework dogfoods library mode via its own `pyproject.toml`.
- v1.4 carry-forward UATs closed during the dogfood pass: README test-code-scenarios PASS-sample verified post-Phase-24 (UAT-1), Phase 17 SC1 confirmed at 58 enabled tools with pyright clean (UAT-2), Phase 14 CLI/library parity verified at 7-identical-contract-failure resolution (UAT-4). UAT-3 (v1→v2 migration walkthrough) retired-by-deletion (closed via backlog 999.4).
- ~53,000+ LOC Python overall (v1.4 alone added +34,284 / −2,120 across 181 files — dominated by `src/mcp_test_framework/_plugin.py` + `_reporter.py` + `contracts/` sub-package + tests + docs rewrite)
- v1.4 generalizations: load-bearing technical bet (`_ContractsModule(_PytestModule)` virtual-module synthesis injecting `<mcp-contracts>::test_<name>[<tool>]` nodeids) shipped without an architecture rewrite. Pytest-asyncio strict-mode loop wiring intact under plugin auto-discovery. Single config-resolution route (`mcp_config_file` ini key) across CLI and library modes; one render path via in-subprocess reporter.
- Live green: `uv run mcp-contracts run --config config.yaml` and `uv run pytest -o "mcp_config_file=config.yaml"` produce equivalent JUnit XML against live `homelab-mcp` (via `uvx`) + Ollama at `127.0.0.1:11434`; framework self-tests green at 670 passed / 3 skipped / 1 xfailed / 0 failed / 0 errored.

## Long-term Vision

*Established 2026-05-07, post-v1.0 milestone, via `/gsd-explore` session.*

**The product:** First-hand validation that LLM agents can find, understand, and use your MCP tools — including with the imperfect inputs real agents produce. CI-friendly, local-first, exit-code-clean.

### Primary audience: CI engineers + SDETs

CI engineers wiring this into their PR pipelines are the first-class user; SDETs writing intentional stateful scenarios against MCP servers are the second-class user (added in v1.3). **Secondary:** audit/QA teams needing history and comparable scoring across runs. **Deprioritized:** MCP server *authors* doing fast local iteration — supported, but not the design driver.

### What "first-hand validation" means

Other test frameworks measure proxies for agent-usability ("is this schema valid?", "does this function return X?"). This framework measures it directly by putting an LLM in the loop. It answers three questions an agent has to answer to succeed with a tool:

1. **Should I pick this tool right now?** — description quality / disambiguation
2. **Can I construct a valid call?** — schema clarity, parameter documentation
3. **Does the tool handle inputs real agents send — including imperfect ones?** — agent-realism / fuzz (lives inside the dynamic-rubrics milestone)

**v1.3 added a fourth dimension for stateful tools:** Can a human SDET author a `create → modify → delete` scenario against the same MCP server, with typed params/response classes, and have teardown reliably execute even when an intervening assertion fails?

### Anti-vision (deliberately NOT building)

| Adjacent product | Why not |
|------------------|---------|
| Load tester | Different question (server throughput ≠ agent usability) |
| Generic JSON-RPC tester | MCP-specific by design — generalizing to OpenAPI/gRPC is a fork, not a feature |
| Production monitoring | Different lifecycle — we're shift-left; monitoring is shift-right |
| Security scanner | Black-box info envelope: can't tell whether a JSON value is sensitive without reading server source |
| Random adversarial fuzzer | Out of scope. *Agent-realistic-mistake* fuzz IS in scope (see #3 above) |
| SUT-aware framework features | The framework is a **generic MCP test framework** — `homelab-mcp` is the dogfood SUT, not a feature target. Framework `src/` and shipped `tests/` stay SUT-agnostic; no homelab-, Proxmox-, Ansible-, or other SUT-specific code/tests/decorators (e.g. `requires_homelab(proxmox=...)`) ever land in the framework itself. SUT-specific reachability, fixtures, and scenarios live in the SDET's own test code via stock pytest primitives (`@pytest.mark.skipif`, conftest helpers). When future milestones surface "the framework should know about &lt;subsystem X&gt;," that's the violation — re-scope to a generic primitive or push into the SDET-side recipe. *Locked Phase 20 (v1.3) after PREFLIGHT-01/02 reframe; structurally enforced Phase 21.1 by deleting `src/mcp_test_framework/sdet/generated/`.* |

### Cost model: local-first, hosted opt-in via OpenAI-compatible API

The framework defaults to a **local LLM judge** on user-owned hardware (Ollama, llama.cpp, vLLM, LM Studio). **Test data never leaves the user's network** — a real value prop for security-conscious CI environments.

**OpenAI-compatible API is the unifier:** one backend implementation, configured via `base_url` + `api_key`, covers Ollama (OpenAI-compat mode), vLLM, LM Studio, LiteLLM proxy, real OpenAI, hosted Anthropic via gateway. Local → hosted is one config value. The framework deliberately does not carry per-provider SDK dependencies — the interface *is* OpenAI-compatible.

### Performance constraints

- **Wall-clock target per run:** ~5 minutes for a typical multi-tool run. Achieved via warm-up stage (amortize cold-start across the run) + process-parallel test execution.
- **Threading constraint:** `homelab-mcp` and many MCP servers are not thread-safe. Framework parallelizes at the **process level only** (`pytest-xdist` + per-worker isolated subprocess + tempdir). **Per-worker isolation (v1.1) is a hard prerequisite for parallelism (v1.4).**

### Protocol boundary

**MCP-only at the protocol-family level. All MCP transports eventually in scope.** stdio is v1.0; HTTP/SSE are future-work-not-anti-vision. Generalizing to OpenAPI/gRPC is a fork.

### Indicative milestone shape (post-v1.3)

| Milestone | Shape | Seeds activated |
|-----------|-------|-----------------|
| v1.4 | Performance + portability: pytest-xdist parallelism + library-mode delivery (pytest plugin) + OpenAI-compat judge backend | SEED-002, SEED-005, SEED-015 |
| v1.5 | Dynamic rubrics (rubrics-as-data) including agent-realism input fuzz + per-judge `--debug` breakdown | SEED-003, Phase 16 D-11 |
| v2.0 | Agentic tool-use judge — full realization of the vision | SEED-001 |

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
- ✓ v1.1 documentation: README sections (Per-tool config, Isolation guarantee, CI integration) + EXTENDING.md walkthroughs — v1.1 (DOC-04..07)
- ✓ Doc & persona foundation: planning-artifact IDs stripped, `config.example.yaml` split, `config-init` scaffold complete, "Testing an MCP server you didn't write" persona — v1.2 (CLEAN-01..06, PERSONA-01..03)
- ✓ Config safety + opt-in tool selection: `tools:` allowlist, `--config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud` precedence, schema `version: 1 → 2` migration, `.env` + env-overlay dropped — v1.2 (SAFE-01..07)
- ✓ Hybrid runner with domain UI: `cli.py:run` wraps pytest subprocess, internal JUnit XML capture, MCP-domain UI in `_runner.py`, verbosity ladder, `--raw` escape hatch — v1.2 (RUNNER-01..06)
- ✓ Operator vs framework test surface split: `tests/contract/` + `tests/framework/`; runner default scope `tests/contract/` — v1.2 (SURFACE-01..04)
- ✓ Reporter UX overhaul: 8-line pre-run digest, `--explain` skip rationale, post-run per-tool aggregation, D-12 height-bounded digest — v1.2 (UX-01..05)
- ✓ SDET test surface — `tests/sdet/` discovery, `mcp_session` + `tool("name")` fixtures, `--sdet` CLI flag, pytest-asyncio strict mode — v1.3 (SDET-01..04)
- ✓ Schema-driven codegen — `gen-sdet-classes` command, `<Tool>Params` Pydantic from `inputSchema`, `<Tool>Response` typed-when-declared/stub-when-not, `ToolResponse` base with uniform `.raw`/`.data`/`.text`/`.is_error`, typed call wrapper, "do not hand-edit" header — v1.3 (CODEGEN-01..06)
- ✓ Stateful primitives — yield-fixture cleanup contract dogfooded in `test_state_cleanup_on_failure.py`, module-scope state passing via typed `ProxmoxVmLifecycleState`, pytest-order recipe — v1.3 (STATE-01..04)
- ✓ v1.3 scope correction — SUT-specific dogfood deleted from `tests/sdet/` (SEED-022), mock-fixture codegen unit tests added under `tests/framework/unit/`, PREFLIGHT-01/02 dropped — v1.3 (CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01)
- ✓ SDET generated output relocation — `cfg.sdet.generated_root` required field, `gen-sdet-classes` + `mcp_session` config-driven via `spec_from_file_location`, `src/mcp_test_framework/sdet/generated/` deleted — v1.3 (RELOC-01..04)
- ✓ Domain UI integration — `_render_per_tool_rows` scenario rows (parent group header + indented per-test rows), `ToolCallError` typed exception with `.tool`/`.code`/`.message`/`.raw` + em-dash FAIL surfacing + `--debug` appendix dump — v1.3 (UI-01..02)
- ✓ SDET authoring docs — `docs/SDET-AUTHORING.md` walkthrough (worked example, fixture patterns, codegen regen, ordering, skip recipe), CLAUDE.md dual-persona note, README §SDET scenarios with char-for-char renderer parity (operator-approved FAIL-polarity override per Phase 21) — v1.3 (DOC-SDET-01..03)
- ✓ Planning-ID scrub — operator-facing `--help` and entire `src/mcp_test_framework/` tree show zero matches for the locked planning-ID regex; regression test pinned at `test_no_planning_ids_in_src.py` — v1.3 (SCRUB-SRC-01)
- ✓ Tool-call wire serializer — `tool().call()` uses `model_dump(mode="json", exclude_unset=True)`; SDET-omitted optionals stay off the wire; explicit `field=None` still flows null (SEED-022 user-intent discriminator); 3 payload-asserting unit tests + renamed kwargs-spy test lock all three behaviors — v1.3 (SERIALIZER-01)
- ✓ SERIALIZER-DOC-01 partial — `docs/SDET-AUTHORING.md` §inputSchema-workaround softened (workaround now framed as explicit null-test escape hatch only); README §SDET-scenarios PASS-sample re-capture deferred to manual live-UAT (operator-approved regen-failed contract per Plan 24-02; tracked in STATE.md L184 `live-uat` row) — v1.3 (SERIALIZER-DOC-01)

### Active

Scoped for v1.4 — see "Current Milestone" above. Carry-forward debt to fold in:

- [ ] README §SDET-scenarios PASS-sample re-capture (live-UAT with Proxmox keyring access — partial SERIALIZER-DOC-01)
- [ ] Phase 17 SC1 live-stack confirmation at ~70-tool scale (`gen-sdet-classes` against live homelab-mcp + `uv run pyright` on real generated dir)
- [ ] v1.2 carry-forward live-stack UATs: Phase 13 (v2 config + migration walkthrough), Phase 14 (`test_runner_live_smoke.py` + visual domain UI checks)
- [ ] 20 dormant seeds in backlog parking lot — re-triage (SEED-001/002/003/005/006/012/013/015/016/017/018/021/023 etc.; SEED-010 absorbed Phase 15, SEED-011 absorbed Phase 14)

### Out of Scope

- Multiple MCP servers in one run — generalization deferred until single-server contract is proven (✓ proven through v1.3)
- ~~Multiple tool targets in one run~~ — **shipped in v1.1**
- ~~JSON / JUnit output formats~~ — **shipped in v1.1**
- ~~Pluggable judge backends (OpenAI-compatible, etc.)~~ — Ollama-only through v1.3; SEED-005 carries to v1.4
- ~~Stateful or destructive tool testing~~ — **shipped in v1.3** (STATE-01..04; yield-fixture cleanup contract + module-scope state passing)
- ~~Programmatic SDET test authoring~~ — **shipped in v1.3** (CODEGEN-01..06 + SDET-01..04)
- HTTP and SSE MCP transports — stdio is sufficient to validate the contract (✓ validated)
- LLM as test input generator — Plant Seed (Phase 2); judge-only through v1.3; SEED-003 carries to v1.5
- Best-of-N judge consensus — single-shot at `score >= 4` proved adequate; revisit only if flaky in practice
- Performance, load, or security testing — not the integration contract being validated
- Web UI or dashboard — out of scope; CLI-only
- Reading or importing `homelab-mcp` source — black-box subprocess under test (mechanically enforced via `ruff TID251` + `sys.modules` guard)
- SUT-aware framework features (preflight markers, subsystem awareness) — SEED-022; locked Phase 20, structurally enforced Phase 21.1
- CLI `--out` override and `MCPTF_GENERATED_ROOT` env var for `sdet.generated_root` — explicitly rejected Phase 21.1 D-02 (one source of truth)
- ~~SEED-023 SDET→test-code rename~~ — **scoped into v1.4** alongside library-mode public API

## Context

- **v1.0, v1.1, v1.2, v1.3 shipped.** Solo project, local CLI; green CI = green local invocation. No GitHub Actions yet (CI snippet documented in README for downstream users).
- **First customer + reusable framework + dual personas.** `homelab-mcp` validated the integration contract (v1.0), the multi-tool surface (v1.1), the operator UX (v1.2), and now the SDET surface (v1.3). v1.4+ work targets performance/portability (xdist + library mode) and broader judge backends.
- **Authoritative spec preserved at** `docs/mcp_test_framework_mvp_spec.md`.
- **Black-box rule held throughout v1.0–v1.3.** Framework never imports `homelab-mcp`; lint (`ruff TID251`) + runtime guard (`sys.modules`) + banned-imports test all ship.
- **SEED-022 (framework primitives only; SDET owns safety) structurally enforced.** `src/mcp_test_framework/sdet/generated/` deleted in Phase 21.1; codegen output is operator-controlled via `cfg.sdet.generated_root`; planning-ID leaks scrubbed from operator-facing `--help` and entire `src/` tree (Phase 22).
- **Ollama judge dependency** lives at `127.0.0.1:11434` (homelab); `qwen3.6:latest` pulled.
- **v1.3 close state** (29 reqs; 27 satisfied, 2 partial-by-design with operator-approved live-UAT) carries forward:
  - README §SDET-scenarios PASS-sample re-capture (manual live-UAT in operator shell with Proxmox keyring access)
  - Phase 17 SC1 confirmation at ~70-tool scale
  - 20 dormant seeds + 3 pre-existing v1.2 verification gaps (Phases 13, 14, 17 `human_needed`)

## Constraints

- **Tech stack**: Python 3.14, `uv` for dependency management — pinned in `.python-version` and `pyproject.toml`.
- **MCP transport**: stdio only via the official `mcp` SDK's `stdio_client` context manager — no raw `subprocess.Popen`.
- **Judge backend**: Ollama at `127.0.0.1:11434` with model `qwen3.6:latest`, called via `/api/chat` with `stream: false` and `format: json` for structured JSON output.
- **Async**: pytest-asyncio in strict mode with explicit `@pytest.mark.asyncio` markers. `asyncio.timeout` (3.11+) wraps any subprocess or HTTP operation that could hang.
- **Black box**: never import, read, or vendor `homelab-mcp` source — mechanically enforced via `ruff TID251` + `sys.modules` guard.
- **SEED-022 framework primitives**: `src/mcp_test_framework/` contains zero SUT-specific code; SDET owns reachability, fixtures, and scenarios via stock pytest primitives. Structurally enforced by deletion of `src/.../sdet/generated/` (Phase 21.1).
- **Pass threshold**: judge tests pass at `score >= 4` (1–5 rubric).
- **SDET tool-call serializer**: `model_dump(mode="json", exclude_unset=True)` — SDET-omitted optionals stay off the wire; explicit `field=None` still flows null (Phase 24 SERIALIZER-01).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single MCP server, single tool for MVP | Validate the integration contract end-to-end before generalizing | ✓ Good — contract proven; v2 generalization unblocked |
| Ollama (qwen3.6:latest) as judge backend | Local, free, already running on homelab; no API key management | ✓ Good — cold-start belt-and-braces (think:false, /no_think, <think> strip, keep_alive:30m) made it reliable |
| Single-shot judge calls (no best-of-N) | Simpler MVP; revisit only if flakiness hurts signal | ✓ Good — `score >= 4` threshold + `temperature:0` proved adequate |
| stdio-only MCP transport for MVP | Sufficient to validate the contract | ✓ Good — no transport rewrite needed |
| Treat `homelab-mcp` as a black-box subprocess | Reusability requires zero coupling to a specific server | ✓ Good — mechanically enforced via ruff TID251 + sys.modules guard + banned-imports test |
| `uv` for dep management, Python 3.14 | Already scaffolded; `uv sync` is the documented install path | ✓ Good — `mcp 1.27.0` and all deps install cleanly on 3.14.3 |
| Config precedence `CLI > env > YAML > defaults` | Ecosystem norm; user confirmed | ✓ Good — `.env` + env-overlay dropped in v1.2 after destructive-default repro |
| `Judge` Protocol seam shipped in MVP | Zero-cost post-MVP backend-swap enabler | ✓ Good — JUDGE-01 deferred but seam ready |
| Phase 13 — drop `.env` + env-overlay entirely | Real-world repro 2026-05-08: explicit `--config PATH` silently overridden by `.env` | ✓ Good — destructive-default class of bugs eliminated |
| Phase 13 — schema `version: 1 → 2` with LOCKED migration error | Inverting `tools:` to allowlist is a breaking change | ✓ Good — fresh operators get the right scaffold; existing operators get an actionable path |
| Phase 14 before Phase 15 (RUNNER before SURFACE split) | Runner contract drives what the folder split needs to support | ✓ Good — `tests/contract/` scope baked into `_build_pytest_args` defaults cleanly |
| Phase 14 — hybrid runner via subprocess (not `pytest.main()`) | Subprocess isolation lets the wrapper capture JUnit XML via tempfile; `--raw` trivially bypasses | ✓ Good — operator and maintainer paths share the same config gate |
| Phase 16 — D-11 per-judge breakdown deferred to v1.5 cohort with SEED-003 | Plan 16-01 found D-11 had no clear UI shape yet | — Pending — carries to v1.5 |
| v1.3 — pull SEED-014 + SEED-004 forward from v2.0 | v1.2 closed clean; SDET persona is additive, not disruptive; manual-Claude-client testing is the real bottleneck | ✓ Good — SDET surface shipped clean; 9 phases / 42 plans / 29 reqs delivered in 3 days |
| Phase 17 — codegen as first v1.3 phase | Every downstream phase imports from generated `<ToolName>Params`/`<ToolName>Response`; without codegen the SDET surface is stringly-typed | ✓ Good — Phase 18 wire body wraps the seam cleanly; CODEGEN-04 base unified declared/undeclared response paths |
| Phase 18 — bundle `ToolCallError` with the call wrapper | `ToolCallError` is raised by `.call()` and consumed by both contract and SDET paths — keeping it with the wrapper avoids a v1.3.1 retrofit | ✓ Good — D-09 JUnit user_properties hook + D-11 debug appendix close the typed-error story end-to-end |
| Phase 19 → Phase 20 reframe — delete SUT-specific dogfood (SEED-022) | PREFLIGHT-01/02 `requires_homelab(...)` baked SUT subsystem knowledge into framework API; live VM-lifecycle run revealed scope drift | ✓ Good — D-02 Resolved-by-deletion; mock-fixture codegen tests replace the killed coverage; CI no longer depends on operator infrastructure |
| Phase 21 — operator-approved FAIL-sample README override | Live Proxmox run hit upstream homelab-mcp `inputSchema` bug on `create_proxmox_vm` (not just `manage_proxmox_vm`); operator chose option (a) at checkpoint to embed FAIL output verbatim | ✓ Good — char-for-char doc-mirroring contract preserved; SEED-022 teaching strengthened (framework surfaces upstream contract bugs as real test failures, doesn't mask them) |
| Phase 21.1 — INSERTED mid-flight; `cfg.sdet.generated_root` required, no env override | One source of truth (D-02); structural enforcement of SEED-022 by deleting `src/.../sdet/generated/` | ✓ Good — 58 SUT-specific files removed from framework `src/` tree; SAFE-03 fail-loud on missing config |
| Phase 22 — D-04 zero-allowlist scrub (no `# noqa: SCRUB-SRC-01`) | Planning IDs are removed, not suppressed | ✓ Good — phase-wide regex sweep returns 0 hits; regression test pins the contract |
| Phase 23 — INSERTED to green-up `tests/framework/` pre-Phase-24 | `tests/framework/` accumulated 12 fails + 1 error from v1.2 folder split + v2 schema migration; Phase 24's serializer change needs an isolated ripple | ✓ Good — 575 passed close-gate; D-02 invariant (zero `src/` changes) held |
| Phase 24 — `exclude_unset=True` (not `exclude_none=True`) | SEED-022 user-intent discriminator: distinguish SDET-omitted (unset) from SDET-explicitly-null (set); `exclude_none` would mask upstream null-handling bugs | ✓ Good — 3 payload-asserting tests lock all three behaviors; SDET who tests null-handling explicitly still triggers the upstream bug |
| Phase 24 — Plan 24-02 regen-failed contract for README live-UAT | Proxmox keyring unreachable from agent subprocess; explicit partial-completion contract over silent skip | ✓ Good — README untouched at HEAD; STATE.md `live-uat` row tracks the manual UAT; pattern reusable for future live-stack-dependent doc captures |

## Plant Seed: LLM-Generated Test Cases (Post-MVP)

After v1.3, the natural next milestone for "agent in the loop" depth is **LLM-driven test input generation**: have the judge model read a tool's `inputSchema`, parameter descriptions, and declared output schema, and generate diverse synthetic invocations to broaden coverage beyond the hand-written `{}` call. The v1.3 SDET surface (typed Params/Response classes, `tool().call()` wrapper, `ToolCallError`) gives this a clean seam — the synthetic invocations become `<Tool>Params(...)` constructions driven by the judge. v1.5 (dynamic rubrics + SEED-003) is the planned home.

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
*Last updated: 2026-05-22 — v1.4 Library Mode Delivery shipped. Primary surface is pytest-native: operator sets `[tool.pytest.ini_options] mcp_config_file = PATH` in `pyproject.toml` and the `mcp-contracts` plugin injects parametrized contract tests into their own `pytest` collection (no `register()` API — dropped at Phase 27 D-01 in favor of the ini route). Public API surface renamed (sdet → test_code) and locked. CLI demoted to appendix; `docs/LIBRARY-MODE.md` is the primary reference. v1.5 not yet scoped; carry-forward debt = drop v1.4 deprecation shims + promote backlog 999.1/.2/.3/.4/.5.*
