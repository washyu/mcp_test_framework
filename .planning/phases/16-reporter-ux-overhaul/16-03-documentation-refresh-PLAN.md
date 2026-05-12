---
phase: 16-reporter-ux-overhaul
plan: 03
type: execute
wave: 3
depends_on:
  - 16-02
files_modified:
  - README.md
  - docs/mcp_test_framework_mvp_spec.md
autonomous: true
requirements:
  - UX-01
  - UX-02
  - UX-05
must_haves:
  truths:
    - "README.md's 'Run the test suite' section describes the pre-run digest (server / discovered / running / skipping / judges / test-plan) emitted BEFORE pytest runs."
    - "README.md documents `--explain` with one operator-readable paragraph describing the Skipping (N) expansion and its no-op composition with --raw and -q."
    - "README.md's -q description matches Phase 16 D-09 (suppresses digest + per-tool rows; emits only the Result: line)."
    - "docs/mcp_test_framework_mvp_spec.md no longer pins the post-run header as the FIRST surface of the domain UI (if it does today); any reference to 'header' as part of the post-run output is updated to reflect the pre-run digest reorganization."
  artifacts:
    - path: "README.md"
      provides: "Operator-facing documentation for the pre-run digest + --explain + -q"
      contains: "--explain"
      contains_also: ["pre-run digest", "Skipping"]
    - path: "docs/mcp_test_framework_mvp_spec.md"
      provides: "Authoritative design doc reflecting Phase 16's pre-run-vs-post-run split"
  key_links:
    - from: "README.md 'Run the test suite' section"
      to: "Phase 16 D-01 (digest before pytest) + D-09 (-q parity)"
      via: "prose update + example output block"
      pattern: "(pre-run digest|MCP Test Framework|--explain)"
---

<objective>
Refresh operator-facing documentation to match Phase 16's pre-run digest + `--explain` + `-q` semantics.

Scope is **prose + example-output updates only**. No code changes. Documentation lag is a real operator footgun for v1.2's "Operator-First Design" milestone — the README is the first surface a new operator reads, and Phase 16 changes what `mcp-test-framework run` looks like end-to-end.

Two files to touch:
- `README.md` — primary operator entry point; "Run the test suite" section (and any other section that shows command output) must reflect the pre-run digest and `--explain`.
- `docs/mcp_test_framework_mvp_spec.md` — design spec; verify it doesn't pin the post-run header ordering in a way that contradicts D-01.

Out of scope: REQUIREMENTS.md UX-01 wording amendment (the `Defaulting:` divergence per D-04) — CONTEXT.md §deferred line 204 explicitly defers that to a quick-task post-Phase-16. Not addressed here.

REVISION (checker WARNING 5): D-11 (`--debug` per-judge breakdown block) is deferred to v1.3 per CONTEXT.md Claude's Discretion — the XML-extraction pathway is not exercised in this phase. Documented here so the v1.2 close-out audit doesn't re-surface it as a gap.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md
@.planning/phases/16-reporter-ux-overhaul/16-01-pre-run-digest-renderer-PLAN.md
@.planning/phases/16-reporter-ux-overhaul/16-02-explain-flag-and-cli-wiring-PLAN.md
@README.md
@docs/mcp_test_framework_mvp_spec.md

<interfaces>
<!-- Documentation truth source — the locked digest shape from Plan 01. -->

Locked output shape (D-01, D-12, D-04):
```
========================================
MCP Test Framework
========================================
MCP server:  <command + args>
Discovered:  <N> tools
Running:      <R>  (<sorted comma-joined names>)
Skipping:     <S>  (use --explain to list)
Judges:      <sorted comma-joined>
Test plan:   <R * 10> contract cases
```

Locked `--explain` expansion block (D-05, D-06, D-13):
```
Skipping (N):
  <tool_a>  — <reason>
  <tool_b>  — <reason>
  ...
```

Locked `-q` output (D-09 / UX-05):
```
Result: <summary line only>
```

Locked composition rules (D-08):
- `--explain --raw`: no-op (--raw bypasses the wrapper-side renderer entirely).
- `--explain -q`: no-op (quiet wins; only Result: emits).
- `--explain --with-framework`: digest gains `+ framework self-tests` line below `Test plan:`; Skipping block lists tool-side skips only.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Update README.md "Run the test suite" section with the pre-run digest + --explain + -q</name>
  <files>README.md</files>
  <read_first>
    - README.md (whole file — small enough to read at once; identify every section that shows `mcp-test-framework run` output OR documents the `-q` / `--raw` / `--debug` / `--with-framework` flag matrix)
    - .planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md §decisions D-01, D-05, D-08, D-09, D-12, D-13
  </read_first>
  <behavior>
    - README's "Run the test suite" (or equivalent) section shows the pre-run digest as the first surface an operator sees.
    - The `--explain` flag is documented as one paragraph + a small example output block showing `Skipping (N):` + sorted lines + em-dash separator.
    - The `-q` description (wherever it appears) states: "suppresses the pre-run digest and per-tool rows; emits only the final `Result:` line" — matching D-09.
    - If the README contains a "command flag matrix" or similar table, `--explain` is added there with the composition rules from D-08.
    - The README does NOT show a "post-run header" — if any current example output snippet ends with the banner / labels appearing AFTER pytest output, that snippet must be updated to show banner pre-run + per-tool rows + summary post-run.
  </behavior>
  <action>
**Step 1: Read README.md fully** and identify every section that:
(a) shows example output of `mcp-test-framework run`,
(b) documents the `-q` / `--quiet` flag,
(c) documents the `--raw` / `--debug` / `--with-framework` flags (these likely sit near where `--explain` belongs in the docs),
(d) describes the framework's output shape in prose ("post-run summary", "header", "domain UI", etc.).

**Step 2: For each example output block** showing `mcp-test-framework run` output, replace with a current-shape example. The canonical small-N example (matching the Phase 16 D-01 + D-04 contract) is:

```
========================================
MCP Test Framework
========================================
MCP server:  uvx homelab-mcp
Discovered:  58 tools
Running:      2  (list_registered_servers, query_inventory)
Skipping:    56  (use --explain to list)
Judges:      clarity
Test plan:   20 contract cases

failures:
  list_registered_servers  ✗ FAIL — clarity score 2/5: response is too terse to understand
skipped:
  query_inventory          – SKIP — explicit skip in config
passing:
  (none)

Result: 0 passed, 1 failed, 56 skipped
```

**Step 3: Add a `--explain` documentation paragraph** next to the existing flag documentation (the same section that currently documents `-q` / `--raw` / `--debug` / `--with-framework`). Use exactly this prose (operator-readable, factual, no marketing tone):

> **`--explain`** — Expands the pre-run digest's `Skipping (N) (use --explain to list)` hint into one line per skipped tool with its reason (state-(a) `"not selected in config"` or state-(c) `"explicit skip in config"`, or the operator's `skip_reason:` text if provided). Output is sorted alphabetically, one tool per line, grep-friendly even at homelab-mcp's full ~70-tool surface. Renders inline between the digest and the pytest subprocess. Ignored under `--raw` (no domain UI) and under `-q` / `--quiet` (summary-only output).

Add an example output block immediately after (the `--explain` expansion for the canonical example above):

```
$ mcp-test-framework run --explain
========================================
MCP Test Framework
========================================
MCP server:  uvx homelab-mcp
Discovered:  58 tools
Running:      2  (list_registered_servers, query_inventory)
Skipping:    56  (use --explain to list)
Judges:      clarity
Test plan:   20 contract cases

Skipping (56):
  bulk_update_inventory       — explicit skip in config
  delete_server               — side effects on homelab inventory
  ... (50 more, alphabetical) ...
  zone_reset                  — not selected in config

(pytest output follows)
```

**Step 4: Update the `-q` documentation** wherever it lives. Replace any existing prose with (or add if absent):

> **`-q` / `--quiet`** — Suppresses the pre-run digest, the `--explain` expansion (if also passed), and the per-tool rows. Emits only the final `Result: N passed, M failed, S skipped` line. Mirrors v1.1's quiet-mode parity for CI consumers that want a single-line summary.

**Step 5: If README has a flag-composition matrix or table**, add a row for `--explain` documenting:
- `--explain` alone: expands Skipping into a sorted per-tool list inline.
- `--explain --raw`: no-op (--raw bypasses wrapper output).
- `--explain -q`: no-op (quiet wins).
- `--explain --with-framework`: works; framework self-tests run additionally, digest shows `+ framework self-tests` suffix.

**Step 6: Search-and-update terminology.** If the README uses the phrase "post-run header" or "header at the top of the output", replace with "pre-run digest" (the surface moved per Phase 16 D-01). Use `grep -n -i "header" README.md` to find candidates; treat each in context — some "header" references may be about Markdown / HTTP / non-framework usage and should NOT change.

**Step 7: Preserve everything else.** Do NOT rewrite README sections unrelated to the runner output. Do NOT change the project description, install instructions, dependency notes, or any contributor-facing sections. Preserve Markdown heading levels exactly.
  </action>
  <verify>
    <automated>uv run python -c "import re; src = open('README.md', encoding='utf-8').read(); assert '--explain' in src, '--explain missing from README'; assert 'pre-run digest' in src.lower() or 'MCP Test Framework' in src, 'digest example block missing'; assert 'use --explain to list' in src, 'digest skipping-hint missing'; assert re.search(r'(?i)-q.*(suppress|quiet|summary)', src), '-q docs incomplete'; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c -- "--explain" README.md` is ≥ 2 (at least the flag heading + one example usage).
    - `grep -c "use --explain to list" README.md` is ≥ 1 (the hint string from the digest appears in at least one example block).
    - `grep -c "MCP Test Framework" README.md` is ≥ 1 (the canonical digest example).
    - `grep -i -c "post-run header" README.md` returns 0 (terminology updated).
    - `grep -i -c "Result:" README.md` is ≥ 1 (summary line shown in at least one example).
    - The `-q` documentation paragraph mentions "digest" or "pre-run" AND "summary line" (verified by `<automated>` regex).
    - README still includes its existing install instructions and project description (manual visual confirmation — do not delete unrelated sections).
  </acceptance_criteria>
  <done>README.md accurately documents Phase 16's pre-run digest, `--explain` flag (with composition rules), and `-q` parity. No post-run-header references remain.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Audit and update docs/mcp_test_framework_mvp_spec.md for Phase 16 alignment</name>
  <files>docs/mcp_test_framework_mvp_spec.md</files>
  <read_first>
    - docs/mcp_test_framework_mvp_spec.md (full file — read once; this is the authoritative design doc per CLAUDE.md project instructions)
    - .planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md §decisions D-01, D-04, D-05, D-09
  </read_first>
  <behavior>
    - Spec does NOT contradict Phase 16 D-01 (digest is pre-run, post-run is rows+summary).
    - Spec mentions `--explain` if it documents the operator-facing CLI flag matrix.
    - Spec's "Test Cases" / "Module Layout" sections (which Phase 15 already updated) remain accurate.
    - Spec does NOT contain stale references to "post-run header" or "pytest's N collected, M deselected" framing (the latter is what Phase 16 replaces).
  </behavior>
  <action>
**Step 1: Read `docs/mcp_test_framework_mvp_spec.md`** fully. Identify sections that:
(a) describe the CLI output shape ("Output", "Reporter", "Domain UI", "Header", etc.),
(b) document the operator-facing flag matrix (`-q`, `--raw`, `--debug`, `--with-framework`),
(c) reference pytest's collection framing (Phase 16 explicitly replaces "N collected, M deselected").

**Step 2: If the spec describes the output shape**, ensure the description matches:
- Pre-run: 8-line digest (banner + 5 label rows + Test plan + blank).
- Post-run: per-tool rows (FAIL → SKIP → PASS, alphabetized within each) + summary line.
- `--explain`: inline `Skipping (N):` block between digest and pytest output.
- `-q`: only the `Result:` line.

If the spec currently describes the output as "post-run banner + header + rows + summary" (the Phase 14 shape), update to the Phase 16 shape.

**Step 3: If the spec documents the operator CLI flag matrix**, add `--explain` to the list with the same prose used in README:

> `--explain` — Expands the pre-run digest's `Skipping (N)` hint into one alphabetically-sorted line per skipped tool with its reason. Wrapper-owned (not forwarded to pytest). Ignored under `--raw` and `-q`.

**Step 4: Search-and-update.** Use grep on the spec file for:
- `grep -i -n "n collected" docs/mcp_test_framework_mvp_spec.md` — if pytest's misleading collection framing is mentioned as the operator surface, replace with the pre-run digest framing.
- `grep -i -n "header" docs/mcp_test_framework_mvp_spec.md` — check each match's context; update "post-run header" to "pre-run digest" only where the meaning matches.
- `grep -i -n "explain" docs/mcp_test_framework_mvp_spec.md` — confirm any pre-existing mention is consistent with D-05/D-08/D-09.

**Step 5: If the spec is silent on the output shape**, no changes needed for that section — but DO confirm by reading the relevant sections fully before declaring "no change required." Do NOT skip the read.

**Step 6: Preserve scope discipline.** Spec sections covering Phase 1–15 design decisions (MCP transport, Ollama judge, schema validation, config precedence, isolation, opt-in selection, etc.) are OUT OF SCOPE for this task. Touch ONLY paragraphs that describe the CLI output shape, the `--explain` flag, or the obsolete pytest collection framing.

**Step 7: If after thorough reading no Phase-16-relevant content exists in the spec** (i.e., the spec describes the design contract but not the output shape, OR Phase 15 already abstracted the output description out), record this finding in the SUMMARY and make ZERO changes to the file. A passing verification with zero diff is acceptable. Do NOT manufacture changes to satisfy the task — the spec's purpose is design truth, not CLI output documentation.
  </action>
  <verify>
    <automated>uv run python -c "src = open('docs/mcp_test_framework_mvp_spec.md', encoding='utf-8').read(); lower = src.lower(); has_pytest_collection_mention = 'n collected' in lower or 'collected' in lower and 'deselected' in lower; has_explain = '--explain' in src; print(f'pytest-collection-as-operator-framing-present: {has_pytest_collection_mention}'); print(f'--explain-documented: {has_explain}'); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - File `docs/mcp_test_framework_mvp_spec.md` still exists and is non-empty.
    - `grep -i -c "n collected, m deselected" docs/mcp_test_framework_mvp_spec.md` returns 0 (the obsolete pytest framing is not held up as the operator surface).
    - If the spec documents the CLI flag matrix at all (`-q`, `--raw`, `--debug`, `--with-framework`), then `--explain` is present alongside them.
    - If the spec is silent on the CLI output shape (which is possible — the spec may abstract over reporter details), zero diff is acceptable. The SUMMARY records this explicitly.
    - The spec's existing sections on Python 3.14, uv, MCP stdio transport, Ollama judge, judge rubric, opt-in tool selection, contract/framework split, etc. are PRESERVED unchanged.
    - `git diff docs/mcp_test_framework_mvp_spec.md` (run after the task) touches only Phase-16-relevant paragraphs (operator CLI output / `--explain` / pre-run vs post-run shape).
  </acceptance_criteria>
  <done>Either the spec accurately reflects Phase 16's pre-run/post-run split and documents `--explain`, OR the spec is intentionally silent on those surfaces and the SUMMARY records that finding. No drift between spec and Phase 16's locked decisions.</done>
</task>

</tasks>

<threat_model>
**STRIDE applicability: NONE.** This plan is documentation prose updates only. No code changes, no new inputs, no new persisted state, no new network or filesystem operations beyond the file edits themselves (which are operator-controlled developer-machine writes).

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| (none) | n/a | n/a | n/a | Documentation-only plan. No security-relevant surface change. |
</threat_model>

<verification>
1. `grep -c -- "--explain" README.md` is ≥ 2.
2. `grep -i -c "post-run header" README.md` is 0.
3. `grep -c "use --explain to list" README.md` is ≥ 1.
4. `grep -i -c "n collected, m deselected" docs/mcp_test_framework_mvp_spec.md` is 0.
5. Existing test surface unaffected: `uv run pytest tests/framework/ -x -q` exits 0 (no code changes, no test impact).
6. Manual visual review of README "Run the test suite" section confirms the pre-run digest example block reads cleanly to a new operator.
</verification>

<success_criteria>
- README.md documents the pre-run digest (with a canonical example output block matching the Phase 16 D-01 shape).
- README.md documents `--explain` as a wrapper-owned flag with its composition rules under `--raw` / `-q` / `--with-framework`.
- README.md's `-q` description matches D-09 (suppresses digest + per-tool rows; emits only `Result:` line).
- README.md no longer references a "post-run header"; if a flag-composition matrix exists, `--explain` is added to it.
- `docs/mcp_test_framework_mvp_spec.md` is internally consistent with Phase 16 (either updated to reflect the pre-run digest reorganization, or intentionally silent on the output shape — SUMMARY records which).
- Sections of the spec unrelated to Phase 16 (Python version, uv, MCP stdio, Ollama judge, opt-in selection, contract/framework split) are PRESERVED.
- All existing tests still pass (no code changes in this plan).
</success_criteria>

<output>
After completion, create `.planning/phases/16-reporter-ux-overhaul/16-03-SUMMARY.md` per the GSD summary template. Include:
- The README sections touched (heading paths) and a short diff summary (line count added/removed).
- Whether `docs/mcp_test_framework_mvp_spec.md` was updated or intentionally left unchanged — and if unchanged, the specific reading-based justification (which sections were read, why none required Phase-16-aligned edits).
- A note that REQUIREMENTS.md UX-01's "Defaulting:" wording divergence per D-04 is intentionally NOT addressed in this plan (deferred per CONTEXT.md §deferred line 204).
- REVISION (WARNING 5): record that D-11 (`--debug` per-judge breakdown block) is deferred to v1.3. The XML-extraction pathway is not exercised in this phase; explicitly capturing the deferral in the Phase 16 close-out SUMMARY prevents the v1.2 audit from re-surfacing it as a gap.
</output>
