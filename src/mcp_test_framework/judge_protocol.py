"""Pluggable LLM-judge seam (CORE-04, SEED-001 enabler).

Defines the runtime-checkable ``Judge`` Protocol with the spec-verbatim
async ``judge(rubric, subject, context=None) -> JudgeResult`` signature
per Phase 3 CONTEXT.md decisions D-05 and D-06.

Why ``typing.Protocol`` rather than ``abc.ABC``:
- Structural typing matches the project's "result types live in their
  owning module" convention (``ToolNotFoundError`` in ``mcp_client.py``,
  ``ValidationIssue`` in ``schema_validator.py``); a Protocol does not
  force concrete classes to inherit from a framework type.
- ``@typing.runtime_checkable`` lets the Phase 3 smoke test
  (``tests/smoke/test_smoke_ollama_judge.py``, SC#1 falsifier) assert
  ``isinstance(OllamaJudge(...), Judge)`` without importing the concrete
  class -- the smoke catches the seam regression mechanically.
- The Protocol lives in its own file so a post-MVP ``AgenticJudge``
  (SEED-001) imports the Protocol without pulling in the rubric-style
  ``OllamaJudge`` implementation. That keeps SEED-001 a 1-file
  addition rather than a rewrite (CORE-04 "Judge Protocol seam").

Why import ``JudgeResult`` from ``ollama_judge.py`` rather than re-exporting
from ``models.py``:
- ``JudgeResult`` is a domain-local result type (parallels
  ``ToolNotFoundError``); CONTEXT D-04 / Established Patterns put it in
  the owning module. ``models.py`` holds only cross-cutting Config
  sub-models.
- One-way dependency: ``judge_protocol.py`` -> ``ollama_judge.py``. The
  concrete module never imports from this file, so there is no circular
  import.

WARNING: ``@runtime_checkable`` only checks attribute presence by name --
it does NOT validate signature compatibility (PEP 544 limitation). A class
exposing ``def judge(self, ...)`` (sync) or ``def judge(self) -> int``
(wrong signature) will still pass ``isinstance(x, Judge)``. Phase 3
SC#1 is therefore made load-bearing by the smoke test asserting both
``isinstance(...)`` AND ``inspect.signature`` shape AND
``inspect.iscoroutinefunction``. See PITFALLS Pitfall 4.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from mcp_test_framework.ollama_judge import JudgeResult


@runtime_checkable
class Judge(Protocol):
    """Pluggable LLM-judge seam (CORE-04, SEED-001 enabler).

    Implementations evaluate a ``subject`` against a ``rubric`` and return
    a :class:`JudgeResult`. The optional ``context`` is free-form to
    accommodate post-MVP backends (e.g., SEED-001 reflection traces) without
    forcing a typed wrapper -- per D-05.
    """

    async def judge(
        self,
        rubric: str,
        subject: str,
        context: dict | None = None,
    ) -> JudgeResult: ...
