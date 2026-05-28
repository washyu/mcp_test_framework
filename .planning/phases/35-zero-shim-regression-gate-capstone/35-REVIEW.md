---
phase: 35-zero-shim-regression-gate-capstone
reviewed: 2026-05-28T07:08:29Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - tests/framework/test_zero_shim_regression_gate.py
  - tests/framework/test_sdet_rename_leak_gate.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 35: Code Review Report

**Reviewed:** 2026-05-28T07:08:29Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the new behavioral zero-shim regression gate (`test_zero_shim_regression_gate.py`)
and the docstring-edited rename-leak gate (`test_sdet_rename_leak_gate.py`) as test code.
Both gates run green (9 passed in 0.21s) and I cross-referenced every assertion against the
real probed surfaces: `sdet/__init__.py`, `cli.py` (`_sdet_flag_removed`,
`_gen_sdet_classes_removed`), `_deprecated_script.py`, `pyproject.toml`, `config.py`, and
`_plugin.py`. The assertions correctly match current source behavior, so there are no
correctness BLOCKERs. The findings are about **false-negative risk** (gates that could stay
green while a shim is functionally reintroduced or while a leak slips through) and
**brittleness** (gates that go red on benign rewording). Per the review brief, I did NOT flag
the intentional absence of subprocess/network or the deliberately narrow AST scope.

The single most material finding is a regex asymmetry in the rename-leak gate (WR-01): the
negative lookahead protecting the doctrinal `SDET-safety` compound is attached to only one of
two alternatives, so a lowercase spelling would be flagged while the uppercase one is exempt.

## Warnings

### WR-01: `SDET-safety` exemption lookahead applies to only one regex alternative

**File:** `tests/framework/test_sdet_rename_leak_gate.py:25`
**Issue:** The pattern is `re.compile(r"\bsdet\b|\bSDET\b(?!-safety)")`. The negative
lookahead `(?!-safety)` binds only to the **second** alternative (`\bSDET\b`). The first
alternative (`\bsdet\b`) has no lookahead. So the locked doctrinal compound is exempted only
when spelled uppercase. A lowercase `sdet-safety` (or mixed case landing on the lowercase
branch) would match `\bsdet\b` and be reported as a residual leak — a false positive against a
phrase the comment at lines 21-24 explicitly says must NOT be scrubbed. The current tree only
contains uppercase `SDET-safety` (`src/mcp_test_framework/_isolation.py:119`,
`_black_box_guard.py:10`), so the gate passes today, but the exemption is narrower than its
documented intent.
**Fix:** Attach the lookahead to both alternatives, or anchor it after the alternation:
```python
# Option A — lookahead on both branches
SDET_TERM_PATTERN = re.compile(r"\b[sS][dD][eE][tT]\b(?!-safety)")  # noqa: sdet-rename-shim
# Option B — keep case-explicit branches but guard both
SDET_TERM_PATTERN = re.compile(r"(?:\bsdet\b|\bSDET\b)(?!-safety)")  # noqa: sdet-rename-shim
```
Note Option B still only exempts `-safety` (lowercase suffix). If `-Safety` casing should also
be exempt, make the suffix case-insensitive too.

### WR-02: Discovery-surface gate asserts a verbatim sentence substring of `_plugin.py` source

**File:** `tests/framework/test_zero_shim_regression_gate.py:205`
**Issue:** `assert "tests/sdet/ is no longer auto-discovered as of v1.5" in plugin_src`. This is
a plain text scan of source — the exact failure mode the file's own docstring warns against for
the config test (Pitfall 2, lines 92-93). As a *presence* check it is doubly brittle:
(1) **false red on benign rewording** — if someone rephrases the warning to "is not
auto-collected since v1.5" the detector still functionally fires but this gate fails; (2)
**false green** — the same string appears inside the warning body AND would match if it were
left only in a comment with the surrounding `warnings.warn(...)` detector logic deleted. The
test claims to verify "the detector must survive" but actually verifies "a specific sentence of
prose exists somewhere in the file."
**Fix:** Assert on the detector's structure rather than its prose. Reuse the AST-walk approach
already used by `test_fixture_surface_stubs_present`: confirm `pytest_collection` contains a
`glob("test_*.py")` call gated on a `tests/sdet/` path and a `warnings.warn(... DeprecationWarning)`
in the same block. If a literal anchor is preferred for cost reasons, anchor on a stable
path token (`"tests/sdet"`) plus the presence of a `DeprecationWarning` warn call, not a full
English sentence.

### WR-03: CLI gate accepts any exit code 2, not specifically the intercept's rejection

**File:** `tests/framework/test_zero_shim_regression_gate.py:48,56`
**Issue:** Both CLI probes assert only `exit_code == 2`. Click/Typer return exit code 2 for
*any* usage error. The `run` command sets `ignore_unknown_options=True`
(`cli.py:702`), so if `--sdet` were deleted from the signature it would be swallowed as a
passthrough arg and forwarded to pytest — changing the exit code, which this gate would catch.
But the converse weak spot remains: an exit code of 2 produced by an *unrelated* usage error
(e.g., a future required option added to `run`, or a Typer parsing change) would satisfy the
assertion without the `--sdet`/`gen-sdet-classes` intercept actually firing. The gate
intentionally avoids re-pinning message text (D-02), but exit-code-only leaves a specificity
gap between "the shim hard-rejected" and "the command failed for some reason."
**Fix:** Tighten without re-pinning operator copy by asserting a stable structural token that
only the intercept emits. `runner.invoke` captures output; assert the rejection surfaced the
flag/command name, e.g.:
```python
assert r1.exit_code == 2 and "--sdet" in r1.output, (...)  # noqa: sdet-rename-shim
assert r2.exit_code == 2 and "gen-sdet-classes" in r2.output, (...)  # noqa: sdet-rename-shim
```
This pins identity (the intercept fired) without pinning the full operator-tone sentence.

### WR-04: Leak gate skips inline (trailing) comments in src python files

**File:** `tests/framework/test_sdet_rename_leak_gate.py:106-112`
**Issue:** The comment scan only inspects lines where `line.lstrip().startswith("#")` (full-line
comments). A trailing inline comment on a code line — e.g. `allowed = sorted(...)  # sdet
fallback` — is never scanned, because the line does not start with `#` and `ast` does not expose
comments as nodes. The function's docstring (line 69) advertises it scans "docstrings + string
literals + comments," but inline comments are a real subset it misses. This is a false-negative
gap: an operator-visible-adjacent `sdet`/planning-ID token in a trailing comment inside `src/`
would slip past the gate. (Current src has no such offending inline comment, so the gate is
green today, but the coverage gap is real and contradicts the docstring's stated scope.)
**Fix:** Use `tokenize.generate_tokens` to enumerate all `COMMENT` tokens (full-line and inline)
with accurate line numbers, replacing the `startswith("#")` heuristic. Apply the same
`NOQA_MARKER` line-exclusion. Alternatively, narrow the docstring to "full-line comments" so the
stated scope matches the implementation — but tokenize is the more robust fix given this is an
acceptance gate.

## Info

### IN-01: Redundant bytes round-trip when reading pyproject.toml

**File:** `tests/framework/test_zero_shim_regression_gate.py:72`
**Issue:** `tomllib.loads((REPO_ROOT / "pyproject.toml").read_bytes().decode())` reads bytes,
decodes to str, then calls `tomllib.loads`. `tomllib` is designed to consume bytes directly via
`tomllib.load(fileobj)` opened in binary mode, which also correctly handles the TOML-mandated
UTF-8 + BOM rules. The `.decode()` here relies on the platform default codec being UTF-8 (true
on this project's CPython 3.14, but implicit).
**Fix:** `data = tomllib.load((REPO_ROOT / "pyproject.toml").open("rb"))` or
`tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))`.

### IN-02: Import-surface probe can pass green if the shim breaks for an unrelated import error

**File:** `tests/framework/test_zero_shim_regression_gate.py:37`
**Issue:** `pytest.raises((ModuleNotFoundError, ImportError))` is broad. A functional
reintroduction of `sdet/__init__.py` that re-exports symbols would correctly flip this red
(no exception raised). But if a reintroduced shim re-exported from a module that *itself* failed
to import (raising `ModuleNotFoundError`/`ImportError` for an unrelated reason), the gate would
stay green while the shim is partially back. Low likelihood given the current stub raises
`ModuleNotFoundError` at module-body level, but the assertion does not distinguish "removed
surface" from "broken reintroduction."
**Fix:** Optionally assert the raised message carries the removal pointer token (e.g.
`match="removed in v1.5"`) so an unrelated import failure does not masquerade as a clean
removal. This re-pins a small substring, so weigh against the D-02 no-message-text constraint;
if that constraint dominates, leave as-is and accept the edge case.

### IN-03: Fixture-surface AST walk treats any `pytest.fail`/`fail()` call anywhere in the body as proof of a stub

**File:** `tests/framework/test_zero_shim_regression_gate.py:167-174`
**Issue:** `ast.walk(node)` descends the entire function body and matches the first call to a
function named `fail` (attribute `.fail` or bare `fail`). A reintroduced shim that did real work
and *also* called `pytest.fail` deep in an error branch (or any nested helper named `fail`)
would satisfy the "stub present" assertion even though the fixture is no longer a pure
hard-reject stub. The intended contract per the docstring is "body immediately calls
pytest.fail." Matching anywhere in the subtree is looser than that contract.
**Fix:** Constrain to the first statement of the body, e.g. inspect `node.body[0]` for an
`ast.Expr` whose `.value` is a `Call` to `*.fail`, rather than walking the whole subtree. This
makes "re-aliasing with a real return that happens to also call fail somewhere" flip the gate
red as intended.

---

_Reviewed: 2026-05-28T07:08:29Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
