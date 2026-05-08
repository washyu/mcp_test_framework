# Phase 10: v1.1 documentation - Pattern Map

**Mapped:** 2026-05-08
**Files analyzed:** 2 modified (README.md, docs/EXTENDING.md)
**Analogs found:** 4 / 4 (all in-file analogs from existing sections)

This is a documentation-only phase. The "analogs" are existing sections within
the same files being edited — the planner must inherit their structural shape,
density, and cross-link conventions verbatim. No source code changes.

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `README.md` (insert: Per-tool configuration) | docs (schema reference) | static-reference | `README.md` § Configuration (lines 66-84) | exact (in-file) |
| `README.md` (insert: Isolation guarantee) | docs (claim + verification recipe) | static-reference | `README.md` § Sample green run (lines 86-126) + § Troubleshooting (127-140) | role-match (in-file) |
| `README.md` (insert: CI integration) | docs (copy-pasteable starter snippet) | static-reference | `README.md` § Commands (lines 30-64) | role-match (in-file) |
| `docs/EXTENDING.md` (insert: Add a new MCP tool target) | docs (step-by-step walkthrough) | static-reference | `docs/EXTENDING.md` § Add a new description-quality rubric (lines 14-57) | exact (in-file) |

All four target sections have strong in-file analogs. The planner should
**copy the structural shape verbatim** and only swap the content.

## Pattern Assignments

### `README.md` § Per-tool configuration (DOC-04, doc-schema-reference)

**Analog:** `README.md` § Configuration (lines 66-84)

**Heading hierarchy** (line 66):
```markdown
## Configuration
```
- Top-level section uses `##`. The new "Per-tool configuration" section MUST also use `##`
  for the section header so the GitHub-rendered anchor (`#per-tool-configuration`) matches
  the EXTENDING.md cross-link planned in D-04a.
- No `###` subsections in the Configuration analog. Per-tool configuration MAY use `###`
  for "Block A: skip-with-reason" / "Block B: judges subset" if the planner judges that
  two `###` subsections aid scanning (D-02). Keep ≤ 2 levels deep.

**Density / opening line pattern** (line 68):
```markdown
Precedence: **CLI flag > env var > `.env` > YAML overlay > default**.
```
- Single-sentence orienting statement, then immediately into structure. No multi-paragraph
  preamble. New section's opening line should mirror this — e.g., a single sentence anchoring
  WHERE per-tool config lives in the precedence chain or in the schema.

**Reference-table pattern** (lines 70-80):
```markdown
| Env Var | Default | Purpose |
|---------|---------|---------|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server base URL. |
| ...
```
- The Configuration section uses a markdown table for the env-var reference. The Per-tool
  configuration section's TOOLCFG field reference (`skip`, `skip_reason`, `call_arguments`,
  `judges`, plus reserved `setup` / `depends_on`) SHOULD follow this same table shape:
  three columns (Field | Default | Purpose) with backtick-fenced field names and one-line
  Purpose entries.

**Closing-prose / cross-link pattern** (lines 82-84):
```markdown
Copy `.env.example` to `.env` and edit. The same vars can be set in your shell,
in a YAML overlay pointed at by `MCPTF_CONFIG_FILE` (or `--config`), or in
PowerShell with `$env:VAR = "..."` before invoking the CLI.
```
- After the table, 2-3 lines of plain prose pointing at the on-disk artifact (here `.env.example`).
  New section's closing prose MUST point at `config.example.yaml` per D-01a:
  *"For a complete real-server config, see [`config.example.yaml`](config.example.yaml)."*
- Also include the D-01b reader-substitution callout immediately before the worked YAML
  blocks (one line, in plain prose).

**Code-fence language tag for YAML examples** (Block A / Block B per D-02):
- Use ` ```yaml ` for the per-tool config blocks (CD-04). Match the project's existing YAML
  conventions in `config.example.yaml` (2-space indent, `key: value` colon-space, scalar
  strings in double quotes when they contain commas/colons).

---

### `README.md` § Isolation guarantee (DOC-05, doc-claim-with-verification)

**Analog A (claim + concrete next-step):** `README.md` § Sample green run (lines 86-126)

The "Sample green run" section pattern is: short orienting prose → concrete artifact
(here a captured pytest output block) → multi-paragraph commentary explaining what the
artifact proves and what to do if your run differs. The Isolation guarantee section
inherits this **claim → verification recipe → caveat** rhythm.

**Opening claim pattern** (analog: line 87 caption "Sample green run" sets context, then
line 109's "Captured verbatim from a real local run..." commits to a concrete claim):
- New section opens with a one-sentence strong claim narrowed to what is actually verified
  (per D-05b): *"Test runs do not mutate `~/.homelab_mcp/` real-state files."* No
  hedging adverbs ("largely", "should"); no claim broader than what ISOL-03 verifies.

**Verification-recipe pattern** (analog: lines 88-107 give a concrete copy-pasteable
sample output that the reader can compare against; the Isolation section's analog is
a copy-pasteable bash invocation):
````markdown
```bash
uv run pytest tests/test_isolation.py -v
```
````
- Use ` ```bash ` for the invocation (matches Setup line 19, Commands line 34). One-line
  invocation, no arguments beyond what's load-bearing.

**Caveat / scope-narrowing prose pattern** (analog: lines 118-125 walk through "if your
run looks different, here's what's happening and how to interpret it"):
- After the verification recipe, 2-4 lines of prose calling out:
  - The exact files ISOL-03 sha256s: `~/.homelab_mcp/credential_registry.json`,
    `known_hosts`, `migration_state.json` (D-05a — concrete despite D-01 abstraction
    elsewhere; this is the documented exception).
  - The keyring null-backend dependency: *"Test runs route the OS keyring through a null
    backend, so credentials are not read or written."* (D-05b one-line note.)

**Analog B (cross-link to source artifact):** `README.md` § Troubleshooting (lines 127-140)
references `src/mcp_test_framework/fixtures.py` and `src/mcp_test_framework/cli.py` inline
as backtick-fenced relative paths. The Isolation guarantee section's reference to
`tests/test_isolation.py` follows the same shape: backtick-fenced relative path inline
in prose, NOT a Markdown link (consistent with how cli.py / fixtures.py are referenced
in Troubleshooting).

---

### `README.md` § CI integration (DOC-06, doc-copy-pasteable-snippet)

**Analog:** `README.md` § Commands → "Run the test suite" subsection (lines 32-45)

**Subsection-with-snippet pattern** (lines 32-45):
````markdown
### Run the test suite

```bash
uv run mcp-test-framework run
uv run mcp-test-framework run --config ./config.yaml
uv run mcp-test-framework run -- -x --lf -k schema
```

`run` invokes pytest against the `tests/` directory and exits with pytest's exit
code (0 on green). Anything after the `--` separator is forwarded verbatim to
`pytest.main()` -- use it to pass `-k`, `-x`, `--lf`, or any other pytest flag.
````
- Pattern: heading → fenced code block (3-4 lines) → 3-5 line paragraph explaining
  the snippet. New CI section follows this rhythm but the code block is ~25 lines
  (a GHA workflow file) rather than 3-4. The post-snippet prose stays short.

**Code-fence language tag for GHA snippet** (per CD-04):
- Use ` ```yaml ` for the GitHub Actions workflow YAML (D-03 target ~25 lines).

**Comment-led "translate to other CI" pattern** (D-03c):
- The single GHA snippet ships with a leading YAML comment (e.g., `# GitHub Actions; on
  Jenkins/GitLab translate the job/runs-on/uses keys.`). This is content-pattern, not
  structural-pattern, but mirror it from how `.env.example` and `config.example.yaml`
  use `# ...` comment blocks at the top to orient the reader before the data.

**Action-pinning pattern** (D-03d):
- Major-version tags only: `astral-sh/setup-uv@v6`, `dorny/test-reporter@v2`, `actions/checkout@v5`.
  No SHAs. (No in-file analog — this is an inherited convention from D-03d.)

**Live-test reminder comment** (D-03b):
- One inline YAML comment in the snippet noting that the default `addopts` excludes
  `live_homelab` / `live_ollama` markers. Reference `pyproject.toml` `[tool.pytest.ini_options]`.

**Post-snippet prose** (analog density: lines 40-45 are 6 lines):
- Keep ≤ 6 lines of prose after the snippet. Cross-link the JUnit-XML-flag mention to
  the existing Commands section if helpful, or describe what `dorny/test-reporter@v2`
  surfaces in the GitHub PR Checks UI.

---

### `docs/EXTENDING.md` § Add a new MCP tool target (DOC-07, doc-walkthrough)

**Analog:** `docs/EXTENDING.md` § Add a new description-quality rubric (lines 14-57)

This is the closest possible analog — same file, same kind of "walk a contributor
through adding a new X" section. The new section MUST inherit the analog's full shape.

**Heading hierarchy** (line 14):
```markdown
## Add a new description-quality rubric
```
- `##` for the major seam. The new section uses `## Add a new MCP tool target`. Place
  it between the rubric section and the judge section, OR after the judge section
  (D-04b — Claude's discretion). Recommended placement: **after** the judge section
  so the file reads "ways to extend the framework's code → ways to extend coverage
  via config alone" (config-only is the lighter-weight extension and comes naturally
  at the end before "Further reading").

**Opening-prose pattern** (lines 16-23):
```markdown
The `Rubric` base class (`src/mcp_test_framework/rubrics.py`) is a frozen
Pydantic model with two fields: `dimension` (a short label) and
`dimension_criteria` (the question the judge answers). The framework's three
built-in rubrics (`ClarityRubric`, `DisambiguationRubric`, `ParametersRubric`)
are session-scoped fixtures; add yours the same way.
```
- 2-4 lines of orienting prose: WHAT the seam is, WHERE it lives in the source tree
  (backtick-fenced relative path), AND a one-sentence hook into how the existing
  examples relate. New section's opening should:
  - Name the seam: per-tool config (`tools.<tool_name>:` block in config.yaml).
  - Cite the schema source: `src/mcp_test_framework/config.py` `ToolConfig` (or
    wherever the model lives — read the actual import path before drafting).
  - Cross-link forward to README's Per-tool configuration schema section (D-04a):
    `[Per-tool configuration](../README.md#per-tool-configuration)`.

**"Where to drop the recipe" callout pattern** (line 24):
```markdown
**Where to drop the recipe:** `tests/conftest.py` (or any pytest
plugin / conftest in your test tree).
```
- One-line bolded callout naming the on-disk file the contributor edits. The new
  section's analog: **Where to drop the recipe:** `config.yaml` (or the YAML pointed at
  by `MCPTF_CONFIG_FILE` / `--config`). NO code edits required.

**Numbered-step walkthrough** (per D-04 explicit list):
The Rubric analog jumps straight to a code block, not a numbered list. The new section
DEPARTS from the analog here per D-04: it uses an explicit 4-step walkthrough:
  1. `mcp-test-framework list-tools` to discover.
  2. Pick a tool; decide skip / judges / call_arguments.
  3. Add `tools.<tool_name>:` block (link back to README schema).
  4. Re-run `mcp-test-framework run`; verify the per-tool summary line.

Use a markdown ordered list (`1. ...` `2. ...`). Each step is 1-2 lines. After the
list, present the worked YAML example.

**Code-fence + worked-example pattern** (lines 25-52):
```python
import pytest
from mcp_test_framework.rubrics import Rubric


class SafetyRubric(Rubric):
    ...
```
- The Rubric analog uses ` ```python ` and shows a complete copy-pasteable example
  (~28 lines including the test function). The new section uses ` ```yaml ` and shows
  ONE complete `tools.<tool_name>:` block — D-04c picks the skip-with-reason pattern
  (closest to "I have a destructive tool I want to opt out"). Reference the README
  for the judges-subset pattern: *"See README's Block B for judges-subset usage."*
- Worked example uses abstract placeholder names per D-01: `<your_destructive_tool>` or
  similar angle-bracketed snake_case (D-01b reader-substitution callout precedes the block).

**Closing-prose pattern** (lines 54-57):
```markdown
The framework's `_HARDENING_PREAMBLE` and `_SCORE_ANCHOR_TEMPLATE` (defined in
`rubrics.py`) wrap your `dimension_criteria` automatically via
`Rubric.__str__`, so the judge sees a uniform prompt shape across all
rubrics. Pass threshold is `score >= 4` on the 1-5 scale.
```
- 3-5 lines of "what happens at runtime" prose anchoring the example to the framework's
  internals. New section's analog: explain what happens when the per-tool block is in
  place — *"At collection time, `_iter_tools_for_target_param` reads the registry and
  applies skip/judges/call_arguments per parametrized test ID."* Reference the actual
  collection-time function name from the codebase before drafting.

---

## Shared Patterns

### Cross-link convention (relative paths, backtick-fenced)
**Source:** `README.md` line 144-146 ("Further reading"); `docs/EXTENDING.md` line 119
**Apply to:** All cross-links in new sections

```markdown
- [`docs/mcp_test_framework_mvp_spec.md`](docs/mcp_test_framework_mvp_spec.md) -- authoritative design spec
- [`docs/EXTENDING.md`](docs/EXTENDING.md) -- add a new rubric, swap the judge backend
- [`.planning/PROJECT.md`](.planning/PROJECT.md) -- project mission, constraints, key decisions
```

- **Form:** `` [`relative/path/to/file.md`](relative/path/to/file.md) -- one-line description ``
- The link text is backtick-fenced and identical to the URL target.
- Description follows ` -- ` (two ASCII hyphens, then space). NOT em-dash, NOT en-dash.
- README cross-links to `docs/...` use `docs/` prefix (no leading `./`).
- EXTENDING.md cross-links to README use `../README.md` (one `..` for `docs/` → repo root).
- Anchor links into README from EXTENDING.md (per D-04a):
  `[Per-tool configuration](../README.md#per-tool-configuration)` — GitHub auto-generates
  the anchor from the `## Per-tool configuration` heading (lowercase, spaces→hyphens).

### Inline source-path reference (NOT a Markdown link)
**Source:** `README.md` lines 132-134; `docs/EXTENDING.md` lines 17, 28
**Apply to:** Inline source-tree references in prose

```markdown
... see `src/mcp_test_framework/fixtures.py` and
`src/mcp_test_framework/cli.py`).
```

- Backtick-fenced relative path inline in prose (NOT a Markdown link).
- Used when the path is being NAMED, not navigated to.
- DOC-05's reference to `tests/test_isolation.py` follows this pattern (it's a path the
  reader runs as a pytest argument, not a clickable doc-tree link).

### Code-fence language tag conventions
**Source:** Existing `bash` (README L19, L34, L50, L63), `text` (README L88), `yaml`
(EXTENDING / README implied), `python` (EXTENDING L25, L73)
**Apply to:** All new code blocks (CD-04)

| Block content | Tag |
|---------------|-----|
| Shell invocations | ` ```bash ` |
| YAML config (per-tool config block, GHA workflow) | ` ```yaml ` |
| Captured pytest / CLI output | ` ```text ` |
| Python source (test recipes) | ` ```python ` |

### Density / section-length budget
**Source:** Existing README sections range 4-40 lines; EXTENDING.md sections 40-60 lines
**Apply to:** All new sections

- README "Per-tool configuration": target 35-50 lines (table + 2 YAML blocks + ~6 lines prose).
- README "Isolation guarantee": target 12-18 lines (1-line claim + bash recipe + 4-6 line caveat).
- README "CI integration": target 30-40 lines (~25-line GHA snippet + 5-6 line prose).
- EXTENDING.md "Add a new MCP tool target": target 40-55 lines (4-step list + 1 YAML block + closing prose).
- Combined new content target: ~150 lines (per CONTEXT.md `<specifics>` line 134).

### "No emoji, no marketing voice"
**Source:** Whole-file convention; explicitly noted in CONTEXT.md `<code_context>` line 123
**Apply to:** All prose in new sections

- Engineering-document tone. No "blazing fast", no "amazing", no exclamation points.
- Prefer concrete claims (sha256 hash comparison) over qualitative ones (largely hermetic).
- Sentence-fragment captions are OK when they precede a code block.

### "Further reading" update pattern (CD-03)
**Source:** `README.md` lines 142-146; `docs/EXTENDING.md` lines 117-122
**Apply to:** Both files' Further reading sections

Each file's existing "Further reading" is a `##`-headed section with a flat unordered
list. New cross-links append to the list following the existing form:

README's Further reading should add:
- A link to EXTENDING.md's new tool-target walkthrough (anchor: `#add-a-new-mcp-tool-target`).
- (Optional) a link to `config.example.yaml`.

EXTENDING.md's Further reading should add:
- A link to README's Per-tool configuration anchor: `[Per-tool configuration](../README.md#per-tool-configuration)`.

Do NOT remove existing entries.

## No Analog Found

| Section | Reason | Source-of-truth fallback |
|---------|--------|--------------------------|
| GitHub Actions workflow YAML body | No GHA workflow exists in this repo (no `.github/workflows/` directory). | RESEARCH.md / Phase 09 CD-01 (`dorny/test-reporter@v2`); `astral-sh/setup-uv@v6` per Astral docs; the workflow shape is a fresh authoring task per D-03. |
| Major-version-pinned action references | No prior action references exist in this repo's docs. | D-03d explicit decision (`@v6`, `@v2` — not SHAs). |

For these, the planner should defer to RESEARCH.md (if produced) and to the inline
decisions in CONTEXT.md `<decisions>` D-03..D-03d. There is no in-repo prior art to copy.

## Metadata

**Analog search scope:** `README.md`, `docs/EXTENDING.md`, `config.example.yaml`,
`.planning/phases/10-v1-1-documentation/10-CONTEXT.md`. No `.github/workflows/`
directory exists in the repo (verified — no GHA workflow analog).

**Files scanned:** 4

**Pattern extraction date:** 2026-05-08
