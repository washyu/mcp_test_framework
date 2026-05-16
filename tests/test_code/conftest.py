"""Phase 18 SDET-only conftest: ToolCallError -> JUnit user_properties hook.

Per Phase 18 CONTEXT.md D-09 / D-10 / D-11: the hook below captures
ToolCallError exceptions raised inside an SDET test and stashes three
project-scoped property entries onto report.user_properties so the
pytest JUnit XML writer surfaces them as <property> children of
<testcase>. The domain-UI XML parser at _runner.py reads those keys
to drive the em-dash FAIL row's failure_message and to render the
structured dump block in the --debug appendix. See the hook body below
for the exact key names and order.

This conftest is INDEPENDENT of the parametrize hook in tests/conftest.py
-- SDET tests are hand-authored, not parametrized over discovered tools.
The session fixtures still flow in via plugin inheritance through the
parent tests/conftest.py (which registers mcp_test_framework.fixtures).
"""
from __future__ import annotations

from mcp_test_framework.test_code import ToolCallError


def pytest_exception_interact(node, call, report):
    """D-09 + D-11: hoist ToolCallError fields onto report.user_properties.

    pytest emits user_properties into the JUnit XML as <property> children
    of <testcase>. The wrapper-side XML parser reads the project-scoped
    keys appended below to feed the FAIL row and the --debug appendix
    dump block.

    Strict: only ToolCallError is enriched. Other exceptions (AssertionError,
    plain RuntimeError, etc.) are passed through to pytest's normal failure
    machinery untouched. Generic exception enrichment is a v1.4 candidate
    (CONTEXT.md Deferred Ideas).
    """
    exc = call.excinfo.value if call.excinfo else None
    if isinstance(exc, ToolCallError):
        report.user_properties.append(("mcptf_error_code", exc.code or ""))
        report.user_properties.append(("mcptf_error_message", exc.message))
        # D-11: serialize the live CallToolResult so the --debug appendix
        # can render the raw block (CONTEXT.md lines 123-134). Empty string
        # when exc.raw is None -- keeps the JUnit XML attribute well-formed
        # and lets the renderer detect "no raw" via empty-string check.
        report.user_properties.append((
            "mcptf_error_raw",
            exc.raw.model_dump_json(indent=2) if exc.raw is not None else "",
        ))
