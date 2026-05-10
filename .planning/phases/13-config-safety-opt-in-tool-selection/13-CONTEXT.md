# Phase 13: Config safety & opt-in tool selection - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Make config mandatory and unambiguous so an operator running `mcp-test-framework run` against an unconfigured directory cannot accidentally exercise destructive tools. Invert `tools:` from skip-list to opt-in allowlist, auto-discover `./config.yaml`, fail loud on missing/typo'd config, drop `.env` and the env-overlay entirely, and bump schema `version: 1 → 2` with a loud migration error pointing at `config-init`.

**In scope:** SAFE-01..07 (7 requirements). Config-resolution surgery in `_load_config` and `settings_customise_sources`; allowlist three-state runtime semantics in fixtures + reporter; v2 schema bump and refuse-on-load migration error; new `docs/MIGRATION-v1-to-v2.md`; removal of `target.tool_name` from the Pydantic model (Phase 12 D-03 forward-ref); deletion of the `python-dotenv` direct dep.

**Out of scope:** Phase 14's hybrid runner / domain UI (we still emit pytest-shaped output from the runner); Phase 15's `tests/contract/` vs `tests/framework/` split; Phase 16's reporter UX overhaul (the SAFE-01 skip-reason strings ship here, but the broader pre-run digest and `--explain` flag wait for Phase 16).

**Hard dependency:** Phase 12 must be complete before Phase 13 plans execute — Phase 13 implements `docs/ERROR-STYLE.md`'s pre-drafted SAFE-03 and SAFE-06 messages verbatim (Phase 12 D-17) and depends on the `config-init` scaffold completeness (CLEAN-05). Phase 12 is currently 6/9 plans executed (2026-05-10). Discussion ahead of plan-phase is safe; planning should wait for Phase 12 verification.

</domain>

<decisions>
## Implementation Decisions

### Auto-discovery + error precedence (SAFE-02, SAFE-03, SAFE-04)
- **D-01:** Config resolution precedence is **`--config PATH` > `MCPTF_CONFIG_FILE` > `./config.yaml` autodiscovery > fail-loud**. First miss raises `typer.Exit(2)` with the ERROR-STYLE message from Phase 12 D-17. Resolution happens once, in `_load_config`, before `Config()` is constructed.
- **D-02:** Autodiscovery probes **only `./config.yaml` in `Path.cwd()`**. No walk-up, no alternate filenames. Predictable; an operator running from the wrong directory gets the same loud SAFE-03 error as one with no config at all. Trade-off accepted: operators in subdirectories must `cd` or pass `--config`.
- **D-03:** **Single resolver in `cli.py` / `_load_config`.** Promote the existing helper into the real resolver: it checks `--config`, then `os.environ.get("MCPTF_CONFIG_FILE")`, then `./config.yaml`, and raises `typer.Exit(2)` at the first failure (--config not found, env-var path not found, no autodiscovery hit, OR none of the three set). `Config(...)` receives the resolved path as an explicit `yaml_file` kwarg via `init_settings` — no env-var trick. `settings_customise_sources` reads the path from kwargs, not from `os.environ`. Eliminates the brittle env-var-as-IPC pattern that motivated the SAFE-04 bug report.
- **D-04:** SAFE-04 falls out of D-03 for free: because `_load_config` validates the env-var path before constructing `Config`, a typo'd `MCPTF_CONFIG_FILE` and a typo'd `--config` route through the same error site with the same exit code and the same ERROR-STYLE wording (modulo "the env var" vs "the --config flag" in the lead sentence).

### Env-overlay drop depth (SAFE-05)
- **D-05:** **Full strip** of the env-overlay machinery. Delete `_BareNameNestedEnvSource` entirely (~60 lines in `config.py`); remove `env_settings` and `dotenv_settings` from the `settings_customise_sources` tuple; remove `env_file` and `env_file_encoding` from `model_config`; remove `python-dotenv` from direct `pyproject.toml` deps; delete the `_alias_env_names` helper and `_maybe_json_decode` helper. Config() sources collapse to `init_settings` (CLI-resolved path) → `YamlConfigSettingsSource(yaml_file=<resolved>)` → defaults. Sub-model `validation_alias=AliasChoices(...)` declarations on `OllamaConfig`/`McpServerConfig`/etc. lose their env-var role — keep the YAML key aliases, drop the env-name choices.
- **D-06:** **`MCPTF_CONFIG_FILE` survives, but only as a pointer-to-config read by `_load_config`** — not as a `Config()` source. This is a directory-of-search-paths convention, not config-value-from-env. Same surface area for operators; eliminates the "env beats YAML" bug class.
- **D-07:** **`.env` becomes dead-letter for the framework**, kept only as Phase 12 CLEAN-06 reframed it: a CI-secret passthrough convention for subsystems (e.g., a future HTTP-backed judge reading `JUDGE_API_KEY`). The framework's config layer no longer reads `.env`. `.env.example` already documents this (Phase 12); no further doc churn needed except a one-line note in MIGRATION.

### v1→v2 migration UX (SAFE-06, SAFE-07)
- **D-08:** **`version: 2` is the only accepted value.** Update the `_validate_version` field_validator in `config.py:184-192` from `if v != 1` to `if v != 2`. Loading a `version: 1` config raises with the SAFE-06 ERROR-STYLE message (pre-drafted in Phase 12 ERROR-STYLE.md): names the opt-out→opt-in semantic flip, points at `mcp-test-framework config-init -o config.yaml` to regenerate, links `docs/MIGRATION-v1-to-v2.md`.
- **D-09:** **No `config-migrate` subcommand.** Refuse-on-load + doc-driven manual port is the migration UX. Rationale: the unlisted-default flip (opt-out → opt-in) is consequential enough that operators must re-read every per-tool entry; auto-migration that silently keeps old `call_arguments` while flipping the default behind the operator is the exact silent-destructive class v1.2 is fighting against.
- **D-10:** **`docs/MIGRATION-v1-to-v2.md` is a new standalone file**, diff-driven. Sections: (1) plain-English summary of v2 changes (opt-out→opt-in, `.env` and env-overlay dropped, version bump, `target.tool_name` removed); (2) step-by-step port — rerun `config-init -o config.yaml`, then a side-by-side before/after YAML showing how to move `skip_reason`, `call_arguments`, `judges` blocks for each tool the operator wants to keep; (3) drop `.env` and stop relying on env-overlay. Standalone so the SAFE-06 error message points at a stable URL/path that isn't buried inside EXTENDING.md.
- **D-11:** **`target.tool_name` removed from the Pydantic model in this phase** (executing Phase 12 D-03). When a v1 config still contains `target:` it errors during the v1→v2 refusal anyway (because `version: 1` is rejected first); the MIGRATION doc tells operators to delete the `target:` block when regenerating. No separate deprecation path needed — the version refusal subsumes it.

### Allowlist three-state semantics (SAFE-01)
- **D-12:** **Two distinct reason strings.** State (a) unlisted → reporter reason: `"not selected in config"` (exact SAFE-01 wording). State (c) listed with `skip: true` → reporter reason: the operator's curated `skip_reason` if non-empty, else default `"explicit skip in config"` (covers the legal-but-unhelpful empty-string case). Lets the operator scan the report and distinguish "I forgot this tool" from "I deliberately skipped this tool."
- **D-13:** **Empty `tools:` (`{}` or unset) auto-skips every tool.** Consistent with the unlisted rule: zero tools listed → zero tools selected → every discovered tool renders as state (a). The run succeeds with 0 contract tests executed and a clear reporter line saying nothing was opted in. Preserves the "config-init then opt in" workflow without a special case. (Phase 16's pre-run digest will make the "nothing selected" state visible at runtime; in Phase 13 the per-tool skip lines carry it.)
- **D-14:** **Delete the `target.tool_name` skip-override at `fixtures.py:282-286`.** Since D-11 removes `target.tool_name` from the model entirely, the "overriding tools[target.tool_name].skip=True for this run" override is unreachable code and goes with the field. The new allowlist replaces it: if the operator wants a tool to run, they list it without `skip: true`. Focus-one-tool workflows continue via `focus-toolname.yaml + --config` (Phase 12 D-03).

### Claude's Discretion
- Plan ordering within Phase 13. Suggested sequence: (1) `_load_config` resolver + error-site wiring; (2) `config.py` env-overlay strip + `version: 2` flip; (3) fixtures.py allowlist three-state runtime + reporter wording; (4) `target.tool_name` removal + `fixtures.py:282-286` deletion; (5) `docs/MIGRATION-v1-to-v2.md` + dep cleanup (`python-dotenv` removed from `pyproject.toml`).
- Exact wording of the default skip-reason for state (c) when `skip_reason` is empty (currently `"explicit skip in config"` — adjust if Phase 12 ERROR-STYLE.md pins a better phrasing).
- Whether the resolver prints the resolved config path on a verbose flag (defer to Phase 16 reporter overhaul; Phase 13 stays silent unless it errors).
- Test surface: where the SAFE-01..07 regression tests land (under v1.1's `tests/` until Phase 15's split). Banned-imports / snippet-correctness style tests are encouraged for the SAFE-06 error message wording so Phase 12's ERROR-STYLE.md stays the source of truth.
- Whether the sub-model `validation_alias=AliasChoices(...)` declarations keep their YAML-key aliases or whether the YAML keys become the canonical field names (small refactor opportunity; not required by any SAFE-* requirement).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/REQUIREMENTS.md` §SAFE-01..07 — the 7 locked requirements for this phase
- `.planning/ROADMAP.md` Phase 13 row (lines 64-75) — goal, depends-on, success criteria
- `.planning/PROJECT.md` "Current Milestone: v1.2 Operator-First Design" — milestone framing and anti-vision
- `.planning/STATE.md` — current execution position (Phase 12 6/9 plans as of 2026-05-10)

### Phase 12 forward-refs (LOCKED — implement verbatim)
- `.planning/phases/12-doc-persona-foundation/12-CONTEXT.md` §decisions D-01, D-02, D-03, D-17 — v1→v2 = header bump + flip default; all-skip-true config-init output; `target.tool_name` removal; SAFE-03/SAFE-06 error messages pre-drafted
- `docs/ERROR-STYLE.md` (created by Phase 12, plan 12-01) — style guide AND the pre-drafted SAFE-03 (no-config failsafe) and SAFE-06 (v1→v2 migration) reference messages. Phase 13 MUST implement these verbatim — do not rephrase.
- `.env.example` (rewritten by Phase 12, plan 12-02) — already declares "env vars no longer override config values"; Phase 13 makes the code match the doc

### Files affected by this phase
- `src/mcp_test_framework/config.py` — full env-overlay strip (`_BareNameNestedEnvSource`, dotenv/env sources, `env_file`, helpers); `settings_customise_sources` collapses to init_settings → YamlConfigSettingsSource → defaults; `_validate_version` flips `1 → 2`; remove `target` field from `Config`
- `src/mcp_test_framework/cli.py:178-211` — `_load_config` promoted to full resolver (--config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud); passes resolved path as `yaml_file` kwarg
- `src/mcp_test_framework/cli.py` (config-init body, ~line 219-298) — already emits v2-shape content per Phase 12 D-01; this phase only flips the literal `version: 1` → `version: 2` in the scaffold output
- `src/mcp_test_framework/fixtures.py:262, 282-286, 482-494` — three-state allowlist runtime; delete `target.tool_name` skip-override; tool selection becomes "listed and not skipped"
- `src/mcp_test_framework/models.py` — remove `TargetConfig` import surface used by `target` field; drop `target.tool_name` consumers
- `src/mcp_test_framework/_reporter.py` — emit the two distinct reason strings from D-12
- `pyproject.toml` — remove `python-dotenv` from direct deps

### Files created by this phase
- `docs/MIGRATION-v1-to-v2.md` — SAFE-07; standalone, diff-driven; linked from SAFE-06 error message

### Pre-existing context worth re-reading
- `.planning/debug/config-yaml-auto-discovery-missing.md` — diagnoses the SAFE-02/SAFE-04 silent-fail root cause at `config.py:212` and explains the v1.1 "no cwd auto-discovery" lock that Phase 13 deliberately reverses
- `docs/mcp_test_framework_mvp_spec.md` — authoritative MVP spec (preserved verbatim per PROJECT.md); Phase 13's config-resolver changes must not break stdio-only / black-box / strict-asyncio invariants
- Memory: `project_mcptf_config_file_silent_fail.md`, `project_dotenv_silently_beats_config.md`, `project_config_discovery_and_safety.md`, `project_opt_in_tool_selection.md` — all directly informed the SAFE-* requirement wording and Phase 13's gray-area resolutions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_load_config` in `src/mcp_test_framework/cli.py:178-211` — already validates `--config` path-exists and raises `typer.Exit(2)`; D-03 extends this seam to also handle MCPTF_CONFIG_FILE and cwd autodiscovery. ~80% of the error-handling skeleton already exists.
- `_validate_version` field_validator in `config.py:184-192` — one-line change (`v != 1` → `v != 2`) plus error-message swap; rest of the SAFE-06 wiring is the error-message body coming from ERROR-STYLE.md.
- `YamlConfigSettingsSource` from `pydantic-settings` — already wired in `settings_customise_sources`; D-03/D-05 just change how its `yaml_file` kwarg is sourced (kwarg via init_settings instead of `os.environ`).
- `config-init` body in `cli.py:219-298` — already emits the v2-shape `tools: { skip: true }` block per Phase 12 D-02; Phase 13 only flips the literal version header in the emit.
- Banned-token / snippet-correctness regression suite (v1.1 Phase 10 / Phase 12 wave-0) — drop-in pattern for locking ERROR-STYLE.md wording into a regression test.

### Established Patterns
- Sub-model `validation_alias=AliasChoices("OLLAMA_BASE_URL", "base_url")` pattern in `models.py` — used for both env-var routing AND YAML-key matching. Phase 13 removes the env-var routing role (env source is gone) but the AliasChoices entries still serve YAML-key matching; safe to leave them in place or simplify to plain `Field(alias="base_url")` per Claude's discretion.
- `typer.Exit(2)` for all SAFE-* fatal errors; exit code is consistent across `--config`, MCPTF_CONFIG_FILE, no-config, and v1-config-loaded surfaces. Phase 12's `_emit_operator_error` helper (plan 12-04) is the shared writer.
- `frozen=True` `BaseSettings` for session-scoped sharing across async tests — preserved; nothing about the env-overlay strip touches this.

### Integration Points
- `_load_config` → `Config(yaml_file=...)` — new kwarg passed in; `Config.settings_customise_sources` reads it from `init_settings`. Single seam; no other call site needs to change.
- `fixtures.py` tool-selection (`config.tools.get(...)`) — three-state branch lands here; reporter formatter for `_format_skip_line` (or equivalent in `_reporter.py`) reads the reason string the fixture emits.
- `config-init` already emits the right shape — only the version literal bumps. The MIGRATION doc's "rerun config-init" instruction works without any config-init changes beyond that one literal.

</code_context>

<specifics>
## Specific Ideas

- Phase 12 ERROR-STYLE.md's pre-drafted SAFE-03 message (paraphrased from Phase 12 D-17): "No config found. Run `mcp-test-framework config-init -o config.yaml` to generate a starter config, then re-run." — Phase 13 implements this verbatim.
- Phase 12 ERROR-STYLE.md's pre-drafted SAFE-06 message (paraphrased): "Config schema is v1; this build requires v2. The opt-out semantics changed: tools are now opt-in. Re-run `mcp-test-framework config-init -o config.yaml` and see `docs/MIGRATION-v1-to-v2.md` to port your `call_arguments`, `judges`, and `skip_reason` entries." — Phase 13 implements this verbatim.
- Reporter skip reason for state (a): `"not selected in config"` (exact SAFE-01 wording).
- Reporter skip reason for state (c) with empty `skip_reason`: `"explicit skip in config"` (default; adjust if ERROR-STYLE pins something else).
- MIGRATION doc before/after YAML diff convention: per-tool block side-by-side, with arrows pointing at the three surgery points (drop top-level `target:`, ensure `version: 2`, audit each `tools.<name>` block for opt-in intent).

</specifics>

<deferred>
## Deferred Ideas

### Cross-phase tasks (Phase 14)
- Pre-flight "no config" check happens during framework startup before pytest collection. Phase 14's runner pre-flight reuses D-03's SAFE-03 error site rather than re-checking — keep the resolver as the single source of truth.
- The "Skipping (N)" count in Phase 14's pre-run digest depends on SAFE-01's opt-in semantics being truthful (per ROADMAP Phase 14 depends-on note); Phase 13's three-state implementation must expose the counts at a stable seam the digest can read.

### Cross-phase tasks (Phase 16)
- `--explain` flag rendering per-tool skip reasons in long-form. Phase 13 supplies the two distinct reason strings; Phase 16 designs the verbosity ladder around them.
- Optional verbose flag on the resolver to print the resolved config path on stdout. Deferred to Phase 16's reporter UX overhaul.

### v1.3+ todos (post-milestone)
- Walk-up autodiscovery (ruff/pyproject-style ancestor search) if cwd-only proves too strict in practice — explicitly rejected for v1.2 to keep the resolver predictable.
- `config-migrate` subcommand — explicitly rejected for v1.2 (D-09); revisit only if MIGRATION doc friction becomes a real operator complaint.
- Refactoring `validation_alias=AliasChoices(...)` declarations to plain `Field(alias=...)` once env-var routing is gone — cleanup opportunity, not required.
- A `--only TOOL_NAME` CLI flag — rejected for v1.2 per Phase 12 D-03; `focus-toolname.yaml + --config` is the focus pattern.

### Out of phase scope (already deferred at scoping)
- Hybrid runner / domain UI rendering — Phase 14
- `tests/contract/` vs `tests/framework/` split — Phase 15
- Reporter UX overhaul (pre-run digest, verbosity ladder) — Phase 16

</deferred>

---

*Phase: 13-config-safety-opt-in-tool-selection*
*Context gathered: 2026-05-10*
