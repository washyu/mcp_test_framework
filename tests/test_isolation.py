"""Phase 06 ISOL-03 / ISOL-06 verification: real ~/.homelab_mcp/ unchanged + tempdir-positive.

Primary requirement (ISOL-03): after a full v1.1 tool-surface run, the sha256 of
~/.homelab_mcp/credential_registry.json, ~/.homelab_mcp/known_hosts, and
~/.homelab_mcp/migration_state.json is unchanged from before the run. This is
the regression guard for ROADMAP Phase 06 success criterion #1.

Cross-platform requirement (ISOL-06): the same test body — without any
platform fork — proves that os.path.expanduser('~') inside the spawned
homelab-mcp subprocess resolved to _isolated_home on both Windows
(USERPROFILE redirect) and POSIX (HOME redirect). Step 4 below is the
cross-platform signal: <_isolated_home>/.homelab_mcp/ exists IFF redirection
took effect.

Decisions honored (per .planning/phases/06-per-session-host-state-isolation/06-CONTEXT.md):
- D-08: 4-step body — sha256 snapshot, drive v1.1 tool surface, re-hash + assert
  equal, assert tempdir's .homelab_mcp/ exists.
- D-09: hashes (sha256), NOT mtimes. mtime-only would miss same-second
  identical-content overwrites and adds a Sysinternals-on-Windows /
  /proc-on-POSIX cross-platform tax that sha256 sidesteps entirely.
- D-10: in-process. The mcp_client fixture's own subprocess spawn IS the
  run-under-test. NO recursive `uv run pytest` subprocess; no stdlib
  subprocess module imports anywhere in this file.
- D-11: pytest.skip(...) cleanly when ~/.homelab_mcp/ is absent on the host
  (fresh CI runner). The test's value lives on a developer machine that has
  the real install — exactly where bleed-through bites.

Black-box compliance: this module imports ONLY stdlib (pathlib, hashlib) and
mcp_test_framework public surface — never `homelab_mcp`. The conftest.py
sys.modules guard at lines 32-42 fails the run mechanically if any
homelab_mcp submodule slips into sys.modules.
"""
from __future__ import annotations

# D-09: sha256 (not mtimes) — cross-platform clean, catches same-second
# identical-content overwrites without Sysinternals/proc dependencies.
import hashlib
from pathlib import Path

import pytest

from mcp_test_framework.mcp_client import McpTestClient

# UNMARKED per D-markers-1; preflight is the gate. loop_scope="session"
# required so fixtures + tests share the session loop (matches
# asyncio_default_fixture_loop_scope = "session" in pyproject.toml).
pytestmark = [pytest.mark.asyncio(loop_scope="session")]


# ---------------------------------------------------------------------------
# Module-level constants — locked to v1.1 tool surface per CONTEXT D-08.
# When v1.x adds tools touching other paths under ~/.homelab_mcp/, update
# REAL_FILES additively. Do NOT generalize to a glob — explicit list keeps
# the test's claim narrow and auditable.
# ---------------------------------------------------------------------------

REAL_HOMELAB_DIR = Path.home() / ".homelab_mcp"
REAL_FILES: tuple[Path, ...] = (
    REAL_HOMELAB_DIR / "credential_registry.json",
    REAL_HOMELAB_DIR / "known_hosts",
    REAL_HOMELAB_DIR / "migration_state.json",
)

# The v1.1 tool surface the test exercises. Adding tools here as the surface
# grows guarantees ISOL-03 covers any new mutation pressure.
V11_TOOL_SURFACE: tuple[str, ...] = (
    "list_keyring_credentials",
    "list_registered_servers",
)


def _sha256_of(p: Path) -> str | None:
    """Return hex sha256 of p's bytes, or None if p doesn't exist.

    D-09: sha256 over file contents — NOT modification time. Mtime-only
    checks would miss a same-second overwrite that happens to land on
    identical content, and add a Sysinternals-on-Windows / /proc-on-POSIX
    cross-platform tax that sha256 sidesteps entirely.
    """
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# ISOL-03 primary test (also satisfies ISOL-06 via step 4 cross-platform signal)
# ---------------------------------------------------------------------------


async def test_real_state_unchanged(
    _isolated_home: Path,
    mcp_client: McpTestClient,
) -> None:
    """ISOL-03: real ~/.homelab_mcp/ files unchanged after the run.

    Test scope (D-10): in-process. The mcp_client fixture's own subprocess
    spawn IS the run-under-test — we drive it with call_tool here rather
    than recursively spawning `uv run pytest` as a subprocess. No
    self-recursion pattern; fixture is the seam.

    Also satisfies ISOL-06: the tempdir-positive assertion (step 4) proves
    os.path.expanduser('~') inside the spawned subprocess resolved to
    _isolated_home — works identically on Windows (USERPROFILE) and POSIX
    (HOME) without a platform fork.

    D-11: skip cleanly when ~/.homelab_mcp/ doesn't exist on the host
    (fresh CI box). The test's value lives on a developer machine that has
    the real install — exactly where bleed-through bites.
    """
    # D-11: skip cleanly on hosts without a real homelab-mcp install.
    if not REAL_HOMELAB_DIR.exists():
        pytest.skip(
            "No real ~/.homelab_mcp/ to compare against — "
            "ISOL-03 vacuous on this host"
        )

    # Step 1: snapshot sha256 of the 3 real files BEFORE invoking any tool.
    # D-09: hashes (not mtimes) — mtime-only would miss same-second
    # overwrites with identical content, and avoids cross-platform
    # Sysinternals/proc dependencies.
    before = {p: _sha256_of(p) for p in REAL_FILES}

    # Step 2: drive the v1.1 tool surface in-process (D-10 — no recursive
    # `uv run pytest`). The mcp_client fixture's spawn IS the run-under-test.
    for tool_name in V11_TOOL_SURFACE:
        # call_arguments is {} for the v1.1 tools — both list_* tools take
        # no required parameters at the v1.1 surface.
        await mcp_client.call_tool(tool_name, {})

    # Step 3: re-hash with sha256 (D-09) and assert equality.
    after = {p: _sha256_of(p) for p in REAL_FILES}
    assert before == after, (
        f"ISOL-03 FAIL: real ~/.homelab_mcp/ mutated by the test run. "
        f"before={before!r} after={after!r}"
    )

    # Step 4: positive — tempdir's .homelab_mcp/ exists. D-08 step 4 guards
    # against the silent pass where tools just no-op'd. Also the ISOL-06
    # cross-platform check: this only succeeds if the subprocess's
    # expanduser('~') resolved to _isolated_home, which only happens if HOME
    # (POSIX) or USERPROFILE (Windows) was set correctly via
    # _build_isolated_env.
    tempdir_homelab = _isolated_home / ".homelab_mcp"
    assert tempdir_homelab.exists(), (
        f"Tempdir {tempdir_homelab} was not created — redirection did not "
        f"take effect (ISOL-06 cross-platform signal); tools may have "
        f"no-op'd silently."
    )
