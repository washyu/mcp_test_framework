---
phase: 13-config-safety-opt-in-tool-selection
plan: 02
type: execute
wave: 2
depends_on: [13-01]
files_modified:
  - src/mcp_test_framework/config.py
  - tests/unit/test_config.py
  - tests/unit/test_error_style.py
  - tests/unit/test_cli_errors.py
autonomous: true
requirements: [SAFE-05, SAFE-06]
must_haves:
  truths:
    - "Setting OLLAMA_BASE_URL / MCP_SERVER_COMMAND / TARGET_TOOL_NAME / JUDGE_TIMEOUT_SECONDS in os.environ has ZERO effect on Config() values; only YAML and init kwargs shape the model."
    - "A .env file in cwd has ZERO effect on Config() values."
    - "Loading a config containing `version: 1` raises a typer.Exit(2) error whose body matches docs/ERROR-STYLE.md SAFE-06 verbatim — names `version: 2`, names opt-in/opt-out, points at `config-init -o config.yaml.new`, references docs/MIGRATION-v1-to-v2.md."
    - "Loading a config containing `version: 2` succeeds (no validator rejection)."
    - "Config(yaml_file=<path>) reads its YAML from that path via settings_customise_sources reading init_settings.init_kwargs."
    - "`from dotenv import dotenv_values` no longer appears in src/mcp_test_framework/config.py."
    - "_BareNameNestedEnvSource class no longer exists in src/mcp_test_framework/config.py."
  artifacts:
    - path: "src/mcp_test_framework/config.py"
      provides: "Env-overlay-free Config with v2 validator and YAML-only source pipeline"
      contains: "if v != 2"
    - path: "tests/unit/test_config.py"
      provides: "Regression tests for SAFE-05 env-overlay drop and SAFE-06 v1 rejection"
  key_links:
    - from: "src/mcp_test_framework/config.py:Config.settings_customise_sources"
      to: "src/mcp_test_framework/cli.py:_load_config"
      via: "init_settings.init_kwargs.get('yaml_file')"
      pattern: "init_settings.init_kwargs"
    - from: "src/mcp_test_framework/config.py:_validate_version"
      to: "docs/ERROR-STYLE.md SAFE-06 reference message"
      via: "cli.py:_emit_operator_error_for_validation summary/detail rewrite"
      pattern: "schema version 2 \\(opt-in"
---

<objective>
Strip the env-overlay and `.env` plumbing from `src/mcp_test_framework/config.py` so YAML + init kwargs become the only config sources, and flip the version validator from accepting v1 to accepting v2 — wiring the SAFE-06 ERROR-STYLE message verbatim through `cli.py:_emit_operator_error_for_validation`. After this plan ships, a typo'd env var like `OLLAMA_BASE_URL=wrong` has zero effect on the run, a `.env` file in cwd is dead-letter, and loading a v1-era config produces the locked SAFE-06 operator-tone error pointing at `config-init` and `docs/MIGRATION-v1-to-v2.md`.

Purpose: SAFE-05 (drop env-overlay entirely — closes the "env beats YAML" bug class and the ".env silently beats --config" bug class) and SAFE-06 (version: 1 → 2 with a loud migration error).

Output: A `config.py` whose `settings_customise_sources` returns `(init_settings, YamlConfigSettingsSource(yaml_file=<from init kwargs>), file_secret_settings)`; whose `_validate_version` checks `v != 2`; whose `model_config` has `frozen=True, extra="forbid"` only (no `env_file`/`env_file_encoding`); and a `cli.py:_emit_operator_error_for_validation` whose version-mismatch branch matches `docs/ERROR-STYLE.md:57-73` verbatim.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md
@.planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md
@.planning/phases/13-config-safety-opt-in-tool-selection/13-01-SUMMARY.md
@docs/ERROR-STYLE.md
@src/mcp_test_framework/config.py
@src/mcp_test_framework/cli.py
@src/mcp_test_framework/models.py
@tests/unit/test_config.py
@tests/unit/test_error_style.py

<interfaces>
Key interfaces in scope (extracted to avoid scavenger hunts):

From `src/mcp_test_framework/config.py` (current state, pre-Plan 13-02):
```python
class Config(BaseSettings):
    model_config = SettingsConfigDict(
        frozen=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    mcp_server: McpServerConfig = Field(default_factory=McpServerConfig)
    target: TargetConfig = Field(default_factory=TargetConfig)   # leaves in Plan 13-04
    judge_timeout_seconds: int = 120
    version: int = 1
    tools: dict[str, ToolConfig] = Field(default_factory=dict)

    @field_validator("version", mode="after")
    def _validate_version(cls, v: int) -> int:
        if v != 1:
            raise ValueError(f"config version {v} not supported by this build, expected 1")
        return v

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings,
                                    dotenv_settings, file_secret_settings):
        yaml_path = os.environ.get("MCPTF_CONFIG_FILE")
        sources = [init_settings, _BareNameNestedEnvSource(settings_cls),
                   env_settings, dotenv_settings]
        if yaml_path and Path(yaml_path).is_file():
            sources.append(YamlConfigSettingsSource(settings_cls, yaml_file=yaml_path))
        sources.append(file_secret_settings)
        return tuple(sources)
```

From `src/mcp_test_framework/cli.py` (post-Plan 13-01):
```python
def _load_config(path: Path | None) -> Config:
    # ... resolves --config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud ...
    return Config(yaml_file=str(resolved))  # <-- this is the kwarg Plan 13-02's source reads
```

From `docs/ERROR-STYLE.md:57-73` (LOCKED — copy verbatim into the validation-error mapper):
```
config file uses an older format: <path>

this release of mcp-test-framework expects schema version 2 (opt-in
tool selection); your config is version 1 (opt-out). the difference
matters: in v1 a tool with no entry runs by default, in v2 it skips
by default.

your existing per-tool settings (`call_arguments`, `judges`,
`skip_reason`) port forward unchanged -- only the implicit default
flips. the migration walkthrough at docs/MIGRATION-v1-to-v2.md shows
the steps.

next: run `mcp-test-framework config-init -o config.yaml.new` to see
      the v2 layout, port your tool entries across, then replace your
      existing config
```
</interfaces>
</context>

<truths>
**Locked decisions implemented by this plan (quoted from 13-CONTEXT.md):**

- **D-05:** "Full strip of the env-overlay machinery. Delete `_BareNameNestedEnvSource` entirely (~60 lines in `config.py`); remove `env_settings` and `dotenv_settings` from the `settings_customise_sources` tuple; remove `env_file` and `env_file_encoding` from `model_config`; remove `python-dotenv` from direct `pyproject.toml` deps; delete the `_alias_env_names` helper and `_maybe_json_decode` helper. Config() sources collapse to `init_settings` (CLI-resolved path) → `YamlConfigSettingsSource(yaml_file=<resolved>)` → defaults."
- **D-06:** "`MCPTF_CONFIG_FILE` survives, but only as a pointer-to-config read by `_load_config` — not as a `Config()` source. This is a directory-of-search-paths convention, not config-value-from-env."
- **D-07:** "`.env` becomes dead-letter for the framework. The framework's config layer no longer reads `.env`."
- **D-08:** "`version: 2` is the only accepted value. Update the `_validate_version` field_validator in `config.py:184-192` from `if v != 1` to `if v != 2`. Loading a `version: 1` config raises with the SAFE-06 ERROR-STYLE message (pre-drafted in Phase 12 ERROR-STYLE.md)."
- **Claude's-discretion bullet 5 (kept as-is):** "the `validation_alias=AliasChoices('OLLAMA_BASE_URL', 'base_url')` style on `OllamaConfig`/`McpServerConfig` survives unchanged — env-routing role is gone, but the YAML-key role still works because pydantic's alias resolution accepts any of the choices on the YAML input." DO NOT touch `models.py` sub-model alias declarations in this plan.

**SAFE-06 LOCKED message body** (verbatim from `docs/ERROR-STYLE.md:57-73`) — wire into `_emit_operator_error_for_validation`'s version-mismatch branch (`cli.py:129-143`):

```
config file uses an older format: <path>

this release of mcp-test-framework expects schema version 2 (opt-in
tool selection); your config is version 1 (opt-out). the difference
matters: in v1 a tool with no entry runs by default, in v2 it skips
by default.

your existing per-tool settings (`call_arguments`, `judges`,
`skip_reason`) port forward unchanged -- only the implicit default
flips. the migration walkthrough at docs/MIGRATION-v1-to-v2.md shows
the steps.

next: run `mcp-test-framework config-init -o config.yaml.new` to see
      the v2 layout, port your tool entries across, then replace your
      existing config
```
</truths>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Strip env-overlay machinery from config.py and rewire settings_customise_sources</name>
  <files>src/mcp_test_framework/config.py, tests/unit/test_config.py</files>
  <read_first>
    - src/mcp_test_framework/config.py (read in full — you are deleting ~110 lines and rewriting two methods)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md §3 (the deletion list, the new settings_customise_sources shape, and the `init_settings.init_kwargs.get('yaml_file')` idiom)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md §decisions D-05, D-06, D-07
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-01-SUMMARY.md (confirms 13-01 already passes Config(yaml_file=...) — this plan reads that kwarg)
    - tests/unit/test_config.py (existing regression tests; you will adapt env-overlay tests to xfail/delete, add new SAFE-05 tests)
  </read_first>
  <behavior>
    - Loading a v2 YAML at path P with `Config(yaml_file=str(P))`: returns a Config whose fields reflect P's values.
    - Loading the same YAML with OLLAMA_BASE_URL / MCP_SERVER_COMMAND / TARGET_TOOL_NAME set in os.environ to different values: Config fields reflect the YAML values, NOT the env values.
    - Loading the same YAML with a `.env` file present in cwd setting different values: Config fields reflect the YAML values, NOT the `.env` values.
    - Calling Config() with no `yaml_file` kwarg: returns defaults only (no error) — used internally by tests that want pure-default Config.
    - The module's imports do NOT include `from dotenv import ...` or `from pydantic.fields import FieldInfo`.
    - The classes/functions `_BareNameNestedEnvSource`, `_alias_env_names`, `_maybe_json_decode` are gone.
  </behavior>
  <action>
    Rewrite `src/mcp_test_framework/config.py` to the shape below. Do this as a series of focused edits, not a full file rewrite (the docstring at the top can be modernized but DO NOT touch the `TargetConfig` import — Plan 13-04 owns that removal). The end state must read like this (showing only the changed regions; keep all other tokens, blank lines, and trailing newline behavior consistent with the existing file):

    1. **Module docstring** (lines 1-26): Replace with a shorter, accurate docstring:

       ```python
       """Top-level layered configuration via pydantic-settings.

       Precedence (Phase 13 D-05):

           CLI/init kwargs (yaml_file=PATH) > YAML overlay at PATH > defaults

       The resolver in `cli.py:_load_config` (Phase 13 D-03) passes the resolved
       YAML path as an explicit `yaml_file` kwarg to `Config(...)`. The custom
       `settings_customise_sources` below reads that kwarg from `init_settings`
       and hands it to `YamlConfigSettingsSource`. `MCPTF_CONFIG_FILE`, `--config`,
       and `./config.yaml` autodiscovery are all resolved in `cli.py` BEFORE
       `Config(...)` is constructed; no env vars influence Config values directly.

       `.env` is dead-letter for the framework's config layer (Phase 13 D-07).
       Sub-model `validation_alias=AliasChoices(...)` declarations on
       `OllamaConfig` etc. survive only for YAML-key matching; the env-routing
       role is gone (D-05).
       """
       ```

    2. **Imports** (lines 28-50): The end state is:

       ```python
       from __future__ import annotations

       from pathlib import Path
       from typing import Any

       from pydantic import Field, field_validator
       from pydantic_settings import (
           BaseSettings,
           PydanticBaseSettingsSource,
           SettingsConfigDict,
           YamlConfigSettingsSource,
       )

       from mcp_test_framework.models import (
           McpServerConfig,
           OllamaConfig,
           TargetConfig,
           ToolConfig,
       )
       ```

       Specifically: DELETE `import json`, `import os`, `from dotenv import dotenv_values`, `from pydantic.fields import FieldInfo`, and the `AliasChoices` import (no longer used here). KEEP `TargetConfig` import — Plan 13-04 removes it. KEEP `Any` (still used by `Field` defaults). The unused `Path` import survives because we might use it inside source customization; if your final code does not use Path, drop it — but ruff will catch it.

    3. **Delete helpers and the custom source** (lines 53-147 in the current file):
       - Delete `_alias_env_names` (lines 53-61).
       - Delete `_maybe_json_decode` (lines 64-89).
       - Delete `_BareNameNestedEnvSource` class entirely (lines 92-147).

    4. **`Config.model_config`** (lines 157-162): replace with:

       ```python
       model_config = SettingsConfigDict(
           frozen=True,
           extra="forbid",
       )
       ```

       Specifically: drop `env_file=".env"` and `env_file_encoding="utf-8"`. Keep `frozen=True` and `extra="forbid"` (D-05 explicit).

    5. **`_validate_version`** (lines 184-192): change to:

       ```python
       @field_validator("version", mode="after")
       @classmethod
       def _validate_version(cls, v: int) -> int:
           """Phase 13 D-08: only `2` is accepted; v1 configs raise so cli.py's
           operator-error mapper can render the SAFE-06 ERROR-STYLE message."""
           if v != 2:
               raise ValueError(
                   f"config version {v} not supported by this build, expected 2"
               )
           return v
       ```

       Also flip the default in the class body (line 176):

       ```python
       # Phase 13 D-08: v2 schema. Plan 13-02 flipped from v1.
       version: int = 2
       ```

    6. **`settings_customise_sources`** (lines 194-217): replace with:

       ```python
       @classmethod
       def settings_customise_sources(
           cls,
           settings_cls: type[BaseSettings],
           init_settings: PydanticBaseSettingsSource,
           env_settings: PydanticBaseSettingsSource,
           dotenv_settings: PydanticBaseSettingsSource,
           file_secret_settings: PydanticBaseSettingsSource,
       ) -> tuple[PydanticBaseSettingsSource, ...]:
           """Phase 13 D-05: collapse the source pipeline to
           init_kwargs -> YAML -> defaults. env_settings and dotenv_settings
           are accepted as parameters (pydantic-settings calls us with them)
           but intentionally dropped from the returned tuple.

           The resolver in cli.py:_load_config passes the resolved YAML
           path as `Config(yaml_file=str(path))`; we read that kwarg from
           init_settings.init_kwargs (D-03) and hand it to
           YamlConfigSettingsSource.
           """
           sources: list[PydanticBaseSettingsSource] = [init_settings]
           yaml_file = init_settings.init_kwargs.get("yaml_file")
           if yaml_file and Path(yaml_file).is_file():
               sources.append(
                   YamlConfigSettingsSource(settings_cls, yaml_file=str(yaml_file))
               )
           sources.append(file_secret_settings)
           return tuple(sources)
       ```

       Notes:
       - The `env_settings` and `dotenv_settings` parameters are required by the pydantic-settings signature; we accept them and ignore them. The `# noqa: ARG004` annotation may be needed if ruff complains; do not refactor the signature.
       - We do NOT strip `yaml_file` from `init_settings.init_kwargs` — leaving it in is harmless because `Config` doesn't define a `yaml_file` field, and `extra="forbid"` is enforced on the YAML-merged data, not on init kwargs (pydantic-settings discards unknown init kwargs by default in this idiom; if a TypeError appears, add `yaml_file` to the `Config` class as a `ClassVar[None]` or pop the key inside `settings_customise_sources` before YamlConfigSettingsSource consumes init_settings. Use whichever pydantic-settings 2.14 accepts — verify with `uv run python -c "from mcp_test_framework.config import Config; print(Config(yaml_file='nonexistent').version)"` returning `2`).

    7. **Update existing tests in tests/unit/test_config.py:** locate every test that relies on env-overlay or `.env` setting Config values (search for `monkeypatch.setenv`, `OLLAMA_BASE_URL=`, etc.). For each:
       - If it asserts "env var overrides default": INVERT the assertion to "env var has no effect; default wins". Add a comment `# Phase 13 D-05: env-overlay dropped; this test pins the negation.`
       - If it asserts "env var overrides YAML": INVERT to "env var has no effect; YAML wins".
       - If it asserts ".env file values propagate": INVERT to ".env is ignored; defaults/YAML win".
       - If the test cannot be inverted meaningfully, DELETE it and add a one-line replacement asserting `Config(yaml_file=<minimal-v2-yaml>).ollama.base_url == "<yaml-value>"` (proving YAML still works) AND a sibling asserting the same with env var set to a different value still returns the YAML value.

    8. **Add new SAFE-05 regression tests** to `tests/unit/test_config.py`:

       ```python
       def test_safe_05_env_var_does_not_override_yaml(tmp_path, monkeypatch) -> None:
           """Phase 13 D-05/D-07: env-overlay is gone; YAML wins."""
           yaml_path = tmp_path / "c.yaml"
           yaml_path.write_text(
               "version: 2\n"
               "ollama:\n"
               "  base_url: http://from-yaml:11434\n"
               "  model: qwen3.6:latest\n"
               "mcp_server:\n"
               "  command: /bin/true\n"
               "tools: {}\n",
               encoding="utf-8",
           )
           monkeypatch.setenv("OLLAMA_BASE_URL", "http://from-env:11434")
           monkeypatch.setenv("MCP_SERVER_COMMAND", "/usr/bin/should-be-ignored")
           cfg = Config(yaml_file=str(yaml_path))
           assert cfg.ollama.base_url == "http://from-yaml:11434"
           assert cfg.mcp_server.command == "/bin/true"

       def test_safe_05_dotenv_file_in_cwd_has_no_effect(
           tmp_path, monkeypatch
       ) -> None:
           """Phase 13 D-07: .env is dead-letter for the framework."""
           (tmp_path / ".env").write_text(
               "OLLAMA_BASE_URL=http://from-dotenv:11434\n",
               encoding="utf-8",
           )
           yaml_path = tmp_path / "c.yaml"
           yaml_path.write_text(
               "version: 2\n"
               "ollama:\n  base_url: http://from-yaml:11434\n  model: qwen3.6:latest\n"
               "mcp_server:\n  command: /bin/true\n"
               "tools: {}\n",
               encoding="utf-8",
           )
           monkeypatch.chdir(tmp_path)
           cfg = Config(yaml_file=str(yaml_path))
           assert cfg.ollama.base_url == "http://from-yaml:11434"

       def test_safe_06_version_1_rejected(tmp_path) -> None:
           """Phase 13 D-08: v1 schemas raise so the SAFE-06 ERROR-STYLE mapper
           can render the locked migration message."""
           yaml_path = tmp_path / "v1.yaml"
           yaml_path.write_text(
               "version: 1\n"
               "ollama:\n  base_url: http://x:11434\n  model: m\n"
               "mcp_server:\n  command: /bin/true\n"
               "tools: {}\n",
               encoding="utf-8",
           )
           import pytest
           from pydantic import ValidationError
           with pytest.raises(ValidationError) as exc_info:
               Config(yaml_file=str(yaml_path))
           # Validator message phrasing must enable the mapper at
           # cli.py:_emit_operator_error_for_validation to match.
           assert "not supported by this build" in str(exc_info.value)
           assert "expected 2" in str(exc_info.value)

       def test_safe_06_version_2_accepted(tmp_path) -> None:
           yaml_path = tmp_path / "v2.yaml"
           yaml_path.write_text(
               "version: 2\n"
               "ollama:\n  base_url: http://x:11434\n  model: m\n"
               "mcp_server:\n  command: /bin/true\n"
               "tools: {}\n",
               encoding="utf-8",
           )
           cfg = Config(yaml_file=str(yaml_path))
           assert cfg.version == 2
       ```

    9. **Flip the Plan-13-01 xfail test:** in `tests/unit/test_cli_errors.py`, the `test_safe_02_cwd_autodiscovery_picks_up_local_config` test (added by Plan 13-01 as `xfail`) — remove the xfail marker. It should now pass.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_config.py tests/unit/test_cli_errors.py -v -k "safe_05 or safe_06 or safe_02" 2>&amp;1 | tail -40</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "_BareNameNestedEnvSource" src/mcp_test_framework/config.py` returns ZERO matches.
    - `grep -n "_alias_env_names\|_maybe_json_decode" src/mcp_test_framework/config.py` returns ZERO matches.
    - `grep -n "from dotenv import" src/mcp_test_framework/config.py` returns ZERO matches.
    - `grep -n "from pydantic.fields import FieldInfo" src/mcp_test_framework/config.py` returns ZERO matches.
    - `grep -n "env_file" src/mcp_test_framework/config.py` returns ZERO matches.
    - `grep -nE "if v != 2" src/mcp_test_framework/config.py` returns one match (the validator).
    - `grep -nE "version: int = 2" src/mcp_test_framework/config.py` returns one match.
    - `grep -n "init_settings.init_kwargs" src/mcp_test_framework/config.py` returns at least one match in `settings_customise_sources`.
    - `grep -nE "env_settings|dotenv_settings" src/mcp_test_framework/config.py` returns matches ONLY in `settings_customise_sources`'s parameter list (where pydantic-settings forces us to accept them). The returned tuple does NOT contain them.
    - `uv run pytest tests/unit/test_config.py::test_safe_05_env_var_does_not_override_yaml tests/unit/test_config.py::test_safe_05_dotenv_file_in_cwd_has_no_effect tests/unit/test_config.py::test_safe_06_version_1_rejected tests/unit/test_config.py::test_safe_06_version_2_accepted -x` exits 0.
    - `uv run pytest tests/unit/test_cli_errors.py::test_safe_02_cwd_autodiscovery_picks_up_local_config -x` exits 0 (xfail removed; test now passes for real).
    - `uv run python -c "from mcp_test_framework.config import Config; print(Config(yaml_file='/nonexistent').version)"` prints `2` (default, since the YamlSource skips a non-existent path).
  </acceptance_criteria>
  <done>
    config.py reduces to imports + Config class with the new model_config / validator / sources. The three deleted helpers and the bare-name source class are gone. SAFE-05 and SAFE-06 regression tests pass. The Plan 13-01 xfail test for cwd autodiscovery now passes for real.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rewrite the SAFE-06 mapping in _emit_operator_error_for_validation</name>
  <files>src/mcp_test_framework/cli.py, tests/unit/test_error_style.py, tests/unit/test_cli_errors.py</files>
  <read_first>
    - src/mcp_test_framework/cli.py (lines 97-175 — the `_emit_operator_error_for_validation` function and especially the version-mismatch branch at lines 129-143)
    - docs/ERROR-STYLE.md (lines 57-73 — the LOCKED SAFE-06 reference message; copy verbatim)
    - tests/unit/test_error_style.py (the doc-pin regression pattern at lines 37-42; you will add a parallel test that pins the cli.py-side wiring)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md §decisions D-08, D-10 (D-10 names the MIGRATION-v1-to-v2.md path that the message references)
  </read_first>
  <behavior>
    - When Config(yaml_file=<v1-config>) raises ValidationError for version mismatch, _emit_operator_error_for_validation routes through a branch whose output matches docs/ERROR-STYLE.md:57-73 verbatim (modulo the `<path>` substitution).
    - The output names "schema version 2 (opt-in tool selection)" and "version 1 (opt-out)" and references "docs/MIGRATION-v1-to-v2.md" and ends with the locked `next:` line.
    - The output continues to exit with code 2.
  </behavior>
  <action>
    Inside `cli.py`'s `_emit_operator_error_for_validation` (lines 97-175 currently), locate the version-mismatch branch (currently lines 129-143). The trigger condition `loc == "version" and "not supported by this build" in msg` stays unchanged. Replace the `_emit_operator_error(...)` call body with the LOCKED SAFE-06 wording from `docs/ERROR-STYLE.md:57-73`:

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

    Critical wording notes:
    - The lead is `config file uses an older format: <source>` (the source is the path passed via `Config(yaml_file=...)` — Plan 13-02 Task 1 already wires `source_label` to the resolved path in `_load_config`).
    - Body uses `--` (two hyphens) not `—` (em-dash) — matches ERROR-STYLE.md verbatim.
    - The `next_step` arg combined with `_emit_operator_error`'s line `parts.extend(["", f"next: {next_step}"])` produces the literal `next: run ...` line that the regression test pins.

    Add two regression tests to lock the wiring:

    Test 1 — append to `tests/unit/test_error_style.py` (after the existing `test_error_style_contains_safe_06_*` tests):

    ```python
    def test_error_style_safe_06_body_matches_cli_wiring() -> None:
        """Phase 13 D-08: cli.py's version-mismatch branch must echo the LOCKED
        SAFE-06 body. This test reads cli.py source and pins the verbatim
        substrings so the wording cannot drift away from docs/ERROR-STYLE.md."""
        import pathlib
        cli_text = (
            pathlib.Path(__file__).resolve().parents[2]
            / "src" / "mcp_test_framework" / "cli.py"
        ).read_text("utf-8")
        # These substrings come from docs/ERROR-STYLE.md:57-73 verbatim.
        assert "schema version 2 (opt-in" in cli_text
        assert "your config is version 1 (opt-out)" in cli_text
        assert "in v1 a tool with no entry runs by default, in v2 it skips" in cli_text
        assert "docs/MIGRATION-v1-to-v2.md" in cli_text
        assert "config-init -o config.yaml.new" in cli_text
    ```

    Test 2 — append to `tests/unit/test_cli_errors.py`:

    ```python
    def test_safe_06_v1_config_emits_locked_migration_message(
        tmp_path, monkeypatch
    ) -> None:
        """Phase 13 SAFE-06: loading a v1 config exits 2 with the LOCKED
        ERROR-STYLE message body (docs/ERROR-STYLE.md:57-73)."""
        cfg = tmp_path / "old.yaml"
        cfg.write_text(
            "version: 1\n"
            "ollama:\n  base_url: http://x:11434\n  model: m\n"
            "mcp_server:\n  command: /bin/true\n"
            "tools: {}\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(app, ["run", "--config", str(cfg)])
        assert result.exit_code == 2
        assert "config file uses an older format:" in result.stderr
        assert "schema version 2 (opt-in" in result.stderr
        assert "docs/MIGRATION-v1-to-v2.md" in result.stderr
        assert "config-init -o config.yaml.new" in result.stderr
    ```
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_error_style.py tests/unit/test_cli_errors.py -v -k "safe_06 or error_style" 2>&amp;1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "schema version 2 (opt-in" src/mcp_test_framework/cli.py` returns one match.
    - `grep -n "your config is version 1 (opt-out)" src/mcp_test_framework/cli.py` returns one match.
    - `grep -n "docs/MIGRATION-v1-to-v2.md" src/mcp_test_framework/cli.py` returns one match.
    - `grep -n "config file uses an older format:" src/mcp_test_framework/cli.py` returns one match.
    - `grep -n "config-init -o config.yaml.new" src/mcp_test_framework/cli.py` returns at least one match (the next_step line).
    - The OLD substring `"config file uses an unsupported schema version"` from cli.py:132 is GONE: `grep -n "unsupported schema version" src/mcp_test_framework/cli.py` returns ZERO matches.
    - `uv run pytest tests/unit/test_error_style.py::test_error_style_safe_06_body_matches_cli_wiring tests/unit/test_cli_errors.py::test_safe_06_v1_config_emits_locked_migration_message -x` exits 0.
    - Manual: with a v1 YAML and `--config v1.yaml`, stderr contains the literal verbatim block from ERROR-STYLE.md:57-73 (modulo the `<path>` substitution).
  </acceptance_criteria>
  <done>
    The version-mismatch branch matches the LOCKED SAFE-06 message verbatim; two regression tests prevent wording drift; existing CLI error tests still pass. A future v1 operator running against this build gets the migration UX the spec promises.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| YAML file ← Config() | YAML content is operator-controlled but loaded via `yaml.safe_load` (preserved via pydantic-settings' YamlConfigSettingsSource) |
| Operator shell → process env | Env vars previously influenced Config values; this plan severs that route |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-13-02-01 | Tampering / config injection via env vars | `OLLAMA_BASE_URL`, `MCP_SERVER_COMMAND`, etc. — operator or shell-inherited env values silently overriding YAML | mitigate | This plan IS the mitigation: deleting `_BareNameNestedEnvSource`, `env_settings`, `dotenv_settings` from the source pipeline. The test `test_safe_05_env_var_does_not_override_yaml` is the regression guard. The CIA property restored: an operator's YAML is the only thing that determines what gets called. |
| T-13-02-02 | Tampering via shadowed `.env` files | Stray `.env` in cwd setting `MCP_SERVER_COMMAND` to an attacker-controlled binary | mitigate | Closed by removing `env_file` from `model_config`. Regression: `test_safe_05_dotenv_file_in_cwd_has_no_effect`. |
| T-13-02-03 | Deserialization (YAML) | `YamlConfigSettingsSource` loads the operator-supplied path via `yaml.safe_load` (pydantic-settings default) | accept | `yaml.safe_load` is the existing project pattern (per `<security_threat_model>` directive). No untrusted-YAML threat model change. |
| T-13-02-04 | Information disclosure | The SAFE-06 error echoes the YAML path back to stderr | accept | Operator-controlled path in a single-operator CLI; same disclosure surface as Plan 13-01 SAFE-03/04. ERROR-STYLE.md governs the wording. |
| T-13-02-05 | Repudiation | Removing env-overlay changes audit-relevant precedence | accept | This is the intended behavioral change. Documented in `docs/MIGRATION-v1-to-v2.md` (Plan 13-05); the version validator's refuse-on-load makes the change loud, not silent. |
| T-13-02-06 | DoS via Config recursion | Plan removes a custom settings source; the simpler pipeline reduces attack surface | n/a | No new threat; net reduction in code paths. |

No `high` severity threats. The plan is a net security improvement (closes env-overlay and dotenv-shadow attack classes).
</threat_model>

<verification>
1. SAFE-05 env-overlay drop confirmed: env vars do not change Config values.
2. SAFE-05 dotenv drop confirmed: a `.env` in cwd does not change Config values.
3. SAFE-06 v1 rejection confirmed: a v1 config produces the LOCKED ERROR-STYLE message + exit 2.
4. SAFE-06 v2 acceptance confirmed: a v2 config loads cleanly.
5. Wave-2 parallel-safety: this plan does NOT touch any file modified by Plan 13-03 (which touches `tests/conftest.py` and `src/mcp_test_framework/_reporter.py`). Confirmed by `files_modified` overlap = ∅.
6. The xfail test added by Plan 13-01 (`test_safe_02_cwd_autodiscovery_picks_up_local_config`) flips to a real pass — proves the end-to-end autodiscovery → Config(yaml_file=...) → YAML load chain works.
</verification>

<success_criteria>
- All `must_haves.truths` verifiable in CI: env-var-no-effect, .env-no-effect, v1-rejection, v2-acceptance, Config(yaml_file=...)-loads, no `dotenv` import, no `_BareNameNestedEnvSource`.
- SAFE-06 LOCKED message body present verbatim in `cli.py` and pinned by `tests/unit/test_error_style.py::test_error_style_safe_06_body_matches_cli_wiring`.
- The system no longer has the "env beats YAML" or ".env beats --config" bug classes (memory items `project_dotenv_silently_beats_config.md` and `project_mcptf_config_file_silent_fail.md` resolved).
</success_criteria>

<output>
After completion, create `.planning/phases/13-config-safety-opt-in-tool-selection/13-02-SUMMARY.md`. Include:
- Final shape of `settings_customise_sources` (3-line tuple).
- Final shape of `model_config` (frozen + extra="forbid" only).
- Grep gates passing (the 8 enumerated in acceptance_criteria).
- Forward ref to Plan 13-04: `TargetConfig` import and `target:` field still here, deleted by 13-04.
- Note: Plan 13-05 references this plan when adding the migration doc regression test (the doc must mention "version: 2" — which Plan 13-02 has now made the only accepted value).
</output>
