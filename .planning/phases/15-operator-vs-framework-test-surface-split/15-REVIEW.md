---
phase: 15-operator-vs-framework-test-surface-split
reviewed: 2026-05-11T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - tests/contract/__init__.py
  - tests/framework/__init__.py
  - tests/framework/smoke/__init__.py
  - tests/framework/unit/__init__.py
  - src/mcp_test_framework/_runner.py
  - src/mcp_test_framework/cli.py
  - tests/framework/test_runner_subprocess.py
  - tests/framework/test_banned_imports.py
  - README.md
  - docs/mcp_test_framework_mvp_spec.md
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: issues_found
---

# Phase 15: Code Review Report

**Reviewed:** 2026-05-11
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 15 splits the test tree into operator-relevant `tests/contract/` and framework-internal `tests/framework/` subtrees, flips the runner's default collection scope to `tests/contract/` only, and adds an opt-in `--with-framework` flag. The split is small in surface area (four empty `__init__.py` files, one new flag, one positional-arg change in `_build_pytest_args`) but has a wide blast radius on test files that hard-coded `Path(__file__).parents[N]` arithmetic or fixture path constants.

The implementation is largely sound, but the auto-fix sweep that updated `test_runner_subprocess.py` and `test_banned_imports.py` **missed a third file with the same class of bug** (`tests/framework/test_runner_live_smoke.py`). The README sample-run output was also not refreshed and still shows pre-split paths that no longer exist. The new `--raw` mode help text is now stale with respect to the `--with-framework` interaction.

No security issues, no data-loss risks. All findings are correctness / documentation drift / wording.

## Warnings

### WR-01: Relocation-induced `parents[1]` bug missed in `test_runner_live_smoke.py`

**File:** `tests/framework/test_runner_live_smoke.py:33,47,57`
**Issue:** Phase 15's relocation auto-fix sweep correctly updated `parents[1]` to `parents[2]` in `tests/framework/test_runner_subprocess.py:355` and the fixture-path constant in `tests/framework/test_banned_imports.py:30-32`, but the identical bug class survives in `test_runner_live_smoke.py`. After `git log --follow` confirms the file moved from `tests/test_runner_live_smoke.py` to `tests/framework/test_runner_live_smoke.py` in commit `2e74967` (Plan 15-01), three call sites still compute `Path(__file__).resolve().parents[1]` and treat the result as `repo_root`. Post-split, `parents[1]` now resolves to `<repo_root>/tests/`, not the repo root, so the live smoke tests will `cwd` into the `tests/` directory and the subprocess will run `uv run mcp-test-framework run` from there. `uv run` only resolves a project relative to its own cwd-or-ancestors search, so this will likely succeed by accident on uv's ancestor-walk, but `cwd=tests/` is not what the test author intended and will cause subtle config-discovery surprises (e.g., `./config.yaml` autodiscovery in `_load_config` will look in `tests/`, not the repo root).

This file is gated by `pytest.mark.live_homelab` and therefore not in the default test run, which is why CI did not catch it during Phase 15. It is also not in this review's explicit `files:` list, but it is the same class of bug the phase claims to have auto-fixed and the reviewer is obligated to call it out as an incomplete sweep.

**Fix:**
```python
# tests/framework/test_runner_live_smoke.py:33,47,57
repo_root = Path(__file__).resolve().parents[2]  # was parents[1]
```

### WR-02: README sample-run output references stale test paths

**File:** `README.md:151-162`
**Issue:** The "Sample green run" block displays a pytest progress summary that names test files at their pre-Phase-15 locations:
- `tests\smoke\test_mcp_client_teardown_regression.py` (actual: `tests\framework\smoke\...`)
- `tests\test_homelab_list_registered_servers.py` (file no longer exists; replaced by `tests/contract/test_mcp_tool_contract.py`)
- `tests\unit\test_banned_imports.py` (actual: `tests\framework\test_banned_imports.py`)
- `tests\unit\test_config.py` (actual: `tests\framework\unit\test_config.py`)
- ...and six more lines with the same stale prefix.

Furthermore, the sample is labelled "Captured verbatim from a real local run" and claims `67 passed, 5 deselected` -- but with Phase 15's flipped default (`tests/contract/` only) the default `mcp-test-framework run` no longer collects 67 tests. The framework self-tests in `tests/framework/` are now collected only under `--with-framework`. The sample is now actively misleading: an operator who runs the documented command will not see anything close to this output.

The block at README:168-170 was partially updated to mention `tests/framework/smoke/`, which makes the inconsistency more obvious -- the prose acknowledges the new layout, but the captured-output block contradicts it.

**Fix:** Re-capture the sample output against the post-split layout, or replace it with two annotated samples (one for the default contract-only run, one for `--with-framework`). At minimum, update the file paths in the existing block and the headline numbers (`collected 72 items / 5 deselected / 67 selected` -> the new contract-only count).

### WR-03: `--raw` help text is now stale with respect to `--with-framework`

**File:** `src/mcp_test_framework/cli.py:367-374`
**Issue:** The `--raw` help string asserts the flag is "Equivalent to `uv run pytest tests/contract/` modulo the config pre-flight gate". This is no longer accurate after Plan 15-02 wired `with_framework=with_framework` into the `--raw` branch (`cli.py:478-480`). When `--raw --with-framework` is passed, the actual invocation is `uv run pytest tests/contract tests/framework`, not `uv run pytest tests/contract/`. The help text also gives an operator the impression that `--with-framework` does not compose with `--raw`, which the code shows is false.

**Fix:**
```python
raw: bool = typer.Option(
    False,
    "--raw",
    help=(
        "Bypass the domain UI wrapper and stream pytest's native output. "
        "All flags forward verbatim to pytest. Default scope is tests/contract; "
        "pass --with-framework to also include tests/framework. The config "
        "pre-flight gate still runs."
    ),
),
```

## Info

### IN-01: Stale comment in `test_banned_imports.py` references pre-split fixture path

**File:** `tests/framework/test_banned_imports.py:68-69`
**Issue:** The docstring of `test_ruff_tid251_fires_on_top_level_import` says: "Uses the canonical fixture file at `tests/_fixtures/banned_import_should_fail.py.txt`". After Plan 15-01 the fixture lives at `tests/framework/_fixtures/banned_import_should_fail.py.txt` (and the `_FIXTURE` constant on line 32 reflects the new path correctly). The auto-fix sweep updated the constant but not this docstring. Easy to spot during a future refactor and easy to fix now.
**Fix:** Update the docstring path to `tests/framework/_fixtures/banned_import_should_fail.py.txt` or just drop the explicit path reference since `_FIXTURE` on line 32 is the source of truth.

### IN-02: Empty `__init__.py` files create implicit-package state for `tests/contract/` and `tests/framework/{,smoke,unit}/`

**File:** `tests/contract/__init__.py`, `tests/framework/__init__.py`, `tests/framework/smoke/__init__.py`, `tests/framework/unit/__init__.py` (all 0 bytes)
**Issue:** The four empty `__init__.py` files turn the subtrees into importable packages. `tests/` itself remains a non-package (no `tests/__init__.py`). This mixed model works with pytest's rootdir + `importmode=prepend` default, but it is an inconsistency the codebase will eventually trip over -- e.g., the comment in `src/mcp_test_framework/_runner.py:872-878` explicitly explains the discovery cache lives in `_runner` because `tests/` is NOT a package. Now its subdirectories ARE packages, which weakens that argument. No bug today, but worth a one-line comment in each `__init__.py` explaining why the package marker exists (or remove them if not load-bearing -- pytest's default collection works fine without them).
**Fix:** Either add a one-line docstring to each `__init__.py` explaining the package boundary, or delete them and confirm pytest collection still works.

### IN-03: `_build_pytest_args` positional `"tests/contract"` is a string literal; no constant

**File:** `src/mcp_test_framework/_runner.py:102-104`
**Issue:** The two scope paths `"tests/contract"` and `"tests/framework"` are bare string literals inside `_build_pytest_args`. If a future phase renames either subtree, the literal will drift from the on-disk path silently (pytest exit 5 -> mapped to 0, surfaced only via the "no tests collected" stderr warning -- easy to miss). Hoisting to module-level constants (`_DEFAULT_SCOPE = "tests/contract"`, `_FRAMEWORK_SCOPE = "tests/framework"`) would let the unit tests in `test_runner_subprocess.py:306-339` reference the same constants and catch a rename at a single source.
**Fix:**
```python
# _runner.py module-level
_CONTRACT_SCOPE = "tests/contract"
_FRAMEWORK_SCOPE = "tests/framework"

def _build_pytest_args(...):
    args: list[str] = [_CONTRACT_SCOPE]
    if with_framework:
        args.append(_FRAMEWORK_SCOPE)
```

### IN-04: Docstring in `_runner.py` references "v1.1 to the in-process pytest entry point" -- outdated phrasing

**File:** `src/mcp_test_framework/_runner.py:87-89`
**Issue:** The docstring for `_build_pytest_args` says it "assembles the argv passed to `pytest` (in v1.1 to the in-process entry point; in Phase 14 to the subprocess argv...)". After Phase 14 the in-process path was deleted; the parenthetical about v1.1 is now archaeology. Minor documentation hygiene; the function's behavior is correctly described.
**Fix:** Drop the "(in v1.1 to the in-process entry point; in Phase 14 to the subprocess argv after `[sys.executable, '-m', 'pytest']`)" parenthetical and just say "assembles the argv passed to `pytest` after `[sys.executable, '-m', 'pytest']`".

### IN-05: `with_framework` flag is not surfaced in `--raw` mode help text alongside the existing flag

**File:** `src/mcp_test_framework/cli.py:394-403`
**Issue:** The `--with-framework` flag has clear help text but does not call out its interaction with `--raw` (where it ALSO applies, per `cli.py:475-480`). Operators reading `--help` may infer the flag is default-mode only because the help string focuses on "maintainer runs and CI jobs". A one-clause clarification ("composes with --raw") would prevent the trial-and-error discovery path.
**Fix:** Append "Composes with `--raw`." to the `--with-framework` help string, or rely on the WR-03 fix to surface the composition from the `--raw` side.

### IN-06: Sample-run prose at README:169 contradicts the captured sample's path

**File:** `README.md:169-170`
**Issue:** The prose says "The 5 deselected tests are the live-marker smoke tests in `tests/framework/smoke/`" but the captured output above on line 154 shows `tests\smoke\test_mcp_client_teardown_regression.py`. The two lines disagree about the path. Folded into the WR-02 fix.
**Fix:** Resolve as part of WR-02.

---

_Reviewed: 2026-05-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
