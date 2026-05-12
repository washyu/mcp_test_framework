---
phase: 16-reporter-ux-overhaul
plan: 04
type: execute
wave: 1
depends_on: []
files_modified:
  - README.md
autonomous: true
gap_closure: true
requirements:
  - UX-01
  - UX-05
commit_message: "docs(16-04): correct README runner-output format drift"

must_haves:
  truths:
    - "README.md's documented `Result:` line at lines 84, 92, and 228 matches `_render_summary_line` actual output shape `Result: N PASS / M FAIL [/ S SKIP]  in T.Ts` (uppercase verbs, slash-separated, double space before `in`, includes timing)"
    - "README.md per-tool row examples at lines 81-82 and 225-226 include a `passing:` section header preceding the rows and the rows are indented by 2 spaces, matching `_render_per_tool_rows` actual output at `_runner.py:843-870`"
    - "README.md contains zero occurrences of the old comma-separated lowercase `Result: N passed, M failed, S skipped` shape after the fix"
  artifacts:
    - path: "README.md"
      provides: "Operator-facing documentation of pre-run digest, per-tool row block, and `Result:` summary line"
      contains: "Result: 20 PASS / 0 FAIL / 560 SKIP  in"
      contains_section_header: "passing:"
  key_links:
    - from: "README.md sample output blocks"
      to: "src/mcp_test_framework/_runner.py:_render_summary_line + _render_per_tool_rows"
      via: "literal string mirror — docs quote what the renderer emits, char-for-char"
      pattern: "Result: \\d+ PASS / \\d+ FAIL"
---

<objective>
Close the two documentation-drift gaps that VERIFICATION.md flagged against
Phase 16: README.md's three sample output blocks document a `Result:` summary
line shape and a per-tool row shape that do NOT match what `_runner.py`
actually emits. The code is correct; only the docs are wrong. This plan
rewrites the three affected README sections to mirror the renderer verbatim.

Purpose: Restore the operator contract. CI consumers grepping the documented
`Result:` strings (e.g., `passed,` / `failed,` / `skipped`) currently get zero
matches against actual output. The `-q` flag row at README:92 quotes a format
operators are explicitly told to parse for single-line CI summaries — it must
match reality.

Output: A single commit on README.md replacing six concrete locations with
the renderer's actual output strings, plus adjusted prose nearby (line 241
references "560 skipped" — the `Result:` line's `skipped` field segment — and
must be reworded to reference the new `SKIP` shape).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md
@.planning/phases/16-reporter-ux-overhaul/16-VERIFICATION.md
@.planning/phases/16-reporter-ux-overhaul/16-REVIEW.md
@.planning/phases/16-reporter-ux-overhaul/16-03-documentation-refresh-SUMMARY.md

<interfaces>
<!-- The two renderer functions whose output the README must mirror. -->
<!-- Source of truth: src/mcp_test_framework/_runner.py -->
<!-- Pinned by test: tests/framework/test_runner_renderer.py:223 -->

From src/mcp_test_framework/_runner.py:843-870 (`_render_per_tool_rows`):
```
failures:
  <tool_name_ljust>  ✗ FAIL — <failure_message>
skipped:
  <tool_name_ljust>  – SKIP — <reasons>
passing:
  <tool_name_ljust>  ✓ PASS
```
Notes:
- Section headers (`failures:`, `skipped:`, `passing:`) are flush-left with
  trailing colon, emitted ONLY when that bucket is non-empty.
- Rows are indented exactly 2 spaces.
- Tool names are left-justified to the max-name width across all buckets.
- PASS marker glyph is U+2713 (`✓`); FAIL is U+2717 (`✗`); SKIP is U+2013 en-dash (`–`).
- Reasoning/message separator is U+2014 em-dash (`—`), not ASCII hyphen.

From src/mcp_test_framework/_runner.py:898 (`_render_summary_line`):
```
Result: {n_pass} PASS / {n_fail} FAIL[ / {n_skip} SKIP]  in {total_time:.1f}s
```
Notes:
- A BLANK LINE is printed before the `Result:` line (line 896 of _runner.py:
  `print("", file=file)`).
- `PASS`, `FAIL`, `SKIP` are UPPERCASE verbs separated by ` / ` (space-slash-space).
- The ` / N SKIP` segment is OMITTED ENTIRELY when `n_skip == 0` (see test
  `test_summary_line_omits_skip_when_zero` at `test_runner_renderer.py:228`).
- After the last verdict segment there are TWO SPACES before `in` (literal
  source: `f"...FAIL{skip_segment}  in {parsed.total_time:.1f}s"`).
- Time is single-decimal seconds via `:.1f` formatting (e.g., `4.3s`, `8.3s`).
</interfaces>

@README.md
@src/mcp_test_framework/_runner.py
@tests/framework/test_runner_renderer.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix Result: summary line in three README locations</name>

  <read_first>
    - README.md (entire file — patches land at lines 84, 92, 228; line 241 is adjacent prose that references the `skipped` field name)
    - src/mcp_test_framework/_runner.py lines 878-900 (the literal `f"Result: ..."` print statement at line 898)
    - tests/framework/test_runner_renderer.py lines 218-232 (`test_summary_line_includes_skip_count_when_skips_present` pins `"Result: 2 PASS / 1 FAIL / 1 SKIP"`; `test_summary_line_omits_skip_when_zero` pins the no-SKIP-segment behavior)
  </read_first>

  <files>README.md</files>

  <action>
    Apply three replacements to README.md, verbatim. The replacement strings
    are derived from `_render_summary_line` at `_runner.py:898`
    (`f"Result: {n_pass} PASS / {n_fail} FAIL{skip_segment}  in {parsed.total_time:.1f}s"`).
    Note the DOUBLE SPACE before `in` — this is not a typo; it is what the
    renderer emits and what `test_runner_renderer.py:224` (`"in 8.3s"` after
    `"Result: 2 PASS / 1 FAIL / 1 SKIP"`) implicitly pins.

    **Replacement 1 — README.md line 84 (default sample output block):**
    Current line 84 reads exactly:
    `Result: 20 passed, 0 failed, 560 skipped`
    Replace with:
    `Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s`

    **Replacement 2 — README.md line 92 (`-q` / `--quiet` table row prose):**
    Current line 92 reads exactly:
    `` | `-q` / `--quiet` | Suppresses the pre-run digest, the `--explain` expansion (if also passed), and the per-tool rows. Emits only the final `Result: N passed, M failed, S skipped` line. Mirrors v1.1's quiet-mode parity for CI consumers that want a single-line summary. | ``
    Replace the inline-code segment `` `Result: N passed, M failed, S skipped` `` with:
    `` `Result: N PASS / M FAIL [/ S SKIP]  in T.Ts` ``
    Final line 92 text after replacement:
    `` | `-q` / `--quiet` | Suppresses the pre-run digest, the `--explain` expansion (if also passed), and the per-tool rows. Emits only the final `Result: N PASS / M FAIL [/ S SKIP]  in T.Ts` line (the `SKIP` segment is omitted entirely when zero skips; double space before `in` is literal). Mirrors v1.1's quiet-mode parity for CI consumers that want a single-line summary. | ``

    **Replacement 3 — README.md line 228 (`Sample green run` block):**
    Current line 228 reads exactly:
    `Result: 20 passed, 0 failed, 560 skipped`
    Replace with:
    `Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s`

    **Adjacent prose fix — README.md line 240-242 (Sample green run prose
    that references the field name `skipped`):**
    Current text reads (line 239-242):
    `Skipped tools (` `Skipping: 56` ` in the example) are absent from the per-tool`
    `row block under the default surface -- their counts roll into the ` `Result:` ` line's ` `skipped` ` field at the parametrized-case level (56 tools × 10 cases =`
    `560 skipped cases). Pass ` `--explain` ...
    Replace the `` `skipped` `` field-name reference and `560 skipped cases`
    phrase to align with the new shape. Concretely, change:
    `their counts roll into the ` `Result:` ` line's ` `skipped` ` field at the parametrized-case level (56 tools × 10 cases = 560 skipped cases)`
    to:
    `their counts roll into the ` `Result:` ` line's ` `SKIP` ` segment at the parametrized-case level (56 tools × 10 cases = 560 SKIP cases)`

    **DO NOT** add a `SKIP` segment to the line-92 example if it would imply
    SKIP is always present — note the bracketed `[/ S SKIP]` shows it is
    conditional. **DO NOT** rewrite any other lines, table rows, or
    code-block samples. Scope is exactly these three blocks + the adjacent
    prose sentence.

    Rationale (per CR-01 BLOCKER root cause in `16-VERIFICATION.md` §Gaps
    Summary): Plan 16-03 invented the documented `Result:` shape rather than
    reading `_render_summary_line`. This task closes the operator-contract
    gap (UX-05) by mirroring renderer output literally.
  </action>

  <verify>
    <automated>
      # Must contain the three corrected Result: lines (two in code blocks + one in table prose):
      grep -c 'Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s' README.md
      # Expected: 2  (line 84 sample block + line 228 sample block)

      grep -c 'Result: N PASS / M FAIL \[/ S SKIP\]  in T.Ts' README.md
      # Expected: 1  (line 92 table row)

      # Must NOT contain any of the old comma-separated lowercase forms anywhere:
      grep -c 'Result: .* passed, .* failed' README.md
      # Expected: 0

      grep -c '0 failed, 560 skipped' README.md
      # Expected: 0

      grep -c 'N passed, M failed, S skipped' README.md
      # Expected: 0

      # Adjacent prose at line ~241 updated:
      grep -c '560 SKIP cases' README.md
      # Expected: 1
      grep -c '560 skipped cases' README.md
      # Expected: 0
    </automated>
  </verify>

  <done>
    - `grep -c 'Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s' README.md` returns `2`
    - `grep -c 'Result: N PASS / M FAIL \[/ S SKIP\]  in T.Ts' README.md` returns `1`
    - `grep -c 'Result: .* passed, .* failed' README.md` returns `0`
    - `grep -c '560 skipped cases' README.md` returns `0`
    - `grep -c '560 SKIP cases' README.md` returns `1`
    - No other lines in README.md are modified (diff is bounded to lines 84, 92, 228, and one prose sentence near line 241)
  </done>
</task>

<task type="auto">
  <name>Task 2: Add passing: section headers + 2-space indent to per-tool row examples</name>

  <read_first>
    - README.md lines 70-85 (default sample output block — lines 81-82 are flush-left per-tool rows)
    - README.md lines 213-229 (`Sample green run` block — lines 225-226 are the duplicated flush-left per-tool rows)
    - README.md lines 102-121 (`--explain` example block) — NOTE: this block currently ends with a placeholder `(pytest subprocess runs here, then per-tool rows + Result: line)` at line 120 and does NOT contain concrete per-tool rows. VERIFICATION.md claims lines 109-110 are per-tool rows; this is a verifier counting error — those lines are `Running:` / `Skipping:` digest rows, not per-tool rows. Do NOT fabricate per-tool rows in the `--explain` block.
    - src/mcp_test_framework/_runner.py lines 820-870 (`_render_per_tool_rows` — emits `passing:` / `failures:` / `skipped:` section header followed by 2-space-indented rows; only emits a section header when that bucket is non-empty)
  </read_first>

  <files>README.md</files>

  <action>
    The renderer (`_render_per_tool_rows` at `_runner.py:843-870`) emits a
    flush-left section header (`passing:`, `failures:`, or `skipped:`)
    followed by rows indented exactly 2 spaces. In the all-PASS samples
    used by README's default block and "Sample green run" block, only the
    `passing:` section is emitted (no failures, no skips render in the
    per-tool row block because all 560 skipped contract cases are
    state-(a)/(c) composer entries unioned in via `unparam_skips` — but in
    these README samples those are NOT shown in the row block; they roll
    into the `Result:` SKIP segment only).

    **Replacement 1 — README.md lines 81-82 (default sample output block):**
    Current text (lines 81-82) reads exactly:
    ```
    list_keyring_credentials  ✓ PASS
    suggest_deployments       ✓ PASS
    ```
    Replace with:
    ```
    passing:
      list_keyring_credentials  ✓ PASS
      suggest_deployments       ✓ PASS
    ```
    (Insert `passing:` flush-left on a new line BEFORE the two existing
    rows; indent each existing row by exactly 2 spaces. Preserve the
    existing inter-name spacing — the original rows already use the
    renderer's `ljust(name_width)` spacing for `list_keyring_credentials`
    vs the shorter `suggest_deployments`. After the 2-space indent the
    column alignment between the two rows must remain intact.)

    **Replacement 2 — README.md lines 225-226 (`Sample green run` block):**
    Current text (lines 225-226) reads exactly:
    ```
    list_keyring_credentials  ✓ PASS
    suggest_deployments       ✓ PASS
    ```
    Replace with:
    ```
    passing:
      list_keyring_credentials  ✓ PASS
      suggest_deployments       ✓ PASS
    ```
    (Same transformation as Replacement 1 — insert `passing:` header,
    indent rows by 2 spaces.)

    **No change to the `--explain` block (README lines 102-121):** Verify
    that the existing placeholder comment at README line 120 reads
    `(pytest subprocess runs here, then per-tool rows + Result: line)` and
    leave it as-is. If — and ONLY if — the placeholder is missing or has
    drifted, do NOT invent concrete per-tool rows; the `--explain`
    example's scope is the pre-pytest portion of the surface. Per
    VERIFICATION.md Gap 2 artifacts, the "lines 109-110" reference is a
    counting error in the verifier; the actual README at those lines
    holds `Running:` / `Skipping:` digest rows, which are correctly
    rendered.

    **Adjacent prose check — README.md line ~234:** Verify that the
    sentence at line 234-237 reads:
    `The two ` `✓ PASS` ` rows are the **post-run** per-tool view, one row per tool that actually ran, sorted FAIL → SKIP → PASS within each verdict bucket.`
    This prose is correct as-is and should NOT be modified — `_render_per_tool_rows`
    does emit FAIL → SKIP → PASS section order at `_runner.py:842, 853, 866`.

    Rationale (per IN-02 WARNING in `16-VERIFICATION.md` Anti-Patterns
    table): Plan 16-03 fabricated per-tool row samples without reading
    `_render_per_tool_rows`. Operators reading README and then running
    the framework will see `passing:` headers + 2-space indents that the
    README's flush-left samples don't acknowledge.
  </action>

  <verify>
    <automated>
      # passing: section header appears at least twice (once per fixed sample block):
      grep -c '^passing:$' README.md
      # Expected: >= 2

      # 2-space indented rows appear immediately under each passing: header.
      # Use -A1 to assert "passing:" is followed by a 2-space-indented row:
      grep -A1 '^passing:$' README.md | grep -c '^  list_keyring_credentials  ✓ PASS$'
      # Expected: 2  (both fixed sample blocks)

      grep -c '^  suggest_deployments       ✓ PASS$' README.md
      # Expected: 2

      # The OLD flush-left form must be entirely absent:
      grep -c '^list_keyring_credentials  ✓ PASS$' README.md
      # Expected: 0

      grep -c '^suggest_deployments       ✓ PASS$' README.md
      # Expected: 0

      # --explain placeholder unchanged:
      grep -c '(pytest subprocess runs here, then per-tool rows + Result: line)' README.md
      # Expected: 1
    </automated>
  </verify>

  <done>
    - `grep -c '^passing:$' README.md` returns >= 2
    - `grep -c '^  list_keyring_credentials  ✓ PASS$' README.md` returns 2
    - `grep -c '^  suggest_deployments       ✓ PASS$' README.md` returns 2
    - `grep -c '^list_keyring_credentials  ✓ PASS$' README.md` returns 0 (no flush-left forms remain)
    - `grep -c '^suggest_deployments       ✓ PASS$' README.md` returns 0
    - `grep -c '(pytest subprocess runs here, then per-tool rows + Result: line)' README.md` returns 1 (`--explain` placeholder untouched)
    - No other rendered surface in README (digest banner, table rows, `--explain` digest example) is modified
  </done>
</task>

</tasks>

<verification>
End-to-end grep gate on README.md (run from repo root):

```bash
# Gap 1 (CR-01 BLOCKER) — Result: line format drift closed:
grep -c 'Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s' README.md   # expect 2
grep -c 'Result: N PASS / M FAIL \[/ S SKIP\]  in T.Ts' README.md  # expect 1
grep -c 'Result: .* passed, .* failed' README.md                    # expect 0
grep -c 'N passed, M failed, S skipped' README.md                   # expect 0
grep -c '560 skipped cases' README.md                               # expect 0
grep -c '560 SKIP cases' README.md                                  # expect 1

# Gap 2 (IN-02 WARNING) — per-tool row section headers + indent in place:
grep -c '^passing:$' README.md                                      # expect >= 2
grep -c '^  list_keyring_credentials  ✓ PASS$' README.md            # expect 2
grep -c '^  suggest_deployments       ✓ PASS$' README.md            # expect 2
grep -c '^list_keyring_credentials  ✓ PASS$' README.md              # expect 0
grep -c '^suggest_deployments       ✓ PASS$' README.md              # expect 0

# --explain example block untouched:
grep -c '(pytest subprocess runs here, then per-tool rows + Result: line)' README.md  # expect 1
```

All gates passing closes both verification gaps. No code or test files
should appear in the diff — `git diff --stat` should show only README.md.
</verification>

<success_criteria>
- README.md's three `Result:` documented strings (lines 84, 92, 228) now
  match what `_render_summary_line` emits, char-for-char (including the
  double-space-before-`in` quirk and the conditional `SKIP` segment notation)
- README.md's two per-tool row sample blocks (lines 81-82 and 225-226) now
  show a `passing:` section header flush-left followed by 2-space-indented
  rows, matching `_render_per_tool_rows` output
- One adjacent prose sentence near line 241 is reworded to reference the new
  `SKIP` segment terminology instead of the old `skipped` field-name terminology
- Zero changes to source code, tests, or any other documentation files —
  `git diff --stat` shows README.md and nothing else
- Re-running `gsd-verifier` against this phase resolves both gaps; the
  16-VERIFICATION.md gap-truths revert to ✓ VERIFIED
</success_criteria>

<output>
After completion, create `.planning/phases/16-reporter-ux-overhaul/16-04-readme-format-corrections-SUMMARY.md`.

The summary should include:
- Confirmation that both gaps from 16-VERIFICATION.md are closed
- The verbatim before/after for each of the six edited locations (3 Result: lines + 2 per-tool blocks + 1 prose sentence)
- The grep-gate output proving the acceptance criteria
- A note that no source code or tests were touched — pure docs fix
</output>
