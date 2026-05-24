"""Wave-0 regression guard for Phase 12 CLEAN-06 + CLEAN-01.

.env.example is reframed as CI-secret-passthrough-only documentation.
This test guarantees the framing and the absence of the v1.1
config-via-env declarations.
"""
from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repo root (pyproject.toml) not found")


DOTENV = _repo_root() / ".env.example"


def test_dotenv_example_exists() -> None:
    assert DOTENV.is_file(), f"missing {DOTENV}"


def test_dotenv_example_no_banned_tokens() -> None:
    text = DOTENV.read_text(encoding="utf-8")
    banned = [
        r"\bPhase \d",
        r"\bPlan \d-\d",
        r"\bTOOLCFG-\d",
        r"\bISOL-\d",
        r"\bOUTPUT-\d",
        r"\bD-\d{2}",
        r"\b\d{6}-[a-z0-9]{3}",
    ]
    found = [p for p in banned if re.search(p, text)]
    assert not found, f"banned tokens in .env.example: {found}"


def test_dotenv_example_has_ci_secret_framing() -> None:
    text = DOTENV.read_text(encoding="utf-8")
    assert "CI secret" in text or "CI secrets" in text, (
        ".env.example must frame env vars as CI-secret passthrough (CLEAN-06)"
    )


def test_dotenv_example_points_at_config_init() -> None:
    text = DOTENV.read_text(encoding="utf-8")
    assert "config-init" in text, (
        ".env.example must point at config-init as the configuration entry point"
    )


def test_dotenv_example_no_legacy_overlay_decls() -> None:
    """v1.1 config-via-env declarations are removed; config lives in config.yaml."""
    text = DOTENV.read_text(encoding="utf-8")
    legacy_decls = [
        r"^TARGET_TOOL_NAME=",
        r"^MCP_SERVER_COMMAND=",
        r"^MCP_SERVER_ARGS=",
        r"^MCP_SERVER_TIMEOUT_SECONDS=",
        r"^OLLAMA_BASE_URL=",
        r"^OLLAMA_MODEL=",
        r"^OLLAMA_TIMEOUT_SECONDS=",
        r"^JUDGE_TIMEOUT_SECONDS=",
    ]
    found = [p for p in legacy_decls if re.search(p, text, re.MULTILINE)]
    assert not found, f"legacy v1.1 env-var declarations still present: {found}"


def test_dotenv_example_no_mcptf_config_file_mention() -> None:
    """Phase 31 SHIM-05 D-05: .env.example no longer documents
    ``MCPTF_CONFIG_FILE`` as a config-resolution route.

    The env var is inert as a value source as of v1.5; the only two
    operator routes are ``--config PATH`` and
    ``[tool.pytest.ini_options] mcp_config_file = PATH``, neither of
    which lives in ``.env``.
    """
    text = DOTENV.read_text(encoding="utf-8")
    assert "MCPTF_CONFIG_FILE" not in text, (
        ".env.example must not mention MCPTF_CONFIG_FILE (Phase 31 "
        "SHIM-05 D-05: env var is inert as a value source)."
    )


def test_dotenv_example_line_count_reasonable() -> None:
    """Was 24 lines in v1.1; should shrink to ~12-20 lines after CLEAN-06 reframe."""
    text = DOTENV.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert 10 <= len(lines) <= 25, f"unexpected line count: {len(lines)}"


def test_readme_does_not_imperatively_cp_dotenv_example() -> None:
    """README quickstart must not teach `cp .env.example .env` as setup.

    The .env.example v1.2 file framings itself as CI-secret passthrough only;
    a quickstart `cp` instruction contradicts that mental model.
    """
    readme = _repo_root() / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert "cp .env.example .env" not in text, (
        "README quickstart still teaches operators to copy .env.example as "
        "part of setup, which contradicts .env.example's own CI-secret-"
        "passthrough framing."
    )


def test_extending_mentions_dotenv_example_with_ci_secret_framing() -> None:
    """docs/EXTENDING.md must mention .env.example exactly once with CI-secret framing."""
    extending = _repo_root() / "docs" / "EXTENDING.md"
    text = extending.read_text(encoding="utf-8")
    needle = ".env.example"
    occurrences = text.count(needle)
    assert occurrences == 1, (
        f"EXTENDING.md must mention .env.example exactly once "
        f"(found {occurrences})."
    )
    idx = text.index(needle)
    start = max(0, idx - 100)
    end = min(len(text), idx + len(needle) + 100)
    window = text[start:end]
    framings = ("CI secret", "CI secrets", "secret passthrough", "CI-secret")
    assert any(f in window for f in framings), (
        "EXTENDING.md mentions .env.example but without the CI-secret "
        "framing the file itself uses."
    )


def test_readme_mentions_dotenv_example_at_most_once() -> None:
    """README must not reference .env.example more than once.

    The file's narrow CI-secret-passthrough purpose can't survive multiple
    framings in the same doc.
    """
    readme = _repo_root() / "README.md"
    text = readme.read_text(encoding="utf-8")
    occurrences = text.count(".env.example")
    assert occurrences <= 1, (
        f"README still references .env.example multiple times "
        f"(found {occurrences}) — the file's narrow purpose can't survive "
        f"multiple framings."
    )
