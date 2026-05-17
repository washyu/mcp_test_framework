# Phase 28: Codegen output path (CODEGEN) - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

> ⚠️ **REQUIREMENTS.md CODEGEN-LIB-01 SUPERSEDED BY THIS CONTEXT.**
> Discussion rejected the "smart default `<cwd>/tests/_generated/<server_slug>/`" framing entirely. The framework will NOT invent an output path; it fails loud when `cfg.test_code.generated_root` is unset. CODEGEN-LIB-01 needs amending — see `<downstream_impact>` below. Planning should proceed against the decisions in this CONTEXT.md, not against the now-stale REQUIREMENTS / ROADMAP text.

<domain>
## Phase Boundary

`gen-test-classes` writes generated typed Pydantic Params/Response classes to a path the operator declared in `cfg.test_code.generated_root`. The framework refuses to silently invent a path, and refuses to write under its own installed-package tree. Phase 28 also closes the seam between the Typer CLI's config resolution and the pytest ini route that Phase 27 made canonical.

**What ships in Phase 28:**

1. **Pre-handshake site-packages guard** (CODEGEN-LIB-02) — `gen-test-classes` resolves `cfg.test_code.generated_root` to absolute, compares against `Path(mcp_test_framework.__file__).parent.parent`, and aborts with operator-tone error BEFORE attempting the MCP handshake if the target is a descendant of the framework's own install root.
2. **Non-empty-directory overwrite prompt** — at command time, if the resolved target dir is non-empty, `typer.confirm(...)` asks the operator before wiping. In non-TTY contexts the command aborts with a helpful error (no `--yes` flag).
3. **`gen-test-classes` reads pyproject.toml** — Typer command parses `[tool.pytest.ini_options] mcp_config_file` from the operator's pyproject.toml at command start to find the config, matching pytest's resolution. `--config PATH` still overrides for one-off runs.
4. **CODEGEN-LIB-01 reframed** — current REQUIREMENTS text ("default = `<cwd>/tests/_generated/<server_slug>/`", "`--output-dir` flag") is REMOVED. New text: "fail-loud when `generated_root` unset; operator-tone error names the missing field and points at `mcp-contracts config-init`."
5. **Existing `--config PATH` flag** — preserved as the override.
6. **Operator-tone error refresh** — the current "config error" path for missing `generated_root` is reviewed against `docs/ERROR-STYLE.md` and rewritten to name the field + point at `config-init`.

**Out of scope (deferred to later phases or v1.5):**

- Smart default-path inference (`tests/_generated/<slug>/`, `tests/test_code/_generated/`, etc.) — explicitly rejected; the framework knows nothing about the operator's project layout.
- `--output-dir` CLI flag — explicitly rejected; config is the sole source of truth.
- `--yes` / `--force` flag for the overwrite prompt — explicitly rejected; operators clean their dirs manually in CI.
- `gen-test-classes -o key=value` pytest-style runtime overrides — deferred (covered by `--config PATH` for the only use case that matters).
- `MCPTF_CONFIG_FILE` env var handling in `gen-test-classes` — kept on the v1.5 cleanup list with the rest of the deprecation shims; Phase 28 emits the same deprecation warning Phase 27 introduced (no special handling here).
- `config-init` scaffold rewrite — keeps emitting `test_code.generated_root: tests/test_code/_generated` verbatim. Operators inherit a working value; no change.
- Schema-level validation beyond today's "not empty string" check (no `..`-rejection, no relative-only enforcement) — pushed to runtime command-layer checks per D-04.
- Slug-rebase-escape defense (`out_root / slug` check post-handshake) — not added; appending a path segment never escapes upward, so the pre-handshake check is sufficient.

</domain>

<decisions>
## Implementation Decisions

### Default-path policy

- **D-01:** The framework does NOT invent a default output path. `cfg.test_code.generated_root` stays REQUIRED in `TestCodeConfig` (today's `Field(...)` behavior) with fail-loud on absence. Driver: operator-as-visionary call that the framework cannot guess project layout — "we can't assume we know where the tests should be in a project." Memory traceability: `feedback_scaffold_completeness` (scaffolds must be runnable, not partial), `project_vibe_coded_persona` (operator may not know what they want, but framework guessing for them is worse than asking explicitly), Phase 27 D-09/D-11 (kill-magic posture). CODEGEN-LIB-01 needs amending — see `<downstream_impact>`.
- **D-02:** When `generated_root` is unset, the fail-loud error is operator-tone, names the missing field by full path (`test_code.generated_root`), and points at `mcp-contracts config-init` for scaffold generation. Follows `docs/ERROR-STYLE.md`. Mirrors the existing missing-required-key path; the planner verifies whether today's error already says this or needs a rewrite.
- **D-03:** No `--output-dir` CLI flag. One source of truth: `cfg.test_code.generated_root`. Operators who want per-invocation redirection point at a different config file via `--config PATH`. Matches Phase 27 D-11's "one config route end-to-end" principle.

### Field semantics

- **D-04:** `generated_root: Path = Field(...)` stays as-is at the schema level. The empty-string-rejection field validator stays. No additional pydantic-level validators (no absolute/relative enforcement, no `..`-segment rejection). Everything else — existence, writability, site-packages guard, non-empty-directory prompt — happens at command time in `cli.py:gen_test_classes`. Pydantic stays a dumb pipe; policy lives in the CLI layer.

### Pre-write target-directory prompt

- **D-05:** At command time, after the site-packages guard but before any file write, `gen-test-classes` inspects `out_root` (the fully resolved target including slug). If the dir does not exist → create silently. If it exists but is empty → write silently. If it exists with files → prompt: `typer.confirm("N files exist in <path>. Overwrite? [y/N]")`. Operator must confirm to proceed.
- **D-06:** In non-TTY contexts (CI, scripts, piped input), `gen-test-classes` detects the missing TTY at the prompt step and aborts with a helpful operator-tone error: "target directory `<path>` is non-empty and gen-test-classes cannot prompt for confirmation in this environment; clean the directory manually and re-run." Exit code 2 (same as other config / setup errors). NO `--yes` / `--force` flag — the only way to overwrite in CI is to delete the dir first. Strongest "never destroy data" posture; matches user-as-visionary's heavy-hand stance on framework-driven file writes.

### Site-packages guard (CODEGEN-LIB-02)

- **D-07:** Strict guard. Resolve `out_root` to absolute, compare against `Path(mcp_test_framework.__file__).parent.parent` (the framework's sys.path entry root), abort with operator-tone error if `out_root` is a descendant. Single robust check that works uniformly across: standard site-packages installs, editable installs (`pip install -e .`), vendored copies, Windows + Linux + venv + uv + pyz environments. No special-casing of `site-packages` / `dist-packages` directory names.
- **D-08:** Guard fires BEFORE the MCP handshake — at command start, immediately after `cfg` is loaded and `out_root` resolved. Server is never started if the target is unsafe. Cheapest, fastest, no subprocess-died noise. Per REQUIREMENTS "at command-start" literal text. The slug-rebase case (`out_root / slug` could escape) is impossible (appending a segment never moves the target outside its parent), so a post-handshake recheck adds zero safety.
- **D-09:** No bypass. No `allow_unsafe_generated_root` config knob, no `--unsafe` flag. Operators who hit the guard must change `generated_root` to a path outside the framework's install root. Consistent with the D-01 / D-03 "kill magic, no escape hatches" posture.
- **D-10:** Guard error is operator-tone per `docs/ERROR-STYLE.md`, names the offending field (`test_code.generated_root`), shows the resolved-absolute target path, names the framework's detected install root, and tells the operator to set the field to a path inside their own project tree. Returncode 2.

### `gen-test-classes` config resolution

- **D-11:** `gen-test-classes` reads `[tool.pytest.ini_options] mcp_config_file` from the operator's pyproject.toml at command start. Same single source of truth as pytest. `--config PATH` still overrides for one-off runs. New precedence ladder for the Typer command: `--config PATH` (flag) > `[tool.pytest.ini_options] mcp_config_file` (pyproject) > `./config.yaml` autodiscovery > fail-loud.
- **D-12:** Today's `MCPTF_CONFIG_FILE` env var path in `_load_config()` continues to fire the Phase 27 D-09 deprecation warning. Phase 28 adds no new logic here — env var still works (with warning), still gets removed in v1.5.
- **D-13:** pyproject.toml parsing uses stdlib `tomllib` (Python 3.11+). Fail-soft: if pyproject.toml is missing, malformed, or has no `[tool.pytest.ini_options]` section, fall through to `./config.yaml` autodiscovery silently. No noise for operators who haven't onboarded library mode yet.

### Claude's Discretion

- **`out_root` resolution semantics:** today's code resolves `cfg.test_code.generated_root` against `Path.cwd()` when relative. After D-11 (config found via pyproject.toml), the planner picks whether relative paths resolve against `cwd` (today's convention, matches the `MCPTF_CONFIG_FILE` legacy semantic) or against pyproject.toml's directory (pytest's `inipath`-relative convention, matches Phase 27's `mcp_config_file` resolution). Suggested: pyproject.toml-relative, for consistency with Phase 27. Verify against Phase 27's actual `mcp_config_file` resolution behavior before locking.
- **`config-init` scaffold copy edits:** the existing scaffold writes `test_code.generated_root: tests/test_code/_generated`. Phase 28 likely doesn't need to touch this — but if D-02's error message tells operators to "run `mcp-contracts config-init`," the planner verifies the scaffold value is still sensible and the README / docs reflect the same path as a recommended starting point. No scope creep into scaffold rewrites unless the message goes out of date.
- **Non-empty-dir detection cost:** the prompt only fires if the dir exists and contains files. Planner picks the iteration shape — `any(out_root.iterdir())` (cheapest, one syscall) vs counting files (operator-friendlier message). Suggested: count files for the prompt copy ("N files exist"), short-circuit on first hit if scanning is slow.
- **Guard error: name the framework root or not?** D-10 includes "names the framework's detected install root" — useful for debugging editable-install confusion, but reveals internal layout. Planner picks; suggested: include it, since this is a CLI tool talking to a developer, not an end-user-facing service.

</decisions>

<downstream_impact>
## Downstream Impact (not Phase 28 implementation scope, but planner must surface as separate work)

The D-01 rejection of "smart default" invalidates CODEGEN-LIB-01 as written. These docs need amending — either as a Phase 28 plan (a docs-sweep plan, similar to Phase 27's pattern) or as a quick task before Phase 29 starts.

### REQUIREMENTS.md amendments

- **CODEGEN-LIB-01** — rewrite around fail-loud + operator-tone error. Old text: "Operator who runs `gen-test-classes` from a project with a `tests/` directory gets generated classes under `<cwd>/tests/_generated/<server_slug>/` by default — no config required. Operators in projects without a `tests/` directory get a friendly error directing them to set `cfg.test_code.generated_root` or use `--output-dir`." New text: "Operator who runs `gen-test-classes` without `cfg.test_code.generated_root` set gets a fail-loud operator-tone error naming the missing field and pointing at `mcp-contracts config-init`. No smart default; the framework does not infer project layout. No `--output-dir` flag; `--config PATH` is the only invocation-level override." Add: "Operator running against a non-empty target dir is prompted before overwrite; in non-TTY contexts the command aborts." Add: "`gen-test-classes` resolves the config via the same `[tool.pytest.ini_options] mcp_config_file` route as pytest."
- **CODEGEN-LIB-02** — preserved verbatim. Strict-guard, fail-fast-at-command-start interpretation locked.

### ROADMAP.md amendments

- **Phase 28 Goal text** — currently "`gen-test-classes` writes generated typed classes to a sensible default path inside the operator's project (never into `site-packages/`)." Rewrites to "`gen-test-classes` refuses to invent an output path or write under its own install tree, and reads the same `mcp_config_file` ini route pytest uses." Drop "default path" framing.
- **Phase 28 Success Criteria 1** — currently SC1 is the smart-default + friendly-error spec. Rewrites to: "Operator running `mcp-contracts gen-test-classes` without `cfg.test_code.generated_root` set sees a fail-loud operator-tone error naming the missing field and pointing at `mcp-contracts config-init`. Operator with the field set sees codegen succeed (target dir is created if missing; non-empty target prompts for confirmation; non-TTY non-empty target aborts with a helpful error)."
- **Phase 28 Success Criteria 2** — preserved (site-packages guard, command-start check, friendly error). Refine to specify pre-handshake timing.
- **Phase 28 Success Criteria 3 (NEW)** — add: "Operator who set `[tool.pytest.ini_options] mcp_config_file = PATH` in pyproject.toml sees `mcp-contracts gen-test-classes` use the same config file as `pytest`, without passing `--config`."
- **Phase 30** — no impact. CLI demotion + dogfood verification unchanged.

### Future-deferred items to add

- `MCPTF_CONFIG_FILE` removal stays on v1.5 cleanup list (no change; Phase 28 inherits Phase 27 D-09 deprecation).
- `--yes` / `--force` flag for non-TTY overwrite — explicitly rejected by D-06; do NOT add to deferred-ideas.

</downstream_impact>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & roadmap

- `.planning/PROJECT.md` — Vibe-coded operator persona; library-mode milestone context.
- `.planning/ROADMAP.md` §"Phase 28: Codegen output path (CODEGEN)" — NOTE: SC1 stale per D-01; SC2 preserved with pre-handshake timing refinement; SC3 is new. Planner amends during planning.
- `.planning/REQUIREMENTS.md` CODEGEN-LIB-01 — NOTE: text stale per D-01 / D-03 / D-06 / D-11; CODEGEN-LIB-02 preserved verbatim. Planner amends during planning.
- `.planning/STATE.md` — Phase position, milestone counters.

### Phase 27 carry-forward (the config-resolution substrate Phase 28 extends)

- `.planning/phases/27-register-api-contracts-sub-package-test-extraction-lib/27-CONTEXT.md` — Source of `mcp_config_file` ini route, D-09 `MCPTF_CONFIG_FILE` deprecation, D-11 CLI mode subprocess `-o "mcp_config_file=PATH"`. Phase 28 reuses the same ini key in the Typer CLI's pyproject.toml-reading path.
- `.planning/phases/27-register-api-contracts-sub-package-test-extraction-lib/27-VERIFICATION.md` — Confirms `mcp_config_file` ini route is the locked single source of truth; 13/13 PASS.
- `src/mcp_test_framework/_plugin.py` — plugin reads ini value via `config.getini("mcp_config_file")` at `pytest_configure`. Phase 28's CLI-side reader uses stdlib `tomllib` against pyproject.toml directly (Typer CLI doesn't run under pytest's config-parsing).
- `pyproject.toml` `[tool.pytest.ini_options] mcp_config_file = "./config.test.yaml"` — Phase 27 D-06 framework dogfood line. Phase 28's `gen-test-classes` invoked in framework dev now finds this automatically.

### Phase 25 carry-forward (deprecation pattern)

- `.planning/phases/25-public-api-rename-seed-023-sdet-test-code/25-CONTEXT.md` §"Deprecation mechanics" — pattern reused by the existing `MCPTF_CONFIG_FILE` warning in `_load_config`. Phase 28 does NOT add new deprecations; the existing one keeps firing.

### Operator-tone error references

- `docs/ERROR-STYLE.md` — Operator-tone error template. D-02 (missing-field error), D-06 (non-TTY abort), D-10 (guard error) all follow this style.
- `src/mcp_test_framework/cli.py` `_emit_operator_error()` — error helper Phase 28 reuses verbatim. Planner verifies signature still matches needed args (summary, detail, next_step).

### Codebase landmarks (Phase 28 will touch)

- `src/mcp_test_framework/cli.py::gen_test_classes` (line ~997) — current command body. Phase 28 adds: pyproject.toml parsing (D-11), pre-handshake site-packages guard (D-07/D-08), `out_root` non-empty prompt + non-TTY abort (D-05/D-06). Existing config-load fail-loud path stays.
- `src/mcp_test_framework/cli.py::_load_config` (line ~221+) — current config resolution chain. Phase 28 extends with `[tool.pytest.ini_options] mcp_config_file` source between `--config` flag and `./config.yaml` autodiscovery (D-11). Today's `MCPTF_CONFIG_FILE` deprecation-warning path preserved.
- `src/mcp_test_framework/models.py::TestCodeConfig` (line ~190) — `generated_root: Path = Field(...)` REQUIRED stays; empty-string validator stays; no new validators added per D-04.
- `src/mcp_test_framework/test_code/_codegen.py` — `generate()` function called from `cli.py`. Phase 28 does NOT touch this — it consumes `out_root` after the new guard + prompt logic resolves the path.
- `src/mcp_test_framework/cli.py::config_init` (line ~820) — scaffold writer. Phase 28 likely doesn't touch unless D-02 error copy references it inconsistently with the scaffold's current `test_code.generated_root: tests/test_code/_generated` line.

### Python references (researcher should fetch)

- Python `tomllib` stdlib docs — for D-13 pyproject.toml parsing. https://docs.python.org/3/library/tomllib.html
- `typer.confirm` docs — interactive confirmation prompt for D-05. https://typer.tiangolo.com/tutorial/prompt/#confirmation-prompt
- `sys.stdin.isatty()` / `sys.stdout.isatty()` — for D-06 non-TTY detection. Match Typer / Click conventions for `--no-input` behavior.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`_emit_operator_error()` helper in `cli.py`** — operator-tone error emission used by every existing fail-loud path in `gen-test-classes`. Phase 28 reuses verbatim for D-02 (missing-field), D-06 (non-TTY abort), D-10 (guard failure).
- **`_load_config(config, allow_missing=...)` in `cli.py`** — central config-load entry point. Phase 28 extends with the new pyproject.toml-reading branch (D-11) between the `--config` and `MCPTF_CONFIG_FILE` checks.
- **Existing `gen-test-classes` body in `cli.py`** — already does fail-loud config load, handshake, server-name validation, slug derivation, wipe-and-write codegen. Phase 28 inserts the guard before the handshake and the overwrite-prompt before the codegen call. No restructuring of the existing flow.
- **`TestCodeConfig.generated_root` field validator** — already rejects empty strings with operator-friendly error. D-04 keeps this verbatim.
- **`config-init` scaffold writer** — emits `test_code.generated_root: tests/test_code/_generated` as the default scaffolded value. Phase 28 likely doesn't touch this; the D-02 error message points operators at it.

### Established Patterns

- **Operator-tone error pattern (`docs/ERROR-STYLE.md`)** — summary line, detail bullets, next_step phrase. Every Phase 28 error follows this template (D-02, D-06, D-10).
- **Exit code conventions in `cli.py`** — 0 success, 2 config / setup / validation error, 130 KeyboardInterrupt. Phase 28's new failures (guard, missing field, non-TTY abort, prompt-declined) all use exit code 2.
- **Phase 27 single-config-route principle** — D-11 extends this to the Typer CLI surface: `gen-test-classes` and `pytest` find the same config via the same mechanism.
- **Wipe-and-write codegen (`_codegen.generate`)** — historical default. D-05 wraps this with a confirmation gate; the underlying generator is unchanged.

### Integration Points

- **`gen-test-classes` ↔ pyproject.toml** — new at-command-start `tomllib.load(open("pyproject.toml", "rb"))` reads `[tool.pytest.ini_options] mcp_config_file`. Fail-soft on missing / malformed pyproject.
- **`gen-test-classes` ↔ pytest plugin** — no direct integration. Both independently consume the same ini value from pyproject.toml. Single source of truth; two readers.
- **Site-packages guard ↔ framework install detection** — `Path(mcp_test_framework.__file__).parent.parent` resolves to the sys.path entry the framework was imported from. Works for site-packages, editable installs, vendored copies. Cross-platform.
- **Confirmation prompt ↔ TTY detection** — Typer's `typer.confirm` already raises in non-TTY by default; Phase 28 catches and converts to operator-tone error. Verify Typer's exact non-TTY behavior in research.

</code_context>

<specifics>
## Specific Ideas

- **The framework knows nothing about project layout** — user-as-visionary call. Drives D-01 / D-03 / D-06 directly: no smart default, no `--output-dir`, no `--yes`. The framework's job is to write where told, refuse when unsafe, ask when destructive.
- **Single-config-route extends to Typer CLI** — Phase 27 D-11 established one config-resolution route between CLI mode and library mode. Phase 28 D-11 extends this so `gen-test-classes` (a Typer command, not a pytest run) also reads the same ini value. End state: any time the framework needs to know where config lives, it asks pyproject.toml.
- **Strict guard with no escape hatch is consistent with v1.4's posture** — Phase 27 killed `MCPTF_CONFIG_FILE` magic and refused a `register(config_file=PATH)` escape hatch. Phase 28 refuses an `allow_unsafe_generated_root` knob for symmetric reasons.
- **Non-empty-dir prompt is the only piece of NEW operator-facing UX in Phase 28** — everything else is either a refactor of existing error paths (D-02, D-10) or a new safety check (D-07). The prompt is the one place an operator sees novel behavior.

</specifics>

<deferred>
## Deferred Ideas

### Phase 29 (already roadmapped, unchanged)
- `--mcp-domain-ui` reporter plugin driven by `pytest_runtest_logreport`; xdist master-only; CI/no-TTY auto-OFF.

### Phase 30 (already roadmapped; no impact from Phase 28)
- Production PyPI publish.
- README rewrite leading with library mode.
- CLI demotion to appendix.
- Carry-forward live UATs.

### v1.5 cleanup (inherited from Phase 27, untouched by Phase 28)
- `MCPTF_CONFIG_FILE` env var removal.
- Tool auto-discovery.
- Multi-config (list of paths).

### Documentation amendments (post-Phase-28, pre-Phase-29)
- REQUIREMENTS.md CODEGEN-LIB-01 rewrite per `<downstream_impact>`.
- ROADMAP.md Phase 28 Goal + SC1 + SC2 + new SC3 per `<downstream_impact>`.
- Planner picks: bundle as a Phase 28 docs plan OR a quick task before Phase 29.

### Explicitly REJECTED (do not resurrect)

- Smart default for `generated_root` (`tests/_generated/`, `tests/test_code/_generated/`, cwd-inspection heuristics) — rejected by D-01 with strong user-as-visionary signal. Future phases must not reintroduce.
- `--output-dir` CLI flag — rejected by D-03; reintroducing would split the config-source-of-truth.
- `--yes` / `--force` flag on `gen-test-classes` — rejected by D-06. Reintroducing weakens the "never silently destroy data" stance.
- `allow_unsafe_generated_root` config bypass for the site-packages guard — rejected by D-09.

</deferred>

---

*Phase: 28-codegen-output-path-codegen*
*Context gathered: 2026-05-16*
