---
phase: 16-reporter-ux-overhaul
reviewed: 2026-05-11T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - README.md
  - src/mcp_test_framework/_runner.py
  - src/mcp_test_framework/cli.py
  - tests/framework/test_runner_renderer.py
  - tests/framework/test_runner_verbosity.py
  - tests/framework/unit/test_runner_explain.py
  - tests/framework/unit/test_runner_pre_run_digest.py
findings:
  critical: 1
  warning: 5
  info: 7
  total: 13
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-05-11
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 16 introduces the pre-run digest, `--explain` flag, and reshapes the run output. The implementation is well-tested and the renderer/composer split is clean. The main concern is **a documented-vs-actual output-format mismatch in README.md** that will mislead operators writing CI grep/parsers. Several quality issues around environment-variable mutation, code duplication between the digest and pre-run composer, and stale code comments are worth addressing.

## Critical Issues

### CR-01: BLOCKER — README documents wrong `Result:` summary line format

**File:** `README.md:84, 228`
**Issue:** Two prominent sample outputs claim the summary line shape is:

```
Result: 20 passed, 0 failed, 560 skipped
```

(lowercase verbs, comma-separated, no timing). But `src/mcp_test_framework/_runner.py:898` actually emits:

```
Result: {n_pass} PASS / {n_fail} FAIL / {n_skip} SKIP  in {time:.1f}s
```

(uppercase verbs, slash-separated, includes `in T.Ts` timing). Existing tests (`test_runner_renderer.py:223`) pin the actual format: `assert "Result: 2 PASS / 1 FAIL / 1 SKIP" in out`.

This will break:
- Any CI consumer that greps for `passed,` / `failed,` / `skipped` (e.g. shell pipelines following the README literally).
- Operators copy-pasting the documented examples into job scripts.
- The "single-line summary" CI contract promised in the `-q` flag table row.

The README also adds a third item — the README example shows the timing line absent, but the renderer always emits `  in {T}s`.
**Fix:** Update README.md to match the actual emitted format. Either:

```text
Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s
```

or change `_render_summary_line` to match the documented format (less desirable — the test suite pins the current format and `-q` parity to v1.1 was documented). Recommended: update README in both places (line 84 and line 228) and add a `Result:` shape paragraph next to the `-q` description so operators have a stable parse target.

## Warnings

### WR-01: WARNING — `_load_config` mutates `os.environ` as a side-effect

**File:** `src/mcp_test_framework/cli.py:269`
**Issue:** `os.environ["MCPTF_CONFIG_FILE"] = str(resolved)` rewrites the environment to propagate the resolved YAML path to the pytest subprocess. The comment explains the rationale, but:

1. The mutation persists across `CliRunner.invoke` calls in tests (Typer's `CliRunner` does not isolate `os.environ`), causing leakage between tests when run in the same process. The mock-driven tests in `test_runner_explain.py` and `test_runner_verbosity.py` may silently rely on or be affected by this — a re-invocation with a different `--config` will still see the old `MCPTF_CONFIG_FILE` if the second call doesn't reach this branch.
2. It conflates "load config" with "broadcast config path to subprocesses." `run_pytest_subprocess` already explicitly composes `child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}` — the propagation should live there.
3. From the memory note on "MCPTF_CONFIG_FILE silent fail": this env var has been a footgun precisely because mismatch between explicit and env-derived paths is silent. Adding a second writer increases that surface.

**Fix:** Return the resolved path from `_load_config` (or attach to the `Config` instance) and have `run_pytest_subprocess` set `MCPTF_CONFIG_FILE` in `child_env` explicitly:

```python
child_env = {
    **os.environ,
    "PYTHONIOENCODING": "utf-8",
    "MCPTF_CONFIG_FILE": str(yaml_path),
}
```

This keeps the parent's environment clean and makes the propagation visible in the subprocess-dispatch seam where it belongs.

### WR-02: WARNING — `_render_pre_run_digest` duplicates the running-set predicate used by `_compose_pre_run_skip_reasons`

**File:** `src/mcp_test_framework/_runner.py:742-746` and `_runner.py:621-625`
**Issue:** Both functions compute the "running" set with the same predicate (`name in tools_config and not getattr(tools_config[name], "skip", False)`):

- Digest (line 742): `running = sorted(t for t in ctx.discovered_tools if t in ctx.tools_config and not getattr(ctx.tools_config[t], "skip", False))`
- Composer (line 621): `running: set[str] = {name for name in discovered_tools if name in tools_config and not getattr(tools_config[name], "skip", False)}`

Two independent copies of the same logic invite silent drift. If the "state-(b) = running" rule ever changes (e.g., to also exclude tools with `judges: []`), one of these may be missed.

**Fix:** Extract a single helper:

```python
def _running_tool_set(discovered: list[str], tools_config: dict) -> set[str]:
    return {
        name for name in discovered
        if name in tools_config and not getattr(tools_config[name], "skip", False)
    }
```

Use it in both `_render_pre_run_digest` and `_compose_pre_run_skip_reasons`.

### WR-03: WARNING — Pre-run digest right-justification breaks at >99 tools

**File:** `src/mcp_test_framework/_runner.py:758, 762, 764`
**Issue:** The digest formats counts as `f"{running_n:>2}"` (2-character right-justification). At N >= 100 the count exceeds the reserved column width and the indent is wrong:

```
Running:      99  (...)   # aligned
Running:     100  (...)   # overflows
```

While 70 tools (homelab-mcp) is comfortably under the threshold, the framework is general-purpose and the README emphasizes "scales to the full ~70-tool surface" — operators may point it at larger MCP servers (the spec does not cap tool count).

**Fix:** Either compute the width dynamically from `discovered_n` (`width = max(2, len(str(discovered_n)))`) or use `>3`/`>4` proactively. The same applies to `Discovered:` which has no padding at all (line 757) — combining the three counts into a unified column width is cleanest.

### WR-04: WARNING — Pre-run digest's `Test plan` line overcounts when tools have non-default `judges` lists

**File:** `src/mcp_test_framework/_runner.py:751, 766`
**Issue:** `planned_cases = running_n * CASES_PER_CONTRACT_TOOL` (10 per tool) assumes every running tool exercises all 10 contract tests. But in `tests/contract/test_mcp_tool_contract.py:124-186`, the per-judge tests skip at runtime when the configured `judges` list omits their rubric — e.g., `judges: [clarity]` means `test_description_disambiguation` and `test_parameters_self_explanatory` always `pytest.skip()`. Those still count as "cases" in pytest's collected count, so `parsed.total_cases` reconciles, BUT the **post-run summary will show a SKIP count that the digest's "Test plan: N contract cases" does not predict**.

An operator reading `Test plan: 20 contract cases` followed by `Result: 12 PASS / 0 FAIL / 8 SKIP` will be confused — those 8 SKIPs include intra-test runtime skips, not just unlisted tools.

**Fix:** Either:
- Compute `planned_cases` more carefully (account for `judges` lists, e.g. `5 schema + len(judges or [3-judge-default]) + 1 output` per tool), OR
- Reword the line: `Test plan:   {planned_cases} contract cases (some may skip at runtime)`, OR
- Add a note in the README explaining that "Test plan" is the parametrize ceiling, not the executed count.

### WR-05: WARNING — Stale comment references deleted test path

**File:** `tests/framework/test_runner_renderer.py:9-16`
**Issue:** The docstring says "Test file lives at tests/test_runner_renderer.py per Plan 14-03 spec" and references a fallback `move the file to tests/unit/ post-hoc`. The file is now at `tests/framework/test_runner_renderer.py` (after the Phase 15 operator/framework split). The recovery command `uv run pytest tests/test_runner_renderer.py --no-header -p no:cacheprovider` will fail because that path no longer exists.

**Fix:** Update the docstring to reflect the current location (`tests/framework/test_runner_renderer.py`), and remove or update the fallback recovery command.

## Info

### IN-01: INFO — Unused `import pytest` in four test modules

**Files:**
- `tests/framework/test_runner_renderer.py:23`
- `tests/framework/test_runner_verbosity.py:13`
- `tests/framework/unit/test_runner_explain.py:15`
- `tests/framework/unit/test_runner_pre_run_digest.py:16`

**Issue:** `import pytest` is present but never referenced (no `pytest.skip`, `pytest.raises`, decorators, etc.). pytest is implicitly used by virtue of the file being collected, so the import is harmless but unused.

**Fix:** Remove the import in each file, or add a `# noqa: F401` if the project's lint config tolerates the unused import for convention reasons.

### IN-02: INFO — README sample FAIL row whitespace doesn't match renderer output

**File:** `README.md:251`
**Issue:** The README shows:

```
list_registered_servers  ✗ FAIL — clarity score 2/5: description is too terse...
```

But `_render_per_tool_rows` (line 849) emits `f"  {tool.ljust(name_width)}  ✗ {tag} — {v.failure_message}"` — there is a two-space indent before the tool name. The README example renders flush-left.

**Fix:** Indent the sample by two spaces:

```
  list_registered_servers  ✗ FAIL — clarity score 2/5: ...
```

This applies to the per-tool row samples at lines 81-82, 109-110, 225-226 as well — none of them show the two-space leading indent.

### IN-03: INFO — Inline imports in `cli.py:run` could move to module top

**File:** `src/mcp_test_framework/cli.py:474-475`
**Issue:** `from mcp_test_framework import _runner` and `import xml.etree.ElementTree as ET` are imported inside the `run` function body. There is no circular-import risk (cli.py already imports `_emit_operator_error` and `_build_pytest_args` from `_runner` at module load via the `noqa: E402` lines), and these are only inside the function for what looks like incidental reasons.

**Fix:** Consolidate the `_runner` import with the existing one at the top of the file. Move `import xml.etree.ElementTree as ET` to module-level.

### IN-04: INFO — `_render_skipped_tools_explain` emits redundant "Skipping (0):" when nothing to explain

**File:** `src/mcp_test_framework/_runner.py:799-804`
**Issue:** When `--explain` is passed but no tools are skipped, the function emits `Skipping (0):` followed by a blank. Since the pre-run digest already shows `Skipping:     0`, this duplicates info. The "explicit empty state" framing in the comment is reasonable but operators get two near-identical lines.

**Fix:** Either omit the block entirely on empty (the digest already conveys "0 skipped"), or emit a single line like `(no skipped tools to explain)` to differentiate from the digest.

### IN-05: INFO — `_render_pre_run_digest` and `_render_header` are near-duplicates

**File:** `src/mcp_test_framework/_runner.py:658-695` and `_runner.py:703-773`
**Issue:** `_render_header` (Phase 14) and `_render_pre_run_digest` (Phase 16) share ~80% of their output structure. With the digest now emitted pre-run, `_render_header` is no longer called by `render_domain_ui` (the test at line 273-275 of `test_runner_renderer.py` confirms the banner is gone from `render_domain_ui` output). Yet `_render_header` remains exported and is still tested at lines 56-94 of `test_runner_renderer.py`. If `_render_header` is no longer reachable from production code paths, it is dead code.

**Fix:** If `_render_header` is genuinely unused in production, delete it (and its tests). If it is retained intentionally for a future code path, add a comment explaining the contract and why both renderers must coexist.

### IN-06: INFO — `_render_pre_run_digest` comment claims "≤ 10 total in default mode" but content is 9 lines + 1 blank = 10

**File:** `src/mcp_test_framework/_runner.py:711, 729-730`
**Issue:** The docstring says "≤ 10 total in default mode; up to 11 with with_framework=True". The test `test_pre_run_digest_height_bounded_at_small_N` allows `<= 11` for the small-N case (banner 3 + 6 label lines + 1 trailing blank = 10, then `split("\n")` returns 11 chunks including the trailing empty). The numbers are consistent but the prose ("8 label-bearing lines" in the test comment at `test_runner_pre_run_digest.py:135`) doesn't match reality (5 label-bearing lines: MCP server, Discovered, Running, Skipping, Judges, Test plan = 6). Minor doc-vs-code drift.

**Fix:** Update the test comment at `test_runner_pre_run_digest.py:135-136` to say "3 banner + 6 label lines + 1 trailing blank = 10 actual lines, 11 split chunks".

### IN-07: INFO — `_render_pre_run_digest` `+ framework self-tests` continuation has no count

**File:** `src/mcp_test_framework/_runner.py:771-772`
**Issue:** Under `--with-framework`, the digest emits:

```
Test plan:   10 contract cases
             + framework self-tests
```

The operator gets a count for contract cases but not for framework cases. With `tests/framework/` already containing 100+ tests, the operator cannot estimate run length from the digest. This is consistent with the README description but the README itself notes "framework tests have no per-tool skip semantics" — it would be cheap to also emit "+ N framework self-tests" by collecting `tests/framework/` upfront or using a constant.

**Fix:** Either add a count (requires a pre-run pytest collection probe or a constant) or document that the framework-tests size is intentionally hidden from the digest.

---

_Reviewed: 2026-05-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
