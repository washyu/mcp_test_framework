"""Regression gate: no planning-system requirement IDs may appear in src/mcp_test_framework/.

The locked regex below is the single source of truth for what counts as a leak.
Documented in .planning/phases/22-scrub-requirement-id-leaks-from-src/22-CONTEXT.md
decision D-05.

Phase NN prefixes are deliberately NOT in the regex (per D-06): "Phase \\d+" can
legitimately appear in operator-facing prose (error messages, changelogs); the
Phase NN scrub is a one-time discipline executed in the Phase 22 PR and not
enforced thereafter, because TAG-NN/D-NN anchors typically co-occur with a
Phase NN prefix and the regex catches the former.

Policy: 22-CONTEXT.md D-04 (hard zero, no allowlist, no per-file exemptions).
"""

from __future__ import annotations

import re
from pathlib import Path


# LOCKED REGEX (D-05 single source of truth -- do NOT edit without updating
# 22-CONTEXT.md and the Phase 22 SUMMARY).
_LEAK_RE = re.compile(
    r"(CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB|RELOC)-\d+|\bD-\d+\b"
)

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "mcp_test_framework"


def test_no_planning_ids_in_src() -> None:
    """Every .py file under src/mcp_test_framework/ must be free of planning-ID leaks."""
    assert _SRC_ROOT.is_dir(), (
        f"src root not found at {_SRC_ROOT!r} -- path resolution broken; "
        "fix the `parents[N]` index in test_no_planning_ids_in_src.py"
    )
    offenders: list[str] = []
    for py_path in sorted(_SRC_ROOT.rglob("*.py")):
        if "__pycache__" in py_path.parts:
            continue  # D-07: skip .pyc cache (defense-in-depth; rglob already excludes .pyc)
        text = py_path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if _LEAK_RE.search(line):
                rel = py_path.relative_to(_SRC_ROOT.parent.parent)
                offenders.append(f"  {rel}:{line_no}: {line.strip()}")
    assert not offenders, (
        "Planning-system requirement IDs leaked back into src/mcp_test_framework/.\n"
        "Locked regex: "
        "(CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB|RELOC)-\\d+|\\bD-\\d+\\b\n"
        "Policy: 22-CONTEXT.md D-04 (hard zero, no allowlist).\n"
        "Offending sites:\n" + "\n".join(offenders)
    )
