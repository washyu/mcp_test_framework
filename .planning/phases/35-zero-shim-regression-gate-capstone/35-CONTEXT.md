# Phase 35: Zero-shim regression gate (capstone) - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship a single CI-runnable test under `tests/framework/` that pins the v1.5 zero-shim STATE across the five retired-shim surfaces (import / CLI / config / fixtures / discovery) and fails loudly when a *functional* shim is reintroduced. SHIM-09 is the v1.5 capstone — it lands LAST, after every other SHIM/V1DROP/BUCKET/ISOL surface is stable.

**In scope:** SHIM-09 only — the cross-surface regression gate.

**Out of scope (different phases / already shipped):** the actual shim removals (SHIM-01..08, V1DROP-01..04 — Phases 31/32, complete); the per-surface operator-tone *message-text* tests shipped alongside those removals; BUCKET (Phase 33) and ISOL (Phase 34) surfaces; the v1.6 clean-deletion of the grandfathered intercepts.

### CRITICAL: grandfathered intercepts (locked carry-forward from 32-CONTEXT.md §deferred)

The gate must NOT treat these as reintroduced shims — they are *intentional hard-reject intercepts* that survive through v1.5 and are clean-deleted in v1.6. A naive `grep sdet` would fail on all of them:

1. `src/mcp_test_framework/sdet/__init__.py` — hard-raise migration stub (raises `ModuleNotFoundError`/`ImportError` with pointer to `mcp_test_framework.test_code`).
2. `--sdet` and `gen-sdet-classes` — hidden Typer intercepts that raise operator-tone `UsageError`/`BadParameter` pointing at `--test-code` / `gen-test-classes`.
3. Six unprefixed stub-raise fixtures in `_plugin.py` (`config`, `judge`, `target_tool`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`) — `pytest.fail(..., pytrace=False)` pointing at the `mcp_*`-prefixed names. (Note: SC#1's "unprefixed quartet" wording is imprecise — the real surface is SIX fixtures; `client` is NOT among them.)
4. `mcp-test-framework` `[project.scripts]` entry + `src/mcp_test_framework/_deprecated_script.py` — hard-raise console-script naming `mcp-contracts`.
5. `tests/sdet/` warn-on-presence path-string in `_plugin.py` — discovery is removed (only `tests/test_code/` auto-discovered); a warn-on-presence detector remains.

</domain>

<decisions>
## Implementation Decisions

### Detection strategy (Sweep semantics)
- **D-01:** **Behavioral-first + narrow AST backstop.** Primary detection = probe each of the five surfaces and assert it hard-rejects or no-ops. This is what catches reintroduction: re-adding a *functional* shim (e.g. neutering the `--sdet` hidden intercept back into a working flag) makes the corresponding "assert it rejects" probe FAIL. This resolves the apparent tension between SHIM-09's "zero matches" wording and the surviving grandfathered intercepts — "zero shims" means "no functional shim exists / every surviving surface hard-rejects," NOT "the word `sdet` never appears."
- **D-02:** **Behavior-only assertions.** Each probe asserts only the observable behavior: import raises, CLI invocation exits non-zero / raises, fixture fails at resolution, `tests/sdet/` is not auto-collected, a `sdet:` config is rejected at load, `MCPTF_CONFIG_FILE` is inert. The gate does NOT re-assert the exact operator-tone message text — the Phase 31/32 per-surface tests already pin that. Keeps the gate about STATE, fast, and non-duplicative.
- **D-03:** **AST-targeted narrow backstop** for the two surfaces that were *fully deleted* (no surviving intercept): assert via AST that `src/` contains no `Field(alias="sdet")` on the config model and no `os.environ` read of `MCPTF_CONFIG_FILE` in the config-source code. Deliberately NOT a text-regex sweep for the token `sdet` — that would collide with the grandfathered intercept stubs and demand brittle exclusion bookkeeping. **RESEARCH-FOR-PLAN:** confirm the exact AST node shapes to match (`Field(alias=...)` keyword on a model field; `os.environ[...]` / `os.environ.get(...)` / `os.getenv(...)` with the env-var name) and the exact config-source module(s) to walk.

### Failure-message granularity / structure
- **D-04:** **Separate named test function per surface** (e.g. `test_import_surface_shim_absent`, `test_cli_surface_shims_reject`, `test_config_surface_shims_absent`, `test_fixture_surface_shims_fail`, `test_discovery_surface_not_auto_collected`). The surface name lives in the function name, so a failing test names the regressed surface natively (satisfies SC#2). Five surface groups; sub-shims within a surface (e.g. the three CLI shims) are separate asserts inside the surface's function.
- **D-05:** **Self-explaining failure messages.** Each assertion message names: the surface, the specific failing probe / what regressed, the requirement id (SHIM-0x), and the fact that the shim must remain a hard-reject intercept until v1.6 clean-delete — so a contributor whose PR goes red can self-correct without digging through `.planning/`.

### Relationship to existing gates
- **D-06:** **Coexist with the RENAME-06 terminology gate** (`tests/framework/test_sdet_rename_leak_gate.py`). It guards docs/src against the *word* `sdet` leaking into operator-facing surfaces — orthogonal to SHIM-09's *functional-reintroduction* guard. Both stay. Phase 35 corrects that gate's stale docstring ("Removed in v1.5 when the deprecation shims drop and the gate becomes a no-op") to reflect reality: the grandfathered intercepts keep it live (with its `# noqa: sdet-rename-shim` exclusions) until v1.6. This is a light docstring fix, NOT a behavior change to that gate.
- **D-07:** **Do not duplicate the per-surface message-text tests.** Phase 32 D-09 already drew the line: SHIM-09 = cross-surface behavioral state sweep; the Phase 31/32 per-plan tests = exact migration-message-text pins. SHIM-09 references the surfaces, not the message strings. (Reinforced by D-02.)

### Constraints (locked by SC#3)
- **D-08:** Single file under `tests/framework/`, no shared fixtures, runtime <1s standalone (regex/AST sweeps + import probes only). **RESEARCH-FOR-PLAN:** how to probe the `mcp-test-framework` console-script's hard-reject WITHOUT spawning a subprocess (keeps it <1s + no network) — likely import `_deprecated_script` and call/inspect `main()` directly, or assert the `[project.scripts]` wiring points at the hard-raise entry. Confirm the no-subprocess approach against SC#1's "CLI surface" intent.

### Claude's Discretion
- Exact test-function names and the internal ordering of surface probes (planner/executor choice; D-04 fixes the per-surface granularity, not the literal names).
- Whether the AST backstop lives in its own helper or inline (D-03 fixes the technique).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope + locked requirements
- `.planning/ROADMAP.md` §"Phase 35" — locked success criteria SC#1-3 (five-surface sweep returns zero matches; reintroduction fails the gate naming the regressed surface; single file, no shared fixtures, <1s).
- `.planning/REQUIREMENTS.md` §"SHIM-09" (line 25) — atomic requirement text enumerating the exact surfaces: importable (`mcp_test_framework.sdet`), CLI (`--sdet`, `gen-sdet-classes`, `mcp-test-framework`), config (`cfg.sdet.*`, `MCPTF_CONFIG_FILE`), fixture names (unprefixed), discovery (`tests/sdet/`).
- `.planning/STATE.md` §"Decisions" 2026-05-23 — Phase 35 is the 1-req capstone that lands LAST; capstone-phase precedent.

### Grandfathering calibration (load-bearing — defines what the gate must NOT flag)
- `.planning/phases/32-surface-shim-removals-cli-package-fixtures-discovery/32-CONTEXT.md` §deferred (line 124-126) — the explicit grandfathering list forwarded to the Phase 35 planner: which surfaces survive as intercepts through v1.5. D-03..D-07 of that file document the exact intercept mechanism per surface.
- `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md` — what was *fully deleted* on the config surface (`Field(alias="sdet")`, `MCPTF_CONFIG_FILE` env route) vs surviving — calibrates the D-03 AST backstop targets.

### Existing analog + per-surface tests (reuse / coexist, do not duplicate)
- `tests/framework/test_sdet_rename_leak_gate.py` — RENAME-06 terminology gate; the closest structural analog (regex sweep + `# noqa: sdet-rename-shim` exclusion). D-06: coexists; Phase 35 fixes its stale v1.5-removal docstring.
- `tests/framework/unit/test_config_sdet_field.py` — SHIM-04 per-surface message-text test (config `sdet:` alias rejection).
- `tests/framework/unit/test_phase_31_mcptf_config_file_scrub.py` + `test_plugin_mcptf_config_file_deprecation.py` — SHIM-05 per-surface tests (`MCPTF_CONFIG_FILE` removal).
- `tests/framework/unit/test_gen_sdet_classes_cli.py` — SHIM-03 per-surface test (`gen-sdet-classes` intercept).
- `tests/framework/unit/test_console_script_removed.py` — SHIM-08 per-surface test (`mcp-test-framework` console-script hard-reject).
- `tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py` — SHIM-07 per-surface test (stub-raise fixtures).
- `tests/framework/unit/test_plugin_tests_sdet_warning.py` — SHIM-06 per-surface test (`tests/sdet/` warn-on-presence).
- `tests/framework/test_banned_imports.py` + `tests/framework/unit/test_no_planning_ids_in_src.py` — other sweep-style gates; reference for the project's established static-gate idiom.

### Error contract (only relevant if any probe inspects message text — D-02 says it should not)
- `docs/ERROR-STYLE.md` — operator-tone three-part error shape. Referenced for context; SHIM-09 deliberately does NOT re-pin this (D-02/D-07).

### Code touch-points (the grandfathered intercept sources the gate probes)
- `src/mcp_test_framework/sdet/__init__.py` — import-surface intercept.
- `src/mcp_test_framework/cli.py` — `--sdet` / `gen-sdet-classes` hidden Typer intercepts.
- `src/mcp_test_framework/_plugin.py` — six stub-raise fixtures + `tests/sdet/` warn-on-presence detector.
- `src/mcp_test_framework/_deprecated_script.py` + `pyproject.toml` `[project.scripts]` — console-script intercept.
- `src/mcp_test_framework/config.py` (config model + config-source) — AST backstop target for `Field(alias="sdet")` + `MCPTF_CONFIG_FILE` (RESEARCH-FOR-PLAN: confirm the exact module).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`test_sdet_rename_leak_gate.py` scan scaffolding** — `REPO_ROOT` resolution, `ast.walk` + string-constant scanning, `# noqa` exclusion helpers. SHIM-09's AST backstop (D-03) can mirror this technique (AST-target specific nodes rather than text-scan).
- **Per-surface tests (above)** — each already proves its surface's intercept behaves. SHIM-09 re-probes behavior at the cross-surface level WITHOUT importing/duplicating their message-text assertions.

### Established Patterns
- **Sweep-style gate idiom** — `test_banned_imports.py`, `test_no_planning_ids_in_src.py`, `test_sdet_rename_leak_gate.py` establish the repo convention for static regression gates living under `tests/framework/`. SHIM-09 follows this idiom (single-purpose, no shared fixtures).
- **`# noqa: sdet-rename-shim` marker** — grandfathered intercept lines carry this marker. SHIM-09's AST backstop (D-03) sidesteps the marker entirely by matching constructs, not tokens — so it does not need to honor or maintain the marker list.

### Integration Points
- **No-subprocess CLI probe** — the console-script hard-reject (SHIM-08) must be checked without spawning a process to honor the <1s / no-network constraint (D-08). Likely via importing `_deprecated_script` + calling `main()` under a raises-assertion, or asserting the `[project.scripts]` target. RESEARCH-FOR-PLAN.
- **Typer intercept probe** — `--sdet` / `gen-sdet-classes` checked via `CliRunner`/`typer.testing` in-process invocation, asserting non-zero exit, not via shell.
</code_context>

<specifics>
## Specific Ideas

- "Zero matches" is reinterpreted (not contradicted) as "zero *functional* shims" — every surviving surface must hard-reject. This reframing is the spine of the whole gate and was the user's explicit choice (D-01).
- The gate is a guard for FUTURE contributors, not a one-time check — its failure messages (D-05) must teach the tripwire's purpose (shim retired in v1.5, stays a hard-reject until v1.6) so a red PR is self-correcting.
</specifics>

<deferred>
## Deferred Ideas

- **v1.6 clean-deletion of the grandfathered intercepts** — when the `sdet/` dir, the two hidden Typer intercepts, the six stub-raise fixtures, the `mcp-test-framework` script entry + `_deprecated_script.py`, and the `tests/sdet/` warn-detector are deleted outright. At that point SHIM-09's per-surface probes flip from "assert hard-reject" to "assert absent" (stock `ModuleNotFoundError` / Typer `No such option` / fixture-not-found), and the RENAME-06 terminology gate (D-06) can finally retire. Belongs to v1.6. (Carried from 32-CONTEXT.md §deferred.)
- **CHANGELOG / milestone footnote for the v1.4→v1.5 shim retirement** — out of Phase 35 scope; nice-to-have historical record. (Carried from 32-CONTEXT.md §deferred.)

### Reviewed Todos (not folded)
None — `gsd-sdk query todo.match-phase 35` returned `todo_count: 0`.

</deferred>

---

*Phase: 35-Zero-shim regression gate (capstone)*
*Context gathered: 2026-05-27*
