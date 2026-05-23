---
phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/mcp_test_framework/config.py
  - src/mcp_test_framework/cli.py
  - tests/framework/unit/test_error_style.py
autonomous: true
requirements: [SHIM-04]
tags: [config, deprecation-shim, operator-error, pydantic]
must_haves:
  truths:
    - "A config.yaml with a top-level `sdet:` block is rejected at load time with the D-02 three-part operator-tone error naming `test_code:`."
    - "The rejection fires uniformly in CLI mode (`mcp-contracts run --config sdet-config.yaml`) AND library mode (bare `pytest` with `mcp_config_file = sdet-config.yaml` in pyproject.toml)."
    - "No `validation_alias=AliasChoices('test_code','sdet')` resolution path remains anywhere in src/."
    - "No `_warn_or_reject_legacy_sdet_key` model_validator, no `_check_legacy_sdet_key_in_yaml` pre-scan, no `model_validate` override on Config."
  artifacts:
    - path: "src/mcp_test_framework/config.py"
      provides: "Pydantic Config model with bare extra='forbid' (no sdet alias machinery)"
      contains: "extra=\"forbid\""
    - path: "src/mcp_test_framework/cli.py"
      provides: "_emit_operator_error_for_validation with new extra_forbidden/sdet branch"
      contains: "extra_forbidden"
    - path: "tests/framework/unit/test_error_style.py"
      provides: "Pinned-text test for the D-02 sdet-rejection message"
      contains: "rename the `sdet:` key to `test_code:`"
  key_links:
    - from: "src/mcp_test_framework/_plugin.py"
      to: "src/mcp_test_framework/cli.py:_emit_operator_error_for_validation"
      via: "lazy import in pytest_configure ValidationError handler"
      pattern: "_emit_operator_error_for_validation"
    - from: "src/mcp_test_framework/cli.py:_load_config"
      to: "src/mcp_test_framework/cli.py:_emit_operator_error_for_validation"
      via: "Config(yaml_file=...) ValidationError catch"
      pattern: "_emit_operator_error_for_validation"
---

<objective>
Remove the v1.4-introduced `cfg.sdet.*` YAML alias machinery from the Config model and surface a targeted operator-tone error when an operator points the framework at a config carrying a top-level `sdet:` key. Implements SHIM-04 per Phase 31 CONTEXT D-01..D-04.

Purpose: Reduce the operator-facing config surface to a single valid test-code key (`test_code:`); kill the v1.4 deprecation shim at the locked v1.5 expiry; preserve the operator-tone error shape (three-part summary/detail/next_step) so the rejection is actionable rather than a raw Pydantic traceback.

Output: ~110 lines deleted from `config.py`; one new branch (~25 lines) in `cli.py:_emit_operator_error_for_validation`; one new pinned-text test in `tests/framework/unit/test_error_style.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md
@.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md
@docs/ERROR-STYLE.md
@src/mcp_test_framework/config.py
@src/mcp_test_framework/cli.py
@src/mcp_test_framework/_plugin.py

<interfaces>
<!-- The shared error-mapper hook (D-04 verdict) — both cli.py and _plugin.py route through this. -->
From src/mcp_test_framework/cli.py (verified at HEAD):
```python
def _emit_operator_error_for_validation(
    exc: ValidationError, *, source: str
) -> typing.NoReturn:
    """Map pydantic.ValidationError -> operator-tone error per docs/ERROR-STYLE.md."""
```

From src/mcp_test_framework/cli.py:_emit_operator_error (existing render helper):
```python
def _emit_operator_error(*, summary: str, detail: list[str], next_step: str) -> typing.NoReturn:
    """Render operator-tone three-part error then raise typer.Exit(code=2)."""
```

From src/mcp_test_framework/_plugin.py (verified at HEAD L181-196):
- pytest_configure already catches ValidationError from `Config(yaml_file=str(path))`
  and lazy-imports `_emit_operator_error_for_validation` from cli.py — the new
  SHIM-04 branch surfaces in BOTH personas with zero plugin changes.

Pydantic v2 error shape for `extra=forbid`:
- `err_type == 'extra_forbidden'`
- `loc == ('sdet',)` for top-level `sdet:` key
- `msg` starts with "Extra inputs are not permitted"
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator config file -> Pydantic model | YAML loaded from disk; operator-authored content; structurally untrusted (typos, schema drift) but not adversarial (single-user/operator file) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-31-01-01 | Information Disclosure (LOW) | `_emit_operator_error_for_validation` new branch | mitigate | Branch matches by exact `(err_type, loc)` tuple per D-03 — no operator-supplied data is reflected into the error body beyond the source path (which the operator already knows). Body text is static. |
| T-31-01-02 | Tampering (LOW) | Regression of plugin ValidationError routing | mitigate | The plugin's lazy-import path is verified at HEAD (research §D-04). The new branch is added inside the existing dispatcher — no plugin code changes required; the routing contract is unchanged. New pinned-text test asserts the branch fires from BOTH personas. |
| T-31-01-03 | Denial of Service (INFORMATIONAL) | New branch could be skipped if branch ordering is wrong | accept | Branch order is documented: `extra_forbidden+sdet` BEFORE the generic-fallback. If a future edit reorders, the pinned-text test fails — covered by V1DROP-04 self-test gate landing in Plan 06. |

ASVS classification: V8.2 (Operator-facing logging without sensitive data). Phase has no HIGH threats.
</threat_model>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Delete `sdet:` alias machinery from Config model</name>
  <files>src/mcp_test_framework/config.py</files>
  <read_first>
    - src/mcp_test_framework/config.py (read entirety; the deletions span L52-L312)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md (D-01 specifies what to delete)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md §"Verified Line Numbers" (canonical line numbers for the deletion targets)
  </read_first>
  <behavior>
    - The Config model still has `extra="forbid"` after the edit (this is the central mechanism for surfacing the rejection).
    - A `Config(yaml_file=...)` call against a YAML containing top-level `sdet:` raises `ValidationError` with `errors()` containing `{'type': 'extra_forbidden', 'loc': ('sdet',), ...}`.
    - A `Config(yaml_file=...)` call against a YAML containing top-level `test_code:` succeeds (unchanged behavior).
    - No code path in config.py references the string `"sdet"` after the edit (except possibly inside an unrelated docstring that the executor should also scrub; verify via grep).
    - All `# noqa: sdet-rename-shim` markers in this file are removed alongside the code they protected.
  </behavior>
  <action>
    Per CONTEXT D-01, delete every piece of `sdet:` alias machinery from src/mcp_test_framework/config.py:

    1. **`test_code` field declaration (around L58-72)** — remove `validation_alias=AliasChoices('test_code', 'sdet')` from the `Field(...)` call. The field stays required; only the alias is dropped. If `AliasChoices` is then unused in the file, also remove its import.

    2. **`_warn_or_reject_legacy_sdet_key` model_validator (around L73-180)** — delete the entire `@model_validator(mode='before')` decorated function. This is the "before"-mode validator that pre-scanned init-kwargs / source-dict for legacy `sdet:` keys and emitted warnings/errors.

    3. **`model_validate` classmethod override (around L181-191)** — delete the override that re-runs the legacy-key pre-scan on dict input. Pydantic's default `model_validate` is sufficient — `extra="forbid"` handles top-level `sdet:` natively.

    4. **`_check_legacy_sdet_key_in_yaml` helper + call site (L254-312 helper definition; L226-247 call inside `settings_customise_sources`)** — delete the helper function AND the call to it inside `settings_customise_sources`. The settings-source pipeline returns to the bare default chain (init_kwargs > env > dotenv > yaml_file > secrets > defaults — SHIM-05 in Plan 02 will further unwire the env-var fallback; that work is orthogonal).

    5. **`# noqa: sdet-rename-shim` markers** — grep `grep -n 'sdet-rename-shim' src/mcp_test_framework/config.py` and remove every line carrying that marker (the noqa directives go with the deleted code).

    6. **Imports** — after deletions, `from pydantic import AliasChoices` (if it was imported) is unused; remove it. `from pydantic import model_validator` may still be used elsewhere — keep only if used.

    Net diff target: ~110 lines deleted, ~0 added (small import cleanup may net out to ~115 deleted / ~0 added). Do NOT delete the `extra="forbid"` line in `model_config = SettingsConfigDict(...)` — that is the surviving rejection mechanism per D-01.

    After edits, run `grep -n 'sdet' src/mcp_test_framework/config.py` — the only remaining matches MUST be either (a) unrelated text in unrelated docstrings (e.g., an `sdet:`-historical reference comment, if present), or zero matches. If any code references `sdet` outside an inert comment, you missed a deletion target.
  </action>
  <verify>
    <automated>uv run python -c "from mcp_test_framework.config import Config; import pydantic; exc=None\ntry: Config.model_validate({'test_code': {'generated_root': 'x'}, 'sdet': {'foo': 'bar'}})\nexcept pydantic.ValidationError as e: exc=e\nassert exc is not None, 'sdet should be rejected'\nerrs=exc.errors(); assert any(e['type']=='extra_forbidden' and tuple(e['loc'])==('sdet',) for e in errs), errs; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n 'AliasChoices' src/mcp_test_framework/config.py` returns no matches (or matches only inside removed-feature comments).
    - `grep -n '_warn_or_reject_legacy_sdet_key\|_check_legacy_sdet_key_in_yaml' src/mcp_test_framework/config.py` returns zero matches.
    - `grep -n 'sdet-rename-shim' src/mcp_test_framework/config.py` returns zero matches.
    - `grep -n 'extra="forbid"' src/mcp_test_framework/config.py` returns at least one match (the central mechanism is preserved).
    - `uv run python -c "from mcp_test_framework.config import Config; Config.model_validate({'test_code': {'generated_root': 'x'}})"` exits 0.
    - The Pydantic ValidationError raised on top-level `sdet:` has at least one error with `type == 'extra_forbidden'` and `loc == ('sdet',)`.
  </acceptance_criteria>
  <done>
    config.py contains no `sdet:` alias machinery; Pydantic's bare `extra="forbid"` mechanism surfaces top-level `sdet:` as `extra_forbidden` errors with `loc=('sdet',)`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add `extra_forbidden`+`sdet` branch to `_emit_operator_error_for_validation`</name>
  <files>src/mcp_test_framework/cli.py</files>
  <read_first>
    - src/mcp_test_framework/cli.py (focus L244-347 — the existing dispatcher; the new branch is inserted here)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md (D-02 specifies VERBATIM message text; do not reword)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md §"D-04 Resolution" (confirms shared mapper exists; new branch lands here)
    - docs/ERROR-STYLE.md (three-part operator-tone shape contract)
    - tests/framework/unit/test_config_sdet_field.py (template — invokes `_emit_operator_error_for_validation` directly)
  </read_first>
  <behavior>
    - When `_emit_operator_error_for_validation(exc, source=...)` is called with a `ValidationError` whose `errors()` contains `{'type': 'extra_forbidden', 'loc': ('sdet',), ...}`, the function renders the D-02 three-part message and raises `typer.Exit(code=2)`.
    - The branch fires BEFORE the generic-fallback at the bottom of the function.
    - The branch fires AFTER the existing `version` branch (D-03: exact-match on `(err_type='extra_forbidden', loc=('sdet',))`; ordering vs `version` branch is irrelevant since the tuples are disjoint, but place after `version` for source-locality with `extra_forbidden`-class branches).
    - Other `extra_forbidden` errors with different `loc` (e.g., `loc=('typo_key',)`) fall through to the generic fallback unchanged — the branch is targeted, not blanket.
    - Calling the function with a non-`sdet` ValidationError shape is unchanged from current behavior (regression-free for non-targeted shapes).
  </behavior>
  <action>
    Insert a new branch into `src/mcp_test_framework/cli.py:_emit_operator_error_for_validation`. The branch lands between the existing `version`/"not supported by this build" branch (L292-315 — to be REWRITTEN by Plan 03; treat current shape as the insertion landmark) and the existing `missing`/`value_error.missing` branch (L316-329).

    The branch detection logic walks the FULL errors list (do not rely on `primary` — the `extra_forbidden` on `sdet` may co-occur with other errors, and the `version_err` scan-and-prefer pattern at L267-275 demonstrates the correct idiom):

    ```python
    sdet_err = next(
        (
            e
            for e in errors
            if e.get("type") == "extra_forbidden"
            and tuple(e.get("loc", ())) == ("sdet",)
        ),
        None,
    )
    if sdet_err is not None:
        _emit_operator_error(
            summary="unknown config key: sdet",
            detail=[
                "the `sdet:` key was renamed to `test_code:` in v1.4 and removed in v1.5.",
                "your existing block under `sdet:` ports forward unchanged -- just rename the top-level key.",
            ],
            next_step="rename the `sdet:` key to `test_code:` in your config.yaml",
        )
    ```

    **The message text above is VERBATIM from CONTEXT D-02 and was operator-approved during the /gsd-discuss-phase session. Do NOT reword. Do NOT add a `source` substitution. Do NOT add a `docs/MIGRATION-v1-to-v2.md` reference (that doc is deleted in Plan 04).**

    The dispatcher must check for the `sdet` branch BEFORE returning the generic-fallback (lines L330-347). Order vs the `version` branch (L292-315) is irrelevant — the `(err_type, loc)` tuples are disjoint — but place the new branch immediately AFTER the `version` branch for source-locality.

    Do NOT modify the existing `version` branch in this task — Plan 03 owns that rewrite. The two changes are landing in different waves; do not pre-rewrite or you create a merge conflict surface against Plan 03.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_config_sdet_field.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n 'extra_forbidden' src/mcp_test_framework/cli.py` returns at least one match inside `_emit_operator_error_for_validation`.
    - `grep -n 'unknown config key: sdet' src/mcp_test_framework/cli.py` returns exactly one match.
    - `grep -n 'rename the .sdet: key to .test_code: in your config.yaml' src/mcp_test_framework/cli.py` returns exactly one match (the literal next_step text from D-02).
    - `grep -n 'MIGRATION-v1-to-v2' src/mcp_test_framework/cli.py` finds NO new references in the sdet branch (the existing v1-rejection branch's MIGRATION reference is Plan 03's responsibility).
    - The new branch text contains no `Phase \d`, `Plan \d-\d`, `[A-Z]{2,}-\d{2}` patterns (per ERROR-STYLE.md "Banned strings").
    - Existing v1-rejection text (`"config file uses an older format"`) is unchanged in this task — Plan 03 owns that rewrite.
  </acceptance_criteria>
  <done>
    `_emit_operator_error_for_validation` carries a targeted `(extra_forbidden, ('sdet',))` branch that renders the D-02 verbatim three-part operator-tone message and raises `typer.Exit(code=2)`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Pin the D-02 sdet-rejection message in test_error_style.py</name>
  <files>tests/framework/unit/test_error_style.py</files>
  <read_first>
    - tests/framework/unit/test_error_style.py (entire file — match the existing test idiom for new test)
    - tests/framework/unit/test_config_sdet_field.py (template that invokes `_emit_operator_error_for_validation` directly — D-04 reference asset)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md (D-02 verbatim text)
    - src/mcp_test_framework/cli.py (the branch added in Task 2 — confirm the live text matches the test expectation)
  </read_first>
  <behavior>
    - A new test `test_error_style_sdet_rejection_message` invokes `_emit_operator_error_for_validation` with a hand-crafted ValidationError whose `errors()` contains `{'type': 'extra_forbidden', 'loc': ('sdet',), ...}`.
    - The test captures the rendered stderr/output (or, mirroring `test_config_sdet_field.py`, captures `typer.Exit` and inspects the rendered message).
    - The test asserts the exact summary string `"unknown config key: sdet"` is present.
    - The test asserts the exact next_step string `"rename the \`sdet:\` key to \`test_code:\` in your config.yaml"` is present.
    - The test asserts the exact detail strings from D-02 are present (both lines).
    - The test asserts `typer.Exit(code=2)` is raised.
    - The test does NOT mark itself xfail/skip.
  </behavior>
  <action>
    Add ONE new test to `tests/framework/unit/test_error_style.py` named `test_error_style_sdet_rejection_message`. Follow the existing test idiom in that file (likely: build a synthetic `ValidationError`, call `_emit_operator_error_for_validation`, catch `typer.Exit`, inspect captured output).

    To build a synthetic `ValidationError` with the right shape, mirror the approach in `tests/framework/unit/test_config_sdet_field.py` — either (a) construct a real `Config(yaml_file=...)` against a tmp_path YAML containing `sdet:` and let Pydantic raise naturally, or (b) construct a `ValidationError` manually via `Config.model_validate({'sdet': {...}})`.

    Path (a) — preferred for end-to-end realism — uses pytest's `tmp_path` fixture:
    ```python
    def test_error_style_sdet_rejection_message(tmp_path, capsys):
        from mcp_test_framework.cli import _emit_operator_error_for_validation
        from mcp_test_framework.config import Config
        from pydantic import ValidationError
        import typer

        cfg = tmp_path / "sdet.yaml"
        cfg.write_text("version: 2\nsdet:\n  generated_root: out\n", encoding="utf-8")
        try:
            Config(yaml_file=str(cfg))
        except ValidationError as exc:
            try:
                _emit_operator_error_for_validation(exc, source=str(cfg))
            except typer.Exit as ex:
                assert ex.exit_code == 2
            captured = capsys.readouterr()
            text = captured.out + captured.err
            assert "unknown config key: sdet" in text
            assert "the `sdet:` key was renamed to `test_code:` in v1.4 and removed in v1.5." in text
            assert "your existing block under `sdet:` ports forward unchanged" in text
            assert "rename the `sdet:` key to `test_code:` in your config.yaml" in text
        else:
            raise AssertionError("Config(yaml_file=...) with sdet: key should have raised ValidationError")
    ```

    Adapt to the file's existing helper functions / fixtures if they differ. Do not change other tests in this file in this task — V1DROP-04 relaxations land in Plan 03 (test_error_style L74-86 rewrite) and Plan 06 (other test files); this Task only ADDS a new test.

    **Verbatim message strings** must match the D-02 text inserted by Task 2. If a string mismatch is detected during verify, fix the test text (Task 2's verbatim D-02 wording is the source of truth — D-02 in CONTEXT is operator-approved).
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_error_style.py::test_error_style_sdet_rejection_message -x -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n 'test_error_style_sdet_rejection_message' tests/framework/unit/test_error_style.py` returns exactly one match (the test definition).
    - `uv run pytest tests/framework/unit/test_error_style.py::test_error_style_sdet_rejection_message -q` exits 0.
    - The test contains the literal substrings: `"unknown config key: sdet"`, `"rename the \`sdet:\` key to \`test_code:\` in your config.yaml"`.
    - The test asserts `ex.exit_code == 2` (or equivalent typer.Exit code check).
    - The test does NOT carry `@pytest.mark.xfail`, `@pytest.mark.skip`, or `pytest.skip(...)` at runtime.
  </acceptance_criteria>
  <done>
    The D-02 sdet-rejection message text is pinned by a regression test; future drift breaks the test.
  </done>
</task>

</tasks>

<verification>
Phase-level checks after all three tasks complete:

1. `uv run pytest tests/framework/unit/test_error_style.py tests/framework/unit/test_config_sdet_field.py -q` exits 0.
2. End-to-end realism (manual or smoke):
   - Create `/tmp/sdet-test.yaml` with `version: 2\nsdet:\n  generated_root: x\n`.
   - `uv run mcp-contracts run --config /tmp/sdet-test.yaml` exits 2 and prints the D-02 three-part message.
   - With `[tool.pytest.ini_options] mcp_config_file = /tmp/sdet-test.yaml` in pyproject.toml, `uv run pytest` exits 2 and prints the D-02 three-part message.
3. `grep -rn 'AliasChoices' src/mcp_test_framework/` returns no matches (or only in unrelated contexts).
4. `grep -rn 'sdet-rename-shim' src/mcp_test_framework/` returns no matches.
</verification>

<success_criteria>
- All three tasks' acceptance criteria met.
- `uv run pytest tests/framework/unit/test_error_style.py` is green.
- Operator pointing the framework at a `sdet:`-keyed YAML hits the D-02 three-part operator-tone error in BOTH CLI and library modes.
- ~110 lines deleted from config.py; ~25 lines added to cli.py; ~25 lines added to test_error_style.py.
</success_criteria>

<output>
After completion, create `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-01-SUMMARY.md`
</output>
