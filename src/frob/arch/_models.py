"""Result models for the architectural analysis (docs/modules/arch.md's data shapes)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel

ArchCategory = Literal[
    "long-function",
    "god-class",
    "high-coupling",
    "deep-nesting",
    "abstraction-opportunity",
    "large-file",
    # T-0332: advisory design-pattern recommender categories -- a detected
    # structural HALLMARK maps to a recommended GoF/modern PATTERN, or a
    # detected ANTI-PATTERN maps to a concrete ESCAPE route. Both stay on
    # the unwaivable advisory channel like every other category here
    # (`frob.gates._unwaivable_channel_rules`) -- see docs/modules/arch.md's
    # "design-pattern recommender" section for the registry.
    "pattern-recommendation",
    "anti-pattern-escape",
    # T-0616: SRP/cohesion family (ARCH1xx), written once against the T-0609
    # normalized model (`frob.arch._srp`) so each fires identically across
    # every `LanguageAdapter` -- see docs/modules/arch.md's "SRP/cohesion
    # checks" section for the per-category proxy definition.
    "low-cohesion-class",
    "god-module",
    "mixed-concern-function",
    # T-0617: OCP checks (ARCH1xx family, T-0330's SOLID catalog). Both stay
    # on the unwaivable advisory channel like every other category here
    # (`frob.gates._unwaivable_channel_rules`) until a future ticket wires a
    # real ARCH1xx gate (the T-0289 pattern ARCH001 already established);
    # `symref`/`metric` are populated on every finding so that wiring is a
    # gate-side addition, not a re-instrumentation of these checks.
    "type-dispatch-smell",
    "non-exhaustive-enum-match",
]

ArchSeverity = Literal["warning", "suggestion", "info"]


# frob:doc docs/modules/arch.md#arch-suggestion
class ArchSuggestion(BaseModel):
    file: str
    line: int | None = None
    category: ArchCategory
    severity: ArchSeverity
    message: str
    detail: str | None = None
    # T-0289: set for checks that are about exactly one symbol (currently
    # long-function) so `frob.gates`' ARCH001 job can bind a `frob:waive`
    # directive to the precise function (`path::qualname`) instead of the
    # whole file, and so a `ceiling=` waiver can compare against `metric`.
    symref: str | None = None
    # T-0289: the raw measured value the finding is about (e.g. a
    # long-function's line count) -- lets a reasoned waiver's `ceiling=N`
    # re-fire once the function outgrows the ceiling, instead of muting it
    # permanently.
    metric: int | None = None


# frob:doc docs/modules/arch.md#arch-result
class ArchResult(BaseModel):
    root: str
    suggestions: list[ArchSuggestion]

    def as_text(self) -> str:
        # frob:doc docs/modules/arch.md#arch-result
        if not self.suggestions:
            return "no architectural issues found"
        lines: list[str] = []
        for s in self.suggestions:
            loc = s.file
            if s.line is not None:
                loc = f"{loc}:{s.line}"
            lines.append(f"{loc}  {s.severity}  {s.category}")
            lines.append(f"  {s.message}")
            if s.detail:
                lines.append(f"  {s.detail}")
        return "\n".join(lines)

    def as_json(self) -> str:
        # frob:doc docs/modules/arch.md#arch-result
        return json.dumps(self.model_dump(), indent=2)
