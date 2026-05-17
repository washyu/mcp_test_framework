---
phase: 28-codegen-output-path-codegen
fixed_at: 2026-05-16T00:00:00Z
review_path: .planning/phases/28-codegen-output-path-codegen/28-REVIEW.md
iteration: 1
fix_scope: user_selected
findings_in_scope: 4
fixed: 4
skipped: 2
status: all_fixed
---

# Phase 28: Code Review Fix Report

**Fixed at:** 2026-05-16
**Source review:** .planning/phases/28-codegen-output-path-codegen/28-REVIEW.md
**Iteration:** 1
**Fix scope:** user_selected (WR-02, WR-03, WR-04, WR-06)

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped (out-of-scope): 2 (WR-01 deferred, WR-05 user-declined)

All four in-scope warnings were fixed and committed atomically. Full
`tests/framework/` regression sweep at 637 passed / 1 skipped / 1 xfailed
after the four commits land — five tests above the pre-fix baseline of
632, accounting for the 13 new test cases added across the four fixes
(some replace prior assertions in-place rather than add new test ids).

## Fixed Issues

### WR-03: 1000-entry cap suffix off-by-one

**Files modified:** `src/mcp_test_framework/cli.py`, `tests/framework/unit/test_gen_test_classes_overwrite_prompt.py`
**Commit:** 604b2a1
**Applied fix:** Replaced `if len(files) >= 1000: break` with
`if len(files) > CAP: break` (CAP=1000), and replaced the post-loop
counters with `file_count = min(len(files), CAP)` /
`suffix = "+" if len(files) > CAP else ""`. The loop now appends one
entry past the cap so the "+" suffix accurately reflects whether
overflow occurred. Added a parametrized boundary test covering
`(999, "999", "")`, `(1000, "1000", "")`, `(1001, "1000", "+")` using
`monkeypatch.setattr(Path, "iterdir", lambda self: iter(fake_entries))`
to control entry count without creating thousands of real files.

### WR-02: OSError branch must fail loud, not silently skip the prompt

**Files modified:** `src/mcp_test_framework/cli.py`, `tests/framework/unit/test_gen_test_classes_overwrite_prompt.py`
**Commit:** 33d3bc9
**Applied fix:** Converted the `except OSError: return` branch in
`_confirm_or_abort_non_empty_target` into an `_emit_operator_error`
call that names the target path, the underlying OSError, and the
remediation (fix permissions or change `test_code.generated_root`).
This resolves the comment-vs-code mismatch in-place (the misleading
"fall through to the prompt anyway" comment is gone) and preserves the
safety gate as the load-bearing check rather than deferring failure to
codegen's wipe-and-write step. Added a unit test using
`monkeypatch.setattr(Path, "iterdir", ...)` to simulate
`PermissionError`; asserts exit code 2 plus the path, cause, and
remediation copy appear in stderr/stdout.

### WR-04: pyproject.toml lookup is cwd-only; library-mode pytest walks upward

**Files modified:** `src/mcp_test_framework/cli.py`, `tests/framework/unit/test_gen_test_classes_pyproject_config.py`
**Commit:** e20b064
**Applied fix:** Added `_find_pyproject_upward(start: Path) -> Path | None`
helper that walks from `start` through `start.parents` looking for
`pyproject.toml` (mirrors pytest's rootpath discovery). Wired into the
Branch 1.5 call site in `_load_config` so
`_read_mcp_config_file_from_pyproject` is now called with the
discovered pyproject's parent directory rather than the bare cwd. The
helper signature stays the same — only the call site changed. Added
four tests: helper finds pyproject at start, helper finds two levels
up, defensive negative test for no-pyproject-anywhere (with comment
explaining why the runner's own pyproject ancestry is not a false
positive), and the load-bearing end-to-end test where `pyproject.toml`
lives in `tmp_path` and cwd is `tmp_path / "sub" / "subsub"`.

### WR-06: Test gaps around `_read_mcp_config_file_from_pyproject`

**Files modified:** `tests/framework/unit/test_gen_test_classes_pyproject_config.py`
**Commit:** f4e90b5
**Applied fix:** Three test additions to lock undocumented helper
behavior:
1. `test_pyproject_non_string_value_falls_through_silently` —
   parametrized over `[1, 2]`, `5`, `true`, `{ key = "val" }` (TOML
   inline table). Substitutes the in-TOML literal directly rather than
   going through the helper's string-quote wrapper, so the
   `isinstance(raw, str)` guard's fall-through is genuinely exercised.
   Note: `None` is omitted because TOML has no null literal; the
   equivalent ("key absent entirely") is already covered by
   `test_pyproject_without_ini_options_section_falls_through`.
2. `test_pyproject_absolute_path_value` — writes an absolute path into
   pyproject (Windows-safe escape of backslashes), chdirs to an
   unrelated directory, verifies the resolved config matches the
   absolute path verbatim (no pyproject-parent join).
3. Extended `test_pyproject_typo_value_raises_fail_loud` to capture
   stderr/stdout via `capsys` and assert the raw ini value
   (`./does-not-exist.yaml`), the resolved candidate path
   (`tmp_path / does-not-exist.yaml`), and the pyproject.toml location
   (`tmp_path / pyproject.toml`) all appear in the operator copy. A
   refactor that swaps to a generic "config not found" message would
   now fail the test rather than silently degrading operator UX.

Used `capsys` rather than `CliRunner` for the typo test because the
helper is being called directly (not via a Typer subcommand). `capsys`
captures the same stderr `_emit_operator_error` writes, with no extra
ceremony, matching the pattern used by other direct-helper tests in
this file.

## Skipped Issues

### WR-01: Operator next-step copy points at legacy `mcp-test-framework` CLI name on five branches

**File:** `src/mcp_test_framework/cli.py:294-297, 326-329, 449-453, 481-484, 508-511`
**Reason:** Out of scope per user instruction — the five legacy
`mcp-test-framework config-init` strings are pinned verbatim by
`tests/framework/unit/test_error_style.py` against
`docs/ERROR-STYLE.md`. Phase 28-03's deviation note already deferred
this rename to v1.5 (when the legacy CLI shim drops). Fixing here
would break the pinned regression test without an accompanying
docs/ERROR-STYLE.md update, which is itself v1.5-scoped.
**Original issue:** Five operator-facing `next_step` strings in
`_load_config` and `_emit_operator_error_for_validation` still name
the deprecated `mcp-test-framework config-init` while the new
pyproject branch (L391-394) and missing-required-field branch
(L309-311) use the canonical `mcp-contracts config-init`. Self-inconsistent.

### WR-05: Site-packages guard ignores `framework_install_root.parent.parent` for non-src layouts

**File:** `src/mcp_test_framework/cli.py:122-128`
**Reason:** Out of scope per user instruction — the user declined the
fix; the current heuristic stays.
**Original issue:** The two-level walk
`Path(mcp_test_framework.__file__).resolve().parent.parent` assumes a
parent directory exists above the package directory that is the right
boundary to block. A project-root-vendored copy (no `src/` shim) would
make the guard block any `generated_root` anywhere in the operator's
project. The current test suite only exercises the editable-src
layout, so both code and tests share the assumption without verifying
it.

---

_Fixed: 2026-05-16_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
