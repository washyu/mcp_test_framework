---
phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
plan: 05
type: execute
wave: 3
depends_on: [31-04]
files_modified:
  - README.md
  - docs/ERROR-STYLE.md
  - docs/LIBRARY-MODE.md
  - docs/EXTENDING.md
autonomous: true
requirements: [V1DROP-02]
tags: [v1-decommission, doc-scrub]
must_haves:
  truths:
    - "`grep -rn 'MIGRATION-v1-to-v2' README.md docs/` returns zero matches."
    - "`grep -rn 'MCPTF_CONFIG_FILE' README.md docs/` returns zero matches (the env-var doc scrub completes the SHIM-05 doc story)."
    - "README references `version: 2` directly with NO migration callout."
    - "docs/ERROR-STYLE.md reference messages no longer cite `docs/MIGRATION-v1-to-v2.md`."
    - "docs/LIBRARY-MODE.md has no `## Migration from MCPTF_CONFIG_FILE env var` section."
    - "docs/EXTENDING.md references `--config` only (not `MCPTF_CONFIG_FILE / --config`)."
  artifacts:
    - path: "README.md"
      provides: "Cross-ref scrub - MCPTF_CONFIG_FILE + MIGRATION-v1-to-v2 mentions removed"
      contains: "mcp_config_file"
    - path: "docs/ERROR-STYLE.md"
      provides: "SAFE-06 reference message rewritten to D-11 wording (or section deleted)"
      contains: "schema version 2"
    - path: "docs/LIBRARY-MODE.md"
      provides: "Migration section deleted; env-var references scrubbed"
      contains: "mcp_config_file"
    - path: "docs/EXTENDING.md"
      provides: "L211 env-var reference scrubbed"
      contains: ""
  key_links: []
---

<objective>
Scrub every `docs/MIGRATION-v1-to-v2.md` cross-reference AND every operator-facing `MCPTF_CONFIG_FILE` mention from the doc tree. Updates four files per RESEARCH §"Doc / Config-File Inventory". Implements V1DROP-02 per Phase 31 CONTEXT.

Purpose: Complete the V1DROP doc story. After this plan, the operator reading README / ERROR-STYLE / LIBRARY-MODE / EXTENDING finds zero mentions of the deleted migration doc and zero operator-facing references to the removed env-var. Lands in WAVE 2 because RESEARCH §"Strict ordering constraint 1" requires the file to be deleted (Plan 04) BEFORE the scrub — otherwise the docs go through a mid-state where they reference a deleted file.

Output: Four file edits, ~50 lines of doc deletions/rewrites across README + ERROR-STYLE + LIBRARY-MODE + EXTENDING.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md
@.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md
@README.md
@docs/ERROR-STYLE.md
@docs/LIBRARY-MODE.md
@docs/EXTENDING.md
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator reading docs -> docs tree | Operator follows doc breadcrumbs; broken/stale references erode trust |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-31-05-01 | Information Disclosure (LOW) | Stale env-var docs lead operators to set `MCPTF_CONFIG_FILE` and expect it to work | mitigate | This plan's scrub completes the operator-facing surface removal; combined with Plan 02's D-06 loud DeprecationWarning, operators get clear "this no longer works" signal in both the docs and at runtime. |
| T-31-05-02 | Repudiation (INFORMATIONAL) | LIBRARY-MODE's deleted migration section was the operator-visible record of the v1.4 -> v1.5 deprecation timeline | accept | Git history preserves the deletion; CONTEXT.md §"Deferred Ideas" notes optional CHANGELOG capture as backlog. |

ASVS classification: N/A (pure doc edits). Phase has no HIGH threats.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Scrub README.md and docs/EXTENDING.md MCPTF_CONFIG_FILE + MIGRATION cross-references</name>
  <files>README.md, docs/EXTENDING.md</files>
  <read_first>
    - README.md (focus L73, L331, L343, L350, L609 per RESEARCH; read entire file or at minimum surrounding context of each line)
    - docs/EXTENDING.md (focus L211)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md §"Doc / Config-File Inventory"
  </read_first>
  <behavior>
    - `grep -n 'MCPTF_CONFIG_FILE' README.md` returns zero matches.
    - `grep -n 'MIGRATION-v1-to-v2' README.md` returns zero matches.
    - `grep -n 'MCPTF_CONFIG_FILE' docs/EXTENDING.md` returns zero matches.
    - README still has working operator-facing copy describing the two surviving config routes (`--config PATH` for CLI; `mcp_config_file` ini key for library mode); rewrites do not leave the file in a state that says "to configure, do X" where X is broken.
    - Any "migration from MCPTF_CONFIG_FILE" callout in README is REPLACED with a direct anchor / link to the surviving routes (or simply deleted if the surrounding copy still makes sense without it).
  </behavior>
  <action>
    Per RESEARCH §"Doc / Config-File Inventory":

    **README.md** — five sites to address (L73, L331, L343, L350, L609 per RESEARCH; verify against current HEAD). For each:
    - If the line is a passing mention (`"or set MCPTF_CONFIG_FILE=..."`), REMOVE the env-var clause. Surrounding sentence should make sense without it.
    - If the line is a section header or callout about migration FROM `MCPTF_CONFIG_FILE` to `mcp_config_file`, DELETE the section. The migration is complete; no operator needs the v1.4->v1.5 walkthrough now.
    - If the line references `docs/MIGRATION-v1-to-v2.md`, DELETE the reference. After Plan 04 the file does not exist.

    Be careful at L73 — RESEARCH does not characterize the surrounding context; read it and decide whether the removal leaves the paragraph coherent. If the paragraph degrades, rewrite it to reference the surviving two routes (`--config` for CLI, `mcp_config_file` ini key for library mode) explicitly.

    **docs/EXTENDING.md L211** — scrub the reference to `"MCPTF_CONFIG_FILE / --config"`. Replace with `--config` only. Verify the surrounding context after edit (likely a section about how to point `extending` consumers at custom configs; the env-var alternative is no longer offered).

    Do NOT touch ERROR-STYLE.md or LIBRARY-MODE.md in this task — Task 2 handles those.
  </action>
  <verify>
    <automated>uv run python -c "import subprocess; r1=subprocess.run(['grep','-c','MCPTF_CONFIG_FILE','README.md'], capture_output=True, text=True); r2=subprocess.run(['grep','-c','MIGRATION-v1-to-v2','README.md'], capture_output=True, text=True); r3=subprocess.run(['grep','-c','MCPTF_CONFIG_FILE','docs/EXTENDING.md'], capture_output=True, text=True); print('README MCPTF:', r1.stdout.strip()); print('README MIGRATION:', r2.stdout.strip()); print('EXTENDING MCPTF:', r3.stdout.strip()); assert r1.stdout.strip() in ('0',''); assert r2.stdout.strip() in ('0',''); assert r3.stdout.strip() in ('0',''); print('OK clean')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n 'MCPTF_CONFIG_FILE' README.md` returns zero matches.
    - `grep -n 'MIGRATION-v1-to-v2' README.md` returns zero matches.
    - `grep -n 'MCPTF_CONFIG_FILE' docs/EXTENDING.md` returns zero matches.
    - `grep -n 'mcp_config_file' README.md` returns at least one match (the surviving library-mode route is documented).
    - `grep -n 'config' README.md` returns at least one match describing the surviving CLI route.
    - README passes basic markdown lint (no dangling section anchors / TOC entries pointing at deleted sections).
  </acceptance_criteria>
  <done>
    README and EXTENDING contain no operator-facing env-var or migration-doc references; the surviving two routes are still documented.
  </done>
</task>

<task type="auto">
  <name>Task 2: Rewrite docs/ERROR-STYLE.md SAFE-06 reference message + delete docs/LIBRARY-MODE.md migration section</name>
  <files>docs/ERROR-STYLE.md, docs/LIBRARY-MODE.md</files>
  <read_first>
    - docs/ERROR-STYLE.md (entire file - small; focus L57-73 SAFE-06 reference message section)
    - docs/LIBRARY-MODE.md (focus L14, L118, L293-315 per RESEARCH)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md (D-11 verbatim v1-rejection wording)
    - src/mcp_test_framework/cli.py (verify the D-11 wording committed by Plan 03 - this task SYNCHRONIZES ERROR-STYLE.md's reference message body with cli.py's actual output)
  </read_first>
  <behavior>
    - `docs/ERROR-STYLE.md` reference message section "Config uses an older schema version" (L57-73) is REWRITTEN to carry the D-11 verbatim wording (matching what cli.py renders post-Plan-03), OR is DELETED if the rewriter judges it no longer adds operator value.
    - `docs/ERROR-STYLE.md` contains no `docs/MIGRATION-v1-to-v2.md` reference.
    - `docs/ERROR-STYLE.md` reference message contains no `opt-in`, `opt-out`, `the difference matters`, `in v1 a tool with no entry`, `migration walkthrough`.
    - `docs/LIBRARY-MODE.md` has no `## Migration from MCPTF_CONFIG_FILE env var` section.
    - `docs/LIBRARY-MODE.md` L14 and L118 mentions of `MCPTF_CONFIG_FILE` are scrubbed.
    - `grep -n 'MCPTF_CONFIG_FILE' docs/LIBRARY-MODE.md` returns zero matches.
    - `grep -n 'MIGRATION-v1-to-v2' docs/LIBRARY-MODE.md` returns zero matches.
  </behavior>
  <action>
    Two-file edit. Both small and mechanical.

    **File 1: docs/ERROR-STYLE.md**

    Locate the section header "### Config uses an older schema version" (around L57-73 per RESEARCH). The current body of this reference message is the pre-V1DROP-03 text (carries `docs/MIGRATION-v1-to-v2.md` reference + v1-vs-v2 walkthrough language).

    Decide between TWO options based on judgment:

    **Option A** - REWRITE the reference message to the D-11 verbatim text (sync with what cli.py now renders post-Plan-03):

        ### Config uses an older schema version

            unsupported config version <version>

            this build supports schema version 2.
            your config declares version <version>, which is no longer accepted.

            next: run `mcp-contracts config-init -o config.yaml` to generate a
                  current scaffold

    **Option B** - DELETE the entire section. The D-11 text is generic enough that pinning it in ERROR-STYLE.md as a reference-message exemplar may be over-pinning. The other reference messages in the file ("No config found, framework refuses to run") stay; only this section goes. Adjust the surrounding doc structure (table of contents, neighbor headings) accordingly.

    **Recommendation:** Option A is safer (preserves the operator-facing reference shape for future editors); Option B is cleaner. Pick one and execute.

    Also scrub any other reference inside ERROR-STYLE.md to `MIGRATION-v1-to-v2.md` (the file is deleted; references break). After edit, `grep -n 'MIGRATION' docs/ERROR-STYLE.md` should return zero matches (or only matches inside the deleted section's residual TOC entry - clean those up too).

    **File 2: docs/LIBRARY-MODE.md**

    Three sites per RESEARCH:

    1. **L14** - scrub passing mention of `MCPTF_CONFIG_FILE`. Read surrounding context; replace with `mcp_config_file` ini-key reference OR remove the mention if the sentence still parses.

    2. **L118** - same scrub treatment as L14.

    3. **L293-315** - DELETE the entire `## Migration from MCPTF_CONFIG_FILE env var` section (23 lines per RESEARCH). The section documents v1.4->v1.5 migration which is now complete (no live operators exist). Adjust the surrounding doc structure (TOC, anchors, neighbor sections) accordingly.

    After edit, `grep -n 'MCPTF_CONFIG_FILE' docs/LIBRARY-MODE.md` MUST return zero matches AND `grep -n 'MIGRATION-v1-to-v2' docs/LIBRARY-MODE.md` MUST return zero matches.
  </action>
  <verify>
    <automated>uv run python -c "import subprocess; checks = [('docs/ERROR-STYLE.md','MIGRATION-v1-to-v2'),('docs/ERROR-STYLE.md','opt-in tool selection'),('docs/LIBRARY-MODE.md','MCPTF_CONFIG_FILE'),('docs/LIBRARY-MODE.md','MIGRATION-v1-to-v2')]; errors=[]\nfor f,p in checks:\n  r=subprocess.run(['grep','-c',p,f], capture_output=True, text=True); n=r.stdout.strip(); print(f, p, '->', n);\n  if n not in ('0',''): errors.append((f,p,n))\nassert not errors, errors\nprint('OK clean')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n 'MIGRATION-v1-to-v2' docs/ERROR-STYLE.md` returns zero matches.
    - `grep -n 'opt-in tool selection' docs/ERROR-STYLE.md` returns zero matches.
    - `grep -n 'opt-out' docs/ERROR-STYLE.md` returns zero matches (inside the rewritten/deleted SAFE-06 section).
    - `grep -n 'MCPTF_CONFIG_FILE' docs/LIBRARY-MODE.md` returns zero matches.
    - `grep -n 'MIGRATION-v1-to-v2' docs/LIBRARY-MODE.md` returns zero matches.
    - `grep -n 'mcp_config_file' docs/LIBRARY-MODE.md` returns at least one match (the surviving ini-key route is still documented).
    - If Option A taken: `grep -n 'unsupported config version' docs/ERROR-STYLE.md` returns at least one match.
    - If Option B taken: `grep -n 'Config uses an older schema version' docs/ERROR-STYLE.md` returns zero matches (the section header is gone).
  </acceptance_criteria>
  <done>
    ERROR-STYLE.md SAFE-06 reference message is either rewritten to D-11 or deleted; LIBRARY-MODE.md migration section is deleted and env-var mentions scrubbed.
  </done>
</task>

</tasks>

<verification>
Phase-level checks after both tasks complete:

1. `grep -rn 'MCPTF_CONFIG_FILE' README.md docs/` returns zero matches.
2. `grep -rn 'MIGRATION-v1-to-v2' README.md docs/` returns zero matches.
3. `grep -rn 'opt-in tool selection\|in v1 a tool with no entry\|the difference matters' docs/` returns zero matches.
4. Manual operator-experience check: open README in a markdown viewer, follow the "how to configure" trail - the operator reaches `--config PATH` (CLI) and `[tool.pytest.ini_options] mcp_config_file = PATH` (library) with no broken links and no env-var detours.
</verification>

<success_criteria>
- Both tasks' acceptance criteria met.
- Operator reading docs sees a single coherent two-route config story (CLI `--config`, library `mcp_config_file` ini key).
- No surviving doc reference to the deleted `docs/MIGRATION-v1-to-v2.md` (Plan 04 deleted the file; this plan completes the cross-ref scrub).
- No surviving operator-facing doc reference to `MCPTF_CONFIG_FILE` (Plan 02 unwired the env var; this plan completes the doc scrub).
</success_criteria>

<output>
After completion, create `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-05-SUMMARY.md`
</output>
