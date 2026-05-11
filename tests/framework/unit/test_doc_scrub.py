"""Wave-0 banned-token regression guard for Phase 12 CLEAN-01 + PERSONA-01 + CLEAN-04.

Asserts the four user-facing files (README, config.example.yaml, .env.example,
docs/EXTENDING.md) carry zero spec IDs / phase IDs / quick-task IDs / file:line
refs after Phase 12. Asserts the PERSONA-01 framing section exists in README and
EXTENDING. Asserts CLEAN-04's "link to BOTH" contract.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
README = ROOT / "README.md"
EXTENDING = ROOT / "docs" / "EXTENDING.md"
CFG_EXAMPLE = ROOT / "config.example.yaml"
DOTENV = ROOT / ".env.example"


BASE_BANNED = [
    r"\bPhase \d",
    r"\bPlan \d-\d",
    r"\bTOOLCFG-\d",
    r"\bISOL-\d",
    r"\bOUTPUT-\d",
    r"\bD-\d{2}",
    r"\b\d{6}-[a-z0-9]{3}",
]


def _scan(text: str, patterns: list[str]) -> list[str]:
    return [p for p in patterns if re.search(p, text)]


def test_readme_exists_and_no_banned_tokens() -> None:
    assert README.is_file()
    text = README.read_text(encoding="utf-8")
    patterns = BASE_BANNED + [r"src/[\w/.]+\.py:\d+"]
    bad = _scan(text, patterns)
    assert not bad, f"banned tokens in README.md: {bad}"


def test_extending_exists_and_no_banned_tokens() -> None:
    assert EXTENDING.is_file()
    text = EXTENDING.read_text(encoding="utf-8")
    patterns = BASE_BANNED + [
        r"\bDOC-\d",
        r"_isolation\.py:\d+",
        r"06-VERIFICATION",
        r"MILESTONE-AUDIT",
    ]
    bad = _scan(text, patterns)
    assert not bad, f"banned tokens in docs/EXTENDING.md: {bad}"


def test_config_example_no_banned_tokens() -> None:
    text = CFG_EXAMPLE.read_text(encoding="utf-8")
    bad = _scan(text, BASE_BANNED + [r"\bCD-\d"])
    assert not bad, f"banned tokens in config.example.yaml: {bad}"


def test_dotenv_example_no_banned_tokens() -> None:
    text = DOTENV.read_text(encoding="utf-8")
    bad = _scan(text, BASE_BANNED)
    assert not bad, f"banned tokens in .env.example: {bad}"


def test_readme_has_persona_heading_once() -> None:
    text = README.read_text(encoding="utf-8")
    assert text.count("## Testing an MCP server you didn't write") == 1


def test_extending_has_persona_heading_once() -> None:
    text = EXTENDING.read_text(encoding="utf-8")
    assert text.count("## Testing an MCP server you didn't write") == 1


def test_readme_links_both_example_files() -> None:
    text = README.read_text(encoding="utf-8")
    assert "config.example.yaml" in text
    assert "examples/homelab-mcp.yaml" in text


def test_readme_no_target_tool_name() -> None:
    """D-03: TARGET_TOOL_NAME env var is leaving in Phase 13; do not advertise."""
    text = README.read_text(encoding="utf-8")
    assert "TARGET_TOOL_NAME" not in text


def test_readme_persona_section_has_locked_phrase() -> None:
    """Pitfall 5: the locked persona-framing sentence must be verbatim."""
    text = README.read_text(encoding="utf-8")
    assert "treats your MCP server as a black box" in text


def test_readme_persona_section_has_no_marketing_words() -> None:
    """Pitfall 5: anti-marketing tone in operator-facing prose."""
    text = README.read_text(encoding="utf-8")
    # Extract the persona section: from heading to next H2 (or EOF)
    m = re.search(
        r"## Testing an MCP server you didn't write\n(.*?)(?=\n## |\Z)",
        text,
        re.DOTALL,
    )
    assert m, "persona section not found"
    section = m.group(1)
    for word in ("powerful", "seamless", "empowers", "leverage", "cutting-edge"):
        assert word.lower() not in section.lower(), f"marketing word in persona section: {word!r}"


def test_extending_step2_mentions_uvx_pipx_bootstrap_flags() -> None:
    """Plan 12-08: EXTENDING Step 2 must show the uvx/pipx config-init bootstrap.

    Operators following the canonical walkthrough will only discover the
    `--command`/`--arg` flags exist if they're documented inside Step 2 of the
    'Testing an MCP server you didn't write' walkthrough. Without this
    subsection the only way to find the bootstrap recipe is reading the
    `--help` output -- which an operator on a fresh checkout with a
    not-on-PATH default would only consult AFTER hitting the launch failure
    they're trying to avoid.
    """
    text = EXTENDING.read_text(encoding="utf-8")
    assert "--command" in text, (
        "EXTENDING Step 2 still doesn't show the uvx/pipx bootstrap recipe -- "
        "operators following the canonical walkthrough won't discover the "
        "flags exist."
    )
    assert "--arg" in text, (
        "EXTENDING mentions --command but not --arg; both are needed to "
        "describe the typical uvx/pipx invocation."
    )
    assert "uvx" in text or "pipx" in text, (
        "EXTENDING --command/--arg mention must name at least one of "
        "uvx / pipx so operators recognize the use case."
    )
    # Sanity: the --command mention must sit near a `config-init` invocation,
    # not in some unrelated context.
    idx = text.index("--command")
    window = text[max(0, idx - 200) : idx + 200]
    assert "config-init" in window, (
        "EXTENDING --command mention is not in a config-init context; the "
        "subsection must show the flags as part of the bootstrap recipe."
    )


@pytest.mark.parametrize("path", [README, EXTENDING])
def test_doc_invocations_consistently_pair_with_config(path: Path) -> None:
    """Plan 12-09 (UAT gap 3, Option C): every operator-facing
    `mcp-test-framework run|list-tools|config-init` invocation in fenced code
    blocks must pair with `--config`, OR carry an explicit exemption flag
    (`--help`, `--command` for the bootstrap form per Plan 12-08).

    Documented exemptions:
    - `--config` : explicit config flag (canonical pairing)
    - `--help`   : help mode, no config needed
    - `--command`: bootstrap form per Plan 12-08; --config logically
                   unavailable because the config file doesn't exist yet
    - README "Sample green run" pytest-output style lines are output, not
      invocations — heuristically excluded by the prefix list below.

    `mcp-test-framework version` is naturally excluded (the regex matches
    only run|list-tools|config-init, not version).

    The runtime contract being protected: per CONTEXT.md (locked decision),
    the framework does NOT auto-discover a `config.yaml` in the cwd. Docs
    that omit --config from bare invocations actively teach a broken mental
    model. SEED-006 owns the v1.2 redesign that may flip this; until then,
    the docs and the runtime must agree.
    """
    text = path.read_text(encoding="utf-8")
    in_block = False
    offending: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            continue
        m = re.search(r"mcp-test-framework (run|list-tools|config-init)\b", line)
        if not m:
            continue
        # Documented exemptions: --config, --help, --command (bootstrap)
        if "--config" in line or "--help" in line or "--command" in line:
            continue
        # README-only exemption: pytest-output style lines (Sample green run)
        if any(
            line.lstrip().startswith(prefix)
            for prefix in (
                "platform ",
                "rootdir:",
                "configfile:",
                "plugins:",
                "asyncio:",
                "collected ",
                "tests\\",
                "tests/",
                "=====",
            )
        ):
            continue
        offending.append((i, line.rstrip()))
    assert not offending, (
        f"{path.name}: bare `mcp-test-framework <cmd>` invocations without "
        f"`--config`, `--help`, or `--command`:\n"
        + "\n".join(f"  line {i}: {ln}" for i, ln in offending)
        + "\n\nPair each with `--config config.yaml` (Option C of UAT gap 3), "
        "or use `--command` for the documented bootstrap form (Plan 12-08), "
        "or document the exception in surrounding prose."
    )
