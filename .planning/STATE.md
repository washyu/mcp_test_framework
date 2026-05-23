---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Library Mode Delivery
status: executing
stopped_at: Phase 30 Plan 30-04 dogfood verification complete
last_updated: "2026-05-23T03:56:34.918Z"
last_activity: 2026-05-23
progress:
  total_phases: 11
  completed_phases: 6
  total_plans: 27
  completed_plans: 27
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-15 after v1.3 milestone close + v1.4 scoping)

**Core value:** A `pytest`-runnable test suite that exercises every MCP tool end-to-end (schema → call → judge) for the operator persona AND lets an SDET author typed scenario tests against the same MCP server for stateful coverage — exits non-zero on any failure, no `homelab-mcp`-specific code in framework `src/` (SEED-022).
**Current focus:** Phase 30 — cli-demotion-carry-forward-uat-closure-docs-rewrite

## Current Position

Phase: 30 (cli-demotion-carry-forward-uat-closure-docs-rewrite) — EXECUTING
Plan: 2 of 4
Status: Ready to execute
Last activity: 2026-05-23

## Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| v1.0 closing metrics (reference) | 7 phases / 22 plans / 29 reqs | shipped 2026-05-06 |
| v1.1 closing metrics (reference) | 6 phases / 17 plans / 25 reqs | shipped 2026-05-08 |
| v1.2 closing metrics | 5 phases / 30 plans / 31 reqs | shipped 2026-05-12 |
| v1.2 source diff | +37,100 / −1,928 across 168 files | doc churn + tests dominate |
| v1.2 timeline | 4 days (2026-05-09 → 2026-05-12) | 236 commits in range |
| v1.2 quick tasks | 1 (260512-dcs) | CLEAN-03 closure via audit |
| v1.3 closing metrics | 9 phases / 42 plans / 29 reqs | shipped 2026-05-15 |
| v1.4 scoping metrics | 6 phases / 28 reqs / plans TBD | roadmap created 2026-05-15 |
| Cross-milestone totals (shipped) | 27 phases / 111 plans / 114 reqs | v1.0 + v1.1 + v1.2 + v1.3 |
| Phase 18 P03 | 365 | 1 tasks | 4 files |
| Phase 18 P04 | 51 | 1 tasks | 1 files |
| Phase 18 P07 | ~1500 | 3 tasks | 4 files |
| Phase 18 P08 | ~1500 | 4 tasks | 4 files | 50 tests added; Task 5 no-op (pre-satisfied by 18-02) |
| Phase 20 P20-05 | 2min | 1 tasks | 1 files |
| Phase 21 P01 | ~20min | 4 tasks | 2 files |
| Phase 21 P02 | ~25min | 4 tasks (Task 2 re-scoped) | 1 modified, 1 deleted | embedded FAIL output as README sample (operator decision at human-verify checkpoint) |
| Phase 21 P03 | ~2min | 1 task | 1 file | dual-persona note appended to CLAUDE.md '## What This Project Is' |
| Phase 21 P04 | ~5min | 1 task | 0 files modified | verification matrix: 16/16 checks PASS (B4 deviation documented; re-scope approved) |
| Phase 21.1 P01 | 80min | 3 tasks | 17 files |
| Phase 21.1 P02 | 6min | 3 tasks | 6 files |
| Phase 21.1 P03 | ~6.5min | 4 tasks | 3 files |
| Phase 21.1 P04 | ~5min | 4 tasks | 63 files |
| Phase 23 P01 | ~20min | 4 tasks | 5 files | Cluster A reds resolved + D-03 env-pollution seal |
| Phase 23 P02 | ~2min | 2 tasks | 2 files | Cluster B parents[2]→parents[3] mechanical bump |
| Phase 23 P03 | ~6min | 4 tasks (2 diagnostic) | 1 file | Cluster C README D-05 + D-06 fixes |
| Phase 23 P04 | ~5min | 1 task (diagnostic-only) | 0 files | close-gate GREEN: 575 passed / 0 failed / 0 errored |
| Phase 24 P01 | ~10min | 3 tasks | 3 files |
| Phase 24 P24-03 | ~3min | 1 tasks | 1 files |
| Phase 25 P01 | ~9min | 3 tasks | 19 files |
| Phase 25 P02 | ~15min | 2 tasks | 4 files |
| Phase 25 P03 | ~20min | 2 tasks | 17 files |
| Phase 25 P04 | ~25min | 4 tasks | 11 files | Rule-1 deviation: 5 framework self-tests repointed (argv assertions + conftest path + helper name) + 4 D-07 ID literals stripped
| Phase 25 P25-05 | ~20min | 3 tasks | 31 files |
| Phase 25 P25-06 | ~6min | 1 tasks | 2 files | Option A executed: per-line noqa tags on 4 README snapshot lines + leak gate authored; bite-test verified; Phase 25 closed end-to-end (RENAME-01..06)
| Phase 26 P26-01 | ~12min | 3 tasks | 4 files | Wave 1: pyproject.toml dist-rename to mcp-contracts + entry-points + scripts; cli.py:974 fix; REQUIREMENTS.md + ROADMAP.md source-of-truth amendments
| Phase 26 P26-03 | ~3min | 2 tasks | 4 files | Wave 1: three PEP 561 py.typed markers + contracts/__init__.py stub (docstring-only; register() reserved for Phase 27 per D-14)
| Phase 26 P26-02 | ~25min | 3 tasks | 3 files | Wave 2: _plugin.py (pytest11 + 3 hook stubs + 7 fixture re-exports + 6 deprecation aliases) + _deprecated_script.py (console-script shim with lazy cli-import inside main()) + fixtures.py (6 renames + 8 cross-ref repairs including _preflight getfixturevalue string)
| Phase 27 P01 | 45 | 3 tasks | 3 files |
| Phase 27 P02 | 15 | - tasks | - files |
| Phase 27 P03 | 40 | 2 tasks | 1 files |
| Phase 27 P04 | 25min | 3 tasks | 6 files |
| Phase 27 PP05 | 20min | 4 tasks | 13 files |
| Phase 28 P01 | ~8min | 1 tasks | 2 files |
| Phase 28 PP02 | 2.5min | 1 tasks | 2 files |
| Phase 28 PPP03 | 4min | 2 tasks | 3 files |
| Phase 28 P04 | 4min | 2 tasks | 2 files |
| Phase 29 P29-01 | 6min | 2 tasks | 2 files |
| Phase 29 P29-03 | ~12min | 3 tasks | 5 files |
| Phase 30 P04 | ~7min | 3 tasks | 1 files | dogfood verification: passed=670, skipped=3, xfailed=1, failed=0, errored=0; config.test.yaml empty tools: confirmed; parity test collected (1 under -m parity), default-deselected (0 under default addopts) |

## Accumulated Context

### Decisions

Full decision log lives in PROJECT.md "Key Decisions" table (with outcomes assessed at v1.0 + v1.1 + v1.2 + v1.3 close).

**v1.2 roadmapping decisions (2026-05-09):**

- **Phase 12 (CLEAN + PERSONA merged) lands first.** SEED-009 says "FIRST in v1.2" for doc cleanup — foundational hygiene that other phases benefit from (clean docs not churned twice). SEED-007 says "Surface FIRST during milestone framing — cheap to land but expensive to retrofit." Both are doc-heavy and small; merging avoids the overhead of two near-trivial phases. The merged phase still passes the "complete capability" test: an operator browsing a clean repo with a runnable scaffold and persona-correct docs is a coherent verifiable outcome.
- **Phase 13 (SAFE) is the semantic core.** Riskiest single chunk because of the schema v1→v2 migration + opt-in inversion + dropping `.env`. Lands after Phase 12 so the missing-config error and the v1→v2 migration error can both reference the now-complete `config-init` scaffold from CLEAN-05.
- **Phase 14 (RUNNER) before Phase 15 (SURFACE) — explicit user decision locked at scoping.** SEED-011: "Decide BEFORE SEED-010 folder split." The runner contract drives what the folder split needs to support; reversing the order would make the folder split speculative.
- **Phase 16 (UX) lands last.** SEED-008: "Land AFTER SEED-006 (semantics) and SEED-009 (doc cleanup), since this is the UX layer over the new semantics." UX-03 explicitly subsumes v1.1's `_reporter.py`, which RUNNER-01 may obsolete entirely — sequencing UX after RUNNER lets the reporter rebuild rather than be ported.
- **5 phases for 31 reqs.** Comparable density to v1.1 (6 phases / 25 reqs). Phase 12 is intentionally larger (9 reqs) because CLEAN+PERSONA is mostly mechanical doc work; Phase 13 (7 reqs) is the heaviest single technical chunk (schema migration). No phase is a "feature half" — each delivers a coherent operator-perceivable capability.
- **Granularity = standard.** v1.1's "coarse" justification (each phase genuinely separable) holds here too; calibrated 5 phases without padding or compression.
- **No v1.3+ work in v1.2.** xdist (SEED-002), OpenAI-compat backend (SEED-005), warm-up stage all deferred per scoping decision. v1.2 = operator-first foundations.

**v1.3 roadmapping decisions (2026-05-12):**

- **Pivot from "performance + portability" to "SDET + stateful primitives".** v1.2 close + operator pain-point clarification ("manually testing through the Claude client is time-consuming") reframed the v1.3 driver. The originally-pencilled xdist + OpenAI-compat cohort is real, but it deepens the existing contract-validation product; SDET + state opens a new persona (SDET) and unblocks coverage of stateful homelab-mcp tools (VM lifecycle, etc.) that the contract-rubric model can't exercise meaningfully. SEED-014 + SEED-004 pulled forward from `target_milestone: v2.0+`; SEED-015 (library mode) deferred to v1.4 so the SDET surface stabilizes on CLI first. SEED-005/SEED-003 carry to v1.4–v1.5.
- **Phase 17 (CODEGEN) lands first.** Every downstream phase imports from the generated `<ToolName>Params` / `<ToolName>Response` classes (`tool("name").call(params)`). Without codegen, the SDET surface in Phase 18 is stringly-typed and the STATE dogfood in Phase 19 has no typed response object to pass through module-scope fixtures. CODEGEN is the structural seam the other phases hang off.
- **Phase 18 (SDET surface + UI-02 typed error) bundles the API and the typed-error class.** `ToolCallError` is raised by the call wrapper built in this phase and consumed by both contract and SDET paths — keeping it with the wrapper avoids a v1.3.1 retrofit. SDET-01..04 + UI-02 together = "the SDET can write a test and see structured failure detail."
- **Phase 19 (STATE + UI-01) bundles primitives with their first visible consumer.** STATE-01..04 alone is paperwork (yield-fixture pattern doc); STATE-01..04 + UI-01 + a shipping VM-lifecycle scenario = "stateful testing is observably real in the operator UI." Avoids the SEED-004 "half-product" trap explicitly flagged in the seed.
- **Phase 20 (PREFLIGHT) is a small standalone phase.** PREFLIGHT-01..02 are dependency-light (just need the `mcp_test_framework.sdet` namespace from Phase 18); could in principle run in parallel with Phase 19 by the planner. Kept as its own phase because the capability ("clean operator-domain SKIP when env is absent") is verifiable independently, and folding it into Phase 19 would have made that phase a 7-req grab-bag.
- **Phase 21 (DOC-SDET) lands last per the v1.2 Phase 12/16 precedent.** Docs after the surface stabilizes, not against a moving target. DOC-SDET-03 (README char-for-char parity) literally cannot land before Phase 19 ships the renderer integration.
- **5 phases for 21 reqs.** Comparable density to v1.0 (5 reqs/phase) and v1.2 (6 reqs/phase). v1.3 = 4.2 reqs/phase, slightly lower density because Phase 20 is intentionally small (2 reqs) and Phase 21 is a 3-req doc capstone. No phase is a "feature half".
- **Granularity = coarse (per config.json).** Each phase delivers a coherent SDET- or operator-perceivable capability; no phase is splittable without losing coherence. Phase 17 (codegen) is the technically heaviest single chunk because the codegen library choice + Pydantic-from-JSON-Schema + idempotent regen + ToolResponse uniformity are all interlocking.
- **Carry-forward debt:** Phase 13 + 14 live-stack UATs from v1.2 will close opportunistically during v1.3 — the SDET runs against live homelab-mcp + Proxmox + Ollama are the same live-stack exercise those UATs were waiting on. Phase 16 D-11 `--debug` per-judge breakdown remains deferred to v1.5 (cohort with SEED-003); v1.3 does NOT pick it up.

**v1.4 roadmapping decisions (2026-05-15):**

- **Phase numbering continues from v1.3 (Phase 24 → Phase 25).** No `--reset-phase-numbers` flag passed; continuous numbering across milestones preserved (v1.0=01-05, v1.1=06-11, v1.2=12-16, v1.3=17-24, v1.4=25-30).
- **Phase 25 (RENAME) MUST land first.** SEED-023 (`sdet` → `test_code`) is irreversible after the first PyPI publish under any `mcp_test_framework.contracts.register()` surface. Lock the public import surface (package dir, CLI command name, flag name, config field name, docs terminology) BEFORE Phase 26's packaging foundation publishes a corrected dist name to PyPI. All three researchers (Stack/Architecture/Pitfalls) independently arrived at the same first-phase placement.
- **Phase 26 (PACK) MUST come before Phase 27 (LIB).** `[project.entry-points.pytest11]` declaration is the precondition for plugin auto-loading; `register()` injection in Phase 27 requires the plugin entry-point to exist. Six pitfalls preventively addressed in one phase (asyncio config self-check, fixture namespace collision, black-box-rule-in-wheel, `py.typed` missing, wheel-content drift, dist-name typo). Plugin skeleton lands as empty hooks so Phase 27 adds business logic without re-touching `pyproject.toml`.
- **Phase 27 (LIB) is the load-bearing technical bet.** Combines registry → extract → inject (Architecture phases C+D+F) because they're a coherent capability that's only useful as a unit. Spike `pytest_collect_file` virtual `_ContractsModule` injection at phase entry to validate the pattern before locking the API shape (research-flagged MEDIUM-HIGH confidence; HIGH after spike). `register()` accepts only explicit typed kwargs (NO `**kwargs`); signature snapshot test pinned. Multiple `register()` calls per conftest raises (safer for Stable API; merge-configs deferred to v1.5).
- **Phase 28 (CFG + CODEGEN) bundles config seam with codegen output path.** Library-mode config flow has to be settled before docs reference `register()` examples; codegen output path is coupled — operators have no `config.yaml` to set `generated_root`, so the default must work cwd-relative. Cheaper after Phase 27 (uses register's kwarg surface as source of truth).
- **Phase 29 (REPORTER) is orthogonal — independently landable.** Renderer is already input-agnostic; refactor not rewrite. Pairs naturally with renderer split (`_build_parsed_run_from_reports(TestReport[...])` alongside `parse_junit_xml(path)`). Default OFF (TS-5 in research); CI/no-TTY detection forces OFF; xdist coexistence via master-only emission; separate entry-point key so operator can `-p no:mcp_test_framework_reporter` while keeping contract fixtures.
- **Phase 30 (CLOSE) lands last.** Docs LAST per v1.2 Phase 16 / v1.3 Phase 21 precedent — avoid doc-then-redoc churn. CLI demotion only after library mode is proven end-to-end via the framework's own `tests/contract/conftest.py` calling `register()`. Carry-forward UATs (README PASS-sample re-capture, Phase 17 SC1 ~70-tool live, v1.2 Phase 13+14 live-stack UATs) close as part of the library-mode dogfood pass.
- **6 phases for 28 reqs.** Density 4.7 reqs/phase, comparable to v1.3 (4.2) and v1.0 (4.1). Phase 27 is intentionally the largest (8 reqs) because the `register()` API + contracts sub-package + test extraction is one coherent capability — splitting would ship a half-product. Phase 29 is intentionally small (2 reqs) because the reporter capability is independently verifiable and orthogonal to injection.
- **Granularity = coarse (per config.json).** Each phase delivers a coherent operator-perceivable capability; no phase is splittable without losing coherence.
- **Out of v1.4 (deferred to v1.5+):** pytest-xdist parallelism (SEED-002), OpenAI-compat judge backend (SEED-005), `scoped_register()` multi-server context manager, URL-style judge kwarg sugar (`judge="ollama://..."` parser), `gen-test-classes` as library callable, `register(tools=None)` auto-discovery, removal of deprecation aliases, per-judge `--debug` breakdown (Phase 16 D-11 dormant carry-over), schema v2→v3 migration. All explicitly captured in REQUIREMENTS.md "Future Requirements" section to prevent re-triage churn.
- [Phase 25-01]: Rule-1 deviation — 11 framework self-tests under tests/framework/unit/ repointed to mcp_test_framework.test_code (sdet shim only re-exports four public names; private submodules moved with the package)
- [Phase ?]: Phase 25-02 — D-19 resolved (two separate Typer Options for --test-code + hidden --sdet, not combined declaration)
- [Phase ?]: [Phase 25-03]: D-13 implementation moved upstream — pydantic-settings collapses AliasChoices keys before model_validator(mode='before') runs; checks split across _check_legacy_sdet_key_in_yaml (YAML path) + Config.model_validate override (dict path) + the model_validator as defense-in-depth. Behavior contract preserved.
- [Phase 25-04]: Dual-discovery argv shape locked — primary `tests/test_code` is always passed; legacy `tests/sdet` is appended ONLY when the directory contains `test_*.py` files. Empty-directory case (after `git mv`) leaves argv as single-path; populated case (external operator with untouched legacy tree) gets both paths + the session-once `DeprecationWarning` from `tests/test_code/conftest.py`. Classname-prefix check in the JUnit testcase parser accepts BOTH `tests.test_code.test_` AND `tests.sdet.test_` (renderer compatibility through the dual-discovery window).
- [Phase ?]: [Phase 25-05]: docs/SDET-AUTHORING.md moved via git mv to docs/TEST-CODE-AUTHORING.md
- [Phase ?]: [Phase 25-05]: README captured CLI snapshot tagged with HTML sentinel comment for v1.4 close milestone re-capture (D-11). Snapshot block intentionally preserved as verbatim pre-rename capture.
- [Phase ?]: [Phase 25-05]: Rule-1 deviation -- 15 framework self-tests + 1 README HTML-comment rewrite directly caused by Task 3 sweep (AUTOGENERATED header + typer.echo digest + scenario digest banner + ERROR-STYLE.md section headings + doc-scrub Phase-N guard). Bundled in Task 3 commit per plans 25-01..04 precedent.
- [Phase ?]: [Phase 25-05]: Per-line # noqa: sdet-rename-shim tagging applied to all D-18 compat-shim lines because plan 06 leak gate is line-by-line, not block-aware. Includes config.py AliasChoices block, _runner.py sdet= kwarg, cli.py --sdet shim, examples/homelab-mcp.yaml sdet: alias demo.
- [Phase ?]: [Phase 25-06]: Option A executed -- per-line HTML-comment noqa suffix tags on the 4 untagged README snapshot lines (348, 354, 416, 417). Rule-1 deviation absorbing plan-05 territory; honors locked D-18 line-level semantic verbatim; preserves Phase 30 re-capture handoff.
- [Phase ?]: [Phase 25]: Phase 25 (RENAME) closed end-to-end -- 6 plans / 6 waves; RENAME-01 through RENAME-06 shipped. Public import surface locked behind CI gate (tests/framework/test_sdet_rename_leak_gate.py). Phase 26 (PACK) unblocked.
- [Phase ?]: Plan 27-01: Wave 0 spike PASSED -- hybrid _ContractsModule(_PytestModule) injection pattern is GO for Plans 27-02 and 27-03.
- [Phase ?]: Plan 27-01: Operator-facing -k selection against <mcp-contracts> requires substring match (e.g. -k mcp) since pytest -k parser treats - as binary operator.
- [Phase ?]: 27-02: Config loader driven via Config(yaml_file=str(path)) explicit kwarg; rejected env-var-magic internal-workaround on principle.
- [Phase ?]: 27-02: Planning-ID gate (D-NN/LIB-NN/TEST-NN regex) takes precedence over plan's verbatim docstring instructions in src/; scrub before commit (repeat of Plan 27-01 deviation).
- [Phase ?]: Plan 27-03: pytest_collection stash + session.genitems(collector) in pytest_collection_modifyitems is the locked two-hook attachment ritual; sentinel-walk-up from metafunc.definition.parent is required because metafunc.module returns the imported Python module not the _ContractsModule collector
- [Phase ?]: Phase 27-04: _load_config refactored to tuple-return; CLI threads resolved path to subprocess via pytest -o mcp_config_file=PATH; one config-resolution route
- [Phase ?]: Phase 27-04: _session_needs_preflight hybridized to mcp_contract marker OR _LIVE_PREFIXES nodeid; tests/contract/ retained transitionally until Plan 27-05
- [Phase ?]: Plan 28-01: pre-handshake site-packages guard wired into gen-test-classes; out_root resolved + descendant-check fires BEFORE asyncio.Runner(); no bypass per D-09; planning-ID literals scrubbed from src/ per Plan 27-01 leak-gate precedent.
- [Phase ?]: Plan 28-03: overwrite-prompt gate wired between slug derivation and _codegen.generate; no --yes/--force escape hatch (D-06 regression-guarded); missing-test_code.generated_root next-step flipped to canonical mcp-contracts config-init (D-02; v1->v2 + no-config-found messages left on v1.5 cleanup track because ERROR-STYLE.md still pins legacy name).
- [Phase ?]: Plan 28-04 docs sweep complete; CODEGEN-LIB-02 preserved verbatim; stale smart-default removed
- [Phase ?]: Phase 29 Plan 01 — planning IDs scrubbed from src/ to satisfy leak gate
- [Phase 30 P04]: dogfood verification green at v1.4 close -- Phase 27 D-06 ini line (`mcp_config_file = "./config.test.yaml"`) intact; `uv run pytest` returns exit 0 with 670 passed / 3 skipped / 0 failed / 0 errored; Plan 01 parity test correctly collected under -m parity (1 item) and default-deselected under pyproject addopts (0 items); empty allowlist in config.test.yaml verified (zero `<mcp-contracts>::test_*` items collected). CLOSE-01 dogfood verification thread closed (text amendment lives in Plan 30-02).

### Roadmap Evolution

- 2026-05-13: Phase 22 added — scrub requirement-ID leaks from `src/` (5 user-visible CLI docstrings + 58 internal references). Surfaced during Phase 17 live UAT when `mcp-test-framework --help` exposed `CLI-01`/`PERSONA-02`/`CODEGEN-01`-style tags. Source-code analog of the v1.2 doc scrub. v1.3 milestone range extended from Phases 17–21 to Phases 17–22.
- 2026-05-13: Phase 23 added — test suite debt cleanup. Surfaced during Phase 20 UAT: `uv run pytest tests/framework/` returns 11 failed + 1 error, all pre-existing at baseline `cfb04f2`. Four categories: (1) Config schema v1→v2 mismatch — 4 tests in `test_tool_config.py`/`test_homelab_config.py` still expect `version=1`; (2) `parents[2]` path resolution broken after Phase 15-01 folder split (`2e74967`) — 5 tests in `test_cli_errors.py`/`test_migration_doc.py` resolve repo root to `tests/`; (3) missing `tests.test_mcp_tool_contract` module + `tests/docs/MIGRATION-v1-to-v2.md` doc; (4) README line 104 bare `mcp-test-framework run --explain` doc drift; plus 1 environmental ERROR (`homelab-mcp` not on PATH). Gate before v1.3 milestone close so debt does not carry forward. v1.3 milestone range extended from Phases 17–22 to Phases 17–23.
- 2026-05-14: Phase 24 added — tool call serializer omits unset optional params (`model_dump(exclude_unset=True)`). Surfaced during Phase 21 Plan 21-02 UAT: live Proxmox run failed with the upstream homelab-mcp `inputSchema` bug hitting `create_proxmox_vm` (Phase 19-04's prediction that create was safe did not hold). Investigation found `_tool_factory.py:107` emits `null` for unset `cdrom`/`iso` fields. The Phase 17 SEED-022 lock-in disallowed `exclude_none=True` (which masks null bugs); `exclude_unset=True` is the SEED-022-compatible fix — distinguishes user-omitted from user-explicitly-set. Touches `_tool_factory.py`, `docs/SDET-AUTHORING.md` inputSchema-workaround section, README Plan 21-02 sample (re-capture as PASS), and the long-standing `homelab-mcp inputSchema` deferred-fix entry. v1.3 milestone range extended from Phases 17–23 to Phases 17–24.
- 2026-05-15: v1.4 ROADMAP.md created — 6 phases / 28 reqs (RENAME×6, PACK×4, LIB×8, CFG×2, CODEGEN×2, REPORTER×2, CLOSE×4). 100% coverage; no orphans; phase numbering starts at 25.
- Phase 21.1 inserted after Phase 21: SDET generated output relocation — make codegen output config-driven; remove SUT-specific code from src/ (URGENT)

### Blockers/Concerns

None at roadmap stage. Two research-flagged spikes to land during planning:

- **Phase 27 spike:** `pytest_collect_file` returning a virtual `_ContractsModule` is documented but the exact `from_parent` + `_getobj` wiring for a non-filesystem module needs validation. Mitigation: time-box spike at Phase 27 entry; fall back to operator-writes-one-re-export-file if blocked.
- **Phase 29 spike:** Verify `pytest_runtest_logreport` event ordering under pytest-xdist; verify CI environment detection across GitHub Actions / Jenkins. (Relevant for SEED-002 in v1.5.)

Open design questions deferred to plan-phase decisions (not roadmap blockers): URL-style judge kwarg vs split kwargs (Phase 28 decides); `gen-test-classes` library callable vs CLI-only (Phase 28 decides per "v1.4 requires CLI install" carve-out); fixture-rename one-milestone deprecation window (Phase 26 decides).

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260506-qxs | Diagnostic spike — homelab-mcp host-state surface (recon for v1.1 isolation) | 2026-05-07 | 23cc6e1 | [260506-qxs-diagnostic-spike-identify-what-user-visi](./quick/260506-qxs-diagnostic-spike-identify-what-user-visi/) |
| 260507-j6i | Enrich `MCP server command not on PATH` error with MCPTF_CONFIG_FILE / config.example.yaml hint | 2026-05-07 | bfc1e65 | [260507-j6i-enrich-mcp-server-not-on-path-error-with](./quick/260507-j6i-enrich-mcp-server-not-on-path-error-with/) |
| 260507-n0g | Safe-by-default tool skips in `config.example.yaml` (55 new skip entries; only `list_keyring_credentials` + `suggest_deployments` enabled) | 2026-05-07 | 0d8337b | [260507-n0g-safe-by-default-tool-skips](./quick/260507-n0g-safe-by-default-tool-skips/) |
| 260508-p0b | v1.1.1 hotfix: filter `tools.<name>.skip:true` at parametrize time so skipped tools are absent from collection (not runtime-SKIPPED 10x each); 691 → 133 collected under config.example.yaml | 2026-05-08 | 509daee | [260508-p0b-fix-v1-1-skip-doesnt-filter-parametrize-](./quick/260508-p0b-fix-v1-1-skip-doesnt-filter-parametrize-/) |
| 260512-dcs | Migrate example configs to schema v2 (closes CLEAN-03 BLOCKER from v1.2 milestone audit; examples/homelab-mcp.yaml + config.example.yaml flipped to `version: 2`, `.env` precedence comment stripped) | 2026-05-12 | 814d743 | [260512-dcs-flip-example-config-version-1-to-2-close](./quick/260512-dcs-flip-example-config-version-1-to-2-close/) |
| 260513-chh | Fix `_session_needs_preflight` nodeid path mismatch — invert predicate to live-scope allowlist (`tests/contract/`, `tests/sdet/`); 9-case regression test added; framework unit tests no longer trigger live MCP preflight | 2026-05-13 | 1ba103b | [260513-chh-fix-session-needs-preflight-nodeid-path-](./quick/260513-chh-fix-session-needs-preflight-nodeid-path-/) |

## Deferred Items

Items acknowledged at v1.0 / v1.1 close and carried into v1.2+ scope:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| upstream-fix | `homelab-mcp` `list_registered_servers` description rewrite (would let TEST-06 pass against the original target tool) | Open | v1.0 close (2026-05-07) |
| upstream-fix | Framework default behavior contribution to homelab-mcp inputSchema null trigger — `_tool_factory.py:99` `model_dump(mode='json')` emitted `null` for unset optional Pydantic fields, conflicting with upstream `type: 'string'` declarations. Resolution: `exclude_unset=True` shipped in Phase 24; SDET-omitted optionals stay off the wire. SDETs explicitly passing `field=None` to test null-handling still trigger the upstream bug — that is SEED-022-by-design (see Row B and memory `project_framework_primitives_sdet_safety_principle.md`). | Resolved | Phase 19 close (2026-05-13) → resolved Phase 24 (2026-05-15) |
| upstream-fix | Upstream homelab-mcp inputSchema bug — Proxmox tools (and likely others) declare optional fields as `type: 'string'` (no `'null'`) but default them to `null`. SDETs explicitly testing null-handling hit `Input validation error: None is not of type 'string'` (e.g. via `_CpuBumpManageVmParams(extra='allow')` pattern in `docs/SDET-AUTHORING.md`). Server should declare `type: ['string','null']` or strip null-valued keys before its own jsonschema check. | Open | Phase 19 close (2026-05-13) |
| testing-scaffold | Automated cross-platform SIGINT UAT (Get-Process / pgrep + programmatic SIGINT helper) | Open | v1.0 close (2026-05-07) |
| open-source-prep | Scrub homelab IP from README (05-SECURITY.md AR-05-12) | Partially absorbed into v1.2 Phase 12 (CLEAN-02..04) | v1.0 close (2026-05-07) |
| open-source-prep | Scrub homelab-specific captures from `.planning/` (05-SECURITY.md AR-05-15) | Open — only triggers if/when repo goes public | v1.0 close (2026-05-07) |
| process-hygiene | Backfill 04.1-VERIFICATION.md (UAT.md status:complete is current evidence of record) | Open — optional | v1.0 close (2026-05-07) |
| seed | SEED-001 — Replace rubric-style judge with full agent tool-use loop | dormant | v1.1 close (2026-05-08) |
| seed | SEED-002 — Tool-level parallelism via pytest-xdist with read/write resource markers | dormant — v1.5 cohort (deferred from v1.4) | v1.1 close (2026-05-08) |
| seed | SEED-003 — Dynamic judging protocol — rubrics as data, not code | dormant — v1.5 | v1.1 close (2026-05-08) |
| seed | SEED-004 — Stateful tool testing with resource setup/teardown | activated → Phase 19 (v1.3) | v1.1 close (2026-05-08) |
| seed | SEED-005 — OpenAI-compatible judge backend as the unifier (local-first / hosted-opt-in) | dormant — v1.5 (deferred from v1.4) | v1.1 close (2026-05-08) |
| seed | SEED-006 — Config loading safety + opt-in tool selection | activated → Phase 13 (v1.2) | 2026-05-09 (v1.2 framing) |
| seed | SEED-007 — Vibe-coded MCP user persona reframe | activated → Phase 12 (v1.2) | 2026-05-09 (v1.2 framing) |
| seed | SEED-008 — Reporter UX overhaul — pre-run digest + --explain flag | activated → Phase 16 (v1.2) | 2026-05-09 (v1.2 framing) |
| seed | SEED-009 — Doc & example cleanup phase (v1.2) | activated → Phase 12 (v1.2) | 2026-05-09 (v1.2 framing) |
| seed | SEED-010 — Separate operator-facing tests from framework self-tests | activated → Phase 15 (v1.2) | 2026-05-09 (v1.2 framing) |
| seed | SEED-011 — Hybrid runner with domain-language UI | activated → Phase 14 (v1.2) | 2026-05-09 (v1.2 framing) |
| seed | SEED-014 — Programmatic SDET test authoring (param/response classes + scenario API) | activated → Phases 17–21 (v1.3) | 2026-05-12 (v1.3 framing) |
| seed | SEED-015 — Library mode / pytest plugin delivery | activated → Phases 25–30 (v1.4) | 2026-05-15 (v1.4 framing) |
| seed | SEED-023 — Rename `sdet` → `test_code` for public-API freeze | activated → Phase 25 (v1.4) | 2026-05-15 (v1.4 framing) |
| defer | Phase 16 D-11 `--debug` per-judge breakdown block | dormant — v1.5 cohort with SEED-003 | v1.2 close (2026-05-12) |
| live-uat | Phase 13 live-stack UAT (v2 config + migration walkthrough) | Open — closes in v1.4 Phase 30 (CLOSE-04 carry-forward) | v1.2 close (2026-05-12) |
| live-uat | Phase 14 live-stack UAT (test_runner_live_smoke.py + visual domain UI checks) | Open — closes in v1.4 Phase 30 (CLOSE-04 carry-forward) | v1.2 close (2026-05-12) |
| docs-polish | EXTENDING.md WR-01: line-range citation `_isolation.py:33-36` should be `36-39` (11-REVIEW.md) | Absorbed into Phase 12 (CLEAN-01 sweep) | v1.1 close (2026-05-08) |
| docs-polish | EXTENDING.md IN-01: "five entries" framing for `_PASSTHROUGH_ALLOWLIST` (4-tuple + separate `_MCP_PREFIX`) (11-REVIEW.md) | Absorbed into Phase 12 (CLEAN-01 sweep) | v1.1 close (2026-05-08) |
| seed-defer | Hello-world MCP server for CI/CD coverage — tiny in-tree MCP with hand-crafted tools (required/optional params, scalars/arrays, declared/undeclared outputSchema) lets CI run a real end-to-end "every discovered tool gets wrapped" pass without operator infrastructure. | Open — future v1.x phase | Phase 20 reframe (2026-05-13) |
| deferred-resolved | Phase 19 D-02 (CPU-cores bump impossible via `manage_proxmox_vm` lifecycle-action-only tool) — defer to Phase 20 substitution decision | Resolved-by-deletion (Phase 20) — the dogfood file hosting the substitution was deleted in Phase 20 per D-04; no substitution needed | v1.3 Phase 19 close → resolved Phase 20 (2026-05-13) |
| live-uat | README §`## SDET scenarios` PASS-sample re-capture (Plan 24-02 Task 3a/3b) — Proxmox credential keyring is not reachable from the agent's PowerShell session even after `MCPTF_DOGFOOD_PROXMOX_HOST=192.168.10.20` is set; homelab-mcp reports `No Proxmox credentials found for 192.168.10.20`. The README §`## SDET scenarios` snapshot still shows the pre-Phase-24 FAIL output even though the framework default no longer triggers it; intro paragraph (L266-L272) and post-snapshot framing paragraph (L420-L427) remain in their pre-Plan-24-02 state. Tasks 1+2 of Plan 24-02 committed (SERIALIZER-DOC-01 row + SDET-AUTHORING soften). Re-snapshot manually when running in an operator shell that has keyring access — see Phase 21 D-14 manual-snapshot precedent. | Open — closes in v1.4 Phase 30 (CLOSE-04 carry-forward) | Phase 24 Plan 24-02 close (2026-05-15) |

### Acknowledged at v1.3 milestone close (2026-05-15)

Items acknowledged via the v1.3 close pre-flight artifact audit and deferred:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| uat | Phase 18 18-UAT.md — 7 pending scenarios (testing status); SDET surface UAT not fully exercised against live homelab-mcp | Open — closes opportunistically against live homelab-mcp | v1.3 close (2026-05-15) |
| verification | Phase 13 13-VERIFICATION.md — `human_needed` (v1.2 carryover) | Open — closes in v1.4 Phase 30 (CLOSE-04) | v1.3 close (2026-05-15) |
| verification | Phase 14 14-VERIFICATION.md — `human_needed` (v1.2 carryover) | Open — closes in v1.4 Phase 30 (CLOSE-04) | v1.3 close (2026-05-15) |
| verification | Phase 17 17-VERIFICATION.md — `human_needed` (live homelab-mcp at ~70 tools + `uv run pyright` on real generated dir) | Open — closes in v1.4 Phase 30 (CLOSE-04) | v1.3 close (2026-05-15) |
| quick_task | 260508-p0b-fix-v1-1-skip-doesnt-filter-parametrize — quick-task file missing (pre-v1.3 leftover) | Open — file missing; carry to next milestone triage | v1.3 close (2026-05-15) |
| quick_task | 260512-dcs-flip-example-config-version-1-to-2-close — quick-task file missing (pre-v1.3 leftover) | Open — file missing; carry to next milestone triage | v1.3 close (2026-05-15) |
| quick_task | 260513-chh-fix-session-needs-preflight-nodeid-path — quick-task file missing (pre-v1.3 leftover) | Open — file missing; carry to next milestone triage | v1.3 close (2026-05-15) |
| seed | 18 dormant seeds (SEED-001/002/003/005/006/007/008/009/012/013/015/016/017/018/021/023) + 2 active-but-already-shipped (SEED-010 absorbed Phase 15, SEED-011 absorbed Phase 14) | Backlog parking lot — SEED-015 + SEED-023 activated → v1.4 (2026-05-15); 16 remain dormant | v1.3 close (2026-05-15) |

## Session Continuity

Last session: 2026-05-20T01:22:07.958Z
Stopped at: Phase 30 Plan 30-04 dogfood verification complete
Resume next: `/gsd-verify-phase 30` then `/gsd-complete-milestone v1.4`
