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
  - tests/unit/test_error_style.py
autonomous: true
requirements: [SAFE-02, SAFE-03, SAFE-04, SAFE-06]
must_haves:
  truths:
    - "D-01: An operator running `mcp-test-framework run` from a directory with NO config.yaml, NO --config, NO MCPTF_CONFIG_FILE sees the locked SAFE-03 ERROR-STYLE message and exits 2."
    - "D-01: An operator running with `--config /missing/path` sees an exit-2 error mentioning --config."
    - "D-04: An operator running with `MCPTF_CONFIG_FILE=/missing/path` set sees an exit-2 error mentioning MCPTF_CONFIG_FILE (parity with --config)."
    - "D-02: An operator running with a valid ./config.yaml present (no flag, no env var) auto-discovers and loads it."
    - "D-03: _load_config passes the resolved path to Config() as a keyword argument; os.environ[\"MCPTF_CONFIG_FILE\"] is never mutated as an IPC channel."
    - "D-08 (scaffold side): `config-init` emits `version: 2` in the scaffold body (not `version: 1`)."
    - "D-03: An operator running from an unconfigured directory CAN run `config-init` (with --command/--arg overrides) and `list-tools` (with --command override); only `run` fails loud under SAFE-03. The SAFE-03 message's recovery command does not brick itself."
    - "D-01: The SAFE-03 message body in cli.py matches docs/ERROR-STYLE.md:46-55 verbatim (pinned by a source-text regression test, not just CliRunner substring assertions)."
    - "D-04: The SAFE-04 message body in cli.py (env-var lead) matches the locked shape verbatim (pinned by a source-text regression test)."
  artifacts:
    - path: "src/mcp_test_framework/cli.py"
      provides: "Full _load_config resolver with --config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud precedence; allow_missing=True bypass for config-init/list-tools; scaffold emits version: 2"
      contains: "version: 2"
    - path: "tests/unit/test_cli_errors.py"
      provides: "Regression tests for SAFE-02 autodiscovery, SAFE-03 no-config fail-loud, SAFE-04 MCPTF_CONFIG_FILE typo parity, and the config-init/list-tools allow_missing bypass"
    - path: "tests/unit/test_error_style.py"
      provides: "Source-text regression tests pinning SAFE-03 and SAFE-04 verbatim wording in cli.py"
  key_links:
    - from: "src/mcp_test_framework/cli.py:_load_config"
      to: "src/mcp_test_framework/config.py:Config()"
      via: "Config(yaml_file=resolved_path) kwarg"
      pattern: "Config\\(yaml_file="
    - from: "src/mcp_test_framework/cli.py:_load_config"
      to: "docs/ERROR-STYLE.md SAFE-03 reference message"
      via: "_emit_operator_error verbatim copy"
      pattern: "the framework refuses to run without a config file"
    - from: "src/mcp_test_framework/cli.py:config_init"
      to: "src/mcp_test_framework/cli.py:_load_config"
      via: "allow_missing=True kwarg for bootstrap-from-empty-dir"
      pattern: "_load_config\\(config, allow_missing=True\\)"
---

<objective>
Promote `_load_config` (`src/mcp_test_framework/cli.py:178-211`) into the full Phase 13 resolver so config discovery is mandatory, unambiguous, and fails loud when no config is reachable — EXCEPT for the bootstrap-from-empty-directory commands (`config-init`, `list-tools`) which must keep working in an unconfigured directory because SAFE-03's own recovery action invokes one of them. The resolver becomes the single seam that passes a resolved path to `Config()` as an explicit `yaml_file` kwarg — eliminating the brittle `os.environ["MCPTF_CONFIG_FILE"] = str(path)` IPC pattern that motivated the SAFE-04 bug report. Also flip the literal `version: 1` → `version: 2` inside the `config-init` scaffold output and the surrounding comment/docstrings so a freshly-generated config loads cleanly under the v2 validator that Plan 13-02 will install.

Purpose: SAFE-02 (cwd autodiscovery), SAFE-03 (no-config refuse-on-load with the LOCKED ERROR-STYLE message, applied ONLY to `run`), SAFE-04 (typo'd MCPTF_CONFIG_FILE parity with --config typos), and the `config-init`-side of SAFE-06 (the scaffold the migration error tells operators to regenerate emits v2).

Output: A `cli.py` whose `_load_config(path, allow_missing=False)` raises `typer.Exit(2)` at the first failure for `run` but returns `None` from the same code paths when `allow_missing=True` (for `config-init` and `list-tools`); passes the resolved path as `Config(yaml_file=path)`; whose `config-init` scaffold body declares `version: 2`; whose `config-init` and `list-tools` call sites pass `allow_missing=True` and build a default `Config()` when the resolver returns `None`. Regression tests in `tests/unit/test_cli_errors.py` lock the four error sites + the bootstrap bypass; source-text regression tests in `tests/unit/test_error_style.py` lock the SAFE-03 and SAFE-04 verbatim wording.
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

**Revision note (interactive checker iteration 1):** Without the `allow_missing` bypass, the SAFE-03 recovery message (`mcp-test-framework config-init -o config.yaml`) is bricked because `config_init` itself calls `_load_config`. The `--command`/`--arg` overrides on `config-init` (cli.py:438-440) exist *specifically* to bootstrap a fresh checkout. The bypass is therefore part of the SAFE-03 surface, not a separate concern.

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
  <name>Task 1: Promote _load_config into the SAFE-02/03/04 resolver with allow_missing bypass</name>
  <files>src/mcp_test_framework/cli.py, tests/unit/test_cli_errors.py, tests/unit/test_error_style.py</files>
  <read_first>
    - src/mcp_test_framework/cli.py (read in full; you are rewriting lines 178-211 and updating the call sites in `run` (~line 285), `list_tools` (cli.py:340), and `config_init` (cli.py:458))
    - docs/ERROR-STYLE.md (lines 41-73 — LOCKED SAFE-03 and SAFE-06 reference messages, copy SAFE-03 verbatim; SAFE-04 reuses the same shape with the lead sentence swap)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md §decisions D-01..D-04
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md §1 (the full resolver shape diagram and the "critical change vs existing" note about stopping `os.environ[...]=str(path)`)
    - tests/unit/test_cli_errors.py (read in full to see the existing _emit_operator_error test patterns you will extend)
    - tests/unit/test_error_style.py (lines 25-66 — banned-token / snippet-correctness regression test pattern; the SAFE-03 / SAFE-04 source-pin tests added here mirror Plan 13-02's `test_error_style_safe_06_body_matches_cli_wiring` shape)
  </read_first>
  <behavior>
    - Default mode (`allow_missing=False`, used by `run`):
      - Resolver returns a Config when --config points to a real file: pass-through to Config(yaml_file=<that path>).
      - Resolver returns a Config when MCPTF_CONFIG_FILE points to a real file AND --config is None.
      - Resolver returns a Config when neither --config nor MCPTF_CONFIG_FILE is set AND ./config.yaml exists in cwd.
      - Resolver raises typer.Exit(2) with the verbatim SAFE-03 message body when none of the three is reachable.
      - Resolver raises typer.Exit(2) with a SAFE-04-shaped message ("config file not found via MCPTF_CONFIG_FILE: <path>") when MCPTF_CONFIG_FILE is set to a non-existent path.
      - Resolver raises typer.Exit(2) with the existing SAFE-04-shaped message ("config file not found: <path>" / "the path passed to --config does not exist or is not a file.") when --config points to a non-existent path.
    - Bypass mode (`allow_missing=True`, used by `config-init` and `list-tools`):
      - --config / MCPTF_CONFIG_FILE pointing to a NON-existent path STILL raises typer.Exit(2) (an explicit-but-broken pointer is a typo, not a bootstrap; same as default mode).
      - --config / MCPTF_CONFIG_FILE pointing to a REAL file returns the loaded Config (same as default mode).
      - No flag, no env var, no ./config.yaml → returns `None` (caller builds a default `Config()` itself). NO SAFE-03 raise.
    - Resolver MUST NOT mutate os.environ at any point. The existing `os.environ["MCPTF_CONFIG_FILE"] = str(path)` lines at 199, 203, 206 are deleted.
    - Config() is invoked exactly once per resolver call (in the file-found branches), as `Config(yaml_file=str(resolved_path))`. The trailing `Config()` no-kwarg fallback at line 208-211 is deleted (any unconfigured `run` goes through the SAFE-03 raise above it; `config-init`/`list-tools` get `None` back and build their own default).
    - Call site `run`: `cfg = _load_config(config)` (default `allow_missing=False`). Unchanged shape; new keyword default just keeps existing semantics.
    - Call site `list_tools` (cli.py:340): `cfg = _load_config(config, allow_missing=True)`. If `cfg is None`, `cfg = Config()`. The `--command` override is not yet wired into `list-tools` in v1.1 — leave the operator-facing behavior as "uses defaults from Config() when no config found; an operator with no PATH-resolvable MCP server command will get a downstream FileNotFoundError that already maps to the operator-tone error in cli.py:351-369". Do NOT add a `--command` override to `list-tools` in this plan.
    - Call site `config_init` (cli.py:458): `cfg = _load_config(config, allow_missing=True)`. If `cfg is None`, `cfg = Config()`. The existing `model_copy(update=...)` override path at cli.py:465-473 then applies `--command`/`--arg` on top, which IS the documented bootstrap path.
  </behavior>
  <action>
    Replace the body of `_load_config(path: Path | None, *, allow_missing: bool = False) -> Config | None` (currently `src/mcp_test_framework/cli.py:178-211`) with the resolver below. The signature gains a keyword-only `allow_missing: bool = False` and the return type becomes `Config | None` (only `None` when `allow_missing=True` and no path was reachable). Keep the function name and most of the docstring style. Imports already include `os`, `typer`, `Config`, `Path`, `ValidationError`; no new imports needed.

    The new body (paste this shape; adjust whitespace to match existing 4-space indent):

    ```python
    def _load_config(path: Path | None, *, allow_missing: bool = False) -> Config | None:
        """Resolve the YAML config path and load Config().

        Precedence (Phase 13 D-01):
            --config PATH > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud.

        The resolved path is passed to Config() as a `yaml_file` kwarg
        (Phase 13 D-03); settings_customise_sources reads it from
        init_settings.init_kwargs -- not from os.environ. ValidationError
        is mapped through _emit_operator_error_for_validation per
        docs/ERROR-STYLE.md (PERSONA-03).

        Args:
            path: Value of --config (None when the operator did not pass it).
            allow_missing: When True (used by `config-init` and `list-tools`),
                the "nothing found" branch returns None instead of raising
                SAFE-03. This is the bootstrap path: SAFE-03's recovery
                command (`config-init -o config.yaml`) must itself run from
                an unconfigured directory. An explicit-but-broken --config
                or MCPTF_CONFIG_FILE STILL raises (typo, not bootstrap).
                Defaults to False; only `run` keeps the SAFE-03 surface.

        Returns:
            A Config instance, or None when allow_missing=True and no config
            source was reachable. The caller is responsible for constructing
            a default Config() in the None case.
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

        # Branch 4: nothing found.
        if resolved is None:
            if allow_missing:
                # Bootstrap path: config-init / list-tools may run from an
                # unconfigured directory. Caller constructs a default Config().
                return None
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

    After modifying `_load_config`, update the two bootstrap call sites in `cli.py`:

    **Call site 1: `list_tools` (currently `cli.py:340`):**

    Replace EXACTLY:
    ```python
        cfg = _load_config(config)
    ```
    With EXACTLY:
    ```python
        cfg = _load_config(config, allow_missing=True)
        if cfg is None:
            cfg = Config()
    ```

    Also update the `list-tools` docstring around line 320-339 to add one sentence near the end of the existing docstring (before the closing `"""`):

    ```
    From a directory with no config (no --config, no MCPTF_CONFIG_FILE, no
    ./config.yaml), `list-tools` uses framework defaults rather than failing
    loud. SAFE-03 fail-loud applies to `run` only -- `list-tools` is
    deliberately bootstrap-friendly so an operator can probe a server
    before opting tools in.
    ```

    **Call site 2: `config_init` (currently `cli.py:458`):**

    Replace EXACTLY:
    ```python
        cfg = _load_config(config)
    ```
    With EXACTLY:
    ```python
        cfg = _load_config(config, allow_missing=True)
        if cfg is None:
            cfg = Config()
    ```

    The existing `--command`/`--arg` `model_copy` override at cli.py:465-473 then naturally applies to the default Config when no config file was found — completing the bootstrap chain that SAFE-03's recovery message documents.

    **Call site 3: `run` (currently `cli.py:285` approximately — search for `_load_config(config)` inside the `run` command body):**

    Leave UNCHANGED. The default `allow_missing=False` preserves SAFE-03 fail-loud for the only command that actually executes tests.

    Now add regression tests. Append these to `tests/unit/test_cli_errors.py`:

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

    def test_config_init_works_in_empty_dir_with_command_override(
        tmp_path, monkeypatch
    ) -> None:
        """Phase 13 (revision): SAFE-03 recovery command must run from
        an unconfigured directory. Without the allow_missing bypass, the
        operator-recommended `config-init -o config.yaml` would itself
        fail SAFE-03 -- self-bricking the recovery UX."""
        monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "out.yaml"
        runner = CliRunner(mix_stderr=False)
        # `_list_tools_async` will spawn the subprocess; we use a trivially
        # successful no-discovery command path. The override flags exist
        # exactly for this case (cli.py:438-440 docstring).
        # NOTE: this test is INTEGRATION-shaped (spawns a subprocess). If
        # the test infra forbids subprocess spawn, mark with
        # @pytest.mark.skipif(sys.platform == "win32", reason="...") and/or
        # use a shell builtin that exits 0 (e.g. `cmd.exe /c exit 0` on
        # Windows). The acceptance criterion is the resolver path, not the
        # downstream discovery success -- accept either exit 0 (full
        # success) OR exit 2 with stderr NOT mentioning "no config file
        # found" (resolver passed; downstream MCP handshake may have
        # failed, which is out of scope for this test).
        result = runner.invoke(
            app,
            ["config-init", "--command", "/bin/true", "-o", str(out)],
        )
        # The critical assertion: SAFE-03 did NOT fire. If it had, exit
        # would be 2 AND stderr would name "no config file found".
        assert "no config file found: ./config.yaml" not in (result.stderr or "")

    def test_list_tools_works_in_empty_dir(tmp_path, monkeypatch) -> None:
        """Phase 13 (revision): list-tools must not SAFE-03 in an empty dir.
        Same rationale as test_config_init_works_in_empty_dir_with_command_override:
        bootstrap-friendly commands return defaults; only `run` fails loud."""
        monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
        monkeypatch.chdir(tmp_path)
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(app, ["list-tools"])
        # SAFE-03 did NOT fire. Downstream MCP handshake may fail (default
        # mcp_server.command may not be on PATH), which is acceptable --
        # what we are pinning is the resolver bypass.
        assert "no config file found: ./config.yaml" not in (result.stderr or "")

    def test_run_still_fails_loud_in_empty_dir(tmp_path, monkeypatch) -> None:
        """Phase 13 (revision): regression test pinning that `run` keeps
        SAFE-03 fail-loud even after the allow_missing bypass is added
        to config-init and list-tools."""
        monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
        monkeypatch.chdir(tmp_path)
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(app, ["run"])
        assert result.exit_code == 2
        assert "no config file found: ./config.yaml" in result.stderr
    ```

    Note: `test_safe_02_cwd_autodiscovery_picks_up_local_config` will FAIL until Plan 13-02 lands the v2 validator + the yaml_file kwarg reading in `settings_customise_sources`. Mark it `@pytest.mark.xfail(reason="depends on Plan 13-02: Config(yaml_file=...) wiring + version=2 validator")` so the test surfaces automatically once 13-02 lands. The SAFE-03, SAFE-04, and the three new bypass/regression tests pass on this plan alone.

    Now add the SAFE-03 and SAFE-04 source-text regression tests. Append to `tests/unit/test_error_style.py` (mirroring the shape Plan 13-02 will add as `test_error_style_safe_06_body_matches_cli_wiring`):

    ```python
    def test_error_style_safe_03_body_matches_cli_wiring() -> None:
        """Phase 13 SAFE-03: cli.py's no-config branch must echo the LOCKED
        SAFE-03 body verbatim. Pins the source text so the wording cannot
        drift away from docs/ERROR-STYLE.md:46-55."""
        from pathlib import Path
        cli_text = (
            Path(__file__).resolve().parents[2]
            / "src" / "mcp_test_framework" / "cli.py"
        ).read_text("utf-8")
        # Substrings copied verbatim from docs/ERROR-STYLE.md:46-55.
        assert "no config file found: ./config.yaml" in cli_text
        assert "the framework refuses to run without a config file because it would" in cli_text
        assert "otherwise call every tool the server advertises -- including any" in cli_text
        assert "destructive ones. you must explicitly opt in to which tools run." in cli_text
        assert "run `mcp-test-framework config-init -o config.yaml` to generate" in cli_text
        assert "a starter config, then edit it to enable the tools you want to test" in cli_text

    def test_error_style_safe_04_body_matches_cli_wiring() -> None:
        """Phase 13 SAFE-04 (env-var branch): cli.py's MCPTF_CONFIG_FILE-typo
        branch lead and detail must match the locked shape verbatim. The
        SAFE-04 surface is not pre-locked in ERROR-STYLE.md (it's the
        parallel-of-SAFE-04-as-defined-for-the-flag-typo), so we pin the
        wording the plan committed to."""
        from pathlib import Path
        cli_text = (
            Path(__file__).resolve().parents[2]
            / "src" / "mcp_test_framework" / "cli.py"
        ).read_text("utf-8")
        assert "config file not found via MCPTF_CONFIG_FILE:" in cli_text
        assert "the path in MCPTF_CONFIG_FILE does not exist or is not a file." in cli_text
        assert "check the path or unset MCPTF_CONFIG_FILE and run" in cli_text
    ```
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_cli_errors.py tests/unit/test_error_style.py -v -k "safe_03 or safe_04 or empty_dir or list_tools_works or run_still_fails or error_style_safe_03 or error_style_safe_04" --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "os.environ\[\"MCPTF_CONFIG_FILE\"\] = " src/mcp_test_framework/cli.py` returns ZERO matches (the IPC pattern is gone).
    - `grep -n "Config(yaml_file=" src/mcp_test_framework/cli.py` returns at least one match in `_load_config`.
    - `grep -n "the framework refuses to run without a config file" src/mcp_test_framework/cli.py` returns one match (the SAFE-03 detail body).
    - `grep -n "config file not found via MCPTF_CONFIG_FILE" src/mcp_test_framework/cli.py` returns one match.
    - `grep -n "Path.cwd() / \"config.yaml\"" src/mcp_test_framework/cli.py` returns one match (the autodiscovery branch).
    - `grep -n "allow_missing" src/mcp_test_framework/cli.py` returns at least 5 matches: the parameter declaration, the docstring, the `if allow_missing:` branch, and the two call sites in `list_tools` and `config_init`.
    - `grep -n "_load_config(config, allow_missing=True)" src/mcp_test_framework/cli.py` returns exactly 2 matches (one in `list_tools`, one in `config_init`).
    - `uv run pytest tests/unit/test_cli_errors.py::test_safe_03_no_config_found_fails_loud_with_locked_message tests/unit/test_cli_errors.py::test_safe_04_mcptf_config_file_typo_exits_2 tests/unit/test_cli_errors.py::test_config_init_works_in_empty_dir_with_command_override tests/unit/test_cli_errors.py::test_list_tools_works_in_empty_dir tests/unit/test_cli_errors.py::test_run_still_fails_loud_in_empty_dir -x` exits 0.
    - `uv run pytest tests/unit/test_error_style.py::test_error_style_safe_03_body_matches_cli_wiring tests/unit/test_error_style.py::test_error_style_safe_04_body_matches_cli_wiring -x` exits 0.
    - Manual acceptance (PowerShell): create empty dir, cd into it, run `uv run mcp-test-framework config-init --command /bin/true -o $env:TEMP\out.yaml` — exits 0; run `uv run mcp-test-framework list-tools --command /bin/true` — does NOT emit "no config file found"; run `uv run mcp-test-framework run` — exits 2 with the SAFE-03 message.
    - `grep -nP "^\s*raise\s+_emit_operator_error" src/mcp_test_framework/cli.py` returns ZERO matches (rule from cli.py:75-77 — callers must not prefix with `raise`).
  </acceptance_criteria>
  <done>
    The four-branch resolver is in place with the `allow_missing` bypass; `os.environ[...]=...` IPC writes are gone from `_load_config`; SAFE-03 and SAFE-04 regression tests pass; the SAFE-02 autodiscovery test is xfail with a clear "blocked on Plan 13-02" reason; `config-init` and `list-tools` succeed from an unconfigured directory while `run` keeps SAFE-03 fail-loud; SAFE-03 and SAFE-04 source-pinning regression tests in test_error_style.py prevent verbatim wording drift; `_emit_operator_error_for_validation` is unchanged (Plan 13-02 owns the SAFE-06 wording flip).
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

    The `_validate_version` flip in `config.py` belongs to Plan 13-02 — DO NOT touch `config.py` in this plan.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_config_init.py -v --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "version: 1" src/mcp_test_framework/cli.py` returns ZERO matches.
    - `grep -n "version: 2" src/mcp_test_framework/cli.py` returns at least TWO matches (the comment line + the literal scaffold line in `_format_tools_yaml_scaffold`).
    - `grep -n "This release accepts version 2" src/mcp_test_framework/cli.py` returns one match.
    - `uv run pytest tests/unit/test_config_init.py -v` exits 0 (all updated tests pass).
    - Manual: running `uv run mcp-test-framework config-init -o $env:TEMP\test-v2.yaml` (PowerShell) and inspecting the output file shows `version: 2` on its own line.
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
| T-13-01-06 | Bootstrap UX bricking | The SAFE-03 message recommends `config-init`, but if `config-init` itself raised SAFE-03 the operator would be stuck | mitigate | The `allow_missing=True` bypass at `config_init` and `list_tools` call sites breaks the cycle. Regression tests `test_config_init_works_in_empty_dir_with_command_override` and `test_list_tools_works_in_empty_dir` lock the bypass; `test_run_still_fails_loud_in_empty_dir` confirms `run` is unaffected. |

No `high` severity threats; nothing blocks plan execution.
</threat_model>

<verification>
1. Manual SAFE-03 walk-through (PowerShell): create empty dir, `cd` into it, `Remove-Item Env:\MCPTF_CONFIG_FILE -ErrorAction SilentlyContinue; uv run mcp-test-framework run` — stderr matches the locked ERROR-STYLE.md SAFE-03 block; `$LASTEXITCODE` is 2.
2. Manual SAFE-04 walk-through (PowerShell): `$env:MCPTF_CONFIG_FILE = "C:\nonexistent\path"; uv run mcp-test-framework run` — stderr names MCPTF_CONFIG_FILE; `$LASTEXITCODE` is 2.
3. Manual --config typo walk-through (PowerShell): `uv run mcp-test-framework run --config C:\nonexistent\path` — stderr says `config file not found: C:\nonexistent\path` and names `--config`; `$LASTEXITCODE` is 2.
4. Manual config-init scaffold check (PowerShell): `uv run mcp-test-framework config-init -o $env:TEMP\v2-test.yaml; Select-String "version:" $env:TEMP\v2-test.yaml` shows `version: 2`.
5. Manual SAFE-03 RECOVERY walk-through (PowerShell): from the same empty dir, run `uv run mcp-test-framework config-init --command /bin/true -o config.yaml` — this should NOT raise SAFE-03 (the bypass kicks in); discovery may still fail downstream depending on `/bin/true` availability, but the resolver does not brick.
6. Regression tests: `uv run pytest tests/unit/test_cli_errors.py tests/unit/test_config_init.py tests/unit/test_error_style.py -v` exits 0.
7. Smoke: `uv run mcp-test-framework --help` still works (the resolver does not run for help-rendering); `$LASTEXITCODE` is 0.
</verification>

<success_criteria>
- Operator running `mcp-test-framework run` with no config anywhere sees the locked SAFE-03 message and exit 2 (truth 1 of must_haves).
- Operator with typo'd MCPTF_CONFIG_FILE sees a parity-shaped error (truth 3).
- Operator with valid ./config.yaml in cwd has it auto-discovered after Plan 13-02 lands (truth 4 — xfail test flips green when 13-02 ships).
- `os.environ[...]` is never written by `_load_config` (truth 5; grep-enforced).
- `config-init` scaffold emits `version: 2` (truth 6).
- Operator from unconfigured directory CAN run `config-init` and `list-tools`; only `run` fails loud (new truth 7).
- SAFE-03 and SAFE-04 message bodies are pinned by source-text regression tests in `tests/unit/test_error_style.py` (new truths 8 and 9).
- The "scaffold the SAFE-06 message points at" is correct from the moment Plan 13-02 lands the validator flip — the migration UX is internally consistent.
</success_criteria>

<output>
After completion, create `.planning/phases/13-config-safety-opt-in-tool-selection/13-01-SUMMARY.md` per the template at `$HOME/.claude/get-shit-done/templates/summary.md`. Include:
- The four-branch resolver shape (one diagram or pseudocode block).
- The `allow_missing` bypass: which call sites use it, why (SAFE-03 recovery non-bricking), and which command (`run`) keeps the default fail-loud behavior.
- The two grep gates: `os.environ\[\"MCPTF_CONFIG_FILE\"\] = ` returns 0 and `Config(yaml_file=` returns ≥1.
- A note that the `test_safe_02_cwd_autodiscovery_picks_up_local_config` test is `xfail` pending Plan 13-02 — and that 13-02's done-criteria includes flipping it to a real pass.
- Forward refs to: Plan 13-02 (config.py settings_customise_sources reads `init_kwargs.get("yaml_file")` + version validator flip), Plan 13-05 (MIGRATION-v1-to-v2.md regression test that asserts the scaffold's "version: 2" appears in the migration doc's step-by-step).
</output>
</content>
</invoke>