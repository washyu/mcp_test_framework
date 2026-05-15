---
phase: 24-tool-call-serializer-omits-unset-optional-params-exclude-uns
reviewed: 2026-05-15T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - docs/SDET-AUTHORING.md
  - src/mcp_test_framework/sdet/_tool_factory.py
  - tests/framework/unit/test_tool_factory.py
findings:
  blocker: 0
  warning: 3
  total: 3
status: issues_found
---

# Phase 24: Code Review Report

**Reviewed:** 2026-05-15
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Phase 24's core change is sound: a single-line serializer kwarg flip from
`params.model_dump(mode="json")` to
`params.model_dump(mode="json", exclude_unset=True)` at
`src/mcp_test_framework/sdet/_tool_factory.py:101`, accompanied by three new
payload-asserting tests and one renamed-and-extended kwargs-spy test, plus
a doc softening on the inputSchema workaround.

The serializer change preserves the SEED-022 principle — `exclude_unset`
discriminates on **user intent** (did the SDET touch the attribute on the
constructor?) rather than on **value**, so explicit `field=None` still puts
`null` on the wire. Module docstrings and the spy test are updated to lock
the new kwarg combination in place. The change is local, behavior-preserving
for "explicitly set" payloads, and the test additions cover the three
intent-discriminator cells: unset → omitted, explicit-None → null,
explicit-value → unchanged.

Findings below are all WARNING severity. The change itself is correct and
its tests are well-targeted; the issues sit in the doc framing and in
defensive coverage that the new tests didn't quite reach.

## Warnings

### WR-01: Doc claim "You generally won't hit this bug" is too strong for tools with required null-default fields

**File:** `docs/SDET-AUTHORING.md:259-268`
**Issue:** The new framing block says, "You generally won't hit this bug. As
of Phase 24 the framework's `tool().call()` serializer uses
`model_dump(mode='json', exclude_unset=True)`, which means optional Pydantic
fields that you never set on the params constructor stay off the wire
entirely."

This is true in the narrow case that the contradictory upstream field is
**optional in the inputSchema** (so codegen emits it with a default and the
SDET can legitimately omit it). But the same homelab-mcp class of bug also
manifests on fields that the upstream `inputSchema` declares as
**`required`** with `type: "string"` and an in-schema `default: null` — the
codegen-emitted class will then have that field as a required constructor
arg, the SDET cannot omit it, and `exclude_unset=True` does not help. The
doc's escape-hatch (a `_CpuBump*` subclass with `extra="allow"`) is still
needed in that case, but the new "you generally won't hit this bug" framing
buries that nuance.

Two readers' worth of harm:

1. An SDET who reads "you generally won't hit this" stops worrying and
   then hits a hard ValidationError or wire-side rejection on a required
   field they had no choice but to set.
2. The framing also blurs the `extra="forbid"` half of the upstream bug,
   which is independent of `exclude_unset` — `exclude_unset` controls
   what Pydantic emits FROM a model, not what Pydantic ACCEPTS INTO a
   model. The `_CpuBump*` subclass exists because upstream's declared
   schema is `extra="forbid"` and rejects the action payload; that
   rejection happens at constructor time, before `model_dump` runs.

**Fix:** Tighten the claim. Suggested wording:

```markdown
**You generally won't hit this bug for OPTIONAL fields.** As of Phase 24
the framework's `tool().call()` serializer uses
`model_dump(mode="json", exclude_unset=True)`, which means optional
Pydantic fields that you never set on the params constructor stay off
the wire entirely. The contradiction still surfaces on (a) fields the
upstream `inputSchema` declares as REQUIRED with a `null` default, since
the SDET has no choice but to construct them, and (b) tools whose
declared `extra="forbid"` rejects a polymorphic payload shape at
constructor time — both cases still need the `extra="allow"` escape
hatch below.
```

### WR-02: No test pins behavior for a field constructed with its declared default value

**File:** `tests/framework/unit/test_tool_factory.py:228-309`
**Issue:** The three new payload-asserting tests cover (1) unset → omitted,
(2) explicit-None → present-as-null, and (3) explicit-value → present-as-value.
A fourth cell is missing: **field constructed with the same value as its
declared default**. Pydantic v2 treats this as `set` because the field
appeared in the constructor — so the serializer will emit it, even though
the SDET wrote the literal default value.

Example:

```python
# _FakeParamsWithOptional declares `cdrom: str | None = None`.
# This call DOES emit `cdrom: null` on the wire, because cdrom was passed.
await wrapper.call(_FakeParamsWithOptional(name="x", cdrom=None))
```

The existing `test_call_serializes_explicit_none_to_wire_null` happens to
hit this exact case because the default IS `None`, but the test reads as
testing "explicit None" rather than the more general "any constructor-passed
value, even the declared default, is `set`". A non-None default would expose
the gap:

```python
class _FakeParamsWithStringDefault(BaseModel):
    name: str
    cdrom: str = "/iso/default.iso"

# This call ALSO emits `cdrom: "/iso/default.iso"` on the wire because
# the constructor saw it -- even though the SDET passed the declared
# default. exclude_unset=True does not "exclude_redundant".
await wrapper.call(_FakeParamsWithStringDefault(name="x", cdrom="/iso/default.iso"))
# sent_args == {"name": "x", "cdrom": "/iso/default.iso"}  # not {"name": "x"}
```

Without this pin, a future maintainer reading only the existing three tests
could conclude that `exclude_unset` is "smart" about default-equality and
swap in `exclude_defaults=True` without breaking the existing suite — at
which point an SDET who explicitly wrote `cdrom="/iso/default.iso"` to
test the server's handling of the default would silently lose the field on
the wire. That is exactly the SEED-022-violating regression the new tests
are supposed to prevent.

**Fix:** Add a fourth payload-asserting test:

```python
@pytest.mark.asyncio
async def test_call_emits_field_set_to_its_declared_default() -> None:
    """Phase 24 SERIALIZER-01 / SEED-022: exclude_unset is intent-driven, not
    value-driven. A field the SDET constructs with the same value as its
    declared default IS `set` and MUST appear on the wire -- preventing a
    future swap to exclude_defaults=True from silently dropping payloads."""
    class _ParamsWithStringDefault(BaseModel):
        name: str
        cdrom: str = "/iso/default.iso"

    # ... usual stub-client wiring ...
    await wrapper.call(_ParamsWithStringDefault(name="x", cdrom="/iso/default.iso"))
    sent_args = stub.calls[0][1]
    assert sent_args == {"name": "x", "cdrom": "/iso/default.iso"}
```

### WR-03: `_FakeParamsWithOptional` declares `extra="allow"`-free; doesn't pin behavior under the `extra="forbid"` codegen shape used in practice

**File:** `tests/framework/unit/test_tool_factory.py:32-44`
**Issue:** The new `_FakeParamsWithOptional` test fixture is a bare
`BaseModel` (default `extra="ignore"`). The codegen-emitted classes that
actually flow through `tool().call()` in production (e.g. the
`ManageProxmoxVmParams` the doc references) are
`model_config = ConfigDict(extra="forbid")` per the upstream declared
schema — that is the shape the inputSchema bug fires against.

`exclude_unset` semantics are identical between `extra="ignore"` and
`extra="forbid"` models, so the new tests' assertions are correct as far as
they go. But the test class does not look like the production class, and a
reader trying to reason about the homelab-mcp bug — "would the framework
have emitted `cdrom: null` for an `extra="forbid"` model the way it does
for the `extra="ignore"` test fixture?" — has to take it on faith. A more
faithful fixture would let `pyright`-strict readers and future maintainers
trace the test back to the bug it fixed.

**Fix:** Pin the fixture to the production shape:

```python
from pydantic import ConfigDict

class _FakeParamsWithOptional(BaseModel):
    """Phase 24: fixture for exclude_unset semantics tests.

    Mirrors the upstream shape that triggered the homelab-mcp inputSchema bug:
    extra='forbid' (matching codegen output), one required field + one optional
    field with `None` default. ...
    """
    model_config = ConfigDict(extra="forbid")
    name: str
    cdrom: str | None = None
```

This is a low-impact pin — every existing assertion in the three new tests
still passes verbatim — but it tightens the fidelity between the test
fixture and the production codegen output that the bug actually surfaces
through.

---

_Reviewed: 2026-05-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
