---
phase: 28-codegen-output-path-codegen
plan: 03
type: execute
wave: 3
depends_on: [28-01, 28-02]
files_modified:
  - src/mcp_test_framework/cli.py
  - tests/framework/unit/test_gen_test_classes_overwrite_prompt.py
  - tests/framework/unit/test_missing_generated_root_error.py
autonomous: true
requirements:
  - CODEGEN-LIB-01
must_haves:
  truths:
    - "Operator running `mcp-contracts gen-test-classes` in a TTY against a target directory that does not exist sees codegen proceed silently (no prompt)."
    - "Operator running in a TTY against a target directory that exists but is empty sees codegen proceed silently (no prompt)."
    - "D-05: Operator running in a TTY against a target directory that contains files is prompted via `typer.confirm` showing the file count and target path; declining aborts with exit code 2. Missing dir → create silently; empty dir → write silently."
    - "D-04: `generated_root: Path = Field(...)` REQUIRED and its empty-string field validator stay as-is in `models.py`; no new pydantic-level validators added (no absolute/relative enforcement, no `..`-segment rejection). All command-time policy (existence, writability, guard, non-empty prompt) lives in `cli.py:gen_test_classes`, NOT in pydantic."
    - "Operator running in a non-TTY context (CI, scripts, piped stdin) against a non-empty target directory sees `gen-test-classes` abort with exit code 2 and an operator-tone error explaining that the directory must be cleaned manually."
    - "No `--yes` / `--force` flag exists for `gen-test-classes` (per D-06)."
    - "Operator who loads a config YAML missing `test_code.generated_root` sees an operator-tone error whose body contains the literal strings `test_code.generated_root` AND `mcp-contracts config-init` (per D-02)."
  artifacts:
    - path: "src/mcp_test_framework/cli.py"
      provides: "`_confirm_or_abort_non_empty_target(target_dir)` helper called from `gen_test_classes` AFTER the site-packages guard but BEFORE the `_codegen.generate` call; `_emit_operator_error_for_validation` missing-required-field branch verified (or rewritten) to name `test_code.generated_root` and point at `mcp-contracts config-init`."
      contains: "def _confirm_or_abort_non_empty_target("
    - path: "tests/framework/unit/test_gen_test_classes_overwrite_prompt.py"
      provides: "Unit tests covering: empty-dir silent write, missing-dir silent write, non-empty-tty-accept-proceeds, non-empty-tty-decline-aborts-2, non-empty-non-tty-aborts-2, no --yes flag exists on the command."
      contains: "def test_non_empty_dir_in_non_tty_aborts_with_exit_2"
    - path: "tests/framework/unit/test_missing_generated_root_error.py"
      provides: "Regression test asserting the missing-`test_code.generated_root` error names the field path and points at `mcp-contracts config-init` (D-02)."
      contains: "def test_missing_generated_root_error_names_field_and_config_init"
  key_links:
    - from: "src/mcp_test_framework/cli.py::gen_test_classes"
      to: "src/mcp_test_framework/cli.py::_confirm_or_abort_non_empty_target"
      via: "direct call after handshake + server_name resolution, on the resolved `out_root / slug` path, BEFORE `_codegen.generate(...)`"
      pattern: "_confirm_or_abort_non_empty_target\\("
    - from: "src/mcp_test_framework/cli.py::_emit_operator_error_for_validation"
      to: "operator-facing missing-required-field error text"
      via: "literal strings `test_code.generated_root` AND `mcp-contracts config-init` in the rendered error body (D-02)"
      pattern: "mcp-contracts config-init"
---

<objective>
Wrap the wipe-and-write `_codegen.generate(...)` call with a confirmation gate. If the target directory does not exist, create silently. If empty, write silently. If non-empty AND running in a TTY, prompt via `typer.confirm` with file count and target path; decline aborts exit 2. If non-empty AND non-TTY (CI, scripts, piped stdin), abort with operator-tone error exit 2 — no `--yes` flag exists.

Also: audit the existing missing-required-field error path against D-02 / `docs/ERROR-STYLE.md`. The error MUST name the missing field by full path (`test_code.generated_root`) AND point at `mcp-contracts config-init`. If today's text already satisfies both, no code change is required and the audit result is documented. If it does not, rewrite `_emit_operator_error_for_validation`'s missing-field branch (or the equivalent rendering site) so both literal strings appear in operator-facing output.

Purpose: D-05 + D-06 (overwrite prompt) AND D-02 (operator-tone error refresh for missing `generated_root`). Strongest "never silently destroy data" stance. The only way to overwrite in CI is to delete the directory first. The fail-loud-on-missing-field error path is the operator's first contact with `gen-test-classes`; it must speak in operator terms.

Output: new `_confirm_or_abort_non_empty_target(target_dir)` helper in cli.py, wired into `gen_test_classes` between the slug-derivation step and the `_codegen.generate` call. Unit test file covering all five overwrite scenarios plus a regression test that no `--yes` / `--force` flag exists on the command. Regression test asserting the missing-`test_code.generated_root` error names the field and `mcp-contracts config-init` (with rewrite of the rendering site if today's text fails the audit).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md
@.planning/phases/28-codegen-output-path-codegen/28-01-site-packages-guard-PLAN.md
@.planning/phases/28-codegen-output-path-codegen/28-02-pyproject-ini-config-route-PLAN.md
@docs/ERROR-STYLE.md
@src/mcp_test_framework/cli.py

<interfaces>
<!-- Existing operator-tone error helper Phase 28 reuses verbatim. -->

From src/mcp_test_framework/cli.py (lines 97 + 188-203) — reuse:
```python
_emit_operator_error(
    summary="...",
    detail=[...],
    next_step="...",
)
# Raises typer.Exit(code=2). Never returns.
```

`typer.confirm` API (typer 0.25.x, transitive via mcp[cli]):
```python
import typer
proceed = typer.confirm("N files exist in <path>. Overwrite? [y/N]", default=False)
# Returns bool. In a non-TTY context (no stdin tty), typer.confirm raises
# click.exceptions.Abort by default. We catch that and re-emit as operator-tone error.
# Or: check sys.stdin.isatty() BEFORE calling and short-circuit to the
# non-TTY error path. Per Phase 28 D-06 we use explicit isatty() check for
# predictability across Typer/Click versions.
```

`gen_test_classes` insertion site (cli.py, after Plan 28-01 wiring). The new helper call goes AFTER:
- `_guard_against_site_packages_target(out_root)` (Plan 28-01)
- the handshake (`runner.run(_run_codegen_handshake(cfg))`)
- the server-name empty check
- `from mcp_test_framework.test_code._slugs import server_slug` and `slug = server_slug(server_name)` derivation
... and BEFORE the `_codegen.generate(...)` call.

Important: the target the prompt checks is `out_root / slug` (where `_codegen.generate` actually writes), NOT `out_root` itself. Operators may have unrelated content in `out_root` (e.g. other servers' generated trees) — only the specific server's subdirectory is at risk of being overwritten by THIS invocation.

`slug = server_slug(server_name)` lives at cli.py around line 1100; the existing `typer.echo(f"  target:    {out_root / slug}/")` (around line 1104) is the printout that already confirms `out_root / slug` is the actual write target.

Note on slug derivation timing: the slug is only known AFTER the handshake completes (depends on `serverInfo.name`). So the prompt CANNOT fire before the handshake — only after slug derivation. That is the only piece of "destructive" logic that happens after handshake; everything else (config errors, server-name errors) happens before. The prompt placement is therefore minimal-additional-server-startup-cost.

<!-- D-02 audit target: existing missing-required-field error rendering. -->

From src/mcp_test_framework/cli.py lines 172-185 (current `_emit_operator_error_for_validation` missing-field branch):
```python
if err_type in ("missing", "value_error.missing"):
    _emit_operator_error(
        summary=f"config file is missing a required field: {loc}",
        detail=[
            f"the field `{loc}` is required but was not found in {source}.",
            "",
            "see config.example.yaml for the expected shape, or regenerate "
            "a starter file with config-init.",
        ],
        next_step=(
            "copy the relevant block from config.example.yaml or run "
            "`mcp-test-framework config-init -o config.yaml`"
        ),
    )
```

Audit observations the executor must verify by running the live capture in Task 2:
- The literal string `test_code.generated_root` appears in the rendered output ONLY IF Pydantic surfaces `loc = ("test_code", "generated_root")` (which becomes `loc = "test_code.generated_root"`). This depends on whether `TestCodeConfig` is included by `Config()` even when the YAML has no `test_code` block, OR whether the missing-field path fires at `test_code` (one level up) instead of `test_code.generated_root`.
- The literal string `mcp-contracts config-init` does NOT appear in today's text — `next_step` currently says `mcp-test-framework config-init -o config.yaml` (legacy CLI name).

Likely audit outcome: today's error names `test_code.generated_root` correctly when the YAML has `test_code: {}` but no `generated_root`; the legacy `mcp-test-framework config-init` invocation is stale and must be rewritten to `mcp-contracts config-init` to satisfy D-02. The executor confirms both branches via live capture before patching.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add _confirm_or_abort_non_empty_target helper and wire into gen_test_classes between slug derivation and codegen with unit tests</name>
  <files>src/mcp_test_framework/cli.py, tests/framework/unit/test_gen_test_classes_overwrite_prompt.py</files>
  <read_first>
    - src/mcp_test_framework/cli.py lines 1075-1110 (gen_test_classes body around slug derivation + _codegen.generate call) — locate the insertion point
    - src/mcp_test_framework/cli.py lines 97 + 188-203 (_emit_operator_error usage example)
    - .planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md sections `<decisions>` D-05 / D-06 and `<specifics>` "Non-empty-dir prompt is the only piece of NEW operator-facing UX in Phase 28"
    - docs/ERROR-STYLE.md — error tone rules for the non-TTY abort message
    - tests/framework/unit/test_gen_sdet_classes_cli.py — CliRunner test pattern; pay attention to how `_invoke` sets `env` and how `_write_config` builds a minimal config.yaml
    - Plan 28-01 PLAN.md — to confirm the site-packages guard is already in place before this plan runs (depends_on chain)
  </read_first>
  <behavior>
    - Test 1 (missing-target-silent): operator runs `gen-test-classes` with `cfg.test_code.generated_root / slug` NOT existing. No prompt. `_codegen.generate` is called.
    - Test 2 (empty-target-silent): operator runs with target directory existing but empty. No prompt. `_codegen.generate` is called.
    - Test 3 (non-empty-tty-accept-proceeds): operator runs with non-empty target. In a TTY where `typer.confirm` returns True, `_codegen.generate` is called.
    - Test 4 (non-empty-tty-decline-aborts-2): operator runs with non-empty target. In a TTY where `typer.confirm` returns False, command exits 2 with operator-tone message naming the target path.
    - Test 5 (non-empty-non-tty-aborts-2): operator runs with non-empty target AND `sys.stdin.isatty()` returns False (mock via monkeypatch). Command exits 2 with operator-tone error mentioning "non-empty" and instructing the operator to clean the directory manually. The error message MUST NOT mention any `--yes` or `--force` flag.
    - Test 6 (no-force-flag-exists): `mcp-contracts gen-test-classes --help` output does NOT contain the string `--yes` or `--force` (regression guard against future re-introduction per D-06).
    - Test 7 (file-count-in-prompt): the prompt message contains the number of files in the target (e.g. "3 files exist"). Suggested implementation per CONTEXT.md discretion: short-circuit count after, say, 100 hits to keep cost bounded.
  </behavior>
  <action>
    Step 1 — Add `_confirm_or_abort_non_empty_target` helper to `src/mcp_test_framework/cli.py`. Insert after `_guard_against_site_packages_target` (added in Plan 28-01, around line 100-140):

```python
def _confirm_or_abort_non_empty_target(target_dir: Path) -> None:
    """Confirmation gate before wipe-and-write codegen (D-05 + D-06).

    Behavior:
        - target_dir does not exist           -> return silently (caller creates)
        - target_dir exists but is empty      -> return silently
        - target_dir exists with files in TTY -> `typer.confirm` prompt; declining aborts exit 2
        - target_dir exists with files non-TTY -> operator-tone error exit 2 (NO --yes flag exists)

    Per D-06 the only way to overwrite in a non-TTY context (CI, scripts,
    piped stdin) is to delete the directory manually and re-run. The
    framework deliberately offers no `--yes` / `--force` escape hatch.

    Args:
        target_dir: the directory `_codegen.generate` will wipe-and-write
            into (typically `out_root / slug`, NOT `out_root` itself).
    """
    if not target_dir.exists():
        return
    # Count files; cap the walk so a pathological tree doesn't stall the CLI.
    # The exact count goes into the prompt copy per D-05 discretion.
    files = []
    try:
        for entry in target_dir.iterdir():
            files.append(entry)
            if len(files) >= 1000:
                break
    except OSError:
        # If the directory is unreadable, fall through to the prompt anyway
        # — the codegen call will produce a clearer error than we can here.
        return
    if not files:
        return
    file_count = len(files)
    suffix = "+" if file_count >= 1000 else ""
    if not sys.stdin.isatty():
        _emit_operator_error(
            summary=f"gen-test-classes: refusing to overwrite non-empty directory in non-interactive context",
            detail=[
                f"the target directory `{target_dir}` contains {file_count}{suffix} "
                f"entries and gen-test-classes cannot prompt for confirmation in "
                f"this environment (no TTY on stdin).",
                "the framework does not offer a `--yes` / `--force` flag for this "
                "command -- the strongest 'never silently destroy data' posture.",
            ],
            next_step=(
                f"delete the contents of `{target_dir}` manually and re-run "
                f"`mcp-contracts gen-test-classes`"
            ),
        )
    proceed = typer.confirm(
        f"{file_count}{suffix} entries exist in {target_dir}. Overwrite?",
        default=False,
    )
    if not proceed:
        _emit_operator_error(
            summary=f"gen-test-classes: declined; not overwriting `{target_dir}`",
            detail=[
                "you answered no to the overwrite prompt; no files were written.",
            ],
            next_step=(
                "delete the contents of the target directory manually if you "
                "intend to regenerate, then re-run `mcp-contracts gen-test-classes`"
            ),
        )
```

Step 2 — Wire the helper into `gen_test_classes` in `src/mcp_test_framework/cli.py`. Find the existing block around `slug = server_slug(server_name)` (currently ~line 1100) and the subsequent `try: counts = _codegen.generate(...)` call. Insert the gate BETWEEN slug derivation and the codegen call:

```python
    slug = server_slug(server_name)
    target_dir = out_root / slug
    _confirm_or_abort_non_empty_target(target_dir)

    server_version = getattr(server_info, "version", "") or ""
    try:
        counts = _codegen.generate(
            server_name=server_name,
            server_version=server_version,
            tools=tools,
            out_root=out_root,
        )
```

Note: the existing code computes `slug` AFTER the `_codegen.generate(...)` call (currently line 1100 vs the generate call at line 1084). Relocate `slug = server_slug(server_name)` to BEFORE the codegen call so the prompt can reference `out_root / slug`. The existing post-codegen `typer.echo(f"  target:    {out_root / slug}/")` (line 1104) is unaffected (slug is just available earlier now). Also relocate `server_version = ...` to keep it near the `_codegen.generate(...)` call (existing pattern).

Step 3 — Create `tests/framework/unit/test_gen_test_classes_overwrite_prompt.py`. Use a mix of direct helper invocation (with monkeypatch on `sys.stdin.isatty` + `typer.confirm`) and CLI-level tests:

```python
"""Unit tests for the Phase 28 D-05 / D-06 non-empty-dir overwrite prompt."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
import yaml
from typer.testing import CliRunner

from mcp_test_framework.cli import _confirm_or_abort_non_empty_target, app


def test_missing_target_dir_returns_silently(tmp_path: Path) -> None:
    target = tmp_path / "does_not_exist"
    # Should not raise. Should not touch typer.confirm or sys.stdin.
    assert _confirm_or_abort_non_empty_target(target) is None


def test_empty_target_dir_returns_silently(tmp_path: Path) -> None:
    target = tmp_path / "empty"
    target.mkdir()
    assert _confirm_or_abort_non_empty_target(target) is None


def test_non_empty_dir_in_tty_accept_returns_silently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "populated"
    target.mkdir()
    (target / "a.py").write_text("# placeholder")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with patch("mcp_test_framework.cli.typer.confirm", return_value=True) as mock_confirm:
        assert _confirm_or_abort_non_empty_target(target) is None
    assert mock_confirm.call_count == 1


def test_non_empty_dir_in_tty_decline_aborts_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "populated"
    target.mkdir()
    (target / "a.py").write_text("# placeholder")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with patch("mcp_test_framework.cli.typer.confirm", return_value=False):
        with pytest.raises(typer.Exit) as exc_info:
            _confirm_or_abort_non_empty_target(target)
    assert exc_info.value.exit_code == 2


def test_non_empty_dir_in_non_tty_aborts_with_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "populated"
    target.mkdir()
    (target / "a.py").write_text("# placeholder")
    (target / "b.py").write_text("# placeholder")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(typer.Exit) as exc_info:
        _confirm_or_abort_non_empty_target(target)
    assert exc_info.value.exit_code == 2
    captured = capsys.readouterr()
    combined = captured.err + captured.out
    # Mentions non-empty / non-interactive context:
    assert "non-interactive" in combined or "non-empty" in combined
    # Mentions the target path:
    assert str(target) in combined
    # Does NOT advertise a --yes / --force flag (D-06: no escape hatch):
    assert "--yes" not in combined
    assert "--force" not in combined


def test_file_count_appears_in_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "populated"
    target.mkdir()
    for i in range(3):
        (target / f"f{i}.py").write_text("# placeholder")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with patch("mcp_test_framework.cli.typer.confirm", return_value=True) as mock_confirm:
        _confirm_or_abort_non_empty_target(target)
    call_args = mock_confirm.call_args
    prompt_text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "3" in prompt_text  # file count
    assert str(target) in prompt_text


def test_gen_test_classes_command_has_no_yes_or_force_flag() -> None:
    """D-06 regression guard: no --yes / --force ever sneaks back in."""
    runner = CliRunner()
    result = runner.invoke(app, ["gen-test-classes", "--help"])
    assert result.exit_code == 0
    assert "--yes" not in result.stdout
    assert "--force" not in result.stdout
```

Step 4 — Run the tests:

```
uv run pytest tests/framework/unit/test_gen_test_classes_overwrite_prompt.py -x -v
```

Step 5 — Run the broader gen-test-classes regression suite and the full framework suite:

```
uv run pytest tests/framework/unit/test_gen_sdet_classes_cli.py tests/framework/unit/test_gen_sdet_classes_config_driven.py tests/framework/unit/test_gen_test_classes_site_packages_guard.py tests/framework/unit/test_gen_test_classes_pyproject_config.py -x
uv run pytest tests/framework/ -x
```

If any existing gen-test-classes test fails, the regression is likely that the helper now blocks the wipe-and-write path. Update the affected fixture/test to either:
(a) point `test_code.generated_root` at a fresh tmp_path subdir (which is naturally empty), OR
(b) explicitly clean the target between runs, OR
(c) mock `_confirm_or_abort_non_empty_target` at the patch site.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_gen_test_classes_overwrite_prompt.py tests/framework/unit/test_gen_sdet_classes_cli.py tests/framework/unit/test_gen_sdet_classes_config_driven.py tests/framework/unit/test_gen_test_classes_site_packages_guard.py tests/framework/unit/test_gen_test_classes_pyproject_config.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - src/mcp_test_framework/cli.py contains the literal string `def _confirm_or_abort_non_empty_target(`
    - src/mcp_test_framework/cli.py contains the literal string `_confirm_or_abort_non_empty_target(target_dir)` inside `gen_test_classes` body
    - The call sits AFTER `slug = server_slug(server_name)` and BEFORE `_codegen.generate(`
    - `mcp-contracts gen-test-classes --help` output does NOT contain `--yes` or `--force` (verified by `test_gen_test_classes_command_has_no_yes_or_force_flag`)
    - tests/framework/unit/test_gen_test_classes_overwrite_prompt.py exists with at least seven `def test_` functions covering the seven behaviors above
    - `uv run pytest tests/framework/unit/test_gen_test_classes_overwrite_prompt.py -x -v` exits 0
    - `uv run pytest tests/framework/ -x` exits 0 (no regression in existing framework suite, including existing gen-test-classes CLI tests)
    - Grep `grep -n "import sys" src/mcp_test_framework/cli.py` shows `import sys` already present (it is, line 48); no duplicate import added
  </acceptance_criteria>
  <done>
    - Helper defined, wired into gen_test_classes between slug derivation and codegen, seven behavior tests pass, no `--yes`/`--force` flag exists, no regression in existing framework suite.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Audit + (likely) rewrite the missing-`test_code.generated_root` operator error to name the field and point at `mcp-contracts config-init` (D-02)</name>
  <files>src/mcp_test_framework/cli.py, tests/framework/unit/test_missing_generated_root_error.py</files>
  <read_first>
    - src/mcp_test_framework/cli.py lines 100-203 — the full `_emit_operator_error_for_validation` function, including the `missing` / `value_error.missing` branch at lines 172-185 where today's rendering of "config file is missing a required field" lives.
    - docs/ERROR-STYLE.md — full file. The audit checks tone (operator-terms-only, lowercase summary, no internal jargon), field-path naming, and the `next:` imperative-verb shape against this template.
    - src/mcp_test_framework/models.py around line 190 (`TestCodeConfig.generated_root: Path = Field(...)`) — confirms the field path Pydantic surfaces is `("test_code", "generated_root")`, which joins to `test_code.generated_root` in the `loc` formatter at cli.py line 133.
    - .planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md `<domain>` item 6 and `<decisions>` D-02 — the literal acceptance bar.
    - tests/framework/unit/test_sdet_config_model.py and tests/framework/unit/test_config_sdet_field.py — existing missing-`test_code` / missing-`generated_root` test patterns the new test file should mirror in style (file naming, CliRunner usage, capsys / capfd capture conventions).
  </read_first>
  <behavior>
    - Test 1 (field path appears): a YAML config that has a `test_code:` block but is missing `generated_root` (e.g. `test_code: {}`) triggers an operator-tone error whose stderr/stdout contains the literal string `test_code.generated_root`.
    - Test 2 (next-step points at mcp-contracts config-init): the SAME error invocation contains the literal string `mcp-contracts config-init` in its rendered output.
    - Test 3 (no legacy CLI name in next-step): the SAME error invocation does NOT contain `mcp-test-framework config-init` (the legacy command name from the v1.4 deprecation shim — operator-facing next-step copy must point at the new name).
    - Test 4 (exit code): the command exits with code 2 (config / validation error class).

    All four assertions cover the same invocation; they may live in a single `def test_missing_generated_root_error_names_field_and_config_init` body.
  </behavior>
  <action>
    Step A — Audit (live capture, no code change yet):

    Capture today's rendered error text by exercising the path under test. From a fresh REPL or a throwaway script run via `uv run python -c "..."`:

    ```python
    import io
    import contextlib
    from pathlib import Path
    import yaml
    import typer
    from mcp_test_framework.config import Config  # or the appropriate import path

    cfg_path = Path("/tmp/audit_no_generated_root.yaml")
    cfg_path.write_text(yaml.safe_dump({
        "version": 2,
        "mcp_server": {"command": "irrelevant", "args": []},
        "test_code": {},
        "tools": {},
    }))
    # Trigger the same code path the CLI uses (model_validate via Config init).
    # Adapt the call to whichever Config-construction path _load_config takes
    # in src/mcp_test_framework/cli.py.
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf), contextlib.redirect_stdout(buf):
        try:
            Config(yaml_file=cfg_path)
        except (typer.Exit, SystemExit):
            pass
    print("---CAPTURED ERROR TEXT---")
    print(buf.getvalue())
    ```

    Alternatively (cleaner): use Typer's CliRunner with `mcp-contracts run --config /tmp/audit_no_generated_root.yaml` and capture `result.stdout + result.stderr`.

    Compare the captured text against the D-02 acceptance bar:
    1. Does it contain `test_code.generated_root` verbatim?
    2. Does it contain `mcp-contracts config-init` verbatim (not `mcp-test-framework config-init`)?
    3. Is the summary lowercase and operator-tone (no pydantic jargon)?

    Document the audit outcome in the SUMMARY.md output: "audit result: <strings found/missing>; <patched/no patch needed>".

    Step B — Patch (only if audit failed any of 1/2/3):

    Based on the pre-audit reading of cli.py lines 172-185, the expected outcome is:
    - `test_code.generated_root` IS present (the `loc` formatter on line 133 joins the Pydantic loc tuple with `.`, and `Field(...)` REQUIRED status surfaces the leaf field path when `test_code: {}` is provided).
    - `mcp-contracts config-init` is NOT present — today's `next_step` says `mcp-test-framework config-init -o config.yaml` (legacy CLI name).

    If the audit confirms the legacy-name issue, edit `src/mcp_test_framework/cli.py` `_emit_operator_error_for_validation` `missing` branch (lines 172-185). Replace the `next_step` block:

    Find:
    ```python
            next_step=(
                "copy the relevant block from config.example.yaml or run "
                "`mcp-test-framework config-init -o config.yaml`"
            ),
    ```

    Replace with:
    ```python
            next_step=(
                "copy the relevant block from config.example.yaml or run "
                "`mcp-contracts config-init -o config.yaml`"
            ),
    ```

    The detail block already names `{loc}` (which renders as `test_code.generated_root`) and points at `config-init`; only the CLI binary name needs to flip from the legacy `mcp-test-framework` to the v1.4 canonical `mcp-contracts`. This is consistent with the Phase 25 / Phase 27 deprecation pattern (legacy name kept as a working shim until v1.5, but operator-facing next-step copy uses the new name).

    Also scan the rest of `_emit_operator_error_for_validation` (lines 100-203) for any other `mcp-test-framework config-init` occurrences in operator-facing next-step copy. If found, flip those too (they're all in operator-facing next-step lines; commands and shims in the actual code stay legacy-compatible).

    If the audit shows `test_code.generated_root` is NOT surfaced (e.g. Pydantic flags `test_code` one level up), additionally restructure the missing-field branch so the detail block reads:
    ```python
        detail=[
            f"the field `test_code.generated_root` is required but was not found in {source}.",
            ...
        ],
    ```
    (Use a hard-coded `test_code.generated_root` only inside an `if loc in ("test_code", "test_code.generated_root"):` sub-branch — the generic missing-field path still uses `{loc}` for other fields.)

    Step C — Create the regression test `tests/framework/unit/test_missing_generated_root_error.py`:

    ```python
    """Regression test for Phase 28 D-02: missing `test_code.generated_root` error."""
    from __future__ import annotations

    from pathlib import Path

    import pytest
    import yaml
    from typer.testing import CliRunner

    from mcp_test_framework.cli import app


    def _write_no_generated_root_config(tmp_path: Path) -> Path:
        cfg_path = tmp_path / "config.yaml"
        payload = {
            "version": 2,
            "mcp_server": {"command": "irrelevant", "args": []},
            "test_code": {},  # NO generated_root field
            "tools": {},
        }
        cfg_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
        return cfg_path


    def test_missing_generated_root_error_names_field_and_config_init(
        tmp_path: Path,
    ) -> None:
        """D-02: missing-`test_code.generated_root` error must name the field path
        AND point at `mcp-contracts config-init` for scaffold generation."""
        cfg_path = _write_no_generated_root_config(tmp_path)
        runner = CliRunner(mix_stderr=False)
        # `run` is the strict-config command; `gen-test-classes` also works but
        # `run` is the most common operator entry into this error path.
        result = runner.invoke(app, ["run", "--config", str(cfg_path)])

        # Combine stderr + stdout — operator-tone errors may emit on either.
        combined = result.stdout + (result.stderr or "")

        assert result.exit_code == 2, (
            f"expected exit 2 for missing required field; got {result.exit_code}.\n"
            f"output:\n{combined}"
        )
        # D-02 literal-string requirements:
        assert "test_code.generated_root" in combined, (
            "operator error must name the missing field by full path; got:\n" + combined
        )
        assert "mcp-contracts config-init" in combined, (
            "operator next-step must point at `mcp-contracts config-init`; got:\n" + combined
        )
        # Negative assertion: legacy CLI name must not appear in next-step copy.
        assert "mcp-test-framework config-init" not in combined, (
            "operator next-step must use canonical `mcp-contracts`, not the legacy "
            "v1.4-deprecated `mcp-test-framework` command name; got:\n" + combined
        )
    ```

    Step D — Run:

    ```
    uv run pytest tests/framework/unit/test_missing_generated_root_error.py -xvs
    uv run pytest tests/framework/ -x
    ```

    If the new test fails on the third assertion (legacy CLI name still present), Step B was incomplete — grep cli.py for `mcp-test-framework config-init` and flip remaining operator-facing next-step occurrences.

    If the new test fails on the second assertion (`mcp-contracts config-init` missing), confirm the edit landed in the exact branch the missing-field error takes. Use the live capture from Step A to identify which branch fires.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_missing_generated_root_error.py -xvs</automated>
  </verify>
  <acceptance_criteria>
    - tests/framework/unit/test_missing_generated_root_error.py exists with `def test_missing_generated_root_error_names_field_and_config_init`
    - That test passes: rendered error contains literals `test_code.generated_root` AND `mcp-contracts config-init`, and does NOT contain `mcp-test-framework config-init` in operator-facing next-step copy
    - Exit code from the failing-config CLI invocation is 2
    - src/mcp_test_framework/cli.py `_emit_operator_error_for_validation` missing-field branch: any operator-facing `mcp-test-framework config-init` next-step copy has been flipped to `mcp-contracts config-init` (verify with grep — there should be zero `mcp-test-framework config-init` occurrences inside next_step= bodies in cli.py after the patch)
    - `uv run pytest tests/framework/ -x` continues to pass (no regression — in particular `tests/framework/unit/test_error_style.py` and any source-text regression test pinning the v1->v2 migration message stays GREEN, since that branch is the version-mismatch branch, not the missing-field branch)
    - SUMMARY.md documents the audit result: which literal strings were found in pre-patch capture, and whether the patch was applied
  </acceptance_criteria>
  <done>
    - Audit captured live error text and compared against D-02 bar; rewrite applied if needed; regression test pins both required literals; no regression elsewhere in the framework suite.
  </done>
</task>

</tasks>

<verification>
- `uv run pytest tests/framework/unit/test_gen_test_classes_overwrite_prompt.py -x -v` exits 0
- `uv run pytest tests/framework/unit/test_missing_generated_root_error.py -xvs` exits 0
- `uv run pytest tests/framework/ -x` exits 0
- Grep confirms `_confirm_or_abort_non_empty_target` is defined once and called once from `gen_test_classes`
- `mcp-contracts gen-test-classes --help` text contains no `--yes` or `--force` token
- The call ordering in `gen_test_classes` is: load config → resolve out_root → site-packages guard → handshake → server-name check → slug derivation → confirm-or-abort → `_codegen.generate(...)`
- Grep `grep -n "mcp-test-framework config-init" src/mcp_test_framework/cli.py` returns zero matches inside any `next_step=` body (operator-facing copy uses the canonical `mcp-contracts` name)
</verification>

<success_criteria>
Non-empty target directory triggers a prompt in interactive contexts and an exit-2 abort in non-interactive contexts. No `--yes` / `--force` escape hatch. D-05 + D-06 satisfied. The "never silently destroy data" posture is intact. Missing-`test_code.generated_root` operator error names the field path and points at `mcp-contracts config-init` per D-02 (the operator's first contact with the fail-loud-on-missing-field path now speaks operator language end-to-end).
</success_criteria>

<output>
After completion, create `.planning/phases/28-codegen-output-path-codegen/28-03-SUMMARY.md` documenting:
- The helper signature and the five-branch decision tree (missing / empty / non-empty-tty-accept / non-empty-tty-decline / non-empty-non-tty)
- The wiring point in `gen_test_classes` (between slug derivation and `_codegen.generate`)
- The deliberate absence of `--yes` / `--force` (D-06 regression-tested)
- The file-count cap of 1000 (CONTEXT.md discretion: bounded scan cost)
- The D-02 audit result: which literals were found in pre-patch capture (`test_code.generated_root` / `mcp-contracts config-init` / `mcp-test-framework config-init`), and the diff applied to `_emit_operator_error_for_validation` if any
- Confirmation that the new regression test pins both required literals plus the legacy-name negative
</output>
</content>
</invoke>