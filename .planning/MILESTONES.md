# Milestones — mcp_test_framework

## v1.3 Homelab Scenario Testing (Shipped: 2026-05-15)

**Phases completed:** 9 phases, 42 plans, 62 tasks

**Key accomplishments:**

- Found during:
- File modified:
- Closed the renderer side of Phase 18 by hooking the JUnit XML parser to ToolCallError-attached user_properties (D-09 / D-10), shipping the SDET-flavored pre-run digest with cli.py dispatch (D-06), and adding the structured `--- ToolCallError dump ---` block to the `--debug` appendix (D-11). Strategy 1: zero ToolVerdict surface change -- the D-11 appendix re-parses the XML rather than threading dump strings through the dataclass.
- Shipped the `tests/sdet/` scaffolding (package marker + SDET-only conftest with the D-09 / D-11 `pytest_exception_interact` hook + 2 end-to-end sanity tests) and the unit-test harness pinning the hook's strict-ToolCallError discipline. The live `uv run pytest tests/sdet/test_basic_call.py` exits 0 (2/2) against `uvx homelab-mcp`, proving the whole Phase 18 surface composes end-to-end through the public `mcp_test_framework.sdet` barrel.
- Pinned every Phase 18 decision (D-01 through D-11, plus Plan 18-04's `__all__` contract) with framework self-tests under `tests/framework/unit/`. Four-file deliverable: two new files (`test_tool_call_error.py`, `test_sdet_renderer.py`) and two extended files (`test_sdet_fixtures.py`, `test_sdet_cli.py`). Task 5 (update `test_tool_factory.py`) was a no-op because Plan 18-02 had already replaced the `NotImplementedError` test with the new `_ACTIVE_CLIENT`-based contract.
- 1. [Rule 1 - Bug] Ballot-x glyph (`✗`) violated zero-emoji constraint
- SdetConfig sub-model with required `generated_root: Path` lands on top-level Config as a no-default field; missing key routes through the existing SAFE-03 mapper with no new code path; both example YAMLs and the config-init scaffold ship the new key with the recommended `tests/sdet/_generated` convention.
- `gen-sdet-classes` and `mcp_session` both consume `cfg.sdet.generated_root` directly; the fixture's load mechanism switches from `importlib.import_module` against the framework namespace to `importlib.util.spec_from_file_location` with `submodule_search_locations` against the on-disk slug dir. The framework no longer requires generated code to live under its own `src/` tree.
- Three tests reworked off the `mcp_test_framework.sdet.generated.homelab_mcp` import path using the D-09 HYBRID strategy: synthetic codegen + spec-loader for the two unit-test files; live-regen + on-disk spec-loader (with collection-safe module skip) for the README parity scenario. After this plan ships, nothing under `tests/` imports from the in-tree `src/mcp_test_framework/sdet/generated/` package — Plan 04 can delete that tree safely.
- `src/mcp_test_framework/sdet/generated/` is gone from the working tree and the git index. The framework's `src/` tree now contains zero SUT-specific code; SEED-022 is structurally enforced. Phase 21.1 capstone delivered in one atomic commit: 60 deletions + 3 doc/test-docstring updates + 1 new docs subsection guiding operators through the new config setup.
- Operator-facing `--help` and the `src/mcp_test_framework/cli.py` source stop leaking internal planning-system provenance — 52 ID hits and 37 `Phase NN` prefixes scrubbed down to zero, all five Typer command docstrings still operator-readable.
- Phase 23 close-gate is GREEN. `uv run pytest tests/framework/ --tb=no -q` exits 0 with `575 passed, 1 skipped, 17 deselected, 2 xfailed in 15.19s` — failed==0 and errored==0 (D-07/D-08 satisfied). Zero `src/mcp_test_framework/` changes across the entire phase (D-02 invariant holds end-to-end). v1.3 close inherits a green framework suite.
- `tool().call()` now uses `model_dump(mode='json', exclude_unset=True)` so SDET-omitted optional fields stay off the MCP wire while explicit `field=None` still flows `null` (SEED-022 user-intent discriminator preserved); locked by three new payload-asserting unit tests + a renamed kwargs-spy test.
- `docs/SDET-AUTHORING.md` §`## The inputSchema workaround` framing softened (the `_CpuBumpManageVmParams(extra='allow')` pattern is now documented as the explicit-null-test escape hatch only, not the always-needed default for Proxmox calls); SERIALIZER-DOC-01 row added to REQUIREMENTS.md. The README §`## SDET scenarios` PASS-sample re-capture (Tasks 3a/3b) is deferred to a manual UAT via the plan's `regen-failed` partial-completion contract — Proxmox keyring credentials are unreachable from the agent shell that runs under this executor.
- Split STATE.md L155 `homelab-mcp inputSchema` Deferred Items row into Row A (Resolved, framework-side fix shipped Phase 24) + Row B (Open, narrower-scope upstream bug residue) so the audit trail records the partial resolution without erasing what remains.

---

## v1.2 — Operator-First Design

**Shipped:** 2026-05-12
**Phases:** 5 (12, 13, 14, 15, 16)
**Plans:** 30 / 30 complete
**Quick tasks:** 1 (260512-dcs — CLEAN-03 gap closure)
**Requirements:** 31 / 31 satisfied (1 carry-forward live UAT pair in phases 13 & 14)
**Source diff:** +37,100 / −1,928 across 168 files
**Timeline:** 2026-05-09 → 2026-05-12 (4 days, 236 commits)
**Audit:** [v1.2-MILESTONE-AUDIT.md](milestones/v1.2-MILESTONE-AUDIT.md) — status `tech_debt` (CLEAN-03 BLOCKER closed pre-completion)

**Theme:** Reframe the framework around the operator persona — someone testing an MCP server they didn't write — by making every default behavior, error message, and output surface speak the operator's domain language instead of pytest/framework internals.

**Key accomplishments:**

- **Phase 12 — Doc & persona foundation.** Stripped planning-artifact IDs from operator-facing docs; split `config.example.yaml` into a 3-pattern placeholder template + a `examples/homelab-mcp.yaml` worked reference (history preserved via `git mv`); shipped the `config-init` scaffold + `_emit_operator_error` helper across all 8 cli.py/fixtures.py error surfaces; added the "Testing an MCP server you didn't write" persona reframe across README and EXTENDING.
- **Phase 13 — Config safety & opt-in tool selection.** Inverted `tools:` from skip-list to allowlist (TOOLCFG-06 None=run-all-rubrics, []=opt-out, subset=literal); added `--config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud` precedence; bumped schema `version: 1 → 2` with a LOCKED migration error citing `config-init`; dropped `.env` and the env-overlay entirely (eliminating the silent-override class of bugs).
- **Phase 14 — Hybrid runner with domain UI.** Rewrote `cli.py:run` to invoke pytest as a child subprocess with internal tempfile JUnit XML capture; new `src/mcp_test_framework/_runner.py` module owns the MCP-domain UI (header / per-tool rows / summary line); shipped the `-q` / default / `--debug` verbosity ladder (orthogonal, additive, never reshapes the layer below); `--raw` escape hatch preserves the pytest framing for maintainers while keeping the config pre-flight gate.
- **Phase 15 — Operator vs framework test surface split.** `git mv` `tests/` into `tests/contract/` (operator-relevant) and `tests/framework/` (self-tests); runner default scope is `tests/contract/`, `--with-framework` appends (never replaces); banned-imports and snippet checks remain enforced under `tests/framework/`.
- **Phase 16 — Reporter UX overhaul.** 8-line pre-run digest emitted before pytest (server / discovered / running / skipping / judges / test-plan totals) — replaces pytest's misleading "N collected, M deselected" framing; `--explain` flag emits grep-able N+5-line skip rationale at homelab-mcp scale (~70 tools); post-run aggregation per-tool + per-judge reasoning surface on FAIL rows; D-12 height-bounded digest passes capsys test at N=70.

**v1.2 thesis validated:** An operator with no framework internals knowledge can `cd <my-mcp-project> && mcp-test-framework config-init -o config.yaml && (edit allowlist) && mcp-test-framework run` and get a clean domain-language experience start to finish.

**Carry-forward debt:**

- Phase 13: live-stack UAT — E2E run with real MCP server + v2 config; migration doc walkthrough (needs `homelab-mcp` on PATH).
- Phase 14: live-stack UAT — `test_runner_live_smoke.py` with `-m live_homelab` + visual domain UI checks (needs live MCP + Ollama).
- Phase 16: D-11 `--debug` per-judge breakdown block deferred to v1.3 per CONTEXT.md.
- 15 plant-seed items deferred to v1.3+ (see PROJECT.md Deferred section).

---

A running log of shipped versions. Each entry summarizes what was delivered; full archives live in `.planning/milestones/v[X.Y]-*.md`.

---

## v1.1 — Multi-Tool + Isolation + JUnit

**Shipped:** 2026-05-08
**Phases:** 6 (06, 07, 08, 09, 10, 11)
**Plans:** 17 / 17 complete
**Requirements:** 25 / 25 satisfied (audit-clean: W-1, W-3, W-4, W-5, W-6 closed in Phase 11)
**Source diff:** +2,390 / −45 across 17 files (`src/`, `tests/`, `docs/`)
**Codebase:** 5,784 LOC Python
**Timeline:** 2026-05-07 → 2026-05-08

**Delivered:** Generalized the framework from one-tool-per-run to N-tools-per-run, with per-session host-state isolation, declarative per-tool config, and JUnit XML output for CI ingestion.

**Key accomplishments:**

- **Per-session host-state isolation (Phase 06)** — New `_isolation.py` module + `_isolated_home` session fixture redirect `HOME`/`USERPROFILE` to a per-session tempdir, inject `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null`, and lock env passthrough to a 4-entry allowlist + `MCP_*` prefix. ISOL-03 verified empirically: all 3 sha256 hashes of `~/.homelab_mcp/{credential_registry,known_hosts,migration_state}` byte-identical pre/post run; zero tempdir orphans.
- **Multi-tool discovery & parameterized testing (Phase 07)** — `pytest_generate_tests` hook + indirect `target_tool` parametrize discover and exercise every tool the connected MCP server advertises in a single test invocation. Per-tool test IDs render as `<test>[<tool>]` for both terminal output and JUnit XML.
- **Per-tool config registry (Phase 08)** — `tools.<tool_name>` config blocks support `skip` / `skip_reason` / `call_arguments` / `judges` selection, validated by Pydantic with `extra="forbid"` and `version: 1`. `setup:` / `depends_on:` fields reserved for SEED-004 forward-compat. New `mcp-test-framework config-init` Typer subcommand scaffolds a worked `config.example.yaml`.
- **JUnit XML output & per-tool reporting (Phase 09)** — `--junit-xml=PATH` Typer flag, new `_reporter.py` pytest plugin aggregates per-tool PASS/FAIL/SKIP into a terminal summary section, and 29 unit tests + 3 live-marked subprocess tests pin the OUTPUT-01..03 contracts (XML well-formedness, `[<tool>]` suffix, always-on per-tool summary).
- **v1.1 documentation (Phase 10)** — README adds Per-tool configuration / Isolation guarantee / CI integration sections (copy-pasteable GitHub Actions snippet); `docs/EXTENDING.md` adds an "Add a new MCP tool target" walkthrough. Snippet-correctness regression suite pins README examples against drift.
- **v1.1 cleanup & verification hygiene (Phase 11)** — Closed all 5 paper-only audit gaps from `v1.1-MILESTONE-AUDIT.md`: backfilled `09-VERIFICATION.md` (W-1), added EXTENDING.md "Environment passthrough allowlist" section absorbing the `_isolation.py` runtime warning + WR-04 Branch B rationale (W-3, W-6), fixed REQUIREMENTS.md traceability drift (6 Pending → Complete; W-4), corrected ROADMAP.md drift (`mtimes` → `sha256`, Phase 07 row; W-5).

**Known deferred items at close:** 5 SEEDs (dormant; carried into v1.2+ scope), 2 docs-polish nits in EXTENDING.md (line-range citation, "five entries" framing) — see STATE.md `## Deferred Items`.

**Archives:** [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md) · [v1.1-REQUIREMENTS.md](milestones/v1.1-REQUIREMENTS.md) · [v1.1-MILESTONE-AUDIT.md](milestones/v1.1-MILESTONE-AUDIT.md)

---

## v1.0 — MVP

**Shipped:** 2026-05-06
**Phases:** 7 (01, 02, 02.1, 03, 04, 04.1, 05)
**Plans:** 22 / 22 complete
**Requirements:** 29 / 29 satisfied
**LOC:** ~3,562 Python (`src/` + `tests/`)
**Commits:** 166
**Timeline:** 2026-05-04 → 2026-05-06 (3 days)

**Delivered:** A `pytest`-runnable test framework that drives one MCP tool end-to-end (schema → call → judge) over stdio against `homelab-mcp`, with `mcp-test-framework run|list-tools|version` CLI; live green at 67 passed, exit 0.

**Key accomplishments:**

1. End-to-end pytest framework — `uv run mcp-test-framework run` produces `67 passed, exit 0` against live `homelab-mcp` (via `uvx`) + Ollama (`qwen3.6:latest` @ `127.0.0.1:11434`)
2. Black-box rule mechanically enforced — `ruff TID251` ban + `tests/conftest.py` `sys.modules` guard + dedicated banned-imports unit test
3. Async stdio MCP client with clean teardown — owner-task + `anyio.Event` lifecycle (Phase 04.1 fix); zero leftover `homelab-mcp.exe` on Windows
4. Ollama judge with qwen3 belt-and-braces — `<think>` strip, `format:json`, `temperature:0`, `keep_alive:30m`, parse-failure fallback preserving `raw_response`; cold-start timeouts wrapped
5. `Judge` Protocol seam shipped in MVP — zero-cost backend swap post-MVP (JUDGE-01)
6. Typer CLI with three commands — `run` (CLI-01), `list-tools` (CLI-02), `version` (CLI-03); SIGINT exit 130 with explicit handler (WR-05); README + `docs/EXTENDING.md`
7. Layered config — `CLI > env > YAML > defaults` via `pydantic-settings[yaml]`, frozen `Config` with custom bare-name nested env source

**Decimal phases (mid-milestone insertions):**

- Phase 02.1: Close Phase 2 verification gaps (config + UAT) — reconciled `uvx homelab-mcp` invocation, ran live UAT, flipped Phase 2 to passed
- Phase 04.1: McpTestClient session-teardown fix — owner-task + `anyio.Event` rewrite resolved `RuntimeError: Attempted to exit cancel scope in a different task`

**Overrides accepted (3 total, all justified):**

- DEF-04-03-A: `list_registered_servers` description fails rubric → resolved by config switch to `list_keyring_credentials` in Phase 5; framework working as designed; upstream description fix tracked for v2
- DEF-04-03-B: `anyio` cancel-scope teardown error → reassigned to and resolved in Phase 04.1
- OPS-03 PARTIAL PASS (Phase 5) → functionally superseded by WR-05 fix + 05-UAT.md test 8 (live SIGINT exit 130 directly observed); override remains in audit trail

**Known deferred items (carried to v2):**

- Upstream `homelab-mcp` `list_registered_servers` description fix (JUDGE/GEN territory)
- Automated cross-platform SIGINT UAT scaffolding (would need `Get-Process`/`pgrep` + programmatic SIGINT delivery helper)
- Open-source pre-flight scrub: homelab IP from README + homelab-specific captures from `.planning/` (only triggers if/when the repo goes public)

**Process gap (documentation hygiene, not a coverage gap):**

- Phase 04.1 missing 04.1-VERIFICATION.md — UAT.md `status:complete` is the load-bearing evidence and is referenced by Phase 5's threat model and 05-UAT.md test 8

**Archives:**

- `.planning/milestones/v1.0-ROADMAP.md` — full phase + plan details
- `.planning/milestones/v1.0-REQUIREMENTS.md` — final state of 29 v1 requirements (all complete)
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` — pre-close audit report (passed; 29/29 reqs, 7/7 phases, 8/8 flows)

**Tag:** `v1.0`
