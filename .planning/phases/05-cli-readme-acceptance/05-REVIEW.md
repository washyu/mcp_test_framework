---
phase: 05-cli-readme-acceptance
reviewed: 2026-05-06T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - src/mcp_test_framework/cli.py
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-05-06T00:00:00Z
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Reviewed `src/mcp_test_framework/cli.py` (Plans 05-01 / 05-02 / 05-03) at standard
depth. The CLI surface is small, well-commented, and the core wiring works as
intended (verified by invoking `version`, `run --help`, `list-tools --help`, and
`run -- -k foo -v` against a mocked `pytest.main`). No security issues and no
crashes found in the happy path.

However, several quality and robustness issues are worth addressing:

- The `pytest_args` parameter is typed `list[str]` but defaults to `None` --
  Pydantic/mypy wouldn't accept this and a careful reader has to chase the
  `or []` rescue.
- Two mutational side effects can leak across invocations or test sessions
  (`os.environ["MCPTF_CONFIG_FILE"]` is set without ever being cleaned up; the
  env mutation also happens *before* `Config()` validates).
- `_format_tools_json` is asymmetrically defensive (`t.inputSchema` raises if
  the SDK renames it, but `getattr(t, "outputSchema", None)` would silently
  emit `None`), and uses `default=str` which can mask non-JSON schema content
  rather than failing loudly.
- Two docstring claims are not enforced by code: the SIGINT-to-130 guarantee on
  the `list-tools` path, and the "full MCP tool records" wording (the JSON
  emitter actually drops `title`, `icons`, `annotations`, `meta`, `execution`).

No blockers; ship-ready after addressing the warnings.

## Warnings

### WR-01: `pytest_args` typed as `list[str]` but defaults to `None`

**File:** `src/mcp_test_framework/cli.py:92-95`
**Issue:** `pytest_args: list[str] = typer.Argument(None, ...)` -- the static
type says `list[str]` but the default is `None`. This is a type-annotation
contradiction; the `forwarded = list(pytest_args or [])` line on L118 exists
solely to paper over it. A future reader (or mypy in strict mode) will flag
this immediately, and a refactor that removes the `or []` rescue will silently
break for the no-extras invocation.
**Fix:**
```python
pytest_args: list[str] | None = typer.Argument(
    None,
    help="Args after `--` are forwarded to pytest.main([\"tests\", *args]).",
),
```
(Or use `typer.Argument(default_factory=list)` and drop the `or []` rescue.)

### WR-02: `_load_config` mutates `os.environ` before `Config()` validates and never cleans up

**File:** `src/mcp_test_framework/cli.py:72-77`
**Issue:** When `--config PATH` is provided, `os.environ["MCPTF_CONFIG_FILE"]`
is set unconditionally and is never unset, even if `Config()` subsequently
raises a `ValidationError`. Two consequences:

1. **Test isolation:** any test that imports/invokes `_load_config` (e.g.,
   the smoke tests under `tests/smoke/`) will leak the env var into every
   subsequent test in the same process. A previous test's bad config path
   silently tints the next test.
2. **Stale value on retry:** if a user runs `list-tools --config /first/path`
   (which fails validation) followed by `list-tools` (no `--config` flag) in
   the same shell-less harness (e.g., a Python wrapper), the second call will
   still pick up `/first/path` from the leaked env var.

For the `run` command this is intentional (the env var must survive into
`pytest.main`'s plugin chain so fixtures see it), but for `list-tools` the env
var only needs to exist for the duration of the `Config()` constructor call.
**Fix:** scope the env mutation, or document the leak explicitly. Minimal
patch -- pop the var on error, leave it set on success (since `pytest.main`
needs it on the `run` path):
```python
def _load_config(path: Path | None) -> Config:
    if path is not None:
        if not path.is_file():
            typer.echo(f"error: --config path not found: {path}", err=True)
            raise typer.Exit(code=2)
        os.environ["MCPTF_CONFIG_FILE"] = str(path)
        try:
            return Config()
        except Exception:
            os.environ.pop("MCPTF_CONFIG_FILE", None)
            raise
    return Config()
```
At minimum, add a docstring note that the env var leaks on success and is
intentionally so for the `run` path.

### WR-03: Asymmetric defensive attribute access on `Tool` records

**File:** `src/mcp_test_framework/cli.py:222-225`
**Issue:** Inside `_format_tools_json`, `t.inputSchema` is a direct attribute
access while `t.outputSchema` uses `getattr(t, "outputSchema", None)`. Both
fields are declared on the current `mcp.types.Tool` model (verified against
the installed SDK -- both are `model_fields`), so the `getattr` default is
dead code today. The asymmetry creates a hazard:

- If the SDK is ever upgraded and renames `inputSchema` to `input_schema`,
  the line raises `AttributeError` and the whole JSON path crashes.
- If `outputSchema` is similarly renamed, the JSON path silently emits
  `None` for every tool with no error -- a much harder failure to detect.

Pick one stance, not two.
**Fix:** use the same access pattern for both. Since both fields are declared
on `Tool`, prefer direct access (no defensive default needed):
```python
payload = [
    {
        "name": t.name,
        "description": t.description,
        "inputSchema": t.inputSchema,
        "outputSchema": t.outputSchema,
    }
    for t in sorted_tools
]
```

### WR-04: `json.dumps(..., default=str)` masks non-serializable schema content

**File:** `src/mcp_test_framework/cli.py:229`
**Issue:** The comment ("`default=str` is a defensive fallback for any
non-serializable annotation values inside schemas") rationalizes silently
stringifying anything `json` can't handle. But MCP tool `inputSchema` /
`outputSchema` are JSON Schema documents -- they MUST be JSON-serializable by
contract. If the SDK ever exposes a non-JSON value in a schema (or a future
schema validator inserts a compiled regex / sentinel object), `default=str`
will paper over a real spec violation and emit semantically wrong JSON
without a crash.
**Fix:** drop `default=str` and let `json.dumps` raise `TypeError` on
unexpected content. A hard failure here is the correct signal that the SDK
or schema is malformed:
```python
return json.dumps(payload, indent=2) + "\n"
```

### WR-05: Docstring claims SIGINT exit code 130 but no code enforces it

**File:** `src/mcp_test_framework/cli.py:144-147`
**Issue:** The `list-tools` docstring asserts: "KeyboardInterrupt propagates
through the runner ... exit code 130 with no message printed (D-teardown-3)."
There is no explicit `KeyboardInterrupt` handler in this function. When Typer
runs in its default `standalone_mode=True`, a `KeyboardInterrupt` raised out
of `runner.run(...)` is caught by Click and converted to exit code 1 (via
`Abort`), not 130 -- not by the Python default `SIGINT` handler. The actual
runtime behavior may match the docstring on POSIX but diverge on Windows
(which has no real SIGINT) or under console-script wrappers.

This is a **claims-without-evidence** issue: the comment looks authoritative
but is not validated by a test in this phase, and the implementation does not
enforce it.
**Fix:** either (a) add a manual SIGINT integration test that asserts exit
code 130, or (b) downgrade the comment to "KeyboardInterrupt propagates;
exit code is whatever the Click/Typer runner produces" and remove the 130
guarantee. If the intent is to actually guarantee 130:
```python
try:
    with asyncio.Runner() as runner:
        tools = runner.run(_list_tools_async(cfg))
except KeyboardInterrupt:
    raise typer.Exit(code=130)
```

## Info

### IN-01: `_format_tools_json` advertises "full MCP tool records" but drops fields

**File:** `src/mcp_test_framework/cli.py:212-229`
**Issue:** Docstring on L213 says "Full MCP tool record per tool" and lists
`{name, description, inputSchema, outputSchema}`. The actual `mcp.types.Tool`
model has nine fields: `name, title, description, inputSchema, outputSchema,
icons, annotations, meta, execution`. The JSON emitter drops five of them.
This may be an intentional slim shape, but the wording "full" is misleading.
**Fix:** rename the field list in the docstring -- e.g., "the four
spec-essential fields ({name, description, inputSchema, outputSchema}) per
tool" -- or extend the payload to include the dropped fields if downstream
consumers need them.

### IN-02: `version` command catches `PackageNotFoundError` but not `ImportError`

**File:** `src/mcp_test_framework/cli.py:161-165`
**Issue:** The fallback path does `from mcp_test_framework import __version__
as v` inside the `except metadata.PackageNotFoundError` block. If
`__version__` is ever removed from `__init__.py`, the fallback raises an
uncaught `ImportError` -- a crash for an end-user `version` invocation. Today
`__version__` is defined as `"0.1.0"`, so this is theoretical.
**Fix:** harden the fallback or simplify to a single source of truth:
```python
try:
    v = metadata.version("mvp-test-framework")
except metadata.PackageNotFoundError:
    try:
        from mcp_test_framework import __version__ as v
    except ImportError:
        v = "unknown"
typer.echo(v)
```
Alternatively: just always read `__version__` and skip the metadata lookup
(the version is duplicated in `pyproject.toml` and `__init__.py` already, so
the metadata path adds no value).

### IN-03: Empty callback `return None` is redundant

**File:** `src/mcp_test_framework/cli.py:51-61`
**Issue:** `_main` has an explicit `return None` which is redundant -- a
function with no `return` statement returns `None` implicitly. The docstring
above it is excellent and explains why the callback exists; the body should
just be `pass` or omit the `return`.
**Fix:**
```python
@app.callback()
def _main() -> None:
    """..."""
    # callback exists only to lock multi-command mode; no behavior
```

### IN-04: Distribution-name-vs-package-name comment is duplicated

**File:** `src/mcp_test_framework/cli.py:21-25, 162`
**Issue:** The "distribution name vs package name" warning appears twice --
once in the module docstring (L21-25) and once as an inline comment on
L162. Both are accurate; one is sufficient. The inline comment is the more
likely place a future reader looks (it's at the call site), so the module
docstring block is the redundant copy.
**Fix:** remove the module-docstring duplicate (L21-25) and keep the inline
comment on L162. This is purely cosmetic.

---

_Reviewed: 2026-05-06T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
