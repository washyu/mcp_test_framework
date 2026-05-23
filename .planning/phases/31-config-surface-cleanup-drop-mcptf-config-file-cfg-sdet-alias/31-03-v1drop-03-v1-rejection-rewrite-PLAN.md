---
phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
plan: 03
type: execute
wave: 2
depends_on: [31-01]
files_modified:
  - src/mcp_test_framework/cli.py
  - tests/framework/unit/test_error_style.py
  - tests/framework/unit/test_cli_errors.py
autonomous: true
requirements: [V1DROP-03, V1DROP-04]
tags: [v1-decommission, operator-error, self-test-relaxation]
must_haves:
  truths:
    - "A config.yaml declaring `version: 1` is rejected with the D-11 three-part operator-tone error pointing at `mcp-contracts config-init -o config.yaml`."
    - "The rejection message contains NO `docs/MIGRATION-v1-to-v2.md` cross-reference."
    - "The rejection message contains NO v1-vs-v2 walkthrough language (`opt-in`, `opt-out`, `the difference matters`, `in v1 a tool with no entry runs by default`)."
    - "The rejection still exits with code 2 (preserved per ERROR-STYLE.md exit-code table)."
    - "`tests/framework/unit/test_error_style.py::test_error_style_safe_06_body_matches_cli_wiring` is rewritten to assert the D-11 wording (or deleted) — no longer pins MIGRATION text."
    - "`tests/framework/unit/test_cli_errors.py::test_safe_06_v1_config_emits_locked_migration_message` is rewritten to assert the D-11 wording — no longer pins MIGRATION text."
    - "`tests/framework/unit/test_cli_errors.py::test_safe_06_v1_config_via_env_var_emits_locked_migration_message` is DELETED (env-var route gone in Plan 02)."
  artifacts:
    - path: "src/mcp_test_framework/cli.py"
      provides: "_emit_operator_error_for_validation version branch carrying D-11 wording"
      contains: "this build supports schema version 2"
    - path: "tests/framework/unit/test_error_style.py"
      provides: "V1DROP-04 RELAX — SAFE-06 body assertion either rewritten to D-11 or removed"
      contains: "config-init"
    - path: "tests/framework/unit/test_cli_errors.py"
      provides: "V1DROP-04 REWRITE — locked-message assertion replaced with D-11 text"
      contains: "config-init"
  key_links:
    - from: "src/mcp_test_framework/cli.py:_emit_operator_error_for_validation"
      to: "tests/framework/unit/test_cli_errors.py SAFE-06 pinned test"
      via: "verbatim D-11 message text"
      pattern: "unsupported config version"
---

<objective>
Rewrite the v1→v2 migration walkthrough error message in `cli.py:_emit_operator_error_for_validation` to the D-11 generic three-part operator-tone wording, and simultaneously rewrite (RELAX/DELETE per D-12) the two self-test sites that pin the legacy text. Implements V1DROP-03 and the v1-rejection portion of V1DROP-04 per Phase 31 CONTEXT D-11/D-12 and RESEARCH §"Strict ordering constraint 2".

Purpose: Decommission the v1→v2 migration verbiage. The framework has never been published and no live v1 operators exist; the v1-rejection becomes a generic operator-tone error pointing at `config-init` as the recovery mechanism. The paired self-test rewrites land in the SAME plan to honor RESEARCH §"Strict ordering constraint 2" (message rewrite without test relaxation = guaranteed test-suite red between waves).

Output: ~25 lines rewritten in cli.py (L292-315 version branch body); 2-3 test assertions rewritten in test_error_style.py + test_cli_errors.py; 1 test deletion (env-var-based v1-rejection test, since env var is gone in Plan 02).
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
@src/mcp_test_framework/cli.py
@tests/framework/unit/test_error_style.py
@tests/framework/unit/test_cli_errors.py

<interfaces>
<!-- The version branch is the rewrite target — verbatim shape verified at HEAD. -->
From src/mcp_test_framework/cli.py:_emit_operator_error_for_validation L292-315 (verified at HEAD):
```python
if loc == "version" and "not supported by this build" in msg:
    _emit_operator_error(
        summary=f"config file uses an older format: {source}",
        detail=[
            "this release of mcp-test-framework expects schema version 2 (opt-in",
            "tool selection); your config is version 1 (opt-out). the difference",
            "matters: in v1 a tool with no entry runs by default, in v2 it skips",
            "by default.",
            "",
            "your existing per-tool settings (`call_arguments`, `judges`,",
            "`skip_reason`) port forward unchanged -- only the implicit default",
            "flips. the migration walkthrough at docs/MIGRATION-v1-to-v2.md shows",
            "the steps.",
        ],
        next_step=(
            "run `mcp-test-framework config-init -o config.yaml.new` to see "
            "the v2 layout, port your tool entries across, then replace your "
            "existing config"
        ),
    )
```
This entire block is the rewrite target.

D-11 verbatim text (from CONTEXT.md):
- summary: "unsupported config version {v}"
- detail line 1: "this build supports schema version 2."
- detail line 2: "your config declares version {v}, which is no longer accepted."
- next_step: "run `mcp-contracts config-init -o config.yaml` to generate a current scaffold"

The `{v}` placeholder must be sourced from the ValidationError. The `msg` field of the version error carries text like "config version 1 not supported by this build" — extract the version number via regex or string parse.
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator config file `version` field -> rejection-message rendering | The {v} value is substituted into the message body; sourced from a Pydantic-parsed int field, not freeform string |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-31-03-01 | Tampering (LOW) | Self-test relaxation could hide a regression in the version branch | mitigate | The relaxation per D-12 swaps body-text pins for the D-11 verbatim wording — structural assertions (exit code, three-part shape, summary-keyword) survive. The `test_cli_errors.py::test_load_config_validation_error_version` test at L96-126 is already permissive enough to accept the new wording (per RESEARCH inventory) and acts as a regression sibling. |
| T-31-03-02 | Information Disclosure (LOW) | {v} substitution into the message body | accept | Operator's own version-field value is reflected back at them — non-sensitive by definition (operator already knows what they wrote in their config). |

ASVS classification: V8.2. Phase has no HIGH threats.
</threat_model>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Rewrite the version branch body in cli.py:_emit_operator_error_for_validation to D-11 wording</name>
  <files>src/mcp_test_framework/cli.py</files>
  <read_first>
    - src/mcp_test_framework/cli.py L244-347 (the dispatcher; version branch at L292-315)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md (D-11 verbatim text)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md §"Strict ordering constraint 2"
    - docs/ERROR-STYLE.md (operator-tone three-part shape; "Banned strings" checklist)
  </read_first>
  <behavior>
    - The version branch matches the same conditions as before: `loc == "version" and "not supported by this build" in msg`.
    - The branch raises `typer.Exit(code=2)` via `_emit_operator_error(...)` — exit-code contract preserved per ERROR-STYLE.md.
    - The rendered message has:
      - summary line: `"unsupported config version {v}"` where {v} is the actual version number parsed from `msg`.
      - detail block: TWO lines per D-11 — "this build supports schema version 2." and "your config declares version {v}, which is no longer accepted."
      - next_step: `"run \`mcp-contracts config-init -o config.yaml\` to generate a current scaffold"`
    - The rendered message contains NO `docs/MIGRATION-v1-to-v2.md` reference.
    - The rendered message contains NO of: `"opt-in"`, `"opt-out"`, `"the difference matters"`, `"in v1 a tool with no entry"`, `"the migration walkthrough"`, `"port your tool entries"`.
    - The rendered message contains NO `"mcp-test-framework"` console-script reference (the v1.4 legacy name shipped in the old next_step — replaced with `mcp-contracts`).
    - The rendered message passes the ERROR-STYLE.md banned-strings checklist.
  </behavior>
  <action>
    Replace the entire body of the `if loc == "version" and "not supported by this build" in msg:` branch at `src/mcp_test_framework/cli.py:292-315`.

    Parse the actual version number from the Pydantic error message. The validator at `config.py:_validate_version` raises with a message of the form `"config version N not supported by this build"` — extract N via regex. Defensively fall back to a placeholder if parse fails (operator still gets a useful error; just without the specific number).

    ```python
    if loc == "version" and "not supported by this build" in msg:
        # Parse the actual version value from the error message body.
        # _validate_version raises with "config version {v} not supported by this build";
        # extract for substitution into the operator-tone error.
        # Note: `re` is already imported at module-level (cli.py L46), so no local import needed.
        m = re.search(r"config version (\S+) not supported", msg)
        version_val = m.group(1) if m else "?"
        _emit_operator_error(
            summary=f"unsupported config version {version_val}",
            detail=[
                "this build supports schema version 2.",
                f"your config declares version {version_val}, which is no longer accepted.",
            ],
            next_step=(
                "run `mcp-contracts config-init -o config.yaml` to generate a "
                "current scaffold"
            ),
        )
    ```

    **The summary / detail / next_step text above is VERBATIM from CONTEXT D-11.** Do NOT reword. Do NOT add any of the banned phrases listed in `<behavior>`.

    Keep the `# Locked v1 -> v2 migration message` comment at L293-296 OR replace it with: `# v1-rejection: generic operator-tone (V1DROP-03); historical migration verbiage retired in Phase 31`. The comment must NOT reference `docs/MIGRATION-v1-to-v2.md` (that file is deleted in Plan 04).

    Keep ALL OTHER branches in `_emit_operator_error_for_validation` unchanged (the `sdet` branch added in Plan 01, the `missing` branch, the generic fallback).
  </action>
  <verify>
    <automated>uv run python -c "from mcp_test_framework.cli import _emit_operator_error_for_validation; from pydantic import ValidationError; from pydantic_core import PydanticCustomError, InitErrorDetails; import typer; errs=[InitErrorDetails(type=PydanticCustomError('value_error','config version 1 not supported by this build'), loc=('version',), input=1)]; exc=ValidationError.from_exception_data('Config', errs); raised=None
try: _emit_operator_error_for_validation(exc, source='/tmp/v1-test.yaml')
except typer.Exit as ex: raised=ex
assert raised is not None and raised.exit_code==2, raised
print('OK probe exited via typer.Exit(2)')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n 'unsupported config version' src/mcp_test_framework/cli.py` returns exactly one match (inside the version branch).
    - `grep -n 'this build supports schema version 2' src/mcp_test_framework/cli.py` returns exactly one match.
    - `grep -n 'MIGRATION-v1-to-v2' src/mcp_test_framework/cli.py` returns zero matches.
    - `grep -n 'opt-in tool selection' src/mcp_test_framework/cli.py` returns zero matches in the version branch (other occurrences elsewhere in the file are out of scope).
    - `grep -n 'the migration walkthrough' src/mcp_test_framework/cli.py` returns zero matches.
    - `grep -n 'config-init -o config.yaml' src/mcp_test_framework/cli.py` returns at least one match in the version branch (the D-11 next_step).
    - The Python probe in `<automated>` synthesizes a `ValidationError` matching the version-1 shape, invokes `_emit_operator_error_for_validation` directly, and asserts `typer.Exit(code=2)` is raised — no MCP-server spawn, no `uv run mcp-contracts run` invocation. End-to-end realism is covered by the phase-level `<verification>` block.
  </acceptance_criteria>
  <done>
    The version branch carries the D-11 verbatim three-part operator-tone message; the v1→v2 walkthrough verbiage is gone.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rewrite test_cli_errors.py SAFE-06 assertions to D-11; delete env-var-based v1-rejection test</name>
  <files>tests/framework/unit/test_cli_errors.py</files>
  <read_first>
    - tests/framework/unit/test_cli_errors.py (focus L96-126 generic version test; L259-273 SAFE-03; L275-285 SAFE-04 env-var typo test; L286-307 SAFE-02 cwd autodiscovery; L360-419 SAFE-06 paired tests)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md §"Self-Test Inventory" (exact line ranges + dispositions per D-12)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md (D-12 RELAX-not-DELETE default)
  </read_first>
  <behavior>
    - `test_safe_06_v1_config_emits_locked_migration_message` exists (renamed if helpful, e.g., `test_safe_06_v1_config_emits_operator_tone_rejection`) and asserts the D-11 verbatim wording: `"unsupported config version"`, `"this build supports schema version 2"`, `"config-init -o config.yaml"`. Exit code 2. Source-label substitution preserved (the test asserts the config file path appears in the rendered output OR is structurally referenced — confirm against current shape).
    - `test_safe_06_v1_config_via_env_var_emits_locked_migration_message` (the env-var sibling) is DELETED — the env-var route is gone in Plan 02; the test will fail on a setup that no longer works.
    - `test_load_config_validation_error_version` at L96-126 is UNCHANGED (already permissive enough per RESEARCH — accepts `"schema version" in err or "older format" in err or "unsupported" in err` — the new wording satisfies the `"unsupported"` branch).
    - `test_safe_04_mcptf_config_file_typo_exits_2` at L275-285 is DELETED — env-var route gone in Plan 02.
    - `test_safe_03_no_config_found_fails_loud_with_locked_message` at L259-273 is UNCHANGED (SAFE-03 stays).
    - `test_safe_02_cwd_autodiscovery_picks_up_local_config` at L286-307 has its `sdet:` YAML literal swapped to `test_code:` (mechanical SDET-fix per D-12).
    - Other tests in this file embedding `sdet:` YAML (L147-217 MCP-spawn-failure tests) get the same mechanical key swap.
  </behavior>
  <action>
    Multi-edit in `tests/framework/unit/test_cli_errors.py` following RESEARCH inventory §"Self-Test Inventory":

    1. **L360-419 `test_safe_06_v1_config_emits_locked_migration_message`** — REWRITE the body assertion block. Swap any of these pinned-text substring checks with the D-11 verbatim phrases:
       - Replace `"docs/MIGRATION-v1-to-v2.md"` assertions with: `assert "unsupported config version" in output_or_err`
       - Replace `"in v1 a tool with no entry"` / `"opt-in"` / `"opt-out"` / `"the difference matters"` assertions with: `assert "this build supports schema version 2" in output_or_err` and `assert "config-init -o config.yaml" in output_or_err`
       - Keep the exit-code 2 assertion unchanged.

       Optionally rename the test to `test_safe_06_v1_config_emits_d11_operator_tone_rejection` to reflect the new shape (but keeping the legacy name is acceptable — RESEARCH §V1DROP-04 explicitly notes preserving test count/names is fine).

    2. **L360-419 sibling `test_safe_06_v1_config_via_env_var_emits_locked_migration_message`** — DELETE this entire test function. The env-var route is removed in Plan 02; the setup (`monkeypatch.setenv("MCPTF_CONFIG_FILE", ...)` + asserting the loader picks it up) will not work post-SHIM-05.

    3. **L275-285 `test_safe_04_mcptf_config_file_typo_exits_2`** — DELETE this entire test function. Same reasoning: env-var route gone.

    4. **L286-307 `test_safe_02_cwd_autodiscovery_picks_up_local_config`** — find the embedded `sdet:` YAML literal (something like `'sdet:\n  generated_root: ...'`) and swap to `'test_code:\n  generated_root: ...'`. Mechanical key swap. The test's behavior assertion (cwd autodiscovery works) is unchanged.

    5. **L147-217 (two MCP-spawn-failure tests)** — find embedded `sdet:` YAML fixtures and swap to `test_code:`. Mechanical key swap. Behavior assertions unchanged.

    6. **L96-126 `test_load_config_validation_error_version`** — DO NOT modify (RESEARCH §V1DROP-04 inventory: "NO CHANGE — already permissive enough").

    7. **L259-273 `test_safe_03_no_config_found_fails_loud_with_locked_message`** — DO NOT modify (RESEARCH: "NO CHANGE — SAFE-03 stays").

    After edits, the test file's overall test count drops by 2 (env-var SAFE-04 and env-var SAFE-06 deleted). Function names of surviving tests can stay as-is.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_cli_errors.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n 'test_safe_06_v1_config_via_env_var_emits_locked_migration_message' tests/framework/unit/test_cli_errors.py` returns zero matches.
    - `grep -n 'test_safe_04_mcptf_config_file_typo_exits_2' tests/framework/unit/test_cli_errors.py` returns zero matches.
    - `grep -n 'test_safe_06_v1_config_emits' tests/framework/unit/test_cli_errors.py` returns exactly one match (the surviving SAFE-06 test).
    - `grep -n 'MIGRATION-v1-to-v2' tests/framework/unit/test_cli_errors.py` returns zero matches.
    - `grep -n 'sdet:' tests/framework/unit/test_cli_errors.py` returns zero matches (mechanical SDET-fix applied to all embedded YAMLs).
    - `grep -n 'unsupported config version' tests/framework/unit/test_cli_errors.py` returns at least one match (inside the rewritten SAFE-06 test).
    - `uv run pytest tests/framework/unit/test_cli_errors.py -q` exits 0.
  </acceptance_criteria>
  <done>
    test_cli_errors.py asserts the D-11 wording for v1 rejection; env-var-based tests are deleted; embedded sdet: YAML literals flipped to test_code:.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Rewrite test_error_style.py SAFE-06 body assertion to D-11; relax/delete SAFE-04 env-var assertion</name>
  <files>tests/framework/unit/test_error_style.py</files>
  <read_first>
    - tests/framework/unit/test_error_style.py (focus L36-41 SAFE-06 contains-message; L60-71 SAFE-04 env-var body match; L74-86 SAFE-06 body match)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md §"Self-Test Inventory" (exact dispositions: L36-41 RELAX; L60-71 DELETE; L74-86 REWRITE)
    - docs/ERROR-STYLE.md (current reference messages — note the "Config uses an older schema version" reference message at L57-73 is itself being decommissioned by V1DROP-02, which Plan 05 handles)
  </read_first>
  <behavior>
    - `test_error_style_contains_safe_06_message` (L36-41) — the assertion `"docs/MIGRATION-v1-to-v2.md" in text` is REMOVED. The test either is deleted (if it has no other assertions) or relaxed to assert the surviving SAFE-06 markers (e.g., the section header "### Config uses an older schema version" if still present in ERROR-STYLE.md post-V1DROP-02, OR a generic existence check).
    - `test_error_style_safe_04_body_matches_cli_wiring` (L60-71) — DELETED. The env-var typo error body it pins is removed by Plan 02's `_load_config` Branch 2 deletion.
    - `test_error_style_safe_06_body_matches_cli_wiring` (L74-86) — REWRITTEN. Replaces the pinned `"docs/MIGRATION-v1-to-v2.md"` and `"in v1 a tool with no entry runs by default, in v2 it skips"` assertions with the D-11 verbatim text checks: `"unsupported config version"`, `"this build supports schema version 2"`, `"config-init -o config.yaml"`.
    - `test_error_style_sdet_rejection_message` (added in Plan 01 Task 3) is UNCHANGED.
  </behavior>
  <action>
    Multi-edit in `tests/framework/unit/test_error_style.py` per RESEARCH §"Self-Test Inventory":

    1. **L36-41 `test_error_style_contains_safe_06_message`** — find the line `assert "docs/MIGRATION-v1-to-v2.md" in text` (or similar wording). DELETE that assertion. If the test has other assertions that remain valid (e.g., a header-section check), keep them; if the test devolves to only the MIGRATION assertion, DELETE the entire test function. Decide per actual file content — read it first.

       Note: RESEARCH suggests "drop the migration-doc assertion; keep `"### Config uses an older schema version"` + `"config file uses an older format:"` + `"schema version 2"` if those stay in the updated ERROR-STYLE.md, ELSE swap to assert the D-11 generic wording". Plan 05 handles ERROR-STYLE.md scrub — for this Task, the safer option is to drop the MIGRATION assertion AND replace any v1-walkthrough-pinned assertions with neutral "section exists / header present" checks OR with D-11 phrase checks; do NOT pin to ERROR-STYLE.md content that Plan 05 may rewrite.

    2. **L60-71 `test_error_style_safe_04_body_matches_cli_wiring`** — DELETE entire test function. Env-var typo error body is gone (Plan 02 deleted `_load_config` Branch 2).

    3. **L74-86 `test_error_style_safe_06_body_matches_cli_wiring`** — REWRITE. Replace the pinned-text checks with the D-11 verbatim text checks:
       - `assert "unsupported config version" in cli_source` (or whichever variable holds the read of cli.py)
       - `assert "this build supports schema version 2" in cli_source`
       - `assert "config-init -o config.yaml" in cli_source`
       - The test's NAME can stay (RESEARCH: "preserves test count + names").

    DO NOT touch `test_error_style_sdet_rejection_message` (added in Plan 01 Task 3) or any other tests in this file not flagged by RESEARCH §"Self-Test Inventory" as needing V1DROP-04 changes.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_error_style.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n 'test_error_style_safe_04_body_matches_cli_wiring' tests/framework/unit/test_error_style.py` returns zero matches.
    - `grep -n 'MIGRATION-v1-to-v2' tests/framework/unit/test_error_style.py` returns zero matches.
    - `grep -n 'in v1 a tool with no entry' tests/framework/unit/test_error_style.py` returns zero matches.
    - `grep -n 'unsupported config version\|this build supports schema version 2' tests/framework/unit/test_error_style.py` returns at least one match (the rewritten SAFE-06 positive assertion).
    - `uv run pytest tests/framework/unit/test_error_style.py -q` exits 0.
  </acceptance_criteria>
  <done>
    test_error_style.py no longer pins MIGRATION-walkthrough text in positive assertions; SAFE-06 body assertion swapped to D-11 verbatim text; SAFE-04 env-var test deleted.
  </done>
</task>

</tasks>

<verification>
Phase-level checks after all three tasks complete:

1. `uv run pytest tests/framework/unit/test_cli_errors.py tests/framework/unit/test_error_style.py -q` exits 0.
2. End-to-end v1-rejection smoke (the inline command in Task 1's `<automated>` block):
   - Create `/tmp/v1-test.yaml` with `version: 1\ntest_code:\n  generated_root: x\n`.
   - `uv run mcp-contracts run --config /tmp/v1-test.yaml` exits 2.
   - Combined stdout/stderr contains D-11 phrases; contains NO `MIGRATION-v1-to-v2`, `opt-in`, `opt-out`, `the difference matters`, `migration walkthrough`.
3. `grep -rn 'MIGRATION-v1-to-v2' src/mcp_test_framework/cli.py tests/framework/unit/test_cli_errors.py tests/framework/unit/test_error_style.py` returns zero matches (the file `docs/MIGRATION-v1-to-v2.md` is deleted in Plan 04; no negative-assertion residue per F-4 fix from revision).
</verification>

<success_criteria>
- All three tasks' acceptance criteria met.
- The v1-rejection message is generic operator-tone D-11 wording.
- Self-tests pinning the legacy migration-walkthrough text are rewritten (or deleted for env-var-based tests).
- ERROR-STYLE.md reference messages are NOT modified in this plan — Plan 05 (V1DROP-02 doc scrub) handles that file.
</success_criteria>

<output>
After completion, create `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-03-SUMMARY.md`
</output>
