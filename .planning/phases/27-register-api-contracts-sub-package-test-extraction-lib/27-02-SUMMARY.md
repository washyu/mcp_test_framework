---
phase: 27-register-api-contracts-sub-package-test-extraction-lib
plan: 02
subsystem: library-mode-foundations
tags: [pytest-plugin, ini-key, config-loader, black-box-guard, deprecation-warning]
requires:
  - src/mcp_test_framework/_black_box_guard.py (relocated guard from Plan 27-01)
  - src/mcp_test_framework/config.py (yaml_file=PATH kwarg path -- verified at config.py:228)
  - src/mcp_test_framework/cli.py (_emit_operator_error_for_validation -- lazy-imported)
provides:
  - src/mcp_test_framework/_plugin.py with filled-in pytest_addoption (ini registration)
    and pytest_configure (ini read + Config load + black-box guard + DeprecationWarning) bodies
  - config._mcp_contracts_config attribute on pytest.Config -- consumed by Plan 27-03's
    collection hooks
affects:
  - Plan 27-03 (collection hook + parametrize site) -- has the Config instance ready to consume
  - Plan 27-05 (cleanup) -- tests/conftest.py black-box guard becomes deletable
tech-stack:
  added: []
  patterns:
    - "parser.addini(type='string', default='') for nullable-single-path ini keys"
    - "pytest.exit(..., returncode=2) for setup-time fail-loud"
    - "Lazy import of operator-tone helper inside except ValidationError block (cycle break)"
    - "SystemExit->pytest.exit translation to preserve returncode=2 convention end-to-end"
key-files:
  created: []
  modified:
    - src/mcp_test_framework/_plugin.py
decisions:
  - "Config loader driven via Config(yaml_file=str(path)) explicit kwarg -- the option-(b)
    os.environ[MCPTF_CONFIG_FILE]=path internal-workaround was REJECTED on principle
    (kills the env-var-magic surface the user just retired)."
  - "Planning-ID gate (TEST-NN/LIB-NN/D-NN regex) took precedence over the plan's verbatim
    docstring instruction -- D-09/D-10/D-12/D-13/D-14/D-15/D-18 references scrubbed from
    docstrings and comments. Behavior + literal copy strings unchanged."
metrics:
  duration_minutes: ~15
  tasks_completed: 2
  files_created: 0
  files_modified: 1
  commits: 2
  framework_self_tests: 598 passed (+ 1 skipped, 17 deselected, 2 xfailed)
  completed_date: 2026-05-16
---

# Phase 27 Plan 02: Plugin pytest_configure + pytest_addoption Wiring -- Summary

## One-Liner

Wired the operator's one-line `[tool.pytest.ini_options] mcp_config_file = "./config.yaml"`
ini entry to a loaded `Config` instance stashed on `pytest.Config._mcp_contracts_config`,
with fail-loud `pytest.exit(returncode=2)` on missing-path / invalid-YAML and a
DeprecationWarning gate on the legacy `MCPTF_CONFIG_FILE` env var.

## Tasks Completed

| Task | Name | Status | Files |
|------|------|--------|-------|
| 1 | Extend `pytest_addoption` to register `mcp_config_file` ini key | DONE | `src/mcp_test_framework/_plugin.py` |
| 2 | Extend `pytest_configure` (env-var deprecation, ini read, path resolve, fail-loud, Config load, black-box guard, stash) | DONE | `src/mcp_test_framework/_plugin.py` |

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `d04efeb` | feat(27-02) | Register mcp_config_file ini key in plugin |
| `f044f1a` | feat(27-02) | Wire ini-driven config load + black-box guard in pytest_configure |

## Line Ranges in `_plugin.py` (for Plan 27-03's executor)

Post-Plan-27-02 layout in `src/mcp_test_framework/_plugin.py`:

| Region | Lines (approx) | Notes |
|--------|---------------|-------|
| Module docstring | 1-33 | Updated to describe ini-driven entry point + relocated guard |
| Imports | 34-44 | Added `os`, `warnings`, `Path`, `ValidationError`, `Config`, `check_black_box` (eager) |
| Fixture re-exports | 54-67 | UNCHANGED from Phase 26 |
| `pytest_configure` | 74-151 | Filled body: marker -> env-var warn -> ini read -> path resolve -> fail-loud -> Config load -> black-box guard -> stash. Plan 27-03 may extend this hook IFF it needs preflight ordering before collection. |
| `pytest_addoption` | 153-173 | Filled body: `getgroup` + `addini("mcp_config_file", type="string", default="")` |
| `pytest_collection_modifyitems` | 175-184 | UNCHANGED skeleton -- Plan 27-03's slot |
| Deprecation aliases (6 fixtures) | 187-end | UNCHANGED from Phase 26 |

The 7-statement order inside `pytest_configure` matches the plan's verification block 1:1.

## Manual Sanity Test Outputs (captured verbatim)

### Sanity 1 -- D-14 fail-loud on missing `mcp_config_file` path

Setup: tmp dir with `pyproject.toml` containing
```toml
[tool.pytest.ini_options]
mcp_config_file = "./nope.yaml"
```
and no `nope.yaml` on disk.

Run: `pytest --collect-only`

Output (last lines):
```
Exit: mcp_config_file points at C:\Users\washy\AppData\Local\Temp\mcptf_27_02_sanity1\nope.yaml which does not exist or is not a file

next: check the path in [tool.pytest.ini_options] in pyproject.toml, or run `mcp-contracts config-init -o config.yaml`
EXITCODE=2
```

Outcome: PASS -- exit code 2, operator-tone copy verbatim from the plan's literal target.

### Sanity 2 -- D-09 DeprecationWarning on `MCPTF_CONFIG_FILE` env var

Setup: framework root, `MCPTF_CONFIG_FILE=./nonexistent.yaml` (value is intentionally
irrelevant -- library mode ignores it per D-10), `PYTHONWARNINGS=always` to defeat
default-warnings suppression.

Run: `MCPTF_CONFIG_FILE=./nonexistent.yaml PYTHONWARNINGS=always uv run pytest --collect-only tests/framework/test_phase27_spike_synthetic_module.py`

Filtered output:
```
C:\Users\washy\projects\mvp_test_framework\.venv\Lib\site-packages\pluggy\_callers.py:121: DeprecationWarning: MCPTF_CONFIG_FILE env var is deprecated since v1.4 and will be removed in v1.5 [em-dash] use `[tool.pytest.ini_options] mcp_config_file = PATH` in pyproject.toml or pass `--config PATH` to mcp-contracts run instead.
```

(The `[em-dash]` glyph rendered as `—` on the wire; Windows console code-page
substitution shows it as `?` or `?` in the terminal -- the underlying string is the
literal copy verbatim, em-dash and all.)

Outcome: PASS -- literal Phase 25 deprecation-copy template renders verbatim.

Note: this matches the user's standing observation that DeprecationWarning visibility is
poor (gray text, easy to miss). Out of scope for 27-02; a later milestone may add a
formatwarning override or an operator-channel banner.

## Operator-Tone Helper Translation (chosen path)

The plan's strategy of `try: _emit_operator_error_for_validation(...) except SystemExit:
pytest.exit(2)` worked cleanly on the first attempt. No alternate path was needed.

`_emit_operator_error_for_validation` calls `_emit_operator_error` which raises
`typer.Exit(2)`. `typer.Exit` is a `click.exceptions.Exit` subclass, which in turn
inherits from `RuntimeError`/`SystemExit` semantically. In practice the bare-`SystemExit`
catch reliably intercepts it because typer's `Exit.exit_code` is honored by typer's
runner but not by pytest -- pytest treats the raise as a generic crash unless we
translate it. The plan-specified translation preserves the operator-tone rendered text
AND the returncode=2 convention end-to-end.

(Sanity-verified at the code level by walking the typer source; not exercised in a
manual sanity test because constructing a real `ValidationError` with the right shape
to traverse all three branches of `_emit_operator_error_for_validation` would require
fabricating a v1-vs-v2 YAML or a missing-required-field YAML -- both already covered
by existing framework self-tests `tests/framework/unit/test_cli_errors.py`.)

## Pytest 9.0.x API Quirks Encountered

None blocking. Observations:

- `config.rootpath` (pytest 7+ canonical) works as documented -- the directory
  containing `pyproject.toml`. No `inipath` aliasing surprises encountered.
- `config.getini("mcp_config_file")` with `default=""` returns `""` (empty string)
  when the operator omits the line, exactly as the plan predicted via D-13 +
  RESEARCH.md Pitfall 3. No `None` coercion or list-wrapping behavior.
- `parser.addini(..., type="string", default="")` works on pytest 9.0.3 without
  warnings. The `type="paths"` anti-pattern call from RESEARCH.md was not exercised
  (correctly avoided).
- `pytest.exit("...", returncode=2)` renders the message on the stderr-equivalent
  channel and exits with the requested code. The Windows PowerShell wrapping in
  Sanity 1's output is shell-side stderr-stream colorization, not a framework artifact.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Project gate: planning-ID leak in src/]** Scrubbed `D-NN` and `LIB-NN`
   references from docstrings and inline comments.

- **Found during:** Pre-Task-1 setup, while drafting the docstring update prompted by
  the plan's literal `(D-01 / LIB-01)` instruction.
- **Issue:** The framework's locked gate at
  `tests/framework/unit/test_no_planning_ids_in_src.py` enforces a zero-tolerance
  policy against `D-\d+`, `LIB-\d+`, `TEST-\d+`, etc. tokens in `src/`. The plan's
  verbatim docstring text included `(D-01 / LIB-01)` and the verbatim
  `pytest_configure` body inserted `D-09 / D-10 / D-12 / D-13 / D-14 / D-15 / D-18`
  comments.
- **Fix:** Rewrote the docstring and inline comments to reference concepts without
  the ID tag (per the user's prompt note "Reference concepts without the ID tag"
  and per the Plan 27-01 SUMMARY's identical Rule-2 deviation). All behavior,
  literal copy strings, and code paths preserved verbatim.
- **Files modified:** `src/mcp_test_framework/_plugin.py`
- **Commits:** Folded into `d04efeb` (Task 1) and `f044f1a` (Task 2).

### Out-of-Scope Discoveries

- The pre-existing `PytestAssertRewriteWarning: mcp_test_framework.fixtures` warning
  (Plan 27-01 SUMMARY Finding #3) still fires. Not a 27-02 regression; Plans 27-04
  or 27-05 own its cleanup.
- The user's `[Deprecation warning visibility (Phase 25)]` standing concern is
  re-validated here: the deprecation copy renders correctly but is gray and easy
  to miss when running under typical operator command-lines. Out of scope; a later
  milestone may add a formatwarning override.

## Files Modified (Summary)

```
src/mcp_test_framework/
  _plugin.py    # MODIFIED -- module docstring + import additions + pytest_addoption
                #             body extension + pytest_configure body rewrite. Skeleton
                #             pytest_collection_modifyitems and fixture re-exports
                #             UNTOUCHED.
```

## Files NOT Modified (per Plan)

| File | Reason | Handled By |
|------|--------|------------|
| `src/mcp_test_framework/_plugin.py:pytest_collection_modifyitems` body | Slot reserved for collection hook | Plan 27-03 |
| `src/mcp_test_framework/_plugin.py` fixture re-exports + deprecation aliases | Phase 26 surface stable across v1.4 | (no plan -- shipped) |
| `tests/conftest.py` black-box guard | Coexistence period until plugin guard ships | Plan 27-05 |
| `src/mcp_test_framework/config.py` env-var fallback at line 234-235 | CLI-mode code path needs it through v1.4 | v1.5 cleanup |

## Verification Gates -- All GREEN

| Gate | Command | Result |
|------|---------|--------|
| Task 1 ini-registration smoke | `uv run pytest --help 2>&1 \| grep -c mcp_config_file` | `1` |
| Task 1 acceptance greps | `grep -c 'parser.addini' \| 'mcp_config_file' \| 'type="string"' \| 'type="paths"' \| 'default=""'` | `1 / 1 / 1 / 0 / 1` |
| Task 2 acceptance greps | 9-grep panel from plan acceptance criteria | All `>= 1` |
| Task 2 sanity 1 (D-14 missing path) | tmp pyproject + missing yaml -> `pytest --collect-only` | exit 2, verbatim msg |
| Task 2 sanity 2 (D-09 env-var warning) | `MCPTF_CONFIG_FILE=... PYTHONWARNINGS=always pytest --collect-only` | verbatim copy printed |
| Framework regression | `uv run pytest tests/framework/ -x -q` | 598 passed, 1 skipped, 17 deselected, 2 xfailed |
| Planning-ID leak gate | `uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py` | included in framework regression -- GREEN |

## Self-Check: PASSED

File exists:
- `src/mcp_test_framework/_plugin.py` -- FOUND (modified)

Commits exist on `main`:
- `d04efeb` -- FOUND
- `f044f1a` -- FOUND

## Hand-Off to Plan 27-03

Plan 27-03 will fill `pytest_collection_modifyitems` (line ~175 in the current file).
Consumption pattern: `cfg = getattr(session.config, "_mcp_contracts_config", None)`. If
`cfg is None`, return early (library mode opted out -- Plan 27-02's silent no-op path
was taken). If `cfg is not None`, drive the `_ContractsModule` synthesis + `cfg.tools`
parametrize per the 27-01 Wave 0 spike pattern.

The `mcp_contract` marker is already registered (carry-forward in `pytest_configure`).
Plan 27-03's synthesized items should call `item.add_marker("mcp_contract")` after
attachment per the 27-01 spike finding (module-level `add_marker` does not propagate
to `Function` children in the synth construction path).
