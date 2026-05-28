"""RENAME-06 acceptance gate: scan operator-facing surfaces for residual `sdet` terminology and planning-ID leaks.

Implements D-17 patterns + D-16 scope + D-18 exclusions for the Phase 25 public-API rename.
Survives v1.5 — the grandfathered hard-reject intercepts keep the # noqa: sdet-rename-shim exclusions live until the v1.6 clean-delete.
"""  # noqa: sdet-rename-shim
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# D-17 patterns
PLANNING_ID_PATTERN = re.compile(  # noqa: sdet-rename-shim
    r"\b(SDET|RENAME|PERSONA|CLEAN|CLI|CODEGEN|PACK|LIB|REPORTER|"
    r"CFG|CLOSE|STATE|UI|UX|UAT|SAFE|SURFACE|RUNNER|SEED)-\d+(\.\d+)?\b"
)
# The pattern intentionally excludes the SEED-022 doctrinal compound
# `SDET-safety` (framework-primitives / SDET-safety principle); that
# phrase is the locked doctrinal reference for the black-box guard
# rationale, not deprecated v1.4 terminology to be scrubbed.
SDET_TERM_PATTERN = re.compile(r"\bsdet\b|\bSDET\b(?!-safety)")  # noqa: sdet-rename-shim

# D-18 marker (case-sensitive)
NOQA_MARKER = "noqa: sdet-rename-shim"  # noqa: sdet-rename-shim


def _markdown_or_yaml_or_text_files() -> list[Path]:
    """D-16 scope: README + CLAUDE + docs + examples + config.example.yaml."""
    files: list[Path] = []
    for name in ("README.md", "CLAUDE.md", "config.example.yaml"):
        p = REPO_ROOT / name
        if p.is_file():
            files.append(p)
    docs_dir = REPO_ROOT / "docs"
    if docs_dir.is_dir():
        files.extend(sorted(docs_dir.rglob("*.md")))
    examples_dir = REPO_ROOT / "examples"
    if examples_dir.is_dir():
        for ext in ("*.md", "*.yaml", "*.yml"):
            files.extend(sorted(examples_dir.rglob(ext)))
    return files


def _src_python_files() -> list[Path]:
    """D-16 scope: docstrings + string literals inside src/mcp_test_framework/."""
    src_root = REPO_ROOT / "src" / "mcp_test_framework"
    if not src_root.is_dir():
        return []
    return sorted(src_root.rglob("*.py"))


def _scan_text_file(path: Path, pattern: re.Pattern[str]) -> list[tuple[int, str]]:
    """Return [(lineno, line)] for matches not tagged with NOQA_MARKER."""
    hits: list[tuple[int, str]] = []
    with path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            if NOQA_MARKER in line:
                continue
            if pattern.search(line):
                hits.append((ln, line.rstrip()))
    return hits


def _scan_python_strings(path: Path, pattern: re.Pattern[str]) -> list[tuple[int, str]]:
    """AST-walk python files; scan docstrings + string Constants; skip lines tagged with NOQA_MARKER."""
    source = path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        # If the file doesn't parse, fall back to a text scan with noqa exclusion
        return _scan_text_file(path, pattern)

    def _line_is_noqa(ln: int) -> bool:
        if 1 <= ln <= len(source_lines):
            return NOQA_MARKER in source_lines[ln - 1]
        return False

    def _range_is_noqa(start: int, end: int) -> bool:
        # If ANY line in the range carries the noqa marker, treat the whole node as excluded.
        for ln in range(start, end + 1):
            if _line_is_noqa(ln):
                return True
        return False

    hits: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        # String literals (covers operator-visible error messages, help strings, echo strings)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            ln = getattr(node, "lineno", None)
            end_ln = getattr(node, "end_lineno", ln)
            if ln is None:
                continue
            if _range_is_noqa(ln, end_ln or ln):
                continue
            if pattern.search(node.value):
                line_text = source_lines[ln - 1] if 1 <= ln <= len(source_lines) else node.value
                hits.append((ln, line_text.rstrip()))

    # Also scan top-of-file comments (ast doesn't surface them as nodes)
    for ln, line in enumerate(source_lines, 1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            if NOQA_MARKER in line:
                continue
            if pattern.search(line):
                hits.append((ln, line.rstrip()))

    return hits


@pytest.mark.parametrize(
    "pattern_name,pattern",
    [
        ("planning_id", PLANNING_ID_PATTERN),
        ("sdet_terminology", SDET_TERM_PATTERN),  # noqa: sdet-rename-shim
    ],
)
def test_no_residual_match_in_operator_facing_docs(pattern_name: str, pattern: re.Pattern[str]) -> None:
    """RENAME-06 / D-19: scan operator-facing markdown + yaml + config for residual matches."""  # noqa: sdet-rename-shim
    failures: list[tuple[Path, int, str]] = []
    for path in _markdown_or_yaml_or_text_files():
        for ln, line in _scan_text_file(path, pattern):
            failures.append((path.relative_to(REPO_ROOT), ln, line))
    assert not failures, (
        f"{pattern_name}: {len(failures)} residual match(es) found in operator-facing docs/examples. "
        f"Add `noqa: sdet-rename-shim` to the line(s) ONLY if they are a legitimate compat-shim "  # noqa: sdet-rename-shim
        f"or historical migration record per D-18. First 10:\n"
        + "\n".join(f"  {p}:{ln}: {line}" for p, ln, line in failures[:10])
    )


@pytest.mark.parametrize(
    "pattern_name,pattern",
    [
        ("planning_id", PLANNING_ID_PATTERN),
        ("sdet_terminology", SDET_TERM_PATTERN),  # noqa: sdet-rename-shim
    ],
)
def test_no_residual_match_in_src_python_strings(pattern_name: str, pattern: re.Pattern[str]) -> None:
    """RENAME-06 / D-19: scan docstrings + string literals + comments inside src/mcp_test_framework/."""  # noqa: sdet-rename-shim
    failures: list[tuple[Path, int, str]] = []
    for path in _src_python_files():
        for ln, line in _scan_python_strings(path, pattern):
            failures.append((path.relative_to(REPO_ROOT), ln, line))
    assert not failures, (
        f"{pattern_name}: {len(failures)} residual match(es) found in src/mcp_test_framework/. "
        f"Add `# noqa: sdet-rename-shim` to the line(s) ONLY if they are a legitimate compat-shim per D-18. "  # noqa: sdet-rename-shim
        f"First 10:\n"
        + "\n".join(f"  {p}:{ln}: {line}" for p, ln, line in failures[:10])
    )
