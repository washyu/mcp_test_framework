---
phase: 10-v1-1-documentation
plan: 01
subsystem: docs
tags: [docs, readme, per-tool-config, isolation, ci, regression-test]
requires: []
provides:
  - "README anchor #per-tool-configuration (consumed by Plan 10-02 EXTENDING.md cross-link)"
  - "README anchor #isolation-guarantee"
  - "README anchor #ci-integration"
  - "tests/test_readme_snippets.py regression suite (CD-06 enforcement)"
affects:
  - README.md
tech-stack:
  added: []
  patterns:
    - "README insertion via Edit-tool with verbatim old_string anchors (no whole-file rewrites)"
    - "yaml.safe_load CI guard for fenced ```yaml blocks (CD-06)"
    - "ToolConfig schema-drift assertion via Pydantic model_fields introspection"
    - "Conditional pytest.xfail gate for forward-compat anchor links pending downstream plan"
key-files:
  created:
    - tests/test_readme_snippets.py
  modified:
    - README.md
decisions:
  - "Per-tool examples use abstract <safe_read_tool_a>/<safe_read_tool_b> placeholders preceded by the reader-substitution callout (D-01/D-01b); no fictional homelab tool names that drift if upstream renames"
  - "GitHub Actions snippet pinned at major-version tags (@v5/@v6/@v2), with explicit prose noting that SHA-pinning is out-of-scope for a starter (D-03d)"
  - "test_readme_anchor_targets_exist uses pytest.xfail (not skip) so Plan 10-02 flips it to passing automatically once the EXTENDING.md heading lands"
metrics:
  duration: "~4 minutes"
  tasks_completed: 4
  files_created: 1
  files_modified: 1
  completed: 2026-05-08
---

# Phase 10 Plan 01: v1.1 README documentation Summary

Three new top-level README sections (Per-tool configuration, Isolation guarantee, CI integration) plus a regression test that bakes README/model schema-drift detection and YAML snippet correctness into the default `pytest` run.

## Objective Recap

Insert v1.1's user-facing surface into README.md (per-tool config schema, isolation guarantee, JUnit XML / CI integration) so a new contributor or CI engineer can adopt v1.1 by reading only the README -- no source-reading required. Add a regression test (`tests/test_readme_snippets.py`) that fails the suite if any README YAML snippet stops parsing or the documented TOOLCFG fields drift away from `ToolConfig`.

Requirements addressed: DOC-04, DOC-05, DOC-06.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Insert `## Per-tool configuration` section (DOC-04) | `955cea1` | README.md |
| 2 | Insert `## Isolation guarantee` and `## CI integration` sections (DOC-05, DOC-06) | `236a543` | README.md |
| 3 | Update README `## Further reading` with v1.1 cross-links (CD-03) | `8671e01` | README.md |
| 4 | Add `tests/test_readme_snippets.py` regression suite (CD-06) | `1e77deb` | tests/test_readme_snippets.py |

## Architecture / Pattern Notes

- **Insertion-only edits.** Every README change used the Edit tool with verbatim `old_string` anchors that bracket exactly the insertion point. No untouched section text was reflowed; line endings (CRLF) preserved.
- **Section ordering preserved.** Final top-level order: `Configuration -> Per-tool configuration -> Sample green run -> Isolation guarantee -> CI integration -> Troubleshooting (Windows) -> Further reading`. This matches the plan's success_criteria sequence exactly.
- **Worked YAML blocks copy-pasteable.** Each per-tool example shows the COMPLETE `tools.<tool_name>:` mapping (D-02c) so a reader can paste it directly into their `config.yaml` and substitute the placeholder name. Both blocks parse via `yaml.safe_load`.
- **Reserved fields callout (D-02b).** `setup` and `depends_on` carry a single-sentence "typed but no runtime semantics in v1.1" callout immediately under the table, with the literal "TOOLCFG-03" traceability tag preserved.
- **Strong, narrowly-scoped isolation claim (D-05b).** The Isolation guarantee section opens with "Test runs do not mutate `~/.homelab_mcp/` real-state files." -- no hedging, no qualifiers. The follow-up paragraph names exactly the three real-state files (`credential_registry.json`, `known_hosts`, `migration_state.json`) the test in `tests/test_isolation.py` hashes (D-05a; documented exception to D-01's no-real-names rule).
- **CI snippet portable, with translation hint (D-03c).** A leading comment in the GHA YAML block tells Jenkins/GitLab/CircleCI users which keys to translate; the underlying `uv run mcp-test-framework run --junit-xml=results.xml` invocation works on every CI system. Action pins are major-version tags only.
- **CD-06 regression bake-in.** `tests/test_readme_snippets.py` runs by default (no live markers, no fixtures, sync) and enforces three invariants: (1) every fenced ```yaml block parses, (2) every TOOLCFG field listed in the README table exists on `ToolConfig`, (3) every `docs/EXTENDING.md#<anchor>` link in the README resolves to an actual `## Heading` in EXTENDING.md. The third assertion uses `pytest.xfail` (not `skip`) so when Plan 10-02 ships the `## Add a new MCP tool target` heading it flips to passing automatically -- and starts hard-failing if the heading is later renamed.

## Verification Results

All four tasks' automated `<verify>` commands ran cleanly.

```
$ MCPTF_CONFIG_FILE=config.yaml uv run pytest tests/test_readme_snippets.py -v
tests/test_readme_snippets.py::test_readme_yaml_snippets_parse PASSED       [ 33%]
tests/test_readme_snippets.py::test_readme_per_tool_fields_match_model PASSED [ 66%]
tests/test_readme_snippets.py::test_readme_anchor_targets_exist XFAIL       [100%]
======================== 2 passed, 1 xfailed in 3.79s =========================
```

The xfail is the expected forward-compat gate -- Plan 10-02 will introduce `## Add a new MCP tool target` in `docs/EXTENDING.md`, which will satisfy the anchor and flip the test to passing.

Other verifications:
- README headings: `^## Per-tool configuration$`, `^## Isolation guarantee$`, `^## CI integration$` each appear exactly once.
- Both per-tool YAML blocks parse via `yaml.safe_load`; the GHA YAML block parses too.
- All six documented TOOLCFG fields exist as attributes on `ToolConfig` (asserted both at edit-time and in CI via the regression test).
- Action pins (`actions/checkout@v5`, `astral-sh/setup-uv@v6`, `dorny/test-reporter@v2`) and live-marker reminder strings (`live_homelab`, `live_ollama`) are present.
- `uv run mcp-test-framework run -- --co -q` collects 691 tests (706 total, 15 deselected by `addopts`) -- 3 of the new tests are visible in the collection.

## Deviations from Plan

None at the action level -- all four tasks executed exactly as written.

One environmental note (not a deviation; a known worktree-config quirk recorded in user memory): the worktree had no `.env`, so the session-scoped `mcp_client` fixture's `homelab-mcp on PATH` precondition fired during the first `pytest tests/test_readme_snippets.py` invocation. Setting `MCPTF_CONFIG_FILE=config.yaml` for the run resolved it -- the worktree's existing `config.yaml` already points at `uvx homelab-mcp`. Subsequent and CI runs (which set `MCPTF_CONFIG_FILE` via env) work without further intervention. The new test file deliberately does not depend on any session-scoped MCP fixture; it only reads disk and imports `ToolConfig`.

## Authentication Gates

None.

## Known Stubs

None. The xfail in `test_readme_anchor_targets_exist` is an intentional, scheduled forward-compat gate (Plan 10-02), not a stub -- it is documented in the test's docstring and will resolve automatically when Plan 10-02 ships the heading.

## Threat Flags

None. Documentation-only changes; no new network endpoints, auth paths, file-access patterns, or trust boundaries.

## Self-Check: PASSED

- README.md present and updated: FOUND (commits 955cea1, 236a543, 8671e01)
- tests/test_readme_snippets.py present: FOUND (commit 1e77deb)
- All four task commits exist on branch: FOUND (`git log --oneline -5` shows 1e77deb, 8671e01, 236a543, 955cea1)
- `uv run pytest tests/test_readme_snippets.py -v` exits 0 with 2 passed + 1 xfailed: PASSED
