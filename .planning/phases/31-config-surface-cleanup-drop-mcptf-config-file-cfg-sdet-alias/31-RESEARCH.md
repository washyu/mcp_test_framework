# Phase 31: Config-surface cleanup — Research

**Researched:** 2026-05-23
**Domain:** Config-resolution surface tightening, deprecation-shim removal, doc/self-test scrub
**Confidence:** HIGH

## Summary

Phase 31 collapses the operator-facing config-resolution surface to a single route per persona (library = `mcp_config_file` ini key; CLI = `--config PATH`), removes the `sdet:` YAML alias, removes the `MCPTF_CONFIG_FILE` env-var route (replacing it with a single loud DeprecationWarning fired from `_plugin.pytest_configure`), and decommissions the v1→v2 migration doc + every cross-reference to it. The phase touches `config.py`, `cli.py`, `_plugin.py`, `fixtures.py`, `models.py`, three doc files (`README.md`, `docs/LIBRARY-MODE.md`, `docs/ERROR-STYLE.md`), two example/`.env` files at repo root, and ~10 framework self-tests. `docs/MIGRATION-v1-to-v2.md` and `tests/framework/unit/test_migration_doc.py` are deleted on disk.

The two RESEARCH-FOR-PLAN items resolve cleanly:

- **D-04 (shared error-mapper hook):** the shared route already exists. `_plugin.pytest_configure` (lines 182-196) lazily imports `_emit_operator_error_for_validation` from `cli.py` and routes Config `ValidationError`s through it, then translates the `typer.Exit` to `pytest.exit(returncode=2)`. No factor-out needed; the `extra='forbid' → sdet:` branch added to `_emit_operator_error_for_validation` (per D-01/D-02) surfaces uniformly in CLI and library modes.
- **D-08 (visibility upgrade mechanism):** no existing `warnings.formatwarning` override ships in `src/`. Both candidates (formatwarning override vs `_reporter.py` banner) are viable; ship a **`warnings.formatwarning` override installed inside `_plugin.pytest_configure`** scoped only to the `MCPTF_CONFIG_FILE` deprecation message. Smallest delta, single emission site, composes with the existing reporter without coupling to it.

**Primary recommendation:** treat this phase as four near-independent task clusters that can land in any order (SHIM-04 alias removal, SHIM-05 env-var unwiring, V1DROP-01..04 v1-schema decommission) plus one cross-cutting cluster (self-test relaxation per D-12). The sequencing risk is small because `_validate_version` already rejects v1 today — the V1DROP-03 message rewrite swaps the message body, not the rejection.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHIM-04 | Reject `sdet:` YAML alias with operator-tone error pointing at `test_code:` | D-04 verdict (shared mapper exists); ~110 lines of `config.py` to delete; new branch added to `_emit_operator_error_for_validation` (cli.py L244-347) |
| SHIM-05 | Remove `MCPTF_CONFIG_FILE` env-var route; ini key + `--config` are the only two surfaces | D-08 verdict (formatwarning); IPC verification — D-10 mechanism (`-o mcp_config_file=PATH`) is already shipped and in use by `_runner._build_pytest_args:168-177` |
| V1DROP-01 | Delete `docs/MIGRATION-v1-to-v2.md` + cross-refs | Doc inventory below — 3 doc files (README, ERROR-STYLE, LIBRARY-MODE), `_emit_operator_error_for_validation` body, 2 framework tests |
| V1DROP-02 | README + ERROR-STYLE + LIBRARY-MODE reference `version: 2` directly without migration callout | Doc inventory below; README has 4 mentions, LIBRARY-MODE has 5, ERROR-STYLE has 1 |
| V1DROP-03 | `_validate_version` rejection message is generic operator-tone (no `MIGRATION-v1-to-v2.md` ref) | cli.py L292-315 is the body to rewrite; verbatim D-11 text from CONTEXT.md |
| V1DROP-04 | Framework self-tests pinning v1-rejection text are deleted or relaxed | Self-test inventory below — 2 DELETE candidates, 4 RELAX candidates |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Config schema definition + version validation | Library (config.py) | — | Pydantic model is the canonical schema; `_validate_version` is co-located with the field declaration |
| Operator-error rendering | Library (_runner.py:_emit_operator_error) + CLI mapper (cli.py:_emit_operator_error_for_validation) | Plugin (`_plugin.py` lazy-imports the mapper) | The mapper is shared via lazy import; one rendering shape across CLI + library entry points |
| `MCPTF_CONFIG_FILE` deprecation detection | Plugin (`_plugin.pytest_configure`) | — | Plugin is the only sane fire-once trigger that covers both `mcp-contracts run` (which spawns subprocess pytest → loads plugin) and bare `pytest` (library mode) |
| YAML resolution precedence | CLI (cli.py:_load_config) | Plugin (`_plugin.pytest_configure` reads the ini key directly) | CLI resolves --config + pyproject + cwd autodiscovery; plugin reads ini key when CLI route isn't in play |
| Migration-doc UX | Doc tier (`docs/`) | — | Deletion is mechanical; cross-refs in operator-tone error bodies must be scrubbed to keep error wording self-contained |

## D-04 Resolution — Shared Error-Mapper Hook

**Verdict:** the shared route **already exists**. No factor-out needed.

**Evidence:**

`_plugin.py:182-196` (current HEAD) already lazy-imports `_emit_operator_error_for_validation` from `cli.py` and routes Config `ValidationError`s through it:

```python
try:
    cfg = Config(yaml_file=str(path))
except ValidationError as exc:
    # Lazy-import to avoid cli.py <-> _plugin.py circular at module load.
    from mcp_test_framework.cli import _emit_operator_error_for_validation
    try:
        _emit_operator_error_for_validation(exc, source=str(path))
    except SystemExit:
        # _emit_operator_error_for_validation raises typer.Exit (SystemExit
        # subclass) with code=2. Translate to pytest.exit so the convention
        # `returncode=2 = setup error` is preserved end-to-end.
        pytest.exit(...)
```

**Implication for the planner:** the new SHIM-04 branch (D-01/D-02 — `extra_forbidden` on `loc=('sdet',)`) is added to `_emit_operator_error_for_validation` in `cli.py:244-347` (after the `version` branch, before the `missing` branch). Because the plugin already routes through this same function, the branch fires uniformly across:

1. CLI route (`mcp-contracts run --config PATH` → `_load_config:572-575` → `Config(yaml_file=...)` raises → mapper called inline)
2. Library route (`pytest -o mcp_config_file=PATH` → `_plugin.pytest_configure:181-196` → mapper called via lazy import)
3. CLI → subprocess pytest IPC (`cli.py:run` spawns pytest with `-o mcp_config_file=PATH` → plugin route 2 fires inside the subprocess)

**Caller updates required:** none. The function signature `_emit_operator_error_for_validation(exc, source=...)` already accepts the source-label string for substitution into the rendered message. The new branch reads the same `errors` list, matches `err_type == 'extra_forbidden' AND loc == ('sdet',)` (D-03), and renders the D-02 text.

**Recommendation to planner:** do NOT factor out a `_operator_errors.py` module. Adding a third module introduces a fresh circular-import surface (cli.py imports `_runner`, which already houses `_emit_operator_error`, while cli.py also exports the validation mapper). The lazy-import seam at `_plugin.py:184` is the established pattern in this codebase; the SHIM-04 branch lands cleanly under it.

**Reference asset:** `tests/framework/unit/test_config_sdet_field.py` already invokes `_emit_operator_error_for_validation` directly with a missing-field error and asserts the SAFE-03 output. This test file is a ready-made template for the new SHIM-04 branch coverage (operator pins exact `next_step` text per D-02, and asserts `typer.Exit(code=2)`).

## D-08 Resolution — Visibility Upgrade Mechanism

**Verdict:** install a scoped `warnings.formatwarning` override inside `_plugin.pytest_configure`, applied ONLY when the `MCPTF_CONFIG_FILE` deprecation fires. The override prepends a red `[mcp-contracts]` prefix and renders the warning body on its own line, isolated from pytest's default `<file>:<line>: DeprecationWarning: <msg>` shape.

**Evidence:**

- **No existing formatwarning override.** Grep across `src/mcp_test_framework/`: zero hits for `formatwarning`. Phase 25's deprecation-warning visibility work did not ship one — it shipped the per-shim `warnings.warn(..., stacklevel=2)` pattern only.
- **`_reporter.py` is opt-in via `--mcp-domain-ui`.** The reporter is OFF by default (`_reporter.py:103` default="off"); under bare `pytest` (the common library-mode invocation) it never initializes. Tying the visibility upgrade to the reporter would leave the warning unstyled on every non-domain-UI invocation — which is the path most operators actually hit. The reporter has no shared banner/header hook this warning could plug into without first opting the reporter into "always-on" mode (out of scope, regression risk).
- **After v1.5, this is the LAST DeprecationWarning the framework fires.** Phase 32 deletes all six fixture-alias DeprecationWarnings in `_plugin.py:406-475`, the `_warn_sdet_flag` callback in `cli.py:644-657`, the `gen-sdet-classes` shim in `cli.py:1419-1438`, and the `sdet/__init__.py` package-import warning. The `_deprecated_script.py` console-script warning is dropped with the script in SHIM-08 (Phase 32). The `MCPTF_CONFIG_FILE`-set warning (D-06) is the sole survivor. A formatwarning override scoped to this one warning has zero collateral surface to manage.
- **Phase 35 SHIM-09 regression gate grandfathering is already locked** (D-09 / context per `.planning/REQUIREMENTS.md`). The gate must exempt the single `_plugin.py` `MCPTF_CONFIG_FILE` site until v1.6 capstone; the formatwarning override lives in the same scope, no separate grandfathering needed.

**Smallest delta — concrete shape:**

Inside `_plugin.pytest_configure`, replace the existing `warnings.warn(...)` block (current `_plugin.py:148-156`) with:

```python
if os.environ.get("MCPTF_CONFIG_FILE"):
    _original_formatwarning = warnings.formatwarning

    def _mcptf_formatwarning(message, category, filename, lineno, line=None):
        # Operator-tone single-block render. Bypasses pytest's default
        # "<file>:<line>: DeprecationWarning: <msg>" shape so the warning
        # is unambiguously distinct from pytest's own deprecation chatter.
        return f"\n[mcp-contracts] {message}\n\n"

    warnings.formatwarning = _mcptf_formatwarning
    try:
        warnings.warn(
            "MCPTF_CONFIG_FILE is set in your environment but no longer "
            "honored as of v1.5; configure via "
            "`[tool.pytest.ini_options] mcp_config_file = PATH` in "
            "pyproject.toml or pass `--config PATH` to "
            "`mcp-contracts run`.",
            DeprecationWarning,
            stacklevel=2,
        )
    finally:
        warnings.formatwarning = _original_formatwarning
```

**Why scoped restoration (the `try/finally`) matters:** pytest's `_pytest.warnings` plugin sets its own formatter at session start; a leaked override would affect every subsequent operator-authored test that emits a warning. The `try/finally` confines the override to the one `warn()` call and restores pytest's hook on exit.

**Optional color upgrade:** if the planner wants ANSI red on terminals, gate behind `sys.stderr.isatty()` and wrap the `[mcp-contracts]` prefix with `\x1b[31m...\x1b[0m`. Recommended for Phase 31 — single conditional, no new dependency, degrades cleanly to plain text on Windows cmd.exe pre-VT or under stdout redirection.

**Reference asset:** the `_reporter.py:147-151` `sys.stdout.reconfigure(encoding="utf-8")` pattern is the closest template — same defensive-try/except style, same scoped responsibility. Mirror that ergonomic.

## D-10 IPC Channel Verification

**Verdict:** `-o mcp_config_file=PATH` works correctly. The mechanism is **already shipped and in production use as of Phase 27**; no spike needed.

**Evidence (current HEAD):**

- `_runner._build_pytest_args:168-177` already passes `["-o", f"mcp_config_file={mcp_config_path}"]` to the subprocess pytest argv whenever the CLI resolver returned a non-None path:
  ```python
  if mcp_config_path is not None:
      args.extend(["-o", f"mcp_config_file={mcp_config_path}"])
  ```
- `_plugin.pytest_configure:159-203` reads `mcp_config_file` via `config.getini("mcp_config_file")`. `pytest -o key=value` runtime override sets the ini value BEFORE `pytest_configure` runs (pytest applies `-o` overrides during ini-source resolution at session-start, before any plugin hook fires). The plugin sees the override unconditionally.
- `cli.py:run:934-940` already invokes `_runner.run_pytest_subprocess(..., mcp_config_path=resolved, ...)` with the resolved path, threading it through both the `--raw` and default branches.

**Plugin-load-order risk: none.** The plugin is entry-point-registered via `[project.entry-points.pytest11]` in `pyproject.toml`, so pytest loads it before any operator-defined `conftest.py`. `pytest_addoption` (which calls `parser.addini("mcp_config_file", ...)`) runs during pytest's plugin-collection phase — strictly before `pytest_configure` and strictly before runtime `-o` overrides apply. The ini key is always registered by the time the override is parsed.

**Quoting risk: none.** `subprocess.run` (used by `_runner.run_pytest_subprocess`) takes a list and bypasses shell interpretation entirely. Paths with spaces, special chars, or non-ASCII bytes flow through untouched.

**Fallback recommendation (per D-10):** NOT needed. The `_MCPTF_*` private env-var fallback is not required — the mechanism is verified working.

**One caveat for the planner:** after SHIM-05 lands, the `mcp_config_path` kwarg threading in `_runner._build_pytest_args:168-177` MUST stay. It is the ONLY surviving IPC channel between cli.py's resolver and the in-subprocess plugin. The planner should add a guard test under `tests/framework/` pinning that `mcp-contracts run --config PATH ...` produces a subprocess argv containing `["-o", "mcp_config_file=PATH"]`. The existing `tests/framework/unit/test_runner_migration.py` Phase 27 D-11 case (lines 162-222 — "resolver does NOT write `MCPTF_CONFIG_FILE`") is the regression sibling; add a positive assertion alongside it.

## Self-Test Inventory (V1DROP-04 Classification per D-12)

DELETE-class: test pins migration-walkthrough text specifically.
RELAX-class: test asserts structural operator-tone shape — relax body assertion, keep exit-code + shape assertions.
SDET-class: test embeds `sdet:` YAML in test fixtures — must flip to `test_code:` (mechanical) regardless of DELETE/RELAX.

| File | Lines | Pinned text | Disposition |
|------|-------|-------------|-------------|
| `tests/framework/unit/test_migration_doc.py` | entire file (58 lines) | Asserts `docs/MIGRATION-v1-to-v2.md` exists + contains "version: 2", "opt every tool in", etc. | **DELETE** — file is the SAFE-07 regression for a doc that no longer exists |
| `tests/framework/unit/test_error_style.py` | L36-41 `test_error_style_contains_safe_06_message` | `"docs/MIGRATION-v1-to-v2.md" in text` | **RELAX** — drop the migration-doc assertion; keep `"### Config uses an older schema version"` + `"config file uses an older format:"` + `"schema version 2"` if those stay in the updated ERROR-STYLE.md, ELSE swap to assert the D-11 generic wording |
| `tests/framework/unit/test_error_style.py` | L60-71 `test_error_style_safe_04_body_matches_cli_wiring` | Pins `MCPTF_CONFIG_FILE` typo error body in cli.py | **DELETE** — the entire `_load_config` Branch 2 is removed in SHIM-05; the pinned text disappears with it |
| `tests/framework/unit/test_error_style.py` | L74-86 `test_error_style_safe_06_body_matches_cli_wiring` | Pins `"docs/MIGRATION-v1-to-v2.md"` + `"in v1 a tool with no entry runs by default, in v2 it skips"` in cli.py | **REWRITE** — replace assertion body with D-11 verbatim: `"unsupported config version"`, `"this build supports schema version 2"`, `"config-init -o config.yaml"` |
| `tests/framework/unit/test_cli_errors.py` | L96-126 `test_load_config_validation_error_version` | Loose `"schema version" in err or "older format" in err or "unsupported" in err` | **NO CHANGE** — already permissive enough to accept the D-11 wording (note line 121 includes `"unsupported"`) |
| `tests/framework/unit/test_cli_errors.py` | L275-285 `test_safe_04_mcptf_config_file_typo_exits_2` | Asserts typo'd `MCPTF_CONFIG_FILE` → exit 2 with `MCPTF_CONFIG_FILE` in stderr | **DELETE** — env-var route gone; behavior under removal |
| `tests/framework/unit/test_cli_errors.py` | L360-419 `test_safe_06_v1_config_emits_locked_migration_message` + `test_safe_06_v1_config_via_env_var_emits_locked_migration_message` | Pins `"docs/MIGRATION-v1-to-v2.md"`, `"in v1 a tool with no entry"`, `"schema version 2 (opt-in"`, `"config-init -o config.yaml.new"` | **REWRITE** — first test: swap to D-11 text + exit code 2 + source-label substitution. Second test: DELETE (uses `MCPTF_CONFIG_FILE` env-var which is removed) |
| `tests/framework/unit/test_cli_errors.py` | L259-273 `test_safe_03_no_config_found_fails_loud_with_locked_message` | Pins SAFE-03 wording (no-config-found) | **NO CHANGE** — SAFE-03 stays |
| `tests/framework/unit/test_cli_errors.py` | L286-307 `test_safe_02_cwd_autodiscovery_picks_up_local_config` | Embeds `sdet:` YAML | **SDET-fix** — flip `'sdet:\n  generated_root: ...'` → `'test_code:\n  generated_root: ...'` |
| `tests/framework/unit/test_cli_errors.py` | L147-217 (two MCP-spawn-failure tests) | Embed `sdet:` YAML in fixtures | **SDET-fix** (mechanical key swap; behavior assertions unchanged) |
| `tests/framework/unit/test_runner_migration.py` | L88-152 `test_mcptf_config_file_path_pointer_fallback` + similar | Uses `monkeypatch.setenv("MCPTF_CONFIG_FILE", ...)` AND asserts bare `Config()` reads it | **DELETE** — entire path-pointer fallback is removed in SHIM-05 |
| `tests/framework/unit/test_runner_migration.py` | L162-222 `test_resolver_does_not_write_mcptf_config_file` | Asserts the resolver does NOT mutate env (Phase 27 D-11 regression) | **KEEP + STRENGTHEN** — flip to "resolver does not READ env (D-05 post-SHIM-05)" with positive `-o mcp_config_file=PATH` assertion on subprocess argv |
| `tests/framework/unit/test_config.py` | L105-220 (multiple) | Embeds `MCPTF_CONFIG_FILE` env-var clears + `version: 2` YAML; line 238 has `version: 1` test | **SCRUB + DELETE-v1** — drop env-var-related setup; delete the `version: 1` rejection test (SHIM-05 removes the route, V1DROP-03 rewrites the message — `_validate_version` still rejects v1 so a generic "exit 2 on version != 2" test is fine to keep, but pinning the old wording must go) |
| `tests/framework/unit/test_config_init.py` | L60-67 | Asserts scaffold body contains `version: 2` (not v1) | **NO CHANGE** — already aligned with v2 |
| `tests/framework/unit/test_config_init.py` | L100-163 | `MCPTF_CONFIG_FILE` env-var cleanup setup | **SCRUB** — drop the delenv block once the env-var route is gone (env var no longer affects loader) |
| `tests/framework/unit/test_dotenv_example.py` | L75-77 | `assert "MCPTF_CONFIG_FILE" in text` (asserts `.env.example` documents the env var) | **DELETE the assertion** — `.env.example` scrub removes the var |
| `tests/framework/unit/test_mcp_config_fixture.py` | L12 | Comment references env-var fallback | **NO CHANGE to behavior — DOCSTRING SCRUB only** |
| `tests/framework/unit/test_homelab_config.py` | L71-89 | Embeds `sdet:` YAML | **SDET-fix** (mechanical key swap) |
| `tests/framework/unit/test_list_tools_format.py` | L204-212 | Embeds `sdet:` YAML + MCPTF_CONFIG_FILE delenv | **SDET-fix + env-cleanup-scrub** |
| `tests/framework/unit/test_runner_explain.py` | L69-73 | Embeds `sdet:` YAML | **SDET-fix** |
| `tests/framework/unit/test_sdet_cli.py` | L38-283 | Embeds `sdet:` YAML + uses `monkeypatch.setenv("MCPTF_CONFIG_FILE", ...)` extensively | **SDET-fix + env-route-scrub** — this is a Phase 32 SHIM file (sdet CLI), so the file itself will be touched again next phase. Limit Phase 31 changes to the YAML key swap + env-var setup removal; the `--sdet` flag deletion is Phase 32 SHIM-02 scope |
| `tests/framework/unit/test_sdet_fixtures.py` | L219-282 | Same shape as test_sdet_cli.py | **SDET-fix + env-route-scrub** (same boundary; full deletion is Phase 32) |
| `tests/framework/unit/test_codegen_integration_mock.py` | L19 | Docstring mentions `cfg.sdet.generated_root` | **DOCSTRING SCRUB** — flip to `cfg.test_code.generated_root` |
| `tests/framework/unit/test_gen_sdet_classes_cli.py` | L73-203 | Uses `MCPTF_CONFIG_FILE` setenv + cfg.sdet refs | **DEFER to Phase 32** — entire `gen-sdet-classes` shim is removed there (SHIM-03); Phase 31 only does the SDET-fix in test fixtures if the test still runs |
| `tests/framework/unit/test_gen_sdet_classes_config_driven.py` | L44 | `monkeypatch.delenv("MCPTF_CONFIG_FILE", ...)` | **DEFER to Phase 32** (same reasoning) |
| `tests/framework/unit/test_gen_test_classes_pyproject_config.py` | L69, L105 | `monkeypatch.setenv("MCPTF_CONFIG_FILE", ...)` to exercise env-var fallback | **DELETE the env-var-fallback test cases**; keep pyproject-resolution tests |
| `tests/framework/test_config_init_cli.py` | L65-83, L95, L128 | Asserts `"version: 1" in result.output` (test for OLD behavior before v2 flip) — and L128 uses `MCPTF_CONFIG_FILE` setenv | **DELETE the v1-output assertions** (this is stale Phase 13 test — the comment at L65 says `D-22 / TOOLCFG-02 / TOOLCFG-04: default mode prints version: 1`, the test is actually wrong for v1.5; investigate whether it was already passing or skipping); scrub env-var setenv |
| `tests/framework/test_runner_verbosity.py` | L174-177 | Embeds `sdet:` YAML | **SDET-fix** |
| `tests/framework/test_runner_subprocess.py` | L218-241 | Embeds `sdet:` YAML (twice) | **SDET-fix** |
| `tests/framework/test_tool_config.py` | L151-388 | Embeds `version: 2` + `sdet:` + `MCPTF_CONFIG_FILE` setenv (multiple cases) | **SDET-fix + env-cleanup-scrub** — note this is the file that motivates Backlog 999.5 (deep-merge pollution); env-var removal closes the SURFACE but the underlying class-of-bug survives; Phase 34 ISOL-05 will revisit |
| `tests/framework/test_cli_reporter_rewire.py` | L129 | `version: 2` literal | **NO CHANGE** |
| `tests/framework/test_reporter_plugin.py` | L40 | `version: 2` literal | **NO CHANGE** |
| `tests/framework/smoke/test_mcp_client_teardown_regression.py` | L78, L89 | Uses `MCPTF_CONFIG_FILE` env-var to point at config | **REWRITE** — use `["-o", "mcp_config_file=..."]` instead, or use `--config PATH` if the smoke test invokes the CLI |

**Estimate:** ~14 framework test files touched, ~6 with substantive logic changes, the rest mechanical key-swaps or env-var setup removals. `test_migration_doc.py` is the only outright file deletion in `tests/`.

**Phase 32 deferral note:** `test_sdet_cli.py`, `test_sdet_fixtures.py`, `test_gen_sdet_classes_*.py`, `test_runner_sdet_kwarg.py` will be touched again in Phase 32 (SHIM-01..03 surface-shim removals). Phase 31 should limit edits there to YAML-key swaps (`sdet:` → `test_code:`) and env-var setup scrubs only — DO NOT delete or restructure those test files in Phase 31 even if they look stale, because Phase 32's SHIM removal will re-touch the same code.

## Doc / Config-File Inventory (Beyond README + ERROR-STYLE + LIBRARY-MODE)

| File | Lines | What needs scrubbing |
|------|-------|----------------------|
| `README.md` | L73, L331, L343, L350, L609 | Remove all `MCPTF_CONFIG_FILE` mentions; replace "migration from `MCPTF_CONFIG_FILE`" callouts with direct doc anchors to `mcp_config_file` ini key |
| `docs/ERROR-STYLE.md` | L68 | Delete `"docs/MIGRATION-v1-to-v2.md"` reference inside SAFE-06 message section; rewrite that message section to the D-11 generic wording |
| `docs/LIBRARY-MODE.md` | L14, L118, L293-315 | L14 + L118: scrub passing mention; L293-315: DELETE the entire `## Migration from MCPTF_CONFIG_FILE env var` section (23 lines) |
| `docs/MIGRATION-v1-to-v2.md` | entire file | DELETE on disk (V1DROP-01) |
| `docs/EXTENDING.md` | L211 | Scrub `"MCPTF_CONFIG_FILE / --config"` reference — replace with `"--config"` only |
| `docs/SDET-AUTHORING.md` | — | Grep returned zero matches; **no scrub needed** in Phase 31 (this doc is renamed/replaced by TEST-CODE-AUTHORING in Phase 32 SHIM scope) |
| `docs/TEST-CODE-AUTHORING.md` | — | Grep returned zero matches; **no scrub needed** |
| `docs/mcp_test_framework_mvp_spec.md` | — | Grep returned zero matches; **no scrub needed** |
| `config.example.yaml` | (current HEAD) | Already at `version: 2`, already uses `test_code:` — **NO CHANGE NEEDED**. Verified clean at HEAD; the `# set MCPTF_CONFIG_FILE=...` comment shown in worktrees is from older commits, not present in the parent's checked-in file |
| `.env.example` | L15-16 | DELETE the `# Path to a YAML config file (read by --config / MCPTF_CONFIG_FILE).` comment and the `# MCPTF_CONFIG_FILE=./config.yaml` line |
| `examples/homelab-mcp.yaml` | L2 | Edit the header comment from `# Copy to config.yaml at your project root, or point MCPTF_CONFIG_FILE at it.` to `# Copy to config.yaml at your project root, or pass via --config / [tool.pytest.ini_options] mcp_config_file.` |
| `config.scratch.yaml` | L2 | Repo-root artifact (uncommitted? — appears in git-status `??`). Operator's own scratch file; **out of Phase 31 scope** unless the operator wants the line updated as cleanup |

**Worktree noise note:** the grep results show ~50 hits under `.claude/worktrees/agent-*/` for old `# set MCPTF_CONFIG_FILE` comments. These are stale snapshots of older commits; **ignore them**. Phase 31 changes only the parent's HEAD files; worktrees re-sync naturally when the next agent task runs against current HEAD.

## Verified Line Numbers (Current HEAD)

| File | CONTEXT.md cite | Verified line(s) | Notes |
|------|-----------------|------------------|-------|
| `config.py` | L52 (`extra='forbid'`) | L50-53 (SettingsConfigDict block) | Confirmed |
| `config.py` | L58-180 (test_code field + alias + pre-scan + validator) | L58-191 | Slightly wider than cited; includes the `model_validate` override |
| `config.py` | L195-203 (`_validate_version`) | L193-203 | Confirmed |
| `config.py` | L226-247 (`settings_customise_sources` IPC fallback) | L205-251 (whole method); MCPTF_CONFIG_FILE fallback at L229-235 | Confirmed at L229-235 |
| `config.py` | L254-310 (`_check_legacy_sdet_key_in_yaml`) | L254-312 (whole helper) | Confirmed |
| `cli.py` | L14 (module docstring) | L13-21 (docstring `_load_config` precedence block) | Confirmed |
| `cli.py` | L292-315 (v1→v2 migration error path) | L292-315 (inside `_emit_operator_error_for_validation`) | **Confirmed verbatim** |
| `cli.py` | L449-540 (`_load_config` resolver Branch 2) | L442-576 (whole resolver); Branch 2 (env-var) at L521-538 | Branch 2 confirmed at L521-538 |
| `cli.py` | L670 (`--config` help text reference) | L670 (`run` command's `--config`) | Confirmed |
| `cli.py` | L1023 | L1023 (`list-tools` command's `--config`) | Confirmed |
| `cli.py` | L1118 | L1118 (`config-init` command's `--config`) | Confirmed |
| `cli.py` | L1296 | L1295-1297 (`gen-test-classes` command's `--config`) | Confirmed (multi-line help string starting at L1295) |
| `cli.py` | L1425 | L1425 (`gen-sdet-classes` shim's `--config`) | Confirmed; this whole shim block (L1419-1438) gets deleted in Phase 32 SHIM-03, not Phase 31. Phase 31 only updates the help-text string here |
| `cli.py` | (additional) L1308 | L1308 (docstring of `gen-test-classes` body: `"Honors the standard config-source precedence: --config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud."`) | **NEW finding** — not in CONTEXT.md citation list; add to the SHIM-05 scrub list |
| `cli.py` | (additional) L1323 | L1322-1323 (docstring: `"resolved against CWD (mirrors the MCPTF_CONFIG_FILE convention)"`) | **NEW finding** — same scope |
| `_plugin.py` | L135-160 (`MCPTF_CONFIG_FILE` DeprecationWarning) | L135-156 (docstring at L135; emit block at L147-156) | Confirmed; D-06 rewrite target |
| `fixtures.py` | L103 | L102-105 (`mcp_config` docstring referencing `MCPTF_CONFIG_FILE` path-pointer in resolver) | Confirmed |
| `fixtures.py` | L162 | L160-164 (`_session_needs_preflight` docstring) | Confirmed — references `MCPTF_CONFIG_FILE` workaround in historical note |
| `fixtures.py` | L212-235 | L208-239 (`_preflight` docstring + Check 1 emit) | Confirmed — `MCPTF_CONFIG_FILE` hint in the pytest.exit message at L231-238 |
| `fixtures.py` | L321-331 | L321-333 (Check 3 fallback hint) | Confirmed — `MCPTF_CONFIG_FILE` hint in the conditional handler |
| `models.py` | L207 | L206-209 (`MCPTF_CONFIG_FILE` convention comment in TestCodeConfig docstring) | Confirmed; comment scrub only |

**Drift summary:** all CONTEXT.md citations are accurate; two new touch-points were uncovered in cli.py docstrings (L1308 + L1322-1323) — add to the SHIM-05 scrub list.

## Implementation Order / Sequencing Notes

There are minimal ordering constraints. The work groups into four near-independent task families, but two safety rails apply:

**Strict ordering constraint 1 — V1DROP-01 (delete migration doc) BEFORE V1DROP-02/03 (scrub cross-refs):**
If the planner reverses this, the regression test `test_migration_doc.py` will still be passing while `cli.py` no longer references the doc — confusing failure mode. Delete the doc + delete the test in the same task; THEN scrub cross-refs.

**Strict ordering constraint 2 — V1DROP-03 message rewrite BEFORE the V1DROP-04 self-test rewrite:**
Otherwise `test_error_style.py::test_error_style_safe_06_body_matches_cli_wiring` and `test_cli_errors.py::test_safe_06_v1_config_emits_locked_migration_message` will fail when the doc/cross-ref scrub lands but the messages haven't been rewritten yet. Better: rewrite the message + relax/delete the test in the same wave.

**Strict ordering constraint 3 — SHIM-04 alias removal in config.py + the new error-mapper branch in cli.py land together.**
If the planner removes the alias first without adding the branch, an operator's `sdet:` config will surface as a generic Pydantic `extra_forbidden` error without the operator-tone wording — a regression vs the pre-Phase-31 behavior.

**No constraint between SHIM-04 and SHIM-05:** the two families are orthogonal. The `extra='forbid'` model already exists; SHIM-04 only removes the alias + pre-scan that were widening it. SHIM-05 only touches the env-var route. They can land in either order or in parallel.

**No constraint between SHIM-04/05 and V1DROP-01..04:** the v1-schema decommission is a doc-and-message rewrite layer that does not depend on the config-surface changes.

**Recommended task-grouping for the planner (four task groups, no strict ordering between them except as flagged above):**

1. **Group A — SHIM-04 (alias removal):** config.py edits (delete alias, validator, pre-scan, `model_validate` override); cli.py new branch in `_emit_operator_error_for_validation`; new test under `tests/framework/unit/` pinning the D-02 message; sdet-key swaps in fixture YAMLs (mechanical, ~10 files).
2. **Group B — SHIM-05 (env-var unwiring):** config.py settings_customise_sources fallback removal; cli.py `_load_config` Branch 2 removal + 5 help-text edits + 2 docstring scrubs; fixtures.py 4-site hint scrub; models.py L207 comment scrub; _plugin.py DeprecationWarning rewrite + formatwarning override (D-08); .env.example scrub + examples/homelab-mcp.yaml header edit; self-test scrubs (env-var setup removal, env-var typo test deletion).
3. **Group C — V1DROP-01..03 (migration doc decommission):** delete `docs/MIGRATION-v1-to-v2.md`; delete `tests/framework/unit/test_migration_doc.py`; rewrite `_emit_operator_error_for_validation` version branch body (cli.py L292-315) to D-11 wording; scrub README + ERROR-STYLE + LIBRARY-MODE + EXTENDING cross-refs.
4. **Group D — V1DROP-04 (self-test relaxation):** apply DELETE/RELAX/REWRITE dispositions from the inventory table above. This group depends on Groups A/B/C landing first (the assertions reference rewritten message text).

Group A + Group B + Group C can land in parallel; Group D lands last (verification gate).

**Cross-cutting work-saver:** the YAML-key swap (`sdet:` → `test_code:`) inside test fixtures is mechanical and identical across ~10 files. A single sed-equivalent task can land that in one commit. SEED-022 does not apply (these are test-internal fixtures, not framework code).

## Risks + Landmines

1. **Pytest plugin double-load under in-process `pytest.main()`.** The reporter plugin (`_reporter.py:152-170`) already has a `WR-04` defensive re-init guard for in-process re-entry. The new `formatwarning` override (D-08) is restored via `try/finally`, so even if `pytest_configure` fires twice the override is cleanly scoped to a single `warnings.warn(...)` call window. Low risk.

2. **`warnings.formatwarning` interaction with pytest's own warning filter.** Pytest installs `_pytest.warnings.WarningsChecker` which captures warnings into reports — it does NOT replace `warnings.formatwarning`. A scoped override inside `pytest_configure` modifies the rendering path only during the one `warn()` call; pytest's filter still captures the warning into its session warnings list (the `--with-framework` JUnit XML will still see the deprecation as a warning). Verified by reading the Python `warnings` source — `warnings.warn()` calls `warnings.formatwarning()` during the `showwarning()` path; pytest hooks at `showwarning()`, not at `formatwarning()`. Low risk.

3. **Test suite ordering — `test_config.py` line 238 has a pinned `version: 1` test.** If the planner doesn't catch this in the V1DROP-04 sweep, the rewritten validator message will cause a confusing failure (the test will fail because the message text changed, not because the rejection itself changed). Inventory above flags it explicitly.

4. **`test_runner_migration.py` Phase 27 D-11 sibling.** This test currently asserts the resolver does NOT mutate `os.environ["MCPTF_CONFIG_FILE"]`. After SHIM-05, the resolver also doesn't READ it. The test still passes as-is (the assertion is "doesn't write"; doesn't-read is a strictly stronger property) — but it's now over-narrow. Recommend the planner strengthen it to also assert positive `-o mcp_config_file=PATH` injection in the subprocess argv.

5. **Worktree contamination from old commits.** Grep hits in `.claude/worktrees/agent-*/` are noise from older snapshots. The planner should configure test-runner working-directory expectations to ignore worktrees. The framework's existing `tests/framework/unit/test_no_planning_ids_in_src.py` and friends already use repo-root walking with `Path(__file__).resolve().parents[3]`, so no special handling needed.

6. **`config.example.yaml` IS already v2-clean at HEAD.** Operator-facing yaml at the parent's HEAD shows `version: 2` and `test_code:` correctly. Only the worktree-snapshot greps showed `version: 1` + `MCPTF_CONFIG_FILE` legacy comments. The planner should NOT panic-edit `config.example.yaml` — it's correct.

7. **`tests/framework/test_config_init_cli.py:65-95` pins `version: 1` in scaffold output.** This test was written for the pre-v2 flip (Phase 13 SAFE-06 inverted it). It MAY currently be xfailing or fully broken — the planner should verify its current status before treating it as load-bearing. Either fix (flip to `version: 2`) or delete during V1DROP-04.

8. **SEED-022 guardrail honored.** No proposed rewrite drifts toward SUT-specific guidance. The D-02 `sdet:`-rejection text ("rename the `sdet:` key to `test_code:` in your config.yaml") is generic config-shape guidance. The D-11 v1-rejection text ("run `mcp-contracts config-init -o config.yaml` to generate a current scaffold") is generic operator-recovery guidance. The D-06 `MCPTF_CONFIG_FILE`-detection text ("configure via `[tool.pytest.ini_options] mcp_config_file = PATH` or pass `--config PATH`") is generic surface guidance. Compliant.

9. **Phase 35 SHIM-09 grandfathering: ONE survivor in src/.** After Phase 31, the regression-gate sweep will find exactly ONE `MCPTF_CONFIG_FILE` match in `src/mcp_test_framework/_plugin.py:148` (the detection). The gate must allow this until v1.6. The CONTEXT.md D-09 already locks this; the planner should drop a TODO/comment marker in `_plugin.py` at the detection site so Phase 35's plan author finds it without re-discovering the constraint.

10. **`_isolation.py` strips `MCPTF_CONFIG_FILE`-prefixed env vars from MCP subprocesses.** Worth verifying the planner adds no new env-var to the allowlist — and worth a quick grep of `_isolation.py` for `MCPTF_*` (likely just `MCP_*` allowlisted; the env-var removal shouldn't touch the isolation surface). NOT a Phase 31 deliverable; just a "don't accidentally widen" note.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Pytest's `-o key=value` runtime ini override is parsed BEFORE `pytest_configure` runs | D-10 verification | LOW — verified by reading `_runner._build_pytest_args` + `_plugin.pytest_configure` which already use the mechanism in production; failure mode would already be visible in Phase 27 dogfood |
| A2 | `warnings.formatwarning` override inside `pytest_configure` only affects the immediate `warn()` call when wrapped in `try/finally` | D-08 recommendation | LOW — `warnings` module is stdlib, behavior pinned by Python language spec; restoration is deterministic |
| A3 | `tests/framework/unit/test_config_sdet_field.py` is a valid template for the SHIM-04 branch test | D-04 reference asset | LOW — file directly invokes `_emit_operator_error_for_validation`, identical shape needed for the new branch |
| A4 | `config.example.yaml` at parent HEAD is already at `version: 2` + uses `test_code:` | Doc inventory | VERIFIED via direct read |
| A5 | The `MCPTF_CONFIG_FILE` detection in `_plugin.py:148` is the only DeprecationWarning surviving Phase 32 | D-08 rationale | MEDIUM — depends on Phase 32 fully removing the six fixture aliases + the four CLI/package shims; if Phase 32 partially defers, the formatwarning override may not be unique-but-still-correct |

**Nothing else assumed.** All other claims are file-content reads from current HEAD.

## Project Constraints (from CLAUDE.md)

- **Python 3.14, `uv` for dependency management** — no new deps in Phase 31.
- **MCP transport stdio-only via `stdio_client`** — Phase 31 does not touch MCP transport code; constraint preserved by inaction.
- **Black box: never import from `homelab-mcp`** — Phase 31 does not touch any SUT-interaction code.
- **`pytest-asyncio` strict mode, explicit `@pytest.mark.asyncio` markers** — new SHIM-04 branch test does not need asyncio (pure validation-error test).
- **SEED-022: framework primitives only, no SUT-safety reasoning** — explicitly verified in Risks section above (rewrite #8).
- **Phase scope = phase title** — D-08 visibility upgrade IS in scope per user-locked decision; do not let sub-agent reframe.
- **GSD-workflow gating** — file changes happen under `/gsd-execute-phase`; this research artifact is the input to the planner.

## Sources

### Primary (HIGH confidence)
- Direct reads of current HEAD: `src/mcp_test_framework/config.py`, `cli.py`, `_plugin.py`, `_reporter.py`, `_runner.py`, `fixtures.py`, `models.py`.
- Direct reads of `tests/framework/unit/test_*.py` for the 14 self-tests inventoried.
- Direct read of `docs/ERROR-STYLE.md`, `docs/LIBRARY-MODE.md`, `docs/MIGRATION-v1-to-v2.md`, `docs/EXTENDING.md`, `README.md` (via grep).
- `.planning/phases/31-.../31-CONTEXT.md` (user-locked decisions).
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` (SHIM-04, SHIM-05, V1DROP-01..04 traceability).

### Secondary (MEDIUM confidence)
- Python stdlib `warnings` module behavior (training knowledge + cross-verified against `_reporter.py:147-151` reconfigure pattern in same codebase).

### Tertiary (LOW confidence)
- None — every claim in this research is verified against the current repo or against user-locked CONTEXT.md decisions.

## Metadata

**Confidence breakdown:**
- D-04 verdict: HIGH — direct read of `_plugin.py:182-196` confirms shared mapper.
- D-08 verdict: HIGH — direct grep confirms no existing formatwarning override; mechanism is stdlib-standard.
- D-10 verification: HIGH — mechanism already in production at `_runner._build_pytest_args:168-177` and `_plugin.pytest_configure:159+`.
- Self-test inventory: HIGH for explicit-text matches; MEDIUM for D-12 dispositions (planner may choose differently per assertion).
- Doc inventory: HIGH — grepped exhaustively, line numbers verified.
- Line-number verification: HIGH — every CONTEXT.md citation re-checked against current HEAD.

**Research date:** 2026-05-23
**Valid until:** 2026-06-22 (30 days; the code is stable v1.4-release, Phase 31 work itself will change everything researched here)

## RESEARCH COMPLETE
