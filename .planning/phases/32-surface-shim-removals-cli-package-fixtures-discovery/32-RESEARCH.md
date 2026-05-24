# Phase 32: Surface-shim removals — CLI + package + fixtures + discovery - Research

**Researched:** 2026-05-24
**Domain:** Operator-surface deprecation-shim removal (Python package import / Typer CLI / pytest plugin / fixtures / console-script)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** 1:1 per SHIM — **six plans, six commits**. Plans 32-01 (SHIM-01), 32-02 (SHIM-02), 32-03 (SHIM-03), 32-04 (SHIM-06), 32-05 (SHIM-07), 32-06 (SHIM-08).
- **D-02:** Internal plan-execution order is interchangeable; canonical numeric 01→06.
- **D-03 (SHIM-01):** Keep `src/mcp_test_framework/sdet/__init__.py` as a **hard-raise migration shim**, not a clean delete. Raises `ModuleNotFoundError`/`ImportError` with operator-tone three-part message naming `mcp_test_framework.test_code`.
- **D-04 (SHIM-02/03):** Register `--sdet` flag and `gen-sdet-classes` command as **hidden Typer intercepts** that raise `typer.BadParameter` / `typer.UsageError` naming `--test-code` / `gen-test-classes`.
- **D-05 (SHIM-06):** **Loud collection-time detection** — warn (not hard-fail) on `tests/sdet/` presence; pointer at `tests/test_code/`. Strip the dual-discovery fallback so the path is no longer collected.
- **D-06 (SHIM-07):** **Stub-raise fixtures**, not clean delete. The six unprefixed fixture names stay registered; bodies raise immediately with operator-tone message naming the `mcp_*`-prefixed equivalent.
- **D-07 (SHIM-08):** Keep `[project.scripts] mcp-test-framework = "..._deprecated_script:main"` entry; convert `_deprecated_script.py:main()` to **hard-raise** that prints operator-tone three-part message and exits with code 2.
- **D-08:** Shared helper — research outcome (see below): Phase 31 did NOT extract a separate `_operator_errors.py`; the shared emit helper `_emit_operator_error(...)` lives in `src/mcp_test_framework/_runner.py` L52-79 (moved there in pre-Phase-31 work to break a circular import). All six Phase 32 plans import that.
- **D-09:** Each Phase 32 plan ships its own positive test under `tests/framework/unit/` asserting (a) the legacy surface raises/fails with the expected operator-tone message and (b) the post-v1.4 replacement still works end-to-end.

### Claude's Discretion

- Plan-execution order within the phase (canonical 01→06 recommended; research surfaced no coupling that forces a different order).
- Choice of exception subclass within the constraints above (e.g., `ModuleNotFoundError` vs `ImportError`; `pytest.fail` vs `pytest.UsageError` for fixture bodies) — research recommendations below; planner finalizes.
- Whether plan 32-01 also extracts `_emit_operator_error` to a new module or all six plans simply import from `_runner`.

### Deferred Ideas (OUT OF SCOPE)

- **v1.6 capstone clean-deletion** of every surface this phase grandfathers (the `sdet/` directory, the two hidden Typer intercepts, the six stub-raise fixtures, the `_deprecated_script.py` + its `[project.scripts]` entry, the `tests/sdet/` warn-on-presence detector in `_plugin.py`). Phase 35 SHIM-09 regression gate must grandfather all of those for v1.5.
- `docs/MIGRATION-v1-to-v2.md`-style archival of the v1.4→v1.5 shim retirement story (capture as `CHANGELOG.md` / `MILESTONES.md` footnote).
- Phase 35 SHIM-09 grandfathering list construction (forward to Phase 35 planner).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHIM-01 | `from mcp_test_framework.sdet import ...` raises `ModuleNotFoundError` with operator-tone message pointing at `mcp_test_framework.test_code` | §SHIM-01 below: confirmed module-load-time raise fires eagerly on every Python 3.14 import form (PEP 690 rejected; PEP 810 explicit opt-in only — neither active by default). |
| SHIM-02 | `--sdet` flag removed; UsageError points at `--test-code` | §SHIM-02 below: Typer 0.25 `hidden=True` + eager `BadParameter` callback pattern; current code at `cli.py` L735–742 is already on this shape. |
| SHIM-03 | `gen-sdet-classes` CLI command removed; UsageError points at `gen-test-classes` | §SHIM-03 below: `@app.command("gen-sdet-classes", hidden=True)` already exists at `cli.py` L1420; flip body to raise `typer.BadParameter` / call `_emit_operator_error`. |
| SHIM-06 | `tests/sdet/` no longer auto-discovered; clean removal of DeprecationWarning | §SHIM-06 below: warn-on-presence at `pytest_collection` (extend existing hook at `_plugin.py` L255), strip dual-discovery branches at `_runner.py` L134–143 + L608/L619 + L797/L803 + L1271/L1285, scrub all 26 `# noqa: sdet-rename-shim` markers across `_runner.py` / `fixtures.py` / `_reporter.py` / `_black_box_guard.py`. |
| SHIM-07 | Unprefixed fixtures (`config`, `judge`, `target_tool`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`) fail at fixture-resolution time with the prefixed names surfaced | §SHIM-07 below: there are **SIX** aliases at `_plugin.py` L433–502, NOT four. CONTEXT.md SC#4 naming is incomplete (mentions `client` which is not actually aliased; doesn't mention the three rubric aliases). `pytest.fail(reason=..., pytrace=False)` is the chosen mechanism — guarantees the message appears with the failing fixture's name in the trace. |
| SHIM-08 | Legacy `mcp-test-framework` console-script removed | §SHIM-08 below: `_deprecated_script.py:main()` rewritten to print operator-tone message via stderr and `sys.exit(2)`. Exit code 2 confirmed — no existing test pins another value. |

</phase_requirements>

## Summary

Phase 32 deletes the six v1.4-introduced `sdet`-flavored surface shims with **mechanically orthogonal removals across six surfaces** (package import / Typer flag / Typer command / pytest discovery / pytest fixtures / console-script). The phase decomposition (1:1 per SHIM, six plans, six commits) is **locked** — research does not relitigate it; instead it resolves the six RESEARCH-FOR-PLAN flags embedded in D-03..D-08 so each plan has concrete, evidence-backed mechanics.

**The single most load-bearing research finding:** Phase 31 did NOT extract a separate `_operator_errors.py` module. The shared three-part emit helper `_emit_operator_error(summary=, detail=, next_step=, *, exit_code=2)` lives in `src/mcp_test_framework/_runner.py` L52–79 (moved there to break the cli.py↔_runner.py circular import). All six Phase 32 plans should import it directly from `_runner`, not from `cli` (cli re-exports it but `from mcp_test_framework._runner import _emit_operator_error` is the canonical path used by cli.py L243's dispatcher itself). No extraction work is needed in plan 32-01.

**Primary recommendation:** Each plan stays narrowly on its single surface (per CONTEXT.md memory `feedback_phase_scope_intent`); each plan imports `_emit_operator_error` from `_runner` directly; each plan scrubs the `# noqa: sdet-rename-shim` markers grandfathering its surface in the same commit; each plan ships a positive regression test under `tests/framework/unit/` pinning the operator-tone message text verbatim (mirroring Plan 31-01's `test_error_style_sdet_rejection_message` pattern); and each plan sweeps the doc surfaces for surviving mentions of its surface in the same commit.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| sdet package import surface | Python import system | — | `__init__.py` module body fires at import; native exception channel. |
| `--sdet` flag intercept | Typer / Click option callback | — | Eager `callback=` fires during argv parsing, before command body. Same surface that already warns today. |
| `gen-sdet-classes` command intercept | Typer command registration | — | `@app.command(..., hidden=True)` decorator; body raises instead of delegating. |
| `tests/sdet/` discovery detection | pytest plugin hook (`pytest_collection`) | `_runner.py` argv assembly | Plugin reports the situation to the operator; runner strips the dual-discovery branch from pytest argv (independent surface). |
| Unprefixed fixture aliases | pytest fixture system (plugin-registered) | — | Fixtures stay registered (so pytest's resolver finds them by name); body raises. |
| `mcp-test-framework` console-script | Python entry-point trampoline | — | `[project.scripts]` invokes `_deprecated_script:main()` directly; main() raises instead of delegating. |

All six tiers are independent. No cross-tier coupling. Plans can land in any order.

## Per-SHIM Research Findings

### SHIM-01 — `mcp_test_framework.sdet` package import (D-03)

**Mechanism (recommended): raise `ModuleNotFoundError` at module body, eagerly.**

**Why ModuleNotFoundError (not ImportError):** `ModuleNotFoundError` is a subclass of `ImportError` and is the exception Python's import machinery itself raises for a missing module. SHIM-01's success-criterion text mandates `ModuleNotFoundError`. Raising it preserves `except ImportError:` compatibility for any operator code defensively guarding the import, while also matching Python's own surface for the same operator perception ("the module is gone"). `[VERIFIED: REQUIREMENTS.md SHIM-01 line 17 explicitly says "ModuleNotFoundError"]`.

**Eagerness on Python 3.14 across all import forms:**

| Import form | Fires `__init__.py` body? | Notes |
|-------------|---------------------------|-------|
| `import mcp_test_framework.sdet` | YES, eagerly | Standard import path — `__init__.py` body executes top-to-bottom before binding. |
| `from mcp_test_framework.sdet import X` | YES, eagerly | Same machinery; the body raises before the `from` clause can read `X`. |
| `from mcp_test_framework import sdet` | YES, eagerly | `mcp_test_framework/__init__.py` triggers the submodule resolution, which executes `sdet/__init__.py` body. |

**PEP 690 / PEP 810 caveat:** `[VERIFIED: WebSearch + peps.python.org]` PEP 690 (transparent lazy imports) was **rejected** by the Steering Council. PEP 810 (explicit-opt-in lazy imports) was accepted 2025-11-03 but uses opt-in syntax (`lazy import X`) — it is **not** active by default in Python 3.14 (released 2025-10-07) or any anticipated 3.x. **Conclusion:** raising in `sdet/__init__.py` body fires eagerly on every import form under every supported Python configuration. The planner can rely on this with HIGH confidence.

**Exact module body to write (template — planner copies + adjusts to ERROR-STYLE.md tone):**

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

**Why a `raise` instead of calling `_emit_operator_error`:** `_emit_operator_error` raises `typer.Exit` which is appropriate for a CLI entry point — but `sdet/__init__.py` is imported by tests/library users where `typer.Exit` would surface as an unexpected `SystemExit`. The plain `raise ModuleNotFoundError(...)` preserves the import-error semantics operators (and their IDEs / pytest's collection error rendering) expect, while still carrying the three-part operator-tone text in `args[0]`. The three-part shape (summary line, blank, detail, blank, `next:`) is preserved within the single string.

**Existing test scaffold to extend:** the operator-error regression file `tests/framework/unit/test_error_style.py` is the canonical pinning location (per Plan 31-01 precedent — `test_error_style_sdet_rejection_message` at L98). Plan 32-01's test mirrors that shape: `import importlib; with pytest.raises(ModuleNotFoundError) as exc_info: importlib.import_module("mcp_test_framework.sdet"); assert "mcp_test_framework.test_code" in str(exc_info.value); assert "next:" in str(exc_info.value)`.

**Confidence:** HIGH (verified import semantics; PEP status verified via web search).

---

### SHIM-02 — `--sdet` Typer flag (D-04)

**Mechanism (recommended): keep the option registered with `hidden=True`, flip the eager callback from `warnings.warn` to `raise typer.BadParameter`.**

**Current shape (already correct hidden-intercept skeleton):** `cli.py` L735–742 already has:
```python
sdet_legacy: bool = typer.Option(
    False,
    "--sdet",
    hidden=True,                           # already correct
    help="Deprecated alias for --test-code; removed in v1.5.",
    callback=_warn_sdet_flag,              # callback to flip
    is_eager=True,                         # already correct
),
```
The phase 32-02 work is **purely to flip the callback body** (`cli.py` L645–658, `_warn_sdet_flag`) plus scrub the body of `run()` at L786–790 that coerces `sdet_legacy=True` to `test_code=True`.

**Typer 0.25 BadParameter semantics:** `[CITED: typer.tiangolo.com tutorial/options/callback-and-context]` `typer.BadParameter` "shows the error with the parameter that generated it" and inherits from `typer.UsageError`. The traceback printed to the operator is consistent with Typer's stock "Invalid value for '--option': ..." surface but with the custom message body, so the migration message is rendered in the operator's familiar Typer UX. **`is_eager=True` is critical** — it ensures the callback fires during option parsing, before `run()`'s body or `--help` short-circuits.

**Recommended callback body (planner-adapt to final wording):**

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

**Why `typer.BadParameter` and NOT `_emit_operator_error`:** `_emit_operator_error` raises `typer.Exit(2)` directly, which Typer renders as a bare stderr block without the option-context prefix. `typer.BadParameter` renders with Typer's standard "Invalid value for '--sdet': ..." surface, which is what success-criterion #2 means by "UsageError-style." Both exit with code 2 — but `BadParameter` produces the more conventional operator UX. **Hard constraint:** the message body still conforms to ERROR-STYLE.md three-part shape inside the exception string.

**Scrub:** also delete `sdet_legacy` parameter from `run()` signature, the `if sdet_legacy:` coercion block at L786–790, and the `sdet=test_code` kwarg passes at L837 + L940 (the `_runner.run_pytest_subprocess` callers — replace `sdet=test_code` with `sdet=test_code` already correct; the rename happens at the runner layer in SHIM-06).

**Confidence:** HIGH (Typer pattern verified; current code already on the right skeleton).

---

### SHIM-03 — `gen-sdet-classes` Typer command (D-04)

**Mechanism (recommended): keep `@app.command("gen-sdet-classes", hidden=True)` registration; replace the body's `warnings.warn` + `gen_test_classes(...)` delegation with a hard `raise typer.BadParameter` (or call `_emit_operator_error`).**

**Current shape:** `cli.py` L1420–1438. Decorator is already `hidden=True`; body warns then delegates. The 32-03 work is **purely body-flip**.

**Why `BadParameter` over `UsageError`:** Typer/Click's `BadParameter` is the more specific subclass and inherits from `UsageError`. For an unknown / removed command, `typer.BadParameter` renders against the implicit "no such argument" context in the same Typer-conventional way `--sdet` will. Alternative: raise stock `typer.Exit(2)` after writing via `typer.echo(..., err=True)`. Both work; recommend `BadParameter` for consistency with `--sdet`.

**Recommended body:**

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

The `config` parameter stays so legacy operator argv (`gen-sdet-classes --config X`) parses cleanly enough to reach the body and surface the error message rather than producing a stock "no such option" before the body fires. Setting `hidden=True` on the option keeps it out of `--help`.

**Confidence:** HIGH.

---

### SHIM-06 — `tests/sdet/` discovery (D-05)

**Severity: warn (not hard-fail).** Phase 31 D-06 chose warn-only for the `MCPTF_CONFIG_FILE` survival, and SHIM-06 inherits that precedent — see `_plugin.py` L148–183 (the formatwarning-prefixed warn-once pattern is reusable here verbatim). Hard-failing would prevent operators from running their `tests/test_code/` suite while they mid-migrate.

**Hook choice: `pytest_collection` (already exists in `_plugin.py` at L255), NOT `pytest_collectstart`.**

- `pytest_collection(session)` fires once per session, before any per-collector traversal starts. It's the right place for a "does this directory exist" check that should fire once. `[VERIFIED: pytest docs via WebSearch — pytest_collection is the session-start hook called before collection begins]`.
- `pytest_collectstart(collector)` fires once per collector node and would double-fire if both `tests/test_code/` and `tests/sdet/` are present — wrong shape for this check.
- `pytest_configure(config)` fires too early (before testpaths are resolved) for a path-existence check anchored to `rootpath`.
- Reusing the existing `pytest_collection` hook also keeps the plugin surface lean (no new hook function).

**Double-fire concern (CONTEXT.md flag):** with `pytest_collection`, the check runs once per session. Both-directories-present case fires the warning exactly once. Confirmed safe.

**Recommended hook body insert (extends existing `_plugin.py:pytest_collection` at L255):**

```python
def pytest_collection(session: pytest.Session) -> None:
    """... existing docstring ..."""
    # ... existing body ...

    # v1.5 SHIM-06: warn (do not fail) if tests/sdet/ is present.
    # tests/sdet/ is no longer auto-discovered; this detector survives
    # the surface removal so operators mid-migration see a loud signal.
    # Planned removal: v1.6 capstone.
    legacy_dir = session.config.rootpath / "tests" / "sdet"
    if legacy_dir.is_dir() and any(legacy_dir.glob("test_*.py")):
        _original_formatwarning = warnings.formatwarning
        warnings.formatwarning = _mcptf_formatwarning  # reuse the Phase 31 D-08 prefix
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

**Note:** the Phase 31 D-08 `_mcptf_formatwarning` is a **local nested function** inside `pytest_configure` (see `_plugin.py` L156–166), not module-level. The SHIM-06 plan should refactor it to module-level so both warnings reuse the same `[mcp-contracts]` prefix renderer — this is a small ride-along refactor scoped to D-05's already-in-scope file.

**Dual-discovery strip:** in addition to the warn-on-presence hook, plan 32-04 strips every `tests/sdet/` reference from the runner/fixtures/reporter so the path is no longer in pytest's argv. **Sites to edit (verified via Grep):**

| File | Line(s) | What |
|------|---------|------|
| `src/mcp_test_framework/_runner.py` | L87, L107, L109, L116, L128, L134, L137, L141–143, L211, L276, L312, L608, L619, L760, L797, L803, L1271, L1283, L1285 | `sdet=` parameter, dual-discovery branches, JUnit XML classname-prefix detection (`tests.sdet.test_` strings — strip the second branch), docstrings, `# noqa: sdet-rename-shim` markers. **21 marker sites in _runner.py.** |
| `src/mcp_test_framework/fixtures.py` | L130, L135, L153, L206 | `tests/sdet/` references in path-validation docstrings + path-list array. **4 marker sites.** |
| `src/mcp_test_framework/_reporter.py` | L219 | `tests/sdet/` mention in collection-source detection comment. **1 marker site.** |
| `src/mcp_test_framework/_black_box_guard.py` | L10 | `SDET-safety principle` reference; **this is a doctrinal SEED-022 mention, NOT a v1.4 deprecation shim — DO NOT scrub** (per memory `project_framework_primitives_sdet_safety_principle`). The `# noqa: sdet-rename-shim` marker there is a misapplication and the planner should DELETE THE MARKER but PRESERVE THE PROSE. |

**Parameter rename:** the `sdet=True` kwarg threaded through `_build_pytest_args`/`run_pytest_subprocess` (cli.py + _runner.py) is operator-facing-named-after-the-flag. After `--sdet` is gone (SHIM-02), the kwarg should be renamed `test_code=True`. **Coupling:** this is a SHIM-06 ride-along, not a SHIM-02 concern (the SHIM-02 plan removes the `--sdet` argv source; the SHIM-06 plan removes the kwarg surface).

**Total noqa markers to scrub across the codebase:** 71 (counted via Grep). 60 of these are in `cli.py`/`sdet/__init__.py`/`_runner.py`/`fixtures.py`/`_reporter.py` (the v1.4 shim sites); 1 is the wrongly-marked SEED-022 reference in `_black_box_guard.py`; the remaining 10 are in plan-artifact / planning files (ignore — not source).

**`tests/sdet/` on disk RIGHT NOW:** The directory exists but contains only `__pycache__/` and `_generated/` — **no `test_*.py` files** (verified via Glob: only `_generated/homelab_mcp/*.py` test-code-class scaffolds, plus `__pycache__/*.pyc` artifacts from a previous run). **Implication:** the SHIM-06 warn-on-presence detector (which requires `any(legacy_dir.glob("test_*.py"))`) will silently NOT fire on the current working tree — the detector is purely a safety net for operators with stale `tests/sdet/` who haven't moved their scenarios. The framework's own runtime is unaffected. Plan 32-04 should also **delete the on-disk `tests/sdet/` directory** to remove dead `_generated/` and `__pycache__/` clutter, but this is a CLEANUP ride-along, not part of the SHIM-06 surface itself.

**Confidence:** HIGH (hook semantics verified; file/line touch-points grep-verified).

---

### SHIM-07 — unprefixed fixtures (D-06)

**Count correction:** CONTEXT.md success criterion #4 names `config`, `judge`, `client`, `target_tool` (4 names). **The actual count is SIX, and `client` is NOT one of them.** Verified by reading `_plugin.py` L433–502 + plugin docstring L12.

**The full alias set (six fixtures):**

| Alias (registered name) | Prefixed equivalent | `_plugin.py` line |
|-------------------------|---------------------|---------------------|
| `config` | `mcp_config` | L433–442 |
| `judge` | `mcp_judge` | L445–454 |
| `target_tool` | `mcp_target_tool` | L457–466 |
| `rubric_clarity` | `mcp_rubric_clarity` | L469–478 |
| `rubric_disambiguation` | `mcp_rubric_disambiguation` | L481–490 |
| `rubric_parameters` | `mcp_rubric_parameters` | L493–502 |

**There is no `client`/`mcp_client` alias.** The `mcp_client` fixture exists (in `fixtures.py` L402) but has no unprefixed alias in the plugin. CONTEXT.md's SC#4 naming is editorial shorthand; the planner should pin tests against the **actual six** above. **Recommend: planner amends CONTEXT.md (or the plan-level success criteria) to enumerate the six explicitly to prevent downstream test under-coverage.**

**Mechanism: `pytest.fail(reason=..., pytrace=False)` inside each fixture body.**

**Why `pytest.fail` over alternatives:**

| Option | Outcome | Verdict |
|--------|---------|---------|
| `pytest.fail(reason=MSG, pytrace=False)` | Fixture-setup-error → test reported as FAILED with `MSG` printed in the failure block | **CHOSEN.** The operator sees the MSG verbatim in pytest output and the failing test name carries the unprefixed fixture name (e.g., `ERROR ... at setup of test_X — fixture 'config' raised FixtureLookupError or pytest.Failed`). |
| `raise RuntimeError(MSG)` | Same outcome but pytest wraps with traceback noise | Worse than pytest.fail — exposes implementation detail. |
| `pytest.skip(MSG)` | Test SKIPPED, message in skip reason | **WRONG.** Success criterion #4 says "fail at fixture-resolution time" — skip is not a failure. |
| Delete the fixture; let pytest's stock `fixture 'config' not found` fire | Pytest's fuzzy-match suggests `mcp_config` but does NOT guarantee the prefixed name appears in the error | **REJECTED** per D-06 rationale; loses pointer guarantee. |

**Recommended body shape (six fixtures, one per alias — symmetric):**

```python
@pytest.fixture(scope="session")
def config():  # noqa: sdet-rename-shim
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

**Critical:** the fixture body **must not take the prefixed fixture as a dependency anymore** (current code does — see L434 `def config(mcp_config):`). The prefixed-fixture dependency would resolve the real fixture (running its session-scoped setup) before failing the test — wastes startup time and risks the failure being conflated with a real `mcp_config` setup error. **Drop the parameter** so `pytest.fail` fires immediately at fixture lookup with zero side effects.

**Pin test pattern (one per fixture; planner can parametrize):**

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

**Confidence:** HIGH (fixture count + names verified; `pytest.fail(pytrace=False)` mechanism is the standard pytest pattern).

---

### SHIM-08 — `mcp-test-framework` console-script (D-07)

**Mechanism: rewrite `_deprecated_script.py:main()` to print operator-tone message to stderr and `sys.exit(2)`.**

**Why NOT raise `typer.Exit` or `typer.BadParameter`:** `main()` is a bare console-script trampoline — Typer's `app()` is not in the call stack at the failure point. Raising `typer.Exit` works (it's a `SystemExit` subclass) but introduces a noisy traceback frame. Plain `sys.exit(2)` after a `print(MSG, file=sys.stderr)` produces the cleanest operator surface: one block of text, then process exit.

**Exit code: 2.** Verified — no existing test under `tests/framework/` pins a specific exit code for `mcp-test-framework` invocation; the only tests of this script today verify the DeprecationWarning fires (test files that mention `mcp-test-framework command is deprecated` per Grep). `[VERIFIED: grep across tests/framework/ shows no exit-code pin]`. Exit code 2 matches the ERROR-STYLE.md table for "Config not found / framework refuses to run" — consistent operator-mental-model "framework refused to start; exit 2."

**stdout vs stderr:** stderr. Phase 31 D-08's `_mcptf_formatwarning` override applies to `warnings.warn()` calls inside the framework — it does NOT apply to bare `print()` in `_deprecated_script.py:main()`. The bare-script can apply the same `[mcp-contracts]` prefix manually for visual consistency, but does not need the override.

**Recommended body:**

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

**`[project.scripts]` entry stays** per D-07 — `pyproject.toml` L25 (`mcp-test-framework = "mcp_test_framework._deprecated_script:main"`) is preserved. If the entry were removed, operators' shells would emit `command not found` with no pointer to the new name.

**Confidence:** HIGH.

---

### D-08 — Shared `_emit_legacy_surface_pointer` helper (RESOLVED)

**Phase 31 outcome:** Phase 31 did NOT extract a separate `_operator_errors.py` module. The shared three-part emit helper is `_emit_operator_error(...)` and lives in **`src/mcp_test_framework/_runner.py` L52–79**.

**Verified by:**
- Grep across `src/`: only `_runner.py` and `cli.py` define functions named `_emit_operator_error*`. `_runner.py:52` defines `_emit_operator_error`; `cli.py:243` defines `_emit_operator_error_for_validation` (a dispatcher that calls the helper).
- `_runner.py` module docstring L22–26 explicitly documents the move: *"This module also hosts `_build_pytest_args` and `_emit_operator_error` — they were moved here from `cli.py` to avoid a circular import (`cli.py` imports `_runner`; `_runner` needs the helpers). `cli.py` re-exports both symbols so existing tests that `from mcp_test_framework.cli import _build_pytest_args` keep working."*
- No `_operator_errors.py` exists in `src/mcp_test_framework/` (verified via Glob).
- Phase 31 summary frontmatter `key-files.modified` lists `_runner.py` once (via Plan 31-02's `_runner._build_pytest_args` config-path threading change) but does not include extraction of a new shared-errors module.

**Exact signature for all six Phase 32 plans to import:**

```python
from mcp_test_framework._runner import _emit_operator_error

# Signature:
_emit_operator_error(
    summary: str,
    detail: list[str],
    next_step: str,
    *,
    exit_code: int = 2,
) -> typing.NoReturn:
    """Raises typer.Exit(exit_code); never returns. See docs/ERROR-STYLE.md."""
```

**Three formatting facts the planner needs to know:**

1. `typer.echo("\n".join(parts), err=True)` — output goes to **stderr**.
2. `parts = [summary, "", *detail, "", f"next: {next_step}"]` — fixed three-part shape, blank lines separate.
3. `raise typer.Exit(code=exit_code)` — default 2; planner can override per-call (e.g., the `mcp-test-framework` stub uses sys.exit not Exit, see SHIM-08).

**Recommendation: import directly from `_runner` (NOT from `cli`).** The cli.py re-export exists for backward compatibility with tests that pre-date the move, but new code calling sites should use the canonical path. This avoids contributing to a future deprecation of the cli.py re-export.

**Should plan 32-01 extract a NEW helper (`_emit_legacy_surface_pointer`)?** Recommend NO. The existing `_emit_operator_error` already takes the three text parts as kwargs; a thin wrapper that just templates "X was removed in v1.5 / X was renamed to Y / next: rename X to Y" would save ~5 lines per call site at the cost of introducing one more indirection. The six call sites are mechanically identical in *shape* but each one has different replacement-name and recovery-step text — templating is more brittle than verbatim. **Verdict: each Phase 32 plan calls `_emit_operator_error(...)` directly with its own three-part text, or (for the import-time / fixture-time sites that can't use typer.Exit) raises an exception with the same three-part text in the message.**

**Hard constraint reminder:** every emitted message must conform to docs/ERROR-STYLE.md three-part shape and pass `tests/framework/unit/test_error_style.py`. Plan 32-01's regression test must verify the `ModuleNotFoundError` message contains both `next:` and `mcp_test_framework.test_code`; similarly for the other five plans.

**Confidence:** HIGH (file existence, signature, and re-export verified via Grep + file read).

## File Touch-Points

Per-plan source file inventory. Cross-reference for plan-checker.

### 32-01 — SHIM-01 (sdet package import)

| File | Action | Line range | Notes |
|------|--------|------------|-------|
| `src/mcp_test_framework/sdet/__init__.py` | REWRITE | full file (26 lines → ~18 lines) | Body becomes `raise ModuleNotFoundError(MSG)`; preserve `# noqa: sdet-rename-shim` markers for the v1.5 grandfathering window (Phase 35 SHIM-09 gate references the surviving directory). |
| `tests/framework/unit/test_error_style.py` | EXTEND | append a new test | `test_error_style_sdet_package_removed` — pins the ModuleNotFoundError message text. Mirror the `test_error_style_sdet_rejection_message` (L98) shape. |
| `README.md` | SCRUB | L166, L238, L244, L306, L307 | Five sites mention `mcp_test_framework.sdet.errors.ToolCallError` and "(SDET)" in a fenced snapshot. Scrub the SDET label and the .sdet.errors.ToolCallError class paths; update the noqa marker comment to reflect post-v1.5 state. |
| `docs/SDET-AUTHORING.md` | DELETE or DEPRECATE | full file | File exists at `docs/SDET-AUTHORING.md` with a `noqa: sdet-rename-shim` marker at L3. Replaced operationally by `docs/TEST-CODE-AUTHORING.md` (per CLAUDE.md). Recommend DELETE in plan 32-01; if planner prefers preserve-with-redirect, the file becomes a one-line pointer to TEST-CODE-AUTHORING.md. |

### 32-02 — SHIM-02 (`--sdet` Typer flag)

| File | Action | Line range | Notes |
|------|--------|------------|-------|
| `src/mcp_test_framework/cli.py` | REWRITE | L645–658 (`_warn_sdet_flag`) | Rename to `_sdet_flag_removed`; body raises `typer.BadParameter`. |
| `src/mcp_test_framework/cli.py` | EDIT | L735–742 (`sdet_legacy` option), L786–790 (coercion block), L837 + L940 (kwarg pass) | Keep option registration (hidden=True), update `help=` text to "removed in v1.5", delete coercion block (raise fires from callback before body), keep `sdet=test_code` kwarg passes unchanged (those rename in SHIM-06). |
| `tests/framework/unit/test_error_style.py` | EXTEND | append | `test_error_style_sdet_flag_removed` — uses `CliRunner` to invoke `run --sdet`, asserts `result.exit_code == 2` + message contains `--test-code`. |
| `README.md` | SCRUB | any surviving `--sdet` mention | Verify via grep; none found in current README sweep but verify before commit. |
| `docs/EXTENDING.md`, `docs/mcp_test_framework_mvp_spec.md` | SCRUB | as needed | Spec doc has `mcp-test-framework` invocations — those belong to SHIM-08's sweep, not this plan. |

### 32-03 — SHIM-03 (`gen-sdet-classes` Typer command)

| File | Action | Line range | Notes |
|------|--------|------------|-------|
| `src/mcp_test_framework/cli.py` | REWRITE | L1420–1438 (`_gen_sdet_classes_shim`) | Body raises `typer.BadParameter`; signature drops most options (keep `--config` hidden so legacy argv parses). |
| `tests/framework/unit/test_error_style.py` | EXTEND | append | `test_error_style_gen_sdet_classes_removed` — `CliRunner` invokes `gen-sdet-classes`, asserts exit 2 + message contains `gen-test-classes`. |
| `README.md`, `docs/` | SCRUB | any `gen-sdet-classes` mention | Verify via grep at commit time. |

### 32-04 — SHIM-06 (`tests/sdet/` discovery)

| File | Action | Line range | Notes |
|------|--------|------------|-------|
| `src/mcp_test_framework/_plugin.py` | EDIT | L255 (`pytest_collection` body) | Append warn-on-presence block; refactor nested `_mcptf_formatwarning` (L156–166) to module-level so SHIM-06 reuses it. |
| `src/mcp_test_framework/_runner.py` | STRIP | L87, L107, L109, L116, L128, L134–143, L211, L276, L312, L608, L619, L760, L797, L803, L1271, L1283, L1285 | Drop `sdet=` kwarg branch in `_build_pytest_args` + caller chain; strip `tests/sdet/` from path-lists; strip `tests.sdet.test_` JUnit classname branches; scrub all 21 sdet-rename-shim markers; rename kwarg `sdet` → `test_code`. |
| `src/mcp_test_framework/fixtures.py` | EDIT | L130, L135, L153, L206 | Drop `tests/sdet/` from path-validation tuple at L135; scrub the four `# noqa: sdet-rename-shim` markers and the docstring mentions. |
| `src/mcp_test_framework/_reporter.py` | EDIT | L219 | Strip the `tests/sdet/` mention in the comment; remove the noqa marker. |
| `src/mcp_test_framework/_black_box_guard.py` | EDIT | L10 | DELETE the `# noqa: sdet-rename-shim` marker only — preserve the SEED-022 doctrinal prose. |
| `tests/framework/unit/test_plugin_tests_sdet_warning.py` | CREATE | new file | Pins warn-on-presence behavior using `pytester` + assert UserWarning/DeprecationWarning text contains `tests/test_code/`. |
| `tests/sdet/` (on disk) | DELETE (recommended) | entire directory | `_generated/homelab_mcp/` scaffolds + `__pycache__/` artifacts; no live `test_*.py` files. Cleanup ride-along. |

### 32-05 — SHIM-07 (unprefixed fixtures)

| File | Action | Line range | Notes |
|------|--------|------------|-------|
| `src/mcp_test_framework/_plugin.py` | REWRITE | L433–502 (six fixtures), L12 (docstring) | Each fixture body → `pytest.fail(MSG, pytrace=False)`; drop prefixed-fixture parameter; update docstring L12 to "six removal stubs" (was "deprecation aliases"). |
| `tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py` | CREATE | new file | Parametrized six-fixture regression test (see body shape above). |
| Search for tests using `def test_X(config, ...)` etc. | AUDIT | repo-wide | Some self-tests may still consume the unprefixed names; need rename. Verify with `grep -rn 'def test.*\b\(config\|judge\|target_tool\|rubric_\(clarity\|disambiguation\|parameters\)\)\b' tests/` and amend in-plan. |

### 32-06 — SHIM-08 (`mcp-test-framework` console-script)

| File | Action | Line range | Notes |
|------|--------|------------|-------|
| `src/mcp_test_framework/_deprecated_script.py` | REWRITE | full file (33 lines → ~25 lines) | Body becomes print-to-stderr + sys.exit(2). Drop the `from mcp_test_framework.cli import app` (no delegation). |
| `pyproject.toml` | KEEP | L25 | `[project.scripts]` entry stays so the trampoline survives to print the message. |
| `README.md` | SCRUB | L423–425 | Three sites describe the deprecation-warning copy — rewrite to "removed in v1.5" + pointer to `mcp-contracts`. |
| `docs/ERROR-STYLE.md` | SCRUB | L3, L54 | Replaces `mcp-test-framework` with `mcp-contracts` in body prose and the locked reference message. **Caution:** L54 is inside a LOCKED reference message block — verify the locked text already cites `mcp-contracts` (it does on L64 — the L54 leftover is in the "No config found" message which was NOT updated when the script was renamed; this is an existing bug and SHIM-08's sweep is the natural place to fix it). |
| `docs/EXTENDING.md` | SCRUB | L22, L33, L39, L52, L60, L82, L213, L216, L218, L280 | Ten sites use `mcp-test-framework` in shell-command examples; flip all to `mcp-contracts`. |
| `docs/TEST-CODE-AUTHORING.md` | SCRUB | L17, L18, L36 | Three sites with `mcp-test-framework` in install + first-run instructions. |
| `docs/mcp_test_framework_mvp_spec.md` | SCRUB or PRESERVE | L235, L236, L237, L276, L277 | This is a HISTORICAL spec document; the planner decides whether to update the example commands or pin a "(historical — see EXTENDING.md for current)" note. |
| `tests/framework/unit/test_console_script_removed.py` | CREATE | new file | Asserts invoking `mcp-test-framework --help` exits 2 and stderr contains `mcp-contracts`. Use `subprocess.run([sys.executable, "-c", "from mcp_test_framework._deprecated_script import main; main()"])` to drive (avoids needing the installed script). |

## Operator-Tone Error Texture

Every Phase 32 migration message conforms to docs/ERROR-STYLE.md and matches the texture Phase 31 established. Template:

```
<legacy surface> was removed in v1.5

<the legacy thing> was renamed to <new thing> in v1.4 and removed in v1.5.
<one-line description of what's unchanged about behavior>.

next: <imperative action verb> <concrete instruction>
```

**Phase 31 verbatim sample (D-02 wording, from cli.py L329–334) — paste-and-fill template:**

```
unknown config key: sdet

the `sdet:` key was renamed to `test_code:` in v1.4 and removed in v1.5.
your existing block under `sdet:` ports forward unchanged -- just rename the top-level key.

next: rename the `sdet:` key to `test_code:` in your config.yaml
```

**Six per-SHIM texts (recommended verbatim — planner may fine-tune):**

| SHIM | Summary | Detail line 1 | Detail line 2 | Next step |
|------|---------|---------------|---------------|-----------|
| 01 | `mcp_test_framework.sdet was removed in v1.5` | `the mcp_test_framework.sdet import surface was renamed to mcp_test_framework.test_code in v1.4 and removed in v1.5.` | `every public symbol (ToolCallError, ToolResponse, mcp_session, tool) is re-exported unchanged from the new location.` | `replace from mcp_test_framework.sdet import X with from mcp_test_framework.test_code import X in your tests.` |
| 02 | `--sdet was removed in v1.5` | `the --sdet flag was renamed to --test-code in v1.4 and removed in v1.5.` | `every behavior is unchanged — only the flag spelling moved.` | `pass --test-code instead of --sdet to mcp-contracts run.` |
| 03 | `gen-sdet-classes was removed in v1.5` | `the gen-sdet-classes command was renamed to gen-test-classes in v1.4 and removed in v1.5.` | `every flag is unchanged — only the command name moved.` | `invoke mcp-contracts gen-test-classes (same flags).` |
| 06 | `tests/sdet/ is no longer auto-discovered as of v1.5` | `the tests/sdet/ directory contains test_*.py files but is no longer collected by mcp-contracts run --test-code.` | `every scenario should live under tests/test_code/; the two layouts are otherwise identical.` | `move your tests/sdet/test_*.py files to tests/test_code/ and re-run.` |
| 07 | `the \`{alias}\` fixture was removed in v1.5` (per-fixture) | `the \`{alias}\` fixture was renamed to \`{prefixed}\` in v1.4 and removed in v1.5.` | `the fixture body, scope, and return value are unchanged — only the name moved.` | `rename \`{alias}\` to \`{prefixed}\` in your test signature.` |
| 08 | `mcp-test-framework was removed in v1.5` | `the mcp-test-framework console-script was renamed to mcp-contracts in v1.4 and removed in v1.5.` | `every subcommand and every flag is unchanged — only the script name moved.` | `invoke mcp-contracts instead of mcp-test-framework (same args).` |

## Common Pitfalls

### Pitfall 1: Re-using the prefixed fixture as a parameter in stub-raise fixture body
**What goes wrong:** `def config(mcp_config): pytest.fail(...)` resolves `mcp_config` (running its session-scoped setup, including the MCP subprocess spawn) before calling `pytest.fail` — wastes startup and risks the failure being conflated with a real `mcp_config` setup error.
**How to avoid:** drop the parameter entirely. The fixture is a pure stub — `def config(): pytest.fail(...)`.
**Warning signs:** the test shows two error frames (one from `mcp_config` setup, one from the alias) instead of one.

### Pitfall 2: Scrubbing the SEED-022 SDET-safety doctrinal mention as if it were a v1.4 deprecation shim
**What goes wrong:** `_black_box_guard.py` L10 mentions "SDET-safety principle" — a doctrinal reference to memory `project_framework_primitives_sdet_safety_principle`, NOT a v1.4 surface rename. The line carries a `# noqa: sdet-rename-shim` marker erroneously (left over from a broad-pattern noqa sweep).
**How to avoid:** in plan 32-04, DELETE the marker but PRESERVE the prose. The SEED-022 doctrine survives all of v1.5.

### Pitfall 3: Phase 31 D-08 `_mcptf_formatwarning` is a nested local, not module-level
**What goes wrong:** plan 32-04 (SHIM-06) needs to reuse the same `[mcp-contracts]`-prefixed formatwarning override for the `tests/sdet/` warn-on-presence. If the planner duplicates the nested function inside the new hook, drift between the two copies is a regression vector.
**How to avoid:** refactor `_mcptf_formatwarning` to module-level inside `_plugin.py` as a small ride-along in plan 32-04. Both warning sites import the same helper. Scope is appropriate for SHIM-06's plan.

### Pitfall 4: ERROR-STYLE.md L54 still cites `mcp-test-framework` in a LOCKED reference message
**What goes wrong:** the "No config found" locked reference message at `docs/ERROR-STYLE.md` L46–55 still says `mcp-test-framework config-init` (L54) but the next locked message (L57–65, "Config uses an older schema version") was updated to `mcp-contracts config-init` (L64) by Plan 31-03. The first is a pre-existing leak.
**How to avoid:** Plan 32-06 (SHIM-08) flips L54 to `mcp-contracts config-init` as part of its doc-sweep. **Verify** by grep: `mcp-test-framework` should appear zero times in `docs/ERROR-STYLE.md` after Plan 32-06.

### Pitfall 5: typer.Exit traceback noise inside `_deprecated_script.py:main()`
**What goes wrong:** raising `typer.Exit` from `main()` where Typer's app() is not in the call stack produces a `SystemExit` with a traceback frame. Operators see Python machinery clutter.
**How to avoid:** plain `print(MSG, file=sys.stderr); sys.exit(2)` produces the clean operator surface. See SHIM-08 recommended body.

### Pitfall 6: Forgetting tests/sdet/ on disk is empty
**What goes wrong:** plan 32-04 author writes a warn-on-presence regression test that creates `tests/sdet/test_x.py` and asserts the warning fires — works in the test sandbox. But the production-tree `tests/sdet/` directory contains NO `test_*.py` files (only `_generated/` scaffolds and `__pycache__`). The detector silently does nothing in production unless an operator has actively migrated mid-cycle.
**How to avoid:** in the SHIM-06 plan, ALSO delete the on-disk `tests/sdet/` directory as a cleanup ride-along; document the detector is a future-protection net, not a current-state assertion.

## Code Examples

### `_emit_operator_error` canonical import + call (for any plan that needs typer.Exit)

```python
# Source: src/mcp_test_framework/_runner.py L52-79 (Phase 31 + pre-existing)
from mcp_test_framework._runner import _emit_operator_error

_emit_operator_error(
    summary="<legacy surface> was removed in v1.5",
    detail=[
        "<the legacy thing> was renamed to <new thing> in v1.4 and removed in v1.5.",
        "<one-line about behavior preservation>.",
    ],
    next_step="<imperative verb> <concrete instruction>",
)  # raises typer.Exit(2); never returns
```

### Plan 31-01 D-02 test pattern (model for all six SHIM regression tests)

```python
# Source: tests/framework/unit/test_error_style.py L98-128 (Phase 31 Plan 01)
def test_error_style_sdet_rejection_message(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pin verbatim summary/detail/next_step text from CONTEXT D-02."""
    cfg = tmp_path / "sdet.yaml"
    cfg.write_text("version: 2\nsdet:\n  generated_root: out\n", encoding="utf-8")
    try:
        Config(yaml_file=str(cfg))
    except ValidationError as exc:
        with pytest.raises(typer.Exit) as exit_info:
            _emit_operator_error_for_validation(exc, source=str(cfg))
        assert exit_info.value.exit_code == 2
        captured = capsys.readouterr()
        text = captured.out + captured.err
        assert "unknown config key: sdet" in text
        # ...
```

### Phase 31 D-08 scoped-formatwarning override (paste-and-extend for SHIM-06)

```python
# Source: src/mcp_test_framework/_plugin.py L154-183 (Phase 31 Plan 02)
_original_formatwarning = warnings.formatwarning

def _mcptf_formatwarning(message, category, filename, lineno, line=None):
    prefix = "[mcp-contracts]"
    try:
        if sys.stderr.isatty():
            prefix = f"\x1b[31m{prefix}\x1b[0m"
    except Exception:
        pass
    return f"\n{prefix} {message}\n\n"

warnings.formatwarning = _mcptf_formatwarning
try:
    warnings.warn(MSG, DeprecationWarning, stacklevel=2)
finally:
    warnings.formatwarning = _original_formatwarning
```

## Project Constraints (from CLAUDE.md)

- **Python 3.14 pinned.** All shim removals must work under 3.14 (no 3.13-only patterns). Verified for `ModuleNotFoundError` semantics, Typer 0.25 API, pytest 9.x hooks.
- **No SUT imports.** None of the shim removals touch homelab-mcp surface; SEED-022 not at risk.
- **`uv` and `pyproject.toml`-driven.** `[project.scripts]` and `[project.entry-points.pytest11]` blocks stay intact per D-07; only `_deprecated_script.py:main()` body changes.
- **pytest-asyncio strict mode.** No async-related work in this phase.
- **GSD workflow enforcement.** Each plan is a `/gsd-execute-phase` execution per CLAUDE.md; no direct edits.
- **v1.4 → v1.5 deprecation-shim policy.** Every shim was introduced in v1.4 with one-milestone deprecation window explicitly locked at v1.5 expiry. Removing them is the explicit v1.5 milestone work — no further deprecation handling needed.

## Environment Availability

No external runtime dependencies for this phase. All work is in-repo Python source + docs + pyproject.toml.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | runtime | ✓ | 3.14 (pinned) | — |
| uv | dep management | ✓ | 0.11.x | — |
| pytest | test runner | ✓ | 9.0.3 | — |
| typer | CLI framework | ✓ | 0.25.x (transitive via mcp[cli]) | — |

## Validation Architecture

**SKIPPED** — per init context, `workflow.nyquist_validation` is not enabled for this phase, and the per-plan regression-test placement (D-09) provides the appropriate test coverage at the per-surface granularity without a separate validation framework.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python 3.14 ships without active PEP 690 / PEP 810 lazy imports by default | SHIM-01 | LOW. PEP 810 is opt-in; PEP 690 was rejected. Verified via web search but not directly tested on local 3.14 install. If an operator opts into PEP 810 syntax (`lazy import mcp_test_framework.sdet`), the `ModuleNotFoundError` fires when `sdet` is first referenced, NOT at the `import` statement — same operator-facing message, slightly different timing. Acceptable. |
| A2 | `typer.BadParameter` from an eager option callback fires before `--help` short-circuit | SHIM-02 | LOW. Current `_warn_sdet_flag` callback is already proven to fire on `--sdet --help` (per `cli.py` L787 comment). Flipping the body from `warn` to `raise` keeps the same firing point. |
| A3 | No `tests/framework/` test pins the `mcp-test-framework` console-script exit code | SHIM-08 | LOW. Verified via Grep for `mcp-test-framework command is deprecated` matches — only the DeprecationWarning text is pinned, not exit code. If a hidden subprocess test exists that this grep missed, plan 32-06 surfaces it in TDD-RED. |
| A4 | `pytest.fail(pytrace=False)` from a session-scoped fixture body surfaces as a setup ERROR (not a FAILED test) with the message visible | SHIM-07 | LOW. Standard pytest pattern documented at every pytest reference. If pytest renders the error differently than expected, the SHIM-07 plan's regression test catches it. |
| A5 | The `mcp_client` fixture is NOT one of the six unprefixed aliases | SHIM-07 | NONE. Verified by reading `_plugin.py` L433–502 directly. CONTEXT.md SC#4 naming includes `client` editorially but no such fixture exists in code. |

## Open Questions

1. **Should the SHIM-06 plan delete the on-disk `tests/sdet/` directory?**
   - What we know: the directory exists, contains `_generated/homelab_mcp/` scaffolds (60+ test-code-class files) and stale `__pycache__/` artifacts, but NO `test_*.py` files. The runtime detector won't fire on it.
   - What's unclear: whether the planner wants to keep the `_generated/` scaffolds as historical reference or treat them as dead code.
   - Recommendation: DELETE the on-disk `tests/sdet/` directory as part of plan 32-04. The directory is dead code; `tests/test_code/_generated/homelab_mcp/` already mirrors it (verified via Glob).

2. **Should CONTEXT.md be amended to enumerate the SIX unprefixed fixtures explicitly (not the four it names + `client`)?**
   - What we know: CONTEXT.md SC#4 names `config`, `judge`, `client`, `target_tool`. Actual code has `config`, `judge`, `target_tool`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`. `client` is not an alias.
   - What's unclear: whether this needs a CONTEXT amend or whether the plan-level success criteria capture the six explicitly.
   - Recommendation: planner amends CONTEXT.md (small edit, no re-discuss) OR the SHIM-07 plan's success criteria explicitly list the six. Either path closes the gap.

3. **Should `docs/SDET-AUTHORING.md` be deleted in plan 32-01 (alongside the sdet/ package shim) or in a separate "doc scrub" pass?**
   - What we know: the file exists with a `noqa: sdet-rename-shim` marker; CLAUDE.md says `docs/TEST-CODE-AUTHORING.md` is the post-v1.4 walkthrough.
   - What's unclear: whether the file content is fully ported to TEST-CODE-AUTHORING.md or whether some unique content lives only in SDET-AUTHORING.md.
   - Recommendation: plan 32-01 scout step verifies content parity. If parity confirmed, DELETE in 32-01; if not, KEEP as a redirect stub or port the missing content to TEST-CODE-AUTHORING.md in the same commit.

4. **Should `docs/mcp_test_framework_mvp_spec.md` `mcp-test-framework` invocations be updated or left as historical?**
   - What we know: this is the original MVP spec (CLAUDE.md cites it as "the authoritative design document"); L235–237 show `mcp-test-framework run`/`list-tools`/`version` in a usage block.
   - What's unclear: whether the planner treats the spec as a frozen historical document or a living one.
   - Recommendation: plan 32-06 either flips the invocations or adds a one-line "(historical — see EXTENDING.md for current command)" note at the top of the relevant section. Planner picks.

## Sources

### Primary (HIGH confidence)
- `src/mcp_test_framework/_runner.py` L52-79 — `_emit_operator_error` signature + docstring.
- `src/mcp_test_framework/cli.py` L243 + L645-742 + L1420-1438 — current Typer flag/command surfaces.
- `src/mcp_test_framework/_plugin.py` L128-183 + L255 + L433-502 — pytest_configure / pytest_collection / unprefixed-fixture aliases.
- `src/mcp_test_framework/sdet/__init__.py` — current sdet package re-export shim.
- `src/mcp_test_framework/_deprecated_script.py` — current console-script trampoline.
- `pyproject.toml` L17-37 — `[project.scripts]` + `[project.entry-points.pytest11]` declarations.
- `docs/ERROR-STYLE.md` — three-part operator-tone contract.
- `.planning/phases/31-.../31-01-SUMMARY.md` + `31-02-SUMMARY.md` — Phase 31 outcomes confirming no `_operator_errors.py` extracted.
- Grep sweep across `src/`: 71 total `# noqa: sdet-rename-shim` markers (60 in shim sites, 1 misapplied in _black_box_guard.py).

### Secondary (MEDIUM confidence — web-search verified against official docs)
- [Typer CLI Option Callback and Context](https://typer.tiangolo.com/tutorial/options/callback-and-context/) — `typer.BadParameter` UX semantics.
- [pytest documentation — Writing hook functions](https://docs.pytest.org/en/stable/how-to/writing_hook_functions.html) — `pytest_collection` vs `pytest_collectstart` vs `pytest_collection_modifyitems` ordering.
- [PEP 690 – Lazy Imports](https://peps.python.org/pep-0690/) (REJECTED) — confirms transparent lazy imports are NOT in 3.14.
- [PEP 810 – Explicit Lazy Imports](https://peps.python.org/pep-0810/) (ACCEPTED 2025-11-03) — confirms PEP 810 is opt-in syntax only.

### Tertiary (LOW confidence — assumed but not directly tested)
- A5 in Assumptions Log (verified via code reading, not via live pytest run).

## Metadata

**Confidence breakdown:**
- D-03 mechanism (SHIM-01 ModuleNotFoundError eagerness): HIGH — verified import semantics + PEP status.
- D-04 mechanism (SHIM-02/03 Typer hidden intercept + BadParameter): HIGH — existing code already on the skeleton; pattern verified via Typer docs.
- D-05 mechanism (SHIM-06 hook choice + warn vs fail): HIGH — pytest hook ordering verified; Phase 31 precedent for warn-only.
- D-06 mechanism (SHIM-07 pytest.fail + six-not-four fixture count): HIGH — code-read confirmed; count discrepancy with CONTEXT.md surfaced.
- D-07 mechanism (SHIM-08 exit code + stderr routing): HIGH — no test pins another exit code; stderr matches ERROR-STYLE.md.
- D-08 outcome (shared helper location): HIGH — verified by `Grep` + file read; no `_operator_errors.py` exists; `_emit_operator_error` lives in `_runner.py`.

**Research date:** 2026-05-24
**Valid until:** 2026-06-23 (30 days — stable surface; Python 3.14 + Typer 0.25 + pytest 9.0 + pydantic 2.13 all pinned).

---

*Phase: 32-Surface-shim removals — CLI + package + fixtures + discovery*
*Research completed: 2026-05-24*
