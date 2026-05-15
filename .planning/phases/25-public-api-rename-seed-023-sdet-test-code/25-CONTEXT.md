# Phase 25: Public-API rename (SEED-023) — `sdet` → `test_code` - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Lock the public import surface for operators and SDETs before Phase 26 publishes the corrected dist name to PyPI. Mechanical refactor + dual-write compatibility shims for v1.4 (removed in v1.5). Six concrete surfaces change in lockstep:

1. Package directory: `src/mcp_test_framework/sdet/` → `test_code/` (all internal imports updated).
2. CLI command: `gen-sdet-classes` → `gen-test-classes` (old name = deprecation shim).
3. CLI flag: `--sdet` → `--test-code` on `mcp-test-framework run` (old flag = deprecation shim).
4. Operator-authored tests dir: `tests/sdet/` → `tests/test_code/` (both paths discoverable for v1.4).
5. Config field: `cfg.sdet.generated_root` → `cfg.test_code.generated_root` (Pydantic alias shim).
6. Operator-facing docs + terminology: `docs/SDET-AUTHORING.md` → `docs/TEST-CODE-AUTHORING.md`; README / CLAUDE.md / docs / src docstrings / CLI `--help` use "test-code" consistently; planning-ID + `sdet`-literal sweep returns zero matches.

Out of scope (deferred to v1.5 per ROADMAP): removal of every compat shim, schema v2→v3 migration for `cfg.sdet` key, retirement of `tests/sdet/` dual-discovery.

</domain>

<decisions>
## Implementation Decisions

### Deprecation mechanics

- **D-01:** Use Python's stdlib `DeprecationWarning` for every v1.4 compat shim — *not* a custom subclass and *not* `FutureWarning`. Idiomatic; operators already know how to filter it.
- **D-02:** Firing cadence: once-per-process per shim. Use `warnings.warn(..., stacklevel=2)` and rely on Python's default `default` filter (first hit of each unique `(message, category, module)` is shown, rest suppressed). No `simplefilter('always')`.
- **D-03:** Framework-internal visibility: add `filterwarnings = always::DeprecationWarning:mcp_test_framework` (or equivalent per-module entry) under `[tool.pytest.ini_options]` in `pyproject.toml` so our own pytest suite still surfaces the warnings on every run — protects us from accidentally still using the old surface in framework code. External operator pytest config is left alone.
- **D-04:** Operator CLI visibility: the shim entry points (`gen-sdet-classes`, `--sdet`) are invoked from `__main__`, so Python's default filter already shows `DeprecationWarning` there. No extra plumbing needed — verify in Phase 25 UAT that an operator running `mcp-test-framework run --sdet` sees the warning on stderr.
- **D-05:** Removal milestone is named in every warning message: "deprecated since v1.4, removed in v1.5; use `<new-name>` instead." Hardcoded as a literal string per call site (no central constant — six call sites total, churn is low).

### `tests/sdet/` migration

- **D-06:** Use `git mv` to move `tests/sdet/conftest.py` and `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py` to `tests/test_code/` in Phase 25. Preserves blame; ships the canonical home for the dogfood file. Test-file path renames also touch the README §SDET-scenarios sample (snapshot path stays stale until Phase 30 carry-forward UAT re-captures it, per existing deferred-item plan).
- **D-07:** Discovery scope is dual-path for v1.4: `tests/test_code/` is the documented primary, `tests/sdet/` continues to be collected. If any items are collected from `tests/sdet/`, fire a single `DeprecationWarning` per session (not per file) naming the new path. The old `tests/sdet/` directory ends up empty inside this repo after `git mv` — the dual-path discovery is a courtesy to external operators only.
- **D-08:** Do NOT leave a stub file at `tests/sdet/`. The directory simply becomes empty after `git mv`; dual-scope discovery handles operator compat. Avoids "is this stub a test? is it a doc?" ambiguity.

### Doc rename strategy

- **D-09:** `git mv docs/SDET-AUTHORING.md docs/TEST-CODE-AUTHORING.md`. Preserves blame.
- **D-10:** Drop a one-line stub at the old path `docs/SDET-AUTHORING.md` after the move: `> Renamed to [TEST-CODE-AUTHORING.md](TEST-CODE-AUTHORING.md). The old filename is removed in v1.5.` Keeps internal links one-hop redirected during v1.4; removed in v1.5 cleanup phase.
- **D-11:** Phase 30 README rewrite is the authoritative re-linking pass for operator-facing surfaces. Phase 25 only updates *direct* references to the doc path in `CLAUDE.md`, `README.md` body, and any docstrings — Phase 30 does the full lead-with-library-mode rewrite.

### Pydantic alias shape

- **D-12:** Single field on the parent config:
  ```python
  test_code: TestCodeConfig = Field(
      default_factory=TestCodeConfig,
      validation_alias=AliasChoices("test_code", "sdet"),
  )
  ```
  Old YAML key `sdet:` and new YAML key `test_code:` both resolve to the same `TestCodeConfig`.
- **D-13:** Pair the field with a `@model_validator(mode='before')` on the parent that inspects the raw input dict: if `'sdet'` is present (regardless of whether `'test_code'` is also present), emit one `DeprecationWarning` per process via `warnings.warn(...)`. If BOTH `'sdet'` and `'test_code'` keys are present in the same YAML, raise a friendly `ValidationError` — ambiguous, no silent precedence rule.
- **D-14:** Internal code reads `cfg.test_code.*` exclusively after Phase 25; there is no `cfg.sdet` attribute. (The alias is YAML-input-only — operators writing Python code use the new name. Acceptance criterion in RENAME-05 is "operator can set `cfg.sdet.generated_root` in `config.yaml`", explicitly YAML scope.)
- **D-15:** Rename the inner Pydantic model class `SdetConfig` → `TestCodeConfig`. Old name removed in v1.5 (do not keep a `SdetConfig = TestCodeConfig` typing alias — internal class, not on operator import surface).

### Planning-ID + terminology sweep (RENAME-06)

- **D-16:** Sweep covers operator-facing surfaces: `README.md`, `CLAUDE.md`, all `docs/*.md`, all docstrings inside `src/mcp_test_framework/`, the Typer CLI `--help` output strings, and operator-visible error messages (`errors.py`, anything raised from CLI / discovery paths). Excludes `.planning/`, `tests/`, internal `_`-prefixed names, `__dunder__` names, and git history.
- **D-17:** Patterns searched:
  - Planning IDs: `\b(SDET|RENAME|PERSONA|CLEAN|CLI|CODEGEN|PACK|LIB|REPORTER|CFG|CLOSE|STATE|UI|UX|UAT|SAFE|SURFACE|RUNNER|SEED)-\d+(\.\d+)?\b`
  - Terminology: `\bsdet\b` (case-insensitive) and `\bSDET\b`.
- **D-18:** Allowed exclusions in matched files (must be one of):
  - Lines explicitly marked with the comment `# noqa: sdet-rename-shim` (or `<!-- noqa: sdet-rename-shim -->` in markdown) — for the compat shim definitions themselves.
  - Sections inside `docs/MIGRATION-v1-to-v2.md` and the equivalent v2→v3 migration doc (when written) — historical record of the old name. These docs may legitimately reference `sdet` when explaining the rename.
  - Stub at `docs/SDET-AUTHORING.md` (D-10) — its whole purpose is to mention the old name.
- **D-19:** Acceptance gate: a CI-runnable script (e.g. `scripts/check_sdet_leak.sh` or a pytest test under `tests/framework/`) walks the in-scope file set, applies the exclusions, and exits non-zero on any residual match. Lands as part of Phase 25 so Phase 26+ can't reintroduce a leak.

### Claude's Discretion

- Exact wording of the six `DeprecationWarning` message strings — keep them parallel ("`gen-sdet-classes` is deprecated since v1.4 and will be removed in v1.5 — use `gen-test-classes` instead.") but Claude picks the prose.
- File-order of edits inside the rename plans (Claude/planner decides waves).
- Whether `--test-code` and `--sdet` flags coexist via Typer's `--sdet`-as-alias mechanism vs. two separate options that both set the same internal var. Pick whichever is cleaner once the planner reads `cli.py`.
- Whether the alias shim's warning fires from `__init__.py` of the new package or from a lightweight `sdet/` re-export module. Either is fine; planner picks.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase-defining artifacts
- `.planning/ROADMAP.md` §"Phase 25: Public-API rename" — phase goal, depends-on, success criteria (5 SC items).
- `.planning/REQUIREMENTS.md` — RENAME-01 through RENAME-06 acceptance language.
- `.planning/PROJECT.md` — project-level constraints (SEED-022, dual-persona, black-box rule).

### Architectural decisions still in force
- Memory `project_framework_primitives_sdet_safety_principle.md` (SEED-022) — framework does no tool-safety reasoning; SDET decides what to call. Rename must NOT add any auto-detect/skip behavior to `test_code/` that wasn't in `sdet/`.
- Memory `project_serializer_exclude_unset_phase_24.md` — `tool().call()` uses `model_dump(exclude_unset=True)`. Carries through unchanged into the renamed package.
- Phase 22 SUMMARY (`.planning/phases/22-*/22-SUMMARY.md` if it exists, otherwise commit `b0dee98^` history) — operator-facing planning-ID scrub precedent. Same approach scaled up here.

### Code that names the old surface (must be touched)
- `src/mcp_test_framework/sdet/` — entire package, contents listed: `__init__.py`, `_codegen.py`, `_slugs.py`, `_tool_factory.py`, `errors.py`, `response.py`, `session.py`.
- `src/mcp_test_framework/cli.py` — `gen-sdet-classes` command, `--sdet` flag on `run`, docstrings.
- `src/mcp_test_framework/config.py` — `SdetConfig` model class, `cfg.sdet` field on parent config.
- `src/mcp_test_framework/fixtures.py`, `src/mcp_test_framework/_runner.py`, `src/mcp_test_framework/models.py` — import sites of the `sdet` package.
- `src/mcp_test_framework/_runner.py` and any `_session_needs_preflight` predicate — v1.3 quick-task `260513-chh` set the allowlist to `tests/contract/`, `tests/sdet/`. Phase 25 must update it to allow `tests/test_code/` AND keep `tests/sdet/` for the dual-scope milestone.
- `tests/sdet/conftest.py`, `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py` — moved via `git mv` per D-06.

### Operator-facing surfaces to scrub
- `README.md` — terminology + sample paths + planning-ID scan.
- `CLAUDE.md` — terminology + the "What This Project Is" v1.3 SDET persona paragraph (rewrite to "test-code" persona language).
- `docs/SDET-AUTHORING.md` → `docs/TEST-CODE-AUTHORING.md` — full content scrub.
- `docs/EXTENDING.md`, `docs/ERROR-STYLE.md`, `docs/MIGRATION-v1-to-v2.md` — incidental references.
- `examples/homelab-mcp.yaml`, `config.example.yaml` — `sdet:` key → `test_code:` (with `sdet:` retained in one example as the documented compat-alias demo).

### Carry-forward items that don't ship in Phase 25
- README §SDET-scenarios PASS-sample re-capture — closes in Phase 30 (CLOSE-04). Phase 25 updates the *path* but not the captured output.
- v1.2 Phase 13 / 14 live-stack UATs — closes in Phase 30.
- v1.3 Phase 17 SC1 (~70-tool live `gen-test-classes`) — closes in Phase 30.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- v1.3 Phase 22 scrub script and approach — was the planning-ID leak fix for `src/`. Phase 25's sweep is the same idea with a broader pattern set and broader file scope.
- Existing Pydantic v2 idioms in `config.py` — `model_validator`, schema versioning. Adding `AliasChoices` + a `mode='before'` validator is consistent with how schema v1→v2 migration was wired.
- `warnings.warn` already used in `cli.py` for some operator-facing notices — keep the same pattern.

### Established Patterns
- **One-milestone deprecation window** is the project's established pattern (cf. Phase 16 fixture rename precedent referenced in ROADMAP "fixture-rename one-milestone deprecation window" — Phase 26 will use the same window).
- **Dual-discovery with deprecation warning** matches how Phase 15 introduced `tests/framework/` and `tests/contract/` alongside the old flat `tests/` layout.
- **Pydantic alias for schema migration** mirrors the v1→v2 config migration (Phase 13) — `AliasChoices` is the established mechanism for this codebase.

### Integration Points
- `_session_needs_preflight` allowlist (`_runner.py`) — must accept both `tests/test_code/` and `tests/sdet/` for v1.4.
- Typer CLI command registration in `cli.py` — adding a second command name as a shim is a one-decorator add; Typer's `hidden=True` flag keeps `gen-sdet-classes` out of the auto-generated help table while still callable.
- Codegen output path default (`_codegen.py`) — uses `cfg.test_code.generated_root` AFTER rename; default value (`tests/_generated/<server_slug>/`) is unchanged. Phase 28 owns the cwd-relative default decision.

</code_context>

<specifics>
## Specific Ideas

- Deprecation warning string template (parallel across all six call sites):
  `"<old> is deprecated since v1.4 and will be removed in v1.5 — use <new> instead."`
  with the per-site swap (`gen-sdet-classes` → `gen-test-classes`, `--sdet` → `--test-code`, `cfg.sdet` → `cfg.test_code`, `tests/sdet/` → `tests/test_code/`, `from mcp_test_framework.sdet` → `from mcp_test_framework.test_code`, `SdetConfig` is internal so no warning).
- Sweep exclusion marker for code: `# noqa: sdet-rename-shim`. For markdown: `<!-- noqa: sdet-rename-shim -->`. One consistent token across the codebase makes the CI gate trivially `grep -v`-able.
- `docs/SDET-AUTHORING.md` stub content (exact one-liner): `> Renamed to [TEST-CODE-AUTHORING.md](TEST-CODE-AUTHORING.md). The old filename is removed in v1.5.`

</specifics>

<deferred>
## Deferred Ideas

- **`scoped_register()` multi-server context manager** — already flagged in ROADMAP "Out of v1.4". Phase 27 may surface naming questions here; not Phase 25's problem.
- **URL-style judge kwarg** (`judge="ollama://..."`) — deferred to Phase 28 framing.
- **Schema v2→v3 migration** — drops `sdet`-key alias entirely; deferred to v1.5.
- **Auto-discovery `register(tools=None)`** — deferred to v1.5 (ROADMAP "Out of v1.4").
- **Removing deprecation aliases** (full retirement of `sdet` surface) — explicitly v1.5.
- **Per-judge `--debug` breakdown** (dormant Phase 16 D-11) — v1.5 cohort with SEED-003.

</deferred>

---

*Phase: 25-public-api-rename-seed-023-sdet-test-code*
*Context gathered: 2026-05-15*
