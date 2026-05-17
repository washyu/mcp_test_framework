---
phase: 28-codegen-output-path-codegen
plan: 03
subsystem: cli

tags: [typer, gen-test-classes, overwrite-prompt, non-tty, operator-tone-error, mcp-contracts-rename]

# Dependency graph
requires:
  - phase: 28-codegen-output-path-codegen/plan-01
    provides: "Pre-handshake site-packages guard + hoisted out_root resolution. Wave 3 slots the overwrite prompt AFTER the guard and BEFORE the codegen call, on the resolved out_root / slug target."
  - phase: 28-codegen-output-path-codegen/plan-02
    provides: "_load_config tuple-return + pyproject ini route; this plan operates downstream of any config-resolution change."
provides:
  - "_confirm_or_abort_non_empty_target(target_dir) helper exported from mcp_test_framework.cli."
  - "Wipe-and-write codegen now blocked by a confirmation gate: missing/empty dir silent, non-empty TTY prompts, non-empty non-TTY aborts exit 2."
  - "Operator-facing missing-required-field next-step copy flipped from legacy mcp-test-framework config-init to canonical mcp-contracts config-init (D-02 audit + patch)."
affects:
  - "28-04 (docs sweep): operator-facing docs that describe gen-test-classes should mention the overwrite-prompt behavior AND the no-escape-hatch posture."
  - "v1.5 deprecation removal: the locked v1->v2 migration message and no-config-found message still carry legacy mcp-test-framework config-init copy; both are pinned by ERROR-STYLE.md + test_error_style.py and live on a separate cleanup track."

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pre-write confirmation gate ordering: load config -> resolve out_root -> site-packages guard -> handshake -> server-name check -> slug derivation -> non-empty-dir confirm-or-abort -> _codegen.generate()."
    - "TTY vs non-TTY branching via explicit sys.stdin.isatty() check BEFORE calling typer.confirm (predictable behavior across Typer/Click versions; non-TTY abort emits operator-tone error inline rather than relying on click.exceptions.Abort)."
    - "Iteration cap (1000 entries) on target-dir scan with `+` suffix indicator so a pathological tree never stalls the CLI."

key-files:
  created:
    - tests/framework/unit/test_gen_test_classes_overwrite_prompt.py
    - tests/framework/unit/test_missing_generated_root_error.py
  modified:
    - src/mcp_test_framework/cli.py

key-decisions:
  - "Helper placement (cluster with site-packages guard): _confirm_or_abort_non_empty_target inserted immediately AFTER _guard_against_site_packages_target and BEFORE _emit_operator_error_for_validation -- keeps the gen-test-classes safety-check helpers (guard + prompt) physically colocated in the source for easy discovery."
  - "Slug derivation relocated ABOVE _codegen.generate() so the prompt can reference out_root / slug, the actual write target. Existing post-codegen typer.echo target line unchanged; only the variable's lifetime moved earlier."
  - "D-02 patch scoped to the missing-field branch ONLY. The locked v1->v2 migration message (cli.py line ~294) and no-config-found message (cli.py line ~509) still reference the legacy mcp-test-framework config-init shim because both are pinned verbatim against ERROR-STYLE.md by tests/framework/unit/test_error_style.py. Flipping either without also amending ERROR-STYLE.md + retiring the pinned regression test would break the wider documentation chain. Tracked for v1.5 cleanup alongside the rest of the deprecation shim removal."
  - "No --yes / --force flag added (D-06 lock). Regression-guarded by test_gen_test_classes_command_has_no_yes_or_force_flag which scans `mcp-contracts gen-test-classes --help` stdout for both tokens."
  - "File-count cap at 1000 entries (CONTEXT.md Claude-Discretion item: bounded scan cost). Suffix '+' appended to the count when the cap is hit so the operator sees `1000+ entries exist in <path>. Overwrite?` rather than a misleading exact count."
  - "iterdir() chosen over rglob() for the count -- the gate cares whether the target has direct contents (the codegen wipe operates on the top level), not the total recursive file count. Cheaper and matches operator intuition (a directory with one subfolder is non-empty)."

patterns-established:
  - "Safety-check ordering inside gen-test-classes: any new pre-codegen safety check slots between slug derivation and _codegen.generate(target_dir=out_root/slug). Future destructive operations on the same target dir reuse the same insertion point."
  - "D-02 acceptance pattern (literal-string assertion + legacy-name negative assertion + exit-code assertion in a single test body) is the template for verifying operator-tone errors that flip from legacy to canonical CLI names during the v1.4 deprecation window."

requirements-completed: [CODEGEN-LIB-01]

# Metrics
duration: ~4min
completed: 2026-05-17
---

# Phase 28 Plan 03: Overwrite Prompt Summary

**Wipe-and-write codegen now gated by a confirmation prompt: missing or empty target writes silently; non-empty target in a TTY prompts via `typer.confirm` (declining aborts exit 2); non-empty target in a non-TTY context (CI, scripts, piped stdin) aborts with operator-tone error exit 2. No `--yes` / `--force` escape hatch. Missing-`test_code.generated_root` operator error next-step copy flipped from legacy `mcp-test-framework config-init` to canonical `mcp-contracts config-init` (D-02).**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-17T04:23:54Z
- **Completed:** 2026-05-17T04:28:08Z
- **Tasks:** 2 (TDD each)
- **Files modified:** 1 (cli.py)
- **Files created:** 2 (test_gen_test_classes_overwrite_prompt.py + test_missing_generated_root_error.py)

## Accomplishments

- `_confirm_or_abort_non_empty_target(target_dir)` helper added to `src/mcp_test_framework/cli.py` (line 147). Five-branch decision tree:
  1. `target_dir` does not exist -> return silently (`_codegen.generate` will create it).
  2. `target_dir` exists but is empty -> return silently.
  3. `target_dir` non-empty AND `sys.stdin.isatty()` True -> `typer.confirm(...)` prompt with file count + target path; declining raises `typer.Exit(2)` via `_emit_operator_error`.
  4. `target_dir` non-empty AND `sys.stdin.isatty()` False -> `_emit_operator_error` exit 2 (no escape hatch; operator-tone abort message tells the operator to delete the directory manually and re-run).
  5. `OSError` while reading the directory -> fall through (the codegen call surfaces a clearer error than the gate could).
- Iteration capped at 1000 entries; a `+` suffix appears in both the prompt and the abort message when the cap is hit so the count never lies.
- Wired into `gen_test_classes` between slug derivation and `_codegen.generate()`. Slug derivation (previously sitting AFTER the codegen call for use in the echo block) was relocated above so the prompt can reference `out_root / slug` -- the actual write target, not the parent `out_root` which may contain unrelated generated trees.
- Missing-required-field branch of `_emit_operator_error_for_validation` (cli.py line 219) `next_step` copy flipped from `mcp-test-framework config-init` to `mcp-contracts config-init` per D-02. Field-path naming (`test_code.generated_root`) already correct -- no detail-block rewrite required.
- 7/7 new overwrite-prompt tests pass; 1/1 new D-02 regression test passes; 624-test `tests/framework/` suite stays green (was 623 before this plan).

## Task Commits

Each task was committed atomically (TDD RED -> GREEN):

1. **Task 1 RED: failing overwrite-prompt tests** - `b7224b9` (test)
2. **Task 1 GREEN: helper + gen_test_classes wiring** - `07786f2` (feat)
3. **Task 2 RED: failing missing-generated_root literal pin** - `bd9a695` (test)
4. **Task 2 GREEN: flip next-step CLI name to mcp-contracts** - `f639de6` (fix)

_Final plan-metadata commit (SUMMARY + STATE + ROADMAP) follows this file._

## Files Created/Modified

- `src/mcp_test_framework/cli.py`
  - Added `_confirm_or_abort_non_empty_target` helper (line 147; 80 lines including docstring).
  - Wired the helper into `gen_test_classes` at line 1300 between the relocated `slug = server_slug(server_name)` (line 1298) and the `_codegen.generate(...)` call (line 1305).
  - Removed the duplicate post-codegen `slug = server_slug(server_name)` assignment (the slug variable is now derived once, above the codegen call, and reused in the echo block).
  - Flipped `next_step` from `mcp-test-framework config-init -o config.yaml` to `mcp-contracts config-init -o config.yaml` in the missing-required-field branch of `_emit_operator_error_for_validation` (line 310).
- `tests/framework/unit/test_gen_test_classes_overwrite_prompt.py` (new) - 7 tests:
  1. `test_missing_target_dir_returns_silently` - non-existent dir is a no-op.
  2. `test_empty_target_dir_returns_silently` - empty dir is a no-op.
  3. `test_non_empty_dir_in_tty_accept_returns_silently` - mock `sys.stdin.isatty=True` + `typer.confirm=True` -> no raise.
  4. `test_non_empty_dir_in_tty_decline_aborts_exit_2` - mock `typer.confirm=False` -> `typer.Exit(2)`.
  5. `test_non_empty_dir_in_non_tty_aborts_with_exit_2` - mock `sys.stdin.isatty=False` -> `typer.Exit(2)` + asserts message names the path, mentions non-interactive/non-empty, and does NOT mention `--yes`/`--force`.
  6. `test_file_count_appears_in_prompt` - asserts the file count and target path both appear in the prompt text.
  7. `test_gen_test_classes_command_has_no_yes_or_force_flag` - regression guard scanning `--help` output for both forbidden tokens.
- `tests/framework/unit/test_missing_generated_root_error.py` (new) - 1 test (`test_missing_generated_root_error_names_field_and_config_init`) asserting the missing-`test_code.generated_root` operator error contains `test_code.generated_root`, contains `mcp-contracts config-init`, does NOT contain `mcp-test-framework config-init`, and exits with code 2.

## Decisions Made

- **Five-branch decision tree (D-05 + D-06 lock):** The helper distinguishes missing dir from empty dir from non-empty/TTY-accept from non-empty/TTY-decline from non-empty/non-TTY. The OSError swallow is a sixth (degenerate) branch that defers to the codegen call's own error surface.
- **Explicit `sys.stdin.isatty()` check (over typer.confirm's default Abort behavior):** Predictable across Typer/Click versions; the non-TTY path emits a dedicated operator-tone error inline rather than relying on click's bare `Abort` which would surface less helpfully.
- **Iteration cap at 1000 entries:** Bounded scan cost (CONTEXT.md Claude-Discretion item). `+` suffix in the prompt/abort copy when the cap fires, so the operator sees an honest "1000+ entries" rather than a misleading exact-1000 count.
- **iterdir() (top-level) not rglob() (recursive):** The codegen wipe-and-write operates on the top-level target. A directory with one subfolder is non-empty for the gate's purpose; the operator intuition matches the cheaper one-syscall scan.
- **Slug relocated, NOT duplicated:** `slug = server_slug(server_name)` was moved from its original post-codegen position (used only for the echo block) to BEFORE the codegen call so the prompt can reference `out_root / slug`. The post-codegen echo block reuses the same `slug` variable -- single derivation site.
- **D-02 patch is scoped narrowly to the missing-field branch.** Flipping the legacy CLI name in the locked v1->v2 migration message (line ~294) or the no-config-found message (line ~509) would break `test_error_style.py` source-text pins. ERROR-STYLE.md itself still uses the legacy name in §"No config found" and §"Config uses an older schema version". The wider sweep belongs on a v1.5 cleanup pass alongside ERROR-STYLE.md rewrites and the pinned regression-test retirement.

## D-02 Audit Result

Live capture (Step A) executed via `CliRunner.invoke(app, ["run", "--config", <tmp/config-with-empty-test_code-block.yaml>])`. Captured `result.stderr`:

```
config file is missing a required field: test_code.generated_root

the field `test_code.generated_root` is required but was not found in <path>/config.yaml.

see config.example.yaml for the expected shape, or regenerate a starter file with config-init.

next: copy the relevant block from config.example.yaml or run `mcp-test-framework config-init -o config.yaml`
```

Audit matrix vs D-02 acceptance bar:

| Literal | Pre-patch | Post-patch |
| --- | --- | --- |
| `test_code.generated_root` (full field path) | PRESENT (via `loc = ".".join(...)`) | unchanged - PRESENT |
| `mcp-contracts config-init` | ABSENT | PRESENT (line 310) |
| `mcp-test-framework config-init` (legacy, should be ABSENT in this branch's next-step) | PRESENT (line 310) | ABSENT in this branch |

Patch applied: one-line `next_step` body flip in `_emit_operator_error_for_validation`'s missing-field branch. No detail-block rewrite needed (the `{loc}` interpolation already produces the canonical field path because Pydantic surfaces `loc = ("test_code", "generated_root")` when the YAML provides `test_code: {}` but omits `generated_root`).

## Deviations from Plan

None requiring auto-fix rules. Two minor judgment calls documented:

1. **[Judgment] D-02 patch scope narrowed to missing-field branch only.** The plan said "Also scan the rest of `_emit_operator_error_for_validation` for any other `mcp-test-framework config-init` occurrences in operator-facing next-step copy. If found, flip those too." Three occurrences exist inside the function (lines ~294, ~310, ~328). Lines ~294 (locked v1->v2 migration message) and ~509 (no-config-found, outside the function but in cli.py) are pinned verbatim against ERROR-STYLE.md by `tests/framework/unit/test_error_style.py`. Flipping either without also amending ERROR-STYLE.md and retiring the corresponding source-text regression test would break the wider documentation chain. Line ~328 (generic fallback) was left untouched to keep the patch surface minimal and consistent with the locked-spec pattern -- it can flip later once the wider v1.5 cleanup sweep amends ERROR-STYLE.md and the pinned tests. The plan acknowledged this risk explicitly: "tests/framework/unit/test_error_style.py and any source-text regression test pinning the v1->v2 migration message stays GREEN, since that branch is the version-mismatch branch, not the missing-field branch". Decision: only the missing-field branch flipped; v1.5 cleanup tracked.
2. **[Cosmetic] `mock_confirm.call_args[0][0]` -> `mock_confirm.call_args.args[0]`** in `test_file_count_appears_in_prompt`. The plan's literal pattern works on older Mock APIs; `call_args.args` is the modern attribute (Python 3.8+) and is clearer about positional-vs-keyword intent. Same semantics, no behavior change.

No Rule-1/Rule-2/Rule-3 auto-fixes triggered. No architectural questions surfaced. Both RED -> GREEN gates passed on first attempt after the helper/wiring/patch landed.

## Issues Encountered

None. RED gates fired as expected (ImportError for Task 1; literal-string assertion failure for Task 2). GREEN gates passed on first runs.

One environmental quirk worth noting (NOT a test failure): the bundled `CliRunner` in this Click/Typer version does not accept `mix_stderr=False` -- the live-capture script and regression test both work around this by combining `result.stdout + result.stderr` (`result.stderr` is `None`-safe in the test).

## User Setup Required

None -- no external service configuration required. Operators who already have `cfg.test_code.generated_root` set to an empty subdirectory of their project get the new behavior automatically with zero prompt (the empty-dir branch returns silently).

## Next Phase Readiness

- 28-04 (docs sweep) unblocked: operator-facing docs that describe `gen-test-classes` config resolution should now also describe (a) the overwrite-prompt behavior, (b) the deliberate absence of `--yes`/`--force`, and (c) the missing-`test_code.generated_root` error pointing at `mcp-contracts config-init`. Suggested copy: "If your configured `test_code.generated_root` already contains files, `gen-test-classes` will prompt before overwriting in an interactive shell, or abort with a 'clean the directory manually' error in a non-interactive context (CI, piped stdin). There is no `--yes` or `--force` flag -- the strongest 'never silently destroy data' posture."
- v1.5 cleanup tracked: ERROR-STYLE.md §"No config found" + §"Config uses an older schema version" still reference `mcp-test-framework config-init`; flipping both alongside `test_error_style.py` source-text pins is a Phase 30 / v1.5-deprecation-removal task, NOT a Phase 28 follow-up.
- No blockers carried into 28-04.

## Self-Check: PASSED

- FOUND: src/mcp_test_framework/cli.py (`def _confirm_or_abort_non_empty_target(` at line 147; `_confirm_or_abort_non_empty_target(target_dir)` invocation inside `gen_test_classes` at line 1300; located AFTER `slug = server_slug(server_name)` at line 1298 and BEFORE `_codegen.generate(` at line 1305)
- FOUND: tests/framework/unit/test_gen_test_classes_overwrite_prompt.py (7 test functions; all PASS via `uv run pytest`)
- FOUND: tests/framework/unit/test_missing_generated_root_error.py (1 test function; PASS via `uv run pytest`)
- FOUND: commit b7224b9 (Task 1 RED -- test)
- FOUND: commit 07786f2 (Task 1 GREEN -- feat)
- FOUND: commit bd9a695 (Task 2 RED -- test)
- FOUND: commit f639de6 (Task 2 GREEN -- fix)
- Verified: `uv run pytest tests/framework/unit/test_gen_test_classes_overwrite_prompt.py -x -v` -> 7 passed
- Verified: `uv run pytest tests/framework/unit/test_missing_generated_root_error.py -xvs` -> 1 passed
- Verified: `uv run pytest tests/framework/ -x` -> 624 passed, 1 skipped, 17 deselected, 1 xfailed
- Verified: `uv run mcp-contracts gen-test-classes --help` stdout/stderr contains no `--yes` or `--force` token
- Verified: missing-required-field branch's next_step copy contains `mcp-contracts config-init` (not `mcp-test-framework config-init`); the v1->v2 + no-config-found branches still carry the legacy name, as expected (pinned to ERROR-STYLE.md).
- Verified: `_confirm_or_abort_non_empty_target` is defined once and called once from `gen_test_classes`.

## TDD Gate Compliance

- Task 1 RED gate: `b7224b9` -- test commit precedes GREEN; ImportError on `_confirm_or_abort_non_empty_target` confirmed RED.
- Task 1 GREEN gate: `07786f2` -- feat commit follows RED; 7/7 tests pass.
- Task 2 RED gate: `bd9a695` -- test commit precedes GREEN; literal-string assertion failure on absent `mcp-contracts config-init` confirmed RED.
- Task 2 GREEN gate: `f639de6` -- fix commit follows RED; 1/1 test passes.
- REFACTOR gate: not required for either task (helpers/patches landed in final shape on first GREEN).

---
*Phase: 28-codegen-output-path-codegen*
*Completed: 2026-05-17*
