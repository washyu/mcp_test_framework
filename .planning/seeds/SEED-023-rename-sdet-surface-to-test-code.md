---
id: SEED-023
status: dormant
planted: 2026-05-13
planted_during: Phase 17 live UAT — operator asked whether "SDET" framing should be "test-code classes/wrappers" and the command renamed to e.g. `gen-test-stubs` / `gen-test-classes`. Deferred to v1.4 scoping to avoid Phase 17 UAT delay.
trigger_when: /gsd-new-milestone for v1.4 (or earlier if any milestone mentions "rename SDET", "test-code", "developer ergonomics", "API surface review", or "public-API naming"). Also surface if the framework starts attracting external users who aren't familiar with the SDET role term.
scope: Medium-Large
related_seeds: [SEED-021 (test class docs — also touches naming/persona), SEED-022 (framework primitives principle — uses SDET term in its definition)]
target_phase: v1.4 scoping (probably its own dedicated rename phase before any new public-API expansion lands)
---

# SEED-023: Rename "SDET" surface to "test-code" / "test-classes"

## Why This Matters

"SDET" (Software Development Engineer in Test) is a real industry role term,
but it's not universal — many test/automation shops use "test engineer",
"automation engineer", "QA developer", "tooling engineer". Tying the public
API surface to one specific persona-role name (instead of the function it
performs — "test-code", "test-classes", "tool-wrappers") creates friction
for adoption outside shops that use that term.

The operator who is the primary v1.3 user surfaced this concern unprompted
during the very first Phase 17 live UAT — strong signal that the name reads
strangely from the outside.

## Trigger Conditions

Promote this seed when ANY of:

- /gsd-new-milestone for v1.4 scoping (natural breakpoint — SDET-named
  surfaces from Phase 18-21 will have landed; rename before they harden
  into "public-API-this-can't-change" territory)
- Anyone mentions "API surface rename", "developer ergonomics", "public-API
  naming", "test-code", "first impression for new users"
- The framework starts attracting external contributors / users who aren't
  in homelab-mcp's immediate orbit

## What's In Scope (blast radius captured 2026-05-13)

**Code:**
- `src/mcp_test_framework/sdet/` → `src/mcp_test_framework/test_code/` (or chosen successor)
- `src/mcp_test_framework/sdet/generated/` → `.../test_code/generated/`
- `gen-sdet-classes` Typer command → `gen-test-classes` (NOT `gen-test-stubs` — `<Tool>Params` are fully-typed, not stubs; only outputSchema-undeclared Responses are pass-stubs)
- `tests/sdet/` test discovery scope (lands in Phase 18) → `tests/test_code/`
- `--sdet` flag on `run` (lands in Phase 18) → `--test-code` (or rename whole concept)
- Generated file imports: `from mcp_test_framework.sdet import ToolResponse` → `from mcp_test_framework.test_code import ToolResponse`

**Requirements:**
- `SDET-01..04` → `TESTCODE-01..04` (or similar)
- `DOC-SDET-01..03` → `DOC-TESTCODE-01..03`
- Keep `CODEGEN-01..06` (those name the mechanism, not the persona — OK as-is)

**Docs:**
- `docs/SDET-AUTHORING.md` (Phase 21 deliverable, may not exist yet — name TBD if rename lands first) → `docs/TEST-CODE-AUTHORING.md`
- README "SDET" mentions
- CLAUDE.md "dual-persona" note (Phase 21 deliverable)

**Planning artifacts:**
- Phase 18/19/21 roadmap titles
- Memory entries: "Vibe-coded MCP persona", "Framework primitives; SDET owns safety (SEED-022)"
- SEED-021, SEED-022 references to "SDET"

## What's NOT In Scope (deliberate)

- The "operator + tester" dual-persona framing itself — that's good design
  (operators run the framework, testers extend it). Just rename the tester
  role from "SDET" to something more universal.
- `CODEGEN-01..06` requirement IDs — those name the mechanism, not the
  persona, and survive the rename unchanged.
- Phase 17 code (already shipped 2026-05-13) — rename via Phase 22 scrub
  if it lands first, or as part of the dedicated rename phase if not.

## Pitfalls

- **Don't bikeshed the successor term.** Decide once. Candidates collected
  2026-05-13: "test-code", "test-classes", "tool-wrappers", "client-classes",
  "test-bindings". Operator's intuition was "test-code classes/wrappers" —
  start there.
- **Coordinate with Phase 22 (src/ scrub).** If Phase 22 lands BEFORE this
  rename, plan it as the scrub-AND-rename pass to avoid touching the same
  files twice. If Phase 22 ships first with SDET names intact, this rename
  is the second pass.
- **Don't rename `gen-sdet-classes` → `gen-test-stubs`.** "Stubs" implies
  placeholder-for-future-implementation. The Params classes are fully-typed
  and usable as-is; only outputSchema-undeclared Response classes are true
  `pass`-stubs. `gen-test-classes` reads accurately.

## Predecessor Note

Operator's instinct on the command name (`gen-test-stubs`) surfaced 2026-05-13
during Phase 17 UAT and was deferred to avoid scope-creep into the verification
gate. The "stubs" vs "classes" distinction is captured here so the rename phase
doesn't relitigate.
