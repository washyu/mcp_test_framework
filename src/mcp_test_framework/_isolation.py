"""Per-session host-state isolation: env-allowlist + HOME redirect for spawned MCP subprocess.

Builds the COMPLETE ``env`` dict passed to
``mcp.client.stdio.StdioServerParameters`` so the spawned MCP server inherits
ONLY allowlisted environment variables and a HOME/USERPROFILE redirected to
a per-session tempdir.

Design constraints:
- Isolation is ON BY DEFAULT (``host_isolation='strict'``) and disabled
  per-config-file via ``host_isolation='passthrough'``. The maintainer
  warning below stays in force for the strict allowlist; passthrough is
  all-or-nothing by design (no per-var widening, no per-tool toggle).
- NO ``IsolationConfig`` model, NO ``extra_env`` field, NO new public Config
  surface. The allowlist lives at the spawn site as a module-level constant --
  not a Config sub-model -- to keep the public configuration surface frozen.
- The allowlist is exact (PATH, SYSTEMROOT, LANG, USERNAME, MCP_*) plus
  HOME/USERPROFILE/TEMP/TMP/TMPDIR overrides. Documented inline.

Rationale: the ``mcp_test_framework`` runs under a developer's interactive
shell, which carries the developer's real ``~/.homelab_mcp/`` registry, OS
keyring credentials, AWS keys, GITHUB_TOKEN, and similar. By default,
``stdio_client`` would inherit the FULL parent env into the spawned
``homelab-mcp`` subprocess. That violates the project's "tests must not
mutate user state" guarantee. Replacing inheritance with a narrow allowlist
plus a HOME redirect to a tempdir gives the subprocess a clean, ephemeral
universe.

Keyring axis: the null keyring backend short-circuits the Python ``keyring``
library's backend chain so any keyring access becomes a no-op. NOTE: this
only neutralises the ``keyring`` Python library -- direct Win32
``CredWrite`` / libsecret calls via ``ctypes`` would bypass it. The
filesystem-state snapshot (sha256 of three registry files) covers ONLY the
``~/.homelab_mcp/`` filesystem axis; it does NOT snapshot the keyring axis.
There is no continuous keyring-axis regression guard in the suite.

DO NOT widen ``_PASSTHROUGH_ALLOWLIST`` without updating the maintainer
docs. Each new pass-through is a hole in the isolation guarantee and must
be justified by a real subprocess need (e.g., locale resolution for a
non-English server) -- not "the test wouldn't run otherwise" without a
root cause.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

# Module-level constants: allowlist exact, no widening, no Config field.
# Underscore-private to match the framework's existing convention for non-public
# surface (see _preflight, _owner_task in fixtures.py).

_PASSTHROUGH_ALLOWLIST: tuple[str, ...] = (
    "PATH",         # binary lookup for the MCP server command itself
    "SYSTEMROOT",   # Windows DLL resolution; without it, Python interpreters in
                    # the spawned subprocess fail to import stdlib modules
    "LANG",         # locale resolution for non-English MCP server output
    "USERNAME",     # informational; some servers log it for diagnostics.
                    # NOTE: POSIX ``USER`` is intentionally NOT in this allowlist
                    # -- the locked allowlist names exactly ``USERNAME``.
                    # On Linux/macOS, ``getpass.getuser()`` consults ``USER`` and
                    # ``USERNAME`` is rarely set, so the spawned subprocess sees
                    # no user identity at all. This is spec-faithful; widening
                    # the allowlist would require an explicit decision and a
                    # maintainer-doc update (out of scope for a code-review fix).
)
_MCP_PREFIX = "MCP_"  # pass MCP_* through (includes MCP_CONNECTION_NONBLOCKING)
_HOME_OVERRIDES: tuple[str, ...] = (
    "HOME",         # POSIX
    "USERPROFILE",  # Windows -- what os.path.expanduser('~') consults on Win32
    "TEMP",         # Windows tempdir
    "TMP",          # Windows tempdir alternate
    "TMPDIR",       # POSIX tempdir
)

# Null keyring backend override. The Python `keyring` library consults this
# env var first and short-circuits to a no-op backend when set.
_KEYRING_OVERRIDES: dict[str, str] = {
    "PYTHON_KEYRING_BACKEND": "keyring.backends.null.Null",
}


def _build_isolated_env(isolated_home: Path) -> dict[str, str]:
    """Return env dict for StdioServerParameters spawning into an isolated home.

    Replaces full os.environ inheritance with allowlist + overrides:
      1. Pass-through PATH, SYSTEMROOT, LANG, USERNAME.
      2. Pass-through any MCP_* var (includes MCP_CONNECTION_NONBLOCKING).
      3. Override HOME/USERPROFILE/TEMP/TMP/TMPDIR -> isolated_home so
         os.path.expanduser('~') inside the spawned subprocess resolves to
         the tempdir on Windows and POSIX alike.
      4. Override PYTHON_KEYRING_BACKEND to the null backend.

    The returned dict is the COMPLETE env passed to StdioServerParameters --
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


def _build_passthrough_env() -> dict[str, str]:
    """Return a literal ``dict(os.environ)`` copy -- passthrough mode contract.

    Operator opted into ``host_isolation='passthrough'``: the spawned MCP subprocess
    sees the operator's full env, including HOME / USERPROFILE / TEMP and the
    operator's keyring backend. Nothing stripped, nothing injected. The hermetic
    property is explicitly traded for credential reachability.

    Framework-primitive contract (SDET-safety): this primitive takes no Config
    blob -- the caller passed the mode as plain data.
    """
    return dict(os.environ)


def _build_subprocess_env(
    mode: Literal['strict', 'passthrough'],
    isolated_home: Path | None,
) -> dict[str, str]:
    """Dispatch to the right env builder based on ``host_isolation`` mode.

    Spawn-site callers (``fixtures.py``, ``mcp_client.py``, ``_plugin.py``) pass
    ``cfg.host_isolation`` as ``mode`` and the resolved ``_isolated_home`` Path
    (or None under passthrough where the tempdir is unallocated).

    Strict mode REQUIRES an ``isolated_home`` -- the assertion is a defensive
    guard against caller drift; passthrough mode ignores it.
    """
    if mode == 'passthrough':
        return _build_passthrough_env()
    assert isolated_home is not None, (
        "_build_subprocess_env(mode='strict') requires isolated_home; "
        "caller must allocate the tempdir before invoking strict-mode dispatch"
    )
    return _build_isolated_env(isolated_home)
