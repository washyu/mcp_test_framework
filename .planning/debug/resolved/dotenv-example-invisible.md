---
status: diagnosed
trigger: "Phase 12 UAT Test 5 — operator reported '.env.example' not visible in workspace file browser"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
---

## Current Focus

hypothesis: The file is fine; discoverability is the actual bug. The operator walkthrough (docs/EXTENDING.md) never mentions .env.example exists, so an operator following Persona-01 has no signal that the file is part of their workflow. The file-browser visibility issue is downstream of the documentation gap.
test: grep EXTENDING.md for .env(.example); confirm README references; check for editor config that hides dotfiles
expecting: zero mentions in EXTENDING.md (canonical walkthrough); README mentions only as a "cp" step with no framing
next_action: return diagnosis to caller

## Symptoms

expected: .env.example is visible/discoverable to an operator opening the workspace in their editor
actual: "i don't see the .env.example file in the file browser for this workspace"
errors: none
reproduction: Phase 12 UAT Test 5 — operator was asked to open .env.example and reported they couldn't see it in the workspace file browser
started: discovered 2026-05-09 during UAT

## Eliminated

- hypothesis: file is gitignored or missing
  evidence: ls -la shows -rw-r--r-- 807 bytes May 9 09:33 .env.example at repo root; .gitignore contains `.env` (no asterisk, no `.env.example` entry)
  timestamp: 2026-05-09

- hypothesis: in-repo editor config hides dotfiles
  evidence: no .vscode/ or .idea/ directories exist in the worktree; both are listed in .gitignore as folders the project does not commit; therefore no in-repo settings.json could be hiding dotfiles
  timestamp: 2026-05-09

## Evidence

- timestamp: 2026-05-09
  checked: ls -la at repo root + .gitignore content
  found: .env.example exists (807 bytes), and .gitignore line 13 is `.env` (literal — does NOT match `.env.example` because gitignore does not glob suffix)
  implication: file is committed, tracked, present on disk — not a git/filesystem invisibility issue

- timestamp: 2026-05-09
  checked: grep "\.env\.example" docs/EXTENDING.md
  found: ZERO matches. The canonical operator walkthrough ("Testing an MCP server you didn't write" Steps 1–4) makes no reference to .env.example, .env, environment variables, or CI secrets at all.
  implication: an operator following the prescribed PERSONA-01 walkthrough never has reason to look for .env.example; the file is discoverability-orphaned from the operator entry point.

- timestamp: 2026-05-09
  checked: README.md references to .env.example
  found: 4 mentions — line 25 (Prerequisites: ".env.example default" for uvx), line 32 (Setup: `cp .env.example .env`), line 85–86 (config table notes "ships uvx" defaults), line 91 ("Copy .env.example to .env and edit"). All are imperative ("copy this") with no signposting that the file is structurally optional under v1.1's "env vars no longer override config" model.
  implication: README mentions exist but treat .env.example as a Setup-step artifact, not as the CI-secret passthrough it now is. EXTENDING.md (the canonical operator walkthrough) carries the operator workflow forward without re-mentioning it.

- timestamp: 2026-05-09
  checked: actual .env.example content (12 lines including blanks)
  found: file is correctly framed as "CI-secret passthrough only" — explicitly says "env vars no longer override config values" and points the operator at `mcp-test-framework config-init -o config.yaml` for actual configuration. JUDGE_API_KEY is shown as the canonical example (commented). MCPTF_CONFIG_FILE hint preserved.
  implication: the file's CONTENT correctly matches Test 5's expected truth. Test 5's failure is purely about visibility/discoverability, NOT about content correctness. The README still tells the operator to `cp .env.example .env` — which contradicts the file's own "env vars no longer override config" framing and creates onboarding confusion.

- timestamp: 2026-05-09
  checked: no in-repo editor workspace config exists
  found: no .vscode/ directory; no .idea/ directory; both are gitignored anyway. Repo ships nothing that would tell an editor to hide or show dotfiles.
  implication: there is currently no repo-level lever to surface .env.example in editor file browsers. The repo does NOT ship a .vscode/settings.json (which could set "files.exclude": {} to explicitly show dotfiles) — adding one is a viable in-repo mitigation.

## Resolution

root_cause: |
  This is NOT a code defect. The file exists, is tracked, and has correct content. The reported "I don't see .env.example in the file browser" is a discoverability failure with two reinforcing causes:

  1. (Primary, in-repo fixable) docs/EXTENDING.md — the canonical PERSONA-01 walkthrough — has zero mentions of .env.example. An operator who follows the prescribed entry point (README → "Testing an MCP server you didn't write" → EXTENDING.md walkthrough) is never told the file exists, what it's for, or when they would touch it. So even when the file IS visible in the editor, the operator has no reason to look at it; when it's NOT visible (filtered, collapsed, or off-screen in a long file list), the operator has no model to seek it out.

  2. (Secondary, environmental, not in-repo fixable) The user's editor file browser likely filters or hides dotfiles by default, OR the user is viewing a different cwd than the repo root (the worktree-based GSD workflow places work in .claude/worktrees/{name}/, and the user may have been browsing a different worktree from the one Test 5 referenced). The repo currently ships no .vscode/settings.json or equivalent to override editor dotfile-hiding defaults.

  The README does mention .env.example four times — but always as an imperative Setup step ("cp .env.example .env"), which contradicts the file's own v1.1 framing ("env vars no longer override config"). This is itself a documentation drift: README treats .env.example as required setup, EXTENDING.md treats it as nonexistent, and the file's own header says it's optional CI-secret passthrough.

fix: not yet applied (find_root_cause_only mode)
verification: not yet applied
files_changed: []
