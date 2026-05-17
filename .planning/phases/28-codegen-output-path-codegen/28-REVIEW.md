---
phase: 28-codegen-output-path-codegen
reviewed: 2026-05-16T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/mcp_test_framework/cli.py
  - tests/framework/unit/test_gen_test_classes_overwrite_prompt.py
  - tests/framework/unit/test_gen_test_classes_pyproject_config.py
  - tests/framework/unit/test_gen_test_classes_site_packages_guard.py
  - tests/framework/unit/test_missing_generated_root_error.py
findings:
  blocker: 0
  warning: 6
  total: 6
status: issues_found
---

# Phase 28: Code Review Report

**Reviewed:** 2026-05-16
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 28 added three safety features to `mcp-contracts gen-test-classes`:
the pre-handshake site-packages guard, a pyproject.toml ini-config
resolution branch, and a TTY-aware overwrite confirmation gate. All three
helpers are well-isolated, raise via the established `_emit_operator_error`
contract, and ship with dedicated unit tests.

No BLOCKER-class defects (no incorrect security posture, no data-loss
window, no crash path that bypasses the gate). The findings below are all
WARNING-class: behavior-vs-comment mismatches, off-by-one in the "+"
suffix, an inconsistency in the boundary cwd-vs-rootpath used to discover
pyproject.toml relative to the in-subprocess pytest plugin, and the
recurring "operator next-step copy still names the legacy CLI" issue that
the missing-generated-root regression test was explicitly written to lock
down on its own branch but is NOT locked down on the surrounding
sibling error branches.

## Warnings

### WR-01: Operator next-step copy points at legacy `mcp-test-framework` CLI name on five branches

**File:** `src/mcp_test_framework/cli.py:294-297, 326-329, 449-453, 481-484, 508-511`
**Issue:**
Phase 28 introduces `test_missing_generated_root_error.py`, which asserts
that the missing-`test_code.generated_root` next-step copy names the
canonical `mcp-contracts config-init` and EXPLICITLY rejects the legacy
`mcp-test-framework config-init` (CLAUDE.md: legacy name is a v1.4
deprecation shim, removed v1.5). The test passes because the
`err_type in ("missing", "value_error.missing")` branch at line 309-310
was updated to the canonical name.

However, FIVE sibling operator-facing next-step strings in the very same
file still hard-code `mcp-test-framework config-init`:

- L294-297 (v1→v2 migration `next_step`): `mcp-test-framework config-init -o config.yaml.new`
- L326-329 (generic validation fallback `next_step`): `mcp-test-framework config-init -o config.yaml`
- L449-453 (`--config PATH` not found): `mcp-test-framework config-init -o config.yaml`
- L481-484 (`MCPTF_CONFIG_FILE` not found): `mcp-test-framework config-init -o config.yaml`
- L508-511 (no config file found): `mcp-test-framework config-init -o config.yaml`

Phase 28's new pyproject branch (L391-394) correctly uses `mcp-contracts
config-init`, and so does the new missing-required-field branch (L309-311),
so the file is now self-inconsistent: half of `_load_config`'s operator
output points at the canonical CLI, half at the deprecated one.

Operators hitting any of these five error paths will be advised to run
the deprecated command. The 28-04 docs sweep was scoped to docs; this
in-code copy was not swept.

**Fix:**
Replace `mcp-test-framework config-init` with `mcp-contracts config-init`
in every operator-facing `next_step=` string under `_load_config` and
`_emit_operator_error_for_validation`, and add a literal-string regression
guard in the existing missing-generated-root test family that scans
`runner.invoke(app, ...).stdout + stderr` for `"mcp-test-framework
config-init"` across all five branches.

---

### WR-02: `_confirm_or_abort_non_empty_target` OSError handler comment contradicts behavior

**File:** `src/mcp_test_framework/cli.py:178-181`
**Issue:**
```python
except OSError:
    # Unreadable directory: fall through to the prompt anyway; the
    # codegen call will produce a clearer error than we can here.
    return
```
The comment says "fall through to the prompt anyway", but the code
`return`s, which SKIPS the prompt entirely. The actual runtime behavior
is: gen-test-classes proceeds past the safety gate as if the directory
were empty, then `_codegen.generate()` attempts to wipe-and-write and
fails there. There is no test exercising this branch (no
`test_unreadable_dir_*`), so the divergence between intent and behavior
is hidden.

Two problems compounded:
1. A future maintainer reading the comment will believe the prompt fires
   (it does not). They may add a "decline" path here that never executes.
2. The "strongest 'never silently destroy data' posture" docstring at
   L160 is technically violated on the unreadable-but-not-empty branch:
   if the directory is unreadable, the prompt is skipped and codegen's
   wipe-and-write runs unprompted. The actual write-side will then fail
   on the same OSError, but the safety gate's contract is broken on
   paper.

**Fix:**
Either align the comment to the code (`# Unreadable directory: skip the
prompt and let codegen surface the OSError with the full path context.`)
or — preferred for the safety-gate posture — convert this branch into an
`_emit_operator_error` call that names the path and the OSError, so the
gate continues to be the load-bearing safety check rather than the eventual
codegen crash:
```python
except OSError as exc:
    _emit_operator_error(
        summary=(
            "gen-test-classes: cannot inspect target directory "
            f"`{target_dir}`"
        ),
        detail=[f"the directory exists but iterdir() failed: {exc}"],
        next_step=(
            "fix permissions on the target directory or pick a different "
            "`test_code.generated_root` in your config.yaml"
        ),
    )
```

---

### WR-03: 1000-entry cap shows "+" suffix when exactly 1000 entries exist (off-by-one in user-facing copy)

**File:** `src/mcp_test_framework/cli.py:172-185`
**Issue:**
```python
for entry in target_dir.iterdir():
    files.append(entry)
    if len(files) >= 1000:
        break
...
suffix = "+" if file_count >= 1000 else ""
```
When the directory contains exactly 1000 entries, the loop appends all
1000, the post-append check trips at `len(files) == 1000`, the loop
breaks before observing whether a 1001th entry exists, and `suffix = "+"`
fires regardless. The prompt then reads "1000+ entries exist" when there
are exactly 1000. Inaccurate user-facing copy.

There is no test for the cap-boundary behavior (no test with 1000 or
1001 entries), so the off-by-one is unobserved.

**Fix:**
Loop one entry further than the cap so the "+" suffix reflects whether
overflow actually occurred:
```python
CAP = 1000
for entry in target_dir.iterdir():
    files.append(entry)
    if len(files) > CAP:
        break
file_count = min(len(files), CAP)
suffix = "+" if len(files) > CAP else ""
```
Add a unit test parametrized over `(999, "999", ""), (1000, "1000", ""),
(1001, "1000", "+")` to lock the boundary.

---

### WR-04: pyproject.toml lookup is cwd-only; library-mode pytest uses upward rootpath discovery

**File:** `src/mcp_test_framework/cli.py:362-365, 463-465`
**Issue:**
`_read_mcp_config_file_from_pyproject(Path.cwd())` only inspects
`<cwd>/pyproject.toml`. If the operator invokes `mcp-contracts
gen-test-classes` (or `run`) from any subdirectory of their project,
no pyproject is found, the branch falls through to MCPTF_CONFIG_FILE /
`./config.yaml`, and the operator gets a "no config file found" error.

The in-subprocess pytest plugin uses pytest's normal `config.rootpath`
discovery, which walks upward to find pyproject.toml. So the same
operator runs:
- `pytest tests/test_code/` from the subdir → works (pytest finds the
  pyproject upstream).
- `mcp-contracts gen-test-classes` from the subdir → fails with "no
  config file found".

The docstring on `_read_mcp_config_file_from_pyproject` at L337-339
claims this helper "mirrors the pytest-plugin ini-resolution behavior",
but the mirror is only cwd-deep. The "one source of truth across CLI +
library mode" property described in `_load_config`'s docstring (L18-21)
is broken for any non-rootdir invocation.

**Fix:**
Walk upward from `Path.cwd()` until you find a pyproject.toml or hit a
filesystem root, mirroring pytest's `rootdir_fallback` semantics:
```python
def _find_pyproject_upward(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        pp = candidate / "pyproject.toml"
        if pp.is_file():
            return pp
    return None
```
Then pass the discovered pyproject's parent into the existing helper.
Add a test where pyproject lives in `tmp_path` but cwd is
`tmp_path / "sub" / "subsub"` to lock the upward walk.

---

### WR-05: Site-packages guard ignores `framework_install_root.parent.parent` for non-src layouts

**File:** `src/mcp_test_framework/cli.py:122-128`
**Issue:**
```python
framework_install_root = Path(mcp_test_framework.__file__).resolve().parent.parent
```
This walks `mcp_test_framework/__init__.py` → `mcp_test_framework/` →
`src/` (in this repo's editable install) or → `site-packages/` (in pip
install). Both are sensible "do not write here" roots.

However, the two-level walk silently assumes a parent directory exists
above the package directory that is the right boundary to block. If the
package is ever vendored at the project root (`<repo>/mcp_test_framework/__init__.py`,
no `src/` shim), the walk lands on the project root itself — which would
then block any `generated_root` ANYWHERE in the operator's project
(`tests/test_code/_generated` IS under the project root). The
gen-test-classes command becomes unusable.

Phase 28's test suite only exercises the editable-src layout
(`_framework_install_root()` in the test does the same `.parent.parent`).
Both the code and the test agree, so the tests pass on every CI run, but
neither verifies the assumption.

**Fix:**
Either (a) constrain the guard to a known set of "danger" parent
directory NAMES (`site-packages`, `dist-packages`) plus an editable-install
detection sentinel, OR (b) keep the current heuristic but assert
explicitly in a comment / docstring that the framework MUST be installed
as either editable-with-src or pip-into-site-packages, never as a
project-root-vendored copy. Add a test that constructs a fake
package-at-project-root layout and verifies the guard does not block
sibling paths under that root (currently it would).

---

### WR-06: Test gaps around `_read_mcp_config_file_from_pyproject` edge cases

**File:** `tests/framework/unit/test_gen_test_classes_pyproject_config.py:1-189`
**Issue:**
The test suite covers the happy paths and one fail-loud case, but
several behaviors documented in the helper's docstring are unverified:

1. **Non-string `mcp_config_file` value** (e.g. `mcp_config_file = ["a", "b"]`
   or `mcp_config_file = 5`). The helper's `isinstance(raw, str)` check
   collapses these to `""` and falls through silently, but no test pins
   that behavior. A future refactor that drops the isinstance check would
   raise `AttributeError: 'list' object has no attribute 'strip'` and
   crash the CLI.

2. **Absolute path in `mcp_config_file` value**. All current tests pass
   relative paths (`./inner.yaml`, `./from-pyproject.yaml`). The
   `if not candidate.is_absolute()` branch is untested.

3. **`test_pyproject_typo_value_raises_fail_loud`** asserts only
   `exit_code == 2`. It does NOT assert the operator-facing error names
   the offending `mcp_config_file` value, the resolved candidate path,
   or the pyproject.toml location. A refactor that swaps to a generic
   "config not found" error message (losing the typo-specific context)
   would not be caught.

**Fix:**
Add three tests:
- `test_pyproject_non_string_value_falls_through_silently`
  (parametrized over `[1, 2]`, `5`, `True`, `None`).
- `test_pyproject_absolute_path_value` exercising the
  `candidate.is_absolute()` branch.
- Extend `test_pyproject_typo_value_raises_fail_loud` to capture stderr
  (via `CliRunner`/`capsys`) and assert the raw value, resolved
  candidate, and pyproject.toml path all appear in the operator copy.

---

_Reviewed: 2026-05-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
