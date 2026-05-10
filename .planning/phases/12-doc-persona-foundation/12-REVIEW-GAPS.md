---
phase: 12-doc-persona-foundation
reviewed: 2026-05-09T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/mcp_test_framework/cli.py
  - tests/unit/test_cli_errors.py
  - tests/unit/test_config.py
  - tests/unit/test_config_init.py
  - tests/unit/test_doc_scrub.py
  - tests/unit/test_dotenv_example.py
findings:
  blocker: 0
  warning: 5
  total: 5
status: issues_found
---

# Phase 12 Gap-Closure Code Review (12-07 / 12-08 / 12-09)

**Reviewed:** 2026-05-09
**Depth:** standard
**Diff base:** 209726c (gap-closure plans 12-07/08/09)
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the gap-closure changes for plans 12-07 (UAT gap 1: doc/runtime
agreement), 12-08 (UAT gap 2: `--command/--arg` bootstrap + fallback scaffold),
and 12-09 (UAT gap 3: doc invocation pairing). Source changes are confined to
`src/mcp_test_framework/cli.py` (config-init flag additions + fallback
scaffold path); the rest are new tests.

No blockers. Five warnings — all about robustness, test fragility, or
maintainability rather than incorrect runtime behavior. The largest concrete
risk is WR-01: the recovery path advertised in the fallback scaffold's header
is mechanically broken because re-running `config-init -o <path>` will hit
the refuse-to-overwrite gate without `--force`.

## Warnings

### WR-01: Fallback scaffold header advertises a recovery path that the refuse-to-overwrite gate will reject

**File:** `src/mcp_test_framework/cli.py:496-509`
**Issue:**
The fallback scaffold's header instructs the operator to:

> "Fill in `mcp_server.command` (and any required `mcp_server.args`) so the launch command resolves on PATH, then re-run `mcp-test-framework config-init` to populate the tool list."

But the refuse-to-overwrite gate at `cli.py:449-456` rejects an `-o PATH`
invocation when `PATH` already exists and `--force` is not set. After the
fallback scaffold is written to `out.yaml`, the literal command in the
header (`mcp-test-framework config-init`) cannot be re-run with the same
`-o` because the file now exists. The advertised recovery is therefore a
trap — the operator will hit a second operator-tone error and have to
discover `--force` independently.

This also conflicts with the doc-pairing guard in `test_doc_scrub.py:158`:
the suggested re-run lacks `--config`, but here `--config` is genuinely
unavailable (the operator was bootstrapping). The header's bare command
form is correct for the bootstrap case; the missing piece is `--force`.

**Fix:** Either (a) update the header to spell out the re-run with the
flags the operator must use, e.g.:

```python
header = (
    "# mcp-test-framework starter config -- TOOL DISCOVERY FAILED.\n"
    "# The framework could not launch your MCP server, so the\n"
    "# `tools:` block below is empty. Fill in `mcp_server.command`\n"
    "# (and any required `mcp_server.args`) so the launch command\n"
    "# resolves on PATH, then re-run with `--force` and a working\n"
    "# `--command` / `--arg` (or pass `--config <this-file>`):\n"
    "#   mcp-test-framework config-init --command <CMD> --arg <ARG> -o <THIS_FILE> --force\n"
    ...
)
```

Or (b) write the fallback to a `.fallback` sibling path and instruct the
operator to copy/edit, leaving the `--output` slot free for the next attempt.

---

### WR-02: FileNotFoundError detection by string-prefix match is brittle

**File:** `src/mcp_test_framework/cli.py:352, 510`
**Issue:**
Both `list-tools` and `config-init` distinguish "command not on PATH" from
generic launch failures via:

```python
if str(exc).startswith("MCP server command not on PATH:"):
```

This relies on an exact prefix from `McpTestClient.__aenter__`. If that
message ever changes punctuation, capitalization, or wording, the branch
silently falls through to the generic "MCP server failed to start" path
without any test catching the regression. The new tests
(`test_list_tools_mcp_spawn_failure`, `test_config_init_mcp_spawn_failure`)
only assert "MCP server" appears in stderr, which matches BOTH branches —
so a silent regression to the generic path would pass.

**Fix:** Either (a) raise a typed exception subclass from McpTestClient
(e.g., `class CommandNotOnPathError(FileNotFoundError)`) and `except
CommandNotOnPathError` on it; or (b) add a test that asserts the
specific-branch detail — the `f"`{cfg.mcp_server.command} {...}`"` line —
is present in stderr only when the bogus command path is exercised. Option
(a) is more durable.

---

### WR-03: `test_emit_operator_error_returns_no_return_annotation` checks against the wrong sentinel

**File:** `tests/unit/test_cli_errors.py:63-70`
**Issue:**
The assertion:

```python
assert sig.get("return") in (typing.NoReturn, type(None).__class__) or \
       getattr(sig.get("return"), "__name__", "") == "NoReturn"
```

`type(None).__class__` evaluates to `type` (the metaclass), not `NoneType`
as appears intended. So the tuple is effectively
`(typing.NoReturn, type)` — both members are bogus comparison targets
when `typing.get_type_hints` returns `NoReturn`. The test only passes
because the `or` clause names-checks `"NoReturn"`. The first half of the
disjunction is dead.

If a contributor tightens `_emit_operator_error`'s annotation in a way
that the `__name__` clause stops reporting `"NoReturn"` (e.g., a
`TypeAlias`), the broken first half won't catch it.

**Fix:** Replace with a meaningful check:

```python
import typing
sig = typing.get_type_hints(_emit_operator_error, include_extras=False)
ret = sig.get("return")
# typing.NoReturn normalizes consistently across 3.10+; assert directly.
assert ret is typing.NoReturn, f"expected NoReturn, got {ret!r}"
```

If `typing.Never` is also acceptable for forward-compat, allow both:
`assert ret in {typing.NoReturn, typing.Never}`.

---

### WR-04: `test_config_init_command_arg_flags_override_defaults` does not isolate cwd

**File:** `tests/unit/test_config_init.py:155-194`
**Issue:**
The test calls `_clear_spec_env(monkeypatch)` but does NOT
`monkeypatch.chdir(tmp_path)`. `_load_config(None)` then runs from
whatever cwd the developer/CI invoked pytest from. If that cwd contains a
`.env` (which the repo does have at root), Pydantic-settings will read it
via the project's `_BareNameNestedEnvSource`. A `.env` line like
`MCP_SERVER_COMMAND=homelab-mcp` would normally be benign, but a
contributor's local `.env` could absolutely break this test.

The sibling test `test_config_init_fallback_scaffold_not_written_in_stdout_mode`
DOES `monkeypatch.chdir(tmp_path)` — the inconsistency is the smell.

Compare: `test_config.py::_isolate_cwd` is `autouse=True` precisely to
prevent this leakage; the new `test_config_init.py` tests are missing the
same guard.

**Fix:** Add an `autouse` chdir fixture at module scope:

```python
@pytest.fixture(autouse=True)
def _isolate_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
```

Then drop the per-test `monkeypatch.chdir(tmp_path)` in
`test_config_init_fallback_scaffold_not_written_in_stdout_mode`.

The same gap exists in `tests/unit/test_cli_errors.py` (e.g.,
`test_config_init_fallback_scaffold_no_banned_tokens` at line 212-238).

---

### WR-05: `--command ""` / `--arg ""` bypass any future validation via `model_copy`

**File:** `src/mcp_test_framework/cli.py:465-473`
**Issue:**
`Pydantic v2 model_copy(update=...)` does NOT re-run validators by
default. Today this is benign — `McpServerConfig.command` carries no
`min_length` / `pattern` constraint and `args` is just `list[str]` — but
the override path silently sidesteps any future validator the team adds
to those fields. A contributor adding e.g. `command: str = Field(...,
min_length=1)` to `McpServerConfig` will not see `--command ""` rejected;
they will see a runtime error at subprocess-launch time instead, after
`_load_config` has already returned a "valid" Config.

**Fix:** Either (a) construct a fresh `McpServerConfig` via
`model_validate({**cfg.mcp_server.model_dump(), **overrides})` to force
validators to run, or (b) document the bypass with a comment and add a
test that empty `--command ""` is rejected (forcing future validators to
align with operator expectations). Option (a) is the safer path:

```python
if command is not None or arg is not None:
    overrides: dict[str, object] = {}
    if command is not None:
        overrides["command"] = command
    if arg is not None:
        overrides["args"] = list(arg)
    new_mcp = McpServerConfig.model_validate(
        {**cfg.mcp_server.model_dump(), **overrides}
    )
    cfg = cfg.model_copy(update={"mcp_server": new_mcp})
```

---

_Reviewed: 2026-05-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
