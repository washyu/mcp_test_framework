# Requirements — mcp_test_framework v1.2

**Milestone:** v1.2 — Operator-First Design
**Goal:** Reshape the framework around an operator who didn't write the MCP server they're testing — make config safe by default, output legible, examples generic, and the test surface operator-vs-framework-split.

REQ-IDs continue numbering from v1.1 (archived at `.planning/milestones/v1.1-REQUIREMENTS.md`). New v1.2 categories prefixed `CLEAN-`, `PERSONA-`, `SAFE-`, `RUNNER-`, `SURFACE-`, `UX-`.

**Sources:** SEED-006 (config safety + opt-in), SEED-007 (vibe-coded persona reframe), SEED-008 (reporter UX overhaul), SEED-009 (doc & example cleanup), SEED-010 (operator vs framework test surface split, formalized 2026-05-08), SEED-011 (hybrid runner with domain UI, formalized 2026-05-08).

**Decisions locked at scoping (2026-05-08):**
- Drop `.env` and env-overlay entirely. Config sources = YAML + CLI flags. Env vars = CI-secret passthrough only.
- Bump config schema `version: 1 → 2` with loud migration error.
- No automated planning-artifact regression guard — manual hygiene only.
- Hybrid runner (SEED-011) decided BEFORE folder split (SEED-010) — runner contract drives split.

**Counts:** 31 requirements across 6 categories — CLEAN (6), PERSONA (3), SAFE (7), RUNNER (6), SURFACE (4), UX (5).

---

## v1.2 Requirements

### CLEAN — Doc & example cleanup (foundational hygiene)

- [ ] **CLEAN-01**: Strip planning-artifact IDs (`Phase \d`, `Plan \d`, `TOOLCFG-`, `D-\w`, `CD-\w`, `ISOL-\w`, `OUTPUT-\w`, `\d{6}-\w{3}`, `FINDINGS-`) from `README.md`, `config.example.yaml`, `.env.example`, `docs/EXTENDING.md`. Spec IDs may remain in `src/` and `tests/` comments where they serve as code↔spec cross-references.
- [ ] **CLEAN-02**: Genericize `config.example.yaml` to use placeholder tool names (`<safe_read_tool_a>`, `<your_tool_name>`, etc.) — remove the ~50 homelab-specific tool entries. The file becomes a worked template, not a homelab-specific config.
- [ ] **CLEAN-03**: Move the existing homelab-mcp config (current `config.example.yaml` content) to `examples/homelab-mcp.yaml` as a reference for operators using homelab-mcp specifically.
- [ ] **CLEAN-04**: README worked examples switch to generic placeholders. Add a "real-world example" link pointing at `examples/homelab-mcp.yaml`.
- [ ] **CLEAN-05**: `mcp-test-framework config-init` emits a complete self-contained starter config (full top-level sections: `ollama:`, `mcp_server:`, `target:`, `judge_timeout_seconds:`, `tools:`) — not partial deltas relying on env defaults to backfill. The emitted file must load and run without any `.env` file present.
- [ ] **CLEAN-06**: `.env.example` updated to reflect the post-overlay-removal model (env vars for CI secrets only, not config). File explicitly states "env vars no longer override config; this file documents secret passthrough patterns only."

### PERSONA — Vibe-coded MCP persona reframe

- [ ] **PERSONA-01**: README and `docs/EXTENDING.md` add a "Testing an MCP server you didn't write" section reframing black-box from a test-discipline rule to a user-facing feature.
- [ ] **PERSONA-02**: `mcp-test-framework list-tools` output includes each tool's `inputSchema` so the operator can see parameter shapes without reading SUT source. Verbosity controls (default summary, `--full` or equivalent for full schema) so output stays readable at homelab-mcp scale (~70 tools).
- [ ] **PERSONA-03**: Operator-facing error messages reviewed and rewritten in operator terms (no internal jargon, no spec IDs in user-visible output). Error messages name actionable next steps (e.g., "run `mcp-test-framework config-init` to generate a starter config").

### SAFE — Config safety + opt-in tool selection

- [ ] **SAFE-01**: `tools:` becomes an opt-in allowlist. Three states: (a) tool unlisted → auto-skip with reason `"not selected in config"`; (b) tool listed with `skip: false` (default) → runs; (c) tool listed with `skip: true` + non-empty `skip_reason` → skip with curated reason. The "master config + focus toggle" workflow is preserved by state (c).
- [ ] **SAFE-02**: When `--config` and `MCPTF_CONFIG_FILE` are both unset, framework auto-discovers `./config.yaml` in the current working directory. `--config PATH` continues to override.
- [ ] **SAFE-03**: When no config is found anywhere (no `--config`, no `MCPTF_CONFIG_FILE`, no `./config.yaml`), framework fails loud with exit code 2 and a message naming `mcp-test-framework config-init -o config.yaml` as the recovery action. Framework refuses to run with destructive defaults.
- [ ] **SAFE-04**: `MCPTF_CONFIG_FILE` set to a non-existent path errors with exit code 2 — mirroring the `--config` CLI behavior. No silent drop. Both routes treat "where is the YAML" identically.
- [ ] **SAFE-05**: Drop `.env` loading and env-var overlay entirely from the config layer. Config sources reduce to: defaults → YAML → CLI flags. Env vars become a passthrough mechanism for CI secrets (e.g., API keys handled by individual subsystems), not a config source.
- [ ] **SAFE-06**: Config schema bumps to `version: 2`. Loading a `version: 1` config produces a loud migration error naming the exact `config-init` command to regenerate. Error message explains the opt-out → opt-in semantic change.
- [ ] **SAFE-07**: Migration documentation (`docs/MIGRATION-v1-to-v2.md` or equivalent) walks an existing operator through: regenerate config via `config-init`, port over `call_arguments` / `judges` / `skip_reason` for tools they want to keep, drop `.env` files.

### RUNNER — Hybrid runner with domain UI

- [ ] **RUNNER-01**: `mcp-test-framework run` wraps the pytest invocation (subprocess vs `pytest.main` decided in plan-phase), captures JUnit XML internally, and renders an MCP-domain UI rather than emitting pytest's native output.
- [ ] **RUNNER-02**: Domain UI shape: header (server, discovered/running/skipping/judges-per-tool/test-plan totals), per-tool result rows (PASS/FAIL/SKIP with judge reasoning on FAIL), summary line. Pytest framing (`=== test session starts ===`, per-test `.`/`F` markers) does not leak into operator output by default.
- [ ] **RUNNER-03**: `--raw` (or equivalent) escape hatch bypasses the wrapper and forwards all flags to pytest verbatim — for maintainers and CI debugging. `mcp-test-framework run --raw` ≈ `uv run pytest tests/`.
- [ ] **RUNNER-04**: Output verbosity ladder: `-q` shows summary line only; default shows the domain UI; `--explain` (from UX-02) adds skipped-tool detail; `--debug` adds raw pytest output and tracebacks.
- [ ] **RUNNER-05**: Existing `--junit-xml=PATH` flag continues to emit operator-specified JUnit XML at the given path (v1.1 OUTPUT-01 contract preserved). The wrapper uses a separate internal tempfile so `--junit-xml=PATH` semantics don't change.
- [ ] **RUNNER-06**: Exit codes preserved across the wrapper: 0 (all pass), 1 (test failures), 2 (config / collection errors), 130 (SIGINT).

### SURFACE — Operator vs framework test surface split

- [ ] **SURFACE-01**: `tests/` directory split into `tests/contract/` (operator-relevant: tests against the SUT contract) and `tests/framework/` (internal: framework self-tests like config validation, reporter, isolation, banned-imports, snippet correctness).
- [ ] **SURFACE-02**: `mcp-test-framework run` (post-RUNNER-01 wrapper) collects only `tests/contract/` by default. Framework self-tests are reachable via `uv run pytest tests/` directly or a `--with-framework` (or equivalent) opt-in flag on the runner.
- [ ] **SURFACE-03**: Existing test files moved to the correct subdirectory via `git mv` so file history is preserved. Shared fixtures (e.g. `pytest_generate_tests` for tool discovery) stay in a top-level `tests/conftest.py` or are split appropriately.
- [ ] **SURFACE-04**: Banned-imports test continues to run against the framework (`tests/framework/test_banned_imports.py` enforces `homelab-mcp` is not imported by `src/`). The black-box rule is enforced regardless of which test surface ran.

### UX — Reporter UX overhaul

- [ ] **UX-01**: Pre-run digest shown by default before tests execute: server, discovered tool count, running count + names, skipping count (with `--explain` cue), defaulting count, judges-per-tool table, test-plan totals (e.g. "20 contract cases"). Replaces pytest's misleading "N collected, M deselected" line.
- [ ] **UX-02**: `--explain` flag adds full per-tool skip reasons (one line per skipped tool, formatted to stay readable at homelab-mcp scale ~70 tools). The `--explain` flag is plumbed through Typer at the framework CLI layer, not forwarded to pytest.
- [ ] **UX-03**: Post-run summary aggregates per-tool PASS/FAIL/SKIP and per-judge reasoning into the domain UI's tail. Subsumes v1.1's `_reporter.py` per-tool summary (the plugin model may be obsoleted entirely by RUNNER-01).
- [ ] **UX-04**: Output design tested at N=70 (homelab-mcp surface). Pre-run digest stays a single screen regardless of N; `--explain` mode produces ≤ N+5 lines and is grep-able.
- [ ] **UX-05**: `-q` / `--quiet` suppresses the digest and per-tool rows; only the final summary line is emitted. Mirrors v1.1's quiet-mode parity.

---

## Future Requirements (deferred — see seeds and Long-term Vision in PROJECT.md)

| REQ family | Target milestone | Seed |
|------------|------------------|------|
| Process-parallel test execution (xdist) | v1.3 | SEED-002 |
| OpenAI-compat judge backend (`base_url` config) | v1.3 | SEED-005 |
| Warm-up stage (amortize Ollama cold-start) | v1.3 | (no seed; co-shipped with SEED-002/005) |
| Dynamic rubric system (rubrics-as-data) | v1.4 | SEED-003 |
| Agent-realistic-mistake input fuzz | v1.4 | SEED-003 |
| Agentic tool-use judge | v1.5+ | SEED-001 |
| Stateful tool testing with setup/teardown | v1.6+ | SEED-004 |
| Automated planning-artifact regression guard | (deferred) | SEED-009 §4 |

Note: v1.2 scoping moved the SEED-002 / SEED-005 / warm-up cohort from "v1.2 (vision pass commitment)" to v1.3. Operator-first foundations (v1.2) precede performance + portability (v1.3).

---

## Out of Scope (explicit exclusions, with reasoning)

| Excluded | Why |
|----------|-----|
| Live-progress streaming in domain UI (per-test progress bar / spinner) | Hard to do well from JUnit XML (which is post-run); fragile from stdout parsing. Defer to v1.3 if needed. RUNNER-01 renders at end of run by default. |
| Color / TTY-aware rendering (`rich` library or equivalent) | Introduces a runtime dep for cosmetics. Keep v1.2 plain-text; revisit only if operator feedback flags it. RUNNER's design should not preclude it. |
| Cross-platform `_isolation.py` POSIX-arm verification | Deferred at v1.1 close (CD-04). Runs as a side-effect of v1.2 development on a non-Windows host; not gated. |
| Multi-server / multi-config runs | Single-server contract preserved. Multi-config workflow (different focus configs per run) is supported via `--config PATH` selection — not multi-config in one invocation. |
| Web UI / dashboard for the domain UI | Out of scope (PROJECT.md). CLI-only; JUnit XML feeds CI dashboards. |
| Anthropic / OpenAI-direct judge backends | v1.3 cohort (SEED-005). |
| `tests/integration/` or other test surface tiers beyond contract/framework | Two tiers cover the operator vs maintainer split. Further tiers (smoke, integration) defer to when there's a concrete need. |

---

## Traceability

**Coverage:** 31 / 31 v1.2 requirements mapped to phases. No orphans, no duplicates.

| REQ-ID | Phase | Status |
|--------|-------|--------|
| CLEAN-01 | Phase 12 | Pending |
| CLEAN-02 | Phase 12 | Pending |
| CLEAN-03 | Phase 12 | Pending |
| CLEAN-04 | Phase 12 | Pending |
| CLEAN-05 | Phase 12 | Pending |
| CLEAN-06 | Phase 12 | Pending |
| PERSONA-01 | Phase 12 | Pending |
| PERSONA-02 | Phase 12 | Pending |
| PERSONA-03 | Phase 12 | Pending |
| SAFE-01 | Phase 13 | Pending |
| SAFE-02 | Phase 13 | Pending |
| SAFE-03 | Phase 13 | Pending |
| SAFE-04 | Phase 13 | Pending |
| SAFE-05 | Phase 13 | Pending |
| SAFE-06 | Phase 13 | Pending |
| SAFE-07 | Phase 13 | Pending |
| RUNNER-01 | Phase 14 | Pending |
| RUNNER-02 | Phase 14 | Pending |
| RUNNER-03 | Phase 14 | Pending |
| RUNNER-04 | Phase 14 | Pending |
| RUNNER-05 | Phase 14 | Pending |
| RUNNER-06 | Phase 14 | Pending |
| SURFACE-01 | Phase 15 | Pending |
| SURFACE-02 | Phase 15 | Pending |
| SURFACE-03 | Phase 15 | Pending |
| SURFACE-04 | Phase 15 | Pending |
| UX-01 | Phase 16 | Pending |
| UX-02 | Phase 16 | Pending |
| UX-03 | Phase 16 | Pending |
| UX-04 | Phase 16 | Pending |
| UX-05 | Phase 16 | Pending |

---

*Last updated: 2026-05-09 — v1.2 Operator-First Design ROADMAP created via `/gsd-new-milestone` → roadmapper. 31 requirements across 6 categories, mapped 1:1 to Phases 12–16.*
