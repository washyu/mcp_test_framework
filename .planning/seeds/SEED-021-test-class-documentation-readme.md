---
id: SEED-021
status: dormant
planted: 2026-05-12
planted_during: Phase 17 planning (post v1.3 milestone open, after SEED-019/020 supersession and architectural principle SEED-022)
trigger_when: Phase 21 (SDET authoring docs + README parity) scoping — natural home. Surface during /gsd-new-milestone if any milestone mentions: "README", "docs", "SDET onboarding", "test class documentation", "judge behavior", or "explain what each test does"
scope: Small
related_seeds: [SEED-022 (architectural principle this docs work explains), SEED-008 (reporter UX overhaul — adjacent doc concerns), SEED-014 (programmatic SDET authoring — Phase 21 already partially scoped here)]
target_phase: 21 (v1.3 SDET authoring docs + README parity)
---

# SEED-021: Document per-test-class safety profile in README

## Why This Matters

The architectural principle locked 2026-05-12 (SEED-022) puts the safety
decision squarely on the SDET: the framework provides primitives, the SDET
decides which tools to opt into which test classes. **That principle only
works if the SDET understands what each test class actually does to the
SUT.**

Today the safety story is hidden in the source. An SDET reading the
README can't tell from the surface description whether opting
`delete_everything_forever` into the `clarity` judge would call the tool
(it wouldn't — judges are pure description analysis), or whether opting
it into `output_conformance` would (it would — that's a wire call).

That ambiguity is exactly the kind of thing that produces the
"i don't really have a decent test enviroment setup" pain — SDETs default
to opting into nothing because they can't reason about safety from the
docs.

The fix is documentation, not code. The framework already has the right
shape (opt-in per tool per judge); the README just needs a table that
makes the safety profile explicit per test class.

## When to Surface

**Trigger:** Phase 21 (SDET authoring docs + README parity) scoping.
This seed fits naturally into Phase 21's existing goal — "a new SDET
arriving at the repo finds a step-by-step authoring walkthrough" — by
adding "...and understands which test classes are safe-by-construction
vs operator-judged."

Surface during `/gsd-new-milestone` if any milestone mentions: README,
docs overhaul, SDET onboarding, or "explain what the judges do."

## Scope Estimate

**Small** — half a day. Concrete deliverable: one README section,
sample config snippets, and updated `config-init` output that points
to the new docs.

### 1. README section: "Test Classes and Safety Profiles"

Required table (verbatim shape, not just outline):

| Test class | Calls the tool? | Side effects on SUT | When to opt in |
|-----------|-----------------|---------------------|----------------|
| Schema validation (structural) | No | None | Every tool with `inputSchema` and/or `outputSchema` |
| Description: clarity | No — analyzes text only | None | Every tool that has a `description` field |
| Description: disambiguation | No — analyzes text only | None | Every tool that has a `description` field |
| Description: parameters | No — analyzes schema only | None | Every tool with `inputSchema` |
| Output conformance | **Yes** — sends a real wire call with `example_args` | Whatever the tool's normal call does | Only when the SDET has decided the tool is safe to call with the configured args |

A one-paragraph explainer per class follows the table:

- **Schema validation:** "Reads `inputSchema` / `outputSchema` and asserts
  Draft 2020-12 validity. Never touches the SUT. Safe for every tool
  including destructive ones."
- **Description judges:** "Feed the tool's `description` (and for
  `parameters`, the `inputSchema`) to a local Ollama judge with a 1–5
  rubric. The judge never sees a real call result; it only reasons about
  the text. Safe for every tool — opting `delete_user` into clarity
  judging cannot delete anything."
- **Output conformance:** "Sends a real tool call using `example_args`
  from config and asserts `isError == False` plus optional response-shape
  judging. This is the only test class that touches the SUT. The SDET's
  act of providing `example_args` is the safety judgment — the framework
  assumes the SDET would not have written down args for a tool they
  didn't want called."

### 2. Sample SDET workflows in the README

Two or three short walkthroughs covering:
- "I want description-quality coverage of all 58 tools without calling
  any of them" — opt every tool into description judges only.
- "I want to assert one read-only tool returns the right shape" — opt
  the tool into output_conformance + provide `example_args`.
- "I want to test a destructive tool" — write a hand-authored SDET test
  file (Phase 18 surface) with explicit setup/teardown; do NOT use
  output_conformance.

### 3. `config-init` emits a comment-prefixed reminder

When `mcp-test-framework config-init` generates a new config, the
emitted `tools:` block opens with a comment:
```yaml
# All tools are opt-in. Description judges (clarity/disambiguation/parameters)
# are safe for every tool — they never call the SUT. Only output_conformance
# sends a real wire call; opt in only for tools you've decided are safe to
# invoke with the example_args you provide. See README §Test Classes for the
# full safety table.
tools:
  ...
```

That puts the principle in front of the SDET at the moment they're
making the decision.

### 4. Cross-reference in error messages

When a test is skipped because a tool was opted into
`output_conformance` without `example_args`, the skip reason links to
the README section:
```
SKIPPED create_proxmox_vm — output_conformance requires example_args (missing: node, vmid)
        See README §Test Classes and Safety Profiles for guidance on opt-in.
```

## Breadcrumbs

Related code (verified present 2026-05-12):
- `README.md` — current docs. Audit for any leftover language implying
  the framework "automatically tests" tools or has built-in safety
  classification (which the architectural principle SEED-022 explicitly
  rejects).
- `src/mcp_test_framework/cli.py::config-init` — where the emitted
  config template lives. Add the comment header described above.
- `config.example.yaml` — operator-facing sample. Should match the
  README's worked examples after this seed lands.
- The three description judges (clarity / disambiguation / parameters)
  in the source — confirm their docstrings match the README's "no wire
  call" claim. Pin in a unit test that imports each judge and asserts
  `calls_tool == False` if that attribute exists, or equivalent.

Related decisions:
- **SEED-022** (architectural principle) — this seed exists to make
  SEED-022's principle legible to SDETs. Without SEED-021, the
  principle is true in code but invisible in docs.
- v1.2 opt-in design — `tools:` is an allowlist. SEED-021 documents
  the safety implications of that opt-in surface.
- Memory note: "doc scrub (v1.2)" — README/config.example/EXTENDING.md
  still leak homelab-mcp specifics and stale phase IDs. Phase 21 will
  scrub those at the same time; SEED-021 is one specific addition to
  that scrub.

Related seeds:
- **SEED-022** — the principle this seed documents.
- **SEED-008** (reporter UX overhaul) — adjacent docs work; both feed
  Phase 21.
- **SEED-018** (example_args manifest) — sibling. SEED-018 adds the
  ergonomic shortcut; SEED-021 explains when an SDET should use it.

## Notes

Captured 2026-05-12 immediately after the user articulated the
architectural principle (SEED-022). The user's own framing was the
trigger:

> "we just need to also make sure we have a good description of the
> what the judges do in the readmes so sdet/developers know what safe."

This is the smallest possible seed that closes the documentation half
of the principle. It belongs in Phase 21 and probably adds half a day
to that phase's existing scope — well under the threshold for needing a
new phase. No replanning required; just expand Phase 21 when planning
it.
