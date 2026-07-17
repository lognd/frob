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
