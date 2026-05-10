---
phase: 12-doc-persona-foundation
reviewed: 2026-05-09T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - .env.example
  - README.md
  - config.example.yaml
  - docs/ERROR-STYLE.md
  - docs/EXTENDING.md
  - examples/README.md
  - examples/homelab-mcp.yaml
  - src/mcp_test_framework/cli.py
  - src/mcp_test_framework/fixtures.py
  - tests/unit/test_cli_errors.py
  - tests/unit/test_config_example.py
  - tests/unit/test_config_init.py
  - tests/unit/test_doc_scrub.py
  - tests/unit/test_dotenv_example.py
  - tests/unit/test_error_style.py
  - tests/unit/test_examples_dir.py
  - tests/unit/test_judge_errors.py
  - tests/unit/test_list_tools_format.py
findings:
  blocker: 2
  warning: 6
  total: 8
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-05-09
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Phase 12 lands a `config-init` subcommand, an operator-tone error helper in `cli.py`, parallel error rewrites in `fixtures.py`, and a Wave-0 doc-scrub regression suite. The error-message rewrites are competently structured, the test scaffolding is dense, and the docs (`README.md`, `EXTENDING.md`, `config.example.yaml`, `.env.example`) are well-scrubbed of planning artefacts.

However, the doc-scrub mission has a **hole**: `examples/homelab-mcp.yaml` — the file Phase 12 explicitly promotes as the "complete worked example" linked from both `README.md` and `config.example.yaml` — is saturated with phase IDs (`Phase 07`, `Phase 08`, `Phase 04/05/08`), spec IDs (`TOOLCFG-01..07`, `CD-05`, `SEED-004`, `TEST-08`), and quick-task IDs (`260507-n0g`). No regression test covers it, so the next doc-scrub phase will discover this on a future run.

A second BLOCKER lives in `_emit_operator_error_for_validation`: the version-mismatch path inlines pydantic's raw `msg` field, which on this codebase reliably contains the literal token `"Value error, "` — pydantic's own internal jargon that ERROR-STYLE.md rule 1 explicitly forbids. The existing test guards against the lowercase `"value_error"` form (pydantic v1 type-string), missing the v2 prose form.

Remaining issues are quality defects: a `NoReturn` annotation gap in `fixtures.py`, a dead/misleading `target.tool_name` "removed in v1.2" branch (the field is not actually removed), inconsistent expression parenthesization in `_format_tools_text`, a fragile relative-path read in a test, and a too-permissive empty-mapping assertion that allows `tools: None` to pass.

## Blocker Issues

### BL-01: examples/homelab-mcp.yaml leaks 18+ planning IDs into the operator-facing example

**File:** `examples/homelab-mcp.yaml:17,23,31,35,44,45,52,66`
**Issue:** Phase 12's CLEAN-01 / CLEAN-04 / doc-scrub mission requires user-facing files to carry zero spec IDs / phase IDs / quick-task IDs. `README.md`, `config.example.yaml`, `.env.example`, and `docs/EXTENDING.md` all have regression tests asserting this (`test_doc_scrub.py`, `test_config_example_no_banned_tokens`, `test_dotenv_example_no_banned_tokens`). But `examples/homelab-mcp.yaml` — explicitly linked as "the complete worked reference" from both `README.md` (line 238) and `config.example.yaml` (lines 10-11) — is saturated with banned tokens:

- Line 17: `# Phase 07 + Phase 08 default: leave tool_name unset...`
- Line 23: `# To restrict to a single tool (CD-05 short-circuit -- ...`
- Line 31: `# Phase 08 schema version. Only \`1\` is accepted...`
- Line 35: `# Per-tool config registry (TOOLCFG-01..07).`
- Line 44: `# Reserved fields ... (TOOLCFG-03) are intentionally`
- Line 45: `# omitted -- they are typed in the model for SEED-004 forward-compat...`
- Line 52: `... ssh_execute_command, ...). Phase 07's multi-tool discovery means TEST-08`
- Line 66: `# ---- Pre-existing (Phase 04/05/08 v1.0 baseline) ------------------------`

Plus the file still contains the `target:` block (lines 16-27) and `tool_name:` field, which `config.example.yaml` and the scaffold both deliberately omit (per `test_config_example_no_target_block` / `test_scaffold_no_target_block`). An operator copying this file to start their own config inherits all the planning artefacts and the deprecated-shape `target:` block that the rest of the v1.2 surface is moving away from.

`tests/unit/test_examples_dir.py` checks `examples/README.md` for banned tokens but does NOT scan `examples/homelab-mcp.yaml` — the regression guard is missing for the file most likely to be copied verbatim by a new user.

**Fix:**
1. Scrub `examples/homelab-mcp.yaml` of all `Phase \d`, `Plan \d-\d`, `[A-Z]+-\d`, and `\d{6}-[a-z0-9]{3}` tokens (rewrite comments in operator terms).
2. Remove the `target:` block to match `config.example.yaml`'s decision (the scaffold doesn't emit it either).
3. Add a regression test mirroring `test_config_example_no_banned_tokens`:

```python
# tests/unit/test_examples_dir.py
def test_homelab_mcp_yaml_no_banned_tokens() -> None:
    text = (EXAMPLES_DIR / "homelab-mcp.yaml").read_text(encoding="utf-8")
    banned = [
        r"\bPhase \d", r"\bPlan \d-\d", r"\bTOOLCFG-\d", r"\bISOL-\d",
        r"\bOUTPUT-\d", r"\bCD-\d", r"\bD-\d{2}",
        r"\b\d{6}-[a-z0-9]{3}", r"\bSEED-\d", r"\bTEST-\d",
    ]
    for p in banned:
        assert not re.search(p, text), f"banned pattern {p!r} in examples/homelab-mcp.yaml"

def test_homelab_mcp_yaml_no_target_block() -> None:
    import yaml
    data = yaml.safe_load((EXAMPLES_DIR / "homelab-mcp.yaml").read_text(encoding="utf-8"))
    assert "target" not in data, "examples/homelab-mcp.yaml must not advertise the leaving target: block"
```

### BL-02: operator-facing version-mismatch error leaks pydantic's "Value error," jargon

**File:** `src/mcp_test_framework/cli.py:119-132`
**Issue:** The version-mismatch branch interpolates pydantic's raw `msg` directly into the operator-facing detail block:

```python
if loc == "version" and "not supported by this build" in msg:
    _emit_operator_error(
        summary=f"config file uses an unsupported schema version: {source}",
        detail=[
            "this release of mcp-test-framework accepts schema version 1.",
            f"the file declares: {msg}.",   # <-- leaks pydantic's prose
            ...
        ],
        ...
    )
```

When the user's `_validate_version` raises `ValueError("config version 99 not supported...")`, pydantic v2 wraps it. The resulting `error['msg']` is verified to be:

```
Value error, config version 99 not supported by this build, expected 1
```

So the operator sees:

```
the file declares: Value error, config version 99 not supported by this build, expected 1.
```

`docs/ERROR-STYLE.md` rule 1 ("Operator terms only. No spec IDs, no internal jargon...") forbids this. `"Value error, "` is pydantic-internal prose with no operator meaning.

The existing guard `assert "value_error" not in err` in `test_load_config_validation_error_version` matches the pydantic v1 type-string spelling (`value_error`), not the v2 prose form (`Value error,`), so the test passes despite the leak.

**Fix:** Strip the `Value error, ` prefix or compose the detail without re-quoting pydantic's `msg`. Example:

```python
if loc == "version" and "not supported by this build" in msg:
    # Strip pydantic's "Value error, " prefix; the remainder is our own
    # validator message from _validate_version.
    clean_msg = msg.removeprefix("Value error, ").removeprefix("Assertion failed, ")
    _emit_operator_error(
        summary=f"config file uses an unsupported schema version: {source}",
        detail=[
            "this release of mcp-test-framework accepts schema version 1.",
            f"the file declares: {clean_msg}.",
            ...
        ],
        ...
    )
```

Tighten the test:

```python
assert "Value error" not in err  # pydantic v2 jargon
assert "value_error" not in err  # pydantic v1 jargon
assert "Assertion failed" not in err
```

## Warning Issues

### WR-01: `_pytest_exit_operator_tone` annotated `-> None` but never returns

**File:** `src/mcp_test_framework/fixtures.py:56-80`
**Issue:** The fixtures.py helper is annotated `-> None`, but `pytest.exit(...)` always raises `_pytest.outcomes.Exit`. The parallel `_emit_operator_error` helper in `cli.py:67-94` is correctly annotated `typing.NoReturn`. Type-checkers and IDEs will incorrectly infer that callers' code after this helper is reachable, suppressing real "unreachable code" diagnostics elsewhere. Inconsistency between the two parallel helpers also weakens the shape-mirror invariant the docstring claims.

**Fix:**

```python
import typing

def _pytest_exit_operator_tone(
    summary: str,
    detail: list[str],
    next_step: str,
    *,
    returncode: int = 2,
) -> typing.NoReturn:
    ...
```

### WR-02: `_emit_operator_error_for_validation` claims `target.tool_name` is "removed in v1.2" but the field is still active

**File:** `src/mcp_test_framework/cli.py:133-147` (cross-references `src/mcp_test_framework/models.py:76-98`, `src/mcp_test_framework/fixtures.py:267-288`)
**Issue:** The error-mapping branch for `extra_forbidden on target.tool_name` says:

```
"the `target.tool_name` field was removed in v1.2."
"the framework now uses the `tools:` block to decide which tools run."
```

But `TargetConfig.tool_name` is still a live, optional field (`models.py:81`), still consumed by `fixtures.py:267-274` for single-target mode, and still present in `examples/homelab-mcp.yaml`. The branch is unreachable today (pydantic will never raise `extra_forbidden` for an existing field) and, if a future operator's `target:` block accidentally includes a typo (e.g., `target: tool_nam:`), they get a misleading "field was removed" message instead of "did you mean tool_name?".

**Fix:** Either (a) actually remove `TargetConfig.tool_name` from `models.py` and the `fixtures.py` consumers (the bigger v1.2 cut Phase 12's docs implied) and update `examples/homelab-mcp.yaml`, OR (b) delete this dead branch from `_emit_operator_error_for_validation` until the removal happens.

### WR-03: README "Per-tool configuration" still documents `skip` semantics that contradict the v2 opt-in direction

**File:** `README.md:96-108`
**Issue:** The "Per-tool configuration" section says:

> Per-tool config lives under the top-level `tools:` key in your YAML overlay; tools with no entry use safe defaults (no skip, all rubrics, empty `call_arguments`).

This documents the **v1 opt-out** semantics (no entry = runs by default) at the same time `config.example.yaml` (lines 35-40, "Pattern A — minimal opt-in"), `EXTENDING.md` (lines 36-50, "Step 2 — scaffold a config", scaffold lists every tool as `skip: true`), and the `_format_tools_yaml_scaffold` output all push **opt-in** as the operator path. This confuses new operators reading the README first: the safe-default story they read in §"Per-tool configuration" contradicts the safe-default story they see when they run `config-init`.

This is also at odds with `docs/ERROR-STYLE.md`'s SAFE-06 reference message that talks about a future v2 schema where "in v1 a tool with no entry runs by default, in v2 it skips by default" — implying v1 (this release) IS opt-out. So the table's wording is technically correct for the schema, but the framing is in tension with the persona-foundation push toward opt-in.

**Fix:** Reconcile by either (a) calling out explicitly in the README that `config-init` produces an opt-IN scaffold despite the schema being opt-OUT (so operators understand the gap), or (b) inverting the schema in a follow-up phase as the SAFE-06 message foreshadows.

### WR-04: `test_scaffold_empty_tool_list_returns_empty_mapping` accepts `tools: None`, defeating its own intent

**File:** `tests/unit/test_config_init.py:72-76`
**Issue:**

```python
def test_scaffold_empty_tool_list_returns_empty_mapping() -> None:
    text = _scaffold([])
    assert "tools:\n  {}\n" in text or "tools: {}\n" in text
    data = yaml.safe_load(text)
    assert data["tools"] in (None, {})
```

The final assertion accepts `None` — which would mean YAML parsed `tools:` as null, NOT as an empty mapping. The scaffold builder `_format_tools_yaml_scaffold` writes `header + "  {}\n"` when there are no tools (`cli.py:724-725`); if a future refactor accidentally drops the `{}` literal, this test would silently pass on `tools:\n` (interpreted as null by YAML), and `Config()` would then fail with a type error at load. The test as written cannot detect that regression.

**Fix:**

```python
def test_scaffold_empty_tool_list_returns_empty_mapping() -> None:
    text = _scaffold([])
    data = yaml.safe_load(text)
    assert data["tools"] == {}, f"empty scaffold must yield empty mapping, got {data['tools']!r}"
```

### WR-05: `test_cli_errors_static_call_sites_no_banned_tokens` reads source via fragile relative path

**File:** `tests/unit/test_cli_errors.py:201-215`
**Issue:**

```python
def test_cli_errors_static_call_sites_no_banned_tokens() -> None:
    import ast
    src = Path("src/mcp_test_framework/cli.py").read_text(encoding="utf-8")
```

The relative path `src/mcp_test_framework/cli.py` only resolves when pytest is invoked from the repo root. Other tests in the suite (e.g. `test_doc_scrub.py:_repo_root`) compute the repo root by walking up from `__file__` to find `pyproject.toml`. This test will fail intermittently if pytest is invoked from any other cwd (e.g. `cd tests && pytest unit/test_cli_errors.py`).

**Fix:** Use the same `_repo_root()` walk pattern other Phase 12 tests use:

```python
def test_cli_errors_static_call_sites_no_banned_tokens() -> None:
    import ast
    repo_root = Path(__file__).resolve().parents[2]
    src = (repo_root / "src" / "mcp_test_framework" / "cli.py").read_text(encoding="utf-8")
    ...
```

### WR-06: `_format_tools_text` line 612 omits parentheses present on lines 528-529, relying on operator precedence

**File:** `src/mcp_test_framework/cli.py:611-612`
**Issue:**

```python
schema = t.inputSchema or {}
props = schema.get("properties") or {} if isinstance(schema, dict) else {}
```

Line 528-529 of the same file uses parens for the same idiom:

```python
props: dict = (schema.get("properties") or {}) if isinstance(schema, dict) else {}
required: list[str] = list(schema.get("required") or []) if isinstance(schema, dict) else []
```

Per Python precedence, `if/else` is lower than `or`, so line 612 parses as `(schema.get("properties") or {}) if isinstance(schema, dict) else {}` — the same as line 528 — but the missing parens make it visually ambiguous and easy to break under refactor. The `schema = t.inputSchema or {}` assignment one line up also makes the `isinstance(schema, dict)` guard non-load-bearing in the `t.inputSchema` is None branch (`{}` is always a dict), but redundant under refactor.

**Fix:** Parenthesize for readability and consistency:

```python
schema = t.inputSchema or {}
props = (schema.get("properties") or {}) if isinstance(schema, dict) else {}
```

---

_Reviewed: 2026-05-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
