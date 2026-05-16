---
status: complete
phase: 25-public-api-rename-seed-023-sdet-test-code
source:
  - 25-01-SUMMARY.md
  - 25-02-SUMMARY.md
  - 25-03-SUMMARY.md
  - 25-04-SUMMARY.md
  - 25-05-SUMMARY.md
  - 25-06-SUMMARY.md
started: 2026-05-16T04:18:51Z
updated: 2026-05-16T04:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. New CLI command surfaces with renamed name
expected: |
  `uv run mcp-test-framework --help` lists `gen-test-classes`. The old
  `gen-sdet-classes` is hidden from `--help`. `uv run mcp-test-framework
  gen-test-classes --help` prints subcommand help with no DeprecationWarning.
result: pass

### 2. Legacy CLI command still callable, warns once, names v1.5
expected: |
  Body-executing invocation (NOT `--help` — `--help` short-circuits
  before the command body runs).
  Re-verified via:
  `uv run python -W always -c "import sys; sys.argv=['mcp-test-framework','gen-sdet-classes']; from mcp_test_framework.cli import app; app()"`
  Emitted exactly one DeprecationWarning naming v1.5:
  `"gen-sdet-classes is deprecated since v1.4 and will be removed in v1.5 — use gen-test-classes instead."`
  Command body then ran codegen successfully (58 tools generated).
result: pass
note: |
  Original pass was a false-positive — test wording used `--help` which
  bypasses the command body where the warning lives. Re-verified with a
  body-executing invocation; warning fires correctly. The
  `gen-sdet-classes` shim emits its warning from the command body
  (line 1093-1099 in cli.py); body runs on real invocations, not on
  `--help`. This is acceptable for command-level shims — operators who
  type `gen-sdet-classes --help` will see only the help text, but the
  next time they actually invoke it they'll see the warning.

### 3. New flag on `run`: `--test-code` works
expected: |
  `uv run mcp-test-framework run --test-code --help` (or any non-destructive
  invocation) accepts the new flag. No DeprecationWarning emitted.
  The flag's help text references `tests/test_code/` (NOT `tests/sdet/`)
  as the discovery scope.
result: pass

### 4. Legacy flag `--sdet` still works, warns once, coerces to `test_code=True`
expected: |
  `uv run mcp-test-framework run --sdet --help` still works (hidden shim)
  and emits exactly one `DeprecationWarning` naming v1.5 removal in the
  same D-05 wording. Subsequent invocations in the same process do not
  re-fire.
result: pass
note: |
  GAP-01 RESOLVED. Original implementation had the warning inside the
  `run` callback body; Typer/Click short-circuits on `--help` before the
  body runs, so the warning never fired. Fix applied in this UAT session:
  moved the warning into an eager Typer callback (`_warn_sdet_flag`)
  registered with `callback=` + `is_eager=True` on the `--sdet` Option
  (cli.py:_warn_sdet_flag + sdet_legacy Option). The eager callback
  fires during option parsing, BEFORE --help short-circuits.
  Re-verified: `uv run python -W always -c "import sys; sys.argv=
  ['mcp-test-framework','run','--sdet','--help']; from
  mcp_test_framework.cli import app; app()"` emits the D-05 warning at
  typer/main.py:1836 with em-dash, then renders help.
secondary_concern: |
  Operator observation: the DeprecationWarning renders as plain
  uncolored text and is easily lost inside the large `--help` text
  block. Worth a visibility pass — possibly a colored prefix or moving
  the warning to a separate display channel. NOT a Phase 25 gap;
  candidate for a v1.4 close polish task or absorbed into Phase 30.

### 5. New `test_code:` config key loads; legacy `sdet:` warns; both keys → error
expected: |
  Three sub-cases against a `config.yaml`:
  (a) `test_code:` at the top level — loads cleanly, no warning.
  (b) `sdet:` at the top level — still loads (AliasChoices), but emits
      one `DeprecationWarning` per process naming v1.5 removal.
  (c) Both `test_code:` AND `sdet:` in the same file — raises a
      `pydantic.ValidationError` with an operator-tone message rejecting
      the ambiguity (no silent precedence).
result: pass
note: |
  Verified via `Config.model_validate(yaml.safe_load(...))` direct path.
  (a) OK-A, no warning. (b) OK-B plus literal DeprecationWarning
  `"config.yaml key 'sdet:' is deprecated since v1.4 and will be removed
  in v1.5 -- use 'test_code:' instead."` (c) ValidationError with
  message `"config.yaml contains both 'sdet' and 'test_code' keys --
  remove the legacy 'sdet' key (deprecated since v1.4, removed in v1.5)
  and keep only 'test_code'."` UAT-design note: test wording was
  ambiguous about (c) — operator initially read the traceback as a
  failure rather than the success condition. Future rename UATs should
  phrase "expected" as "raises ValidationError with text X" rather than
  the generic "raises an error".

### 6. New package import works; legacy import still works with warning
expected: |
  `python -c "from mcp_test_framework.test_code import tool, mcp_session, ToolCallError, ToolResponse"`
  succeeds silently.
  `python -c "from mcp_test_framework.sdet import tool, mcp_session, ToolCallError, ToolResponse"`
  also succeeds but emits exactly one `DeprecationWarning` per process
  naming v1.5 removal (per D-05 wording).
result: pass
note: |
  Legacy import emitted exactly one warning with D-05 text:
  `"mcp_test_framework.sdet is deprecated since v1.4 and will be removed
  in v1.5 — use mcp_test_framework.test_code instead."` (em-dash present).
  Side observation: both imports also surface 2 unrelated
  `DeprecationWarning` lines from pytest-asyncio's plugin.py:15
  (`asyncio.AbstractEventLoopPolicy` slated for removal in Python 3.16).
  Upstream pytest-asyncio forward-compat — NOT phase 25. Worth a
  separate hygiene note: importing `mcp_test_framework.*` shouldn't
  transitively load pytest-asyncio when called from non-test code paths.

### 7. Operator-authored tests discovered from `tests/test_code/` by default; legacy path still works with session-once warning
expected: |
  The framework's argv builder targets `tests/test_code/` as the operator
  scope (visible in `_runner.py` or via a `--collect-only` smoke run).
  When ANY test is collected from `tests/sdet/`, exactly one
  session-scoped `DeprecationWarning` fires pointing operators at the new
  path.
result: pass
note: |
  (a) `tests/test_code/` exists with `__init__.py`, `conftest.py`,
  `test_proxmox_vm_lifecycle_readme_sample.py` (3 files plus
  __pycache__). (b) `_build_pytest_args(None, None, sdet=True)` returns
  `['tests/test_code']`. Function kwarg remains `sdet=` per D-16/D-18
  internal-name exclusion (`_`-prefixed names are out of scope); the
  surface-facing path that operators perceive (CLI flag, discovery dir)
  IS renamed. Session-once DeprecationWarning on legacy `tests/sdet/`
  collection NOT exercised in this UAT (legacy dir is empty in the
  current tree); behavior covered by plan 25-04 SUMMARY's unit assertion
  but worth a smoke test if a legacy SDET test reappears.

### 8. Docs: `docs/TEST-CODE-AUTHORING.md` is canonical; old path is a redirect stub
expected: |
  `docs/TEST-CODE-AUTHORING.md` exists with the full authoring guide
  (git log shows blame preserved via `git mv`).
  `docs/SDET-AUTHORING.md` is a short stub (≤ a few lines) that points
  to the new file.
result: pass

### 9. CI leak gate green at the close gate
expected: |
  `uv run python -m pytest tests/framework/test_sdet_rename_leak_gate.py -v`
  returns 4 passed / 0 failed. (Already verified once by the orchestrator;
  this UAT row confirms the operator can re-run it themselves.)
result: pass

### 10. Framework self-test suite stays green
expected: |
  `uv run python -m pytest tests/framework/ -q` returns ~584 passed /
  1 skipped / 17 deselected / 2 xfailed, 0 failures. (Plan-05 baseline
  through plan-06 close.) Any new failures should be reported.
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0

## Gaps

- truth: "Invoking `mcp-test-framework run --sdet --help` emits exactly one DeprecationWarning (D-05 wording, naming v1.5 removal)"
  status: resolved
  resolved_in_session: true
  fix: |
    cli.py — added _warn_sdet_flag() helper as an eager Typer/Click
    callback; attached to the `--sdet` Option via
    `callback=_warn_sdet_flag, is_eager=True`; removed the now-redundant
    `warnings.warn(...)` block from the `run` body. Eager callbacks fire
    during option parsing, BEFORE --help short-circuits, so operators
    using `--sdet` (with or without --help) see the deprecation warning.
  severity: major
  test: 4

## Secondary Observations

- observation: |
    DeprecationWarning renders as plain uncolored text and is easily
    lost in `--help` text blocks (operator UX feedback during UAT).
    Possible fix: colored prefix on `warnings.formatwarning` override,
    or render warnings to a separate channel that bypasses help's
    text-wall framing.
  scope: out-of-scope for Phase 25
  candidate: v1.4 close polish task or Phase 30 absorption
  source: operator UAT 2026-05-16 (test 4 re-verification)
