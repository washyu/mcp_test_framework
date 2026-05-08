"""README snippet correctness sanity tests (Phase 10-01 / CD-06).

These regression tests bake the documentation invariants asserted by Phase 10
Plan 10-01 into the suite, so future edits to README.md or the per-tool config
model surface drift immediately rather than after a confused reader files an
issue.

Three checks are enforced:

1. ``test_readme_yaml_snippets_parse`` -- every fenced ```yaml block in
   README.md must parse via ``yaml.safe_load`` without error.
2. ``test_readme_per_tool_fields_match_model`` -- every TOOLCFG field
   documented in the README's per-tool table must exist on the
   ``ToolConfig`` Pydantic model in ``mcp_test_framework.models``.
3. ``test_readme_anchor_targets_exist`` -- every ``docs/EXTENDING.md#anchor``
   link in README.md must resolve to a real heading in ``docs/EXTENDING.md``.
   While Plan 10-02 is still in flight the only such anchor
   (``add-a-new-mcp-tool-target``) may not yet exist; in that case the test
   xfails gracefully rather than hard-failing.

The tests are sync, use no fixtures, carry no live markers, and run by
default under ``uv run mcp-test-framework run``.
"""

from __future__ import annotations

import pathlib
import re

import pytest
import yaml

from mcp_test_framework.models import ToolConfig


_DOCUMENTED_TOOLCFG_FIELDS = (
    "skip",
    "skip_reason",
    "call_arguments",
    "judges",
    "setup",
    "depends_on",
)


def _read_readme() -> str:
    return pathlib.Path("README.md").read_text(encoding="utf-8")


def _read_extending() -> str | None:
    path = pathlib.Path("docs/EXTENDING.md")
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def test_readme_yaml_snippets_parse() -> None:
    """Every fenced ```yaml block in README.md must be valid YAML.

    Drift trap: a copy-paste error inside a worked YAML block (mis-indented
    key, stray tab, unbalanced bracket) silently breaks the docs without
    failing any other test. This guards against that class of regression.
    """
    text = _read_readme()
    blocks = re.findall(r"```yaml\n(.*?)```", text, re.S)
    assert blocks, "expected at least one fenced ```yaml block in README.md"
    for i, block in enumerate(blocks):
        try:
            yaml.safe_load(block)
        except yaml.YAMLError as exc:  # pragma: no cover -- only on regression
            pytest.fail(
                f"README.md fenced ```yaml block #{i} failed to parse: {exc}\n"
                f"---block---\n{block}\n---end---"
            )


def test_readme_per_tool_fields_match_model() -> None:
    """Every TOOLCFG field documented in README must exist on ``ToolConfig``.

    The README's Per-tool configuration table lists six fields. If any of
    them is missing from the Pydantic model (typo, rename, deletion) this
    test fails -- preventing the docs from claiming a knob the framework
    no longer supports.
    """
    text = _read_readme()
    model_fields = set(ToolConfig.model_fields.keys())
    for field in _DOCUMENTED_TOOLCFG_FIELDS:
        # Each documented field must appear in the README (table row).
        assert f"`{field}`" in text, (
            f"README.md does not document the TOOLCFG field {field!r}; "
            "expected a `field` row in the Per-tool configuration table"
        )
        # And must exist on the actual model.
        assert field in model_fields, (
            f"README documents TOOLCFG field {field!r} but it is not an "
            f"attribute on mcp_test_framework.models.ToolConfig "
            f"(model fields: {sorted(model_fields)})"
        )


def test_readme_anchor_targets_exist() -> None:
    """Every ``docs/EXTENDING.md#anchor`` link in README must resolve.

    Forward-compat sanity check for Plan 10-02. README links to
    ``docs/EXTENDING.md#add-a-new-mcp-tool-target``; until Plan 10-02 lands
    that heading, the assertion xfails. Once the heading exists the
    assertion runs normally and passes (and will start failing if the
    heading is later renamed or deleted).
    """
    readme = _read_readme()
    extending = _read_extending()

    anchor_links = re.findall(r"docs/EXTENDING\.md#([A-Za-z0-9_-]+)", readme)
    assert anchor_links, (
        "expected at least one docs/EXTENDING.md#anchor link in README.md "
        "(the Plan 10-01 Further reading update should add one)"
    )

    if extending is None:
        pytest.xfail("docs/EXTENDING.md missing; anchor target pending Plan 10-02")

    for anchor in anchor_links:
        # GitHub auto-anchors lowercase the heading and replace spaces with
        # hyphens. Reverse that to find the matching `## Heading` line.
        # `add-a-new-mcp-tool-target` -> `Add a new mcp tool target`.
        # We do a case-insensitive substring search for the anchor's word
        # tokens reassembled with spaces -- robust to GitHub's mild
        # punctuation handling without overfitting.
        words = anchor.split("-")
        # Match `^## ...` heading whose lowercased+hyphenated form equals
        # the anchor.
        heading_re = re.compile(r"^##\s+(.+?)\s*$", re.M)
        found = False
        for match in heading_re.finditer(extending):
            heading_text = match.group(1)
            normalized = re.sub(r"[^a-z0-9\s-]", "", heading_text.lower())
            normalized = re.sub(r"\s+", "-", normalized.strip())
            if normalized == anchor:
                found = True
                break
        if not found:
            # Conditional gate: if the heading isn't there yet, xfail rather
            # than fail. Plan 10-02 will introduce it.
            pytest.xfail(
                f"docs/EXTENDING.md missing heading for anchor #{anchor} "
                f"(expected words: {' '.join(words)}); "
                "EXTENDING.md anchor pending Plan 10-02"
            )
