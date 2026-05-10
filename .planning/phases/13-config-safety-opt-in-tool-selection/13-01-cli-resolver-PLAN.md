---
phase: 13-config-safety-opt-in-tool-selection
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/mcp_test_framework/cli.py
  - tests/unit/test_cli_errors.py
  - tests/unit/test_config_init.py
autonomous: true
requirements: [SAFE-02, SAFE-03, SAFE-04, SAFE-06]
must_haves:
  truths:
    - "An operator running `mcp-test-framework run` from a directory with NO config.yaml, NO --config, NO MCPTF_CONFIG_FILE sees the locked SAFE-03 ERROR-STYLE message and exits 2."
    - "An operator running with `--config /missing/path` sees an exit-2 error mentioning --config."
    - "An operator running with `MCPTF_CONFIG_FILE=/missing/path` set sees an exit-2 error mentioning MCPTF_CONFIG_FILE (parity with --config)."
    - "An operator running with a valid ./config.yaml present (no flag, no env var) auto-discovers and loads it."
    - "_load_config passes the resolved path to Config() as a keyword argument; os.environ[\"MCPTF_CONFIG_FILE\"] is never mutated as an IPC channel."
    - "`config-init` emits `version: 2` in the scaffold body (not `version: 1`)."
  artifacts:
    - path: "src/mcp_test_framework/cli.py"
      provides: "Full _load_config resolver with --config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud precedence; scaffold emits version: 2"
      contains: "version: 2"
    - path: "tests/unit/test_cli_errors.py"
      provides: "Regression tests for SAFE-02 autodiscovery, SAFE-03 no-config fail-loud, SAFE-04 MCPTF_CONFIG_FILE typo parity"
  key_links:
    - from: "src/mcp_test_framework/cli.py:_load_config"
      to: "src/mcp_test_framework/config.py:Config()"
      via: "Config(yaml_file=resolved_path) kwarg"
      pattern: "Config\\(yaml_file="
    - from: "src/mcp_test_framework/cli.py:_load_config"
      to: "docs/ERROR-STYLE.md SAFE-03 reference message"
      via: "_emit_operator_error verbatim copy"
      pattern: "the framework refuses to run without a config file"
---

<objective>
Promote `_load_config` (`src/mcp_test_framework/cli.py:178-211`) into the full Phase 13 resolver so config discovery is mandatory, unambiguous, and fails loud when no config is reachable. The resolver becomes the single seam that passes a resolved path to `Config()` as an explicit `yaml_file` kwarg — eliminating the brittle `os.environ["MCPTF_CONFIG_FILE"] = str(path)` IPC pattern that motivated the SAFE-04 bug report. Also flip the literal `version: 1` → `version: 2` inside the `config-init` scaffold output and the surrounding comment/docstrings so a freshly-generated config loads cleanly under the v2 validator that Plan 13-02 will install.

Purpose: SAFE-02 (cwd autodiscovery), SAFE-03 (no-config refuse-on-load with the LOCKED ERROR-STYLE message), SAFE-04 (typo'd MCPTF_CONFIG_FILE parity with --config typos), and the `config-init`-side of SAFE-06 (the scaffold the migration error tells operators to regenerate emits v2).

Output: A `cli.py` whose `_load_config` raises `typer.Exit(2)` at the first failure (--config missing, MCPTF_CONFIG_FILE missing, no autodiscovery hit, OR none of the three set), passes the resolved path as `Config(yaml_file=path)`, and whose `config-init` scaffold body declares `version: 2`. Regression tests in `tests/unit/test_cli_errors.py` lock the three error sites and the autodiscovery behavior.
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
@docs/ERROR-STYLE.md
@src/mcp_test_framework/cli.py
@tests/unit/test_cli_errors.py
@tests/unit/test_error_style.py
</context>

<truths>
**Locked decisions implemented by this plan (quoted from 13-CONTEXT.md):**

- **D-01:** "Config resolution precedence is `--config PATH` > `MCPTF_CONFIG_FILE` > `./config.yaml` autodiscovery > fail-loud. First miss raises `typer.Exit(2)` with the ERROR-STYLE message from Phase 12 D-17. Resolution happens once, in `_load_config`, before `Config()` is constructed."
- **D-02:** "Autodiscovery probes only `./config.yaml` in `Path.cwd()`. No walk-up, no alternate filenames."
- **D-03:** "Single resolver in `cli.py` / `_load_config`. ... `Config(...)` receives the resolved path as an explicit `yaml_file` kwarg via `init_settings` — no env-var trick. `settings_customise_sources` reads the path from kwargs, not from `os.environ`. Eliminates the brittle env-var-as-IPC pattern that motivated the SAFE-04 bug report."
- **D-04:** "SAFE-04 falls out of D-03 for free: because `_load_config` validates the env-var path before constructing `Config`, a typo'd `MCPTF_CONFIG_FILE` and a typo'd `--config` route through the same error site with the same exit code and the same ERROR-STYLE wording (modulo 'the env var' vs 'the --config flag' in the lead sentence)."
- **D-08 (scaffold-side only — config.py validator flip belongs to Plan 13-02):** "`version: 2` is the only accepted value." The `config-init` scaffold MUST emit `version: 2`.

**SAFE-03 LOCKED message body** (copy verbatim from `docs/ERROR-STYLE.md:46-55`):
```
no config file found: ./config.yaml

the framework refuses to run without a config file because it would
otherwise call every tool the server advertises -- including any
destructive ones. you must explicitly opt in to which tools run.

next: run `mcp-test-framework config-init -o config.yaml` to generate
      a starter config, then edit it to enable the tools you want to test
```
</truths>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Promote _load_config into the full SAFE-02/03/04 resolver</name>
  <files>src/mcp_test_framework/cli.py, tests/unit/test_cli_errors.py</files>
  <read_first>
    - src/mcp_test_framework/cli.py (read in full; you are rewriting lines 178-211 and adjusting Config() call sites)
    - docs/ERROR-STYLE.md (lines 41-73 — LOCKED SAFE-03 and SAFE-06 reference messages, copy SAFE-03 verbatim; SAFE-04 reuses the same shape with the lead sentence swap)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md §decisions D-01..D-04
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md §1 (the full resolver shape diagram and the "critical change vs existing" note about stopping `os.environ[...]=str(path)`)
    - tests/unit/test_cli_errors.py (read in full to see the existing _emit_operator_error test patterns you will extend)
    - tests/unit/test_error_style.py (lines 25-66 — banned-token / snippet-correctness regression test pattern)
  </read_first>
  <behavior>
    - Resolver returns a Config when --config points to a real file: pass-through to Config(yaml_file=<that path>).
    - Resolver returns a Config when MCPTF_CONFIG_FILE points to a real file AND --config is None.
    - Resolver returns a Config when neither --config nor MCPTF_CONFIG_FILE is set AND ./config.yaml exists in cwd: pass cwd_config to Config(yaml_file=<cwd/config.yaml>).
    - Resolver raises typer.Exit(2) with the verbatim SAFE-03 message body when none of the three is reachable.
    - Resolver raises typer.Exit(2) with a SAFE-04-shaped message ("config file not found via MCPTF_CONFIG_FILE: <path>") when MCPTF_CONFIG_FILE is set to a non-existent path.
    - Resolver raises typer.Exit(2) with the existing SAFE-04-shaped message ("config file not found: <path>" / "the path passed to --config does not exist or is not a file.") when --config points to a non-existent path. This part already exists at cli.py:186-198 — preserve verbatim.
    - Resolver MUST NOT mutate os.environ at any point. The existing `os.environ["MCPTF_CONFIG_FILE"] = str(path)` lines at 199, 203, 206 are deleted.
    - Config() is invoked exactly once per resolver call, as `Config(yaml_file=str(resolved_path))`. The trailing `Config()` no-kwarg fallback at line 208-211 is deleted (any unconfigured run goes through the SAFE-03 raise above it).
  </behavior>
  <action>
    Replace the body of `_load_config(path: Path | None) -> Config` (currently `src/mcp_test_framework/cli.py:178-211`) with the four-branch resolver below. Keep the function signature and docstring style. Imports already include `os`, `typer`, `Config`, `Path`, `ValidationError`; no new imports needed except confirming `Path` is in scope.

    The new body (paste this shape; adjust whitespace to match existing 4-space indent):

    ```python
    def _load_config(path: Path | None) -> Config:
        """Resolve the YAML config path and load Config().

        Precedence (Phase 13 D-01):
            --config PATH > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud.

        The resolved path is passed to Config() as a `yaml_file` kwarg
        (Phase 13 D-03); settings_customise_sources reads it from
        init_settings.init_kwargs -- not from os.environ. ValidationError
        is mapped through _emit_operator_error_for_validation per
        docs/ERROR-STYLE.md (PERSONA-03).
        """
        resolved: Path | None = None
        source_label: str = ""  # "--config" / "MCPTF_CONFIG_FILE" / "./config.yaml"

        # Branch 1: --config wins.
        if path is not None:
            if not path.is_file():
                _emit_operator_error(
                    summary=f"config file not found: {path}",
                    detail=[
                        "the path passed to --config does not exist or is not a file.",
                    ],
                    next_step=(
                        "check the path or run "
                        "`mcp-test-framework config-init -o config.yaml` "
                        "to generate a starter config"
                    ),
                )
            resolved = path
            source_label = str(path)
        else:
            # Branch 2: MCPTF_CONFIG_FILE.
            env_path_str = os.environ.get("MCPTF_CONFIG_FILE")
            if env_path_str:
                env_path = Path(env_path_str)
                if not env_path.is_file():
                    _emit_operator_error(
                        summary=f"config file not found via MCPTF_CONFIG_FILE: {env_path}",
                        detail=[
                            "the path in MCPTF_CONFIG_FILE does not exist or is not a file.",
                        ],
                        next_step=(
                            "check the path or unset MCPTF_CONFIG_FILE and run "
                            "`mcp-test-framework config-init -o config.yaml` "
                            "to generate a starter config"
                        ),
                    )
                resolved = env_path
                source_label = str(env_path)
            else:
                # Branch 3: ./config.yaml autodiscovery.
                cwd_config = Path.cwd() / "config.yaml"
                if cwd_config.is_file():
                    resolved = cwd_config
                    source_label = str(cwd_config)

        # Branch 4: nothing found -> SAFE-03 fail-loud.
        if resolved is None:
            _emit_operator_error(
                summary="no config file found: ./config.yaml",
                detail=[
                    "the framework refuses to run without a config file because it would",
                    "otherwise call every tool the server advertises -- including any",
                    "destructive ones. you must explicitly opt in to which tools run.",
                ],
                next_step=(
                    "run `mcp-test-framework config-init -o config.yaml` to generate "
                    "a starter config, then edit it to enable the tools you want to test"
                ),
            )

        # Load with the resolved path as an explicit kwarg.
        try:
            return Config(yaml_file=str(resolved))
        except ValidationError as exc:
            _emit_operator_error_for_validation(exc, source=source_label)
    ```

    Critical notes:
    1. DO NOT prefix any `_emit_operator_error(...)` call with `raise` — see `_emit_operator_error`'s docstring at `cli.py:75-77`. It already raises internally and is typed `-> typing.NoReturn`.
    2. DO NOT touch `_emit_operator_error_for_validation` in this task — Plan 13-02 owns updating its `summary`/`detail` to match the new locked SAFE-06 text. For this plan the existing "config file uses an unsupported schema version" mapping stays in place.
    3. The SAFE-03 detail block is THREE lines of body text (lines 50-52 of ERROR-STYLE.md). They're written as a Python list of three strings — `_emit_operator_error` already inserts the blank-line separator before the `next:` line via `parts.extend(["", f"next: {next_step}"])`.
    4. The SAFE-04 lead sentence for the env-var branch is exactly: `"config file not found via MCPTF_CONFIG_FILE: {env_path}"`. The detail body says "the path in MCPTF_CONFIG_FILE does not exist or is not a file." (parallel structure to the existing --config branch).

    After modifying `_load_config`, add these regression tests to `tests/unit/test_cli_errors.py` (append; follow the existing import style and CliRunner usage in that file):

    ```python
    def test_safe_03_no_config_found_fails_loud_with_locked_message(
        tmp_path, monkeypatch
    ) -> None:
        """Phase 13 SAFE-03: cwd has no config.yaml, no env var, no --config."""
        monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
        monkeypatch.chdir(tmp_path)
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(app, ["run"])
        assert result.exit_code == 2
        # Verbatim SAFE-03 lead and SAFE-03 detail (docs/ERROR-STYLE.md:46-55).
        assert "no config file found: ./config.yaml" in result.stderr
        assert "the framework refuses to run without a config file" in result.stderr
        assert "destructive ones. you must explicitly opt in" in result.stderr
        assert "config-init -o config.yaml" in result.stderr

    def test_safe_04_mcptf_config_file_typo_exits_2(tmp_path, monkeypatch) -> None:
        """Phase 13 SAFE-04: typo'd MCPTF_CONFIG_FILE mirrors --config typo."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("MCPTF_CONFIG_FILE", str(tmp_path / "missing.yaml"))
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(app, ["run"])
        assert result.exit_code == 2
        assert "MCPTF_CONFIG_FILE" in result.stderr
        assert "does not exist" in result.stderr

    def test_safe_02_cwd_autodiscovery_picks_up_local_config(
        tmp_path, monkeypatch
    ) -> None:
        """Phase 13 SAFE-02: ./config.yaml is auto-discovered when no flag/env."""
        # Write a minimal v2 config (Plan 13-02 will accept this).
        (tmp_path / "config.yaml").write_text(
            "version: 2\n"
            "ollama:\n  base_url: http://127.0.0.1:11434\n  model: qwen3.6:latest\n"
            "mcp_server:\n  command: /bin/true\n  args: []\n"
            "tools: {}\n",
            encoding="utf-8",
        )
        monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
        monkeypatch.chdir(tmp_path)
        # We assert resolver discovery via the loader directly (no pytest spawn).
        from mcp_test_framework.cli import _load_config
        cfg = _load_config(None)  # Plan 13-02 makes version=2 valid.
        assert cfg is not None
    ```

    Note: `test_safe_02_cwd_autodiscovery_picks_up_local_config` will FAIL until Plan 13-02 lands the v2 validator + the yaml_file kwarg reading in `settings_customise_sources`. Mark it `@pytest.mark.xfail(reason="depends on Plan 13-02: Config(yaml_file=...) wiring + version=2 validator")` OR add it but skip until 13-02 completes — choose xfail so the test surfaces automatically once 13-02 lands. The SAFE-03 and SAFE-04 tests pass on this plan alone.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_cli_errors.py -v -k "safe_03 or safe_04" 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "os.environ\[\"MCPTF_CONFIG_FILE\"\] = " src/mcp_test_framework/cli.py` returns ZERO matches (the IPC pattern is gone).
    - `grep -n "Config(yaml_file=" src/mcp_test_framework/cli.py` returns at least one match in `_load_config`.
    - `grep -n "the framework refuses to run without a config file" src/mcp_test_framework/cli.py` returns one match (the SAFE-03 detail body).
    - `grep -n "config file not found via MCPTF_CONFIG_FILE" src/mcp_test_framework/cli.py` returns one match.
    - `grep -n "Path.cwd() / \"config.yaml\"" src/mcp_test_framework/cli.py` returns one match (the autodiscovery branch).
    - `uv run pytest tests/unit/test_cli_errors.py::test_safe_03_no_config_found_fails_loud_with_locked_message -x` exits 0.
    - `uv run pytest tests/unit/test_cli_errors.py::test_safe_04_mcptf_config_file_typo_exits_2 -x` exits 0.
    - `grep -nP "^\s*raise\s+_emit_operator_error" src/mcp_test_framework/cli.py` returns ZERO matches (rule from cli.py:75-77 — callers must not prefix with `raise`).
  </acceptance_criteria>
  <done>
    The four-branch resolver is in place; `os.environ[...]=...` IPC writes are gone from `_load_config`; SAFE-03 and SAFE-04 regression tests pass; the SAFE-02 autodiscovery test is xfail with a clear "blocked on Plan 13-02" reason; `_emit_operator_error_for_validation` is unchanged (Plan 13-02 owns the SAFE-06 wording flip).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Flip `version: 1` -> `version: 2` literal in config-init scaffold + docstrings</name>
  <files>src/mcp_test_framework/cli.py, tests/unit/test_config_init.py</files>
  <read_first>
    - src/mcp_test_framework/cli.py (lines 425-450 for `config-init` docstring, lines 730-799 for `_format_tools_yaml_scaffold`)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md §decisions D-08 ("`version: 2` is the only accepted value")
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md §2 (the literal flip — lines 771-772 of cli.py is the surgery point)
    - tests/unit/test_config_init.py (read in full to see existing scaffold-output assertions you will update)
  </read_first>
  <behavior>
    - `mcp-test-framework config-init -o config.yaml` writes a file whose body contains the line `version: 2` (not `version: 1`).
    - The comment immediately above the version line reads "Schema version. This release accepts version 2." (not "version 1").
    - Existing tests in `tests/unit/test_config_init.py` that assert `"version: 1"` are updated to assert `"version: 2"`.
    - All non-version lines in the scaffold (ollama, mcp_server, judge_timeout_seconds, tools blocks) are unchanged byte-for-byte.
  </behavior>
  <action>
    Make three edits in `src/mcp_test_framework/cli.py`:

    1. Inside `_format_tools_yaml_scaffold` (currently lines 770-772):

       Replace EXACTLY:
       ```python
               "# Schema version. This release accepts version 1.\n"
               "version: 1\n"
       ```
       With EXACTLY:
       ```python
               "# Schema version. This release accepts version 2.\n"
               "version: 2\n"
       ```

    2. In the `config-init` Typer command docstring around line 429 (look for the substring `version: 1`):

       Replace EXACTLY any occurrence of `'version: 1'` inside the docstring with `'version: 2'`. Use grep first: `grep -n "version: 1" src/mcp_test_framework/cli.py` to confirm there are exactly three remaining hits (the scaffold body line you just changed, the comment line above it, and the docstring(s) at lines ~429 and ~739) — your replacements should leave ZERO matches for `version: 1` in cli.py after this task.

    3. Around line 739 (inside the `_format_tools_yaml_scaffold` docstring), update the comment `- `version: 1` literal (this release's accepted version).` to `- `version: 2` literal (this release's accepted version).`.

    Then update `tests/unit/test_config_init.py`: locate every assertion that searches for the string `"version: 1"` (use grep against the file first), and change to `"version: 2"`. Add one new assertion explicitly:

    ```python
    def test_config_init_scaffold_emits_version_2() -> None:
        """Phase 13 SAFE-06 / D-08: the regenerated scaffold targets v2."""
        # Use whichever helper the existing tests use to invoke config-init
        # against a tmp dir; assert "version: 2\n" appears in the output file
        # and "version: 1\n" does NOT.
        ...  # mirror existing test pattern in this file
    ```

    Confirm in the final state that `grep -c "^\s*\"version: 1\\\\n\"\|version: 1" src/mcp_test_framework/cli.py | grep -v "^#"` returns 0 (no remaining v1 literal). The `_validate_version` flip in `config.py` belongs to Plan 13-02 — DO NOT touch `config.py` in this plan.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_config_init.py -v 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "version: 1" src/mcp_test_framework/cli.py` returns ZERO matches.
    - `grep -n "version: 2" src/mcp_test_framework/cli.py` returns at least TWO matches (the comment line + the literal scaffold line in `_format_tools_yaml_scaffold`).
    - `grep -n "This release accepts version 2" src/mcp_test_framework/cli.py` returns one match.
    - `uv run pytest tests/unit/test_config_init.py -v` exits 0 (all updated tests pass).
    - Running `uv run mcp-test-framework config-init -o /tmp/test-v2.yaml` (or PowerShell equivalent — write to a tmp path) and `grep "version:" /tmp/test-v2.yaml` shows `version: 2`.
  </acceptance_criteria>
  <done>
    Every literal `version: 1` in cli.py is gone; the scaffold emits `version: 2`; test_config_init.py assertions match the new literal; one new explicit assertion documents the SAFE-06 / D-08 intent. The config-init command remains independently runnable; only the version literal has changed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator shell → CLI | Untrusted strings reach the resolver via `--config PATH` (CLI arg) and `MCPTF_CONFIG_FILE` (env var) |
| Filesystem ← CLI | Resolver calls `Path.is_file()` and `Path.cwd()` against operator-supplied paths |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-13-01-01 | Tampering / Path traversal | `_load_config` resolver — operator-supplied `--config PATH` and `MCPTF_CONFIG_FILE` env var | accept | These paths are operator-controlled inputs in a local CLI process; the operator already has the shell's full authority. `Path(env_path_str)` does not canonicalize or follow symlinks beyond `is_file()`; `pydantic-settings`' `YamlConfigSettingsSource` reads the file via `yaml.safe_load`. No privilege boundary is crossed. No mitigation beyond existing `is_file()` guard. |
| T-13-01-02 | Information disclosure | Error messages echo the full resolved path back to stderr | mitigate | ERROR-STYLE.md governs the exact wording; the leaked information (the path the operator just typed) is not sensitive in a single-operator CLI context. Mitigation = adhere to ERROR-STYLE.md's locked text and do not append cwd / username / stack traces. Verified by the `test_safe_03_*` and `test_safe_04_*` regression tests that pin the exact substrings allowed in stderr. |
| T-13-01-03 | Denial of service | Operator passes a /dev/zero or fifo path to --config | accept | `is_file()` returns False for fifos and special devices on POSIX; on Windows, the same. `yaml.safe_load` has well-known DoS via deeply nested anchors, but pydantic-settings limits this and the operator is already trusted. No mitigation in this plan; treat as accepted risk consistent with v1.1 baseline. |
| T-13-01-04 | Repudiation / Elevation | os.environ mutation as a side channel between CLI layers (the v1.1 behavior we are removing) | mitigate | This plan DELETES the `os.environ["MCPTF_CONFIG_FILE"] = str(path)` writes at cli.py:199/203/206. Replacement: pass `yaml_file` as an explicit kwarg to `Config(...)`. Acceptance criterion `grep -n "os.environ\[\"MCPTF_CONFIG_FILE\"\] = " src/mcp_test_framework/cli.py` returns 0 enforces the mitigation. |
| T-13-01-05 | Deserialization (YAML) | Resolver hands `yaml_file=...` to `YamlConfigSettingsSource` which uses `yaml.safe_load` | accept | `yaml.safe_load` is the existing project pattern (preserved per `<security_threat_model>` directive). No code in this plan changes the loader; the resolver only chooses which path to pass. |

No `high` severity threats; nothing blocks plan execution.
</threat_model>

<verification>
1. Manual SAFE-03 walk-through: `cd /tmp/empty-dir && unset MCPTF_CONFIG_FILE && uv run mcp-test-framework run` (or PowerShell equivalent) — stderr matches the locked ERROR-STYLE.md SAFE-03 block; exit code 2.
2. Manual SAFE-04 walk-through: `MCPTF_CONFIG_FILE=/nonexistent/path uv run mcp-test-framework run` — stderr names MCPTF_CONFIG_FILE; exit code 2.
3. Manual --config typo walk-through: `uv run mcp-test-framework run --config /nonexistent/path` — stderr says `config file not found: /nonexistent/path` and names `--config`; exit code 2.
4. Manual config-init scaffold check: `uv run mcp-test-framework config-init -o /tmp/v2-test.yaml && grep "version:" /tmp/v2-test.yaml` shows `version: 2`.
5. Regression tests: `uv run pytest tests/unit/test_cli_errors.py tests/unit/test_config_init.py -v` exits 0.
6. Smoke: `uv run mcp-test-framework --help` still works (the resolver does not run for help-rendering); exit 0.
</verification>

<success_criteria>
- Operator running `mcp-test-framework run` with no config anywhere sees the locked SAFE-03 message and exit 2 (truth 1 of must_haves).
- Operator with typo'd MCPTF_CONFIG_FILE sees a parity-shaped error (truth 3).
- Operator with valid ./config.yaml in cwd has it auto-discovered after Plan 13-02 lands (truth 4 — xfail test flips green when 13-02 ships).
- `os.environ[...]` is never written by `_load_config` (truth 5; grep-enforced).
- `config-init` scaffold emits `version: 2` (truth 6).
- The "scaffold the SAFE-06 message points at" is correct from the moment Plan 13-02 lands the validator flip — the migration UX is internally consistent.
</success_criteria>

<output>
After completion, create `.planning/phases/13-config-safety-opt-in-tool-selection/13-01-SUMMARY.md` per the template at `$HOME/.claude/get-shit-done/templates/summary.md`. Include:
- The four-branch resolver shape (one diagram or pseudocode block).
- The two grep gates: `os.environ\[\"MCPTF_CONFIG_FILE\"\] = ` returns 0 and `Config(yaml_file=` returns ≥1.
- A note that the `test_safe_02_cwd_autodiscovery_picks_up_local_config` test is `xfail` pending Plan 13-02 — and that 13-02's done-criteria includes flipping it to a real pass.
- Forward refs to: Plan 13-02 (config.py settings_customise_sources reads `init_kwargs.get("yaml_file")` + version validator flip), Plan 13-05 (MIGRATION-v1-to-v2.md regression test that asserts the scaffold's "version: 2" appears in the migration doc's step-by-step).
</output>
