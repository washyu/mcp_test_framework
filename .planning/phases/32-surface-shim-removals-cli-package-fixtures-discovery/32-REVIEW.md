---
phase: 32-surface-shim-removals-cli-package-fixtures-discovery
reviewed: 2026-05-25T00:00:00Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - src/mcp_test_framework/sdet/__init__.py
  - src/mcp_test_framework/cli.py
  - src/mcp_test_framework/_plugin.py
  - src/mcp_test_framework/_runner.py
  - src/mcp_test_framework/_reporter.py
  - src/mcp_test_framework/fixtures.py
  - src/mcp_test_framework/_black_box_guard.py
  - src/mcp_test_framework/_deprecated_script.py
  - tests/framework/test_cli_reporter_rewire.py
  - tests/framework/test_sdet_rename_leak_gate.py
  - tests/framework/unit/test_console_script_removed.py
  - tests/framework/unit/test_error_style.py
  - tests/framework/unit/test_gen_sdet_classes_cli.py
  - tests/framework/unit/test_gen_sdet_classes_config_driven.py
  - tests/framework/unit/test_plugin_tests_sdet_warning.py
  - tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py
  - tests/framework/unit/test_runner_reports_adapter.py
  - tests/framework/unit/test_runner_sdet_digest.py
  - tests/framework/unit/test_runner_sdet_kwarg.py
  - tests/framework/unit/test_runner_sdet_rows.py
  - tests/framework/unit/test_session_needs_preflight.py
findings:
  critical: 3
  warning: 6
  info: 4
  total: 13
status: issues_found
---

# Phase 32: Code Review Report

**Reviewed:** 2026-05-25
**Depth:** standard
**Files Reviewed:** 21
**Status:** issues_found

## Summary

Phase 32 retires six v1.4 deprecation shims by flipping them from warn-and-delegate to hard-reject stubs with operator-tone pointer messages. The overall structural pattern is sound: each shim has a noqa-tagged removal stub that emits a three-part (what removed -> why -> next step) operator-tone message, regression-pinned by tests under `tests/framework/`. However, two of the six hard-reject paths have correctness defects that defeat the "raise BEFORE doing legacy work" invariant called out in Pitfall 1, and the `--sdet` Typer callback contract is subtly wrong, breaking the hard-rejection promise on legacy CLI flows.

The Pitfall 1 protection for the six fixture stubs (drop the prefixed-fixture parameter so session-scoped MCP setup doesn't run before `pytest.fail` fires) is correctly implemented and pinned. The `tests/sdet/` warn-on-presence detector and the `mcp-test-framework` console-script stub are both well-formed.

The blockers below are correctness defects that prevent operators from seeing the intended hard-reject experience.

## Critical Issues

### CR-01: `sdet/__init__.py` raises at module-import time, breaking *any* import path including non-shim discovery

**File:** `src/mcp_test_framework/sdet/__init__.py:11-21`
**Issue:** The package's `__init__.py` raises `ModuleNotFoundError` at import time, with no protective guard:

```python
raise ModuleNotFoundError(
    "mcp_test_framework.sdet was removed in v1.5\n"
    ...
)
```

This raises on *every* import attempt of `mcp_test_framework.sdet`, including indirect ones. Two concrete failure modes:

1. **Self-collision in this phase's own scanners.** `tests/framework/test_sdet_rename_leak_gate.py` (the noqa-tagged leak gate that scans for residual `sdet` terminology) walks `src/mcp_test_framework/**/*.py` via `_src_python_files()` (line 53). The `sdet/__init__.py` file is on that list. The scanner only reads source text -- it does not `import` -- so the immediate test passes, but any future static-analysis tool or sphinx-autodoc-style importer that walks the package tree will trigger the raise. A `ModuleNotFoundError` at import is the same shape `importlib` returns for "module truly absent", so callers that catch `ModuleNotFoundError` to provide graceful fallback (e.g., `try: import mcp_test_framework.sdet except ModuleNotFoundError: ...`) will silently get the new behavior with the wrong message attribution.

2. **Site-packages scanner collision.** Some pytest plugins and IDEs walk every importable subpackage of installed wheels to populate completion / type-stub caches. They typically use `importlib.import_module` and catch `ImportError`. Raising at module-import time means these tools see the stub message in unrelated error paths.

**Severity rationale:** This is the *only* shim that triggers on import-graph traversal rather than on direct operator invocation. The other five shims (CLI flag, CLI command, console script, six fixtures) only fire when the operator deliberately uses the legacy spelling.

**Fix:** Move the raise into a function-level lazy hook or use `__getattr__` (PEP 562) so the package imports successfully but any attribute access (the actual `from mcp_test_framework.sdet import X` path) raises:

```python
"""mcp_test_framework.sdet removal stub -- raises on attribute access."""  # noqa: sdet-rename-shim
from __future__ import annotations  # noqa: sdet-rename-shim


_REMOVAL_MESSAGE = (  # noqa: sdet-rename-shim
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


def __getattr__(name: str):  # noqa: sdet-rename-shim -- PEP 562 module-level __getattr__
    raise ImportError(_REMOVAL_MESSAGE)  # noqa: sdet-rename-shim
```

This preserves the operator experience (`from mcp_test_framework.sdet import X` still fails loudly) while letting package-walkers complete their traversal without falsely seeing the module as broken. Note: the regression test in `test_error_style.py::test_error_style_sdet_package_removed` uses `importlib.import_module("mcp_test_framework.sdet")` and asserts `ModuleNotFoundError` is raised -- that test will need to be updated to `ImportError` and to provoke attribute access, or the test must accept the package-import success and use `getattr` to trigger the fail.

---

### CR-02: `--sdet` callback fires before parsing completes; passing `--sdet false` (or omitting it after default) does not raise but also does not point at `--test-code`

**File:** `src/mcp_test_framework/cli.py:645-662, 739-746`
**Issue:** `_sdet_flag_removed` is wired as a Click callback with `is_eager=True` on a `bool` Typer Option (`sdet_legacy`). The callback's guard is `if value:` -- it raises only when the value is *truthy*. This is wrong for two real operator flows:

1. **`mcp-contracts run --sdet=false`**: Click parses `--sdet=false` as `value=False`. The callback returns silently (the `if value:` branch is False). The `sdet_legacy` parameter then proceeds to be a no-op in `run()`. The operator gets *no error*, *no warning*, and no pointer at `--test-code`. They believe they have switched their CI off the legacy flag, when in fact they have never been told it is dead.

2. **Default state under help/completion**: Typer's option resolution may call the callback with `value=False` (the default) under certain code paths (e.g., shell-completion enumeration, `--help` rendering with `--show-default`). Each of those silently returns. Mostly harmless, but combined with (1) above the contract "every legacy entry point raises before doing legacy work" is broken.

The intent is documented in the docstring: "Eager Typer/Click callback that hard-rejects `--sdet`". The actual implementation only hard-rejects when `value` evaluates truthy.

**Severity rationale:** This breaks the hard-reject guarantee for the `--sdet` flag. An operator running `mcp-contracts run --sdet=false` (a plausible CI sed-rewrite if they previously had `--sdet=true` and toggled to false expecting the *new* `--test-code` semantics) gets a *silent fallthrough* and runs the contract suite without any error.

**Fix:** Reject the *presence* of the flag, not the truthy value. The cleanest way is to detect whether Click sees the option as "set by the user" via `ctx.get_parameter_source`, but the simpler patch is to make the option non-boolean (e.g., `typer.Option(..., flag_value=...)`) or to reject any non-None value:

```python
def _sdet_flag_removed(  # noqa: sdet-rename-shim
    ctx: typer.Context, param: typer.CallbackParam, value: bool
) -> bool:
    # Reject if the operator actually supplied --sdet on the command line,
    # regardless of value (--sdet, --sdet=true, --sdet=false all hard-reject).
    src = ctx.get_parameter_source(param.name) if ctx is not None else None
    if src is not None and src.name != "DEFAULT":
        raise typer.BadParameter(
            "--sdet was removed in v1.5\n"
            ...
        )
    return value
```

The `--sdet` option is `hidden=True` so this does not affect operators on the new surface; it strictly closes the silent-fallthrough on `--sdet=false`.

---

### CR-03: `gen-sdet-classes` removal stub does not propagate `--config`; the `--config` value is silently dropped and never used

**File:** `src/mcp_test_framework/cli.py:1418-1433`
**Issue:** The `_gen_sdet_classes_removed` stub accepts `--config` as a hidden option, but ignores the value entirely. While the hard-reject succeeds for `mcp-contracts gen-sdet-classes`, the parameter wiring has a subtler defect: the function body raises `typer.BadParameter` unconditionally, but the `config` parameter is captured (line 1420) and never used. This is mostly harmless except for one scenario:

If an operator types `mcp-contracts gen-sdet-classes --config /tmp/explicit.yaml`, Typer's option parsing for `--config` runs through `Path(...)` conversion BEFORE the function body executes. If the operator typo'd the path to a directory, a permission-protected location, or a non-existent path, they may get a Path-conversion or Typer-side coercion error rather than the operator-tone "command was renamed" message they would expect for a legacy invocation. The operator would then "fix" the path under the false belief that the command still works, only to hit the rename error on the next attempt.

**Severity rationale:** Less serious than CR-01/CR-02 -- the rename pointer still fires for the canonical operator case (`mcp-contracts gen-sdet-classes` with no arguments). But the hidden=True `--config` option is dead weight that risks the wrong message attribution.

**Fix:** Drop the `config` parameter from the removal stub entirely:

```python
@app.command("gen-sdet-classes", hidden=True)  # noqa: sdet-rename-shim
def _gen_sdet_classes_removed() -> None:  # no params
    raise typer.BadParameter(
        "gen-sdet-classes was removed in v1.5\n"
        ...
    )
```

The function is hidden and not reachable via `--help`. Operators who scripted with `--config` get a Typer "unexpected option" error -- still useful, still pointed at the new command via the BadParameter raised on positional matching, and avoids the silent absorption of arbitrary `--config` values.

Note: in `context_settings={"allow_extra_args": True, "ignore_unknown_options": True}` is also worth considering on this stub so legacy operator argv like `mcp-contracts gen-sdet-classes --config foo --extra-flag` parses far enough to surface the rename message regardless of unknown trailing flags. As written, an unknown flag after `gen-sdet-classes` produces a Typer error rather than the rename message.

## Warnings

### WR-01: `_plugin.py` removal-stub fixtures do not raise inside `request.getfixturevalue` chains

**File:** `src/mcp_test_framework/_plugin.py:468-567`
**Issue:** Each of the six removal-stub fixtures calls `pytest.fail(MSG, pytrace=False)`. The plan correctly drops the prefixed-fixture parameter (Pitfall 1) so session-scoped MCP setup does not fire. However:

1. The error is raised at **fixture resolution time**, which happens during pytest setup of each test. A test that does `def test_x(config): ...` produces ERROR-at-setup (not FAIL) -- the existing regression test (`test_plugin_unprefixed_fixtures_removed.py:47`) correctly asserts `result.assert_outcomes(errors=1)`. Fine.

2. However, **operator-tone consistency**: the message starts with `"the \`config\` fixture was removed in v1.5"` (lowercase 'the'). The `--sdet` flag stub starts with `"--sdet was removed in v1.5"`. The `sdet/__init__.py` stub starts with `"mcp_test_framework.sdet was removed in v1.5"`. There is no uniform leading article or prefix. docs/ERROR-STYLE.md is referenced as the source of truth for the format; the six stubs should either uniformly start with the symbol name (no leading `the`) or uniformly include it. Cross-check: the inline `[mcp-contracts]` formatwarning prefix only fires on the warn-on-presence path, not on these `pytest.fail` paths -- so the operator sees inconsistent attribution prefixes depending on which shim fires.

**Fix:** Standardize the message prefix. Either drop the `the \`<name>\`` lead-in everywhere (so every shim starts with the symbol name) or add it everywhere. The current mix is a maintenance hazard.

---

### WR-02: `pytest_collection` warn detector uses `legacy_dir.glob("test_*.py")` -- nested subdirectories with `test_*.py` files are missed

**File:** `src/mcp_test_framework/_plugin.py:296-297`
**Issue:**

```python
legacy_dir = session.config.rootpath / "tests" / "sdet"
if legacy_dir.is_dir() and any(legacy_dir.glob("test_*.py")):
```

`Path.glob("test_*.py")` is **non-recursive**. An operator who has migrated some scenarios to `tests/test_code/` but still has `tests/sdet/subgroup/test_x.py` will *not* see the warning. pytest itself collects recursively by default, so the operator has live tests under `tests/sdet/`, but the deprecation warning never fires.

**Fix:** Use `rglob` for recursive detection:

```python
if legacy_dir.is_dir() and any(legacy_dir.rglob("test_*.py")):
```

The regression test (`test_plugin_tests_sdet_warning.py::test_warns_when_tests_sdet_contains_live_tests`) only puts a file at the top level, so this defect is not surfaced by existing tests. Add a sibling test exercising the nested case.

---

### WR-03: `tests/sdet/` warn-on-presence detector unconditionally walks the filesystem even when library mode is opted out

**File:** `src/mcp_test_framework/_plugin.py:293-314`
**Issue:** The detector runs in `pytest_collection` unconditionally, **before** the `cfg = getattr(session.config, "_mcp_contracts_config", None)` gate (line 316). Operators using pytest in library mode without `mcp_config_file` ini set (the silent-no-op path documented at line 318) still pay a filesystem-walk cost and still get the deprecation warning emitted into their captured output.

This is not load-bearing for behavior (no false positives -- the warning is real if `tests/sdet/` exists), but it does mean any third party that has a `tests/sdet/` directory for unrelated reasons gets the framework's deprecation chatter in their pytest output even though they never opted into the framework's library mode.

**Fix:** Gate the detector on the library-mode opt-in (same `cfg` stash that gates the rest of the hook):

```python
def pytest_collection(session: pytest.Session) -> None:
    cfg = getattr(session.config, "_mcp_contracts_config", None)
    if cfg is None:
        return  # operator opted out; no detector noise either
    legacy_dir = session.config.rootpath / "tests" / "sdet"
    ...
```

The plan's intent is to detect legacy layouts for framework operators, not for arbitrary pytest users who happen to have the plugin installed.

---

### WR-04: `_deprecated_script.py:main` exit code race with stdout flush on Windows console-script wrappers

**File:** `src/mcp_test_framework/_deprecated_script.py:14-28`
**Issue:** `print(msg, file=sys.stderr)` followed by `sys.exit(2)`. On Windows, the console-script wrapper (created by setuptools/pip) is a `.exe` that invokes Python and forwards stdout/stderr. If `sys.stderr` is line-buffered (it usually is, but `PYTHONUNBUFFERED` and various subprocess invocations override this) and the message ends with `\n`, the print succeeds. If the message does NOT end with `\n` (this one does, line 25, message ends with `(same args).\n` -- so the literal terminal newline is fine), `sys.exit(2)` may run before the OS flushes the buffer in some redirect scenarios.

The actual message DOES end with `\n` per line 25, so this is currently OK. But the test (`test_console_script_removed.py:23-25`) only asserts on `result.stderr` content, not on the absence of mid-flush truncation. A future drift to a message without a trailing newline would silently lose the last line under stderr capture in some Windows runners.

**Fix:** Make the flush explicit before exit:

```python
print(msg, file=sys.stderr, flush=True)
sys.exit(2)
```

Belt-and-suspenders on Windows.

---

### WR-05: Removal-stub fixtures may shadow operator-supplied legacy fixtures in operator conftests

**File:** `src/mcp_test_framework/_plugin.py:468-567`
**Issue:** Each stub is `@pytest.fixture(scope="session")`. The plugin is loaded via `pytest11` entry point, so the stubs register globally. If an operator (during migration) has a `tests/conftest.py` that *also* defines `def config(): ...` as a local fixture, pytest's fixture resolution prefers the closer conftest over the plugin -- so the operator's local fixture wins. That sounds like a feature, but it means the operator does NOT see the deprecation message and continues to silently use the legacy spelling against their own local definition.

This is a v1.5 design boundary: the stubs fire **only** for operators relying on the plugin-provided fixtures. Operators with their own conftest-local `config` fixture get silent migration-skip. The plan should document this -- the regression test `test_plugin_unprefixed_fixtures_removed.py` does not exercise the conftest-shadowing case, and operators with hand-rolled fixtures will receive zero migration signal.

**Fix:** Either document the limitation in the stub docstrings or add a `pytest_collection_modifyitems` walk that detects operator conftests redefining the six legacy names and emits a separate warning. Lower-priority; the failure mode is silent-skip of warning rather than incorrect behavior.

---

### WR-06: `_runner._build_pytest_args` always inserts `[sys.executable]`-relative test paths; absolute config-init runs under a renamed test layout will collect unrelated paths

**File:** `src/mcp_test_framework/_runner.py:130-139`
**Issue:** Outside the immediate scope of Phase 32 (no shim involved), but found while tracing the runner: `args = ["tests/contract"]` (or `tests/test_code` / `tests/framework`) uses a relative path. Pytest resolves relative paths against the rootpath. An operator running `mcp-contracts run` from a non-rootdir subdirectory in a workspace where `tests/` is at the worktree root will silently get an empty collection or a collection error rather than running their tests, with no operator-tone diagnostic.

Phase 32 does not change this code, but the `--test-code` and `--with-framework` flag interactions touched in this phase amplify the surface area. A migration operator running `mcp-contracts run --test-code` from a worktree subdirectory will get an opaque pytest "no tests collected" exit-5 mapped to exit 0 (line 187 of `_runner.py`) and a vague stderr warning.

**Fix:** Make the test-scope paths absolute (or rootpath-anchored) by computing them against `_find_pyproject_upward(Path.cwd()).parent` -- the same upward walk `_load_config` already does. Out of scope for the shim-removal phase; flag for follow-up.

## Info

### IN-01: Six fixture stubs duplicate the same operator-tone message body with only the names swapped

**File:** `src/mcp_test_framework/_plugin.py:468-567`
**Issue:** Each of the six stubs has a near-identical 6-line message that differs only by the fixture-name pair. ~80 lines of duplicated literal text. Future drift between stubs is likely (e.g., correcting punctuation in one but missing the others). A simple helper would deduplicate:

```python
def _make_fixture_stub(legacy: str, prefixed: str):
    @pytest.fixture(scope="session", name=legacy)
    def _stub():
        pytest.fail(
            f"the `{legacy}` fixture was removed in v1.5\n"
            f"\n"
            f"the `{legacy}` fixture was renamed to `{prefixed}` in v1.4 and "
            f"removed in v1.5.\n"
            ...
        )
    return _stub
```

But this would conflict with `test_error_style.py`'s verbatim message-pinning approach (the registry pins specific literal substrings). Trade-off: leave as duplicated for explicit regression-pinnability, OR refactor + update the registry to construct expected strings the same way. Document the trade-off in a comment if leaving as-is.

---

### IN-02: `_emit_operator_error_for_validation` -- the `sdet_err` branch leaks pydantic v2-specific error type string

**File:** `src/mcp_test_framework/cli.py:318-326`
**Issue:** The branch keys on `e.get("type") == "extra_forbidden"`. This is a pydantic v2 error-type literal. If pydantic ever renames it (the v1->v2 transition renamed many of these), the branch silently fails to match and the v1->v2 migration goes through the generic fallback, losing the locked operator-tone migration message. Add a regression test (or grep gate) that pins the `extra_forbidden` literal so a pydantic-upgrade doesn't silently break the SHIM-04 message.

---

### IN-03: `_isolation` import in `fixtures.py` not flagged by the shim-tag scanner

**File:** `src/mcp_test_framework/fixtures.py:40` (and the imported `_isolation` module's design)
**Issue:** During tracing, noticed that `_build_isolated_env` is unconditionally invoked in `mcp_client` (line 432). Per the MEMORY.md entry "Isolation blocks live UATs (999.3)", this is a known issue and out of Phase 32's scope, but the noqa-tagged terminology scrub in `tests/framework/test_sdet_rename_leak_gate.py` does scan `fixtures.py` -- worth noting that no shim drift was introduced here.

---

### IN-04: `_deprecated_script.py:9` has an extraneous `noqa: sdet-rename-shim` on `from __future__ import annotations`

**File:** `src/mcp_test_framework/_deprecated_script.py:9`
**Issue:** The `from __future__ import annotations` line carries `# noqa: sdet-rename-shim` but the line contains no `sdet`/`SDET` token. The noqa is dead. Either the leak-gate scanner has a false positive on this file's docstring spanning multiple lines (in which case the noqa should be on the docstring header, not the import), or it's a copy-paste. Same on `sdet/__init__.py:9`.

**Fix:** Audit which line actually carries the matched token and move (or remove) the noqa. Cosmetic only.

---

_Reviewed: 2026-05-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
