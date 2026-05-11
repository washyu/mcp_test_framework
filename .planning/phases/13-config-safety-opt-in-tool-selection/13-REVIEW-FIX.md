---
phase: 13-config-safety-opt-in-tool-selection
fixed_at: 2026-05-10T00:00:00Z
review_path: .planning/phases/13-config-safety-opt-in-tool-selection/13-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 7
skipped: 1
status: all_fixed
---

# Phase 13: Code Review Fix Report

**Fixed at:** 2026-05-10
**Source review:** .planning/phases/13-config-safety-opt-in-tool-selection/13-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope (CR + WR): 8
- Fixed (committed with code/test change): 7
- Fixed (no code change required, resolved transitively via CR-01): 1
- Skipped: 0
- Out of scope (IN findings, deferred per fix_scope = critical_warning): 4

## Fixed Issues

### CR-01: Resolved YAML path does not reach the in-process pytest Config()

**Files modified:** `src/mcp_test_framework/config.py`, `src/mcp_test_framework/cli.py`
**Commit:** a521489
**Applied fix (option (a) from review):**
- `cli.py:_load_config`: after resolving the YAML path, sets
  `os.environ["MCPTF_CONFIG_FILE"] = str(resolved)` before constructing
  `Config(yaml_file=str(resolved))`. The env var now acts as a PATH POINTER
  for downstream bare `Config()` calls inside the pytest.main session.
- `config.py:settings_customise_sources`: after `init_settings.init_kwargs.pop("yaml_file", None)`,
  falls back to `os.environ.get("MCPTF_CONFIG_FILE")` if the kwarg was
  not supplied. SAFE-05 is preserved because the env var only directs
  the YAML loader to a file -- it never injects scalar config values.
- Module docstring updated to describe the new precedence:
  `init kwarg > MCPTF_CONFIG_FILE (path pointer) > YAML at PATH > defaults`.

**Verification note:** the fix changes a logic path (IPC handoff between
the CLI process and the in-process pytest session). Marked as
`requires human verification` — recommended live-acceptance test:
`mcp-test-framework run --config focus-list_registered_servers.yaml`
should now parametrize at least one contract test instead of reporting
every discovered tool as state-(a) "not selected in config".

### CR-02: Reporter loads bare Config() and ignores the operator's tools block

**Files modified:** (resolved transitively via CR-01 fix)
**Commit:** a521489 (same atomic commit as CR-01)
**Applied fix:** the reporter's `_FwConfig()` call site at
`_reporter.py:230-231` now picks up the operator's YAML via the
MCPTF_CONFIG_FILE path-pointer fallback installed in CR-01. No code
change at the reporter site itself (per the review's recommendation:
"After CR-01 is fixed, this site will pick up the operator's config
automatically -- no code change needed beyond CR-01"). The misleading
`except Exception` rationale was addressed separately under WR-06.

### CR-01/CR-02 regression test

**Files modified:** `tests/unit/test_reporter.py`
**Commit:** 47120bc
**Applied fix:** added three regression tests pinning the IPC handoff:
1. `test_cr01_bare_config_picks_up_mcptf_config_file` — bare `Config()`
   with no kwargs reads `MCPTF_CONFIG_FILE` and loads the operator's
   `tools:` block.
2. `test_cr01_resolver_writes_mcptf_config_file_env_var` — `_load_config`
   exports the resolved path; downstream bare `Config()` sees state-(b)
   and state-(c) entries.
3. `test_cr02_reporter_state_c_renders_curated_skip_reason` — exercises
   `_compose_unparametrized_skips` against the same bare `_FwConfig()`
   the reporter uses, confirming the operator's curated `skip_reason`
   flows through instead of the state-(a) default.

These would have failed against the pre-fix code (Config defaults to
`tools={}`). All 11 reporter tests pass after the fix.

**End-to-end live test (deferred to human verification):** the review
asks for an integration test that drives `mcp-test-framework run --config
<yaml>` to assert parametrized tests run AND state-(c) reporter output
renders. This requires a live homelab-mcp + Ollama and is gated by the
`_preflight` autouse fixture. Recommended next step: add under
`tests/contract/` (or follow-up phase) once the operator/dev split from
SEED-010 lands. The unit-level regression tests above pin the
mechanism without requiring the live environment.

### WR-01: --config help text falsely claims it sets MCPTF_CONFIG_FILE

**Files modified:** `src/mcp_test_framework/cli.py`
**Commit:** 52229d2
**Applied fix:** all three identical help strings on `run`,
`list-tools`, and `config-init` updated from
`"Path to a YAML config overlay (sets MCPTF_CONFIG_FILE)."`
to
`"Path to a YAML config (overrides MCPTF_CONFIG_FILE and ./config.yaml autodiscovery)."`.

### WR-02: _load_config docstring claims ValidationError propagates

**Files modified:** `src/mcp_test_framework/cli.py`
**Commit:** 7bae326
**Applied fix:** module-header docstring rewritten to describe Phase 13
D-01/D-03 behavior (resolver precedence + yaml_file kwarg + MCPTF_CONFIG_FILE
export). Inline comment at the `_load_config(config)` call site changed
from `"raises typer.Exit(2) on bad path; ValidationError propagates"` to
`"raises typer.Exit(2) on any unrecoverable error"`.

### WR-03: fixtures.config docstring lists removed env precedence

**Files modified:** `src/mcp_test_framework/fixtures.py`
**Commit:** 384ff8b
**Applied fix:** docstring rewritten from
`"Load env + YAML config once per session (Phase 1 precedence: CLI > env > YAML > default)."`
to a multi-line explanation describing Phase 13 precedence
(`init kwarg > MCPTF_CONFIG_FILE path-pointer > YAML > defaults`) and the
CR-01 IPC handoff. Also documents why a bare `Config()` works in this
fixture.

### WR-04: Preflight hint recommends MCPTF_CONFIG_FILE for value injection

**Files modified:** (none — resolved transitively via CR-01 fix)
**Commit:** a521489 (CR-01)
**Applied fix:** per the review's own resolution path: "After CR-01 is
fixed via the env-var-pointer approach, this hint becomes accurate and
the in-sync comments are correct." The three identical hint blocks in
`fixtures.py:148-156`, `fixtures.py:247-253`, and `tests/conftest.py:123-129`
now describe behavior the code actually delivers — setting
`MCPTF_CONFIG_FILE` from outside the CLI works as a path pointer for
the in-process pytest session. No text change required.

### WR-05: NoReturn type assertion accepts non-NoReturn return types

**Files modified:** `tests/unit/test_cli_errors.py`
**Commit:** 38cc2cf
**Applied fix:** removed the `type(None).__class__` middle branch
(which resolved to `<class 'type'>` and accidentally permitted any
class-typed return annotation like `-> int`). New assertion only
accepts `typing.NoReturn` identity or `__name__ == "NoReturn"`. Test
still passes against the current `_emit_operator_error` signature.

### WR-06: Reporter rationale comment contradicts actual Config() behavior

**Files modified:** `src/mcp_test_framework/_reporter.py`
**Commit:** 79c9438
**Applied fix:** comment on the `except Exception` block rewritten from
`"under unit-only runs Config() may fail (SAFE-03 fail-loud, no config in cwd)"`
to a correct rationale: bare `Config()` succeeds with defaults today
(SAFE-03 fail-loud lives in `cli.py:_load_config`, not `Config.__init__`);
the guard is documented as belt-and-suspenders defensiveness against
future regressions.

## Skipped Issues

None — all in-scope findings (2 BLOCKER + 6 WARNING) were either fixed
with code/test changes or resolved transitively via the CR-01 IPC fix.

## Out of Scope (deferred per fix_scope=critical_warning)

The following INFO-level findings were not addressed in this iteration
and remain in the review for later cleanup:

- IN-01: Resolved Config from `cli.run()` is constructed and discarded.
  (Minor cleanup; not blocking; defer.)
- IN-02: `yaml_file=non-existent path` silently returns defaults.
  (Behavior pinned by existing test; tightening is optional surface.)
- IN-03: Docstring for `_load_config` says "Phase 13 D-NN" inside source.
  (Tracked under the broader v1.2 doc-scrub initiative —
  `feedback_doc_scrub_planning_artifacts.md`.)
- IN-04: Migration doc references `--config focus-list_tools.yaml`
  without verifying flow. (Auto-resolves after CR-01 — no doc change
  needed once the fix is shipped.)

## Verification Performed

- Tier 1: re-read each modified file section to confirm fix text present
  and surrounding code intact.
- Tier 2: `python -c "import ast; ast.parse(...)"` on every modified `.py`
  file (config.py, cli.py, fixtures.py, _reporter.py, test_reporter.py,
  test_cli_errors.py).
- Tier 3 (integration): full `uv run pytest tests/unit/` after final
  commit — **183 passed, 1 warning** (the unrelated `_reporter`
  `PytestAssertRewriteWarning`).

## Commits (atomic per finding)

```
a521489 fix(13): CR-01/CR-02 propagate resolved YAML path to in-process pytest Config()
47120bc test(13): CR-01/CR-02 regression coverage for IPC handoff to bare Config()
52229d2 fix(13): WR-01 update --config help text to reflect Phase 13 resolver
7bae326 fix(13): WR-02 correct _load_config docstring on ValidationError handling
384ff8b fix(13): WR-03 update fixtures.config docstring for Phase 13 precedence
38cc2cf fix(13): WR-05 tighten NoReturn assertion to actually enforce NoReturn
79c9438 fix(13): WR-06 correct misleading except Exception rationale in reporter
```

CR-02 and WR-04 carry no separate commit — both are resolved transitively
by a521489 (CR-01) per the review's recommended resolution path.

---

_Fixed: 2026-05-10_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
