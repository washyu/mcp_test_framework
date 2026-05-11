# Phase 15: Operator vs framework test surface split - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Split `tests/` into `tests/contract/` (operator-relevant: tests exercising the SUT contract) and `tests/framework/` (internal: framework self-tests — config validation, runner parsing, error-style locks, isolation, banned-imports, README/example snippet correctness, smoke checks against live external systems). Retarget the runner's default collection scope from `tests/` to `tests/contract/`. Add a `--with-framework` opt-in that appends `tests/framework/` to the default scope for maintainer / CI use. Preserve git history via `git mv` for every moved file.

**In scope:** SURFACE-01..04 (4 requirements). Folder creation, file moves, runner default-scope flip (single string in `src/mcp_test_framework/_runner.py:95`), `--with-framework` Typer flag, `--raw` anchor update, conftest verification (no split — top-level stays as-is), banned-imports test relocation.

**Out of scope:**
- **Phase 16** — Reporter UX overhaul (`--explain`, pre-run digest polish, N=70 readability). Phase 15 changes WHAT is collected; Phase 16 changes HOW the collection is summarized.
- **CI workflow files outside this repo** — Phase 15 ships the test-surface contract; whatever CI consumes it adapts independently. (The repo has no `.github/workflows/`-style CI files in the tree right now.)
- **Smoke-test audit / removal** — `tests/smoke/*` files are inherited from v1.0/v1.1 and may be partially obsolete. Phase 15 relocates them under `tests/framework/smoke/`; an audit-and-prune is deferred (Phase 11 / SEED-013 territory).
- **Renaming / refactoring inside moved files** — `git mv` only. Content changes risk breaking history-preservation per SURFACE-03.

**Hard dependency:** Phase 14 must be complete (it is — shipped 2026-05-11). The seam Phase 15 flips is `args: list[str] = ["tests"]` in `src/mcp_test_framework/_runner.py:95` (inside `_build_pytest_args`), introduced specifically for this phase by Phase 14 deferred §"Cross-phase tasks (Phase 15)".

**Sequencing note:** SEED-011 rule was Phase 14 (runner contract) BEFORE Phase 15 (folder split). Honored — runner contract is locked, the folder split is now a mechanical retarget.

</domain>

<decisions>
## Implementation Decisions

### Opt-in flag (SURFACE-02)
- **D-01:** **Flag name: `--with-framework`.** Matches REQUIREMENTS.md verbatim; reads naturally as "run with framework self-tests included". Composes with `--raw` and `-q`/`--debug` as independent axes (scope / rendering / verbosity).
- **D-02:** **APPEND semantics, not REPLACE.** `--with-framework` collects `tests/contract/` AND `tests/framework/`. This matches the natural-language reading, mirrors the pre-Phase-15 behavior of `pytest tests/` (so CI doesn't need two invocations), and aligns with SURFACE-02's "reachable through the operator CLI for CI use" framing. A maintainer wanting framework-only can still `uv run pytest tests/framework/` directly.
- **D-03:** **Argv translation.** `_build_pytest_args` currently emits `args: list[str] = ["tests"]` (single positional). After Phase 15: when `with_framework=False`, emit `["tests/contract"]`; when `with_framework=True`, emit `["tests/contract", "tests/framework"]`. Preserve the rest of `_build_pytest_args` unchanged — `--junitxml=PATH` insertion and passthrough precedence (Phase 09 D-01a / Phase 14 D-02) are untouched. The flag plumbs through `cli.py:run` → `run_pytest_subprocess` → `_build_pytest_args` as a new bool keyword param.

### Conftest split strategy (SURFACE-03)
- **D-04:** **Top-level `tests/conftest.py` stays as-is — no split.** Three reasons: (1) `pytest_configure` (homelab-mcp `sys.modules` guard at lines 30–55) MUST apply to both subtrees — the black-box rule is universal; (2) `pytest_generate_tests` (lines 146–158) is already a no-op for tests that don't request `target_tool` (line 154 early-return), so framework tests are unaffected by its presence; (3) `pytest_plugins = ["mcp_test_framework.fixtures"]` (line 18) is harmless for framework tests that don't use the fixtures. Zero churn for the conftest — only test files move.
- **D-05:** **No new per-subdir conftest files.** Avoid `tests/contract/conftest.py` and `tests/framework/conftest.py`. If a future split becomes necessary (e.g., framework tests need a fixture incompatible with the live-MCP discovery hook), revisit then — not preemptively.

### Test file classification (SURFACE-01)
- **D-06:** **Contract surface = exactly one file: `tests/test_mcp_tool_contract.py` → `tests/contract/test_mcp_tool_contract.py`.** It is the only test that exercises the SUT (homelab-mcp or any operator-configured MCP server) end-to-end via discovery + schema + judge. Every other top-level / unit / smoke test exercises the framework's own internals.
- **D-07:** **Framework surface — moves with `git mv`:**
  - `tests/test_config_init_cli.py` → `tests/framework/test_config_init_cli.py`
  - `tests/test_isolation.py` → `tests/framework/test_isolation.py`
  - `tests/test_readme_snippets.py` → `tests/framework/test_readme_snippets.py`
  - `tests/test_runner_live_smoke.py` → `tests/framework/test_runner_live_smoke.py`
  - `tests/test_runner_renderer.py` → `tests/framework/test_runner_renderer.py`
  - `tests/test_runner_subprocess.py` → `tests/framework/test_runner_subprocess.py`
  - `tests/test_runner_verbosity.py` → `tests/framework/test_runner_verbosity.py`
  - `tests/test_tool_config.py` → `tests/framework/test_tool_config.py`
  - `tests/unit/` (20 files) → `tests/framework/unit/` (preserve `__init__.py`; entire directory moves intact)
  - `tests/smoke/` (3 files including `__init__.py`) → `tests/framework/smoke/` (entire directory moves intact)
  - `tests/_fixtures/banned_import_should_fail.py.txt` → `tests/framework/_fixtures/banned_import_should_fail.py.txt`
  - `tests/fixtures/junit-*.xml` (4 XML files) → `tests/framework/fixtures/junit-*.xml`
- **D-08:** **Smoke tests go to `tests/framework/smoke/`, not `tests/contract/smoke/`.** They hardcode `homelab-mcp` and live Ollama at `127.0.0.1:11434` — running them against an operator's MCP server would produce false failures. Conceptually framework reachability checks, not SUT-contract checks. (`test_smoke_homelab_mcp.py`, `test_smoke_ollama_judge.py`, `test_mcp_client_teardown_regression.py`.)
- **D-09:** **`test_runner_live_smoke.py` is framework, not contract.** Tests the wrapper rendering end-to-end (the framework's own runner). Operators running `mcp-test-framework run` don't need to re-test the wrapper that's running them. Maintainers exercise via `tests/framework/`.
- **D-10:** **Banned-imports test relocation (SURFACE-04).** Current path: `tests/unit/test_banned_imports.py`. After move: `tests/framework/unit/test_banned_imports.py` (carried inside the bulk `tests/unit/` → `tests/framework/unit/` move). SURFACE-04's spec says `tests/framework/test_banned_imports.py` — accept the deeper `unit/` path as functionally equivalent (the SURFACE-04 contract is "the test runs under `tests/framework/` somewhere"), or hoist the single file out of `unit/` post-move. **Recommend hoisting** for SURFACE-04 spec literalism: an extra `git mv tests/framework/unit/test_banned_imports.py tests/framework/test_banned_imports.py` after the bulk directory move. Cheap to keep the path SURFACE-04 names.

### --raw semantics post-split (Phase 14 D-11 carryover)
- **D-11:** **`--raw` follows the operator default scope: `tests/contract/` only.** Three independent axes:
  - **Scope:** `--with-framework` (appends `tests/framework/`)
  - **Rendering:** `--raw` (no domain UI; pytest-native stdout)
  - **Verbosity:** `-q` / default / `--debug`

  Each composes orthogonally. `--raw --with-framework` = unwrapped pytest over both subtrees. `--raw` alone = unwrapped pytest over `tests/contract/` only. This preserves Phase 14 D-11's *spirit* (raw = no wrapper rendering) while letting the scope-flip from Phase 15 carry through cleanly.
- **D-12:** **Update Phase 14's docstring anchor.** `cli.py:371`'s error/help text currently reads `"\`uv run pytest tests/\` modulo the config pre-flight gate"`. Update to `"\`uv run pytest tests/contract/\` modulo the config pre-flight gate"` so operator-facing help text matches the post-split reality. Also update `_runner.py:188-192` doc comment block describing default-mode behavior.

### Claude's Discretion
- **Plan ordering within Phase 15.** Suggested sequence: (1) `git mv` test files into `tests/contract/` and `tests/framework/` per D-06/D-07/D-10; preserve `__init__.py` / fixtures; commit with `git log --follow` verified for one file from each subtree (SURFACE-03). (2) Flip `_build_pytest_args` default to `["tests/contract"]`; add `with_framework: bool = False` param threading through `run_pytest_subprocess` and `cli.py:run` to a new Typer `--with-framework` flag; update `--raw` argv builder to use the same scope logic (D-03/D-11). (3) Update docstrings / help text anchors (D-12); update `tests/test_readme_snippets.py` if it pins `uv run pytest tests/` literally; update `docs/mcp_test_framework_mvp_spec.md` if it references collection paths. (4) Verify all moved tests still pass: `uv run pytest tests/contract/` (contract only), `uv run pytest tests/framework/` (framework only), `uv run pytest tests/` (both — backward-compat for maintainers), `mcp-test-framework run` (default scope = contract only, no framework noise), `mcp-test-framework run --with-framework` (both, CI use). (5) Refresh `tests/conftest.py` docstring header comment if it cites Phase 14 / pre-split paths.
- **Whether to hoist `test_banned_imports.py` out of `unit/`** (D-10 recommends yes for SURFACE-04 literalism; keeping it inside `unit/` is also defensible — judgment call during planning).
- **README updates.** If `README.md` documents `uv run pytest tests/` as the dev recipe, update to `uv run pytest tests/` (still works — collects both) OR `uv run pytest tests/framework/` for framework-only or `uv run pytest tests/contract/` for contract-only. Phase 12 doc-scrub may have already established the wording — verify before churning.
- **Whether to add a CHANGELOG-style entry.** No CHANGELOG.md exists in repo per Phase 12 cleanup; defer unless one materializes.
- **Conftest module-docstring update.** `tests/conftest.py:1-14` describes pre-Phase-15 layout; touching it is content-edit and the file isn't being moved — optional refresh, not load-bearing.
- **Whether SURFACE-04's literal path `tests/framework/test_banned_imports.py` is satisfied by `tests/framework/unit/test_banned_imports.py`** — depends on how strictly the planner reads the requirement. Plan can either hoist OR document the equivalence in the verification step.

</decisions>

<specifics>
## Specific Ideas

- **The seam was deliberately left by Phase 14.** `_runner.py:95` `args: list[str] = ["tests"]` is a single-string flip; Phase 14 deferred §"Cross-phase tasks (Phase 15)" explicitly names this and `--raw`'s equivalence target. The whole phase is mostly `git mv` + that one line + the new Typer flag.
- **SURFACE-03 verification recipe:** after the move, run `git log --follow tests/contract/test_mcp_tool_contract.py` and `git log --follow tests/framework/unit/test_banned_imports.py` — both must show pre-move history (the test files have commits going back to Phase 04 / Phase 01 respectively). Add this as a verification step in PLAN.md.
- **Contract test count check.** SURFACE-02 SC-1: an operator with two enabled tools sees ~20 contract cases. The single contract file has ~10 cases per tool (5 schema validators + 4 judge dimensions + 1 output conformance, parametrized over discovered tools). Verify after the move that `mcp-test-framework run --config <2-tool-config>` produces ~20 collected cases, zero framework self-tests in the output.
- **Backward compat for `pytest tests/`.** Maintainers running `uv run pytest tests/` continue to collect both subtrees (pytest recurses into subdirectories by default). This is the migration-friendly path and is what SURFACE-02 implicitly assumes.
- **The runner's pre-flight gate stays unchanged.** `_load_config` (Phase 13) still fires before subprocess pytest regardless of scope flag. `--with-framework` does NOT bypass SAFE-03's refuse-on-no-config — the framework's own self-tests still need a resolved config for fixtures that touch live Ollama / live MCP via `MCPTF_CONFIG_FILE`.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/REQUIREMENTS.md` §SURFACE-01..04 (lines 58–61) — the 4 locked requirements
- `.planning/ROADMAP.md` Phase 15 row (lines 102–111 and 42) — goal, depends-on, 4 success criteria
- `.planning/PROJECT.md` — milestone v1.2 framing (Operator-First Design)
- `.planning/STATE.md` — current position (Phase 14 complete 2026-05-11)

### SEED-010 — primary design spec for this phase
- `.planning/seeds/SEED-010-operator-vs-framework-test-surface.md` — full motivation, folder-split mockup at §"1. Folder split", operator-runner default-scope rule at §"2. Operator runner default scope", CI matrix at §"3. CI matrix", breadcrumbs naming specific files

### Phase 14 forward-refs (LOCKED — implement against)
- `.planning/phases/14-hybrid-runner-with-domain-ui/14-CONTEXT.md` §decisions D-09, D-11, §deferred "Cross-phase tasks (Phase 15)" — the seam Phase 15 flips and the `--raw` semantic carryover
- `src/mcp_test_framework/_runner.py:79-99` (`_build_pytest_args`) — the seam (line 95) Phase 15 modifies; passthrough precedence (Phase 09 D-01a) is preserved
- `src/mcp_test_framework/_runner.py:125-200` (`run_pytest_subprocess`) — `--raw` vs default-mode argv builders; both consume `_build_pytest_args` so D-03 / D-11 are a single change site
- `src/mcp_test_framework/cli.py:394-485` (the `run` Typer command) — where the new `--with-framework` flag gets registered; threading goes `run` → `run_pytest_subprocess(..., with_framework=...)` → `_build_pytest_args`
- `src/mcp_test_framework/cli.py:371` — the docstring/help-text anchor citing `tests/` that becomes `tests/contract/` per D-12

### Phase 13 forward-refs (LOCKED — do not modify in Phase 15)
- `.planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md` §D-13 — SAFE-01 opt-in allowlist; framework tests still need `MCPTF_CONFIG_FILE` resolution, so the pre-flight gate fires regardless of `--with-framework`
- `tests/conftest.py:88-143` (`_resolve_tool_names`) — Phase 13 D-13 / SAFE-01 allowlist; D-04 keeps this conftest top-level so both subtrees inherit

### v1.1 contracts preserved by this phase
- Phase 07 `ids=names` parametrize convention at `tests/conftest.py:146-158` — preserved by D-04
- Phase 09 D-01a passthrough precedence in `_build_pytest_args` — preserved by D-03 (the scope flip is positional, junitxml insertion order unchanged)
- Phase 04.1 AsyncExitStack-owned `mcp_client` — unchanged (lives in `src/mcp_test_framework/fixtures.py`, registered via top-level `pytest_plugins`)

### Files affected by this phase
- `src/mcp_test_framework/_runner.py:79-99` — flip `["tests"]` to scope-aware list (D-03)
- `src/mcp_test_framework/_runner.py:125-200` — accept `with_framework: bool` param, thread to `_build_pytest_args`
- `src/mcp_test_framework/cli.py:394-485` — register `--with-framework` Typer flag, forward to subprocess dispatch
- `src/mcp_test_framework/cli.py:371` — update help-text anchor from `tests/` to `tests/contract/` (D-12)
- `tests/conftest.py` — module docstring refresh optional (Claude's discretion); content unchanged (D-04/D-05)
- `tests/test_readme_snippets.py` if it pins literal `tests/` paths — verify and update
- `docs/mcp_test_framework_mvp_spec.md` if it references collection paths — verify and update
- `README.md` if it documents `uv run pytest tests/` as the dev recipe — verify and update

### Files moved by this phase (via `git mv`)
- 1 file → `tests/contract/test_mcp_tool_contract.py` (D-06)
- 8 files → `tests/framework/*.py` (D-07)
- 20+ files → `tests/framework/unit/*.py` (full directory `git mv`)
- 3 files → `tests/framework/smoke/*.py` (full directory `git mv`)
- 4 XML files → `tests/framework/fixtures/junit-*.xml`
- 1 file → `tests/framework/_fixtures/banned_import_should_fail.py.txt`
- (Optional) 1 hoist: `tests/framework/unit/test_banned_imports.py` → `tests/framework/test_banned_imports.py` for SURFACE-04 path literalism (D-10)

### Memory references (operator-vs-dev pattern context)
- `feedback_phase_scope_intent.md` — the operator-vs-dev pattern this phase institutionalizes
- `project_output_ergonomics_at_scale.md` — homelab-mcp ≈ 70 tools; 84% noise reduction is the operator-perceived win

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **The Phase 14 seam.** `_build_pytest_args` at `src/mcp_test_framework/_runner.py:79-99` already centralizes the scope argv contribution to one line (`args: list[str] = ["tests"]`, line 95). All paths that invoke pytest — default mode, `--raw` mode, operator-junit-xml mode — funnel through this helper. Phase 15's scope flip is a single change site.
- **Typer flag registration pattern.** `cli.py` already has `--raw`, `--debug`, `-q`, and `--junit-xml=PATH` on the `run` command per Phase 14 D-11..D-15. Adding `--with-framework: bool = False` follows the established pattern verbatim.
- **`run_pytest_subprocess` keyword-only param surface.** Already takes `junit_xml`, `pytest_args`, `raw` as keyword-only. Adding `with_framework: bool` is purely additive — no positional reshuffle.
- **`tests/conftest.py` is auto-loaded for subdirectories by pytest's discovery rules** — moving test files into `tests/contract/` and `tests/framework/` does not break the top-level fixture / discovery / black-box-guard wiring.

### Established Patterns
- **`git mv` preserves history for moved files** — confirmed by Phase 14's deletion of `_reporter.py` (history still in `git log`). SURFACE-03's `git log --follow` verification is the standard check.
- **Phase 12 doc-scrub + Phase 13/14 implementation rounds** have already touched `README.md`, `config.example.yaml`, `.env.example` (deleted in Phase 13), and `tests/test_readme_snippets.py`. Verify whether any of those pin literal `tests/` paths before editing.
- **Stdlib-only, no new deps.** Phase 15 adds no Python imports — purely filesystem moves + one Typer flag + one argv list change.

### Integration Points
- `cli.py:run` (new `--with-framework` flag) → `run_pytest_subprocess(..., with_framework=...)` → `_build_pytest_args(junit_xml, pytest_args, with_framework)` → emits `["tests/contract"]` or `["tests/contract", "tests/framework"]`. Single linear flow, no plugin coupling.
- The in-subprocess pytest still constructs `Config()` from `MCPTF_CONFIG_FILE` (Phase 13 / Phase 14 unchanged). Scope flip doesn't touch the env-var export.
- `tests/conftest.py` continues to apply to both subtrees — `pytest_configure` (black-box guard) runs at session start regardless of which subdirectory got selected. SURFACE-04's enforcement is automatic.

</code_context>

<deferred>
## Deferred Ideas

### Cross-phase tasks (Phase 16)
- **Pre-run digest "Skipping (N)" semantics.** Phase 16 owns UX-02's `--explain` and the per-tool skip-reasons rendering. Phase 15 does not change Phase 14's header layout; the count semantics are inherited.
- **N=70 readability tuning** — orthogonal to scope-flip.

### Out of scope at scoping
- **Smoke-test audit.** `tests/smoke/*` are inherited from v1.0/v1.1. Some may be partially obsolete after Phase 14's `_runner.py` rewrite. Phase 15 relocates them to `tests/framework/smoke/`; an audit-and-prune is a separate quick-task (or part of Phase 11 / SEED-013).
- **Renaming files for clarity.** Phase 15 is `git mv` only — no file renames. A future cleanup phase could rename `test_isolation.py` → `test_session_isolation.py` etc., but not here (history preservation per SURFACE-03 is the priority).
- **CI workflow updates.** No `.github/workflows/` lives in this repo currently. If/when CI is added, it should run `uv run pytest tests/contract/` + `uv run pytest tests/framework/` as two jobs (or `uv run pytest tests/` as one). Out of Phase 15 scope.
- **xdist parallelism for the larger framework suite** — v1.3 (SEED-002).
- **Per-judge model config / OpenAI-compat backend** — v1.3 (SEED-005 / SEED-012).

</deferred>

---

*Phase: 15-operator-vs-framework-test-surface-split*
*Context gathered: 2026-05-11*
