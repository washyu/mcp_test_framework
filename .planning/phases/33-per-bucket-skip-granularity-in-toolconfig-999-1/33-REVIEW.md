---
phase: 33-per-bucket-skip-granularity-in-toolconfig-999-1
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - README.md
  - docs/ERROR-STYLE.md
  - docs/LIBRARY-MODE.md
  - src/mcp_test_framework/_plugin.py
  - src/mcp_test_framework/_runner.py
  - src/mcp_test_framework/contracts/_buckets.py
  - src/mcp_test_framework/models.py
  - tests/framework/test_bucket_map.py
  - tests/framework/test_explain_buckets.py
  - tests/framework/test_plugin_bucket_filter.py
  - tests/framework/test_pre_run_digest_buckets.py
  - tests/framework/test_tool_config.py
findings:
  critical: 1
  warning: 6
  info: 4
  total: 11
status: issues_found
---

# Phase 33: Code Review Report

**Reviewed:** 2026-05-26
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 33 adds `skip_buckets: list[BucketName]` to `ToolConfig`, a
collection-time per-bucket filter in `_plugin.pytest_generate_tests`,
a `[NOTSET]` cleanup pass in `pytest_collection_modifyitems`, and a
pair of digest/--explain UI extensions in `_runner.py`. The Pydantic
field, the mutual-exclusion with `skip=True`, and the parametrize-time
filter behave as documented and are well-covered by the new tests.

The headline defect is a digest/runtime drift: the pre-run
`Test plan: N contract cases` count is computed from the running tool
count times the locked 10-cases-per-tool constant, and is NOT decremented
by `skip_buckets`. A tool that opts out of one or more buckets still
contributes a full 10 cases to the plan, so the digest overstates what
pytest will collect for the exact example the README and LIBRARY-MODE.md
document. This is a BLOCKER because both worked-examples reproduce it
verbatim. Secondary issues: list semantics on `skip_buckets` allow silent
duplicates that propagate through the bucket-skip count and the explain
renderer; the explain renderer mixes indentation between Section 1 and
Section 2; the `Judges:` digest line does not reflect a fully
judge-bucket-suppressed run; the wrapper-side bucket counting ignores
discovery so undiscovered, bucket-configured tools inflate the
`Bucket skips:` count without warning.

## Critical Issues

### CR-01: Pre-run "Test plan" count ignores `skip_buckets`, overstates collected cases for the README worked-example

**File:** `src/mcp_test_framework/_runner.py:1184`
**Issue:**
`_render_pre_run_digest` computes the plan as
`planned_cases = running_n * CASES_PER_CONTRACT_TOOL` (line 1184)
where `CASES_PER_CONTRACT_TOOL = 10`. A tool is counted as "running"
iff it is in `tools_config` and `skip` is not True — `skip_buckets`
is not consulted. But the actual parametrize-time filter in
`_plugin.pytest_generate_tests:484-490` drops the (tool, bucket-test)
pair from collection. The plan number is therefore overstated by
`len(skip_buckets) * n_tests_in_that_bucket` per tool.

Concretely for the README's worked example
(`README.md:402-425`, mirrored at `docs/LIBRARY-MODE.md:194-217`):

- `create_proxmox_vm` with `skip_buckets: ["output"]`
- Bucket map (`contracts/_buckets.py:29-33`) puts 3 functions in
  the `output` bucket.
- Digest says `Test plan: 10 contract cases` (1 * 10).
- Actual collected cases = 10 - 3 = 7.

A tool that opts out of every bucket
(`tests/framework/test_plugin_bucket_filter.py::test_every_tool_opts_out_of_every_bucket_emits_zero_items`
covers this) still appears in the `Running:` list and contributes 10
to the plan, while pytest collects 0 items. The digest then
contradicts itself when the `Result:` line lands at `0 PASS / 0 FAIL`.

This violates the documented contract that the pre-run digest is the
operator's authoritative "what will run" preview — same surface the
README screenshots and the LIBRARY-MODE.md docs treat as canonical.

**Fix:**
Either subtract bucket-skipped cases from the plan, or compute it
from the bucket map directly:

```python
# In _render_pre_run_digest, replace:
planned_cases = running_n * CASES_PER_CONTRACT_TOOL

# with something like (sketch — derive bucket-size map once):
from mcp_test_framework.contracts._buckets import TEST_FUNCTION_BUCKETS
_BUCKET_SIZE = {b: len(fns) for b, fns in TEST_FUNCTION_BUCKETS.items()}
planned_cases = 0
for t in running:
    skipped = set(getattr(ctx.tools_config[t], "skip_buckets", []) or [])
    planned_cases += sum(
        sz for b, sz in _BUCKET_SIZE.items() if b not in skipped
    )
```

And add a regression test that asserts the digest plan number agrees
with `len(items)` after a real `pytest --collect-only`, with at least
one `skip_buckets` entry present.

## Warnings

### WR-01: `skip_buckets` allows silent duplicates; inflates count and emits duplicate explain rows

**File:** `src/mcp_test_framework/models.py:103-115`
**Issue:**
`skip_buckets: list[BucketName]` is a list, not a set, and there is no
validator that rejects duplicates. `ToolConfig(skip_buckets=["output", "output"])`
constructs successfully (Pydantic just validates each element is a valid
literal). Downstream:

- `_count_bucket_skips` in `_runner.py:1019` counts via `len(...)`, so the
  digest will show `Bucket skips: 2` for a single tool that "skips output
  twice".
- `_render_skipped_tools_explain` in `_runner.py:1376-1384` iterates the
  list and emits one `bucket=output: skipped via ...` line per occurrence
  — two identical rows in the same block.

Operators are unlikely to type duplicates intentionally; the absence of a
validator turns a typo into a quietly-wrong count.

**Fix:**
Add a `field_validator("skip_buckets", mode="after")` (or normalize in
the after validator already on the model) that either deduplicates or
raises:

```python
@field_validator("skip_buckets", mode="after")
@classmethod
def _no_duplicate_buckets(cls, v: list[BucketName]) -> list[BucketName]:
    if len(set(v)) != len(v):
        # operator-tone, mirrors docs/ERROR-STYLE.md
        raise ValueError(
            "skip_buckets contains duplicate bucket name(s); each "
            "bucket may appear at most once. valid values: "
            "'schema', 'judge', 'output'."
        )
    return v
```

### WR-02: `_count_bucket_skips` and `Section 2` of `--explain` ignore `ctx.discovered_tools`; configured-but-undiscovered tools inflate the count

**File:** `src/mcp_test_framework/_runner.py:1019-1029, 1370-1385`
**Issue:**
Both `_count_bucket_skips` (used by `_render_pre_run_digest`) and the
"Bucket-skipped tools" Section 2 of `_render_skipped_tools_explain`
iterate `ctx.tools_config.items()` without filtering against
`ctx.discovered_tools`. A tool that the operator configured with
`skip_buckets` but that the MCP server does not advertise will still
contribute to `Bucket skips: N` and still appear in the explain block.

This is inconsistent with the rest of the digest: `Skipping:` is
computed as `discovered_n - running_n` (line 1181), so undiscovered
tools are simply absent from both `Running` and `Skipping`. They
appear only on the bucket-skip surface. The framework also already
issues an "unknown tool" warning for unlisted tools elsewhere; the
inconsistency here masks that signal.

**Fix:**
Restrict both functions to discovered tools:

```python
def _count_bucket_skips(tools_config: dict, discovered: list[str]) -> int:
    total = 0
    for name in discovered:
        tcfg = tools_config.get(name)
        if tcfg is None:
            continue
        total += len(getattr(tcfg, "skip_buckets", []) or [])
    return total
```

And in `_render_skipped_tools_explain` Section 2, filter
`bucket_skipped` by `name in ctx.discovered_tools` before rendering.

### WR-03: Indentation mismatch between Section 1 and Section 2 of `_render_skipped_tools_explain`

**File:** `src/mcp_test_framework/_runner.py:1358-1362` vs `1378-1384`
**Issue:**
Section 1 (whole-tool skips with defensive bucket fallback) emits each
bucket line with 2 leading spaces:

```
  bucket={bucket}: skipped via tools.{tool}.skip_buckets
```

Section 2 (state-b tools with skip_buckets) emits each bucket line under
a 2-space tool header with 4 leading spaces:

```
  {tool}:
    bucket={bucket}: skipped via tools.{tool}.skip_buckets
```

A defensive emit in Section 1 (only reachable if a future caller bypasses
`_skip_buckets_not_with_whole_tool_skip`) also lacks a tool-header line,
so the bucket rows are visually loose compared to Section 2's nested
shape. The two sections become inconsistent the moment the defensive
path fires.

Lower-priority: the comment block at `_runner.py:1310-1316` claims the
section-1 bucket lines "hang under their tool's whole-tool line", which
is true in source order but visually misleading because the tool line is
em-dashed and the bucket line is at the same indent — they look like
peer rows.

**Fix:**
Align Section 1's defensive bucket emit with Section 2's shape:

```python
if tcfg is not None and tcfg.skip_buckets:
    for bucket in tcfg.skip_buckets:
        print(
            f"    bucket={bucket}: skipped via tools.{tool}.skip_buckets",
            file=file,
        )
```

(4-space lead instead of 2, matching Section 2.) Optionally suppress the
defensive emit entirely now that the model validator rejects the
combination — dead-code today, drift risk tomorrow.

### WR-04: `Judges:` digest line does not reflect judge-bucket-suppressed runs

**File:** `src/mcp_test_framework/_runner.py:1032-1056, 1210`
**Issue:**
`_compose_judges_from_tool_configs` builds the digest's `Judges:` union
purely from `ToolConfig.judges` semantics (None → all rubrics, [] → no
rubrics). It does not consider `skip_buckets`. If every running tool has
`skip_buckets: ["judge"]`, the digest still shows
`Judges: clarity, disambiguation, parameters` even though zero judge
tests will execute.

Operator surface impact: `Judges:` is one of the few "what's actually
going to fire" lines in the digest. With a judge-bucket-suppressed
config, the line lies about activity, which is exactly the failure
mode `_compose_judges_from_tool_configs` was already rewritten to fix
(comment block at `_runner.py:1041-1045` describes the prior None→[]
silent-collapse bug).

**Fix:**
Suppress a tool's judges contribution when `"judge" in
tool_cfg.skip_buckets`:

```python
for tool_cfg in tools_config.values():
    if "judge" in (getattr(tool_cfg, "skip_buckets", []) or []):
        continue
    declared = getattr(tool_cfg, "judges", None)
    if declared is None:
        judges_set.update(RUBRIC_IDS)
    else:
        judges_set.update(declared)
```

And add a regression test (`tests/framework/unit/test_runner_pre_run_digest.py`
is the existing host) that pins the behavior.

### WR-05: `Bucket skips:` digest line column alignment drifts from `Skipping:` by one character

**File:** `src/mcp_test_framework/_runner.py:1191-1209`
**Issue:**
Layout inconsistency on the digest:

- `Skipping:    {n:>2}  ...` — label is 13 chars wide (9 + 4 spaces),
  number field is 2 chars, total 15 chars before the hint.
- `Bucket skips:{n:>3}  ...` — label is 13 chars wide (13 + 0 spaces),
  number field is 3 chars, total 16 chars.

The two number columns are misaligned by one character. The README
canonical example reproduces the misalignment verbatim
(`README.md:421-424`), so the docs document the bug rather than the
intended layout. With N >= 100 bucket skips the drift increases.

Not a correctness issue; a polish bug that will surface in operator
screenshots / regression-baseline updates.

**Fix:**
Either widen the `Bucket skips:` field to match (`f"Bucket skips:{n:>2}"`
with a leading-space adjustment), or right-align both around a fixed
"column-15" anchor:

```python
print(f"Skipping:    {skipping_n:>3}  (use --explain to list)", file=file)
print(f"Bucket skips:{bucket_skip_n:>3}  (use --explain to list)", file=file)
```

(Widen `Skipping:` to `:>3` to match, so both number columns end at the
same position.) Update the README and LIBRARY-MODE.md canonical
examples in lockstep.

### WR-06: `_skip_buckets_not_with_whole_tool_skip` runs after `_skip_requires_reason`; operator sees the wrong error when both rules are violated

**File:** `src/mcp_test_framework/models.py:136-173`
**Issue:**
Two `model_validator(mode="after")` validators are declared in this order:

1. `_skip_requires_reason` — raises when `skip=True` and reason is blank.
2. `_skip_buckets_not_with_whole_tool_skip` — raises when `skip=True` and
   `skip_buckets` is non-empty.

`ToolConfig(skip=True, skip_buckets=["output"])` (no `skip_reason`)
violates both. The operator gets the "skip_reason required" message, then
fixes that, runs again, and only then sees the "mutually exclusive"
message. Two round-trips on the same config edit.

The validator order is incidental (source declaration order). The more
informative error in this case is the mutual-exclusion one — once the
operator drops `skip_buckets`, the skip-with-reason rule is the obvious
next step.

**Fix:**
Either combine both checks into one validator that emits a single
operator-tone error covering both conditions, or reorder so the
mutual-exclusion check runs first. Add a parametrized regression test
to lock the chosen order.

## Info

### IN-01: README example output line for `Skipping (0):` may surprise operators when zero whole-tool skips exist

**File:** `src/mcp_test_framework/_runner.py:1364-1368`, `README.md:412`
**Issue:**
When no tool is whole-tool-skipped but at least one has `skip_buckets`,
`_render_skipped_tools_explain` emits a literal `Skipping (0):` header
followed by a blank line, then the `Bucket-skipped tools (1):` block.
The README shows this verbatim. Some operators may read `Skipping (0):`
as redundant noise when the more interesting content follows. Consider
omitting the empty Section 1 entirely when Section 2 has content.

**Fix:**
Skip Section 1 when `not skipped` AND Section 2 is non-empty, or always
condense to a single combined header. Cosmetic.

### IN-02: `pytest_generate_tests` silently no-ops when test function isn't in `TEST_FUNCTION_BUCKETS`

**File:** `src/mcp_test_framework/_plugin.py:478-490`
**Issue:**
If a contract test function is added to `contracts/_tests.py` without
being added to `TEST_FUNCTION_BUCKETS`, `owning_bucket` is `None` and
the per-bucket filter is silently bypassed (the function still runs
against every opted-in tool). The "every test must be in exactly one
bucket" rule is enforced only by
`tests/framework/test_bucket_map.py::test_every_contract_test_function_belongs_to_exactly_one_bucket`.
That test catches the gap, but inside `pytest_generate_tests` itself
there is no defensive assert. A developer hand-running a single
contract test (and not the bucket-map test) gets no signal.

**Fix:**
Optional: assert `owning_bucket is not None` after the loop when the
sentinel is set, with an operator-tone error pointing at the bucket
map source file. Or document the behavior in a code comment.

### IN-03: `_render_pre_run_digest` docstring claims "<= 12 lines with `with_framework=True` and bucket skips active"

**File:** `src/mcp_test_framework/_runner.py:1138-1156`
**Issue:**
Counting from the source: banner (3) + server + discovered + running +
skipping + bucket-skips + judges + test-plan + framework-continuation
+ trailing blank = 11 lines, not 12. Docstring overstates by one.

**Fix:**
Update the docstring counts to match the actual emit, or add an
explicit "header banner = 3 lines" note.

### IN-04: `Bucket skips:` label-spacing comment claims "no new digest noise when feature is unused"

**File:** `src/mcp_test_framework/_runner.py:1198-1201`
**Issue:**
The mitigation comment (`T-33-12 mitigation: no new digest noise when
feature is unused`) is internal-spec jargon (`T-33-12`) that won't
survive a future plan/spec retirement. Per `docs/ERROR-STYLE.md:84-89`
banned-strings list, internal IDs of the form `[A-Z]{2,}-\d{2}` are
prohibited in operator-facing surfaces. This is a code comment, not an
operator error string, so it doesn't violate the style guide directly,
but the project pattern is to avoid spec-ID leakage in source comments
that may become stale.

**Fix:**
Replace `T-33-12` with a brief inline description (`omit when no tool
sets skip_buckets`) or drop the reference entirely.

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
