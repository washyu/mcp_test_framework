# Phase 32: Surface-shim removals — Pattern Map

**Mapped:** 2026-05-24
**Files analyzed:** 6 plans × (1–3 source + 1 test + 1–8 doc) ≈ 35 file touch-points
**Analogs found:** 6 / 6 plans have a Phase 31 structural twin

## Phase 31 → Phase 32 Plan Twinning

| Phase 32 plan | Surface | Phase 31 analog | Why it's the closest match |
|---------------|---------|-----------------|----------------------------|
| 32-01 (SHIM-01 sdet package import) | Python import-time raise + pinned-text test | **31-01** (SHIM-04 sdet alias removal) | Same operator-tone D-02 verbatim message pattern; same "ADD pinned-text test in `tests/framework/unit/test_error_style.py`" shape; both target the `sdet` rename, just at different layers (Pydantic field vs Python import) |
| 32-02 (SHIM-02 `--sdet` flag) | Typer eager-callback flip + UsageError | **31-01** (cli.py dispatcher branch) + existing `_warn_sdet_flag` at `cli.py:645-658` | Existing callback skeleton already on the right shape; only the body flips from `warnings.warn` → `raise typer.BadParameter`. Pinned-text test mirrors 31-01 |
| 32-03 (SHIM-03 `gen-sdet-classes` command) | Typer hidden command body flip | **31-01** + existing `_gen_sdet_classes_shim` at `cli.py:1420-1438` | Decorator already `hidden=True`; only the body flips from `warnings.warn` + delegation → `raise typer.BadParameter`. Same regression-test pattern as 32-02 |
| 32-04 (SHIM-06 `tests/sdet/` discovery) | pytest hook warn-on-presence + dual-discovery strip + 26-marker scrub | **31-02** (SHIM-05 MCPTF_CONFIG_FILE) | **STRONGEST ANALOG.** 31-02 is the only Phase 31 plan that touched `_plugin.py:pytest_configure`, installed the scoped `[mcp-contracts]` formatwarning override, and did a multi-file noqa/docstring scrub with `_runner.py` / `fixtures.py` / `_reporter.py` ride-alongs. Inverted-test pattern reusable for the 5+ tests that consume the unprefixed YAML/path-list. |
| 32-05 (SHIM-07 unprefixed fixtures) | Fixture body flip from passthrough → `pytest.fail` | **31-02** (inverted regression test pattern) + 31-01 (operator-tone pin) | The fixture-body flip is structurally the same as the Typer-callback flip in 32-02: registration stays, body inverts. 31-02's "inverted regression test pattern" is the test playbook (the existing test files that consume `def test_X(config)` now invert in place to pin the absence). |
| 32-06 (SHIM-08 console-script) | Console-script trampoline body flip + doc sweep | **31-02** (multi-file doc scrub) + existing `_deprecated_script.py:main` | Body flip is one file (`_deprecated_script.py`); the dominant work is the doc sweep across README + ERROR-STYLE.md + EXTENDING.md + TEST-CODE-AUTHORING.md + mvp_spec.md — exactly the cross-doc scrub shape 31-02 ran for MCPTF_CONFIG_FILE. |

## File Classification

### 32-01 — SHIM-01 (sdet package import)

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/sdet/__init__.py` | shim source (module-load raise) | import-time-event | Phase 31 `config.py` deletions + the existing 26-line re-export shim itself | exact (same file, body inverts) |
| `tests/framework/unit/test_error_style.py` (extend) | regression test (pinned-text) | request-response (synth) | `test_error_style_sdet_rejection_message` (L98–138) | exact |
| `README.md` (scrub L166, L238, L244, L306, L307) | docs | static | Phase 31 README scrubs (31-02 .env.example / examples/homelab-mcp.yaml) | role-match |
| `docs/SDET-AUTHORING.md` (DELETE or one-line redirect) | docs | static | Phase 31 `docs/MIGRATION-v1-to-v2.md` deletion (Plan 31-04) | exact |

### 32-02 — SHIM-02 (`--sdet` Typer flag)

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/cli.py` (rewrite `_warn_sdet_flag` L645–658, edit option L735–742, delete coercion L786–790) | Typer eager-callback | request-response (CLI parse) | self (existing `_warn_sdet_flag` skeleton) + 31-01 dispatcher-branch shape | exact |
| `tests/framework/unit/test_error_style.py` (extend) | regression test | request-response | `test_error_style_sdet_rejection_message` (31-01) | exact |
| `README.md`, `docs/EXTENDING.md` (verify scrub) | docs | static | 31-02 cross-doc scrub | role-match |

### 32-03 — SHIM-03 (`gen-sdet-classes` Typer command)

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/cli.py` (rewrite `_gen_sdet_classes_shim` L1420–1438) | Typer hidden command | request-response | self (existing decorator skeleton) | exact |
| `tests/framework/unit/test_error_style.py` (extend) | regression test | request-response | `test_error_style_sdet_rejection_message` | exact |

### 32-04 — SHIM-06 (`tests/sdet/` discovery)

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/_plugin.py` (extend `pytest_collection` L255; refactor nested `_mcptf_formatwarning` L156–166 → module-level) | pytest plugin hook | event-driven (collection) | 31-02's `pytest_configure` env-var detector L148–183 | exact (same file, same plugin) |
| `src/mcp_test_framework/_runner.py` (strip dual-discovery: 21 marker sites listed in RESEARCH §SHIM-06; rename kwarg `sdet`→`test_code`) | service / argv assembly | batch | 31-02 `_runner.py` config-path thread + helper relocate | exact |
| `src/mcp_test_framework/fixtures.py` (4 marker sites; docstring scrub) | fixture body | request-response | 31-02 fixtures.py docstring scrub (mcp_config / _preflight) | exact |
| `src/mcp_test_framework/_reporter.py` (1 marker site, L219 comment) | reporter / detection | event-driven | 31-02 plugin scrubs | role-match |
| `src/mcp_test_framework/_black_box_guard.py` (DELETE noqa marker L10, PRESERVE prose) | doctrinal source | static | none — surgical one-line edit (no analog needed) | partial |
| `tests/framework/unit/test_plugin_tests_sdet_warning.py` (CREATE) | regression test (`pytester`) | event-driven | 31-02 `test_plugin_mcptf_config_file_deprecation.py` (created in 31-02) | exact |
| `tests/sdet/` (DELETE on-disk dir cleanup) | dead code | static | n/a — ride-along cleanup | partial |

### 32-05 — SHIM-07 (unprefixed fixtures)

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/_plugin.py` (rewrite 6 fixtures L433–502; update docstring L12) | fixture body (stub-raise) | event-driven | 31-02 `_plugin.py` warn-block rewrite | exact (same file, same plugin) |
| `tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py` (CREATE) | regression test (parametrized `pytester`) | event-driven | 31-02's parametrized `test_phase_31_mcptf_config_file_scrub.py` | exact |
| In-tree tests consuming `def test_X(config, …)` (audit + rename) | test rename sweep | static | 31-02's 8-test in-place inversion sweep | exact |

### 32-06 — SHIM-08 (`mcp-test-framework` console-script)

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/_deprecated_script.py` (rewrite full file) | console-script trampoline | request-response (process boot) | self (current 33-line warn+delegate body) | exact (same file, body inverts) |
| `pyproject.toml` L25 (KEEP entry, no edit) | config | static | n/a — preservation, not modification | n/a |
| `README.md` (scrub L423–425) | docs | static | 31-02 README/EXTENDING scrub | exact |
| `docs/ERROR-STYLE.md` (scrub L3 + L54 leak inside locked message block) | docs (with care for locked blocks) | static | 31-02 examples/homelab-mcp.yaml header rewrite | role-match |
| `docs/EXTENDING.md` (10 sites L22, L33, L39, L52, L60, L82, L213, L216, L218, L280) | docs (shell-command examples) | static | 31-02 multi-doc scrub | exact |
| `docs/TEST-CODE-AUTHORING.md` (3 sites L17, L18, L36) | docs | static | 31-02 docs scrub | exact |
| `docs/mcp_test_framework_mvp_spec.md` (5 sites L235–237, L276–277 — historical doc, planner decides) | docs (historical) | static | 31-02 .env.example header decision | partial |
| `tests/framework/unit/test_console_script_removed.py` (CREATE) | regression test (subprocess) | request-response (process boot) | 31-02 `test_plugin_mcptf_config_file_deprecation.py` (subprocess invoke pattern) | role-match |

---

## Pattern Assignments

### Shared canonical pattern: `_emit_operator_error` import + three-part shape

**Source:** `src/mcp_test_framework/_runner.py` L52–79

This helper is the **post-Phase-31 verified canonical emit path**. Every Phase 32 plan that can raise `typer.Exit` calls it; every Phase 32 plan that CANNOT (import-time, fixture-time, bare-script) uses the same three-part text shape inside its own exception.

**Helper body (verbatim from `_runner.py` L52–79 — read but DO NOT modify):**

```python
def _emit_operator_error(
    summary: str,
    detail: list[str],
    next_step: str,
    *,
    exit_code: int = 2,
) -> typing.NoReturn:
    """Render an operator-grade error and exit (see docs/ERROR-STYLE.md).

    This function never returns; it raises typer.Exit internally. Callers
    MUST NOT prefix calls with `raise`.

    Format (per docs/ERROR-STYLE.md):
        <one-line summary>
        <blank>
        <detail line 1>
        <detail line 2>
        ...
        <blank>
        next: <action verb> <command-or-instruction>
    """
    parts: list[str] = [summary, ""]
    parts.extend(detail)
    parts.extend(["", f"next: {next_step}"])
    typer.echo("\n".join(parts), err=True)
    raise typer.Exit(code=exit_code)
```

**Canonical import for any plan that can use `typer.Exit`:**

```python
from mcp_test_framework._runner import _emit_operator_error
```

**For import-time / fixture-time / bare-script sites** (32-01, 32-05, 32-06): cannot raise `typer.Exit` cleanly — instead, format the three parts inline into the exception message string, preserving the `<summary>\n\n<detail>\n\n next: <next_step>` shape.

---

### 32-01 — SHIM-01 (sdet package import)

**Analog:** Plan 31-01 (pinned-text test) + the file itself (current shim body inverts).

**Current shim body to invert** (full file `src/mcp_test_framework/sdet/__init__.py` lines 1–25):

```python
"""Back-compat shim — re-exports the public surface from mcp_test_framework.test_code."""
from __future__ import annotations

import warnings

warnings.warn(  # noqa: sdet-rename-shim
    "mcp_test_framework.sdet is deprecated since v1.4 and will be removed in v1.5 — "
    "use mcp_test_framework.test_code instead.",
    DeprecationWarning,
    stacklevel=2,
)

from mcp_test_framework.test_code import (  # noqa: sdet-rename-shim, E402
    ToolCallError,
    ToolResponse,
    mcp_session,
    tool,
)

__all__ = ["ToolCallError", "ToolResponse", "mcp_session", "tool"]
```

**Target body shape** (from `32-RESEARCH.md` §SHIM-01 — adapt to ERROR-STYLE.md three-part text):

```python
# noqa: sdet-rename-shim  -- this marker stays alongside the surviving stub
"""mcp_test_framework.sdet removal stub — raises on import."""
from __future__ import annotations

raise ModuleNotFoundError(
    "mcp_test_framework.sdet was removed in v1.5\n"
    "\n"
    "the `mcp_test_framework.sdet` import surface was renamed to "
    "`mcp_test_framework.test_code` in v1.4 and removed in v1.5.\n"
    "every public symbol (ToolCallError, ToolResponse, mcp_session, tool) "
    "is re-exported unchanged from the new location.\n"
    "\n"
    "next: replace `from mcp_test_framework.sdet import X` with "
    "`from mcp_test_framework.test_code import X` in your tests."
)
```

**Pinned-text test pattern** (copy from `tests/framework/unit/test_error_style.py` L98–138 — `test_error_style_sdet_rejection_message`):

```python
def test_error_style_sdet_package_removed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Phase 32 SHIM-01: importing mcp_test_framework.sdet raises
    ModuleNotFoundError with operator-tone three-part text pointing
    at mcp_test_framework.test_code. Future drift breaks this test."""
    import importlib
    import sys

    # Force a fresh import even if the module was previously cached.
    sys.modules.pop("mcp_test_framework.sdet", None)
    with pytest.raises(ModuleNotFoundError) as exc_info:
        importlib.import_module("mcp_test_framework.sdet")
    msg = str(exc_info.value)
    assert "mcp_test_framework.sdet was removed in v1.5" in msg
    assert "mcp_test_framework.test_code" in msg
    assert "next:" in msg
```

---

### 32-02 — SHIM-02 (`--sdet` Typer flag)

**Analog:** Existing `_warn_sdet_flag` callback at `cli.py:645–658` (skeleton already correct — only body flips).

**Current callback to invert** (`src/mcp_test_framework/cli.py` L645–658):

```python
def _warn_sdet_flag(value: bool) -> bool:  # noqa: sdet-rename-shim
    """Eager Typer/Click callback that emits the --sdet -> --test-code
    deprecation warning during option parsing, BEFORE --help short-circuits
    the command body. Fires once per process via Python's default filter.
    """
    if value:
        import warnings
        warnings.warn(
            "--sdet is deprecated since v1.4 and will be removed in v1.5 — "
            "use --test-code instead.",
            DeprecationWarning,
            stacklevel=2,
        )
    return value
```

**Target callback body** (from RESEARCH §SHIM-02 — rename to `_sdet_flag_removed`):

```python
def _sdet_flag_removed(value: bool) -> bool:  # noqa: sdet-rename-shim
    """Eager callback that hard-rejects --sdet with an operator-tone pointer
    to --test-code. Replaces the v1.4 _warn_sdet_flag DeprecationWarning."""
    if value:
        raise typer.BadParameter(
            "--sdet was removed in v1.5\n"
            "\n"
            "the `--sdet` flag was renamed to `--test-code` in v1.4 and "
            "removed in v1.5.\n"
            "every behavior is unchanged — only the flag spelling moved.\n"
            "\n"
            "next: pass `--test-code` instead of `--sdet` to `mcp-contracts run`."
        )
    return value
```

**Option registration stays** (`cli.py:735–742` — update `help=`, keep `hidden=True` + `is_eager=True`, repoint `callback=` to the renamed function):

```python
sdet_legacy: bool = typer.Option(  # noqa: sdet-rename-shim
    False,
    "--sdet",
    hidden=True,
    help="Removed in v1.5; use --test-code (this flag raises if passed).",
    callback=_sdet_flag_removed,
    is_eager=True,
),
```

**Scrub:** delete the `if sdet_legacy: test_code = True` coercion block (cli.py L786–790). The eager callback fires BEFORE the body, so the coercion is dead code.

**Regression test pattern** (mirror 31-01's `capsys` shape, drive via Typer's `CliRunner` — adapt from existing test file):

```python
def test_error_style_sdet_flag_removed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Phase 32 SHIM-02: --sdet raises typer.BadParameter with operator-tone
    text pointing at --test-code."""
    from typer.testing import CliRunner
    from mcp_test_framework.cli import app

    result = CliRunner(mix_stderr=False).invoke(app, ["run", "--sdet"])
    assert result.exit_code == 2
    combined = (result.stdout or "") + (result.stderr or "")
    assert "--sdet was removed in v1.5" in combined
    assert "--test-code" in combined
    assert "next:" in combined
```

---

### 32-03 — SHIM-03 (`gen-sdet-classes` Typer command)

**Analog:** Existing `_gen_sdet_classes_shim` at `cli.py:1420–1438` (decorator already correct; body inverts).

**Current body to invert** (`cli.py` L1420–1438):

```python
@app.command("gen-sdet-classes", hidden=True)  # noqa: sdet-rename-shim
def _gen_sdet_classes_shim(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Path to a YAML config (overrides ./config.yaml autodiscovery).",
    ),
) -> None:
    """Deprecated alias for `gen-test-classes` -- removed in v1.5."""
    import warnings
    warnings.warn(
        "gen-sdet-classes is deprecated since v1.4 and will be removed in v1.5 — "
        "use gen-test-classes instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    gen_test_classes(config=config)
```

**Target body** (from RESEARCH §SHIM-03 — drop delegation; raise `typer.BadParameter`):

```python
@app.command("gen-sdet-classes", hidden=True)  # noqa: sdet-rename-shim — stub for v1.5
def _gen_sdet_classes_removed(
    config: Path | None = typer.Option(None, "--config", hidden=True),
) -> None:
    """Removed in v1.5 — see error message."""
    raise typer.BadParameter(
        "gen-sdet-classes was removed in v1.5\n"
        "\n"
        "the `gen-sdet-classes` command was renamed to `gen-test-classes` "
        "in v1.4 and removed in v1.5.\n"
        "every flag is unchanged — only the command name moved.\n"
        "\n"
        "next: invoke `mcp-contracts gen-test-classes` (same flags)."
    )
```

**Regression test pattern:** same `CliRunner` shape as 32-02; invoke `["gen-sdet-classes"]`; assert exit 2 + `"gen-test-classes"` in combined output.

---

### 32-04 — SHIM-06 (`tests/sdet/` discovery)

**Primary analog:** Plan 31-02 `pytest_configure` env-var detector at `_plugin.py:148–183` (THIS IS THE LOAD-BEARING ANALOG for the warn-on-presence + formatwarning override).

**Phase 31 scoped-formatwarning pattern to extend** (`src/mcp_test_framework/_plugin.py` L148–183):

```python
# Emit DeprecationWarning if MCPTF_CONFIG_FILE is set in env.
#
# NOTE for the future EOL planner: this MCPTF_CONFIG_FILE detection is
# grandfathered in src/ for v1.5; planned removal lands in v1.6
# alongside the other operator-facing env-var removals.
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
            "MCPTF_CONFIG_FILE is set in your environment but"
            " no longer honored as of v1.5;"
            " configure via `[tool.pytest.ini_options]"
            " mcp_config_file = PATH` in pyproject.toml or pass"
            " `--config PATH` to `mcp-contracts run`.",
            DeprecationWarning,
            stacklevel=2,
        )
    finally:
        warnings.formatwarning = _original_formatwarning
```

**Apply to 32-04** (per RESEARCH §SHIM-06):

1. **Refactor** `_mcptf_formatwarning` from nested inside `pytest_configure` → module-level helper inside `_plugin.py`. Both call sites (the existing MCPTF_CONFIG_FILE one + the new `tests/sdet/` one) import the same helper. This is a small ride-along scoped to 32-04's already-in-scope file.

2. **Add a new warn-on-presence block** inside `pytest_collection` (L255 — already exists in `_plugin.py`). Body shape per RESEARCH §SHIM-06:

```python
def pytest_collection(session: pytest.Session) -> None:
    """... existing docstring ..."""
    # ... existing body ...

    # tests/sdet/ is no longer auto-discovered as of v1.5; this detector
    # survives the surface removal so operators mid-migration see a loud
    # signal. Planned removal: v1.6 capstone.
    legacy_dir = session.config.rootpath / "tests" / "sdet"
    if legacy_dir.is_dir() and any(legacy_dir.glob("test_*.py")):
        _original_formatwarning = warnings.formatwarning
        warnings.formatwarning = _mcptf_formatwarning  # module-level helper
        try:
            warnings.warn(
                "tests/sdet/ is no longer auto-discovered as of v1.5\n"
                "\n"
                "the `tests/sdet/` directory contains test_*.py files but is "
                "no longer collected by `mcp-contracts run --test-code`.\n"
                "every scenario should live under `tests/test_code/`; the "
                "two layouts are otherwise identical.\n"
                "\n"
                "next: move your `tests/sdet/test_*.py` files to "
                "`tests/test_code/` and re-run.",
                DeprecationWarning,
                stacklevel=2,
            )
        finally:
            warnings.formatwarning = _original_formatwarning
```

**Dual-discovery strip pattern** (mirror Plan 31-02's `_runner.py` config-path threading — strip the `sdet=` kwarg branch from `_build_pytest_args` and caller chain). All 21 marker sites in `_runner.py` enumerated in RESEARCH §SHIM-06 file-table. Rename kwarg `sdet`→`test_code` end-to-end (the CLI surface that fed it is dead after 32-02).

**Marker scrub pattern** (mirror Plan 31-01 §Action step 5):

```bash
# For each file in the SHIM-06 touch list:
grep -n 'sdet-rename-shim' <file>
# Remove every line carrying the marker (the noqa directives go with the deleted code).
# EXCEPTION: _black_box_guard.py L10 — DELETE the marker but PRESERVE the prose
# (SEED-022 doctrinal reference, NOT a v1.4 shim).
```

**Plugin regression test pattern** — adapt from 31-02's `tests/framework/unit/test_plugin_mcptf_config_file_deprecation.py` (created in Plan 31-02 per its frontmatter `key-files.created`). Use `pytester` to create a fake `tests/sdet/test_x.py` inside a tmp project, run pytest, assert `[mcp-contracts]`-prefixed DeprecationWarning fires with `tests/test_code/` in the text.

---

### 32-05 — SHIM-07 (unprefixed fixtures)

**Analog:** The current fixture bodies at `_plugin.py:433–502` (skeleton stays; bodies invert). Test pattern from RESEARCH §SHIM-07 + 31-02's parametrized regression-guard idiom.

**Current fixture body to invert** (one of six — same shape for all; `_plugin.py:433–442`):

```python
@pytest.fixture(scope="session")
def config(mcp_config):
    """Deprecated alias for `mcp_config` — removed in v1.5."""
    warnings.warn(
        "the `config` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_config` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_config
```

**Target body shape** (from RESEARCH §SHIM-07 — **CRITICAL: drop the prefixed-fixture parameter**, per Pitfall 1):

```python
@pytest.fixture(scope="session")
def config():  # noqa: sdet-rename-shim — NB: dropped mcp_config parameter
    """Removed in v1.5 — use mcp_config instead."""
    pytest.fail(
        "the `config` fixture was removed in v1.5\n"
        "\n"
        "the `config` fixture was renamed to `mcp_config` in v1.4 and "
        "removed in v1.5.\n"
        "the fixture body, scope, and return value are unchanged — only "
        "the name moved.\n"
        "\n"
        "next: rename `config` to `mcp_config` in your test signature "
        "(e.g. `def test_X(mcp_config): ...`).",
        pytrace=False,
    )
```

Apply symmetrically to all six aliases (`config`/`judge`/`target_tool`/`rubric_clarity`/`rubric_disambiguation`/`rubric_parameters`).

**Plugin docstring scrub** (`_plugin.py:7-16` — update "Six unprefixed deprecation aliases" → "Six removal stubs").

**Parametrized regression test pattern** (from RESEARCH §SHIM-07 — mirror 31-02's `test_phase_31_mcptf_config_file_scrub.py` parametrize idiom):

```python
@pytest.mark.parametrize("legacy,prefixed", [
    ("config", "mcp_config"),
    ("judge", "mcp_judge"),
    ("target_tool", "mcp_target_tool"),
    ("rubric_clarity", "mcp_rubric_clarity"),
    ("rubric_disambiguation", "mcp_rubric_disambiguation"),
    ("rubric_parameters", "mcp_rubric_parameters"),
])
def test_unprefixed_fixture_removed(pytester, legacy, prefixed):
    pytester.makepyfile(f"def test_x({legacy}): pass")
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines([f"*{prefixed}*", "*next:*"])
```

**In-tree test-rename audit pattern** (mirror 31-02 §Deviation 1 inverted-test pattern — Plan 31-02 updated 8 test files in place to consume the new surface). Sweep:

```bash
# Find any framework self-tests still consuming the unprefixed names:
grep -rn 'def test.*\b\(config\|judge\|target_tool\|rubric_\(clarity\|disambiguation\|parameters\)\)\b' tests/
# Rename in place to mcp_-prefixed equivalents.
```

---

### 32-06 — SHIM-08 (`mcp-test-framework` console-script)

**Analog:** Current `_deprecated_script.py:main` (skeleton stays; body inverts) + Plan 31-02's multi-doc scrub pattern.

**Current body to invert** (`src/mcp_test_framework/_deprecated_script.py` full file, 33 lines):

```python
"""mcp-test-framework console-script deprecation shim.

The console-script `mcp-test-framework` is retained for v1.4 as a back-compat
entry point. It emits a single DeprecationWarning on first process call and
then dispatches to the same Typer `app` the new `mcp-contracts` script
targets.

Removed in v1.5 alongside every other v1.4 deprecation shim.
"""
from __future__ import annotations

import warnings


def main() -> None:
    """Console-script entry point — warn once then delegate to cli:app."""
    warnings.warn(
        "mcp-test-framework command is deprecated since v1.4 and will be removed in v1.5 — "
        "use mcp-contracts instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from mcp_test_framework.cli import app
    app()
```

**Target body** (from RESEARCH §SHIM-08 — bare-script does NOT use `typer.Exit`; uses `print` + `sys.exit(2)` per Pitfall 5):

```python
"""mcp-test-framework console-script removal stub — v1.5."""
from __future__ import annotations

import sys


def main() -> None:
    """Console-script entry point — hard-rejects and points at mcp-contracts."""
    msg = (
        "[mcp-contracts] mcp-test-framework was removed in v1.5\n"
        "\n"
        "the `mcp-test-framework` console-script was renamed to "
        "`mcp-contracts` in v1.4 and removed in v1.5.\n"
        "every subcommand and every flag is unchanged — only the script "
        "name moved.\n"
        "\n"
        "next: invoke `mcp-contracts` instead of `mcp-test-framework` "
        "(same args).\n"
    )
    print(msg, file=sys.stderr)
    sys.exit(2)
```

**`pyproject.toml` `[project.scripts]` block STAYS UNCHANGED** (`pyproject.toml:24-25`):

```toml
mcp-contracts = "mcp_test_framework.cli:app"
mcp-test-framework = "mcp_test_framework._deprecated_script:main"
```

Removing the entry would degrade the operator UX to a shell-level "command not found" with zero pointer to `mcp-contracts` (per D-07 rationale).

**Multi-doc scrub pattern** (mirror Plan 31-02's `.env.example` + `examples/homelab-mcp.yaml` + 7 test-file scrub):

```bash
# Per doc file, sweep for `mcp-test-framework` and replace with `mcp-contracts`.
# Then verify zero residual mentions:
grep -rn 'mcp-test-framework' docs/ README.md
# Acceptable residuals: only inside _deprecated_script.py module docstring
# (the literal name must appear so operators searching the source find the stub).
```

**Bonus fix flagged in RESEARCH §Pitfall 4:** `docs/ERROR-STYLE.md` L54 cites `mcp-test-framework config-init` inside a LOCKED reference message (the "No config found" block L46–55). Plan 31-03 updated the adjacent v1-rejection block (L57–65) but missed this one. Plan 32-06 fixes it.

**Subprocess regression-test pattern** (per RESEARCH §SHIM-08):

```python
def test_console_script_removed():
    """Phase 32 SHIM-08: invoking the legacy console-script exits 2 with
    operator-tone text pointing at mcp-contracts."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-c",
         "from mcp_test_framework._deprecated_script import main; main()"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "mcp-test-framework was removed in v1.5" in result.stderr
    assert "mcp-contracts" in result.stderr
    assert "next:" in result.stderr
```

---

## Shared Patterns

### Pattern S-01: Three-part operator-tone text shape (ERROR-STYLE.md contract)

**Source:** `docs/ERROR-STYLE.md` (canonical contract) + Plan 31-01 D-02 verbatim wording.
**Apply to:** All six Phase 32 migration messages.

```
<legacy surface> was removed in v1.5

<the legacy thing> was renamed to <new thing> in v1.4 and removed in v1.5.
<one-line description of what's unchanged about behavior>.

next: <imperative action verb> <concrete instruction>
```

**Phase 31 reference wording (Plan 31-01 D-02 — operator-approved):**

```
unknown config key: sdet

the `sdet:` key was renamed to `test_code:` in v1.4 and removed in v1.5.
your existing block under `sdet:` ports forward unchanged -- just rename the top-level key.

next: rename the `sdet:` key to `test_code:` in your config.yaml
```

Each Phase 32 plan picks its own summary / detail / next_step text (RESEARCH §"Operator-Tone Error Texture" table) — wording in PATTERNS.md and CONTEXT.md is the source of truth; the planner is operator-author for these strings.

### Pattern S-02: Pinned-text regression test in `tests/framework/unit/test_error_style.py`

**Source:** `tests/framework/unit/test_error_style.py:98-138` (`test_error_style_sdet_rejection_message` — Plan 31-01 Task 3).
**Apply to:** Plans 32-01, 32-02, 32-03 (sites whose error fires through Typer or import paths and renders to stdout/stderr).

Shape: arrange minimal trigger → catch `typer.Exit` or `ModuleNotFoundError` → `capsys.readouterr()` → assert each verbatim D-style substring is in `captured.out + captured.err`. Future text drift breaks the test by design.

### Pattern S-03: `pytester`-driven plugin regression test

**Source:** `tests/framework/unit/test_plugin_mcptf_config_file_deprecation.py` (created in Plan 31-02 per its frontmatter).
**Apply to:** Plans 32-04 (warn-on-presence collection hook) and 32-05 (fixture-resolution failure).

Shape: `pytester.makepyfile(...)` to synthesize a test that triggers the surface → `pytester.runpytest()` → assert outcomes + `result.stdout.fnmatch_lines([...])` for operator-tone substrings.

### Pattern S-04: `# noqa: sdet-rename-shim` marker scrub-with-the-code

**Source:** Plan 31-01 Action step 5 + Plan 31-02 marker scrub across config.py / cli.py / _plugin.py.
**Apply to:** All six Phase 32 plans — each plan scrubs the markers grandfathering its surface.

Rule: every `# noqa: sdet-rename-shim` exists because the line it guards is a v1.4 deprecation shim. When the shim dies, the marker dies. The single grandfathered exception is the `sdet/__init__.py` module-level marker that survives Phase 32 to grandfather the directory through v1.5 (deleted at v1.6 capstone). The misapplied marker in `_black_box_guard.py:10` is deleted in 32-04 with the surrounding SEED-022 prose preserved.

### Pattern S-05: Scoped `warnings.formatwarning` override with try/finally restore

**Source:** `src/mcp_test_framework/_plugin.py:148-183` (Plan 31-02 D-08).
**Apply to:** Plan 32-04 (refactor nested → module-level, share between MCPTF_CONFIG_FILE and `tests/sdet/` warn sites).

Verbatim helper to relocate from nested → module-level (see 32-04 section above).

### Pattern S-06: Inverted regression-test rewrite-in-place

**Source:** Plan 31-02 Deviation 1 + frontmatter `patterns-established` entry.
**Apply to:** Plan 32-05 (in-tree tests that consume the unprefixed fixture names) and any 32-04 test that previously pinned the dual-discovery `tests/sdet/` behavior.

Rule: when a deprecated code path is deleted, the test that pinned it is rewritten IN PLACE with the inverted assertion and a renamed function (e.g. `test_env_var_still_works` → `test_env_var_no_longer_routed`). The test's existence remains a maintenance-time tripwire; deleting it would lose coverage of the post-removal invariant.

### Pattern S-07: Neutral-English in-source comments (no planning IDs)

**Source:** Plan 31-02 Deviation 2 — `no_planning_ids_in_src` leak guard (`tests/framework/unit/test_no_planning_ids_in_src.py`).
**Apply to:** ALL six Phase 32 plans — any in-source comment must use neutral English (`v1.5`, `v1.6`, `future EOL planner`); banned: `Phase \d`, `Plan \d-\d`, `[A-Z]{2,}-\d{2}` (matches `SHIM-01`, `D-03`, etc.).

This is a HARD GATE — the test in `tests/framework/unit/test_no_planning_ids_in_src.py` fires on any leak. Plan 31-02 caught this post-hoc and required a fix-up commit (`d891c66`). Phase 32 plans bake compliance in from the first commit.

---

## No Analog Found

All six Phase 32 plans have at least one strong Phase 31 analog. The only file with no analog is `_black_box_guard.py` for the single-marker scrub at L10 — but this is a one-line surgical edit (delete the misapplied `# noqa: sdet-rename-shim` marker, preserve the SEED-022 prose) and needs no pattern; it's described directly in RESEARCH §Pitfall 2.

---

## Metadata

**Analog search scope:**
- `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/` (all 6 plan files + 6 summary files + CONTEXT/RESEARCH/DISCUSSION-LOG)
- `src/mcp_test_framework/sdet/__init__.py`
- `src/mcp_test_framework/_runner.py` (L1–90 for `_emit_operator_error`)
- `src/mcp_test_framework/_plugin.py` (L1–30 docstring; L140–230 pytest_configure; L420–510 unprefixed fixtures)
- `src/mcp_test_framework/_deprecated_script.py` (full file)
- `src/mcp_test_framework/cli.py` (L640–750 Typer flag block; L1410–1450 gen-sdet-classes command)
- `tests/framework/unit/test_error_style.py` (L90–139 for the Plan 31-01 pinned-text test pattern)
- `pyproject.toml` (L15–37 `[project.scripts]` + `[project.entry-points.pytest11]`)

**Files scanned:** 9 source / config + 8 planning artifacts.
**Pattern extraction date:** 2026-05-24

---

*Phase: 32-Surface-shim removals — CLI + package + fixtures + discovery*
*Pattern mapping completed: 2026-05-24*
