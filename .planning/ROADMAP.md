# Roadmap: mcp_test_framework

## Milestones

- ✅ **v1.0 MVP** — Phases 01–05 (shipped 2026-05-06) — see [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Multi-Tool + Isolation + JUnit** — Phases 06–11 (shipped 2026-05-08) — see [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Operator-First Design** — Phases 12–16 (shipped 2026-05-12) — see [v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Homelab Scenario Testing** — Phases 17–24 (shipped 2026-05-15) — see [v1.3-ROADMAP.md](milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 Library Mode Delivery** — Phases 25–30 (shipped 2026-05-22) — see [v1.4-ROADMAP.md](milestones/v1.4-ROADMAP.md)
- 🚧 **v1.5 Shim Retirement + Operator Escape Hatches** — Phases 31–35 (in planning)

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

<details>
<summary>✅ v1.2 Operator-First Design (Phases 12–16) — SHIPPED 2026-05-12</summary>

- [x] Phase 12: Doc & persona foundation (9/9 plans) — completed 2026-05-10
- [x] Phase 13: Config safety & opt-in tool selection (5/5 plans) — completed 2026-05-11
- [x] Phase 14: Hybrid runner with domain UI (7/7 plans) — completed 2026-05-11
- [x] Phase 15: Operator vs framework test surface split (4/4 plans) — completed 2026-05-12
- [x] Phase 16: Reporter UX overhaul (5/5 plans) — completed 2026-05-12

Quick task in milestone: 260512-dcs (CLEAN-03 closure — example configs migrated to v2 schema).

</details>

<details>
<summary>✅ v1.3 Homelab Scenario Testing (Phases 17–24) — SHIPPED 2026-05-15</summary>

- [x] Phase 17: Schema-driven codegen surface (6/6 plans) — completed 2026-05-13
- [x] Phase 18: SDET test surface + typed errors (8/8 plans) — completed 2026-05-13
- [x] Phase 19: Stateful primitives + domain UI integration (4/4 plans) — completed 2026-05-13 (PASS-WITH-DEFERRALS; D-02 Resolved-by-deletion in Phase 20)
- [x] Phase 20: v1.3 scope correction — dogfood cleanup + codegen coverage (5/5 plans) — completed 2026-05-14
- [x] Phase 21: SDET authoring docs + README parity (4/4 plans) — completed 2026-05-14 (operator-approved FAIL-sample override)
- [x] Phase 21.1: SDET generated output relocation (4/4 plans, INSERTED) — completed 2026-05-14
- [x] Phase 22: Scrub requirement-ID leaks from src/ (4/4 plans) — completed 2026-05-15
- [x] Phase 23: Test suite debt cleanup (4/4 plans, INSERTED) — completed 2026-05-15
- [x] Phase 24: Tool call serializer omits unset optional params (3/3 plans, INSERTED) — completed 2026-05-15

</details>

<details>
<summary>✅ v1.4 Library Mode Delivery (Phases 25–30) — SHIPPED 2026-05-22</summary>

- [x] Phase 25: Public-API rename (SEED-023) — sdet → test_code (6/6 plans) — completed 2026-05-16
- [x] Phase 26: Packaging foundation — entry-point + py.typed + dist-name + plugin skeleton (5/5 plans) — completed 2026-05-16
- [x] Phase 27: pytest-native ini config + contracts test injection + dogfood (LIB) (5/5 plans) — completed 2026-05-17
- [x] Phase 28: Codegen output path (CODEGEN) (4/4 plans) — completed 2026-05-17
- [x] Phase 29: Live domain-UI reporter plugin (3/3 plans) — completed 2026-05-17
- [x] Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite (4/4 plans) — completed 2026-05-22

</details>

### 🚧 v1.5 Shim Retirement + Operator Escape Hatches (Phases 31–35) — IN PROGRESS

- [x] **Phase 31: Config-surface cleanup — drop `MCPTF_CONFIG_FILE` + `cfg.sdet.*` alias + v1-schema decommission** — Tighten the config surface around `mcp_config_file` ini route as the sole library-mode config source; delete the v1→v2 migration path; relax pinned-message self-tests.
 (completed 2026-05-24)
- [x] **Phase 32: Surface-shim removals — CLI + package + fixtures + discovery** — Delete the v1.4-introduced `sdet`-flavored CLI, package, fixture, console-script, and discovery shims; operator hits operator-tone migration errors pointing at the post-v1.4 names.
 (completed 2026-05-25)
- [x] **Phase 33: Per-bucket skip granularity in `ToolConfig` (999.1)** — Operator escape hatch for required-field tools: opt out of the output bucket per tool while preserving schema + judge signal; collection-time filtering; digest + `--explain` reflect per-bucket skip; docs walkthrough.
 (completed 2026-05-26)
- [x] **Phase 34: Opt-in host isolation passthrough (999.3)** — Audit bare `Config()` callers; ship `host_isolation: strict | passthrough` so live-UAT + SDET scenarios reach operator credentials; passthrough clamps xdist to 1; SEED-022 safety delegation surfaced in docs.
 (completed 2026-05-27)
- [ ] **Phase 35: Zero-shim regression gate (capstone)** — Single CI-runnable sweep across import / CLI / config / fixture / discovery surfaces pinning zero matches for every retired shim; blocks reintroduction.

## Phase Details

### Phase 31: Config-surface cleanup — drop `MCPTF_CONFIG_FILE` + `cfg.sdet.*` alias + v1-schema decommission
**Goal**: Operator's config surface is reduced to one config-resolution route (`mcp_config_file` ini key for library mode + `mcp-contracts run --config PATH` for CLI), one schema version (v2), one valid `test_code:` key — no env-var route, no `sdet:` alias, no v1→v2 migration verbiage anywhere in src/, docs/, or self-tests.
**Depends on**: Nothing (lands first; all other v1.5 phases work against the cleaned surface)
**Requirements**: SHIM-04, SHIM-05, V1DROP-01, V1DROP-02, V1DROP-03, V1DROP-04
**Success Criteria** (what must be TRUE):
  1. Operator pointing `MCPTF_CONFIG_FILE=/path/config.yaml` at `pytest` sees no config loaded from that path — the env var is silently inert (removed); the operator-tone error guidance points at the `mcp_config_file` ini key + `mcp-contracts run --config`.
  2. Operator's `config.yaml` with a top-level `sdet:` block is rejected at load time with an operator-tone Pydantic `extra="forbid"` error naming `test_code:` as the correct key — no `Field(alias="sdet")` resolution path remains.
  3. Operator's `config.yaml` declaring `version: 1` is rejected with a generic operator-tone error pointing at `mcp-contracts config-init` — no migration verbiage, no `docs/MIGRATION-v1-to-v2.md` cross-reference.
  4. `docs/MIGRATION-v1-to-v2.md` no longer exists on disk; README and `docs/ERROR-STYLE.md` and `docs/LIBRARY-MODE.md` reference `version: 2` directly with no migration callout.
  5. `uv run pytest tests/framework/` is green at v1.5 baseline with no self-test pinned to the legacy v1-rejection migration-message text.
**Plans:** 6/6 plans complete
Plans:
- [x] 31-01-PLAN.md - SHIM-04: Remove sdet: alias machinery + add operator-tone rejection branch
- [x] 31-02-PLAN.md - SHIM-05: Unwire MCPTF_CONFIG_FILE + D-06 plugin warning + D-08 formatwarning visibility upgrade
- [x] 31-03-PLAN.md - V1DROP-03/04: Rewrite v1-rejection message to D-11 + relax paired self-tests
- [x] 31-04-PLAN.md - V1DROP-01/04: Delete docs/MIGRATION-v1-to-v2.md + test_migration_doc.py
- [x] 31-05-PLAN.md - V1DROP-02: Doc cross-ref scrub (README, ERROR-STYLE, LIBRARY-MODE, EXTENDING)
- [x] 31-06-PLAN.md - V1DROP-04: SDET YAML swaps + remaining self-test cleanup

### Phase 32: Surface-shim removals — CLI + package + fixtures + discovery
**Goal**: Every v1.4-introduced `sdet`-flavored surface shim is gone; operator invoking any legacy name hits an operator-tone error pointing at the post-v1.4 name.
**Depends on**: Phase 31 (cleaned config surface; `_validate_version` and `extra="forbid"` already tightened before fixture/CLI removals layer in)
**Requirements**: SHIM-01, SHIM-02, SHIM-03, SHIM-06, SHIM-07, SHIM-08
**Success Criteria** (what must be TRUE):
  1. Operator running `from mcp_test_framework.sdet import mcp_session` sees `ModuleNotFoundError` with an operator-tone message pointing at `mcp_test_framework.test_code`; the `sdet` package directory and barrel exports no longer ship.
  2. Operator running `mcp-contracts run --sdet` or `mcp-contracts gen-sdet-classes` hits an operator-tone Typer error naming `--test-code` / `gen-test-classes` as the replacement; the legacy flag/command remain registered as hidden intercepts for v1.5 so the pointer text is guaranteed (clean-delete deferred to v1.6 per CONTEXT D-04 + 32-RESEARCH §SHIM-02/03).
  3. Operator running `mcp-test-framework run` cannot start the framework — the legacy console-script body hard-rejects with an operator-tone message naming `mcp-contracts` and exits non-zero; the `[project.scripts]` entry remains wired to `_deprecated_script:main` for v1.5 so the pointer text is guaranteed, with clean-delete deferred to v1.6 (per CONTEXT D-07 + 32-RESEARCH §SHIM-08). `mcp-contracts` is the only console script that actually runs the framework.
  4. Operator's tests under `tests/sdet/` are no longer auto-discovered (only `tests/test_code/` is); operator-authored tests referencing any of the six unprefixed fixture aliases in `_plugin.py` (`config`, `judge`, `target_tool`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`) fail at fixture-resolution time with the `mcp_*`-prefixed equivalent surfaced in the error (per CONTEXT <domain> post-research correction — the earlier four-name SC#4 wording was imprecise; the post-v1.4 prefixed names are `mcp_config`, `mcp_judge`, `mcp_target_tool`, `mcp_rubric_clarity`, `mcp_rubric_disambiguation`, `mcp_rubric_parameters`).
**Plans**: 6 plans
  - [x] 32-01-PLAN.md — SHIM-01: mcp_test_framework.sdet hard-raise removal stub
  - [x] 32-02-PLAN.md — SHIM-02: --sdet Typer flag hard-rejects with operator-tone pointer to --test-code
  - [x] 32-03-PLAN.md — SHIM-03: gen-sdet-classes Typer command hard-rejects with operator-tone pointer to gen-test-classes
  - [x] 32-04-PLAN.md — SHIM-06: tests/sdet/ discovery removed; warn-on-presence detector + marker scrub + sdet→test_code kwarg rename
  - [x] 32-05-PLAN.md — SHIM-07: six unprefixed fixture aliases become stub-raise pytest.fail with prefixed-name pointer
  - [x] 32-06-PLAN.md — SHIM-08: mcp-test-framework console-script hard-rejects + cross-doc scrub to mcp-contracts

### Phase 33: Per-bucket skip granularity in `ToolConfig` (999.1)
**Goal**: Operator can opt out of named test buckets (`schema`, `judge`, `output`) per tool in `config.yaml` while leaving other buckets enabled — the required-field-tool escape hatch identified during Phase 30 UAT-1.
**Depends on**: Phase 31 (validator + `extra="forbid"` settled; new schema field lands on a stable config surface)
**Requirements**: BUCKET-01, BUCKET-02, BUCKET-03, BUCKET-04, BUCKET-05
**Success Criteria** (what must be TRUE):
  1. Operator setting `tools.<name>.skip_buckets: ["output"]` in `config.yaml` sees the tool's schema + judge tests run while the output-bucket tests do not appear in `pytest --collect-only` output (collection-time filtering — same hotfix pattern as v1.1.1 / 260508-p0b; not rendered as runtime-SKIPPED rows).
  2. Operator typing `skip_buckets: ["otput"]` (or any other unknown bucket) sees a Pydantic validation error at load time naming the three valid buckets (`schema`, `judge`, `output`).
  3. Operator running with `--explain` sees a grep-able per-tool block listing which buckets were skipped and the config field that drove the skip; the pre-run digest reflects per-bucket skip counts alongside the existing whole-tool skip counts.
  4. Operator reading README + `docs/LIBRARY-MODE.md` finds a worked example showing a required-field tool skipping only the `output` bucket while schema + judge still run.
**Plans:** 6/6 plans complete
Plans:
- [x] 33-01-PLAN.md - BUCKET-01/03: ToolConfig.skip_buckets field + contracts/_buckets.py source-of-truth mapping
- [x] 33-02-PLAN.md - BUCKET-01: skip + skip_buckets redundancy validator + docs/ERROR-STYLE.md registration
- [x] 33-03-PLAN.md - BUCKET-02: collection-time per-bucket filter in pytest_generate_tests (v1.1.1 pattern extended)
- [x] 33-04-PLAN.md - BUCKET-04: --explain per-tool block extension + pre-run digest per-bucket counts
- [x] 33-05-PLAN.md - BUCKET-05: worked example in README + docs/LIBRARY-MODE.md using create_proxmox_vm + EXTENDING.md scrub

### Phase 34: Opt-in host isolation passthrough (999.3)
**Goal**: Operator can opt into `host_isolation: passthrough` so live-UAT and SDET scenarios reach the operator's real credentials, HOME, and keyring — at the explicit cost of xdist parallelism — while every bare `Config()` caller in src/ + tests/ is audited so neither mode silently leaks env across the seam.
**Depends on**: Phase 31 (config schema surface stable — new `host_isolation` field lands on settled `extra="forbid"` model)
**Requirements**: ISOL-01, ISOL-02, ISOL-03, ISOL-04, ISOL-05, ISOL-06
**Success Criteria** (what must be TRUE):
  1. Operator setting `host_isolation: passthrough` in `config.yaml` and running the framework sees the spawned MCP subprocess inherit the operator's real HOME / USERPROFILE / TEMP / full env vars (allowlist + tempdir redirect bypassed); `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` is NOT injected, so the operator's keyring backend is reachable.
  2. Operator leaving `host_isolation` unset (or setting `strict`) sees v1.0–v1.4 always-on isolation behavior unchanged: 4-entry allowlist + `MCP_*` prefix + tempdir HOME redirect + null keyring backend.
  3. Operator running `pytest -n 4` with `host_isolation: passthrough` sees worker count clamped to 1 with an operator-tone explanation that passthrough sacrifices parallelism for credential reachability; `strict` mode preserves xdist compatibility.
  4. Every bare `Config()` constructor call site in `src/` and `tests/` is identified, documented (which mode it implicitly assumes), and routed through the resolved-config seam so neither mode silently leaks operator env or surprises the operator with a missing-passthrough path.
  5. Operator reading README + `docs/LIBRARY-MODE.md` finds the `strict`-vs-`passthrough` trade-off documented, the SEED-022 safety-delegation cited, the no-keyring-faking lock surfaced, and the passthrough xdist-incompatibility called out in the same section.
**Plans:** 9/9 plans complete
Plans:
- [x] 34-01-PLAN.md - ISOL-01: add top-level host_isolation Literal field to Config + default-pin test
- [x] 34-02-PLAN.md - ISOL-01: operator-tone literal_error branch in cli.py error mapper + pinned test
- [x] 34-03-PLAN.md - ISOL-02/03: _build_passthrough_env + _build_subprocess_env dispatcher in _isolation.py + module docstring rewording
- [x] 34-04-PLAN.md - ISOL-02/03: spawn-site routing (fixtures.py + mcp_client.py + _plugin.py) + _isolated_home D-06 short-circuit + McpTestClient host_isolation kw-only param
- [x] 34-05-PLAN.md - ISOL-04: xdist clamp in _plugin.py pytest_configure (tryfirst + dual mutation of numprocesses AND tx + operator-tone banner)
- [x] 34-06-PLAN.md - ISOL-05: bare-Config audit deliverable + test_code/session.py:67 stash routing + Proxmox scenario inline comments
- [x] 34-07-PLAN.md - ISOL-01 Claude's Discretion: config-init scaffold emits host_isolation: strict with 5-line trade-off comment block
- [x] 34-08-PLAN.md - ISOL-06: README + LIBRARY-MODE.md worked example (Proxmox repro) + ERROR-STYLE.md registration + EXTENDING.md scrub (no-op -- already clean)
- [x] 34-09-PLAN.md - ISOL-05 gap closure: replace bare Config() at 4 sites with explicit TestCodeConfig construction + _plugin.py CR-02 hoist + correct 34-BARE-CONFIG-AUDIT.md + regression pin

### Phase 35: Zero-shim regression gate (capstone)
**Goal**: A single CI-runnable test sweeps every retired-shim surface and returns zero matches — pinning the v1.5 zero-shim state so accidental reintroduction blocks at PR time.
**Depends on**: Phase 31 + Phase 32 (the gate asserts the zero state across both config-surface and CLI/package/fixture/discovery removals — must land after every other SHIM/V1DROP ships)
**Requirements**: SHIM-09
**Success Criteria** (what must be TRUE):
  1. Operator running `uv run pytest tests/framework/` sees a single regression-gate test pass that sweeps the importable surface (`mcp_test_framework.sdet`), CLI surface (`--sdet`, `gen-sdet-classes`, `mcp-test-framework`), config surface (`cfg.sdet.*`, `MCPTF_CONFIG_FILE`), fixture names (`config` / `judge` / `client` / `target_tool` unprefixed), and discovery surface (`tests/sdet/`) and returns zero matches across all five.
  2. Reintroducing any retired shim (e.g. re-adding `--sdet` to the Typer CLI or re-adding `Field(alias="sdet")` to the config model) fails the gate locally and in CI; the failure message names which surface regressed.
  3. Gate is a single file under `tests/framework/` with no shared fixtures or runtime cost beyond regex sweeps + import probes — runs in <1s standalone.
**Plans**: TBD

## Progress

**Execution Order (v1.5):**
Phases execute in numeric order: 31 → 32 → 33 → 34 → 35. Phase 33 (BUCKET) and Phase 34 (ISOL) are nominally independent of each other and both depend only on Phase 31's settled config surface — order between them is interchangeable; canonical order is 33 then 34. Phase 35 lands LAST (regression gate cannot pass until every other v1.5 shim ships). Decimal phases (e.g., 31.1) reserved for INSERTED urgent fixes between integer phases.

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
| 12. Doc & persona foundation | v1.2 | 9/9 | Complete | 2026-05-10 |
| 13. Config safety & opt-in tool selection | v1.2 | 5/5 | Complete | 2026-05-11 |
| 14. Hybrid runner with domain UI | v1.2 | 7/7 | Complete | 2026-05-11 |
| 15. Operator vs framework test surface split | v1.2 | 4/4 | Complete | 2026-05-12 |
| 16. Reporter UX overhaul | v1.2 | 5/5 | Complete | 2026-05-12 |
| 17. Schema-driven codegen surface | v1.3 | 6/6 | Complete | 2026-05-13 |
| 18. SDET test surface + typed errors | v1.3 | 8/8 | Complete | 2026-05-13 |
| 19. Stateful primitives + domain UI integration | v1.3 | 4/4 | Complete | 2026-05-13 |
| 20. v1.3 scope correction — dogfood cleanup + codegen coverage | v1.3 | 5/5 | Complete | 2026-05-14 |
| 21. SDET authoring docs + README parity | v1.3 | 4/4 | Complete | 2026-05-14 |
| 21.1. SDET generated output relocation | v1.3 | 4/4 | Complete | 2026-05-14 |
| 22. Scrub requirement-ID leaks from src/ | v1.3 | 4/4 | Complete | 2026-05-15 |
| 23. Test suite debt cleanup | v1.3 | 4/4 | Complete | 2026-05-15 |
| 24. Tool call serializer omits unset optional params | v1.3 | 3/3 | Complete | 2026-05-15 |
| 25. Public-API rename (SEED-023) — sdet → test_code | v1.4 | 6/6 | Complete | 2026-05-16 |
| 26. Packaging foundation -- entry-point + py.typed + dist-name + plugin skeleton | v1.4 | 5/5 | Complete | 2026-05-16 |
| 27. register() API + contracts sub-package + test extraction | v1.4 | 5/5 | Complete | 2026-05-17 |
| 28. Codegen output path (CODEGEN) | v1.4 | 4/4 | Complete | 2026-05-17 |
| 29. Live domain-UI reporter plugin | v1.4 | 3/3 | Complete | 2026-05-17 |
| 30. CLI demotion + carry-forward UAT closure + docs rewrite | v1.4 | 4/4 | Complete | 2026-05-20 |
| 31. Config-surface cleanup — drop MCPTF_CONFIG_FILE + cfg.sdet.* alias + v1-schema decommission | v1.5 | 6/6 | Complete   | 2026-05-24 |
| 32. Surface-shim removals — CLI + package + fixtures + discovery | v1.5 | 6/6 | Complete    | 2026-05-25 |
| 33. Per-bucket skip granularity in ToolConfig (999.1) | v1.5 | 6/6 | Complete    | 2026-05-26 |
| 34. Opt-in host isolation passthrough (999.3) | v1.5 | 9/9 | Complete    | 2026-05-28 |
| 35. Zero-shim regression gate (capstone) | v1.5 | 0/0 | Not started | — |

## Backlog

### Phase 999.2: Codegen-driven parameter-test generation for required-field tools (PLANNED)

**Goal:** Extend `mcp-contracts gen-test-classes` to emit `<tool>_call_smoke.py` typed SDET scenarios for every tool whose `inputSchema.required` is non-empty. Operator drops example arg dicts under `tools.<name>.examples:` in `config.yaml`; codegen owns the boilerplate, operator owns the values (SEED-022). Pairs with Phase 33 per-bucket skip — operator pairs `skip_buckets: ["output"]` + `examples:` to restore output-bucket signal via codegen scenarios.
**Requirements:** GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, GEN-06, GEN-07, GEN-08 (derived in 999.2-RESEARCH.md; ROADMAP-level requirements remain TBD until v1.6+ promotion)
**Plans:** 6/6 plans complete

Plans:
- [x] 999.2-01-PLAN.md — GEN-01: ToolConfig.examples field + validator (Wave 1)
- [x] 999.2-02-PLAN.md — GEN-03/04/05: _emit_smoke_scenario pure-data emitter + 10 unit tests (Wave 1)
- [x] 999.2-03-PLAN.md — GEN-02/06: generate() loop wiring + cli.py thread-through + 5 integration tests (Wave 2)
- [x] 999.2-04-PLAN.md — GEN-08: end-to-end self-tests (header parity, overwrite, init integrity, importability) (Wave 3)
- [x] 999.2-05-PLAN.md — GEN-07: config.example.yaml Pattern D + examples/homelab-mcp.yaml opt-in template (Wave 1)
- [x] 999.2-06-PLAN.md — GEN-07: docs touch (LIBRARY-MODE + TEST-CODE-AUTHORING + README) (Wave 3)

**Context (captured 2026-05-19 during Phase 30 UAT-1):** The output-conformance bucket calls every enabled tool with `tool_config.call_arguments` (defaults to `{}`). For tools whose inputSchema declares `required: [...]`, the empty-args call is rejected upstream — the test is structurally non-meaningful unless the operator hand-authors `call_arguments:` per tool. Phase 17 / SEED-014 already ships codegen that derives `<ToolName>Params` Pydantic classes from each tools inputSchema. Proposal: extend `gen-test-classes` to ALSO emit a `tests/test_code/_generated/<tool>_call_smoke.py` per required-field tool — a typed SDET scenario that constructs `<ToolName>Params(...)` from inputSchema example values (or operator-supplied `examples:` blocks) and calls the tool through `tool("name").call(params)` with the Phase 24 `exclude_unset=True` serializer. Authoring story: the operator drops `examples:` into `config.yaml` or `pyproject.toml`, `gen-test-classes` reads them, generated scenarios show up under `tests/test_code/` and run in the test-code surface. Codegen owns the boilerplate; the operator owns the example values (SEED-022 respected). Adjacent: a CLI subcommand `mcp-contracts list-required` that reads inputSchema + emits the example-values template the operator needs to fill in. Pairs with v1.5 Phase 33 (per-bucket skip) — operator can keep the schema+judge buckets running while output-bucket coverage shifts to codegen-generated SDET scenarios.

### Phase 999.5: Framework self-test pollution when MCPTF_CONFIG_FILE is set (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

**Context (captured 2026-05-19 during Phase 30 UAT-4 closure):** `tests/framework/test_tool_config.py::TestV111SkipFilter::test_allowlist_filters_out_skip_true_tools` passes in isolation and passes when targeted with `-o mcp_config_file=./config_safe_run.yaml`. It FAILS only under the full library-mode run (`pytest -o mcp_config_file=... --mcp-domain-ui=force`) when the operators PowerShell session also has `$env:MCPTF_CONFIG_FILE = "config.yaml"` set (left over from the UAT-1 workaround for the test-code scenarios import-time bare Config() call).

The symptom is a cross-test pollution that only surfaces when bare `Config()` callers fire BEFORE the SkipFilter test runs. The test constructs its own `Config(test_code=..., tools={"a":..., "b":..., "c":...})` and expects `allowed == ["a","c"]`. The failure mode is consistent with another test (or framework code path) mutating shared state that the SkipFilter assertion ends up reading.

Likely culprits (NOT investigated -- candidate hypotheses):
  1. Pydantic-settings nested-dict merge between init_kwargs and YAML source: when bare-ish `Config(tools={...})` is called with `MCPTF_CONFIG_FILE` set, the source pipeline merges the YAMLs `tools:` (49-skip allowlist) with the init_kwargs `tools` instead of fully overriding. If true, every test that constructs Config with a custom `tools` dict is potentially polluted by the operators shell env.
  2. Some test outside `TestV111SkipFilter` is mutating module-global state that the SkipFilter reads. The `_reset_discovery_cache` autouse fixture covers `_runner._DISCOVERED_TOOL_NAMES` -- maybe a different cache exists (e.g. `_plugin._MCP_SERVER_INFO`, a pydantic-settings sources cache) that doesnt get reset.
  3. Order-dependent leak from the contract plugins `pytest_configure` interacting with framework-test imports.

**Why this matters:** The frameworks own self-tests are not robust to operator env. An operator running `pytest` in their normal shell (with `MCPTF_CONFIG_FILE` set per docs/LIBRARY-MODE.md) can see spurious self-test failures that arent actually framework bugs. This will surface again every time someone tries to verify library-mode behavior against a populated config.

**Note (post-v1.5 Phase 31):** SHIM-05 removes the `MCPTF_CONFIG_FILE` env-var route entirely in v1.5; the specific repro under "operator shell has MCPTF_CONFIG_FILE set" may no longer reach the framework via the env-var path after Phase 31. The underlying class-of-bug (pydantic-settings deep-merge between init_kwargs and any YAML source under bare `Config()` callers) survives the env-var removal — re-assess at v1.5 close (Phase 34 ISOL-05 audit will surface the bare-caller inventory).

**Proposed resolution scope:**
- Reproduce in a clean shell post-Phase-31 to confirm whether the env-var removal closes the symptom or only the surface trigger.
- Add a `monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)` to a session-scoped autouse fixture under `tests/framework/conftest.py` (defensive even post-removal).
- If the root cause IS pydantic-settings deep-merging, audit every framework self-test that constructs Config with a custom `tools` dict and either pin them via `Config(yaml_file=tmp_yaml)` (explicit YAML source) or strip the env via monkeypatch.
- Pairs naturally with v1.5 Phase 34 (always-on isolation) -- both stem from the same problem: framework code paths leaking host env into spawn / test surfaces. Phase 34 is operator-facing; 999.5 is framework-internal.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)
