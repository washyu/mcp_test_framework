# Roadmap: mcp_test_framework

## Milestones

- ✅ **v1.0 MVP** — Phases 01–05 (shipped 2026-05-06) — see [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Multi-Tool + Isolation + JUnit** — Phases 06–11 (shipped 2026-05-08) — see [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- 🚧 **v1.2 Operator-First Design** — Phases 12–16 (planning, started 2026-05-09)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 01–05) — SHIPPED 2026-05-06</summary>

- [x] Phase 01: Foundation & Pure-Data Core (4/4 plans) — completed 2026-05-04
- [x] Phase 02: MCP Client Wrapper (3/3 plans) — completed 2026-05-05
- [x] Phase 02.1: Close Phase 2 verification gaps — config + UAT (3/3 plans, INSERTED) — completed 2026-05-05
- [x] Phase 03: Ollama Judge (3/3 plans) — completed 2026-05-05
- [x] Phase 04: Fixtures & Test Cases (3/3 plans) — completed 2026-05-06
- [x] Phase 04.1: McpTestClient session-teardown fix (1/1 plan, INSERTED) — completed 2026-05-06
- [x] Phase 05: CLI, README & Acceptance (5/5 plans) — completed 2026-05-06

</details>

<details>
<summary>✅ v1.1 Multi-Tool + Isolation + JUnit (Phases 06–11) — SHIPPED 2026-05-08</summary>

- [x] Phase 06: Per-session host-state isolation (3/3 plans) — completed 2026-05-07
- [x] Phase 07: Multi-tool discovery & parameterized testing (1/1 plan) — completed 2026-05-07
- [x] Phase 08: Per-tool config registry (4/4 plans) — completed 2026-05-07
- [x] Phase 09: JUnit XML output & per-tool reporting (3/3 plans) — completed 2026-05-08
- [x] Phase 10: v1.1 documentation (2/2 plans) — completed 2026-05-08
- [x] Phase 11: v1.1 cleanup & verification hygiene (4/4 plans) — completed 2026-05-08

</details>

### 🚧 v1.2 — Operator-First Design

- [x] **Phase 12: Doc & persona foundation** — Strip planning-artifact IDs, genericize `config.example.yaml`, complete the `config-init` scaffold, and add the "Testing an MCP server you didn't write" reframe across README and EXTENDING. Foundational hygiene + persona positioning land first so downstream phases operate on clean docs and copy.
 (completed 2026-05-10)
- [ ] **Phase 13: Config safety & opt-in tool selection** — Invert `tools:` from skip-list to allowlist, auto-discover `./config.yaml`, fail loud on missing config, drop `.env` and the env-overlay entirely, bump schema `version: 1 → 2` with a loud migration error pointing at `config-init`.
- [ ] **Phase 14: Hybrid runner with domain UI** — `mcp-test-framework run` wraps pytest, captures JUnit XML internally, and renders an MCP-domain UI (header / per-tool rows / summary) in operator language. Pytest framing no longer leaks; `--raw` keeps the maintainer escape hatch.
- [ ] **Phase 15: Operator vs framework test surface split** — `git mv` `tests/` into `tests/contract/` (operator-relevant) and `tests/framework/` (self-tests). The runner's default collection scope becomes `tests/contract/`; banned-imports and snippet checks stay enforced under `tests/framework/`.
- [ ] **Phase 16: Reporter UX overhaul** — Pre-run digest (server / discovered / running / skipping / judges / test-plan totals), `--explain` flag for per-tool skip reasons, post-run aggregation, and verbosity ladder (`-q` / default / `--explain` / `--debug`). Output designed for N=70 readability.

## Phase Details

### Phase 12: Doc & persona foundation
**Goal**: An operator browsing the repo for the first time sees generic, vibe-coded-MCP-friendly docs and a `config-init`-generated config that runs without an `.env` file. Planning provenance (phase numbers, plan IDs, internal spec IDs) does not leak into user-facing surfaces.
**Depends on**: Nothing (first v1.2 phase; v1.1 is shipped)
**Plans:** 9/9 plans complete
  - [x] 12-01-PLAN.md — docs/ERROR-STYLE.md style guide + examples/README.md + Wave-0 banned-token tests (PERSONA-03 setup; wave 1)
  - [x] 12-02-PLAN.md — .env.example reframed for CI-secret passthrough (CLEAN-06 + CLEAN-01; wave 1)
  - [x] 12-03-PLAN.md — git mv config.example.yaml -> examples/homelab-mcp.yaml; rewrite config.example.yaml as 3-pattern placeholder template (CLEAN-02 + CLEAN-03; wave 2, depends on 12-01)
  - [x] 12-04-PLAN.md — cli.py: _emit_operator_error helper + rewrite four PERSONA-03 error sites + rewrite _format_tools_yaml_scaffold for self-contained scaffold (CLEAN-05 + CLEAN-01 + PERSONA-03; wave 2, depends on 12-01)
  - [x] 12-05-PLAN.md — list-tools UX: _format_param_signature + --full + --name flags (PERSONA-02; wave 3, depends on 12-04)
  - [x] 12-06-PLAN.md — README + docs/EXTENDING.md scrub + PERSONA-01 framing/walkthrough sections + Wave-0 cross-file banned-token guard (CLEAN-01 + CLEAN-04 + PERSONA-01; wave 3, depends on 12-03)
**Requirements**: CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04, CLEAN-05, CLEAN-06, PERSONA-01, PERSONA-02, PERSONA-03
**Success Criteria** (what must be TRUE):
  1. An operator who runs `mcp-test-framework config-init -o config.yaml` against any MCP server gets a complete, self-contained config file (top-level `ollama:`, `mcp_server:`, `target:`, `judge_timeout_seconds:`, `tools:` all populated) that loads and runs with no `.env` file present.
  2. An operator who reads `README.md`, `config.example.yaml`, `.env.example`, or `docs/EXTENDING.md` does not encounter `Phase \d`, `Plan \d-\d`, `TOOLCFG-`, `D-…`, `ISOL-…`, `OUTPUT-…`, or quick-task IDs (`260507-…`); a manual scan of those four files returns zero such occurrences.
  3. An operator browsing the repo finds the homelab-mcp-specific config preserved as a worked reference at `examples/homelab-mcp.yaml`; `config.example.yaml` itself uses generic placeholder tool names (`<safe_read_tool_a>`, `<your_tool_name>`).
  4. An operator reading the README finds a "Testing an MCP server you didn't write" section that frames black-box as a feature (test any MCP server you didn't author) and `mcp-test-framework list-tools` shows each discovered tool's `inputSchema` summary so they can construct test calls without reading SUT source.
  5. Operator-visible error messages (config load failures, MCP spawn failures, missing config) are written in operator terms — no internal jargon, no spec IDs — and each one names the actionable next step (e.g., "run `mcp-test-framework config-init -o config.yaml` to generate a starter config").

### Phase 13: Config safety & opt-in tool selection
**Goal**: An operator running `mcp-test-framework run` against an unconfigured directory cannot accidentally exercise destructive tools. Config becomes mandatory, opt-in, and unambiguous about which tools will be invoked. The new `version: 2` schema migration is loud, not silent.
**Depends on**: Phase 12 (the missing-config error message and the `version: 2` migration error both reference `config-init`'s now-complete scaffold from CLEAN-05; PERSONA-03's error-message tone applies here too)
**Requirements**: SAFE-01, SAFE-02, SAFE-03, SAFE-04, SAFE-05, SAFE-06, SAFE-07
**Success Criteria** (what must be TRUE):
  1. An operator running `mcp-test-framework run` from a directory with no `config.yaml`, no `--config`, and no `MCPTF_CONFIG_FILE` set sees a clear error pointing at `mcp-test-framework config-init -o config.yaml`, exits 2, and never spawns the MCP server. No destructive defaults run.
  2. An operator who lists exactly two tools in `tools:` (with no `skip:` field) sees only those two tools run; every other tool the server advertises is auto-skipped with reason `"not selected in config"`. The 56-entry skip-list pattern from v1.1 collapses to a 2-entry allowlist.
  3. An operator who runs `mcp-test-framework run` with no `--config` flag in a directory containing `./config.yaml` sees the framework auto-discover and load that file (no env var or CLI flag required).
  4. An operator who typos `MCPTF_CONFIG_FILE=/path/that/does/not/exist` sees an error and exit code 2 — identical behavior to `--config /path/that/does/not/exist`. Neither route silently drops to defaults.
  5. An operator loading a `version: 1` v1.1-era config sees a loud migration error naming the opt-out → opt-in semantic change and pointing at `config-init` to regenerate; a `docs/MIGRATION-v1-to-v2.md` walks them through porting `call_arguments` / `judges` / `skip_reason` for tools they want to keep.
  6. An operator who has a `.env` file in their working directory sees no behavioral difference from when it is absent — `.env` and env-overlay no longer override config; only YAML and CLI flags shape the run.
**Plans:** 3/5 plans executed
  - [x] 13-01-cli-resolver-PLAN.md — Promote _load_config into the SAFE-02/03/04 resolver + flip config-init scaffold version literal 1→2 (wave 1)
  - [x] 13-02-env-overlay-strip-PLAN.md — Delete _BareNameNestedEnvSource + .env/env-overlay; flip _validate_version 1→2 with LOCKED SAFE-06 ERROR-STYLE message (wave 2, depends 13-01)
  - [x] 13-03-allowlist-three-state-PLAN.md — Invert tests/conftest.py filter to allowlist; compose state-a/state-c reasons in _reporter.py with two locked constants (wave 2, depends 13-01)
  - [ ] 13-04-target-removal-PLAN.md — Delete TargetConfig, Config.target field, and fixtures.py override block; collapse selection to single allowlist mechanism (wave 3, depends 13-02 + 13-03)
  - [ ] 13-05-migration-doc-PLAN.md — Create docs/MIGRATION-v1-to-v2.md (SAFE-07) + audit pyproject.toml has no python-dotenv direct dep (wave 3, depends 13-02)


### Phase 14: Hybrid runner with domain UI
**Goal**: An operator running `mcp-test-framework run` sees output in MCP-domain language (server, tools, judges, verdicts) without pytest's collection / deselection / dot-progress framing. Pytest remains the orchestration engine internally, but its output is invisible to the operator by default.
**Depends on**: Phase 13 (the runner's pre-flight checks and "no config" path use SAFE-03's failsafe; the digest's "Skipping" count needs SAFE-01's opt-in semantics to be truthful)
**Requirements**: RUNNER-01, RUNNER-02, RUNNER-03, RUNNER-04, RUNNER-05, RUNNER-06
**Success Criteria** (what must be TRUE):
  1. An operator running `mcp-test-framework run` against a configured server sees a domain-shaped report: header (server command, discovered/running/skipping counts, judges-per-tool, test-plan totals), per-tool result rows (`✓` / `✗` / `–` with judge-failure reasoning extracted on FAIL), and a single summary line. No `=== test session starts ===`, no per-test `.`/`F` markers, no `[<param>]` parametrize suffixes leak into the output.
  2. A maintainer running `mcp-test-framework run --raw` (or the equivalent escape-hatch flag) sees pytest's full native output — all forwarded flags reach pytest verbatim — equivalent to `uv run pytest tests/contract/`.
  3. An operator running with `-q` sees only the summary line; default verbosity shows the domain UI; `--explain` adds skipped-tool detail; `--debug` adds raw pytest output and tracebacks. Each rung adds information; none re-shapes the layer below.
  4. An operator running `mcp-test-framework run --junit-xml=results.xml` still gets a standard JUnit XML at `results.xml` (v1.1 OUTPUT-01 contract preserved); the wrapper consumes its own internal tempfile so the operator-visible path is untouched.
  5. Exit codes remain stable across the wrapper boundary: 0 (all pass), 1 (test failures), 2 (config / collection / pre-flight errors), 130 (SIGINT). A CI pipeline wired to v1.1's exit-code contract continues to work without changes.
**Plans:** 5 plans
  - [x] 13-01-cli-resolver-PLAN.md — Promote _load_config into the SAFE-02/03/04 resolver + flip config-init scaffold version literal 1→2 (wave 1)
  - [x] 13-02-env-overlay-strip-PLAN.md — Delete _BareNameNestedEnvSource + .env/env-overlay; flip _validate_version 1→2 with LOCKED SAFE-06 ERROR-STYLE message (wave 2, depends 13-01)
  - [x] 13-03-allowlist-three-state-PLAN.md — Invert tests/conftest.py filter to allowlist; compose state-a/state-c reasons in _reporter.py with two locked constants (wave 2, depends 13-01)
  - [ ] 13-04-target-removal-PLAN.md — Delete TargetConfig, Config.target field, and fixtures.py override block; collapse selection to single allowlist mechanism (wave 3, depends 13-02 + 13-03)
  - [ ] 13-05-migration-doc-PLAN.md — Create docs/MIGRATION-v1-to-v2.md (SAFE-07) + audit pyproject.toml has no python-dotenv direct dep (wave 3, depends 13-02)


### Phase 15: Operator vs framework test surface split
**Goal**: An operator running the framework against their MCP server sees only contract-level test results — not the framework's ~107 self-tests for parser internals, config validation, README snippet correctness, or banned imports. Maintainers retain full access to the framework self-test surface for CI.
**Depends on**: Phase 14 (the runner's collection scope contract — what `mcp-test-framework run` defaults to — drives where the contract folder lives and what the wrapper passes to pytest)
**Requirements**: SURFACE-01, SURFACE-02, SURFACE-03, SURFACE-04
**Success Criteria** (what must be TRUE):
  1. An operator running `mcp-test-framework run` against an MCP server with two enabled tools sees only contract-level results (≈ 20 cases for 2 tools); the ~107 framework self-tests are not collected and do not appear in the operator's output.
  2. A maintainer running `uv run pytest tests/` directly continues to exercise both `tests/contract/` and `tests/framework/`; the runner's `--with-framework` (or equivalent) opt-in flag makes the same surface reachable through the operator CLI for CI use.
  3. The repo's `tests/contract/` and `tests/framework/` directory split preserves git history for every moved file (verified by `git log --follow` on at least one file from each subtree).
  4. The black-box rule remains mechanically enforced: `tests/framework/test_banned_imports.py` continues to fail the maintainer suite if `homelab-mcp` is imported anywhere in `src/`. The enforcement does not depend on which test surface the operator selected.
**Plans:** 5 plans
  - [x] 13-01-cli-resolver-PLAN.md — Promote _load_config into the SAFE-02/03/04 resolver + flip config-init scaffold version literal 1→2 (wave 1)
  - [ ] 13-02-env-overlay-strip-PLAN.md — Delete _BareNameNestedEnvSource + .env/env-overlay; flip _validate_version 1→2 with LOCKED SAFE-06 ERROR-STYLE message (wave 2, depends 13-01)
  - [ ] 13-03-allowlist-three-state-PLAN.md — Invert tests/conftest.py filter to allowlist; compose state-a/state-c reasons in _reporter.py with two locked constants (wave 2, depends 13-01)
  - [ ] 13-04-target-removal-PLAN.md — Delete TargetConfig, Config.target field, and fixtures.py override block; collapse selection to single allowlist mechanism (wave 3, depends 13-02 + 13-03)
  - [ ] 13-05-migration-doc-PLAN.md — Create docs/MIGRATION-v1-to-v2.md (SAFE-07) + audit pyproject.toml has no python-dotenv direct dep (wave 3, depends 13-02)


### Phase 16: Reporter UX overhaul
**Goal**: An operator preparing to run the framework sees an unambiguous pre-run digest of what will and won't execute (eliminating pytest's misleading "N collected, M deselected" framing), and a post-run aggregation in the same domain language. Output stays single-screen-readable at homelab-mcp scale (~70 tools).
**Depends on**: Phase 14 (UX-03's aggregation lives inside the runner's domain UI surface; UX-02's `--explain` plumbs through the runner's verbosity ladder; v1.1's `_reporter.py` plugin is subsumed or obsoleted by the runner)
**Requirements**: UX-01, UX-02, UX-03, UX-04, UX-05
**Success Criteria** (what must be TRUE):
  1. An operator running `mcp-test-framework run` sees a pre-run digest before any tests execute, listing: server command, discovered tool count, running count + names, skipping count, judges-per-tool, and test-plan totals — replacing pytest's "N collected, M deselected" framing entirely.
  2. An operator who passes `--explain` sees a one-line-per-tool reason for every skipped tool. At homelab-mcp's ~70-tool surface, the explain output stays under N+5 lines and remains grep-able (one tool per line, no wrapping).
  3. An operator's post-run output aggregates per-tool PASS/FAIL/SKIP plus per-judge reasoning into the domain UI's tail; v1.1's separate `_reporter.py` per-tool summary section is no longer needed (subsumed or replaced).
  4. An operator running `-q` / `--quiet` sees neither the digest nor the per-tool rows — only the final summary line. v1.1's quiet-mode parity is preserved.
  5. The digest's discovered/running/skipping counts agree with what the runner actually executes; an operator's manual config inspection cannot find a tool that the digest claims to skip but that actually runs (or vice versa).
**Plans:** 5 plans
  - [ ] 13-01-cli-resolver-PLAN.md — Promote _load_config into the SAFE-02/03/04 resolver + flip config-init scaffold version literal 1→2 (wave 1)
  - [ ] 13-02-env-overlay-strip-PLAN.md — Delete _BareNameNestedEnvSource + .env/env-overlay; flip _validate_version 1→2 with LOCKED SAFE-06 ERROR-STYLE message (wave 2, depends 13-01)
  - [ ] 13-03-allowlist-three-state-PLAN.md — Invert tests/conftest.py filter to allowlist; compose state-a/state-c reasons in _reporter.py with two locked constants (wave 2, depends 13-01)
  - [ ] 13-04-target-removal-PLAN.md — Delete TargetConfig, Config.target field, and fixtures.py override block; collapse selection to single allowlist mechanism (wave 3, depends 13-02 + 13-03)
  - [ ] 13-05-migration-doc-PLAN.md — Create docs/MIGRATION-v1-to-v2.md (SAFE-07) + audit pyproject.toml has no python-dotenv direct dep (wave 3, depends 13-02)


## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 01. Foundation & Pure-Data Core | v1.0 | 4/4 | Complete | 2026-05-04 |
| 02. MCP Client Wrapper | v1.0 | 3/3 | Complete | 2026-05-05 |
| 02.1. Close Phase 2 verification gaps | v1.0 | 3/3 | Complete | 2026-05-05 |
| 03. Ollama Judge | v1.0 | 3/3 | Complete | 2026-05-05 |
| 04. Fixtures & Test Cases | v1.0 | 3/3 | Complete | 2026-05-06 |
| 04.1. McpTestClient teardown fix | v1.0 | 1/1 | Complete | 2026-05-06 |
| 05. CLI, README & Acceptance | v1.0 | 5/5 | Complete | 2026-05-06 |
| 06. Per-session host-state isolation | v1.1 | 3/3 | Complete | 2026-05-07 |
| 07. Multi-tool discovery & parameterized testing | v1.1 | 1/1 | Complete | 2026-05-07 |
| 08. Per-tool config registry | v1.1 | 4/4 | Complete | 2026-05-07 |
| 09. JUnit XML output & per-tool reporting | v1.1 | 3/3 | Complete | 2026-05-08 |
| 10. v1.1 documentation | v1.1 | 2/2 | Complete | 2026-05-08 |
| 11. v1.1 cleanup & verification hygiene | v1.1 | 4/4 | Complete | 2026-05-08 |
| 12. Doc & persona foundation | v1.2 | 9/9 | Complete   | 2026-05-10 |
| 13. Config safety & opt-in tool selection | v1.2 | 3/5 | In Progress|  |
| 14. Hybrid runner with domain UI | v1.2 | 0/0 | Not started | - |
| 15. Operator vs framework test surface split | v1.2 | 0/0 | Not started | - |
| 16. Reporter UX overhaul | v1.2 | 0/0 | Not started | - |
