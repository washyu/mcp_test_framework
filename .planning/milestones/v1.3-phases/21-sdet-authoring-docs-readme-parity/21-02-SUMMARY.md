---
phase: 21-sdet-authoring-docs-readme-parity
plan: "02"
subsystem: docs
tags: [docs, readme, sdet, snapshot, fail-sample, seed-022]
dependency_graph:
  requires:
    - "21-01: docs/SDET-AUTHORING.md exists as the cross-link target"
    - "19-04: ProxmoxVmLifecycleState pattern, dogfood VMID range convention, _sweep_strands pattern"
    - "20-04: tests/sdet/ baseline state (only __init__.py + conftest.py)"
    - "14-xx: per-tool group + nested rows domain UI (renderer output mirrored verbatim)"
  provides:
    - "README.md '## SDET scenarios' H2 with embedded char-for-char renderer snapshot"
    - "Cross-links from README to docs/SDET-AUTHORING.md (5 link instances in body)"
  affects:
    - "Plan 21-04 (end-of-phase verification sweep) — verifies the new H2 position and link integrity"
tech_stack:
  added: []
  patterns:
    - "Phase 16 doc-mirroring pattern: manual snapshot of renderer output at phase commit time, with HTML-comment pointer to re-capture cue"
    - "FAIL output as the README sample (re-scope from PASS): demonstrates the framework surfacing real upstream contract bugs rather than masking them — SEED-022 narrative reinforcement"
key_files:
  created: []
  modified:
    - README.md
  deleted:
    - tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py
decisions:
  - "Re-scoped Task 2 acceptance criteria at operator direction: live Proxmox run FAILED with the upstream homelab-mcp inputSchema bug ('Input validation error: None is not of type string') hitting create_proxmox_vm in addition to manage_proxmox_vm. Per Task 2 fail-handling clause: 'we revisit'. Operator chose option (a) embed FAIL output as the sample — strong SEED-022 narrative: 'the framework surfaces upstream contract bugs as test failures.' README intro paragraph and closing paragraph now explicitly frame the failure as expected framework behavior and cross-link to docs/SDET-AUTHORING.md for the _CpuBumpManageVmParams workaround."
  - "Code block trimmed from the 184-line Task 1 source to ~50 lines: kept dataclass + module-scope fixture (with try/yield/finally teardown) + 2 tests; elided sweep helpers and _next_free_readme_vmid (those are advanced patterns, full pattern lives in docs/SDET-AUTHORING.md). Reader sees the essential module-scope-state pattern, not the operational helpers."
  - "Replaced all `proxmox_vm_lifecycle_readme_sample` occurrences with `proxmox_vm_lifecycle` in both code block and output block per Task 3 step 4. README sample reads as generic, not as the temp artifact."
  - "Phase 19-04 inputSchema bug DID recur and DID hit the create call this time — Phase 19-04 Finding 2's prediction that create was 'safe' did not hold. Recommend recording in v1.3 close + reconsidering whether the v1.4 hello-world MCP fixture should be promoted up the roadmap to remove the upstream-dependency risk from SDET sample work."
metrics:
  duration: "~25min (incl. operator UAT cycle + re-scope decision)"
  completed: "2026-05-13"
  tasks_completed: "4 (Task 2 re-scoped at human-verify checkpoint)"
  files_created: 0
  files_modified: 1
  files_deleted: 1
  commits: 3
artifacts:
  - path: README.md
    line_range: "260–432"
    summary: "New '## SDET scenarios' H2 — intro framing the FAIL case, Python source code block, literal text snapshot, two closing paragraphs (link to docs/SDET-AUTHORING.md + --sdet invocation pointer)"
verification:
  acceptance_criteria_passed: "Task 1 (8/8), Task 3 (10/11 — '✓' rows substituted with '✗' rows per operator-approved re-scope), Task 4 (6/6)"
  src_changes: 0
  planning_path_leaks_in_readme_section: 0
  position_check: "## SDET scenarios at line 260, between ## Sample green run (213) and ## Isolation guarantee (433) — D-15 placement OK"
  link_check: "5 references to docs/SDET-AUTHORING.md in README (1 in '## Further reading' from Plan 21-01, 4 in new section: intro, closing, comment-near-code, invocation hint)"
followups:
  - "Phase 21-04 verification sweep should confirm the renamed Result line still matches the regex '^Result: \\d+ PASS / \\d+ FAIL / \\d+ SKIP'"
  - "v1.3 close: consider documenting the inputSchema-bug recurrence pattern in a project memory file"
  - "v1.4+: hello-world MCP fixture work may be more urgent than v1.3 roadmap suggests — every doc phase that needs a live SUT run is at risk of this same re-scope cycle"
---

# Plan 21-02 — README "## SDET scenarios" snapshot (re-scoped to FAIL sample)

## Summary

Added a new `## SDET scenarios` H2 to README between `## Sample green run` and
`## Isolation guarantee`. The section contains a trimmed Python source sample
(dataclass + module-scope yield fixture + 2 async tests) and the literal
renderer output from a live Proxmox run, plus closing prose pointing readers
at `docs/SDET-AUTHORING.md` for the full authoring walkthrough.

The plan called for a 2 PASS / 0 FAIL sample. The live run instead surfaced
the upstream `homelab-mcp` `inputSchema` bug on both `create_proxmox_vm` and
`delete_proxmox_vm` (the bug pattern Phase 19-04 first identified on
`manage_proxmox_vm` — it has spread further than expected). At the
`checkpoint:human-verify` gate the operator chose to embed the FAIL output
as the sample, with framing prose making the SEED-022 story explicit:
**the framework's role is to surface upstream contract bugs as test failures,
not to mask them.** The new section now opens with that framing, shows the
FAIL rows verbatim from the runner, and closes with a pointer to the
`_CpuBumpManageVmParams(extra="allow")` workaround in
`docs/SDET-AUTHORING.md`.

## What changed

- `README.md`: new 173-line `## SDET scenarios` H2 (intro paragraph + code
  block + output block + two closing paragraphs).
- `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py`: deleted via
  `git rm`; tests/sdet/ is back to Phase 20-04 baseline.

## Commits

- `b5c1ace` — test(21-02): scaffold temp 2-test Proxmox VM-lifecycle scenario for README snapshot
- `50b5ce1` — docs(21-02): insert '## SDET scenarios' H2 with embedded FAIL snapshot
- `6b77fe5` — test(21-02): delete temp readme-sample scenario after snapshot capture

## Re-scope note (Task 2 deviation)

Task 2 acceptance criteria required `Result: 2 PASS / 0 FAIL` and prescribed
"abort and re-scope" on failure. Live run produced
`Result: 0 PASS / 2 FAIL / 58 SKIP  in 6.2s`. Operator chose to ship the
FAIL output as the sample (option a, "embed FAIL output") rather than
substituting a different tool, deferring the H2, or spiking the inputSchema
workaround. Justification:

1. Strong narrative alignment with SEED-022 (framework primitives; SDET owns
   safety) — the FAIL sample makes the framework's responsibility visible.
2. Realistic operator experience — readers see what they'll actually see
   when running against any MCP server with contract bugs.
3. The cross-link to `docs/SDET-AUTHORING.md` directly answers the reader's
   natural next question ("how do I work around this?").

## Outstanding observations for v1.3 close

The Phase 19-04 prediction that `create_proxmox_vm` was safe from the
inputSchema bug did not hold. The upstream surface is wider than the Phase
19-04 finding indicated. Consider:

- Recording the inputSchema-bug recurrence pattern in a project memory file
  so future SDET-sample work plans for it from the start.
- Promoting the v1.4 hello-world MCP fixture up the roadmap — every doc
  phase that requires a live SUT run is at risk of this same re-scope cycle.
