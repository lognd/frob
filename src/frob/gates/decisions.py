"""Architecture Decision Records (ADR) loading + DEC gate rules (T-0004).

A decision record is a tracked `decisions/AD-###.md` file with a status and
rationale; code that implements a decision anchors it with a
`frob:decision AD-###` directive. The DEC gates close the loop the same way
INV does for invariants: an accepted decision must be anchored in code, and
a `frob:decision` edge must point at a real record. So the "why" behind a
choice cannot silently rot away from the code that embodies it.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.graph import EdgeKind, GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?\n)---\n(.*)\Z", re.DOTALL)
_AD_ID_RE = re.compile(r"^AD-\d{3}$")


# frob:doc docs/modules/decisions.md#data-models
# frob:waive COV007 reason="docs/modules/decisions.md's Data models \
# section individually frob:describes this private enum by name \
# (T-0529) -- a deliberate architecture doc, not accidental drift onto a \
# private helper"
class _DecisionStatus(StrEnum):
    """The lifecycle state of an ADR."""

    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"
    DEPRECATED = "deprecated"


# frob:doc docs/modules/decisions.md#data-models
class Decision(BaseModel):
    """One architecture decision record parsed from decisions/AD-###.md."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title: str
    status: _DecisionStatus
    superseded_by: str | None = None


# frob:doc docs/modules/decisions.md#data-models
class DecisionError(ErrorSet):
    """Fallible outcomes of loading decision records."""

    Malformed = "A decision record failed schema validation"
    DuplicateId = "Two decision records share an id"
    BadId = "Decision id is not AD-###"


# frob:doc docs/modules/decisions.md#anchoring-in-code
def decisions_dir(root: Path) -> Path:
    """The tracked decisions/ directory holding AD-###.md records."""
    return root / "decisions"


# frob:doc docs/modules/decisions.md#anchoring-in-code
# frob:waive TEST005 reason="load_decisions 64.3% branch cover, debt T-0160"
def load_decisions(root: Path) -> Result[tuple[Decision, ...], DecisionError]:
    """Parse every decisions/AD-###.md record; any malformation is a hard Err."""
    d = decisions_dir(root)
    if not d.exists():
        return Ok(())
    seen: dict[str, Decision] = {}
    record_paths = sorted(d.glob("AD-*.md"))
    for path in record_paths:
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(text)
        if match is None:
            _log.error("decisions: %s has no frontmatter", path)
            return Err(DecisionError.Malformed)
        try:
            data = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            _log.error("decisions: %s bad YAML: %s", path, exc)
            return Err(DecisionError.Malformed)
        if not isinstance(data, dict):
            return Err(DecisionError.Malformed)
        try:
            decision = Decision.model_validate(data)
        except ValidationError as exc:
            _log.error("decisions: %s failed validation: %s", path, exc)
            return Err(DecisionError.Malformed)
        if not _AD_ID_RE.match(decision.id):
            return Err(DecisionError.BadId)
        if decision.id in seen:
            return Err(DecisionError.DuplicateId)
        seen[decision.id] = decision
    return Ok(tuple(seen.values()))


def _dec001(known: set[str], snapshot: GraphSnapshot) -> list:
    """DEC001: a `frob:decision` edge targets a record that does not exist."""
    from frob.gates._models import Severity, Violation

    violations = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.DECISION or edge.target in known:
            continue
        file, _, line = edge.origin.rpartition(":")
        violations.append(
            Violation(
                rule="DEC001",
                severity=Severity.ERROR,
                file=file or edge.src,
                line=int(line) if line.isdigit() else 0,
                message=(
                    f"DEC001: frob:decision {edge.target} has no "
                    f"decisions/{edge.target}.md record"
                ),
            )
        )
    return violations


def _anchored_decisions(snapshot: GraphSnapshot) -> set[str]:
    """Decision ids carrying a `frob:decision` anchor edge in code."""
    return {e.target for e in snapshot.edges if e.kind == EdgeKind.DECISION}


def _dec002(decisions: tuple[Decision, ...], anchored: set[str]) -> list:
    """DEC002: an accepted decision has no `frob:decision` anchor in code."""
    from frob.gates._models import Severity, Violation

    violations = []
    for decision in decisions:
        if decision.status != _DecisionStatus.ACCEPTED or decision.id in anchored:
            continue
        violations.append(
            Violation(
                rule="DEC002",
                severity=Severity.ERROR,
                file=f"decisions/{decision.id}.md",
                line=0,
                message=(
                    f"DEC002: accepted decision {decision.id} has no "
                    f"frob:decision anchor in code"
                ),
            )
        )
    return violations


# frob:doc docs/modules/decisions.md#anchoring-in-code
def decision_gate(decisions: tuple[Decision, ...], snapshot: GraphSnapshot) -> tuple:
    """DEC001/DEC002 over decision records and their code anchors.

    DEC001: a `frob:decision AD-###` edge targets a record that does not
    exist. DEC002: an accepted decision has no `frob:decision` anchor in
    code (an accepted-but-unimplemented decision is drift). Returns
    `Violation`s; the import is local to avoid a cycle with frob.gates.
    """
    known = {d.id for d in decisions}
    anchored = _anchored_decisions(snapshot)
    violations = [*_dec001(known, snapshot), *_dec002(decisions, anchored)]
    _log.info(
        "decision_gate: %d record(s), %d violation(s)",
        len(decisions),
        len(violations),
    )
    return tuple(violations)


__all__ = [
    "Decision",
    "DecisionError",
    "_DecisionStatus",
    "decision_gate",
    "decisions_dir",
    "load_decisions",
]
