# Phase 31: Config-surface cleanup — drop `MCPTF_CONFIG_FILE` + `cfg.sdet.*` alias + v1-schema decommission - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Tighten the operator-facing config-resolution surface down to one route per persona — library mode = `[tool.pytest.ini_options] mcp_config_file = PATH`, CLI = `mcp-contracts run --config PATH` — one schema version (v2 only), one valid test-code key (`test_code:`). Removes the `MCPTF_CONFIG_FILE` env-var route, the `cfg.sdet.*` alias (`Field(validation_alias=AliasChoices('test_code','sdet'))` + pre-scan + warn/reject model-validator), and every v1→v2 migration verbiage / breadcrumb in src/, docs/, and self-tests. Decommissions `docs/MIGRATION-v1-to-v2.md` by deletion (never-published framework, no live v1 operators).

**In scope:** SHIM-04 (`sdet:` alias removal), SHIM-05 (`MCPTF_CONFIG_FILE` removal), V1DROP-01..04 (migration doc deletion + cross-ref scrub + validator-message rewrite + self-test cleanup).

**Out of scope (different phases):** SHIM-01/02/03/06/07/08 surface-shim removals (Phase 32 — CLI flags, package import, fixtures, discovery), BUCKET-* per-bucket skip granularity (Phase 33), ISOL-* host isolation passthrough (Phase 34), SHIM-09 regression gate (Phase 35).

</domain>

<decisions>
## Implementation Decisions

### `sdet:` key rejection (SHIM-04)

- **D-01:** Removal mechanism is bare `extra='forbid'` + cli.py error mapper. Delete `validation_alias=AliasChoices('test_code','sdet')` on the `test_code` field, delete the `_warn_or_reject_legacy_sdet_key` `model_validator(mode='before')`, delete the `_check_legacy_sdet_key_in_yaml` pre-scan and its call from `settings_customise_sources`, delete the `model_validate` classmethod override that re-runs the pre-scan on dict input. Pydantic surfaces `extra_forbidden` for any top-level `sdet:` key naturally. **Net:** ~110 lines removed from `src/mcp_test_framework/config.py` plus all `# noqa: sdet-rename-shim` markers in that file.
- **D-02:** Targeted operator-tone error message for the `sdet:`-rejection case, three-part shape consistent with cli.py's existing `_emit_operator_error_for_validation_error` branches:
  ```
  summary  = "unknown config key: sdet"
  detail   = ["the `sdet:` key was renamed to `test_code:` in v1.4 and removed in v1.5.",
              "your existing block under `sdet:` ports forward unchanged — just rename the top-level key."]
  next_step = "rename the `sdet:` key to `test_code:` in your config.yaml"
  ```
- **D-03:** Branch trigger is exact-match: `err_type == 'extra_forbidden' AND loc == ('sdet',)`. Nested `cfg.sdet.X` errors never reach (Pydantic stops at the first extra-forbidden on the outer key). Phase 35 SHIM-09 sweeps `cfg.sdet.*` orthogonally.
- **D-04:** Same targeted message renders in BOTH CLI mode AND library mode. `_plugin.py`'s `pytest_configure` catches `Config(...)` `ValidationError`s and routes through the same error-mapper helper as cli.py — single canonical operator-error surface. **RESEARCH-FOR-PLAN:** verify whether `_plugin.py` already has such a mapper path or whether it needs to be factored out of `cli.py` into a shared module (`_operator_errors.py`?). Refactor preferred over duplication.

### Leftover `MCPTF_CONFIG_FILE` env in shell (SHIM-05)

- **D-05:** Env var is fully unwired from value-source / path-pointer code paths. Removes the `os.environ.get("MCPTF_CONFIG_FILE")` fallback inside `Config.settings_customise_sources` (config.py ~L235), removes Branch 2 of cli.py's `_load_config` resolver (~L521), removes the `--config` flag help-text references (`overrides MCPTF_CONFIG_FILE and ./config.yaml autodiscovery` → `overrides ./config.yaml autodiscovery`), removes the fixture-failure hint copy (`fixtures.py` ~L229-235, ~L321-331).
- **D-06:** A single `pytest_configure`-time detection survives: if `os.environ.get("MCPTF_CONFIG_FILE")` is set, fire ONE `DeprecationWarning` via `warnings.warn(..., stacklevel=...)`. Wording:
  ```
  MCPTF_CONFIG_FILE is set in your environment but no longer honored as of v1.5;
  configure via `[tool.pytest.ini_options] mcp_config_file = PATH` in pyproject.toml
  or pass `--config PATH` to `mcp-contracts run`.
  ```
  Never reads the path. Catches the Memory-flagged "MCPTF_CONFIG_FILE silent fail" footgun without forcing operators to unset before they can run.
- **D-07:** This warning fires from the pytest plugin only (`_plugin.py:pytest_configure`). cli.py's `run` command spawns the in-process pytest session which loads the plugin which fires the warning — no duplicate emission site. cli.py removes every operator-facing `MCPTF_CONFIG_FILE` reference; the warning is the sole surviving operator-visible mention.
- **D-08:** Visibility upgrade is IN SCOPE for Phase 31. With every other v1.4 deprecation shim being deleted outright by Phase 32, this MCPTF_CONFIG_FILE detection is the LAST DeprecationWarning the framework will fire. Ship a small `warnings.formatwarning` override (or domain-UI banner integration via `_reporter.py`) so this warning renders with a red `[mcp-contracts]` prefix and is separated from pytest's other output. **RESEARCH-FOR-PLAN:** decide between formatwarning override (broader effect, captures all `warnings.warn` calls from the package) vs domain-UI banner integration (narrow, only this one warning, but composes with existing reporter).
- **D-09:** Warning has a planned EOL: deleted entirely in v1.6 capstone. Captured as a v1.5 close deferred item. Phase 35 SHIM-09 regression gate grandfathers the detection itself for v1.5 (the gate sweeps `MCPTF_CONFIG_FILE` matches in src/ — must allow the single occurrence in `_plugin.py` until v1.6).

### Claude's Discretion (recommended defaults — planner free to revisit with research)

- **D-10 (IPC):** CLI → in-process pytest session passes the resolved config path via `-o mcp_config_file=PATH` (same channel as the library-mode operator) rather than introducing a private `_MCPTF_RESOLVED_CONFIG_FILE` env var. **Rationale:** unifies the two personas at the seam, no new shim, the `mcp_config_file` ini key becomes the single source of truth. If plugin-load-order or `-o` quoting issues surface during research, fall back to a private env var (clearly named `_MCPTF_*` with leading underscore to mark internal).
- **D-11 (v1 rejection message):** Replace the v1→v2 walkthrough text at `cli.py` ~L292-315 with minimal three-part:
  ```
  summary  = "unsupported config version {v}"
  detail   = ["this build supports schema version 2.",
              "your config declares version {v}, which is no longer accepted."]
  next_step = "run `mcp-contracts config-init -o config.yaml` to generate a current scaffold"
  ```
  No migration breadcrumb, no `docs/MIGRATION-v1-to-v2.md` reference (the file is deleted in V1DROP-01), no acknowledgement of v1→v2 history. Generic operator-tone shape, consistent with sibling errors.
- **D-12 (V1DROP-04 self-tests):** Per-test judgement, default to RELAX-not-delete. For each pinned-text assertion at `tests/framework/unit/test_error_style.py` and `tests/framework/unit/test_cli_errors.py` (and any others surfaced during research):
  - If the test pins the migration-walkthrough text specifically (cites `docs/MIGRATION-v1-to-v2.md` / "v1 vs v2 / opt-in vs opt-out") → delete the assertion; the message no longer contains that content.
  - If the test asserts the structural operator-tone shape (summary present, next_step present, exit code = 2) → relax the body match to "rejects unsupported version with operator-tone error" without pinning specific text.
  - Preserves test count + names; structural regression-check survives the message rewrite.

### Folded Todos

None — `gsd-sdk todo.match-phase 31` returned `todo_count: 0`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope + locked requirements
- `.planning/ROADMAP.md` §"Phase 31" — locked success criteria #1-5 (env-var inert, sdet rejected, v1 rejected, MIGRATION doc deleted, `tests/framework/` green).
- `.planning/REQUIREMENTS.md` §"SHIM" + §"V1DROP" — atomic requirements SHIM-04, SHIM-05, V1DROP-01..04 with traceability table.
- `.planning/STATE.md` §"Decisions" 2026-05-23 — phase-bundling rationale (why SHIM-04 + SHIM-05 + V1DROP-01..04 live in one phase) + the two open design questions flagged for plan-phase.

### Operator-error contract (shape + tone the rewrites must match)
- `docs/ERROR-STYLE.md` — operator-tone three-part error shape (summary / detail / next_step), pinned by source-text regression tests under `tests/framework/unit/test_error_style.py`.
- `docs/LIBRARY-MODE.md` — library-mode entry-point (`mcp_config_file` ini key) doc; V1DROP-02 requires sweep for migration references.
- `README.md` — `version: 2` references; V1DROP-02 requires migration-callout scrub.

### Code touch-points (already grep-verified, paths absolute to repo root)
- `src/mcp_test_framework/config.py` L52, L58-180 (`test_code` field + alias + pre-scan + model_validator), L195-203 (`_validate_version`), L226-247 (`settings_customise_sources` IPC fallback), L254-310 (`_check_legacy_sdet_key_in_yaml`).
- `src/mcp_test_framework/cli.py` L14 (module docstring), L292-315 (v1→v2 migration error path — V1DROP-03 target), L449-540 (`_load_config` resolver Branch 2 — SHIM-05 target), L670, L1023, L1118, L1296, L1425 (help-text references on `--config` flag — five occurrences).
- `src/mcp_test_framework/_plugin.py` L135-160 (existing `MCPTF_CONFIG_FILE` DeprecationWarning at `pytest_configure` — D-06 flips wording; D-04 verifies error-mapper hook exists).
- `src/mcp_test_framework/fixtures.py` L103, L162, L212-235, L321-331 (fixture-failure hint copy referencing `MCPTF_CONFIG_FILE`).
- `src/mcp_test_framework/models.py` L207 (comment reference to `MCPTF_CONFIG_FILE` convention — scrub).

### File deletions (V1DROP-01 + V1DROP-04)
- `docs/MIGRATION-v1-to-v2.md` — DELETED on disk.
- `tests/framework/unit/test_migration_doc.py` — likely DELETED (asserts the file exists / its content). Verify during research.
- `tests/framework/unit/test_error_style.py` — RELAX assertions pinning migration-walkthrough text per D-12.
- `tests/framework/unit/test_cli_errors.py` — RELAX assertions on v1-rejection body text per D-12.

### Memory + carry-forward context (the WHY behind several decisions)
- Memory `project_mcptf_config_file_silent_fail.md` — Memory entry that catalyzed SHIM-05 (typo'd path silently drops YAML source; misconfigured env var = destructive run).
- Memory `project_dotenv_silently_beats_config.md` — sibling precedence-confusion finding that informed the env-var removal scope.
- Memory `project_deprecation_warning_visibility.md` — Phase 25 finding driving D-08 (visibility upgrade in scope).
- Memory `feedback_phase_scope_intent.md` — locks scope to the phase title (config-surface cleanup); resist sub-agent reframing of D-08 as cross-cutting.
- Memory `project_framework_primitives_sdet_safety_principle.md` — SEED-022; framework does no SUT-safety reasoning. Cite if any error-message rewrite proposal drifts toward SUT-specific guidance.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cli.py:_emit_operator_error_for_validation_error` — existing dispatcher with branches per `(err_type, loc)` pair (e.g., `version`/`not supported by this build`, `missing`/`value_error.missing`). D-01 adds a new branch; D-11 rewrites the existing `version` branch in place. Same three-part `_emit_operator_error(summary=, detail=, next_step=)` shape.
- `_plugin.py:pytest_configure` — already fires a `DeprecationWarning` for `MCPTF_CONFIG_FILE` at L148-150 with the v1.4 deprecation copy. D-06 flips wording in place; trigger point + fire-once semantics already correct.
- `warnings.formatwarning` override pattern — likely partially shipped from Phase 25 deprecation-warning work; research must locate any existing override before D-08 lands a new one (avoid double-override).

### Established Patterns
- **Operator-tone error contract** — three-part (summary/detail/next_step), pinned by `tests/framework/unit/test_error_style.py`. All new + rewritten messages MUST conform; relaxation of pinned text per D-12 preserves the shape assertion.
- **`extra='forbid'` + targeted cli.py mapper** — established pattern for surfacing Pydantic schema errors with operator-tone wording. D-01 + D-02 extend this pattern symmetrically; the `version`-mismatch branch is the closest template.
- **Plugin-as-canonical-operator-surface** — `_plugin.py` already catches config-load failures and renders operator-tone messages BEFORE pytest's own traceback. D-04 leans on this; research must verify the error-mapper hook is factored out (or factor it out) so cli.py + plugin share one code path.
- **Path-pointer-only env-var idiom** — pre-Phase-31 `MCPTF_CONFIG_FILE` was a "path pointer, not a value source." After removal, `-o mcp_config_file=PATH` (the pytest ini-options channel) becomes the equivalent path-pointer mechanism for the CLI → in-process pytest IPC (D-10).

### Integration Points
- `cli.py:_load_config` resolver — Branch 2 (env-var) deleted; Branch 1 (`--config`) and Branch 3 (`./config.yaml` autodiscovery) survive. Resolver becomes two-branch.
- `cli.py:run` → spawned-pytest IPC — D-10 routes the resolved path via `-o mcp_config_file=PATH` injected into the pytest argv. Replaces the `os.environ["MCPTF_CONFIG_FILE"] = ...` set-before-spawn pattern.
- `_plugin.py:pytest_configure` — sole site of the surviving DeprecationWarning (D-06 + D-07) and (per D-04) the shared error-mapper hook routing Config `ValidationError`s through the same three-part operator-tone surface as cli.py.

</code_context>

<specifics>
## Specific Ideas

- The user has explicitly cited the Memory entries `MCPTF_CONFIG_FILE silent fail` and `.env beats --config` as the real-world repro evidence behind SHIM-05's scope. The DeprecationWarning at D-06 is specifically the antidote to that repro — an operator with stale shell env gets a one-shot loud signal rather than a silently-loaded destructive config.
- D-02 message wording was operator-approved verbatim during discussion; do NOT reword without checking back. Pin the text in a new test under `tests/framework/unit/test_error_style.py` (the canonical operator-error pinning location) so future shim-style edits don't drift it.
- D-08 visibility upgrade is in scope precisely BECAUSE this is the last DeprecationWarning standing post-v1.5. Resist sub-agent reframing as cross-cutting (per Memory `feedback_phase_scope_intent.md`).

</specifics>

<deferred>
## Deferred Ideas

- **MCPTF_CONFIG_FILE DeprecationWarning detection EOL** — capture as v1.5 close deferral; delete the detection (last ~10 lines in `_plugin.py:pytest_configure`) in v1.6 capstone. Phase 35 SHIM-09 regression gate must grandfather this single surviving match in src/ until v1.6.
- **Backlog 999.5 (framework self-test pollution when MCPTF_CONFIG_FILE is set)** — REQUIREMENTS.md flags this for re-assessment AFTER Phase 31. The env-var removal closes the specific repro surface; the underlying class-of-bug (pydantic-settings deep-merge between init_kwargs + YAML source for bare `Config()` callers) survives and re-surfaces at Phase 34 ISOL-05's bare-caller audit.
- **`docs/MIGRATION-v1-to-v2.md` content archival** — file is deleted on disk (V1DROP-01) but the v1→v2 migration story could be captured as a single line in `.planning/MILESTONES.md` v1.2 entry or a one-line `CHANGELOG.md` note. Out of Phase 31 scope; nice-to-have for historical record. Capture as backlog if not picked up by research.

### Reviewed Todos (not folded)

None — `gsd-sdk todo.match-phase 31` returned `todo_count: 0`; no todos to review.

</deferred>

---

*Phase: 31-Config-surface cleanup — drop `MCPTF_CONFIG_FILE` + `cfg.sdet.*` alias + v1-schema decommission*
*Context gathered: 2026-05-23*
