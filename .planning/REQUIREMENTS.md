# mcp_test_framework — v1.5 Requirements

**Milestone:** v1.5 Shim Retirement + Operator Escape Hatches
**Goal:** Retire v1.4-introduced deprecation shims (locked at v1.5 expiry), decommission the unused v1-schema migration path, and ship the two operator escape hatches (per-bucket skip + isolation passthrough) that v1.4 dogfood revealed as needed.
**Defined:** 2026-05-22

---

## Active Requirements

Grouped by category. Each REQ is atomic, testable, and user-centric. Traceability to phases populated by the roadmapper.

### SHIM — Drop v1.4-introduced deprecation shims

All shims below were introduced in v1.4 with one-milestone deprecation windows explicitly locked to expire in v1.5 (see PROJECT.md "Carry-forward debt" and MILESTONES.md v1.4 entry).

- [ ] **SHIM-01**: Operator can no longer `from mcp_test_framework.sdet import ...` — the `sdet` package shim is removed; import raises `ModuleNotFoundError` with operator-tone message pointing at `mcp_test_framework.test_code`.
- [ ] **SHIM-02**: Operator can no longer pass `--sdet` to `mcp-contracts run` — flag removed; UsageError points at `--test-code`.
- [ ] **SHIM-03**: Operator can no longer invoke `gen-sdet-classes` — CLI command removed; UsageError points at `gen-test-classes`.
- [ ] **SHIM-04**: Operator's `config.yaml` using the legacy `sdet:` key (Pydantic `Field(alias=...)`) is rejected — `cfg.sdet.*` alias removed; `extra="forbid"` model surfaces an operator-tone migration error pointing at `test_code:`.
- [ ] **SHIM-05**: Operator can no longer point the framework at a config via `MCPTF_CONFIG_FILE=...` env var — env-var route removed; pytest ini key `[tool.pytest.ini_options] mcp_config_file = PATH` is the sole library-mode config route; `mcp-contracts run --config PATH` is the sole CLI route.
- [ ] **SHIM-06**: Operator's test code under `tests/sdet/` is no longer auto-discovered — discovery fallback removed; only `tests/test_code/` is discovered by default; operator-tone DeprecationWarning replaced by clean removal.
- [ ] **SHIM-07**: Framework fixtures resolve only under the prefixed names — `mcp_config` / `mcp_judge` / `mcp_client` / `mcp_target_tool`; unprefixed aliases (`config` / `judge` / `client` / `target_tool`) are removed; operator-authored tests referencing legacy names fail at fixture-resolution time.
- [ ] **SHIM-08**: Operator can no longer invoke the legacy `mcp-test-framework` console-script — entry-point removed; `mcp-contracts` is the sole console script; `pyproject.toml` `[project.scripts]` reflects removal.
- [ ] **SHIM-09**: Regression-test gate pins zero-shim state in CI — a single test sweep across the importable surface (`mcp_test_framework.sdet`), CLI surface (`--sdet`, `gen-sdet-classes`, `mcp-test-framework`), config surface (`cfg.sdet.*`, `MCPTF_CONFIG_FILE`), fixture names (unprefixed quartet), and discovery surface (`tests/sdet/`) returns zero matches and blocks reintroduction.

### BUCKET — Per-bucket / per-judge opt-in granularity in ToolConfig (999.1)

Operator-facing escape hatch that surfaced during Phase 30 UAT-1: `ToolConfig.skip: true` is whole-tool only; required-field tools need to skip the empty-args output bucket while preserving schema + judge signal. SEED-022 respected — operator still chooses; framework gets a more precise lever.

- [ ] **BUCKET-01**: Operator can set `tools.<name>.skip_buckets: list[Literal["schema","judge","output"]] = []` in `config.yaml` to opt out of named test buckets per tool while leaving others enabled.
- [ ] **BUCKET-02**: Per-bucket skip filters at parametrize collection time, not runtime — skipped buckets are absent from `pytest --collect-only` output, not rendered as runtime-SKIPPED rows (same hotfix pattern as v1.1.1 / 260508-p0b for whole-tool skip).
- [ ] **BUCKET-03**: Invalid bucket name (typo, unknown bucket) is rejected by Pydantic with an operator-tone validation error naming the valid buckets.
- [ ] **BUCKET-04**: Pre-run digest reflects per-bucket skip counts and `--explain` surfaces bucket-level rationale (grep-able N+5-line block per tool listing which buckets were skipped and why per the config).
- [ ] **BUCKET-05**: README + `docs/LIBRARY-MODE.md` document per-bucket skip with a worked example (required-field tool skipping only the `output` bucket; schema + judge still run).

### ISOL — Opt-in host isolation passthrough (999.3)

Operator-facing escape hatch that surfaced during Phase 30 UAT-1 / UAT-2 closure: always-on isolation strips operator HOME/USERPROFILE/keyring before MCP spawn, breaking every live-stack UAT and SDET scenario that needs real credentials. Operator-locked: no keyring faking. SEED-022 respected — passthrough is the operator's explicit choice, operator owns the safety implications.

- [ ] **ISOL-01**: Operator can set top-level `host_isolation: strict | passthrough` in `config.yaml`; default is `strict` (preserves v1.0–v1.4 always-on isolation behavior); operator can opt into `passthrough` per config file.
- [ ] **ISOL-02**: `host_isolation: passthrough` mode inherits operator's full environment (HOME, USERPROFILE, TEMP, full env vars) into the MCP subprocess — allowlist + tempdir redirect bypassed.
- [ ] **ISOL-03**: `host_isolation: passthrough` mode does NOT inject `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` — operator's keyring backend is reachable from the spawned MCP subprocess.
- [ ] **ISOL-04**: `host_isolation: passthrough` mode serializes MCP subprocess spawns — pytest-xdist worker count clamped to 1 with an operator-tone explanation that passthrough sacrifices parallelism for credential reachability; `strict` mode unchanged (xdist-compatible).
- [ ] **ISOL-05**: Bare `Config()` constructor callers in `src/` and `tests/` are audited and documented — every call site states which mode it implicitly assumes; bare callers under both modes route through the resolved-config seam (no silent operator-env leak under `strict`; no missing-passthrough surprise under `passthrough`).
- [ ] **ISOL-06**: README + `docs/LIBRARY-MODE.md` document the `strict`-vs-`passthrough` trade-off, cite SEED-022 safety-delegation, and warn about the no-keyring-faking lock; passthrough's xdist-incompatibility surfaced in the same section.

### V1DROP — Drop v1-schema support (999.4)

Decommission-by-deletion: the framework has never been published, no live v1-schema operators exist, and UAT-3 (v1→v2 migration walkthrough) was retired-by-deletion in Phase 30. Drop the migration path entirely rather than carrying it forward.

- [ ] **V1DROP-01**: `docs/MIGRATION-v1-to-v2.md` is deleted; cross-references throughout the codebase (operator-error messages, ERROR-STYLE.md, README) are scrubbed in the same change.
- [ ] **V1DROP-02**: README and `docs/ERROR-STYLE.md` reference `version: 2` directly with no migration callout; `docs/LIBRARY-MODE.md` is swept for migration references and cleaned.
- [ ] **V1DROP-03**: `_validate_version` rejects unsupported versions (including v1) with a generic operator-tone error — "unsupported config version {v}; run `mcp-contracts config-init` to generate a current scaffold" — with no migration-specific verbiage and no `docs/MIGRATION-v1-to-v2.md` cross-reference.
- [ ] **V1DROP-04**: Framework self-tests pinning the legacy v1-rejection migration-message text are deleted or relaxed to assert "rejects unsupported version with an operator-tone error" without asserting specific message strings; close-gate (`uv run pytest tests/framework/`) green.

---

## Future Requirements (deferred to v1.6+)

- **999.2** — Codegen-driven parameter-test generation for required-field tools (`gen-test-classes` emits typed SDET scenarios from `inputSchema` examples). Pairs with v1.5 BUCKET work but scoped out of v1.5; promote when 999.1 ships and the operator can validate the per-bucket skip story before adding codegen on top.
- **999.5** — Framework self-test pollution when `MCPTF_CONFIG_FILE` is set (pydantic-settings deep-merge audit + `monkeypatch.delenv` autouse in `tests/framework/conftest.py`). Likely re-surfaces during 999.3 isolation work; will re-assess at v1.5 close.
- **SEED-002** — pytest-xdist tool-level parallelism with read/write resource markers (was deferred at v1.4 scoping "lands cleaner on stable library-mode API").
- **SEED-005** — OpenAI-compat judge backend (`base_url` + `api_key` unifier for Ollama / vLLM / LM Studio / hosted).
- **SEED-003** + **Phase 16 D-11** — Dynamic rubrics (rubrics-as-data) cohort with `--debug` per-judge breakdown block; pencilled at v1.5 in the post-v1.3 indicative roadmap, deferred to v1.6 to keep v1.5 cleanup-focused.
- **SEED-001** — Agentic tool-use judge (full realization of the vision); v2.0+.

## Out of Scope

- **Multiple MCP servers in one run** — generalization deferred until single-server contract is fully validated through library-mode (v1.4 ✓); revisit only with concrete multi-server use case.
- **HTTP and SSE MCP transports** — stdio is sufficient to validate the contract; out of scope for v1.5.
- **Web UI or dashboard** — out of scope; CLI + library-mode only.
- **Reading or importing `homelab-mcp` source** — black-box subprocess under test; mechanically enforced via `ruff TID251` + `sys.modules` guard (locked from v1.0).
- **SUT-aware framework features** — SEED-022 locked principle; framework primitives only; SDET owns safety.
- **Schema v2→v3 migration tooling** — `cfg.sdet.*` alias removal (SHIM-04) is a breaking change for any operator with a `sdet:` key in their v2 config, but the rename shim was the only thing supporting them and no real operators exist; surfaces as `extra="forbid"` operator-tone error rather than a versioned migration path. v3 schema bump deferred until a future capability change demands it.
- **Keyring faking / credential mock layer in passthrough mode** — operator-locked at v1.5 framing; the framework will not synthesize credentials; passthrough mode delegates fully to the operator's actual host environment per SEED-022.

## Traceability

Each REQ-ID maps to exactly one phase. Populated by gsd-roadmapper 2026-05-23.

| REQ-ID | Phase | Plan(s) |
|--------|-------|---------|
| SHIM-01 | Phase 32 | TBD |
| SHIM-02 | Phase 32 | TBD |
| SHIM-03 | Phase 32 | TBD |
| SHIM-04 | Phase 31 | TBD |
| SHIM-05 | Phase 31 | TBD |
| SHIM-06 | Phase 32 | TBD |
| SHIM-07 | Phase 32 | TBD |
| SHIM-08 | Phase 32 | TBD |
| SHIM-09 | Phase 35 | TBD |
| BUCKET-01 | Phase 33 | TBD |
| BUCKET-02 | Phase 33 | TBD |
| BUCKET-03 | Phase 33 | TBD |
| BUCKET-04 | Phase 33 | TBD |
| BUCKET-05 | Phase 33 | TBD |
| ISOL-01 | Phase 34 | TBD |
| ISOL-02 | Phase 34 | TBD |
| ISOL-03 | Phase 34 | TBD |
| ISOL-04 | Phase 34 | TBD |
| ISOL-05 | Phase 34 | TBD |
| ISOL-06 | Phase 34 | TBD |
| V1DROP-01 | Phase 31 | TBD |
| V1DROP-02 | Phase 31 | TBD |
| V1DROP-03 | Phase 31 | TBD |
| V1DROP-04 | Phase 31 | TBD |

**Coverage:** 24 / 24 reqs mapped (100%).

**Phase distribution:**
- Phase 31 (config-surface cleanup): 6 reqs — SHIM-04, SHIM-05, V1DROP-01..04
- Phase 32 (surface-shim removals): 6 reqs — SHIM-01, SHIM-02, SHIM-03, SHIM-06, SHIM-07, SHIM-08
- Phase 33 (per-bucket skip): 5 reqs — BUCKET-01..05
- Phase 34 (isolation passthrough): 6 reqs — ISOL-01..06
- Phase 35 (regression gate): 1 req — SHIM-09 (capstone)

---

*Defined 2026-05-22 at v1.5 milestone start (24 reqs across 4 categories; cleanup/hardening milestone closing v1.4 dogfood feedback). Traceability populated 2026-05-23 at roadmap creation.*
