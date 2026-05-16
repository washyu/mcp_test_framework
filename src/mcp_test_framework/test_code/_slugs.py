"""Slug + identifier helpers for the SDET codegen.

  - ``server_slug(name)`` normalizes ``serverInfo.name`` from the MCP
    ``initialize`` handshake. Rule: lowercase -> non-[a-z0-9] to underscore
    -> collapse runs of underscores -> strip leading/trailing underscores.
    Errors loud on empty or all-non-identifier input (callers in cli.py map
    this to an operator error).
  - ``pascal_case`` and ``module_name`` handle tool-name -> class-name and
    tool-name -> file-name conversions with keyword guards.

Pure stdlib (re + keyword). No external deps.
"""
from __future__ import annotations

import keyword
import re

_NON_IDENT = re.compile(r"[^a-zA-Z0-9_]+")
# For PascalCase splitting we also break on `_` so that snake_case names map
# to PascalCase cleanly: `create_vm` -> ["create", "vm"] -> "CreateVm".
_PASCAL_SPLIT = re.compile(r"[^a-zA-Z0-9]+")


def server_slug(server_name: str) -> str:
    """Normalize an MCP server name into a directory slug.

    >>> server_slug("homelab-mcp")
    'homelab_mcp'
    >>> server_slug("My Server v2.0")
    'my_server_v2_0'
    >>> server_slug("___leading-trailing___")
    'leading_trailing'
    """
    if not isinstance(server_name, str):
        raise ValueError(f"server name must be str, got {type(server_name).__name__}")
    lowered = server_name.lower()
    underscored = _NON_IDENT.sub("_", lowered)
    collapsed = re.sub(r"_+", "_", underscored)
    stripped = collapsed.strip("_")
    if not stripped:
        raise ValueError(
            f"server name {server_name!r} normalizes to empty slug; cannot "
            "derive a generated/<slug>/ directory. The MCP server must "
            "report a non-empty serverInfo.name with at least one "
            "[a-z0-9] character after lowercasing."
        )
    return stripped


def pascal_case(tool_name: str) -> str:
    """Convert a tool name to a PascalCase class identifier.

    >>> pascal_case("create_vm")
    'CreateVm'
    >>> pascal_case("list-registered-servers")
    'ListRegisteredServers'
    >>> pascal_case("class")
    'Class_'
    >>> pascal_case("2nd_attempt")
    '_2ndAttempt'
    """
    parts = [p for p in _PASCAL_SPLIT.split(tool_name) if p]
    if not parts:
        raise ValueError(f"tool name {tool_name!r} has no identifier characters")
    pascal = "".join(p[:1].upper() + p[1:] for p in parts)
    if pascal[0].isdigit():
        pascal = "_" + pascal
    # keyword guard (rare for PascalCase but cheap insurance)
    if keyword.iskeyword(pascal) or keyword.iskeyword(pascal.lower()):
        pascal = pascal + "_"
    return pascal


def module_name(tool_name: str) -> str:
    """Convert a tool name to a snake_case module file name.

    >>> module_name("create_vm")
    'create_vm'
    >>> module_name("list-registered-servers")
    'list_registered_servers'
    >>> module_name("import")
    'import_'
    >>> module_name("2nd-attempt")
    '_2nd_attempt'
    """
    name = _NON_IDENT.sub("_", tool_name).strip("_").lower()
    if not name:
        raise ValueError(f"tool name {tool_name!r} has no identifier characters")
    if name[0].isdigit():
        name = "_" + name
    if keyword.iskeyword(name):
        name = name + "_"
    return name
