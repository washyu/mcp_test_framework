---
phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
plan: 02
type: execute
wave: 2
depends_on: [31-01]
files_modified:
  - src/mcp_test_framework/config.py
  - src/mcp_test_framework/cli.py
  - src/mcp_test_framework/_plugin.py
  - src/mcp_test_framework/fixtures.py
  - src/mcp_test_framework/models.py
  - .env.example
  - examples/homelab-mcp.yaml
autonomous: true
requirements: [SHIM-05]
tags: [config, deprecation-shim, env-var, plugin, visibility]
must_haves:
  truths:
    - "`MCPTF_CONFIG_FILE=/path/to/whatever.yaml uv run pytest` does NOT load the YAML at that path (env var is inert as a value source)."
    - "`MCPTF_CONFIG_FILE=/path/to/whatever.yaml uv run pytest` fires EXACTLY ONE DeprecationWarning, with the operator-tone D-06 wording, rendered with the `[mcp-contracts]` prefix (D-08 visibility upgrade)."
    - "`mcp-contracts run --config PATH` still works (CLI route preserved)."
    - "`[tool.pytest.ini_options] mcp_config_file = PATH` still works (library route preserved)."
    - "The CLI -> in-process pytest IPC channel uses `-o mcp_config_file=PATH` (D-10) — already shipped; no change needed except a guard test."
    - "No operator-facing `MCPTF_CONFIG_FILE` mention survives in cli.py help text, cli.py docstrings, fixtures.py error hints, models.py comments, .env.example, or examples/homelab-mcp.yaml header."
  artifacts:
    - path: "src/mcp_test_framework/config.py"
      provides: "settings_customise_sources without MCPTF_CONFIG_FILE env-var fallback"
      contains: "settings_customise_sources"
    - path: "src/mcp_test_framework/cli.py"
      provides: "_load_config with two branches (--config, ./config.yaml autodiscovery) — Branch 2 (env-var) gone"
      contains: "_load_config"
    - path: "src/mcp_test_framework/_plugin.py"
      provides: "pytest_configure with D-06-worded DeprecationWarning + D-08 scoped formatwarning override"
      contains: "no longer honored as of v1.5"
  key_links:
    - from: "src/mcp_test_framework/_plugin.py:pytest_configure"
      to: "warnings.warn(..., DeprecationWarning)"
      via: "scoped formatwarning override + try/finally restore"
      pattern: "formatwarning"
    - from: "src/mcp_test_framework/cli.py:run -> _runner.run_pytest_subprocess"
      to: "subprocess pytest argv ['-o', 'mcp_config_file=PATH']"
      via: "_runner._build_pytest_args (D-10 IPC, already shipped)"
      pattern: "mcp_config_file="
---

<objective>
Remove the `MCPTF_CONFIG_FILE` env-var as a value-source / path-pointer everywhere in src/, replace the v1.4 in-place DeprecationWarning with the operator-tone D-06 wording, install the D-08 scoped `warnings.formatwarning` override so the surviving warning renders with a `[mcp-contracts]` prefix isolated from pytest's deprecation chatter, and scrub every operator-facing mention from `.env.example` + `examples/homelab-mcp.yaml` header. Implements SHIM-05 per Phase 31 CONTEXT D-05..D-10.

Purpose: Close the Memory-flagged "MCPTF_CONFIG_FILE silent fail" / ".env beats --config" footguns by making the env var inert as a value source AND loud as a deprecation signal. Reduce the operator-facing config-resolution surface to two routes: `mcp_config_file` ini key (library mode) and `mcp-contracts run --config PATH` (CLI mode).

Output: ~70 lines deleted across config.py / cli.py / fixtures.py / models.py; ~25 lines rewritten in _plugin.py (D-06 wording + D-08 formatwarning override); ~5 lines edited in .env.example + examples/homelab-mcp.yaml.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md
@.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md
@docs/ERROR-STYLE.md
@src/mcp_test_framework/config.py
@src/mcp_test_framework/cli.py
@src/mcp_test_framework/_plugin.py
@src/mcp_test_framework/fixtures.py
@src/mcp_test_framework/models.py
@src/mcp_test_framework/_runner.py

<interfaces>
<!-- The D-10 IPC channel is already shipped — verified in research §"D-10 IPC Channel Verification". -->
From src/mcp_test_framework/_runner.py:_build_pytest_args (verified at HEAD L168-177):
```python
if mcp_config_path is not None:
    args.extend(["-o", f"mcp_config_file={mcp_config_path}"])
```
This is the surviving IPC channel. Plan 02 MUST NOT delete or alter this.

From src/mcp_test_framework/_plugin.py:pytest_configure (verified at HEAD L147-156):
```python
if os.environ.get("MCPTF_CONFIG_FILE"):
    warnings.warn(
        "MCPTF_CONFIG_FILE env var is deprecated since v1.4 and will be "
        "removed in v1.5 — use `[tool.pytest.ini_options] mcp_config_file = "
        "PATH` ...",
        DeprecationWarning,
        stacklevel=2,
    )
```
This block is the D-06 rewrite target.

From .env.example (verified per RESEARCH §"Doc / Config-File Inventory"):
- L15-16 contain `# Path to a YAML config file (read by --config / MCPTF_CONFIG_FILE).` and `# MCPTF_CONFIG_FILE=./config.yaml` — DELETE both.

From examples/homelab-mcp.yaml:
- L2 header comment carries `or point MCPTF_CONFIG_FILE at it` — EDIT to remove env-var reference.
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator shell env -> framework | Operator's `$env:MCPTF_CONFIG_FILE` may carry stale paths from older invocations |
| pytest plugin -> formatwarning rendering | The plugin temporarily overrides stdlib `warnings.formatwarning`; if not scoped, it could leak into operator-test warning rendering |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-31-02-01 | Information Disclosure (LOW) | Operator runs framework with `$env:MCPTF_CONFIG_FILE` pointing at a stale path | mitigate | The detection emits a loud DeprecationWarning with the `[mcp-contracts]` prefix (D-08 visibility upgrade) — operator gets a one-shot signal rather than a silent-load. The framework does NOT read the path; the env var becomes purely informational. |
| T-31-02-02 | Tampering (LOW) | `warnings.formatwarning` override leaks into pytest's own warning rendering | mitigate | D-08 prescription is a scoped `try/finally` override that restores `warnings.formatwarning` before `pytest_configure` returns — confined to the single `warnings.warn(...)` call window. Verified safe per RESEARCH §"Risks + Landmines" #1-2. |
| T-31-02-03 | Repudiation (INFORMATIONAL) | Operator claims they were not warned about the env-var deprecation | accept | DeprecationWarning fires once per pytest session via `pytest_configure`; pytest's session warnings list captures the warning into JUnit XML output (`_pytest.warnings.WarningsChecker` hook). Operator-visible AND machine-readable. |

ASVS classification: V8.2 (Operator-facing warning without sensitive data). Phase has no HIGH threats. The "loud-fail-instead-of-silent-fail" property is itself the mitigation for the Memory-cataloged footgun.
</threat_model>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Unwire MCPTF_CONFIG_FILE from config.py + cli.py value-source paths</name>
  <files>src/mcp_test_framework/config.py, src/mcp_test_framework/cli.py</files>
  <read_first>
    - src/mcp_test_framework/config.py (focus L205-251 — settings_customise_sources; env-var fallback at L229-235 per RESEARCH §"Verified Line Numbers")
    - src/mcp_test_framework/cli.py (focus L13-21 module docstring; L442-576 `_load_config` resolver; Branch 2 at L521-538; help-text references at L670, L1023, L1118, L1295-1297, L1308, L1322-1323, L1425)
    - src/mcp_test_framework/_runner.py L160-180 (verify _build_pytest_args D-10 IPC is preserved — DO NOT touch)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md (D-05, D-10)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md §"Verified Line Numbers" + §"D-10 IPC Channel Verification"
  </read_first>
  <behavior>
    - `Config(yaml_file=None)` with `MCPTF_CONFIG_FILE=/tmp/x.yaml` in env does NOT pick up `/tmp/x.yaml` — the env var is inert as a value source.
    - `_load_config` in cli.py is a TWO-branch resolver: Branch 1 = `--config PATH` flag; Branch 2 = `./config.yaml` autodiscovery via upward walk. (Old Branch 2 = env var — DELETED. Old Branch 3 = autodiscovery — renumbered to Branch 2.)
    - `mcp-contracts run --help` output does NOT contain the string `MCPTF_CONFIG_FILE`.
    - `mcp-contracts list-tools --help` / `config-init --help` / `gen-test-classes --help` / `gen-sdet-classes --help` output do NOT contain `MCPTF_CONFIG_FILE`.
    - `_runner._build_pytest_args` still threads `["-o", f"mcp_config_file={path}"]` into the subprocess argv whenever a path was resolved (D-10 IPC preserved — this is now the SOLE CLI->plugin channel).
  </behavior>
  <action>
    Two-file edit. Make config.py changes first, then cli.py.

    **File 1: src/mcp_test_framework/config.py**

    Inside `settings_customise_sources` (around L205-251), locate the env-var fallback block at ~L229-235 that calls `os.environ.get("MCPTF_CONFIG_FILE")` and synthesizes a `YamlConfigSettingsSource` against the resolved path. DELETE that entire block. The method should return the normal source-chain (init_kwargs, env_settings, dotenv_settings, file_secret_settings, possibly a `YamlConfigSettingsSource` only if `yaml_file` was passed to `__init__`).

    After deletion, `grep -n 'MCPTF_CONFIG_FILE' src/mcp_test_framework/config.py` should return zero matches.

    **File 2: src/mcp_test_framework/cli.py**

    1. **Module docstring (L13-21)** — scrub the `_load_config` precedence block to remove MCPTF_CONFIG_FILE mention. Replace "precedence: --config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud" (or equivalent) with "precedence: --config > ./config.yaml > fail-loud".

    2. **`_load_config` Branch 2 (L521-538)** — DELETE the entire env-var branch (the block that reads `os.environ.get("MCPTF_CONFIG_FILE")`, validates it, and returns the path). The resolver is now: try `--config` first; if absent, walk upward for `./config.yaml`; if none, fail loud. Renumber Branch 3 as Branch 2 in any comments/docstrings.

    3. **`--config` help-text references at L670, L1023, L1118, L1295-1297, L1425** — for each occurrence, replace strings like `"overrides MCPTF_CONFIG_FILE and ./config.yaml autodiscovery"` with `"overrides ./config.yaml autodiscovery"`. Preserve the rest of each help string. RESEARCH-flagged line numbers are HEAD-verified; exact text varies per command — read each occurrence and remove only the MCPTF_CONFIG_FILE portion.

    4. **L1308 docstring** — RESEARCH flagged: `"Honors the standard config-source precedence: --config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud."` Replace with `"Honors the standard config-source precedence: --config > ./config.yaml > fail-loud."`.

    5. **L1322-1323 docstring** — RESEARCH flagged: `"resolved against CWD (mirrors the MCPTF_CONFIG_FILE convention)"`. Replace with `"resolved against CWD"` (drop the parenthetical entirely).

    6. **L1425** — note that the `gen-sdet-classes` shim block (L1419-1438) is deleted in PHASE 32 SHIM-03, not here. Phase 31 only scrubs the help-text inside this shim — do NOT delete the shim itself.

    After edits, run `grep -n 'MCPTF_CONFIG_FILE' src/mcp_test_framework/cli.py` — the result MUST be zero matches.

    **DO NOT** touch `src/mcp_test_framework/_runner.py` — `_build_pytest_args` L168-177 is the surviving D-10 IPC channel; the `["-o", f"mcp_config_file={mcp_config_path}"]` injection MUST be preserved.
  </action>
  <verify>
    <automated>uv run python -c "import os; os.environ['MCPTF_CONFIG_FILE']='/nonexistent/should-not-load.yaml'; from mcp_test_framework.config import Config; c=Config(test_code={'generated_root':'x'}); print('OK', c.model_dump().get('test_code'))"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n 'MCPTF_CONFIG_FILE' src/mcp_test_framework/config.py` returns zero matches.
    - `grep -n 'MCPTF_CONFIG_FILE' src/mcp_test_framework/cli.py` returns zero matches.
    - `grep -n 'mcp_config_file=' src/mcp_test_framework/_runner.py` returns at least one match (D-10 IPC preserved).
    - `uv run mcp-contracts run --help 2>&1 | grep -c 'MCPTF_CONFIG_FILE'` returns 0.
    - `uv run mcp-contracts list-tools --help 2>&1 | grep -c 'MCPTF_CONFIG_FILE'` returns 0.
    - `uv run mcp-contracts config-init --help 2>&1 | grep -c 'MCPTF_CONFIG_FILE'` returns 0.
    - `uv run mcp-contracts gen-test-classes --help 2>&1 | grep -c 'MCPTF_CONFIG_FILE'` returns 0.
    - `Config(yaml_file=None)` with `MCPTF_CONFIG_FILE` set in env does NOT load the YAML at that path (validated by the inline python command above — the test_code value must come from init_kwargs, not the env-pointed YAML).
  </acceptance_criteria>
  <done>
    `MCPTF_CONFIG_FILE` is fully unwired as a value-source / path-pointer in config.py + cli.py; the D-10 IPC channel (`-o mcp_config_file=PATH` in _runner.py) is preserved.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rewrite _plugin.py DeprecationWarning to D-06 wording + install D-08 scoped formatwarning override</name>
  <files>src/mcp_test_framework/_plugin.py</files>
  <read_first>
    - src/mcp_test_framework/_plugin.py (entire file — focus L130-200; the DeprecationWarning block at L147-156 is the rewrite target)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md (D-06 verbatim wording; D-07 sole-emission-site; D-08 visibility-upgrade in scope; D-09 EOL planned for v1.6)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md §"D-08 Resolution" (concrete shape with try/finally restore)
    - src/mcp_test_framework/_reporter.py L147-151 (defensive-try/except style template per RESEARCH)
  </read_first>
  <behavior>
    - When `MCPTF_CONFIG_FILE` is set in env, `pytest_configure` fires EXACTLY ONE DeprecationWarning per session via `warnings.warn(...)`.
    - The warning message is verbatim D-06: `"MCPTF_CONFIG_FILE is set in your environment but no longer honored as of v1.5; configure via [tool.pytest.ini_options] mcp_config_file = PATH in pyproject.toml or pass --config PATH to mcp-contracts run."`
    - The warning RENDERING (via `warnings.formatwarning`) is prefixed with `[mcp-contracts]` and isolated from pytest's default `<file>:<line>: DeprecationWarning: <msg>` shape.
    - The formatwarning override is RESTORED via `try/finally` so pytest's default formatter is active for every other warning in the session.
    - The plugin does NOT read the path value; the env var remains inert as a value source.
    - When `MCPTF_CONFIG_FILE` is NOT set, no warning fires and no formatwarning override is installed.
    - A grandfathering comment marker is added next to the detection block so Phase 35 SHIM-09 plan author finds it (D-09 EOL: detection deleted in v1.6 capstone).
  </behavior>
  <action>
    Replace the existing block at `src/mcp_test_framework/_plugin.py:147-156` (current `if os.environ.get("MCPTF_CONFIG_FILE"): warnings.warn(...)`) with the D-08 scoped formatwarning shape from RESEARCH §"D-08 Resolution":

    ```python
    # NOTE for Phase 35 SHIM-09 regression-gate author: this MCPTF_CONFIG_FILE
    # detection is grandfathered in src/ for v1.5 (CONTEXT D-09); EOL in v1.6.
    if os.environ.get("MCPTF_CONFIG_FILE"):
        _original_formatwarning = warnings.formatwarning

        def _mcptf_formatwarning(message, category, filename, lineno, line=None):
            # Operator-tone single-block render. Bypasses pytest's default
            # "<file>:<line>: DeprecationWarning: <msg>" shape so the warning
            # is unambiguously distinct from pytest's own deprecation chatter.
            prefix = "[mcp-contracts]"
            try:
                if sys.stderr.isatty():
                    prefix = f"\x1b[31m{prefix}\x1b[0m"
            except Exception:
                pass
            return f"\n{prefix} {message}\n\n"

        warnings.formatwarning = _mcptf_formatwarning
        try:
            warnings.warn(
                "MCPTF_CONFIG_FILE is set in your environment but no longer "
                "honored as of v1.5; configure via "
                "`[tool.pytest.ini_options] mcp_config_file = PATH` in "
                "pyproject.toml or pass `--config PATH` to "
                "`mcp-contracts run`.",
                DeprecationWarning,
                stacklevel=2,
            )
        finally:
            warnings.formatwarning = _original_formatwarning
    ```

    Verify `import sys` and `import warnings` are present at the top of the file; add if missing.

    **The wording inside `warnings.warn(...)` is VERBATIM from CONTEXT D-06.** Do not reword.

    The ANSI red wrap (`\x1b[31m...\x1b[0m`) is the optional color upgrade RESEARCH endorsed — gate via `sys.stderr.isatty()` so it degrades cleanly under stdout redirection / non-VT Windows shells. The defensive try/except handles edge cases where `sys.stderr` is a substitute object without `isatty()`.

    **DO NOT** modify any other block in `_plugin.py` in this task — the rest of `pytest_configure` (mcp_config_file ini key reading, Config loading, ValidationError routing) is unchanged.
  </action>
  <verify>
    <automated>uv run python -c "import os, warnings, types; os.environ['MCPTF_CONFIG_FILE']='/x.yaml'; from mcp_test_framework import _plugin; fake_config=types.SimpleNamespace(getini=lambda k: '', getoption=lambda *a, **k: None, addinivalue_line=lambda *a, **k: None, pluginmanager=types.SimpleNamespace(register=lambda *a, **k: None, hasplugin=lambda *a, **k: False))
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always')
    try: _plugin.pytest_configure(fake_config)
    except Exception: pass
dep=[w for w in caught if issubclass(w.category, DeprecationWarning) and 'no longer honored' in str(w.message)]
assert len(dep)==1, [str(w.message) for w in caught]
print('OK one D-06 DeprecationWarning emitted')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n 'no longer honored as of v1.5' src/mcp_test_framework/_plugin.py` returns exactly one match.
    - `grep -n 'is deprecated since v1.4 and will be' src/mcp_test_framework/_plugin.py` returns zero matches (the old v1.4 wording is gone).
    - `grep -n 'formatwarning' src/mcp_test_framework/_plugin.py` returns at least one match (override is installed).
    - `grep -n 'finally:' src/mcp_test_framework/_plugin.py` returns at least one match in the vicinity of the override (the try/finally restore is present).
    - `grep -n '\[mcp-contracts\]' src/mcp_test_framework/_plugin.py` returns at least one match.
    - `grep -n 'Phase 35 SHIM-09\|v1.6' src/mcp_test_framework/_plugin.py` returns at least one match near the detection (the grandfathering marker for the next-phase planner).
    - The detection block does NOT read `os.environ['MCPTF_CONFIG_FILE']` for its value — only checks `.get(...)` for truthiness.
  </acceptance_criteria>
  <done>
    The surviving `MCPTF_CONFIG_FILE` detection in `_plugin.pytest_configure` fires the D-06 wording via a scoped D-08 formatwarning override that restores via try/finally.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Scrub MCPTF_CONFIG_FILE references from fixtures.py, models.py, .env.example, examples/homelab-mcp.yaml</name>
  <files>src/mcp_test_framework/fixtures.py, src/mcp_test_framework/models.py, .env.example, examples/homelab-mcp.yaml</files>
  <read_first>
    - src/mcp_test_framework/fixtures.py (focus L102-105 mcp_config docstring; L160-164 _session_needs_preflight docstring; L208-239 _preflight Check 1 emit; L321-333 Check 3 fallback hint)
    - src/mcp_test_framework/models.py (focus L206-209 TestCodeConfig docstring referencing MCPTF_CONFIG_FILE convention)
    - .env.example (entire file — L15-16 contain the env-var doc)
    - examples/homelab-mcp.yaml (focus L2 header)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md §"Doc / Config-File Inventory"
  </read_first>
  <behavior>
    - `grep -rn 'MCPTF_CONFIG_FILE' src/mcp_test_framework/fixtures.py src/mcp_test_framework/models.py` returns zero matches.
    - `grep -n 'MCPTF_CONFIG_FILE' .env.example` returns zero matches.
    - `grep -n 'MCPTF_CONFIG_FILE' examples/homelab-mcp.yaml` returns zero matches.
    - Operator-facing fixture error hints (the `mcp_config_file points at PATH which does not exist...` style) still reference `[tool.pytest.ini_options] mcp_config_file = PATH` and `--config PATH` as the actionable next steps.
  </behavior>
  <action>
    Four-file scrub. Each is small and mechanical:

    **File 1: src/mcp_test_framework/fixtures.py**

    Read every site flagged by RESEARCH §"Verified Line Numbers" (L102-105, L160-164, L208-239, L321-333). For each:
    - If the line is a docstring mentioning `MCPTF_CONFIG_FILE` as a resolver convention or workaround — remove or replace with `mcp_config_file` ini-key reference.
    - If the line is part of a `pytest.exit(...)` operator-tone hint message (Check 1 emit at ~L231-238, Check 3 fallback at ~L321-333) — replace `MCPTF_CONFIG_FILE`-bearing copy with the canonical two-route guidance: "set `[tool.pytest.ini_options] mcp_config_file = PATH` in pyproject.toml or pass `--config PATH` to `mcp-contracts run`". Preserve the rest of each error body (exit code, three-part shape).

    **File 2: src/mcp_test_framework/models.py**

    L206-209 contains a comment in `TestCodeConfig`'s docstring referring to `MCPTF_CONFIG_FILE` convention. Scrub the comment — replace with `mcp_config_file` ini-key reference, OR delete the line entirely if it's not load-bearing for the docstring's meaning.

    **File 3: .env.example**

    L15-16 contain:
    ```
    # Path to a YAML config file (read by --config / MCPTF_CONFIG_FILE).
    # MCPTF_CONFIG_FILE=./config.yaml
    ```
    DELETE BOTH LINES. If the surrounding lines reference these via cross-mention, scrub those too. The `.env.example` file should no longer document any way to point at a config — the only two routes are `--config` and `mcp_config_file` ini key, neither of which lives in `.env`.

    **File 4: examples/homelab-mcp.yaml**

    L2 header currently reads (per RESEARCH):
    ```
    # Copy to config.yaml at your project root, or point MCPTF_CONFIG_FILE at it.
    ```
    Replace with:
    ```
    # Copy to config.yaml at your project root, or pass via --config / [tool.pytest.ini_options] mcp_config_file.
    ```

    Do NOT touch `config.example.yaml` — RESEARCH verified it's already clean at HEAD (worktree noise greps showed legacy comments, but parent HEAD is correct).
  </action>
  <verify>
    <automated>uv run python -c "import subprocess; r=subprocess.run(['grep','-rn','MCPTF_CONFIG_FILE','src/mcp_test_framework/fixtures.py','src/mcp_test_framework/models.py','.env.example','examples/homelab-mcp.yaml'], capture_output=True, text=True); print('STDOUT:', r.stdout); print('STDERR:', r.stderr); assert r.stdout.strip()=='', f'leftover refs: {r.stdout}'; print('OK clean')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -rn 'MCPTF_CONFIG_FILE' src/mcp_test_framework/fixtures.py` returns zero matches.
    - `grep -rn 'MCPTF_CONFIG_FILE' src/mcp_test_framework/models.py` returns zero matches.
    - `grep -n 'MCPTF_CONFIG_FILE' .env.example` returns zero matches.
    - `grep -n 'MCPTF_CONFIG_FILE' examples/homelab-mcp.yaml` returns zero matches.
    - `grep -n 'mcp_config_file' src/mcp_test_framework/fixtures.py` returns at least one match in the rewritten operator hint (the scrub does not silently delete operator guidance — it replaces it with the canonical surface).
    - The `examples/homelab-mcp.yaml` L2 header references `--config` or `mcp_config_file` (not the env var).
  </acceptance_criteria>
  <done>
    All operator-facing `MCPTF_CONFIG_FILE` references in src/ + `.env.example` + `examples/homelab-mcp.yaml` are scrubbed; the only surviving src/ match is the grandfathered detection in `_plugin.py` (Task 2).
  </done>
</task>

</tasks>

<verification>
Phase-level checks after all three tasks complete:

1. `grep -rn 'MCPTF_CONFIG_FILE' src/mcp_test_framework/` returns EXACTLY ONE match — the detection block in `_plugin.py:pytest_configure` (Task 2 site).
2. `grep -rn 'MCPTF_CONFIG_FILE' .env.example examples/homelab-mcp.yaml` returns zero matches.
3. `uv run mcp-contracts run --help 2>&1 | grep -c 'MCPTF_CONFIG_FILE'` returns 0.
4. End-to-end loud-warning smoke (manual):
   - Set `$env:MCPTF_CONFIG_FILE = "C:\Users\washy\config.yaml"` in a PowerShell session.
   - Run `uv run pytest tests/framework/unit/test_error_style.py -q`.
   - Expected: a `[mcp-contracts]`-prefixed DeprecationWarning fires once, body matches D-06; pytest continues normally (config.yaml is NOT loaded from the env-pointed path).
</verification>

<success_criteria>
- All three tasks' acceptance criteria met.
- The Memory-flagged "MCPTF_CONFIG_FILE silent fail" footgun is closed: env var is inert as a value source, loud as a deprecation signal.
- D-10 IPC channel (`-o mcp_config_file=PATH` in `_runner._build_pytest_args`) is preserved.
- Phase 35 SHIM-09 plan author can find the grandfathered detection via the in-source `Phase 35 SHIM-09` marker comment in `_plugin.py`.
</success_criteria>

<output>
After completion, create `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-02-SUMMARY.md`
</output>
