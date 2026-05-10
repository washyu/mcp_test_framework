---
phase: 13-config-safety-opt-in-tool-selection
plan: 05
type: execute
wave: 3
depends_on: [13-02]
files_modified:
  - docs/MIGRATION-v1-to-v2.md
  - tests/unit/test_migration_doc.py
  - pyproject.toml
autonomous: true
requirements: [SAFE-07]
must_haves:
  truths:
    - "D-10: The file docs/MIGRATION-v1-to-v2.md exists at repo root + docs/."
    - "D-10: The doc explains v2's opt-in default in plain English and contrasts it with v1's opt-out default."
    - "D-09: The doc contains a step-by-step port walkthrough: rerun `config-init`, port `call_arguments` / `judges` / `skip_reason` per tool, drop `target:` block, drop `.env` overlay reliance."
    - "D-10: The doc includes a before-vs-after YAML diff for at least one example tool."
    - "D-09: The doc references `mcp-test-framework config-init -o config.yaml.new` (the exact command the SAFE-06 error message recommends)."
    - "D-10: A regression test in tests/unit/test_migration_doc.py asserts the doc exists and pins the load-bearing substrings."
    - "D-05: pyproject.toml direct dependencies do NOT include `python-dotenv` (verified absent — the import was the actual cleanup, completed in Plan 13-02)."
  artifacts:
    - path: "docs/MIGRATION-v1-to-v2.md"
      provides: "SAFE-07 standalone diff-driven migration walkthrough"
      min_lines: 60
      contains: "version: 2"
    - path: "tests/unit/test_migration_doc.py"
      provides: "Regression test pinning the doc keywords so wording cannot drift"
  key_links:
    - from: "src/mcp_test_framework/cli.py:_emit_operator_error_for_validation (SAFE-06 branch)"
      to: "docs/MIGRATION-v1-to-v2.md"
      via: "the SAFE-06 message body string `docs/MIGRATION-v1-to-v2.md`"
      pattern: "docs/MIGRATION-v1-to-v2.md"
    - from: "tests/unit/test_migration_doc.py"
      to: "docs/MIGRATION-v1-to-v2.md"
      via: "Path.read_text().__contains__ assertions"
      pattern: "_repo_root\\(\\) / \"docs\""
---

<objective>
Land `docs/MIGRATION-v1-to-v2.md` — the standalone diff-driven port guide referenced by the LOCKED SAFE-06 error message that Plan 13-02 wired into `cli.py`. The doc walks an existing v1 operator through:
1. The opt-out → opt-in semantic flip (plain English; why it matters).
2. The step-by-step port: rerun `config-init -o config.yaml.new`, port `call_arguments` / `judges` / `skip_reason` per tool, drop `target:` block, drop `.env` overlay.
3. A before-vs-after YAML diff for one example tool.
4. A "what about `.env`" coda explaining the framework no longer reads it for config values.

Also: verify `pyproject.toml` direct dependencies do NOT include `python-dotenv` (per 13-PATTERNS.md note, the v1.1 dep was always transitive via `mcp[cli]`, and Plan 13-02 deleted the only direct `from dotenv import` site — this plan is the final audit step).

Purpose: SAFE-07 (migration documentation).

Output: `docs/MIGRATION-v1-to-v2.md` (≤100 lines, plain markdown, no external links beyond in-repo doc paths), a regression test in `tests/unit/test_migration_doc.py` following the existing `tests/unit/test_error_style.py` pattern, and a verified-clean `pyproject.toml`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md
@.planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md
@.planning/phases/13-config-safety-opt-in-tool-selection/13-02-SUMMARY.md
@docs/ERROR-STYLE.md
@tests/unit/test_error_style.py
@pyproject.toml
</context>

<truths>
**Locked decisions implemented by this plan (quoted from 13-CONTEXT.md):**

- **D-10:** "`docs/MIGRATION-v1-to-v2.md` is a new standalone file, diff-driven. Sections: (1) plain-English summary of v2 changes (opt-out→opt-in, `.env` and env-overlay dropped, version bump, `target.tool_name` removed); (2) step-by-step port — rerun `config-init -o config.yaml`, then a side-by-side before/after YAML showing how to move `skip_reason`, `call_arguments`, `judges` blocks for each tool the operator wants to keep; (3) drop `.env` and stop relying on env-overlay. Standalone so the SAFE-06 error message points at a stable URL/path that isn't buried inside EXTENDING.md."
- **D-09 (rationale referenced in the doc):** "No `config-migrate` subcommand. Refuse-on-load + doc-driven manual port is the migration UX. Rationale: the unlisted-default flip (opt-out → opt-in) is consequential enough that operators must re-read every per-tool entry; auto-migration that silently keeps old `call_arguments` while flipping the default behind the operator is the exact silent-destructive class v1.2 is fighting against."

**13-PATTERNS.md correction (load-bearing):** "the current `pyproject.toml` (lines 7-16) does NOT declare `python-dotenv` directly — it arrives only via `mcp[cli]`'s transitive cone. CONTEXT.md D-05 says 'remove `python-dotenv` from direct `pyproject.toml` deps.' There is nothing to remove from `[project].dependencies` itself; the verifiable Phase 13 action is (a) deleting the `from dotenv import dotenv_values` line at `config.py:35` and (b) confirming no other `import dotenv` site exists across `src/`." Plan 13-02 completed (a); this plan completes (b) as an audit.
</truths>

<tasks>

<task type="auto">
  <name>Task 1: Write docs/MIGRATION-v1-to-v2.md per D-10 skeleton + regression test</name>
  <files>docs/MIGRATION-v1-to-v2.md, tests/unit/test_migration_doc.py</files>
  <read_first>
    - docs/ERROR-STYLE.md (the doc this one parallels in style — short, lock-file markdown referenced verbatim from code and tests)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md §decisions D-09, D-10, D-11 (target deletion instruction)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md §8 (the suggested MIGRATION-v1-to-v2.md skeleton)
    - tests/unit/test_error_style.py (lines 19-66 — the doc-pinning regression pattern to mirror)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-02-SUMMARY.md (confirm SAFE-06 message body in cli.py references this filename)
  </read_first>
  <action>
    Create `docs/MIGRATION-v1-to-v2.md` with the following exact body. Word the prose in lowercase-first operator tone (matching `docs/ERROR-STYLE.md` style — sentence-style headings, no Title Case, no emoji, no exclamation marks):

    ```markdown
    # Migrating config from schema v1 → v2

    This release of mcp-test-framework expects schema version 2. v1 configs no
    longer load -- the loader refuses with a clear pointer here. This page
    walks an existing operator through the port.

    ## Why this matters

    In v1, a tool with no `tools.<name>` entry ran by default -- including any
    destructive tools the server advertised. In v2, a tool with no entry skips
    by default. You explicitly opt every tool in.

    The flip is intentional. Auto-migration would silently keep your old
    `call_arguments` while inverting the default behind your back -- the exact
    silent-destructive class v2 is built to prevent. So the migration is
    manual and the framework refuses to load a v1 file.

    ## What stays the same

    Per-tool fields port forward unchanged: `call_arguments`, `judges`,
    `skip_reason`. Top-level `ollama:`, `mcp_server:`, and
    `judge_timeout_seconds:` blocks port forward unchanged.

    ## What changes

    - `version: 1` → `version: 2` (top-level header).
    - `target:` block → DELETE. v2 has no `target` field. Single-tool focus is
      now done via a focus config passed to `--config`
      (e.g. `--config focus-list_tools.yaml`).
    - `.env` files no longer override config. If you had any framework config
      in `.env` (`OLLAMA_BASE_URL`, `MCP_SERVER_COMMAND`, etc.), move it into
      your YAML.
    - env vars no longer override config. The framework's config sources
      collapse to: YAML + CLI flags.
    - Unlisted tools auto-skip. In v1, you skipped destructive tools with
      `tools.<name>.skip: true` entries. In v2, you opt them IN by listing
      them; everything else skips with reason `"not selected in config"`.

    ## Step-by-step port

    1. Run `mcp-test-framework config-init -o config.yaml.new` from your repo
       root. This emits a complete v2 scaffold with every discovered tool
       listed as `skip: true`.
    2. Open both your old `config.yaml` and the new `config.yaml.new` side by
       side.
    3. For each tool you want to keep testing:
       - Find the tool's block in `config.yaml.new`.
       - Delete the `skip: true` and `skip_reason:` lines.
       - Copy your `call_arguments:` / `judges:` blocks across from the old
         file.
    4. Delete the top-level `target:` block from your old config (do not copy
       it into the new file).
    5. If you had framework config in `.env`, move it into your new YAML.
    6. Replace `config.yaml` with `config.yaml.new`.
    7. Re-run `mcp-test-framework run`. The pre-run output will show which
       tools are selected.

    ## Side-by-side per-tool example

    Before (v1):

    ```yaml
    version: 1

    target:
      tool_name: null

    tools:
      list_servers:
        call_arguments:
          tag: "production"
        judges: ["RUB-01"]
      delete_database:
        skip: true
        skip_reason: "destructive -- never run against the live cluster"
    ```

    After (v2 -- opt-in equivalent):

    ```yaml
    version: 2

    # target: block deleted.

    tools:
      list_servers:
        # listed and not skipped -> selected to run.
        call_arguments:
          tag: "production"
        judges: ["RUB-01"]
      delete_database:
        # still listed-with-skip -> SKIP row with the curated reason.
        skip: true
        skip_reason: "destructive -- never run against the live cluster"
      # Every other tool the server advertises auto-skips with reason
      # "not selected in config". You no longer need an entry per tool.
    ```

    ## What about `.env`?

    The framework no longer reads `.env` for config values. CI-secret patterns
    (API keys for future HTTP-backed judges) still pass through `.env` as a
    process-env convention, but the framework's config layer ignores it.

    See `.env.example` in the repo root for the supported pattern.
    ```

    Critical wording invariants (these substrings are what the regression test pins):
    - `version: 2`
    - `opt every tool in`
    - `config-init -o config.yaml.new`
    - `target:` (the deletion instruction)
    - `not selected in config`
    - `docs/MIGRATION-v1-to-v2.md` does NOT appear in its own body (no self-reference)
    - The doc body uses `--` (two hyphens), not `—` (em-dash), matching ERROR-STYLE.md style.

    Now create the regression test at `tests/unit/test_migration_doc.py`:

    ```python
    """Regression for SAFE-07: docs/MIGRATION-v1-to-v2.md exists and pins the
    load-bearing wording. Parallels tests/unit/test_error_style.py.

    Phase 13 SAFE-06's locked operator-error message at
    src/mcp_test_framework/cli.py references this doc by exact path. If the doc
    disappears or the load-bearing substrings drift, the SAFE-06 UX breaks.
    """
    from __future__ import annotations

    from pathlib import Path


    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[2]


    MIGRATION_DOC = _repo_root() / "docs" / "MIGRATION-v1-to-v2.md"


    def test_migration_doc_exists() -> None:
        assert MIGRATION_DOC.is_file(), f"missing {MIGRATION_DOC}"


    def test_migration_doc_pins_v2_keywords() -> None:
        text = MIGRATION_DOC.read_text(encoding="utf-8")
        assert "version: 2" in text
        assert "config-init -o config.yaml.new" in text
        assert "opt every tool in" in text
        assert "target:" in text                          # deletion instruction
        assert "not selected in config" in text           # SAFE-01 reason string
        assert ".env" in text                             # the dotenv coda


    def test_migration_doc_uses_ascii_dashes_not_emdash() -> None:
        """Match ERROR-STYLE.md tone: two hyphens, not U+2014."""
        text = MIGRATION_DOC.read_text(encoding="utf-8")
        assert "—" not in text, "em-dash detected; use `--` to match ERROR-STYLE.md"


    def test_migration_doc_does_not_leak_planning_ids() -> None:
        """Operator-facing doc: same banned tokens as ERROR-STYLE.md."""
        import re

        text = MIGRATION_DOC.read_text(encoding="utf-8")
        banned_patterns = [
            r"\bPhase \d",
            r"\bPlan \d-\d",
            r"\b[A-Z]{2,}-\d{2}\b",     # spec IDs like SAFE-01, TOOLCFG-01
            r"\b\d{6}-[a-z0-9]{3}\b",   # quick-task IDs
            r"\bsrc/.*\.py:\d+",
        ]
        for pat in banned_patterns:
            assert re.search(pat, text) is None, (
                f"migration doc leaks planning-artifact pattern {pat!r}; "
                f"see docs/ERROR-STYLE.md banned-tokens checklist"
            )
    ```

    Note: The banned-pattern test deliberately mirrors the ERROR-STYLE.md "banned strings (manual review checklist)" section at `docs/ERROR-STYLE.md:75-86`. The migration doc is operator-facing and must not leak `SAFE-01`, `Phase 13`, etc. — write the doc body without those tokens.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_migration_doc.py -v --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `test -f docs/MIGRATION-v1-to-v2.md` exits 0 (POSIX) or `Test-Path docs/MIGRATION-v1-to-v2.md` returns True (PowerShell).
    - `grep -c "^" docs/MIGRATION-v1-to-v2.md` returns ≥60 (the doc is the documented length).
    - `grep -n "version: 2" docs/MIGRATION-v1-to-v2.md` returns at least 3 matches (the header explanation + the two YAML examples).
    - `grep -n "opt every tool in" docs/MIGRATION-v1-to-v2.md` returns one match.
    - `grep -n "config-init -o config.yaml.new" docs/MIGRATION-v1-to-v2.md` returns one match.
    - `grep -n "not selected in config" docs/MIGRATION-v1-to-v2.md` returns one match.
    - `grep -n "—" docs/MIGRATION-v1-to-v2.md` returns ZERO matches (em-dash banned).
    - `grep -nE "Phase [0-9]|Plan [0-9]-[0-9]|[A-Z]{2,}-[0-9]{2}\b" docs/MIGRATION-v1-to-v2.md` returns ZERO matches (banned planning IDs).
    - `uv run pytest tests/unit/test_migration_doc.py -v` exits 0.
    - The SAFE-06 wiring test from Plan 13-02 (`test_error_style_safe_06_body_matches_cli_wiring`) still passes (no regression).
  </acceptance_criteria>
  <done>
    The doc exists, is grep-pinned to its load-bearing strings, contains the before/after YAML diff, and contains no planning-artifact leakage. The SAFE-06 CLI error message's reference to `docs/MIGRATION-v1-to-v2.md` resolves to a real, accurate file.
  </done>
</task>

<task type="auto">
  <name>Task 2: Audit pyproject.toml direct deps and confirm no `python-dotenv` declaration</name>
  <files>pyproject.toml</files>
  <read_first>
    - pyproject.toml (full file, focus on `[project].dependencies` lines 7-16)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md §7 (the "no direct python-dotenv dep currently — Plan 13-02 deleted the only `from dotenv import` line" note)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-02-SUMMARY.md (confirms `from dotenv import dotenv_values` was removed from config.py)
  </read_first>
  <action>
    Three steps:

    1. **Verify the existing dependencies block is clean.** Run `grep -nE "dotenv|python-dotenv" pyproject.toml`. Expected: ZERO matches. If a `python-dotenv` line is present (e.g., snuck in via a Phase 12 wave), DELETE it from `[project].dependencies`. The end-state dependencies block (currently lines 7-16) must read exactly:

       ```toml
       dependencies = [
           # `[cli]` extra pulls Typer transitively. Phase 5
           # CONTEXT.md / 05-01-PLAN.md: do NOT declare `typer` directly -- it must
           # remain transitive via mcp[cli] so we have a single source of truth for
           # the CLI framework version.
           "mcp[cli]>=1.27",
           "pydantic>=2.13,<3",
           "pydantic-settings[yaml]>=2.14",
           "jsonschema>=4.26",
       ]
       ```

       Note the comment edit: drop the "(and python-dotenv)" parenthetical from the existing comment at pyproject.toml:8. Old:
       ```
       # `[cli]` extra pulls Typer (and python-dotenv) transitively. ...
       ```
       New:
       ```
       # `[cli]` extra pulls Typer transitively. ...
       ```

       Rationale: even if mcp[cli] still transitively pulls python-dotenv, calling it out is misleading now that the framework's config layer doesn't use it. Keep the explanation accurate.

    2. **Verify no `import dotenv` site remains anywhere in `src/`.** Run `grep -rn "import dotenv\|from dotenv" src/`. Expected: ZERO matches. (Plan 13-02 deleted the one site at `config.py:35`; this is the audit.) If any other site is found, that's a Plan 13-02 gap — surface it and patch it in this plan: delete the import line. If the use is non-trivial (the call is using dotenv_values for something other than env-overlay), STOP and surface a question to the orchestrator — do not silently keep an undocumented dep.

    3. **Step removed (revision iteration 1).** The pre-revision plan suggested an "optional belt-and-suspenders" addition to `tests/unit/test_banned_imports.py`. That file exists but is scoped to ruff TID251 / `homelab_mcp` banned imports (a ruff-rule smoke test, not a generic banned-imports surface); adding a `dotenv` check would dilute its purpose. The grep gates in steps 1-2 plus the regression behavior tests in Plan 13-02 already pin the absence of `import dotenv` and the absence of any direct `python-dotenv` declaration. No additional test is needed.
  </action>
  <verify>
    <automated>uv run python -c "import re, pathlib; root = pathlib.Path('.'); hits = []; \
  [hits.append(str(f)) for f in list((root/'src').rglob('*.py')) + [root/'pyproject.toml'] if f.is_file() and re.search(r'import dotenv|from dotenv|python-dotenv', f.read_text(encoding='utf-8'))]; \
  print('hits:', hits); assert hits == [], f'dotenv references must be zero, got {hits}'"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -nE "dotenv|python-dotenv" pyproject.toml` returns ZERO matches (no comment mentions either; no dependency lines).
    - `grep -rn "import dotenv\|from dotenv" src/` returns ZERO matches.
    - `uv sync` still succeeds (no broken deps — Plan 13-02's import removal made `python-dotenv` an unused transitive; uv resolves it cleanly).
    - The dependencies block in `pyproject.toml` retains the 4 declared deps: `mcp[cli]`, `pydantic`, `pydantic-settings[yaml]`, `jsonschema`.
  </acceptance_criteria>
  <done>
    `pyproject.toml` is verified clean and its existing comment is updated to match reality. No `import dotenv` site survives in source. Plan 13-02's deletion is audited and confirmed complete.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator reading docs | Docs are read-only artifacts; threat surface is misinformation, not code |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-13-05-01 | Information disclosure / misinformation | Migration doc could give incorrect porting instructions and lead an operator to opt destructive tools in by accident | mitigate | The before/after YAML diff is explicit: `delete_database` stays `skip: true` in the v2 example. The doc states twice that "unlisted -> auto-skip" and that the default flipped. Regression test pins the wording so the safety-critical phrasing cannot silently drift. |
| T-13-05-02 | Doc/code drift | The SAFE-06 error references this doc by exact path; if the doc is renamed, the error message points at a 404 | mitigate | Two-sided pin: Plan 13-02 added `test_error_style_safe_06_body_matches_cli_wiring` which asserts the cli.py text contains `docs/MIGRATION-v1-to-v2.md`; this plan adds `test_migration_doc_exists` which asserts the file is there. Renaming either side without the other breaks CI. |
| T-13-05-03 | Stale-dep contamination | Leaving `python-dotenv` as a stated direct dep when it is no longer used | mitigate | Audit step 1 of Task 2 removes the misleading comment and confirms no direct declaration. Grep gate enforces. |
| T-13-05-04 | Supply chain | Adding `python-dotenv` back accidentally | accept | No mitigation needed in this plan — the audit confirms it is not present. Future regressions would be caught by code review; no automated rule needed for v1.2. |

No `high` severity threats. Plan is mostly docs + audit; security posture is unchanged outside the doc's role in directing operators to safe behavior.
</threat_model>

<verification>
1. `docs/MIGRATION-v1-to-v2.md` exists and contains the load-bearing strings.
2. Regression test `tests/unit/test_migration_doc.py` exits 0.
3. The SAFE-06 cli.py reference to `docs/MIGRATION-v1-to-v2.md` (added by Plan 13-02) resolves to a real file.
4. `pyproject.toml` does NOT name `python-dotenv` in any form; comment updated to match.
5. `grep -rn "import dotenv" src/` returns ZERO matches.
6. Manual smoke: an operator running `mcp-test-framework run --config v1.yaml` sees the SAFE-06 error, follows its `next:` step, opens `docs/MIGRATION-v1-to-v2.md`, and finds an actionable port walkthrough.
</verification>

<success_criteria>
- All 7 `must_haves.truths` are observable: file exists, plain-English opt-in/out contrast, step-by-step port, before/after diff, `config-init -o config.yaml.new` reference, regression test, no `python-dotenv` direct dep.
- The end-to-end SAFE-06 UX is complete: v1 config → loud error → operator reads doc → completes port → run succeeds.
- Memory item `project_dotenv_silently_beats_config.md` is fully resolved (Plan 13-02 + this audit close it).
</success_criteria>

<output>
After completion, create `.planning/phases/13-config-safety-opt-in-tool-selection/13-05-SUMMARY.md`. Include:
- The doc's section count and approximate line count.
- The 5 pinned substrings.
- Confirmation that `python-dotenv` is not a direct dep (no removal needed; audit closed).
- Closing note: Phase 13 plans 01-05 deliver all 7 SAFE requirements; the next entry point is `/gsd-execute-phase 13` once `/gsd-verify-phase 12` confirms Phase 12 closure.
</output>
