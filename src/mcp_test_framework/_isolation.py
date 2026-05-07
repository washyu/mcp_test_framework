"""Per-session host-state isolation: env-allowlist + HOME redirect for spawned MCP subprocess.

Phase 06 implementation of ISOL-02, ISOL-04, ISOL-05, ISOL-07. Builds the COMPLETE
``env`` dict passed to ``mcp.client.stdio.StdioServerParameters`` so the spawned
MCP server inherits ONLY allowlisted environment variables and a HOME/USERPROFILE
redirected to a per-session tempdir.

Design constraints (per .planning/phases/06-per-session-host-state-isolation/06-CONTEXT.md):
- D-05: Isolation is ALWAYS-ON. No toggle, no ``--no-isolation`` CLI escape hatch.
- D-06: NO ``IsolationConfig`` model, NO ``extra_env`` field, NO new public Config
  surface. The allowlist lives at the spawn site as a module-level constant — not
  a Config sub-model — to keep the public configuration surface frozen.
- D-07: The allowlist is exact (PATH, SYSTEMROOT, LANG, USERNAME, MCP_*) plus
  HOME/USERPROFILE/TEMP/TMP/TMPDIR overrides. Documented inline.

Rationale (FINDINGS-260506-qxs §3): the ``mcp_test_framework`` runs under a
developer's interactive shell, which carries the developer's real
``~/.homelab_mcp/`` registry, OS keyring credentials, AWS keys, GITHUB_TOKEN, and
similar. By default, ``stdio_client`` would inherit the FULL parent env into the
spawned ``homelab-mcp`` subprocess. That violates the project's "tests must not
mutate user state" guarantee. Replacing inheritance with a narrow allowlist plus
a HOME redirect to a tempdir gives the subprocess a clean, ephemeral universe.

ISOL-04 wiring: Plan 06-01 recon (06-keyring-recon.md §3) recorded a SHIP
decision — homelab-mcp's PyPI README v1.7.0 documents the OS keyring as the sole
credential store. ``PYTHON_KEYRING_BACKEND=keyring.backends.null.Null`` short-
circuits the Python ``keyring`` library's backend chain so any keyring access
becomes a no-op. NOTE (recon §3 caveat / Q1): this only neutralises the
``keyring`` Python library — direct Win32 ``CredWrite`` / libsecret calls via
``ctypes`` would bypass it. ISOL-03 in Plan 06-03 covers the residual surface
with a ``cmdkey /list`` snapshot.

DO NOT widen ``_PASSTHROUGH_ALLOWLIST`` without updating ``EXTENDING.md``
(DOC-07 in Phase 10). Each new pass-through is a hole in the isolation guarantee
and must be justified by a real subprocess need (e.g., locale resolution for a
non-English server) — not "the test wouldn't run otherwise" without a root cause.
"""
from __future__ import annotations

import os
from pathlib import Path

# Module-level constants per D-07 (allowlist exact, no widening, no Config field).
# Underscore-private to match the framework's existing convention for non-public
# surface (see _preflight, _owner_task in fixtures.py).

_PASSTHROUGH_ALLOWLIST: tuple[str, ...] = (
    "PATH",         # binary lookup for the MCP server command itself (ISOL-07)
    "SYSTEMROOT",   # Windows DLL resolution; without it, Python interpreters in
                    # the spawned subprocess fail to import stdlib modules
    "LANG",         # locale resolution for non-English MCP server output
    "USERNAME",     # informational; some servers log it for diagnostics
)
_MCP_PREFIX = "MCP_"  # CD-03: pass MCP_* through (includes MCP_CONNECTION_NONBLOCKING)
_HOME_OVERRIDES: tuple[str, ...] = (
    "HOME",         # POSIX
    "USERPROFILE",  # Windows — what os.path.expanduser('~') consults on Win32
    "TEMP",         # Windows tempdir
    "TMP",          # Windows tempdir alternate
    "TMPDIR",       # POSIX tempdir
)

# ISOL-04: Plan 06-01 SHIP decision — null keyring backend.
# Recon evidence: 06-keyring-recon.md §1 (PyPI README quote) / §2 (cmdkey diff).
_KEYRING_OVERRIDES: dict[str, str] = {
    "PYTHON_KEYRING_BACKEND": "keyring.backends.null.Null",
}


def _build_isolated_env(isolated_home: Path) -> dict[str, str]:
    """Return env dict for StdioServerParameters spawning into an isolated home.

    Replaces full os.environ inheritance with allowlist + overrides (D-07):
      1. Pass-through PATH, SYSTEMROOT, LANG, USERNAME (ISOL-07).
      2. Pass-through any MCP_* var (CD-03 — includes MCP_CONNECTION_NONBLOCKING).
      3. Override HOME/USERPROFILE/TEMP/TMP/TMPDIR -> isolated_home so
         os.path.expanduser('~') inside the spawned subprocess resolves to
         the tempdir on Windows and POSIX alike (ISOL-02 / ISOL-05).
      4. Override PYTHON_KEYRING_BACKEND to the null backend (ISOL-04, Plan
         06-01 SHIP decision).

    The returned dict is the COMPLETE env passed to StdioServerParameters —
    NOT a delta on top of os.environ. Anything not in this dict is invisible
    to the subprocess (intentional; that is the isolation guarantee).
    """
    env: dict[str, str] = {}
    for name in _PASSTHROUGH_ALLOWLIST:
        if (value := os.environ.get(name)) is not None:
            env[name] = value
    for name, value in os.environ.items():
        if name.startswith(_MCP_PREFIX):
            env[name] = value
    home_str = str(isolated_home)
    for name in _HOME_OVERRIDES:
        env[name] = home_str
    env.update(_KEYRING_OVERRIDES)
    return env
