# Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 30-cli-demotion-carry-forward-uat-closure-docs-rewrite
**Areas discussed:** CLI/library parity test design (SC2)

---

## Gray area selection

The orchestrator presented four candidate areas (parity test design, README+docs rewrite scope, live-UAT closure choreography, REQUIREMENTS/ROADMAP amendments + push timing). User selected only **CLI/library parity test design (SC2)** for deep-dive. Other three areas captured under "Claude's Discretion" in CONTEXT.md with default directions and alternatives noted.

| Option | Description | Selected |
|--------|-------------|----------|
| CLI/library parity test design (SC2) | Only new production-shaped code in the phase. Decisions: equivalence definition, config source, invocation strategy. | ✓ |
| README + docs rewrite scope (SC3 + ID-leak scrub) | Decisions: README opener, `docs/LIBRARY-MODE.md` shape, CLI demotion target, ID-leak scrub bundling, SDET-AUTHORING removal timing. | |
| Live-UAT closure choreography (SC4) | Decisions: capture-protocol vs gate-VERIFICATION-on-closure, raw vs sanitized PASS-sample, Phase 17 ~70-tool capture shape. | |
| Amendment scope — REQUIREMENTS / ROADMAP / push timing | Decisions: CLOSE-01 + CLOSE-03 stale-text rewrites, ROADMAP residue (none), `git push` in Phase 30 vs deferred to milestone close. | |

---

## CLI/library parity test design (SC2)

### Sub-decision 1: Equivalence definition

| Option | Description | Selected |
|--------|-------------|----------|
| Counts only | Pass/fail/skip/error totals match on top-level `<testsuite>`. Catches gross divergence, misses same-counts-different-set. | |
| Test-id set + per-test outcome match | Parse both XMLs, build `{nodeid: outcome}` dict, assert equal. Tolerates timestamps/durations/PIDs. (Recommended) | ✓ |
| Structured deep equal with noise-stripping | Strip noisy attrs then deep-compare trees. Catches message-body divergence too. More bikeshed surface. | |
| Combined: counts + outcome match + failure-message smoke-grep | Three-layer pragmatic check; sharp on outcomes, lenient on message text drift. | |

**User's choice:** Test-id set + per-test outcome match (recommended option).
**Notes:** Locks D-01 in CONTEXT.md. The `{nodeid: outcome}` dict is the operator-meaningful interpretation of "identical pass/fail signal" — same tests, same outcomes, tolerant of run-to-run noise.

### Sub-decision 2: Config source

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse `./config.test.yaml` (live homelab-mcp) | Same config Phase 27 D-06 dogfood uses. Zero new fixture infrastructure. | ✓ |
| Dedicated `tests/framework/parity/fixtures/parity_config.yaml` | Subset of `config.test.yaml` for fast iteration. Adds a fixture to keep in sync. | |
| Hermetic stub MCP server under `tests/framework/parity/_fixtures/` | Runs anywhere, no homelab-mcp. Adds stub-server maintenance burden. | |

**User's choice:** Reuse `./config.test.yaml`.
**Notes:** Locks D-02 in CONTEXT.md. The whole v1.4 thesis is "library mode IS the CI loop"; parity test naturally reuses what the rest of framework CI already runs against.

### Sub-decision 3: Invocation strategy + recursion handling

| Option | Description | Selected |
|--------|-------------|----------|
| Two subprocesses + outer marker exclusion | Route A: subprocess `mcp-contracts run ...`. Route B: subprocess `pytest -o "mcp_config_file=..."`. Parity test carries `@pytest.mark.parity`; both subprocesses pass `-m "not parity"` to avoid recursion. (Recommended) | ✓ |
| Two subprocesses, scope inner runs to a single tool | Same shape but `-k <tool_name>` or tiny subset config to limit blast radius. | |
| Typer CliRunner (in-process) + pytester.Pytester | Faster, no subprocess overhead. Bypasses subprocess boundary the CLI normally has — weaker fidelity. | |

**User's choice:** Two subprocesses + outer marker exclusion (recommended option).
**Notes:** Locks D-03 in CONTEXT.md. Operators invoke from a shell; the parity test exercises the same boundary in the same way. `CliRunner` would cut cost but skip the part that matters.

---

## Claude's Discretion

Areas deferred to planner/Claude judgment, captured with default directions in CONTEXT.md `<decisions>` → "Claude's Discretion":

- Parity test file location (default: `tests/framework/parity/test_cli_vs_pytest_route.py`)
- `@pytest.mark.parity` registration site (default: `tests/framework/conftest.py`)
- Skip-when-stack-down behavior (default: mirror `tests/framework/smoke/` pattern)
- `mcp-contracts` invocation form in subprocess (default: `[sys.executable, "-m", "mcp_test_framework.cli", "run", ...]`)
- README + docs rewrite scope (default: rewrite README top, create `docs/LIBRARY-MODE.md`, bundle v1.2-deferred ID-leak scrub, leave `docs/SDET-AUTHORING.md` for v1.5)
- Live-UAT choreography (default: capture-protocols in `30-UAT.md`, do NOT block VERIFICATION.md on UAT closure)
- REQUIREMENTS.md / ROADMAP.md amendments (default: bundle CLOSE-01 + CLOSE-03 rewrites into Phase 30 docs-amendment plan; ROADMAP already current)
- Git push timing (default: defer to `/gsd-complete-milestone v1.4` per memory `project_v1_3_close_push_and_scrub`)

## Deferred Ideas

Captured in CONTEXT.md `<deferred>`:

- **v1.5 cleanup phase carry-over:** `docs/SDET-AUTHORING.md` removal; `mcp-test-framework` CLI alias removal; `MCPTF_CONFIG_FILE` env var removal; schema v2→v3 migration; xdist parallel execution + parity-under-xdist.
- **v1.4-close adjacent:** `/gsd-complete-milestone v1.4` (archives + git push); tool auto-discovery (SEED-???); OpenAI judge backend (SEED-005); multi-server context-manager seam.
- **Explicitly rejected during discussion:** counts-only parity check; structured deep-equal parity; dedicated `parity_config.yaml`; hermetic stub MCP server; in-process CliRunner+Pytester; gating VERIFICATION.md on UAT closure.
