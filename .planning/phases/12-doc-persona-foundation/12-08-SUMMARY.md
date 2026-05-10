---
phase: 12-doc-persona-foundation
plan: 08
subsystem: cli
tags: [cli, config-init, bootstrap, scaffold, gap-closure, typer, pydantic]

# Dependency graph
requires:
  - phase: 12-doc-persona-foundation
    provides: "_format_tools_yaml_scaffold helper (CLEAN-05); operator-tone _emit_operator_error path; AST-scan banned-token guard"
provides:
  - "config-init grows --command/--arg Typer flags overriding mcp_server.command/args via Pydantic v2 model_copy on frozen Config"
  - "FileNotFoundError handler writes a fallback scaffold shell to --output (when given) before _emit_operator_error fires"
  - "Fallback scaffold header names mcp_server.command and acknowledges --command/--arg overrides are not propagated (CONCERN #2 disposition)"
  - "docs/EXTENDING.md Step 2 has a 'Servers installed via uvx or pipx' H4 subsection naming the new flags"
  - "8 new regression tests across test_config_init.py / test_cli_errors.py / test_doc_scrub.py"
affects: ["12-09 (test_doc_scrub.py end-of-file appends; --command lines exempt from --config-pairing regex)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic v2 model_copy(update=...) for one-shot frozen-model field overrides at the CLI seam (do NOT re-instantiate Config(...) — that re-triggers settings_customise_sources and loses operator intent)"
    - "Fallback-scaffold-on-launch-failure pattern: write the runnable shell BEFORE the operator-tone error so 'edit and re-run' replaces 'hand-write a config'"
    - "TDD RED→GREEN with help-text AST-scan as the banned-token regression contract for new Typer flag help strings"

key-files:
  created: []
  modified:
    - "src/mcp_test_framework/cli.py"
    - "tests/unit/test_config_init.py"
    - "tests/unit/test_cli_errors.py"
    - "tests/unit/test_doc_scrub.py"
    - "docs/EXTENDING.md"

key-decisions:
  - "Pydantic v2 model_copy(update=...) on the frozen Config + nested McpServerConfig — re-instantiating Config(...) would re-run settings_customise_sources and erase the operator's --command/--arg intent"
  - "Fallback scaffold writes BEFORE _emit_operator_error so the operator gets BOTH the recovery artifact AND the operator-tone error; stdout-mode (no --output) skips the write because the operator can't edit stdout"
  - "Header comment explicitly tells the operator the scaffold shows framework default values, not their --command/--arg — locks the CONCERN #2 disposition (override propagation deferred) so an operator who used `--command pipx --arg my-server` and got the fallback isn't confused"
  - "Cleaned banned tokens (Phase 08, D-21, D-22, D-24, CD-06) from the config_init docstring as a Rule 1 fix — the new --help banned-token test surfaced them as user-facing leakage"
  - "EXTENDING H4 subsection nests under Step 2 (`####`) preserving the H3 four-step walkthrough sequence"

patterns-established:
  - "Doc-only TDD for narrow walkthrough sections: regression test asserts substring presence + 400-char surrounding-window context to prove the doc edit lives in the right narrative spot"
  - "AST-scan banned-token regression for CLI help text — protects every future Typer-flag help string from spec-ID leakage automatically"

requirements-completed: [CLEAN-05, PERSONA-03, PERSONA-01]

# Metrics
duration: ~10min
completed: 2026-05-09
---

# Phase 12 Plan 08: config-init bootstrap egg Summary

**Closed UAT gap 2 by adding `--command`/`--arg` Typer flags to `config-init`, writing a fallback scaffold on launch failure when `--output` is given, and documenting the uvx/pipx bootstrap recipe under EXTENDING Step 2 — all behind 8 new regression tests.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-09 (worktree timestamp)
- **Completed:** 2026-05-09
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- `mcp-test-framework config-init --command uvx --arg homelab-mcp -o config.yaml` now works on a fresh checkout — the operator no longer has to hand-write a `config.yaml` first to use `config-init`.
- When the configured launch command isn't on `PATH` AND `--output` was given, `config-init` now writes a runnable scaffold shell (four top-level blocks + empty `tools:` mapping + header comment naming `mcp_server.command` as the field to fix) BEFORE the operator-tone error fires. Recovery path is now "edit and re-run", not "start from a blank file".
- The fallback scaffold's header comment explicitly acknowledges that `--command`/`--arg` overrides are NOT propagated into the scaffold's `mcp_server` block — preventing operator confusion when their `--command pipx --arg my-server` invocation falls back to a scaffold showing `uvx` / `your-mcp-server-package`.
- `docs/EXTENDING.md` Step 2 has a new H4 "Servers installed via `uvx` or `pipx`" subsection that names the flags, shows the canonical invocation, and walks the fallback recovery path.
- 39-test plan verification suite green (16 in test_config_init.py + 12 in test_cli_errors.py + 11 in test_doc_scrub.py); full 148-test unit suite green.

## Task Commits

Each task was committed atomically (TDD cycle on tasks 1–2; doc-only TDD on task 3):

1. **Task 1 (RED): regression guards for --command/--arg + fallback scaffold** — `e9a901b` (test)
2. **Task 2 (GREEN): --command/--arg flags + fallback scaffold path in config_init** — `9aa196d` (feat)
3. **Task 3 (DOC + RED→GREEN): EXTENDING uvx/pipx subsection** — `5c7228d` (docs)

## Files Created/Modified

- `src/mcp_test_framework/cli.py` — `config_init` Typer command grew `--command CMD` (single string) and `--arg ARG` (multi-value, repeatable) options; override path uses `cfg.model_copy(update={"mcp_server": cfg.mcp_server.model_copy(update=...)})` on the frozen Config + McpServerConfig instances; FileNotFoundError handler now writes a fallback scaffold via `_format_tools_yaml_scaffold([])` plus a multi-line header comment to `--output` (when given) BEFORE `_emit_operator_error`. Docstring rewritten to drop banned tokens (Phase 08, D-21, D-22, D-24, CD-06) that were leaking into `--help`.
- `tests/unit/test_config_init.py` — 5 new tests appended: `test_config_init_command_arg_flags_override_defaults` (proves flags reach `cfg.mcp_server.command/args` via the operator-tone error's quoted values), `test_config_init_fallback_scaffold_written_on_launch_failure` (file exists, four top-level blocks + empty tools, header names `mcp_server.command`), `test_config_init_fallback_scaffold_header_documents_defaults_limitation` (CONCERN #2 lock), `test_config_init_fallback_scaffold_not_written_in_stdout_mode` (no-write regression guard for stdout mode), `test_config_init_success_path_unchanged_when_command_resolvable` (sanity guard via `monkeypatch.setattr` of `_list_tools_async`).
- `tests/unit/test_cli_errors.py` — 2 new tests appended: `test_config_init_help_text_no_banned_tokens` (catches banned tokens in `--help` output for the new --command/--arg help strings; also catches any future Typer-flag-help-string leakage), `test_config_init_fallback_scaffold_no_banned_tokens` (catches banned tokens in the fallback scaffold's header comment).
- `tests/unit/test_doc_scrub.py` — 1 new test appended: `test_extending_step2_mentions_uvx_pipx_bootstrap_flags` (asserts `--command` + `--arg` + (uvx|pipx) all present, with `--command` in a 400-char window centered on a `config-init` mention).
- `docs/EXTENDING.md` — new H4 subsection "Servers installed via `uvx` or `pipx`" inserted between the existing Step 2 paragraph and the Step 3 H3 heading. Body names the flags, shows `mcp-test-framework config-init --command uvx --arg homelab-mcp -o config.yaml`, explains override semantics ("override `mcp_server.command`/`mcp_server.args` for this one invocation"), and points operators at the fallback scaffold when the launcher itself isn't on PATH.

## Decisions Made

- **Override path uses `model_copy(update=...)`, not Config re-instantiation.** Re-instantiating `Config(mcp_server={...})` would re-trigger `settings_customise_sources` and risk env vars / `MCPTF_CONFIG_FILE` clobbering the operator's CLI-flag intent. Pydantic v2 `model_copy(update=...)` on the frozen instance is the documented idiom for "replace these fields, keep everything else".
- **Fallback scaffold writes BEFORE the operator-tone error inside the except block, not after.** Two reasons: (1) `_emit_operator_error` raises `typer.Exit` which would skip any post-error write, (2) the operator should see the recovery artifact regardless of which error branch fires next.
- **`--command`/`--arg` overrides are NOT propagated into the fallback scaffold's `mcp_server` block — and the header comment says so explicitly.** Propagating them would require either threading override args through `_format_tools_yaml_scaffold` or doing post-render string substitution; both expand the diff beyond the gap-2 scope. The explicit "Note: shows framework default values. If you intended `--command X --arg Y`, edit those lines to substitute your values" sentence in the header is the operator-facing acknowledgment of the limitation, locked behind `test_config_init_fallback_scaffold_header_documents_defaults_limitation`.
- **Cleaned banned tokens from the `config_init` docstring.** The new `test_config_init_help_text_no_banned_tokens` flagged `Phase 08`, `D-21`, `D-22`, `D-24`, `CD-06` already present in the existing docstring — they leaked into `--help` output. Treated as a Rule 1 fix (banned tokens in user-facing `--help` is operator-tone leakage); rewritten the docstring without the spec IDs.
- **EXTENDING H4 subsection (`####`), not H3.** Existing walkthrough uses `### Step 1` ... `### Step 4`. Nesting under Step 2 with H4 keeps the four-step H3 sequence intact.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cleaned banned tokens from config_init docstring (leaked into `--help`)**
- **Found during:** Task 1 RED verification — `test_config_init_help_text_no_banned_tokens` failed because the EXISTING docstring contained `Phase 08`, `D-21`, `D-22`, `D-24`, `CD-06`. The plan's Task 1 framing assumed the help-text test would only fail because the new flags didn't exist; in fact it failed because pre-existing banned tokens were already leaking into `--help` output.
- **Issue:** Banned spec IDs in the `config_init` docstring become part of the `--help` text Typer renders. PERSONA-03 / docs/ERROR-STYLE.md prohibit spec IDs in operator-facing output; `--help` is operator-facing.
- **Fix:** Rewrote the docstring without the spec-ID parentheticals (`(Phase 08 D-21)`, `-- D-24`, `(Phase 08 D-22, CD-06)`). Functionally equivalent text — same description, same exit-code list, same Output section, just no spec IDs. Also added the new "Override flags" section to the docstring describing `--command`/`--arg`.
- **Files modified:** `src/mcp_test_framework/cli.py` (config_init docstring)
- **Verification:** `test_config_init_help_text_no_banned_tokens` passes; full `--help` output verified manually to show the new flags with operator-tone wording.
- **Committed in:** `9aa196d` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug — banned tokens leaking into operator-facing `--help`)
**Impact on plan:** Tightly scoped to the same function the task was already editing. No scope creep — the docstring was the proximal cause of one of the seven Task 1 RED tests failing in a way the plan didn't anticipate.

## Issues Encountered

- **`test_config_init_fallback_scaffold_not_written_in_stdout_mode` passed vacuously in the RED state** rather than failing. Reason: on current trunk, no `--output` AND launch failure means the function path simply doesn't write any file at all (no fallback scaffold path exists yet). The test is therefore a "regression guard" (will catch a future bug where someone wires fallback writing into stdout mode) rather than a "specification of new behavior" test in the RED→GREEN sense. The other 6 tests went RED as expected. Documented in the Task 1 commit message.

## User Setup Required

None — pure additive code + docs. No environment changes; backwards-compatible (existing config-init invocations without `--command`/`--arg` are byte-identical).

## Cross-plan Coordination

- **Wave 1 with 12-07 + 12-09.** 12-07 already shipped (`6355120` SUMMARY, `26cb251` GREEN); this plan respected its ownership of README ~lines 90-93 and the EXTENDING `### CI secrets` subsection — no edits there.
- **`tests/unit/test_doc_scrub.py` co-edit with 12-09.** Per plan frontmatter `coordinates_with: ["12-09"]`. This plan appended `test_extending_step2_mentions_uvx_pipx_bootstrap_flags` end-of-file. 12-09 will append additional tests end-of-file (e.g., the parametrized `--config`-pairing regression test). End-of-file appends — no line collision expected.
- **`--command` lines in EXTENDING are exempt from 12-09's `--config`-pairing regex test by design.** At bootstrap time the operator does not yet have a `config.yaml`, so requiring `--config` on the bootstrap line would be circular. 12-09's planned test must skip lines containing `--command`.

## Forward Notes

- **Out of scope (deferred / acknowledged):**
  - **`McpServerConfig` defaults intentionally unchanged.** `command="homelab-mcp", args=[]` remain in `src/mcp_test_framework/models.py`. The v1.2 redesign that flips defaults to `None` is deferred per project memory `project_genericize_example_config`. Phase 12 must not touch these defaults.
  - **CONCERN #2: per-invocation override propagation into the fallback scaffold's `mcp_server` block is deferred.** When the operator runs `config-init --command pipx --arg my-server -o config.yaml` and launch fails, the resulting fallback scaffold currently shows the framework default `command: "uvx", args: ["your-mcp-server-package"]` — NOT the operator's `pipx`/`my-server`. The header comment's "shows framework default values; substitute your values" note acknowledges the limitation explicitly. Follow-up issue: "config-init fallback scaffold should reflect --command/--arg overrides".
  - **DEFERRED bullet from UAT gap 2: changing `models.py:61-68 command='homelab-mcp'` default to `None`.** v1.2 redesign work; not part of phase 12 scope.

## UAT gap-2 truth status

The UAT gap-2 truth — "An operator with a uvx-installed MCP server can run `mcp-test-framework config-init` against their server out of the box and get a populated scaffold" — flips from `failed` to satisfied via the three-part package:

- **PRIMARY (`--command`/`--arg`):** operator runs `config-init --command uvx --arg homelab-mcp -o config.yaml` on a fresh checkout and gets a populated scaffold. ✓
- **SECONDARY (fallback scaffold):** operator who runs `config-init -o config.yaml` with no flags and a stale default still gets a runnable scaffold shell with header comment guiding the fix. ✓
- **DOC-ONLY (EXTENDING subsection):** operator following the canonical EXTENDING walkthrough discovers the flags exist in Step 2. ✓

## Self-Check

- File checks:
  - `src/mcp_test_framework/cli.py` modified — FOUND
  - `tests/unit/test_config_init.py` modified — FOUND
  - `tests/unit/test_cli_errors.py` modified — FOUND
  - `tests/unit/test_doc_scrub.py` modified — FOUND
  - `docs/EXTENDING.md` modified — FOUND
- Commit checks:
  - `e9a901b` (Task 1 RED) — FOUND
  - `9aa196d` (Task 2 GREEN) — FOUND
  - `5c7228d` (Task 3 DOC) — FOUND
- Verification command (`uv run pytest tests/unit/test_config_init.py tests/unit/test_cli_errors.py tests/unit/test_doc_scrub.py`): 39 passed.
- Full unit suite (`uv run pytest tests/unit/`): 148 passed.

## Self-Check: PASSED

## Next Phase Readiness

- Plan 12-09 (last wave-1 plan) can now land. Its co-edit on `test_doc_scrub.py` will append end-of-file with no collision; its planned `--config`-pairing regex must exempt `--command` lines (the EXTENDING bootstrap recipe lands without `--config` by design).
- UAT gap 2 satisfied via PRIMARY+SECONDARY+DOC-ONLY. Phase 13 (SAFE) can now safely reference `mcp-test-framework config-init` as the canonical recovery action for missing-config and v1→v2 migration errors, knowing the command works on a fresh checkout (a SAFE-prerequisite that was implicit but unvalidated before this plan).

---
*Phase: 12-doc-persona-foundation*
*Completed: 2026-05-09*
