"""Unit tests for mcp_test_framework.sdet._codegen + _slugs.

Pins:
  - _slugs: D-05 server_slug normalization, pascal_case / module_name keyword + digit guards
  - _codegen.translate_tool: D-02 schema coverage rules + degradation comments
    (D-02 enum/oneOf/anyOf/$ref/nullable/array-non-scalar/unknown-type)
  - CODEGEN-06 header marker presence
  - CODEGEN-03 D-06 stub Response for outputSchema-undeclared tools

Pure-sync (no asyncio). Walker is a pure-data transform; no I/O here.
"""
from __future__ import annotations

import pytest

from mcp_test_framework.sdet._slugs import module_name, pascal_case, server_slug


# --- _slugs ----------------------------------------------------------------

class TestServerSlug:
    def test_homelab_mcp(self) -> None:
        assert server_slug("homelab-mcp") == "homelab_mcp"

    def test_mixed_case_and_dots(self) -> None:
        assert server_slug("My Server v2.0") == "my_server_v2_0"

    def test_collapses_runs_and_strips(self) -> None:
        assert server_slug("___leading-trailing___") == "leading_trailing"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty slug"):
            server_slug("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="empty slug"):
            server_slug("   ")


class TestPascalCase:
    def test_snake_case(self) -> None:
        assert pascal_case("create_vm") == "CreateVm"

    def test_kebab_case(self) -> None:
        assert pascal_case("list-registered-servers") == "ListRegisteredServers"

    def test_keyword_guard(self) -> None:
        assert pascal_case("class") == "Class_"

    def test_leading_digit_guard(self) -> None:
        assert pascal_case("2nd_attempt") == "_2ndAttempt"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="no identifier characters"):
            pascal_case("")

    def test_homelab_mcp_tool_set_no_collisions(self) -> None:
        """Pitfall 2: adversarial real-world names round-trip without collision."""
        names = [
            "list_registered_servers",
            "create_vm",
            "delete-vm",
            "check_proxmox_health",
            "import",
            "2fa-verify",
            "class",
        ]
        pascals = [pascal_case(n) for n in names]
        assert len(set(pascals)) == len(names), f"collisions: {pascals}"


class TestModuleName:
    def test_snake_passthrough(self) -> None:
        assert module_name("create_vm") == "create_vm"

    def test_kebab_to_snake(self) -> None:
        assert module_name("list-registered-servers") == "list_registered_servers"

    def test_keyword_guard(self) -> None:
        assert module_name("import") == "import_"

    def test_leading_digit_guard(self) -> None:
        assert module_name("2nd-attempt") == "_2nd_attempt"


# --- _codegen.translate_tool (added in Task 2) ----------------------------
# (walker tests appended in Task 2)
