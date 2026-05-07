---
phase: 05-cli-readme-acceptance
fixed_at: 2026-05-06T00:00:00Z
review_path: .planning/phases/05-cli-readme-acceptance/05-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 4
status: all_fixed
---

# Phase 05: Code Review Fix Report

**Fixed at:** 2026-05-06T00:00:00Z
**Source review:** `.planning/phases/05-cli-readme-acceptance/05-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope (Critical + Warning): 5
- Fixed: 5
- Skipped: 4 (all Info severity, out of default fix scope)

All five Warning findings from REVIEW.md were applied successfully and
committed atomically. The four Info findings were left for a follow-up
pass per the configured `fix_scope: critical_warning`.

## Fixed Issues

### WR-01: `pytest_args` typed as `list[str]` but defaults to `None`

**Files modified:** `src/mcp_test_framework/cli.py`
**Commit:** `f15de64`
**Applied fix:** Changed the parameter annotation on `run`'s
`pytest_args` from `list[str]` to `list[str] | None`. The `None` default
is now expressed in the static type, eliminating the contradiction
between the annotation and the runtime default. The `forwarded =
list(pytest_args or [])` rescue on what was L118 is now consistent with
the annotation rather than papering over it.

### WR-02: `_load_config` mutates `os.environ` and never cleans up

**Files modified:** `src/mcp_test_framework/cli.py`
**Commit:** `ba81b3c`
**Applied fix:** Wrapped `Config()` construction in a `try`/`except`
inside the `path is not None` branch. On `Config()` failure the
`MCPTF_CONFIG_FILE` env var is popped before re-raising, preventing a
stale path from leaking into subsequent CLI invocations or test runs in
the same process. On success the env var is intentionally retained so
the `run` path's `pytest.main()` plugin chain still observes the YAML
overlay -- this contract is now spelled out in the docstring. Matches
the suggested patch verbatim.

### WR-03: Asymmetric attribute access on `Tool` records

**Files modified:** `src/mcp_test_framework/cli.py`
**Commit:** `f2ebe88`
**Applied fix:** Replaced `getattr(t, "outputSchema", None)` with
direct attribute access (`t.outputSchema`) in `_format_tools_json`,
matching the style already used for `inputSchema`. Both fields are
declared on `mcp.types.Tool`, so the `getattr` default was dead code;
removing it ensures the JSON path will surface a loud `AttributeError`
if the SDK ever renames either field, eliminating the silent-`None`
hazard.

### WR-04: `default=str` masks non-serializable schema content

**Files modified:** `src/mcp_test_framework/cli.py`
**Commit:** `0b86565`
**Applied fix:** Removed `default=str` from the `json.dumps` call in
`_format_tools_json`. MCP tool `inputSchema` / `outputSchema` are JSON
Schema documents and MUST be JSON-serializable by contract; an
unexpected non-serializable value now raises `TypeError` instead of
being silently coerced to a string. Updated the docstring rationale to
state the contract explicitly and call out that a `TypeError` here is
the correct signal that the SDK or schema is malformed.

### WR-05: SIGINT exit-code-130 docstring claim not enforced

**Files modified:** `src/mcp_test_framework/cli.py`
**Commit:** `deaf6b3`
**Applied fix:** Wrapped the `asyncio.Runner()` block in `list_tools`
with `try` / `except KeyboardInterrupt` and re-raised as
`typer.Exit(code=130)`. This enforces the existing docstring guarantee
explicitly rather than relying on Click's default `standalone_mode`
behavior (which converts `KeyboardInterrupt` to exit code 1 via
`Abort`). A docstring comment notes the rationale and that the
explicit handler unifies behavior across POSIX and Windows
console-script wrappers. This was the user-recommended option (b) from
the review.

## Skipped Issues

### IN-01: `_format_tools_json` advertises "full MCP tool records" but drops fields

**File:** `src/mcp_test_framework/cli.py:212-229`
**Reason:** Info severity, not in default fix scope (`fix_scope:
critical_warning`).
**Original issue:** Docstring says "Full MCP tool record per tool" but
the emitter drops `title`, `icons`, `annotations`, `meta`, `execution`.
Either the wording should be tightened to "the four spec-essential
fields" or the payload should be extended.

### IN-02: `version` command catches `PackageNotFoundError` but not `ImportError`

**File:** `src/mcp_test_framework/cli.py:161-165`
**Reason:** Info severity, not in default fix scope (`fix_scope:
critical_warning`).
**Original issue:** If `__version__` is ever removed from
`__init__.py`, the fallback raises an uncaught `ImportError`. Today
`__version__ = "0.1.0"` so this is theoretical.

### IN-03: Empty callback `return None` is redundant

**File:** `src/mcp_test_framework/cli.py:51-61`
**Reason:** Info severity, not in default fix scope (`fix_scope:
critical_warning`).
**Original issue:** `_main` has an explicit `return None` which is
redundant -- a function with no `return` statement returns `None`
implicitly.

### IN-04: Distribution-name-vs-package-name comment is duplicated

**File:** `src/mcp_test_framework/cli.py:21-25, 162`
**Reason:** Info severity, not in default fix scope (`fix_scope:
critical_warning`).
**Original issue:** The "distribution name vs package name" warning
appears twice -- once in the module docstring and once as an inline
comment on L162. One copy is sufficient; cosmetic.

---

_Fixed: 2026-05-06T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
