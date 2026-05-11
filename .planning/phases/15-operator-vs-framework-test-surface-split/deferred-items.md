# Phase 15 — Deferred Items

## From Plan 15-02 execution

### test_plugins_list_does_not_register_reporter path bug

**File:** `tests/framework/test_runner_subprocess.py::test_plugins_list_does_not_register_reporter`

**Issue:** The test computes `repo_root = Path(__file__).resolve().parents[1]` and reads `repo_root / "tests" / "conftest.py"`. Before Plan 15-01, when the file was at `tests/test_runner_subprocess.py`, `parents[1]` was the project root. After the Plan 15-01 move to `tests/framework/test_runner_subprocess.py`, `parents[1]` is now `tests/` itself, so the fallback path resolves to `tests/tests/conftest.py` which does not exist. Result: the test fails with `FileNotFoundError` whenever the inner `spec.loader.exec_module(module)` raises (which it does in this environment due to conftest side-effects).

**Root cause:** Pre-existing failure introduced by Plan 15-01's file relocation; not caused by Plan 15-02 changes. Verified by `git stash`-ing Plan 15-02 edits and reproducing the same failure.

**Fix:** Update the path computation to `Path(__file__).resolve().parents[2]` to skip the new `framework/` segment, OR drop the path-based fallback in favor of a pure text grep that opens the conftest via the same module-spec path.

**Recommended owner:** Plan 15-04 (verification / fixup) or a follow-up quick task.
