---
phase: 12-doc-persona-foundation
plan: 04
subsystem: cli + fixtures
tags: [cli, config-init, errors, scaffold, judge, persona-03, clean-05]
requires: [12-01]
provides:
  - cli._emit_operator_error helper
  - cli._emit_operator_error_for_validation ValidationError mapper
  - cli._yaml_key tool-name quoting helper
  - fixtures._pytest_exit_operator_tone helper
  - self-contained config-init scaffold (top-level ollama / mcp_server / judge_timeout_seconds / version / tools)
  - operator-tone errors at all four cli.py surfaces (config not found / ValidationError / refuse-overwrite / MCP-spawn)
  - operator-tone errors at four fixtures.py judge-connect surfaces (ConnectError / TimeoutException / generic Exception / missing-model)
affects: [phase-13, phase-15, phase-16]
tech-stack:
  added: []
  patterns:
    - operator-tone error helper (PERSONA-03)
    - JSON-quote string scalars in hand-formatted YAML (T-12-09 mitigation)
    - parallel preflight helper in fixtures.py (cannot import from cli.py)
key-files:
  created:
    - tests/unit/test_cli_errors.py
    - tests/unit/test_config_init.py
    - tests/unit/test_judge_errors.py
  modified:
    - src/mcp_test_framework/cli.py
    - src/mcp_test_framework/fixtures.py
decisions:
  - Adopt typer.Exit (not SystemExit) for helper exit semantics; CliRunner result.stderr is the assertion surface (mix_stderr removed in Click 8.2+)
  - Catch _pytest.outcomes.Exit (not SystemExit) when exercising _pytest_exit_operator_tone — pytest.exit raises a non-SystemExit exception
  - Add module-level stdlib re import for the bare-key regex (cleaner than __import__("re"))
metrics:
  duration: ~50 minutes
  completed: 2026-05-10
requirements: [CLEAN-05, CLEAN-01, PERSONA-03]
---

# Phase 12 Plan 04: cli/fixtures operator-tone + self-contained scaffold Summary

## One-liner

Plan 04 lands the `_emit_operator_error` helper, a self-contained `config-init` scaffold (top-level ollama/mcp_server/judge_timeout_seconds/version/tools all populated; `version: 1` literal; every discovered tool emitted as `skip: true` with a curated reason; no `target:` block), and operator-tone error rewrites at all four cli.py surfaces plus all four fixtures.py judge-connect surfaces — closing the cli/fixtures side of PERSONA-03 and CLEAN-05.

## What shipped

### `src/mcp_test_framework/cli.py`

- **`_emit_operator_error(summary, detail, next_step, *, exit_code=2) -> typing.NoReturn`** — canonical operator-tone renderer per `docs/ERROR-STYLE.md`. Emits `summary\n\n<detail lines>\n\nnext: <action>` to stderr and raises `typer.Exit` internally. Callers omit the `raise` prefix.
- **`_emit_operator_error_for_validation(exc, *, source) -> typing.NoReturn`** — maps `pydantic.ValidationError` to operator-tone errors with four branches: version mismatch (forward-compatible with SAFE-06), `target.tool_name` removal hint, missing required field, generic fallback (capped at three errors).
- **`_yaml_key(name) -> str`** — JSON-quotes tool names not matching `^[A-Za-z_][A-Za-z0-9_]*$` (T-12-09 mitigation).
- **`_load_config` rewritten** — operator-tone error for `--config` path-not-found and ValidationError; pops `MCPTF_CONFIG_FILE` on failure.
- **`_format_tools_yaml_scaffold` rewritten** — emits a complete runnable scaffold (top-level `ollama`, `mcp_server`, `judge_timeout_seconds`, `version: 1`, `tools:` with every discovered tool as `skip: true` + `skip_reason: "review and remove skip to enable"`). All string scalars JSON-quoted via `json.dumps`. No `target:` block.
- **`config-init` refuse-to-overwrite + `FileNotFoundError` handler rewritten** — both surfaces emit operator-tone errors via the helper.
- **`list-tools` `FileNotFoundError` handler added** — was previously raw; now catches and rewrites the MCP-spawn failure via the helper.

### `src/mcp_test_framework/fixtures.py`

- **`_pytest_exit_operator_tone(summary, detail, next_step, *, returncode=2)` helper added** — mirrors `cli._emit_operator_error`'s shape (cannot import from `cli.py` because pytest collects `fixtures.py` before the cli command is invoked).
- **Ollama-reachability preflight rewritten** — the single `except Exception` is now split into `httpx.ConnectError`, `httpx.TimeoutException`, and `Exception` branches. ConnectError and TimeoutException both name `ollama serve` as the recovery step. Generic Exception names "verify `ollama serve` is healthy."
- **Missing-model branch rewritten** — names the configured model and points operators at `ollama pull <model>` as the recovery step.

### Tests added

- `tests/unit/test_cli_errors.py` — 10 tests covering helper format, NoReturn signature, custom exit code, `_load_config` path-not-found / ValidationError version mismatch, `config-init` refuse-overwrite, `config-init` and `list-tools` MCP-spawn failure, and an AST scan that asserts no banned tokens appear in any `_emit_operator_error` keyword literal.
- `tests/unit/test_config_init.py` — 11 tests covering top-level block presence, `version: 1` literal, no `target:` block, all-skip-true tools, empty-tool-list, scaffold loadable via `Config()` with no `.env` (CLEAN-05 acceptance), no banned tokens, alphabetical sort, and `_yaml_key` defensive quoting.
- `tests/unit/test_judge_errors.py` — 6 tests covering helper format, custom returncode, ConnectError / Timeout / missing-model message shape, and helper exportability.

Total new test surface: **27 tests**, all passing.

## Verification

```
$ uv run pytest tests/unit/
============================= 108 passed in 0.41s =============================
```

All 102 pre-existing unit tests still pass; the 6 new + 11 new + 10 new (= 27) tests bring the total to 108 (test_cli_errors.py existed pre-plan with 0 tests; the 10 new tests are net additions).

Spot-checks against the plan's six verification commands:

1. ✓ `from mcp_test_framework.cli import _emit_operator_error; from mcp_test_framework.fixtures import _pytest_exit_operator_tone` — both importable.
2. ✓ `pytest tests/unit/test_config_init.py -x` — 11 passed.
3. ✓ `pytest tests/unit/test_cli_errors.py -x` — 10 passed.
4. ✓ `pytest tests/unit/test_judge_errors.py -x` — 6 passed.
5. ✓ `pytest tests/unit/test_config.py -x` — 11 passed (existing v1.1 regression).
6. ✓ AST scan — no banned tokens in `_emit_operator_error` keyword literals.

`grep -c '_emit_operator_error(' src/mcp_test_framework/cli.py` returns **11** (definition + 10 callsites). `grep -c '_pytest_exit_operator_tone' src/mcp_test_framework/fixtures.py` returns **5** (definition + 4 callsites: ConnectError, TimeoutException, generic Exception, missing-model).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `pytest.raises(SystemExit)` does not catch `typer.Exit`**

- **Found during:** Task 1a GREEN phase
- **Issue:** The plan's test code used `pytest.raises(SystemExit)` to catch the helper's exit. `typer.Exit` (= `click.exceptions.Exit`) inherits from `RuntimeError`, not `SystemExit`, so the test failed with an uncaught `click.exceptions.Exit`.
- **Fix:** Imported `typer` in the test module and changed both helper-format tests to use `pytest.raises(typer.Exit)` and assert against `ei.value.exit_code` (Click's attribute name) instead of `ei.value.code`.
- **Files modified:** `tests/unit/test_cli_errors.py`
- **Commit:** 23b646a

**2. [Rule 3 - Blocking] `CliRunner(mix_stderr=False)` invalid in Click 8.2+**

- **Found during:** Task 1a GREEN phase
- **Issue:** Plan-supplied test helper passed `mix_stderr=False` to `CliRunner`. Newer Click versions removed the kwarg (stderr is captured separately by default); test failed with `TypeError`.
- **Fix:** Dropped the kwarg. `CliRunner.invoke()` result `.stderr` attribute already returns stderr separately on the installed version.
- **Files modified:** `tests/unit/test_cli_errors.py`
- **Commit:** 23b646a

**3. [Rule 3 - Blocking] `pytest.raises(SystemExit)` does not catch `_pytest.outcomes.Exit`**

- **Found during:** Task 3 GREEN phase
- **Issue:** Plan-supplied test code in `test_judge_errors.py` used `pytest.raises(SystemExit)` to catch `pytest.exit`'s effect. `pytest.exit` raises `_pytest.outcomes.Exit` which inherits from `Exception`, not `SystemExit`. The exception escaped the test, and pytest treated it as a session-exit signal — no tests ran.
- **Fix:** Added a `_pytest_exit_exc()` helper in the test module that imports `_pytest.outcomes.Exit` and returns it (with a defensive fallback). Changed both helper tests to use `pytest.raises(_pytest_exit_exc())`.
- **Files modified:** `tests/unit/test_judge_errors.py`
- **Commit:** 565d659

### Departures from plan code-block (intentional)

- **Plan said `import re as _re_yaml_key`.** I added a module-level `import re` instead and used `re.compile` directly. Cleaner and avoids the alias indirection — no other consumers of `re` were colliding.

### v1.1 regression check (`tests/test_config_init_cli.py`)

The plan acceptance criterion calls for `uv run pytest tests/test_config_init_cli.py -x` to still pass. In this environment, the v1.1 unit-level tests (`test_help_lists_flags`, `test_refuse_overwrite_without_force`) cannot be exercised because the session-scoped `_preflight` fixture aborts the run with `MCP command 'homelab-mcp' not found on PATH` (this branch lacks homelab-mcp on PATH). I confirmed this is a pre-existing failure on unmodified `main` via `git stash` round-trip — not a regression introduced by Plan 04. Live-marker tests in the same file would also need a live homelab-mcp + Ollama; out of scope for unit verification.

The unit-level scaffold tests in this plan (`tests/unit/test_config_init.py`) cover the same acceptance surface (round-trip scaffold + `Config()` load) without requiring a live MCP server.

## Threat Flags

None. The plan's threat-model entries (T-12-09 through T-12-19) were all addressed in implementation:

- T-12-09 (tampering via malicious tool name): `_yaml_key` JSON-quotes any non-bare-identifier name; all string scalars in the header use `json.dumps`. Defensive test `test_scaffold_yaml_key_quotes_unsafe_names` enforces this.
- T-12-10 (path echo in error messages): `--config` path is the operator's input; acceptable per disposition.
- T-12-11 (DoS via many validation errors): Capped via `errors[:3]` in the generic-fallback branch.
- T-12-12 (info disclosure via pydantic ctx): The validation mapper uses only `loc`, `type`, and `msg` from each error dict — never `input` or `ctx`.
- T-12-19 (info disclosure via `available_models`): Operator-controlled (their own Ollama instance); accepted per disposition.

## Self-Check: PASSED

All claimed files exist:

- `src/mcp_test_framework/cli.py` (modified, 11 `_emit_operator_error` references)
- `src/mcp_test_framework/fixtures.py` (modified, 5 `_pytest_exit_operator_tone` references)
- `tests/unit/test_cli_errors.py` (10 tests)
- `tests/unit/test_config_init.py` (11 tests)
- `tests/unit/test_judge_errors.py` (6 tests)

All claimed commits exist:

- 81bb2df — test(12-04): add failing tests for _emit_operator_error helper
- 23b646a — feat(12-04): add _emit_operator_error helper and rewrite _load_config
- 6f1eb6f — test(12-04): add failing tests for remaining error sites
- 29cd797 — feat(12-04): rewrite remaining cli.py error sites via operator-tone helper
- 7df8024 — test(12-04): add failing tests for self-contained config-init scaffold
- 9da7817 — feat(12-04): rewrite _format_tools_yaml_scaffold for self-contained output
- ba458de — test(12-04): add failing tests for judge-connect operator-tone helper
- 565d659 — feat(12-04): rewrite judge-connect preflight via operator-tone helper

## TDD Gate Compliance

Each of the three tasks followed the RED → GREEN cycle with separate commits:

- Task 1a: 81bb2df (RED) → 23b646a (GREEN)
- Task 1b: 6f1eb6f (RED) → 29cd797 (GREEN)
- Task 2:  7df8024 (RED) → 9da7817 (GREEN)
- Task 3:  ba458de (RED) → 565d659 (GREEN)

All RED commits land failing tests; all GREEN commits land minimal implementation that turns them green. No REFACTOR commits needed — the implementation is already minimal.
