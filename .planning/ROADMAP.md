# Roadmap: mcp_test_framework

## Milestones

- ✅ **v1.0 MVP** — Phases 01–05 (shipped 2026-05-06) — see [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Multi-Tool + Isolation + JUnit** — Phases 06–11 (shipped 2026-05-08) — see [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Operator-First Design** — Phases 12–16 (shipped 2026-05-12) — see [v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Homelab Scenario Testing** — Phases 17–24 (shipped 2026-05-15) — see [v1.3-ROADMAP.md](milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 Library Mode Delivery** — Phases 25–30 (shipped 2026-05-22) — see [v1.4-ROADMAP.md](milestones/v1.4-ROADMAP.md)

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

### 🚧 v1.5 (Next) — TBD

Milestone not yet scoped. Run `/gsd-new-milestone` to begin questioning → research → requirements → roadmap.

Carry-forward items expected to land in v1.5 (see MILESTONES.md `v1.4 → Carry-forward debt`):
- Drop v1.4-introduced deprecation shims (sdet package shim, --sdet/gen-sdet-classes CLI shims, cfg.sdet.* alias, MCPTF_CONFIG_FILE env-var route, unprefixed fixture aliases, mcp-test-framework console-script alias).
- Promote backlog 999.1 / 999.2 / 999.3 / 999.4 / 999.5 as scope allows.

## Progress

**Execution Order (v1.4):**
Phases execute in numeric order: 25 → 26 → 27 → 28 → 29 → 30. Decimal phases (e.g., 27.1) reserved for INSERTED urgent fixes between integer phases.

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
| 25. Public-API rename (SEED-023) — sdet → test_code | v1.4 | 6/6 | Complete    | 2026-05-16 |
| 26. Packaging foundation -- entry-point + py.typed + dist-name + plugin skeleton | v1.4 | 5/5 | Complete    | 2026-05-16 |
| 27. register() API + contracts sub-package + test extraction | v1.4 | 5/5 | Complete   | 2026-05-17 |
| 28. Codegen output path (CODEGEN) | v1.4 | 4/4 | Complete   | 2026-05-17 |
| 29. Live domain-UI reporter plugin | v1.4 | 3/3 | Complete    | 2026-05-17 |
| 30. CLI demotion + carry-forward UAT closure + docs rewrite | v1.4 | 4/4 | Complete   | 2026-05-20 |

## Backlog

### Phase 999.1: Per-test-bucket / per-judge opt-in granularity in ToolConfig (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

**Context (captured 2026-05-19 during Phase 30 UAT-1):** `ToolConfig.skip: true` is whole-tool only. The operator wants per-bucket granularity so the output-conformance bucket (`test_empty_args_call_returns_non_error`, `test_result_has_content_or_structured`, `test_text_content_parses_as_json`) can be skipped for tools whose inputSchema declares required fields, while the deterministic schema bucket and the LLM judge bucket still run. Current workarounds: (a) `skip: true` on the whole tool — loses judge signal; (b) author `call_arguments:` per tool. Proposal: add `ToolConfig.skip_buckets: list[Literal["schema","judge","output"]] = []` so the operator can opt out by bucket. Also consider an auto-skip-output-when-required heuristic (off by default, opt-in via top-level flag) so the framework can detect required-field tools and silently skip the empty-args bucket without per-tool enumeration. SEED-022 (framework primitives; SDET owns safety) stays intact — the operator still chooses; the framework just gets a more precise lever.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.2: Codegen-driven parameter-test generation for required-field tools (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

**Context (captured 2026-05-19 during Phase 30 UAT-1):** The output-conformance bucket calls every enabled tool with `tool_config.call_arguments` (defaults to `{}`). For tools whose inputSchema declares `required: [...]`, the empty-args call is rejected upstream — the test is structurally non-meaningful unless the operator hand-authors `call_arguments:` per tool. Phase 17 / SEED-014 already ships codegen that derives `<ToolName>Params` Pydantic classes from each tools inputSchema. Proposal: extend `gen-test-classes` to ALSO emit a `tests/test_code/_generated/<tool>_call_smoke.py` per required-field tool — a typed SDET scenario that constructs `<ToolName>Params(...)` from inputSchema example values (or operator-supplied `examples:` blocks) and calls the tool through `tool("name").call(params)` with the Phase 24 `exclude_unset=True` serializer. Authoring story: the operator drops `examples:` into `config.yaml` or `pyproject.toml`, `gen-test-classes` reads them, generated scenarios show up under `tests/test_code/` and run in the test-code surface. Codegen owns the boilerplate; the operator owns the example values (SEED-022 respected). Adjacent: a CLI subcommand `mcp-contracts list-required` that reads inputSchema + emits the example-values template the operator needs to fill in. Pairs with backlog 999.1 (per-bucket skip) — operator can keep the schema+judge buckets running while output-bucket coverage shifts to codegen-generated SDET scenarios.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.3: Always-on host isolation blocks live-UAT + SDET credential paths (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

**Context (captured 2026-05-19 during Phase 30 UAT-1 + UAT-2 closure):** `_isolation.py` documents itself as `Isolation is ALWAYS-ON. No toggle, no --no-isolation CLI escape hatch.` On every spawn it (a) strips operator env to an allowlist, (b) redirects HOME / USERPROFILE / TEMP to a temp dir, (c) sets `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null`. This is great for hermetic contract testing but **breaks every live-stack UAT that needs real credentials**: `homelab-mcp` spawned inside the framework cannot reach the operators `~/.homelab_mcp/` config or Proxmox keyring entry, even though `uvx homelab-mcp credentials list` from the operators shell sees them. Same property will block SDET-authored scenarios that exercise real infrastructure.

**Constraint locked by operator:** No keyring faking. We will not add a credential-mock layer to the framework.

**Proposed direction (NOT locked):** Make isolation opt-in instead of always-on. A top-level config field like `host_isolation: strict | passthrough` defaulting to `strict` (todays behavior) with `passthrough` allowing the operator to inherit their hosts env + HOME for live-UAT runs. The operators explicit choice = operators safety responsibility (SEED-022). Likely cost: `passthrough` mode must serialize subprocess spawns (no parallel xdist) because operator credentials become a shared resource -- single MCP session at a time. Acceptable trade for the live-UAT story. Also flushes a class of related gaps: bare `Config()` callers (mcp_config fixture before commit 588ffd1, the test-code scenarios `_load_generated_homelab_mcp` at module import time) all depend on host env -- under passthrough mode the operators MCPTF_CONFIG_FILE survives the spawn naturally; under strict mode the plugin stash route is the only correct path. Decide both axes together so future Config() bare callers dont silently leak operator env in strict mode.

**Adjacent observation (homelab-mcp upstream, not framework):** During the same UAT-1 run the scenario sweep code logged `list_proxmox_resources failed: vm is not one of [qemu,lxc,node,storage,pool]` -- the scenario passes an invalid resource_type. Not blocking 999.3 but worth a one-line fix when the live-UAT path is unblocked. Operator captured in UAT notes for upstream reporting.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.4: Drop v1-schema support — remove migration command + README references (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

**Context (captured 2026-05-19 during Phase 30 UAT-3 retire):** Framework has never been published; there are no live operators carrying v1-schema configs. The v1 -> v2 migration code path was preserved through v1.2/v1.3/v1.4 in case external operators existed; UAT-3 was the planned live verification of that path. Decision: there is no one to migrate. Drop v1-schema support entirely instead of carrying it forward. Decommission-by-deletion replaces UAT-3.

**Scope of removal (inventoried 2026-05-19):**

- `src/mcp_test_framework/config.py:74` — `version: int = 2` field stays, but the `_validate_version` validator at line 193-201 (`config version {v} not supported by this build, expected 2`) can be tightened (still useful as a rejection for typos, but the message no longer references migration).
- `src/mcp_test_framework/cli.py:252-307` — the entire v1→v2 migration message block in the operator-error mapper (the `# Locked v1 -> v2 migration message` section, the "matters: in v1 a tool with no entry runs by default, in v2 it skips" line, the `docs/MIGRATION-v1-to-v2.md` cross-reference). Delete the message + the special-case detection that triggers it.
- `docs/MIGRATION-v1-to-v2.md` — delete the whole doc.
- `docs/ERROR-STYLE.md` — scrub MIGRATION-v1-to-v2 references.
- `README.md §Configuration` — remove the migration callout / hint, reference v2 directly.
- `docs/LIBRARY-MODE.md` — sweep for migration references; library-mode docs should describe v2 only.
- Any framework self-tests that pin the v1-rejection message text need to either delete the test (preferred) or relax to "rejects unsupported version with a clean operator-tone error" without asserting the migration verbiage.

**Risk acknowledgement:** This is one-way — once v1-schema rejection is generic ("unsupported version, run config-init"), an operator who somehow has a v1 config gets less specific guidance. Acceptable given there are no such operators.

**Pairs with:** Retired UAT-3 in `.planning/phases/30-cli-demotion-carry-forward-uat-closure-docs-rewrite/30-UAT.md` (closed-by-deletion). When 999.4 lands, the UAT entry can be left as historical evidence of the decision.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

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

**Workaround for the current run:** `Remove-Item env:MCPTF_CONFIG_FILE` (PowerShell: `$env:MCPTF_CONFIG_FILE = $null` -- wait, in PowerShell to unset use `Remove-Item env:MCPTF_CONFIG_FILE`; setting to empty string keeps it set per memory `project_worktree_config.md`) and re-run library mode -- the SkipFilter test should pass.

**Proposed resolution scope:**
- Reproduce in a clean shell to confirm the env-var dependency (the diagnosis above is inferred, not verified).
- Add a `monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)` to a session-scoped autouse fixture under `tests/framework/conftest.py` that strips operator env from every framework self-test by default. SDET-authored tests opt back in if needed.
- If the root cause IS pydantic-settings deep-merging, audit every framework self-test that constructs Config with a custom `tools` dict and either pin them via `Config(yaml_file=tmp_yaml)` (explicit YAML source) or strip the env via monkeypatch.
- Pairs naturally with 999.3 (always-on isolation) -- both stem from the same problem: framework code paths leaking host env into spawn / test surfaces. 999.3 is operator-facing; 999.5 is framework-internal.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)
