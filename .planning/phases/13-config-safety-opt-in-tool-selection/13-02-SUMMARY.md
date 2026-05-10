---
phase: 13-config-safety-opt-in-tool-selection
plan: 02
subsystem: config
tags: [pydantic-settings, env-overlay, dotenv-strip, version-validator, error-style, safe-05, safe-06]

# Dependency graph
requires:
  - phase: 12-doc-persona-foundation
    provides: "docs/ERROR-STYLE.md SAFE-06 LOCKED migration message body; _emit_operator_error helper"
  - plan: 13-01
    provides: "Config(yaml_file=) kwarg seam in _load_config; xfail markers on 6 tests with strict=False"
provides:
  - "settings_customise_sources collapsed to (init_settings, YamlConfigSettingsSource, file_secret_settings)"
  - "_validate_version flipped to accept v2 only; v1 raises with the message the SAFE-06 mapper keys off of"
  - "LOCKED SAFE-06 migration message body wired verbatim into _emit_operator_error_for_validation"
  - "env-overlay and .env attack classes closed (SAFE-05)"
  - "Source-label substitution works via both --config and MCPTF_CONFIG_FILE entry paths"
affects:
  - 13-03-allowlist-three-state
  - 13-04-target-removal
  - 13-05-migration-doc

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "init_settings.init_kwargs.pop('yaml_file', None): pop (not get) so extra='forbid' does not re-trip the validator on the kwarg-as-extra-field path"
    - "Locked operator-message body in cli.py pinned by source-text regression in tests/unit/test_error_style.py (D-08 SAFE-06 wiring)"
    - "Source-label substitution from --config and MCPTF_CONFIG_FILE both feed source_label uniformly through _load_config"

key-files:
  created: []
  modified:
    - "src/mcp_test_framework/config.py - delete _BareNameNestedEnvSource (~60 LOC), _alias_env_names, _maybe_json_decode, dotenv/FieldInfo/AliasChoices/json/os imports; drop env_file from model_config; collapse settings_customise_sources to init_kwargs->YAML->defaults via .pop('yaml_file'); flip validator to require v=2"
    - "src/mcp_test_framework/cli.py - rewrite version-mismatch branch in _emit_operator_error_for_validation with LOCKED SAFE-06 body verbatim from docs/ERROR-STYLE.md:57-73"
    - "tests/unit/test_config.py - invert 5 env-overlay tests (env beats X -> env has no effect); add 4 SAFE-05/06 regression tests; adapt 2 existing tests to Config(yaml_file=) kwarg seam"
    - "tests/unit/test_error_style.py - add test_error_style_safe_06_body_matches_cli_wiring (source-text pin)"
    - "tests/unit/test_cli_errors.py - remove 4 Plan-13-01 xfail markers; add 2 SAFE-06 v1-config end-to-end tests (--config and MCPTF_CONFIG_FILE routes); flip 2 fixture YAMLs from version: 1 -> version: 2"
    - "tests/unit/test_config_init.py - remove xfail on test_scaffold_loadable_via_config; adapt to Config(yaml_file=) kwarg seam"
    - "tests/unit/test_list_tools_format.py - remove xfail on test_json_full_orthogonal; flip fixture YAML from version: 1 -> version: 2"

key-decisions:
  - "Pop pattern (init_kwargs.pop('yaml_file', None)) chosen over get + ClassVar declaration. Probe results recorded in plan: leaving the kwarg in init_kwargs trips extra='forbid' on the model validator (ExtraForbidden); pop neutralizes that before YamlSource is constructed."
  - "env_settings and dotenv_settings accepted as parameters (pydantic-settings forces the signature) but intentionally dropped from the returned tuple. # noqa: ARG003 annotations satisfy ruff without refactoring the signature."
  - "Removed obsolete env-overlay-precedence tests rather than xfail/skip — the v1.1 precedence model is gone, not deferred. Replaced with inverted-assertion tests pinning the new contract."
  - "Three fixture YAMLs that were previously xfailed (and were under version: 1) flipped to version: 2 in the same commit that unblocked them — keeps test intent aligned with the new schema."

patterns-established:
  - "Pop-from-init_kwargs idiom for resolver-IPC under extra='forbid'"
  - "LOCKED migration-message body pinned via source-text regression (test reads cli.py and asserts verbatim substring presence)"

requirements-completed: [SAFE-05, SAFE-06]

# Metrics
duration: 5min
completed: 2026-05-10
---

# Phase 13 Plan 02: Env-overlay strip + v2 validator Summary

**Env-overlay machinery deleted from config.py (D-05/D-06/D-07); _validate_version flipped to require v=2 (D-08); LOCKED SAFE-06 migration message wired verbatim into the version-mismatch branch of _emit_operator_error_for_validation**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-10T23:12:05Z
- **Completed:** 2026-05-10T23:17:15Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 7

## Accomplishments

- **config.py reduces from 217 LOC to ~100 LOC.** Deletions:
  - `_BareNameNestedEnvSource` class (~60 LOC)
  - `_alias_env_names`, `_maybe_json_decode` helpers
  - `from dotenv import dotenv_values`
  - `from pydantic.fields import FieldInfo`
  - `AliasChoices`, `json`, `os` imports at module scope
  - `env_file=".env"` and `env_file_encoding="utf-8"` from `model_config`
- **`settings_customise_sources` is now 3 lines of effective source-pipeline construction** plus a `pop` and a `is_file` guard:
  ```python
  yaml_file = init_settings.init_kwargs.pop("yaml_file", None)
  sources: list[PydanticBaseSettingsSource] = [init_settings]
  if yaml_file and Path(yaml_file).is_file():
      sources.append(YamlConfigSettingsSource(settings_cls, yaml_file=str(yaml_file)))
  sources.append(file_secret_settings)
  return tuple(sources)
  ```
- **`model_config`** is now `SettingsConfigDict(frozen=True, extra="forbid")` — nothing else.
- **`_validate_version`** rejects anything other than 2 with the message `_emit_operator_error_for_validation` keys off (`"not supported by this build"`).
- **SAFE-06 LOCKED body** wired verbatim into the version-mismatch branch — names `schema version 2 (opt-in tool selection)` / `version 1 (opt-out)`, includes the four-line port-forward paragraph, points at `docs/MIGRATION-v1-to-v2.md`, and ends with the locked `next:` line pointing at `config-init -o config.yaml.new`.
- **6 Plan-13-01 xfail markers cleared** — the SAFE-02 cwd autodiscovery test, the v1-validator-error test, both MCP-spawn-failure tests, the scaffold-loadable test, and the `--json --full` orthogonality test all pass for real now that `Config(yaml_file=...)` consumes the kwarg.
- **2 SAFE-06 end-to-end regression tests** — both `--config v1.yaml` and `MCPTF_CONFIG_FILE=v1.yaml` produce the locked SAFE-06 body verbatim with the operator's path echoed back as `source`.

## Task Commits

1. **Task 1 RED: failing tests for SAFE-05 env-overlay drop + SAFE-06 v2 validator** — `a7edc70` (test)
2. **Task 1 GREEN: strip env-overlay + flip validator to v2** — `c9de832` (feat)
3. **Task 2 RED: failing tests for SAFE-06 locked migration message wiring** — `6474e4c` (test)
4. **Task 2 GREEN: wire LOCKED SAFE-06 migration message in version-mismatch branch** — `5506a1f` (feat)

No REFACTOR commits were needed; both GREEN bodies were the final shape.

## Final shapes

### `model_config` (Config class)
```python
model_config = SettingsConfigDict(
    frozen=True,
    extra="forbid",
)
```

### `settings_customise_sources` returned tuple
After pop + skip-on-missing, the returned tuple is one of:

- `(init_settings, file_secret_settings)` — when `yaml_file` is None or points at a non-existent path
- `(init_settings, YamlConfigSettingsSource(...), file_secret_settings)` — when `yaml_file` points at an existing file

Three lines of effective shape; `env_settings` and `dotenv_settings` are dropped on the floor.

### `_validate_version` field validator
```python
@field_validator("version", mode="after")
@classmethod
def _validate_version(cls, v: int) -> int:
    if v != 2:
        raise ValueError(
            f"config version {v} not supported by this build, expected 2"
        )
    return v
```

### `_emit_operator_error_for_validation` version-mismatch branch
```python
if loc == "version" and "not supported by this build" in msg:
    _emit_operator_error(
        summary=f"config file uses an older format: {source}",
        detail=[
            "this release of mcp-test-framework expects schema version 2 (opt-in",
            "tool selection); your config is version 1 (opt-out). the difference",
            "matters: in v1 a tool with no entry runs by default, in v2 it skips",
            "by default.",
            "",
            "your existing per-tool settings (`call_arguments`, `judges`,",
            "`skip_reason`) port forward unchanged -- only the implicit default",
            "flips. the migration walkthrough at docs/MIGRATION-v1-to-v2.md shows",
            "the steps.",
        ],
        next_step=(
            "run `mcp-test-framework config-init -o config.yaml.new` to see "
            "the v2 layout, port your tool entries across, then replace your "
            "existing config"
        ),
    )
```

## Grep Gates (all pass)

| Gate                                                       | File       | Required  | Actual |
|------------------------------------------------------------|------------|-----------|--------|
| `_BareNameNestedEnvSource`                                 | config.py  | 0         | 0      |
| `_alias_env_names` or `_maybe_json_decode`                 | config.py  | 0         | 0      |
| `from dotenv import`                                       | config.py  | 0         | 0      |
| `from pydantic.fields import FieldInfo`                    | config.py  | 0         | 0      |
| `env_file`                                                 | config.py  | 0         | 0      |
| `if v != 2`                                                | config.py  | 1         | 1      |
| `version: int = 2`                                         | config.py  | 1         | 1      |
| `init_settings.init_kwargs.pop`                            | config.py  | 1         | 1      |
| `env_settings`/`dotenv_settings` in returned tuple         | config.py  | 0         | 0      |
| `env_settings`/`dotenv_settings` in parameter list/docs    | config.py  | (allowed) | 3      |
| `schema version 2 (opt-in`                                 | cli.py     | 1         | 1      |
| `your config is version 1 (opt-out)`                       | cli.py     | 1         | 1      |
| `docs/MIGRATION-v1-to-v2.md`                               | cli.py     | 1         | 1      |
| `config file uses an older format:`                        | cli.py     | 1         | 1      |
| `config-init -o config.yaml.new`                           | cli.py     | ≥1        | 1      |
| `unsupported schema version`                               | cli.py     | 0         | 0      |

## Test Results

- `uv run pytest tests/unit/test_config.py tests/unit/test_cli_errors.py -v -k "safe_05 or safe_06 or safe_02"` → **8 passed** (4 SAFE-05/06 in test_config.py + 2 SAFE-06 in test_cli_errors.py + 1 SAFE-02 autodiscovery + 1 SAFE-06 v1 ValidationError); deselected 23.
- `uv run pytest tests/unit/test_error_style.py tests/unit/test_cli_errors.py -v -k "safe_06 or error_style"` → **9 passed, 18 deselected** (the source-text wiring pin + both SAFE-06 end-to-end tests + 6 ERROR-STYLE doc tests).
- `uv run pytest tests/unit/ -q` → **167 passed, 0 xfailed** (was 155 passed, 6 xfailed on Plan 13-01 entry; the +12 swing = 4 new SAFE-05/06 tests in test_config.py + 1 new source-text pin in test_error_style.py + 2 new SAFE-06 e2e tests in test_cli_errors.py + 6 xfails flipped to pass — minus 1 deleted env-overlay test).
- Acceptance gate: `uv run python -c "from mcp_test_framework.config import Config; print(Config(yaml_file='/nonexistent').version)"` prints `2` (the pop neutralized `extra='forbid'`; YamlSource skipped the non-existent path; defaults applied; version defaults to 2).
- `uv run ruff check src/mcp_test_framework/config.py src/mcp_test_framework/cli.py` → All checks passed.

## Decisions Made

- **Pop, not get, in settings_customise_sources.** The plan probe results recorded the deterministic answer: `init_settings.init_kwargs.get("yaml_file")` leaves the kwarg in the init_kwargs dict, which then reaches the model validator under `extra="forbid"` and trips `ExtraForbidden` on the `yaml_file` field. `.pop("yaml_file", None)` removes it before construction; the `None` default keeps `Config()` (no kwargs) working for tests that want pure defaults.
- **# noqa: ARG003 over ARG004 on the signature.** The plan suggested `ARG004` but ruff classifies these as `ARG003` (unused method argument); installed ruff matched on `ARG003`. Functionally equivalent — the parameters are unused-by-design.
- **Deleted `test_env_overrides_dotenv_for_sub_model_fields` outright.** Both env and dotenv are gone; the test's precedence claim no longer makes sense. The 4 inverted-assertion tests cover the new contract.
- **Kept `_scrub_pydantic_jargon` in cli.py.** It's still used by the missing-field and generic-fallback branches of `_emit_operator_error_for_validation`. Only the version-mismatch branch's wording was rewritten.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Two fixture YAMLs in newly-unblocked tests still declared `version: 1`**
- **Found during:** Task 1 GREEN verification (running full unit suite after flipping the validator)
- **Issue:** After removing the Plan-13-01 xfail markers on `test_list_tools_mcp_spawn_failure` and `test_config_init_mcp_spawn_failure`, both tests failed because their inline YAML fixtures still wrote `version: 1` — which the flipped validator now rejects. Same problem in `test_json_full_orthogonal` (Plan 13-01 had xfailed it for the kwarg seam, not for the version flip; both unblocks landed here).
- **Fix:** Flipped `version: 1` -> `version: 2` in all three fixture bodies. These tests are not testing v1/v2 semantics — they test MCP-spawn error handling and JSON-output orthogonality, so the version literal is incidental.
- **Files modified:** `tests/unit/test_cli_errors.py`, `tests/unit/test_list_tools_format.py`
- **Verification:** All three tests now pass.
- **Committed in:** `c9de832` (Task 1 GREEN)

**2. [Rule 3 — Blocking] `test_scaffold_loadable_via_config` used MCPTF_CONFIG_FILE as a Config() source**
- **Found during:** Task 1 GREEN verification
- **Issue:** Per D-06, MCPTF_CONFIG_FILE is no longer a Config() source — the resolver in cli.py reads it but Config() itself does not. The test's previous shape (`monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path)); cfg = Config()`) silently returned defaults instead of the scaffolded YAML.
- **Fix:** Replaced the env-var set + bare `Config()` with `Config(yaml_file=str(cfg_path))` — the kwarg seam the resolver uses. Adjusted the test docstring to call out D-06.
- **Files modified:** `tests/unit/test_config_init.py`
- **Verification:** Test passes; asserts the scaffold's content (`version=2`, `mcp_server.command=='uvx'`, `'11434' in base_url`) survives the load.
- **Committed in:** `c9de832` (Task 1 GREEN)

---

**Total deviations:** 2 auto-fixed (both Rule 3 / blocking-issue scope-fixes to keep the formerly-xfailed tests passing).
**Impact on plan:** None on scope. Both were necessary follow-ups from removing the Plan-13-01 xfail markers — the plan named the xfail removal explicitly in Task 1 step 9.

## Forward refs

- **Plan 13-03 (allowlist three-state):** does not touch `config.py` or the version validator — independent. Wave 2 parallel-safety preserved (`files_modified` intersection with 13-03 is `tests/conftest.py` + `_reporter.py`, none of which Plan 13-02 modified).
- **Plan 13-04 (target removal):** still owns deleting the `target: TargetConfig` field from `Config` and the `TargetConfig` import. Plan 13-02 preserved both verbatim with a one-line comment marker noting the forward-ref.
- **Plan 13-05 (migration doc):** the LOCKED message in `cli.py` references `docs/MIGRATION-v1-to-v2.md` — Plan 13-05 creates that file. The reference in `cli.py` will be the regression-test target for "doc exists at the path the error points at."

## Self-Check: PASSED

All claimed files exist on disk and all claimed commits are reachable from HEAD:

- FOUND: `.planning/phases/13-config-safety-opt-in-tool-selection/13-02-SUMMARY.md` (this file)
- FOUND: `src/mcp_test_framework/config.py`
- FOUND: `src/mcp_test_framework/cli.py`
- FOUND: `tests/unit/test_config.py`
- FOUND: `tests/unit/test_error_style.py`
- FOUND: `tests/unit/test_cli_errors.py`
- FOUND: `tests/unit/test_config_init.py`
- FOUND: `tests/unit/test_list_tools_format.py`
- FOUND commit: `a7edc70` (test RED for Task 1)
- FOUND commit: `c9de832` (feat GREEN for Task 1)
- FOUND commit: `6474e4c` (test RED for Task 2)
- FOUND commit: `5506a1f` (feat GREEN for Task 2)

---
*Phase: 13-config-safety-opt-in-tool-selection*
*Completed: 2026-05-10*
