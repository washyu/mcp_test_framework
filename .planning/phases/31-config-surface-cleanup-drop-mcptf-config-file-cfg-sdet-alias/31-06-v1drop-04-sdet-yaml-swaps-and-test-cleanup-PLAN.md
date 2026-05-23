---
phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
plan: 06
type: execute
wave: 3
depends_on: [31-01, 31-02, 31-03]
files_modified:
  - tests/framework/unit/test_config_sdet_field.py
  - tests/framework/unit/test_config.py
  - tests/framework/unit/test_config_init.py
  - tests/framework/unit/test_homelab_config.py
  - tests/framework/unit/test_list_tools_format.py
  - tests/framework/unit/test_runner_explain.py
  - tests/framework/unit/test_runner_migration.py
  - tests/framework/unit/test_dotenv_example.py
  - tests/framework/unit/test_mcp_config_fixture.py
  - tests/framework/unit/test_codegen_integration_mock.py
  - tests/framework/unit/test_gen_test_classes_pyproject_config.py
  - tests/framework/test_config_init_cli.py
  - tests/framework/test_runner_verbosity.py
  - tests/framework/test_runner_subprocess.py
  - tests/framework/test_tool_config.py
  - tests/framework/smoke/test_mcp_client_teardown_regression.py
  - tests/framework/unit/test_sdet_cli.py
  - tests/framework/unit/test_sdet_fixtures.py
autonomous: true
requirements: [V1DROP-04]
tags: [v1-decommission, self-test-cleanup, sdet-yaml-swap, env-var-scrub]
must_haves:
  truths:
    - "`uv run pytest tests/framework/ -q` exits 0 at v1.5 baseline."
    - "No active positive assertion in tests/framework/ pins legacy v1-rejection migration text (`MIGRATION-v1-to-v2.md`, `opt-in tool selection`, `in v1 a tool with no entry`)."
    - "No test fixture in tests/framework/ embeds a top-level `sdet:` YAML literal (all swapped to `test_code:`); SHIM-04 alias removal in Plan 01 cleared the alias path so these fixtures now correctly construct via the surviving key."
    - "No test in tests/framework/ uses `monkeypatch.setenv('MCPTF_CONFIG_FILE', ...)` to exercise the env-var value-source path — those tests are either DELETED or rewritten to use `Config(yaml_file=...)` / `-o mcp_config_file=...` directly."
    - "Phase 32 deferral note honored — `test_sdet_cli.py`, `test_sdet_fixtures.py`, `test_gen_sdet_classes_*.py` get only minimal SDET-YAML + env-var-setup scrubs in this plan; deeper refactor is Phase 32's responsibility."
  artifacts:
    - path: "tests/framework/"
      provides: "Self-test suite at v1.5 baseline — no legacy text pins, no sdet: YAML, no MCPTF_CONFIG_FILE env-var-setup"
      contains: ""
  key_links: []
---

<objective>
Apply the cross-cutting self-test cleanup that completes V1DROP-04 — mechanical SDET-YAML-key swaps (`sdet:` -> `test_code:`) across ~10 fixture files, env-var-setup scrubs across ~8 files, plus the targeted DELETE/STRENGTHEN dispositions called out in RESEARCH §"Self-Test Inventory" but not handled by Plans 01/03. Runs in WAVE 2 because the test fixtures must follow Plan 01's SHIM-04 alias removal (otherwise `sdet:` fixtures hit the alias path and never see the new `extra_forbidden` branch), Plan 02's env-var unwiring (otherwise env-var-based tests still work for the wrong reason), and Plan 03's message rewrite (otherwise relaxation targets the wrong text). Implements the residual V1DROP-04 work after Plans 01/03 covered their inline test rewrites.

Purpose: Close the V1DROP-04 self-test story — the framework's own test suite is green at v1.5 baseline with no pins on legacy text or removed behaviors. Honors RESEARCH §"Phase 32 deferral note" by limiting edits in `test_sdet_*.py` files to mechanical key swaps and env-var-setup removal (deeper refactor is Phase 32's responsibility when the SDET surface itself is deleted).

Output: Edits across ~16 test files. Most edits are mechanical key swaps or env-var-setup deletions; a few (test_runner_migration.py KEEP+STRENGTHEN, test_config_init_cli.py v1-output assertion deletion) require judgment per RESEARCH guidance.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md
@.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md
@src/mcp_test_framework/config.py
@src/mcp_test_framework/cli.py
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Test fixtures -> framework code under test | Fixtures with stale `sdet:` literals will fail post-Plan-01; mechanical swap is the bulk of the work |
| `monkeypatch.setenv('MCPTF_CONFIG_FILE', ...)` -> Config loader | Post-Plan-02 the env var is inert; tests pinning the legacy behavior need DELETE or rewrite |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-31-06-01 | Tampering (MEDIUM) | Mechanical SDET key swap could miss a fixture and leave a test red | mitigate | Acceptance criteria below pin zero matches across `grep -rn 'sdet:' tests/framework/` (excluding intentional negative-test references); the test command `uv run pytest tests/framework/ -q` is the final gate. |
| T-31-06-02 | Tampering (LOW) | `test_runner_migration.py` STRENGTHEN could over-pin and fail under future legitimate refactors | accept | The strengthened assertion targets `_runner._build_pytest_args` D-10 IPC channel behavior, which RESEARCH §"D-10 IPC Channel Verification" confirms is the ONLY surviving CLI->plugin channel. Pinning it positively is a regression gate, not over-pinning. |
| T-31-06-03 | Repudiation (INFORMATIONAL) | `test_sdet_*` files touched in this plan are touched AGAIN in Phase 32 (SHIM-01..03) | accept | RESEARCH §"Phase 32 deferral note" explicitly flags the boundary: Plan 06 limits edits to YAML key swaps + env-var setup removal; Phase 32 plans the deeper deletion. Edits do not conflict. |

ASVS classification: V8.2 (no production-data exposure; pure test-code hygiene). Phase has no HIGH threats.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Mechanical SDET YAML key swaps (sdet: -> test_code:) across all flagged test fixtures</name>
  <files>tests/framework/unit/test_homelab_config.py, tests/framework/unit/test_list_tools_format.py, tests/framework/unit/test_runner_explain.py, tests/framework/test_runner_verbosity.py, tests/framework/test_runner_subprocess.py, tests/framework/test_tool_config.py, tests/framework/unit/test_codegen_integration_mock.py, tests/framework/unit/test_sdet_cli.py, tests/framework/unit/test_sdet_fixtures.py</files>
  <read_first>
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md §"Self-Test Inventory" (each SDET-fix entry pins the exact file + line range)
    - tests/framework/unit/test_homelab_config.py (L71-89 per RESEARCH)
    - tests/framework/unit/test_list_tools_format.py (L204-212)
    - tests/framework/unit/test_runner_explain.py (L69-73)
    - tests/framework/test_runner_verbosity.py (L174-177)
    - tests/framework/test_runner_subprocess.py (L218-241)
    - tests/framework/test_tool_config.py (L151-388)
    - tests/framework/unit/test_codegen_integration_mock.py (L19 docstring)
    - tests/framework/unit/test_sdet_cli.py + tests/framework/unit/test_sdet_fixtures.py (Phase 32 deferral applies — minimal edits only)
  </read_first>
  <behavior>
    - After this task, no test file in `tests/framework/` contains a top-level YAML literal `sdet:` followed by a nested test-code-shape block (`generated_root:`, `test_code_root:`, etc.). All such literals are flipped to `test_code:`.
    - Negative-test fixtures (where a test INTENTIONALLY embeds `sdet:` to verify the rejection — these were added in Plan 01 Task 3 or Plan 03 Task 2) are KEPT untouched; they are the verification mechanism for the SHIM-04 branch.
    - Docstring references to `cfg.sdet.generated_root` are flipped to `cfg.test_code.generated_root` (mechanical).
    - `test_sdet_cli.py` and `test_sdet_fixtures.py` get ONLY YAML-key swaps + env-var-setup removal in this plan; deeper refactor (deleting tests for `--sdet` flag, etc.) is Phase 32 SHIM-02/03 work.
  </behavior>
  <action>
    For each file, locate the embedded `sdet:` YAML fixture literal (typically inside a `textwrap.dedent("""..."""))` block or a triple-quoted f-string) and swap the top-level key from `sdet:` to `test_code:`. The nested fields under the key (`generated_root: ...`, etc.) are UNCHANGED — only the top-level key flips.

    Concrete example transformation:
    ```python
    # BEFORE
    yaml_content = textwrap.dedent("""\
        version: 2
        sdet:
          generated_root: out/
        tools: {}
    """)

    # AFTER
    yaml_content = textwrap.dedent("""\
        version: 2
        test_code:
          generated_root: out/
        tools: {}
    """)
    ```

    Per-file targets (line ranges per RESEARCH; verify against current HEAD before editing):

    1. **tests/framework/unit/test_homelab_config.py L71-89** — embedded `sdet:` YAML; swap key.
    2. **tests/framework/unit/test_list_tools_format.py L204-212** — embedded `sdet:` YAML + `monkeypatch.delenv("MCPTF_CONFIG_FILE", ...)`; swap key AND remove the delenv call (env-var no longer matters).
    3. **tests/framework/unit/test_runner_explain.py L69-73** — embedded `sdet:` YAML; swap key.
    4. **tests/framework/test_runner_verbosity.py L174-177** — embedded `sdet:` YAML; swap key.
    5. **tests/framework/test_runner_subprocess.py L218-241** — embedded `sdet:` YAML TWICE; swap both occurrences.
    6. **tests/framework/test_tool_config.py L151-388** — embedded `sdet:` + `version: 2` + `MCPTF_CONFIG_FILE` setenv across multiple tests; swap all `sdet:` keys AND remove all `monkeypatch.setenv("MCPTF_CONFIG_FILE", ...)` calls. NOTE: this is the file Backlog 999.5 calls out; env-var removal closes the surface but the underlying class-of-bug (pydantic-settings deep-merge) survives — Phase 34 ISOL-05 will revisit. Document the residual risk by leaving a comment in the file noting Phase 34 follow-up.
    7. **tests/framework/unit/test_codegen_integration_mock.py L19 docstring** — flip `cfg.sdet.generated_root` -> `cfg.test_code.generated_root` (DOCSTRING SCRUB only; no behavior change).
    8. **tests/framework/unit/test_sdet_cli.py + test_sdet_fixtures.py** — Phase 32 deferral applies: ONLY swap embedded `sdet:` YAML literals to `test_code:` AND remove `monkeypatch.setenv("MCPTF_CONFIG_FILE", ...)` calls. DO NOT delete tests for `--sdet` flag; DO NOT delete tests for legacy fixture names. Those deletions are Phase 32 SHIM-02/07 work.

    For any file flagged above, after editing, run `grep -n 'sdet:' <file>` — the only acceptable remaining matches are:
    - inline comments mentioning the historical key,
    - test cases that INTENTIONALLY embed `sdet:` to verify rejection (these are negative tests; RESEARCH inventory does NOT list them as SDET-fix targets — distinguish carefully).
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_homelab_config.py tests/framework/unit/test_list_tools_format.py tests/framework/unit/test_runner_explain.py tests/framework/test_runner_verbosity.py tests/framework/test_runner_subprocess.py tests/framework/test_tool_config.py tests/framework/unit/test_codegen_integration_mock.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - For each file in the file list, `grep -n 'sdet:' <file>` returns either zero matches OR matches only inside (a) inline comments, or (b) intentional negative-test fixtures (a comment near the match should say so).
    - For test_list_tools_format.py, test_tool_config.py, test_sdet_cli.py, test_sdet_fixtures.py: `grep -n 'MCPTF_CONFIG_FILE' <file>` returns zero matches (env-var setup removed).
    - `grep -n 'cfg\.sdet\.generated_root' tests/framework/unit/test_codegen_integration_mock.py` returns zero matches (the docstring scrub is complete).
    - The targeted pytest invocation in `<verify>` exits 0.
  </acceptance_criteria>
  <done>
    All flagged SDET YAML literals are swapped to `test_code:`; env-var-setup is removed from the listed non-`test_sdet_*` files; `test_sdet_cli.py` + `test_sdet_fixtures.py` have ONLY the minimal scrub applied (Phase 32 owns deeper changes).
  </done>
</task>

<task type="auto">
  <name>Task 2: Targeted DELETE / STRENGTHEN / SCRUB dispositions for non-mechanical test edits</name>
  <files>tests/framework/unit/test_runner_migration.py, tests/framework/unit/test_config.py, tests/framework/unit/test_config_init.py, tests/framework/unit/test_dotenv_example.py, tests/framework/unit/test_mcp_config_fixture.py, tests/framework/unit/test_gen_test_classes_pyproject_config.py, tests/framework/test_config_init_cli.py, tests/framework/smoke/test_mcp_client_teardown_regression.py, tests/framework/unit/test_config_sdet_field.py</files>
  <read_first>
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md §"Self-Test Inventory" (specific disposition per file: DELETE-class, RELAX-class, STRENGTHEN, etc.)
    - tests/framework/unit/test_runner_migration.py (L88-152 fallback test - DELETE; L162-222 STRENGTHEN target)
    - tests/framework/unit/test_config.py (L105-220 env-var setup + L238 version: 1 rejection test)
    - tests/framework/unit/test_config_init.py (L100-163 delenv block)
    - tests/framework/unit/test_dotenv_example.py (L75-77 assertion)
    - tests/framework/unit/test_mcp_config_fixture.py (L12 docstring)
    - tests/framework/unit/test_gen_test_classes_pyproject_config.py (L69, L105 env-var setenv)
    - tests/framework/test_config_init_cli.py (L65-83, L95, L128)
    - tests/framework/smoke/test_mcp_client_teardown_regression.py (L78, L89 env-var setup)
    - tests/framework/unit/test_config_sdet_field.py (Plan 01 reference asset; verify still valid post-Plan-01)
  </read_first>
  <behavior>
    - `test_runner_migration.py::test_mcptf_config_file_path_pointer_fallback` (and any similar) is DELETED (env-var path-pointer fallback is removed in Plan 02).
    - `test_runner_migration.py::test_resolver_does_not_write_mcptf_config_file` is KEPT and STRENGTHENED with a positive assertion that `_runner._build_pytest_args(..., mcp_config_path=PATH)` produces a subprocess argv containing `["-o", "mcp_config_file=PATH"]`.
    - `test_config.py` L105-220 env-var setup blocks are removed; L238 `version: 1` rejection test either has its pinned text relaxed to D-11 wording OR is deleted (planner discretion per D-12).
    - `test_config_init.py` L100-163 delenv block is removed (env-var no longer affects loader).
    - `test_dotenv_example.py` L75-77 assertion `"MCPTF_CONFIG_FILE" in text` is DELETED (`.env.example` no longer documents the env var per Plan 02).
    - `test_mcp_config_fixture.py` L12 docstring scrub removes env-var fallback reference (no behavior change).
    - `test_gen_test_classes_pyproject_config.py` L69 + L105: DELETE the test cases that exercise env-var fallback (env-var route gone); KEEP the pyproject-resolution test cases.
    - `test_config_init_cli.py` L65-83/L95: DELETE the v1-output assertions (RESEARCH flags this test as stale — it pre-dates the v1.2 v2-flip and may already be broken). L128 env-var setenv: REMOVE.
    - `test_mcp_client_teardown_regression.py` L78/L89: REWRITE to use `["-o", "mcp_config_file=..."]` IPC channel OR `--config PATH` CLI flag instead of env-var-based config pointing.
    - `test_config_sdet_field.py`: VERIFY still passes against the Plan 01 changes (this file invokes `_emit_operator_error_for_validation` directly; should be aligned with the new SHIM-04 branch).
  </behavior>
  <action>
    Per-file changes per RESEARCH §"Self-Test Inventory":

    1. **tests/framework/unit/test_runner_migration.py**
       - **L88-152 `test_mcptf_config_file_path_pointer_fallback` (and any similarly-shaped tests)** — DELETE entire test function. The path-pointer env-var fallback is removed in Plan 02.
       - **L162-222 `test_resolver_does_not_write_mcptf_config_file`** — KEEP test function. STRENGTHEN by adding a positive assertion:
         ```python
         # NEW positive assertion (after the existing "does not write env" check):
         from mcp_test_framework._runner import _build_pytest_args
         args = _build_pytest_args(mcp_config_path="/tmp/x.yaml", ...)  # match existing call signature
         assert any(a.startswith("mcp_config_file=") for a in args), args
         assert "-o" in args
         ```
         Adapt to actual `_build_pytest_args` signature and existing test idiom. The point is: the D-10 IPC channel (Plan 02's surviving SOLE CLI->plugin channel) is regression-pinned positively.

    2. **tests/framework/unit/test_config.py**
       - **L105-220** — scan for `monkeypatch.setenv("MCPTF_CONFIG_FILE", ...)` and `monkeypatch.delenv("MCPTF_CONFIG_FILE", ...)` calls; REMOVE them. The env-var no longer affects the loader; the calls are no-ops post-Plan-02 but should be removed for clarity.
       - **L238** — locate the `version: 1` rejection test. Per RESEARCH "SCRUB + DELETE-v1": either DELETE the test (Plan 03 already covers the rejection assertion in `test_cli_errors.py` and `test_error_style.py`) OR RELAX its pinned text to the D-11 wording. Recommended: DELETE — V1DROP-03 rejection is already covered in two other test files.

    3. **tests/framework/unit/test_config_init.py L100-163** — REMOVE the `monkeypatch.delenv("MCPTF_CONFIG_FILE", ...)` setup block. Post-Plan-02 the env-var no longer matters; the block is dead code.

    4. **tests/framework/unit/test_dotenv_example.py L75-77** — DELETE the assertion `assert "MCPTF_CONFIG_FILE" in text` (or whichever variable is the `.env.example` contents read). Plan 02 deleted the env-var documentation from `.env.example`; the assertion now fails.

    5. **tests/framework/unit/test_mcp_config_fixture.py L12 docstring** — scrub the env-var fallback comment in the docstring; replace with a `mcp_config_file` ini-key reference OR delete the comment if it's not load-bearing.

    6. **tests/framework/unit/test_gen_test_classes_pyproject_config.py L69, L105** — DELETE the test cases that use `monkeypatch.setenv("MCPTF_CONFIG_FILE", ...)` to exercise env-var-based resolution. KEEP the pyproject-resolution test cases. Net effect: 1-2 test functions deleted; the remaining tests in the file still cover the surviving routes.

    7. **tests/framework/test_config_init_cli.py L65-95 + L128** — DELETE the v1-output assertions (RESEARCH flags this test as stale Phase 13 code that was wrong even at HEAD). Either delete the entire `version: 1` assertion lines OR delete the whole test function if its only purpose was the v1-output check. L128 `monkeypatch.setenv("MCPTF_CONFIG_FILE", ...)`: REMOVE.

    8. **tests/framework/smoke/test_mcp_client_teardown_regression.py L78, L89** — REWRITE the env-var setup. Two routes available:
       - **Option A:** Replace `monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg))` with `monkeypatch.setattr(...)` or fixture-based `--config` CLI flag injection.
       - **Option B:** Replace with pytest's `-o mcp_config_file=...` ini-override mechanism if the test invokes pytest in a subprocess.
       Pick whichever matches the existing test's invocation style. The test's BEHAVIOR (smoke regression for MCP client teardown) is unchanged; only the config-pointing mechanism flips.

    9. **tests/framework/unit/test_config_sdet_field.py** — VERIFY mechanically via `uv run pytest tests/framework/unit/test_config_sdet_field.py -q` (exit 0 required). This file was the Plan 01 Task 3 reference asset; it invokes `_emit_operator_error_for_validation` directly and should still pass post-Plan-01. If the targeted pytest exits non-zero, fix the assertion to align with the new SHIM-04 branch (the new branch renders the D-02 text; the existing test verifies whichever pre-Plan-01 SAFE-03 / missing-field error it covered). Most likely no changes needed — the targeted pytest is the gate.

    After each per-file edit, run the targeted pytest for that file to confirm it passes.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/ -q</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest tests/framework/ -q` exits 0 (the v1.5 baseline gate).
    - `grep -rn 'MCPTF_CONFIG_FILE' tests/framework/` returns zero matches (after all env-var setup removals).
    - `grep -rn 'MIGRATION-v1-to-v2' tests/framework/` returns zero matches (Plan 03's F-4 revision dropped the negative-assertion lines, so a simple zero-match grep is the gate).
    - `grep -rn 'docs/MIGRATION-v1-to-v2' tests/framework/` returns zero matches.
    - `tests/framework/unit/test_runner_migration.py` contains both a deleted `test_mcptf_config_file_path_pointer_fallback` AND a strengthened positive assertion on `_build_pytest_args` D-10 IPC.
    - `tests/framework/unit/test_dotenv_example.py` does NOT contain `"MCPTF_CONFIG_FILE" in` style assertions.
    - `uv run pytest tests/framework/unit/test_config_sdet_field.py -q` exits 0 (the Plan 01 reference asset is green post-revision; F-6 mechanical gate).
  </acceptance_criteria>
  <done>
    All non-mechanical V1DROP-04 self-test dispositions from RESEARCH inventory are applied; `tests/framework/` is green at v1.5 baseline.
  </done>
</task>

</tasks>

<verification>
Phase-level checks after both tasks complete (this is the VERIFICATION GATE for the entire Phase 31 plan set — Plan 06 is the closing wave):

1. `uv run pytest tests/framework/ -q` exits 0 (V1DROP-04 success criterion #5 from ROADMAP).
2. Repo-wide sanity:
   - `grep -rn 'MCPTF_CONFIG_FILE' src/mcp_test_framework/` returns EXACTLY ONE match (the grandfathered detection in `_plugin.py` per D-09).
   - `grep -rn 'MCPTF_CONFIG_FILE' README.md docs/ .env.example examples/ tests/framework/` returns zero matches.
   - `grep -rn 'MIGRATION-v1-to-v2' src/ docs/ README.md tests/framework/` returns zero matches.
   - `grep -rn 'AliasChoices\|sdet-rename-shim\|_warn_or_reject_legacy_sdet_key\|_check_legacy_sdet_key_in_yaml' src/mcp_test_framework/` returns zero matches.
3. End-to-end functional checks (mirror ROADMAP success criteria 1-3):
   - **SC1:** Set `$env:MCPTF_CONFIG_FILE = "C:\Users\washy\AppData\Local\Temp\nonexistent.yaml"`, then `uv run pytest tests/framework/unit/test_error_style.py -q` — exits 0 (the env var is inert as a value source); stderr contains exactly ONE `[mcp-contracts]` DeprecationWarning with D-06 wording.
   - **SC2:** Create `/tmp/sdet-test.yaml` with `version: 2\nsdet:\n  generated_root: x\n`. `uv run mcp-contracts run --config /tmp/sdet-test.yaml` exits 2 with D-02 wording. `[tool.pytest.ini_options] mcp_config_file = /tmp/sdet-test.yaml` in pyproject.toml + `uv run pytest` exits 2 with D-02 wording.
   - **SC3:** Create `/tmp/v1-test.yaml` with `version: 1\ntest_code:\n  generated_root: x\n`. `uv run mcp-contracts run --config /tmp/v1-test.yaml` exits 2 with D-11 wording, no MIGRATION-v1-to-v2 reference.
   - **SC4:** `test ! -f docs/MIGRATION-v1-to-v2.md` AND `grep -rn 'MIGRATION-v1-to-v2' README.md docs/ .env.example examples/` returns zero matches.
</verification>

<success_criteria>
- Both tasks' acceptance criteria met.
- `uv run pytest tests/framework/` is green at v1.5 baseline.
- All four ROADMAP Phase 31 success criteria pass via the end-to-end checks in `<verification>`.
- Phase 32 deferral honored — `test_sdet_*.py` files received only minimal SDET-YAML + env-var-setup scrubs (Phase 32 owns deeper refactor).
- Backlog 999.5 status documented inline (test_tool_config.py comment notes Phase 34 ISOL-05 follow-up for the pydantic-settings deep-merge class-of-bug).
</success_criteria>

<output>
After completion, create `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-06-SUMMARY.md`
</output>
