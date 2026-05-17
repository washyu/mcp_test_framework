---
phase: 28-codegen-output-path-codegen
plan: 04
type: execute
wave: 4
depends_on: [28-01, 28-02, 28-03]
files_modified:
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
autonomous: true
requirements:
  - CODEGEN-LIB-01
  - CODEGEN-LIB-02
must_haves:
  truths:
    - "Operator reading REQUIREMENTS.md sees CODEGEN-LIB-01 describe fail-loud + operator-tone error + pyproject.toml ini route + overwrite prompt (NOT the rejected smart-default + --output-dir framing)."
    - "Operator reading REQUIREMENTS.md sees CODEGEN-LIB-02 preserved verbatim (strict-guard, fail-fast-at-command-start interpretation locked)."
    - "Operator reading ROADMAP.md Phase 28 Goal sees the new framing (refuses to invent path; refuses to write under install tree; uses same `mcp_config_file` ini route pytest uses)."
    - "Operator reading ROADMAP.md Phase 28 Success Criteria sees three SCs: (1) fail-loud-on-missing-field + prompt + non-TTY abort; (2) site-packages guard at pre-handshake timing; (3) NEW pyproject.toml ini route parity with pytest."
  artifacts:
    - path: ".planning/REQUIREMENTS.md"
      provides: "Amended CODEGEN-LIB-01 reflecting Phase 28 CONTEXT.md D-01/D-03/D-06/D-11 decisions; CODEGEN-LIB-02 preserved verbatim."
      contains: "fail-loud operator-tone error naming the missing field"
    - path: ".planning/ROADMAP.md"
      provides: "Amended Phase 28 Goal + 3 success criteria (SC1 rewritten, SC2 refined, SC3 added)."
      contains: "reads the same `mcp_config_file` ini route pytest uses"
  key_links:
    - from: ".planning/REQUIREMENTS.md CODEGEN-LIB-01"
      to: ".planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md `<downstream_impact>` section"
      via: "verbatim copy of the New text from `<downstream_impact>` for CODEGEN-LIB-01"
      pattern: "fail-loud operator-tone error naming the missing field"
    - from: ".planning/ROADMAP.md Phase 28 Success Criteria"
      to: ".planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md `<downstream_impact>` section"
      via: "verbatim adoption of the proposed SC1/SC2/SC3 rewrites"
      pattern: "fail-loud operator-tone error"
---

<objective>
Amend `.planning/REQUIREMENTS.md` and `.planning/ROADMAP.md` to reflect the actual Phase 28 scope as locked in `28-CONTEXT.md`. The current text in both documents was written before discussion rejected the "smart default `<cwd>/tests/_generated/<server_slug>/`" framing and the `--output-dir` flag. This plan replaces the stale framings verbatim with the new text proposed in the CONTEXT.md `<downstream_impact>` section.

Purpose: keep the planning artifacts in sync with what was actually shipped in Plans 28-01 through 28-03. Without this sweep, REQUIREMENTS.md / ROADMAP.md would forever document a feature that was deliberately NOT built.

Output: amended REQUIREMENTS.md (CODEGEN-LIB-01 rewritten; CODEGEN-LIB-02 unchanged) and amended ROADMAP.md (Phase 28 Goal + SC1 rewritten, SC2 refined for pre-handshake timing, SC3 added for pyproject.toml ini-route parity).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md

<interfaces>
<!-- The CONTEXT.md `<downstream_impact>` section IS the source of truth. -->
<!-- Quoted verbatim below so the executor has zero ambiguity. -->

From .planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md `<downstream_impact>`:

### REQUIREMENTS.md amendments

- **CODEGEN-LIB-01** — rewrite around fail-loud + operator-tone error. Old text: "Operator who runs `gen-test-classes` from a project with a `tests/` directory gets generated classes under `<cwd>/tests/_generated/<server_slug>/` by default — no config required. Operators in projects without a `tests/` directory get a friendly error directing them to set `cfg.test_code.generated_root` or use `--output-dir`." New text: "Operator who runs `gen-test-classes` without `cfg.test_code.generated_root` set gets a fail-loud operator-tone error naming the missing field and pointing at `mcp-contracts config-init`. No smart default; the framework does not infer project layout. No `--output-dir` flag; `--config PATH` is the only invocation-level override." Add: "Operator running against a non-empty target dir is prompted before overwrite; in non-TTY contexts the command aborts." Add: "`gen-test-classes` resolves the config via the same `[tool.pytest.ini_options] mcp_config_file` route as pytest."

- **CODEGEN-LIB-02** — preserved verbatim. Strict-guard, fail-fast-at-command-start interpretation locked.

### ROADMAP.md amendments

- **Phase 28 Goal text** — currently "`gen-test-classes` writes generated typed classes to a sensible default path inside the operator's project (never into `site-packages/`)." Rewrites to "`gen-test-classes` refuses to invent an output path or write under its own install tree, and reads the same `mcp_config_file` ini route pytest uses." Drop "default path" framing.

- **Phase 28 Success Criteria 1** — currently SC1 is the smart-default + friendly-error spec. Rewrites to: "Operator running `mcp-contracts gen-test-classes` without `cfg.test_code.generated_root` set sees a fail-loud operator-tone error naming the missing field and pointing at `mcp-contracts config-init`. Operator with the field set sees codegen succeed (target dir is created if missing; non-empty target prompts for confirmation; non-TTY non-empty target aborts with a helpful error)."

- **Phase 28 Success Criteria 2** — preserved (site-packages guard, command-start check, friendly error). Refine to specify pre-handshake timing.

- **Phase 28 Success Criteria 3 (NEW)** — add: "Operator who set `[tool.pytest.ini_options] mcp_config_file = PATH` in pyproject.toml sees `mcp-contracts gen-test-classes` use the same config file as `pytest`, without passing `--config`."

- **Phase 30** — no impact. CLI demotion + dogfood verification unchanged.

<!-- ROADMAP.md Phase 28 section CURRENT text — to be replaced. -->

From .planning/ROADMAP.md lines 139-147 (current Phase 28 Phase Details block):
```
### Phase 28: Codegen output path (CODEGEN)
**Goal**: `gen-test-classes` writes generated typed classes to a sensible default path inside the operator's project (never into `site-packages/`). Library-mode config seam (CFG-01, CFG-02) was closed in Phase 27 (D-01: `register()` API dropped; ini route is the single config source); Phase 28 is now codegen-output-path policy only.
**Depends on**: Phase 27 (`mcp_config_file` ini route is the source of truth for config; `gen-test-classes` reads `cfg.test_code.generated_root` from the same Config object).
**Requirements**: CODEGEN-LIB-01, CODEGEN-LIB-02
**Success Criteria** (what must be TRUE):
  1. Operator running `mcp-contracts gen-test-classes` from a project with a `tests/` directory and no config set gets generated classes under `<cwd>/tests/_generated/<server_slug>/` by default; operator in a project without `tests/` gets a friendly error directing them to set `cfg.test_code.generated_root` or pass `--output-dir`.
  2. `gen-test-classes` refuses to write under any `sys.path` directory containing the installed `mcp_test_framework` package — the resolved absolute target path is checked at command start and aborts with a friendly error if it falls inside an installed-package tree.
**Plans**: TBD
```

<!-- REQUIREMENTS.md CODEGEN section CURRENT text — to be replaced. -->

From .planning/REQUIREMENTS.md lines 45-48:
```
### Codegen Output Path (CODEGEN)

- [ ] **CODEGEN-LIB-01**: Operator who runs `gen-test-classes` from a project with a `tests/` directory gets generated classes under `<cwd>/tests/_generated/<server_slug>/` by default — no config required. Operators in projects without a `tests/` directory get a friendly error directing them to set `cfg.test_code.generated_root` or use `--output-dir`.
- [ ] **CODEGEN-LIB-02**: `gen-test-classes` refuses to write under any `sys.path` directory containing the installed `mcp_test_framework` package (typically `site-packages/`); resolves the target path absolute at command-start and aborts with a friendly error if the resolved path is inside an installed-package tree.
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Amend REQUIREMENTS.md CODEGEN-LIB-01 + leave CODEGEN-LIB-02 verbatim</name>
  <files>.planning/REQUIREMENTS.md</files>
  <read_first>
    - .planning/REQUIREMENTS.md lines 45-50 (full Codegen Output Path section) — locate the exact text to replace
    - .planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md `<downstream_impact>` section "REQUIREMENTS.md amendments" — verbatim text to substitute
  </read_first>
  <action>
    Use the Edit tool to replace the existing CODEGEN-LIB-01 line in `.planning/REQUIREMENTS.md` (around line 47).

    Find the exact line (the existing CODEGEN-LIB-01 bullet, ONE line):
    ```
    - [ ] **CODEGEN-LIB-01**: Operator who runs `gen-test-classes` from a project with a `tests/` directory gets generated classes under `<cwd>/tests/_generated/<server_slug>/` by default — no config required. Operators in projects without a `tests/` directory get a friendly error directing them to set `cfg.test_code.generated_root` or use `--output-dir`.
    ```

    Replace with (a multi-line bullet using sub-bullets so the four locked sub-behaviors are individually testable; matches CONTEXT.md `<downstream_impact>` proposed text plus the two Add: clauses):
    ```
    - [ ] **CODEGEN-LIB-01**: Operator who runs `gen-test-classes` without `cfg.test_code.generated_root` set gets a fail-loud operator-tone error naming the missing field and pointing at `mcp-contracts config-init`. No smart default; the framework does not infer project layout. No `--output-dir` flag; `--config PATH` is the only invocation-level override. Operator running against a non-empty target dir is prompted before overwrite; in non-TTY contexts the command aborts with exit code 2 (no `--yes` / `--force` flag exists). `gen-test-classes` resolves the config via the same `[tool.pytest.ini_options] mcp_config_file` route as pytest (precedence: `--config PATH` > pyproject.toml ini value > `MCPTF_CONFIG_FILE` env var (deprecated, removed v1.5) > `./config.yaml` autodiscovery > fail-loud).
    ```

    Do NOT touch the CODEGEN-LIB-02 line directly below — preserved verbatim per CONTEXT.md `<downstream_impact>`.

    Also update the Traceability table for CODEGEN-LIB-01 + CODEGEN-LIB-02 status from `Pending` to `Complete` ONLY after this plan ships. For this Wave 4 sweep, leave the status as `Pending` — the verification phase will flip these to `Complete` after running the full phase verification.
  </action>
  <verify>
    <automated>node ./node_modules/@gsd-build/sdk/dist/cli.js query frontmatter.validate .planning/phases/28-codegen-output-path-codegen/28-04-docs-sweep-PLAN.md --schema plan</automated>
  </verify>
  <acceptance_criteria>
    - .planning/REQUIREMENTS.md CODEGEN-LIB-01 line contains the literal string "fail-loud operator-tone error naming the missing field"
    - .planning/REQUIREMENTS.md CODEGEN-LIB-01 line contains the literal string "No `--output-dir` flag"
    - .planning/REQUIREMENTS.md CODEGEN-LIB-01 line contains the literal string "non-empty target dir is prompted before overwrite"
    - .planning/REQUIREMENTS.md CODEGEN-LIB-01 line contains the literal string "`[tool.pytest.ini_options] mcp_config_file`"
    - .planning/REQUIREMENTS.md CODEGEN-LIB-01 line does NOT contain "tests/_generated/<server_slug>/" (stale smart-default text removed)
    - .planning/REQUIREMENTS.md CODEGEN-LIB-01 line does NOT contain "by default — no config required" (stale framing removed)
    - .planning/REQUIREMENTS.md CODEGEN-LIB-02 line is UNCHANGED from current text (grep for `refuses to write under any` confirms it's present verbatim)
  </acceptance_criteria>
  <done>
    - CODEGEN-LIB-01 rewritten to reflect actual Phase 28 scope; CODEGEN-LIB-02 untouched.
  </done>
</task>

<task type="auto">
  <name>Task 2: Amend ROADMAP.md Phase 28 Goal + Success Criteria (SC1 rewritten, SC2 refined, SC3 added)</name>
  <files>.planning/ROADMAP.md</files>
  <read_first>
    - .planning/ROADMAP.md lines 139-147 (current Phase 28 Phase Details block) — exact text to replace
    - .planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md `<downstream_impact>` section "ROADMAP.md amendments" — verbatim text to substitute
    - .planning/ROADMAP.md line 81 (the "Phase 28" entry in the v1.4 task list) — leave the brief title alone unless it contradicts the new Goal; the brief is currently "Config seam closed in Phase 27; remaining work is a `tests/_generated/` default that refuses to write into `site-packages/` for `gen-test-classes`." which IS stale. Replace.
  </read_first>
  <action>
    Edit 1 — `.planning/ROADMAP.md` line 81 (the bulleted entry in the v1.4 task list):

    Find:
    ```
    - [ ] **Phase 28: Codegen output path (CODEGEN)** — Config seam closed in Phase 27; remaining work is a `tests/_generated/` default that refuses to write into `site-packages/` for `gen-test-classes`.
    ```

    Replace with:
    ```
    - [ ] **Phase 28: Codegen output path (CODEGEN)** — `gen-test-classes` refuses to invent an output path or write under its own install tree, prompts before overwriting non-empty targets, and reads the same `mcp_config_file` ini route pytest uses.
    ```

    Edit 2 — `.planning/ROADMAP.md` lines 139-147 (the full Phase 28 Phase Details block). Replace the entire block:

    Find:
    ```
    ### Phase 28: Codegen output path (CODEGEN)
    **Goal**: `gen-test-classes` writes generated typed classes to a sensible default path inside the operator's project (never into `site-packages/`). Library-mode config seam (CFG-01, CFG-02) was closed in Phase 27 (D-01: `register()` API dropped; ini route is the single config source); Phase 28 is now codegen-output-path policy only.
    **Depends on**: Phase 27 (`mcp_config_file` ini route is the source of truth for config; `gen-test-classes` reads `cfg.test_code.generated_root` from the same Config object).
    **Requirements**: CODEGEN-LIB-01, CODEGEN-LIB-02
    **Success Criteria** (what must be TRUE):
      1. Operator running `mcp-contracts gen-test-classes` from a project with a `tests/` directory and no config set gets generated classes under `<cwd>/tests/_generated/<server_slug>/` by default; operator in a project without `tests/` gets a friendly error directing them to set `cfg.test_code.generated_root` or pass `--output-dir`.
      2. `gen-test-classes` refuses to write under any `sys.path` directory containing the installed `mcp_test_framework` package — the resolved absolute target path is checked at command start and aborts with a friendly error if it falls inside an installed-package tree.
    **Plans**: TBD
    ```

    Replace with (Goal + SC1 rewritten, SC2 refined for pre-handshake timing, SC3 added for pyproject parity, Plans listed):
    ```
    ### Phase 28: Codegen output path (CODEGEN)
    **Goal**: `gen-test-classes` refuses to invent an output path or write under its own install tree, and reads the same `mcp_config_file` ini route pytest uses. Driver: the framework knows nothing about the operator's project layout (rejecting "smart default" framing); single config-resolution route extended from the pytest plugin to the Typer CLI.
    **Depends on**: Phase 27 (`mcp_config_file` ini route is the source of truth for config; `gen-test-classes` reads `cfg.test_code.generated_root` from the same Config object).
    **Requirements**: CODEGEN-LIB-01, CODEGEN-LIB-02
    **Success Criteria** (what must be TRUE):
      1. Operator running `mcp-contracts gen-test-classes` without `cfg.test_code.generated_root` set sees a fail-loud operator-tone error naming the missing field and pointing at `mcp-contracts config-init`. Operator with the field set sees codegen succeed (target dir is created if missing; non-empty target prompts for confirmation in a TTY; non-TTY non-empty target aborts with a helpful error and exit code 2 — no `--yes` / `--force` flag exists).
      2. `gen-test-classes` refuses to write under any directory containing the installed `mcp_test_framework` package — the resolved absolute target path is checked at command start (BEFORE the MCP handshake) and aborts with an operator-tone error naming `test_code.generated_root`, the resolved target path, and the framework install root if it falls inside the installed-package tree. No bypass flag or config knob exists.
      3. Operator who set `[tool.pytest.ini_options] mcp_config_file = PATH` in pyproject.toml sees `mcp-contracts gen-test-classes` use the same config file as `pytest`, without passing `--config`. Precedence ladder: `--config PATH` > pyproject.toml ini value > `MCPTF_CONFIG_FILE` env var (deprecated, removed v1.5) > `./config.yaml` autodiscovery > fail-loud.
    **Plans**: 4 plans
      - [ ] 28-01-site-packages-guard-PLAN.md — Pre-handshake site-packages guard (CODEGEN-LIB-02)
      - [ ] 28-02-pyproject-ini-config-route-PLAN.md — `gen-test-classes` reads `[tool.pytest.ini_options] mcp_config_file` from pyproject.toml
      - [ ] 28-03-overwrite-prompt-PLAN.md — Non-empty-dir overwrite prompt + non-TTY abort
      - [ ] 28-04-docs-sweep-PLAN.md — REQUIREMENTS.md + ROADMAP.md amendments to reflect actual Phase 28 scope
    ```

    Edit 3 — `.planning/ROADMAP.md` Progress table line for Phase 28. Find:
    ```
    | 28. Config seam + codegen output path | v1.4 | 0/TBD | Not started | - |
    ```
    Replace with:
    ```
    | 28. Codegen output path (CODEGEN) | v1.4 | 0/4 | In progress | - |
    ```
    (Note: this row's Plans column reads `0/4` because the four plans have just been authored; execute-phase will tick them off as plans complete. Status "In progress" reflects that planning is done, execution beginning.)
  </action>
  <verify>
    <automated>node ./node_modules/@gsd-build/sdk/dist/cli.js query frontmatter.validate .planning/phases/28-codegen-output-path-codegen/28-04-docs-sweep-PLAN.md --schema plan</automated>
  </verify>
  <acceptance_criteria>
    - .planning/ROADMAP.md Phase 28 Goal line contains the literal string "refuses to invent an output path or write under its own install tree, and reads the same `mcp_config_file` ini route pytest uses"
    - .planning/ROADMAP.md Phase 28 SC1 contains the literal string "fail-loud operator-tone error naming the missing field"
    - .planning/ROADMAP.md Phase 28 SC1 contains the literal string "no `--yes` / `--force` flag exists"
    - .planning/ROADMAP.md Phase 28 SC2 contains the literal string "BEFORE the MCP handshake"
    - .planning/ROADMAP.md Phase 28 SC2 contains the literal string "No bypass flag or config knob exists"
    - .planning/ROADMAP.md Phase 28 SC3 exists as a numbered item containing the literal string "`[tool.pytest.ini_options] mcp_config_file`"
    - .planning/ROADMAP.md Phase 28 Goal does NOT contain "tests/_generated/" (stale smart-default text removed)
    - .planning/ROADMAP.md Phase 28 Goal does NOT contain "--output-dir" (stale flag reference removed)
    - .planning/ROADMAP.md Plans block lists the four 28-NN-*-PLAN.md filenames matching this phase's actual plans
    - .planning/ROADMAP.md Progress table row for Phase 28 reads "0/4" plans and "In progress"
  </acceptance_criteria>
  <done>
    - Phase 28 Goal rewritten; SC1 rewritten; SC2 refined for pre-handshake timing; SC3 added for pyproject parity; Plans block populated with the four real plan filenames; Progress table updated.
  </done>
</task>

</tasks>

<verification>
- Grep `grep -n "tests/_generated/<server_slug>" .planning/REQUIREMENTS.md .planning/ROADMAP.md` returns NO matches (stale text fully removed)
- Grep `grep -n "\-\-output-dir" .planning/REQUIREMENTS.md .planning/ROADMAP.md` returns NO matches (stale flag reference removed)
- Grep `grep -n "fail-loud operator-tone error naming the missing field" .planning/REQUIREMENTS.md .planning/ROADMAP.md` returns matches in BOTH files
- Grep `grep -n "BEFORE the MCP handshake" .planning/ROADMAP.md` returns a match (SC2 refinement landed)
- Grep `grep -n "\[tool.pytest.ini_options\] mcp_config_file" .planning/ROADMAP.md` returns at least two matches (SC3 + Goal mention)
- CODEGEN-LIB-02 text in REQUIREMENTS.md is byte-identical to pre-edit state (preserved verbatim per CONTEXT.md)
</verification>

<success_criteria>
REQUIREMENTS.md and ROADMAP.md now describe what was actually built in Plans 28-01..03. No reader will reach for the rejected smart-default or `--output-dir` framings. The pyproject.toml ini-route extension (Plan 28-02) is explicit in SC3.
</success_criteria>

<output>
After completion, create `.planning/phases/28-codegen-output-path-codegen/28-04-SUMMARY.md` documenting:
- Which lines of REQUIREMENTS.md were amended (CODEGEN-LIB-01 single bullet)
- Which lines of ROADMAP.md were amended (line 81 brief entry + Phase 28 Phase Details block + Progress table row)
- Confirmation that CODEGEN-LIB-02 in REQUIREMENTS.md is byte-identical to its pre-edit state
- Note that Traceability table CODEGEN-LIB-01/02 status flip from "Pending" → "Complete" is intentionally deferred to phase verification (not this Wave 4 docs sweep)
</output>
