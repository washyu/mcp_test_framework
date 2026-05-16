---
phase: 25-public-api-rename-seed-023-sdet-test-code
plan: 03
subsystem: public-api / config-schema
tags: [rename, sdet, test_code, deprecation-shim, pydantic, AliasChoices, RENAME-05]
requires:
  - src/mcp_test_framework/models.py (SdetConfig pre-rename)
  - src/mcp_test_framework/config.py (Config.sdet field pre-rename)
provides:
  - mcp_test_framework.models.TestCodeConfig (renamed inner Pydantic model)
  - Config.test_code field with validation_alias=AliasChoices("test_code","sdet") (D-12)
  - Config._warn_or_reject_legacy_sdet_key model_validator (D-13 defense-in-depth)
  - _check_legacy_sdet_key_in_yaml YAML pre-scan helper (operator path)
  - Config.model_validate override (dict-validate path)
affects:
  - src/mcp_test_framework/cli.py (SdetConfig import + _BOOTSTRAP rename + cfg.sdet -> cfg.test_code at 1048)
  - src/mcp_test_framework/test_code/session.py (Rule 1: cfg.sdet attribute access at 68 + f-string at 82)
  - tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py (Rule 1: cfg.sdet attribute access at 68)
  - 11 framework self-test files under tests/framework/ (Rule 1: SdetConfig imports + Config(sdet=...) call sites + cfg.sdet source-text assertions)
tech-stack:
  added: []
  patterns:
    - "pydantic.AliasChoices on parent Config field — accepts both canonical and legacy YAML keys (established pattern from v1->v2 migration)"
    - "Pre-validation YAML scan via settings_customise_sources — necessary because pydantic-settings collapses alias keys before model_validator(mode='before') fires"
    - "model_validate override — necessary because BaseSettings.model_validate inherits BaseModel.model_validate but the BaseSettings source pipeline normalizes alias keys before the dict reaches mode='before' validators"
    - "pydantic_core.PydanticCustomError + ValidationError.from_exception_data — programmatic construction of a friendly ValidationError that routes through the existing _emit_operator_error_for_validation mapper"
    - "__test__ = False on TestCodeConfig — suppresses pytest's auto-discovery of Test* classes (defensive, no behavioral impact)"
    - "# noqa: sdet-rename-shim token on every shim line (D-18) for plan 06 sweep exclusion"
key-files:
  created: []
  modified:
    - src/mcp_test_framework/models.py (SdetConfig -> TestCodeConfig rename; __test__ = False)
    - src/mcp_test_framework/config.py (import AliasChoices/model_validator/Any; field rename + AliasChoices; mode='before' validator; settings_customise_sources YAML pre-scan; _check_legacy_sdet_key_in_yaml helper; model_validate override)
    - src/mcp_test_framework/cli.py (SdetConfig import; _BOOTSTRAP_SDET_STUB -> _BOOTSTRAP_TEST_CODE_STUB; two Config(sdet=) -> Config(test_code=); cfg.sdet.generated_root -> cfg.test_code.generated_root)
    - src/mcp_test_framework/test_code/session.py (Rule 1: cfg.sdet.generated_root attribute access -> cfg.test_code; f-string interpolation -> cfg.test_code)
    - tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py (Rule 1: cfg.sdet.generated_root -> cfg.test_code.generated_root)
    - tests/framework/conftest.py (Rule 1: SdetConfig import + _SDET_STUB + Config(sdet=) renamed)
    - tests/framework/test_config_init_cli.py (Rule 1: same pattern)
    - tests/framework/test_tool_config.py (Rule 1: same pattern across 3 sites)
    - tests/framework/smoke/test_smoke_homelab_mcp.py (Rule 1: same pattern)
    - tests/framework/smoke/test_smoke_ollama_judge.py (Rule 1: same pattern)
    - tests/framework/unit/test_config.py (Rule 1: same pattern + YAML BLOCK literal flipped to test_code:)
    - tests/framework/unit/test_config_sdet_field.py (Rule 1: loc=("sdet",) assertions -> loc=("test_code",); docstring + test names updated)
    - tests/framework/unit/test_homelab_config.py (Rule 1: same pattern)
    - tests/framework/unit/test_sdet_config_model.py (Rule 1: bulk SdetConfig -> TestCodeConfig)
    - tests/framework/unit/test_session_loader_invariants.py (Rule 1: source-text assertion grep -> cfg.test_code)
    - tests/framework/unit/test_gen_sdet_classes_config_driven.py (Rule 1: same)
decisions:
  - "D-12 honored: parent Config carries single test_code: TestCodeConfig field with validation_alias=AliasChoices('test_code', 'sdet')"
  - "D-13 honored: @model_validator(mode='before') on Config rejects raw input with BOTH keys present (defense-in-depth backstop)"
  - "D-13 nuance: pydantic-settings collapses alias keys before model_validator(mode='before') runs, so the operator-facing checks were moved upstream — _check_legacy_sdet_key_in_yaml in settings_customise_sources (YAML path) + Config.model_validate override (dict path). Both emit exactly one DeprecationWarning per process per call site. The model_validator stays as defense-in-depth."
  - "D-14 honored: internal code reads cfg.test_code.* exclusively; no cfg.sdet attribute remains in src/ except docstring/comment terminology references (plan 05 territory)"
  - "D-15 honored: SdetConfig class renamed to TestCodeConfig; no `SdetConfig = TestCodeConfig` typing alias retained"
  - "D-01 honored: stdlib DeprecationWarning, no custom subclass, no FutureWarning"
  - "D-02 honored: stacklevel=2, Python's default once-per-process filter"
  - "D-05 honored: warning text uses the locked template '<old> is deprecated since v1.4 and will be removed in v1.5 -- use <new> instead.'"
  - "D-18 honored: every shim line carries '# noqa: sdet-rename-shim' for the plan 06 sweep gate"
  - "Defensive __test__ = False on TestCodeConfig — pytest auto-discovers Test* classes; the model name shadows that convention and would emit a PytestCollectionWarning at every import site. The flag is a no-op for non-pytest callers and is not a runtime constraint."
  - "Plan-scope boundary held: --sdet flag, gen-sdet-classes command, _runner.run_pytest_subprocess(sdet=) kwarg, tests/sdet/ filesystem refs, config-init YAML heredoc, and operator-facing docstrings/error-message string literals all preserved (plans 02/04/05 own those surfaces)"
metrics:
  duration: ~20min
  completed: 2026-05-16
  tasks_completed: 2
  files_modified: 17
  commits: 2
---

# Phase 25 Plan 03: Public-API Rename (sdet -> test_code) — Config Schema Rename Summary

Renamed the Pydantic config model `SdetConfig` -> `TestCodeConfig` and the parent `Config` field `sdet` -> `test_code`. Both legacy (`sdet:`) and canonical (`test_code:`) YAML keys load into the same `TestCodeConfig` via `Field(validation_alias=AliasChoices("test_code","sdet"))`. The legacy key fires one stdlib `DeprecationWarning` per process naming the v1.4->v1.5 removal milestone; YAML with BOTH keys raises a `pydantic.ValidationError` with the canonical operator-tone message (no silent precedence rule). Internal `cfg.sdet.*` attribute reads in `cli.py` and `test_code/session.py` flipped to `cfg.test_code.*` so the codebase still imports + runs cleanly.

## Objective Met

RENAME-05 acceptance text holds:

- **Operator can set `test_code:` key in config.yaml**: loaded `cfg.test_code` returns a `TestCodeConfig` populated from the YAML value (verified end-to-end via `Config(yaml_file=...)` and `Config.model_validate({...})`).
- **Operator can set `sdet:` key in config.yaml**: loaded `cfg.test_code` returns the same `TestCodeConfig` (verified end-to-end); one `DeprecationWarning` per process fires on each entry point (YAML path: `config.py:247`; dict path: `model_validate` override).
- **Both keys in same YAML**: `Config(yaml_file=...)` raises `pydantic.ValidationError` mentioning the ambiguity; `Config.model_validate({...})` raises the same. The ValidationError is constructed against `Config` (title="Config", loc=("test_code",)) so the existing `_emit_operator_error_for_validation` mapper handles it on the same code path as every other config-load failure.
- **Internal code reads cfg.test_code.* exclusively**: the only remaining `cfg.sdet` reference in `src/` is in a module docstring at `test_code/session.py:11` (plan 05 terminology-sweep territory). No live attribute access remains.
- **No `SdetConfig` class**: removed from `models.py`; no typing alias retained per D-15.

## Tasks Completed

| # | Name                                                                                                                | Commit  | Files                                                                                                                                                                            |
| - | ------------------------------------------------------------------------------------------------------------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Rename SdetConfig -> TestCodeConfig + AliasChoices + model_validator + YAML pre-scan + model_validate override     | 1442dda | src/mcp_test_framework/config.py, src/mcp_test_framework/models.py                                                                                                              |
| 2 | Flip internal cfg.sdet read sites to cfg.test_code in cli.py + Rule 1 fixes in session.py + 12 test files          | 14d23aa | src/mcp_test_framework/cli.py, src/mcp_test_framework/test_code/session.py, 11 framework self-test files, tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py, models.py (__test__) |

## Verification

Plan-level `<verification>` block — all pass:

- **`<verification>` 1 (legacy YAML key loads + warns):**
  ```
  $ uv run python -W always::DeprecationWarning -c "...Config.model_validate({'version': 2, 'sdet': {'generated_root': 'x'}})..."
  DeprecationWarning: config.yaml key 'sdet:' is deprecated since v1.4 and will be removed in v1.5 -- use 'test_code:' instead.
  test_code: x
  ```

- **`<verification>` 2 (new YAML key loads silently):**
  ```
  $ uv run python ... Config.model_validate({'version': 2, 'test_code': {'generated_root': 'y'}})
  test_code: y; warnings: 0
  ```

- **`<verification>` 3 (both keys raises ValidationError):**
  ```
  $ uv run python -c "Config.model_validate({'version': 2, 'sdet': {...}, 'test_code': {...}})"
  pydantic.ValidationError: 1 validation error for Config / test_code / config.yaml contains both 'sdet' and 'test_code' keys -- ...
  ```

- **`<verification>` 4 (no live cfg.sdet attribute access in src/):**
  ```
  $ grep -rn "cfg\.sdet\." src/ | grep -v noqa | grep -v __pycache__
  src/mcp_test_framework/test_code/session.py:11:     ``<cfg.sdet.generated_root>/<slug>/__init__.py``
  ```
  Only docstring reference remaining — plan 05 territory.

- **`<verification>` 5 (SdetConfig class gone; TestCodeConfig present):**
  ```
  $ uv run python -c "import mcp_test_framework.models as m; print('SdetConfig:', hasattr(m, 'SdetConfig'), 'TestCodeConfig:', hasattr(m, 'TestCodeConfig'))"
  SdetConfig: False; TestCodeConfig: True
  ```

- **`<verification>` 6 (tests/sdet/ refs in _runner.py preserved):** `grep -c "tests/sdet" src/mcp_test_framework/_runner.py` -> 9 (plan 04 owns these for dual-discovery).

- **`<verification>` 7 (--sdet flag refs in cli.py preserved):** `grep -c -- "--sdet" src/mcp_test_framework/cli.py` -> 2 (plan 02 owns these; hidden shim).

Framework test suite end-state: `uv run python -m pytest tests/framework/ --tb=no -q` -> **578 passed, 1 skipped, 2 xfailed, 17 deselected, 61 warnings**. Same green-up state as plans 25-01 (578 passed) and 25-02 (578 passed). The 61 warnings are intentional shim-coverage DeprecationWarnings: legacy `sdet:` YAML loaders (pinned by D-03 `filterwarnings = always::DeprecationWarning:mcp_test_framework`), `--sdet` flag, `gen-sdet-classes` command, `mcp_test_framework.sdet` package import (all expected during the v1.4 deprecation window).

## Deviations from Plan

### Implementation deviation (D-13 mechanism)

**Plan said:** Add a `@model_validator(mode='before')` on `Config` that handles both the deprecation warning and the ambiguity rejection.

**Reality:** That works correctly for plain `BaseModel.model_validate(dict)` but NOT for `BaseSettings`. Probe verified: pydantic-settings normalizes alias-choice keys via the source-merging pipeline BEFORE `mode='before'` validators run. For `BaseSettings`:

- `Config(yaml_file=both.yaml)`: the YAML source collapses both `sdet:` and `test_code:` into the canonical field name during source construction; the validator only sees the merged dict.
- `Config.model_validate({'sdet': X, 'test_code': Y})`: the dict path also routes through the same alias-resolution; the validator sees only one key.

The locked contract (one DeprecationWarning per process on legacy key; ValidationError on both keys present) is preserved via two upstream interceptors AND the model_validator (as defense-in-depth):

1. **`_check_legacy_sdet_key_in_yaml`** (called from `settings_customise_sources`) pre-scans the raw YAML before pydantic-settings opens the file. Handles the operator path.
2. **`Config.model_validate` override** pre-scans the input dict before delegating to `super().model_validate()`. Handles the dict-validate path (framework self-tests and ad-hoc construction).
3. **`_warn_or_reject_legacy_sdet_key` model_validator** (D-13 backstop) still runs; emits no warning (to avoid double-fire) and only rejects ambiguity. In practice the upstream interceptors catch every realistic case first.

Per CONTEXT.md "Claude's Discretion": the planner explicitly allowed implementation latitude on the warning's call-site location ("Whether the alias shim's warning fires from `__init__.py` of the new package or from a lightweight `sdet/` re-export module. Either is fine; planner picks."). Same principle applies here — the D-13 *behavior contract* is preserved (one warning per process; ValidationError on ambiguity); the *implementation mechanism* moved upstream to accommodate pydantic-settings' source-merging pipeline.

This is not a Rule 4 architectural change — the public API (`AliasChoices` on the field; ambiguity rejected; warning fires once) is exactly what RENAME-05 specifies.

### Auto-fixed Issues

**1. [Rule 1 - Bug] 12 framework self-test files broken by SdetConfig rename + Config field rename**

- **Found during:** Post-Task-2 `uv run python -m pytest tests/framework/`. Same precedent as plans 25-01 (11 test files) and 25-02 (3 test files): the rename of a class/field directly imported by tests breaks them at collection time.
- **Issue (3 categories):**
  1. `from mcp_test_framework.models import SdetConfig` -> ImportError after D-15 hard rename.
  2. `Config(sdet=_SDET_STUB)` keyword -> the `validation_alias=AliasChoices("test_code", "sdet")` accepts the legacy YAML key via `model_validate`, but in `BaseSettings.__init__(**kwargs)` the kwarg name still has to match a field (Pydantic does not route the kwarg through alias resolution on `BaseSettings.__init__`).
  3. Source-text assertions: `test_session_loader_invariants.py` and `test_gen_sdet_classes_config_driven.py` literally `assert "cfg.sdet.generated_root" in <source>` — after the rename, the source contains `cfg.test_code.generated_root`. `test_config_sdet_field.py` literally asserts `loc=("sdet",)` from `ValidationError.errors()` — after the rename, missing-field errors report `loc=("test_code",)`.
- **Fix:** Bulk replace `SdetConfig` -> `TestCodeConfig`, `_SDET_STUB` -> `_TEST_CODE_STUB`, `Config(sdet=...)` -> `Config(test_code=...)` across 12 files. Updated source-text and loc assertions in 3 test files to grep/match the new attribute name.
- **Files modified:** 12 test files plus the two real-attribute-access fixes (`test_code/session.py`, `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py`); listed in the frontmatter `key-files.modified`.
- **Commit:** `14d23aa` (bundled with the Task 2 source change since the test breakage and source rename are atomically linked — same precedent plans 25-01 and 25-02 set).

**Why this isn't out-of-scope:** Per project memory `feedback_phase_scope_intent.md` ("when a phase title names a fix, the actual fix is in scope; don't let sub-agents reframe it as cross-cutting / defer"), a config-schema rename plan that breaks framework self-tests must repair them here. Skipping the fix would leave `tests/framework/` red at HEAD between this plan and the next — exactly the fragmented state plans 25-01 and 25-02 deliberately avoided.

**Why this isn't owned by plan 05 (terminology sweep):** Plan 05 owns the *terminology* sweep — replacing the literal word "sdet" / "SDET" in docstrings, comments, and operator-visible help strings. It does NOT own broken-import / broken-assertion failures from THIS plan's class+field rename. Plan 05 will sweep through the same files cosmetically (docstrings + comments still saying "Phase 21.1 RELOC-01: Config.sdet is REQUIRED") but the import/runtime breakage is solely caused by Task 1's rename and is Task 2's clean-up.

**2. [Rule 1 - Bug] `test_code/session.py` real `cfg.sdet.generated_root` attribute access**

- **Found during:** Code inspection while scoping Task 2. Plan 25-03's Task 2 lists `cli.py / fixtures.py / _runner.py / models.py` for `cfg.sdet` flip, but the production code path that the `mcp_session` fixture exercises lives in `test_code/session.py` (renamed from `sdet/session.py` in plan 25-01). After Task 1 the field name is `test_code`, so `cfg.sdet.generated_root` at line 68 would `AttributeError` at runtime, breaking every SDET scenario that uses the `mcp_session` fixture.
- **Fix:** Two precise edits — the attribute read at line 68 and the f-string interpolation at line 82 (the latter only the slot expression; the string LITERAL `'sdet.generated_root'` stays for plan 05's terminology sweep to flip).
- **Files modified:** `src/mcp_test_framework/test_code/session.py`
- **Commit:** `14d23aa`

**3. [Rule 1 - Bug] `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py` real `cfg.sdet.generated_root` attribute access**

- **Found during:** Pre-commit grep across `tests/` for `cfg.sdet`. Same pattern as the previous deviation — the readme-sample scenario loads generated classes by reading `cfg.sdet.generated_root` at import time. Would break the live-Proxmox UAT after Task 1.
- **Fix:** Single attribute access flip.
- **Files modified:** `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py`
- **Commit:** `14d23aa`

### `__test__ = False` on TestCodeConfig (defensive add)

- **Found during:** Initial `pytest --collect-only` after Task 1. Pytest's default discovery sees `class TestCodeConfig:` (starts with `Test`) and emits `PytestCollectionWarning: cannot collect test class 'TestCodeConfig' because it has a __init__ constructor` for every module that imports the class — i.e. every framework self-test that constructs Config.
- **Fix:** Added `__test__ = False` as a class-level attribute on `TestCodeConfig`. This is the pytest-documented opt-out for `Test*`-named classes. No-op for non-pytest callers; Pydantic doesn't treat it as a field (verified — `model_fields` is unchanged).
- **Files modified:** `src/mcp_test_framework/models.py`
- **Commit:** `14d23aa`

**Why this isn't an architectural concern:** The class name `TestCodeConfig` was locked by D-15. The collision with pytest's `Test*` discovery convention is a side-effect of that naming. `__test__ = False` is the established pytest-side opt-out (documented in pytest's own docs for exactly this case). It is not a workaround for a Pydantic issue and does not affect the model's contract.

## Scope Boundary Held

Per plan 25-03 Task 2 scope rules and CONTEXT.md ownership map, the following were intentionally **not** touched:

- `--sdet` flag on `run` command (cli.py:448, 498 — plan 02 owns)
- `gen-sdet-classes` Typer command shim (cli.py — plan 02 owns)
- `_runner.run_pytest_subprocess(sdet=...)` kwarg in cli.py:549, 621 (the `sdet` kwarg is the function-parameter name on `_runner` — plan 04 owns)
- `_runner.py` `sdet=` parameters at lines 86, 155, 191, 222 (plan 04)
- `tests/sdet/conftest.py` and `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py` directory location (plan 04 will `git mv` these to `tests/test_code/`)
- `tests/sdet/_generated/` untracked operator artifact (regenerated by `gen-test-classes`)
- `config-init` heredoc YAML scaffold at cli.py:1371, 1407-1413, 1419-1420 — emits operator-facing YAML with `sdet:` block (plan 05 will flip to `test_code:`)
- `gen_test_classes` docstring `<sdet.generated_root>` references at cli.py:980, 981, 1031 (plan 05)
- `'sdet.generated_root'` string literal at session.py:82 and `<cfg.sdet.generated_root>` in session.py:11 docstring (plan 05)
- `cfg.sdet.generated_root` references in docstrings/comments of 5 test files (plan 05)
- README §`## SDET scenarios` (plan 05 / Phase 30 CLOSE-04)

## TDD Gate Compliance

Plan type is `execute` (not `tdd`); no RED/GREEN/REFACTOR gate sequence required. The framework-self-test repoint follows the existing test contract (no new test invariants added beyond the strengthened source-text assertions in `test_session_loader_invariants.py` and `test_gen_sdet_classes_config_driven.py`).

## Self-Check: PASSED

Commits verified (`git log --oneline -3`):
- FOUND: 1442dda (feat(25-03): rename SdetConfig to TestCodeConfig + AliasChoices + ambiguity rejection)
- FOUND: 14d23aa (feat(25-03): flip internal cfg.sdet read sites to cfg.test_code)

Files verified (key artifacts referenced in this summary exist on disk):
- FOUND: src/mcp_test_framework/config.py (modified — AliasChoices field + model_validator + YAML pre-scan + model_validate override)
- FOUND: src/mcp_test_framework/models.py (modified — TestCodeConfig class + __test__ = False)
- FOUND: src/mcp_test_framework/cli.py (modified — _BOOTSTRAP_TEST_CODE_STUB + Config(test_code=) + cfg.test_code.generated_root)
- FOUND: src/mcp_test_framework/test_code/session.py (modified — cfg.test_code.generated_root)
- FOUND: tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py (modified — cfg.test_code.generated_root)
- FOUND: tests/framework/conftest.py (modified — TestCodeConfig + Config(test_code=))
- FOUND: tests/framework/unit/test_config.py (modified — TestCodeConfig + _TEST_CODE_STUB + _TEST_CODE_YAML_BLOCK + Config(test_code=))
- FOUND: tests/framework/unit/test_config_sdet_field.py (modified — loc=("test_code",) + cfg.test_code)
- FOUND: tests/framework/unit/test_sdet_config_model.py (modified — TestCodeConfig)
- FOUND: tests/framework/unit/test_homelab_config.py (modified — same pattern)
- FOUND: tests/framework/test_tool_config.py (modified — same pattern)
- FOUND: tests/framework/test_config_init_cli.py (modified — same pattern)
- FOUND: tests/framework/smoke/test_smoke_ollama_judge.py (modified — same pattern)
- FOUND: tests/framework/smoke/test_smoke_homelab_mcp.py (modified — same pattern)
- FOUND: tests/framework/unit/test_session_loader_invariants.py (modified — cfg.test_code.generated_root source assertion)
- FOUND: tests/framework/unit/test_gen_sdet_classes_config_driven.py (modified — cfg.test_code.generated_root source assertion)
