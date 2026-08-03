"""NEGEXIST001: negative-existence prose claims must be bound to a ticket
(docs/modules/gates.md, T-1229, gate-gap class 3 in
docs/audits/docs-staleness-2026-07-29.md).

Motivating case: doc prose like "X does not exist yet" or "not yet wired"
is unanchorable to anything DRIFT001/DOC006 can re-verify -- there is no
symbol to digest, no pointer to resolve -- so the claim silently rots the
moment X ships (the 2026-07-29 audit found ~20 shipped-but-documented-as-
absent instances this way).

The fix is a `frob:until T-####` markdown-side directive
(`<!-- frob:until T-#### -->`, `frob.graph.dsl._UNTIL_RE`) that binds the
prose to the ticket that will build the not-yet-built thing, placed under
the same heading anchor as the claim. `markdown_anchors` also heuristically
detects the claim itself (`_NEGEXIST_PHRASE_RE`) and emits both as edges
sharing the doc's `<doc>#<anchor>` `src`, so this gate never re-reads
markdown text -- it groups already-parsed `GraphSnapshot.edges` instead.

NEGEXIST001 fires in the two ways a negative-existence claim can go stale:
1. UNBOUND: an anchor section has a `CLAIMS_ABSENCE` claim but no sibling
   `UNTIL` edge at all -- nothing will ever catch it when the thing ships.
2. STALE: an anchor section's `UNTIL` edge names a ticket that has already
   closed/archived (not open) -- the claim should have been updated or
   removed when that ticket shipped, and was not.
A claim heuristic match is inherently best-effort (a fixed phrase list,
`frob.graph.dsl._NEGEXIST_PHRASE_RE`'s own docstring) -- a false negative
here just means an unrelated claim goes unflagged, never a false failure.
"""
# frob:ticket T-1229

from __future__ import annotations

from frob.gates._models import Severity, Violation
from frob.graph._models import EdgeKind, GraphSnapshot
from frob.logging import get_logger
from frob.tickets import TicketQueue

_log = get_logger(__name__)

__all__ = ["negexist001_gate"]


def _site_from_origin(origin: str) -> tuple[str, int]:
    """Best-effort `(file, line)` split of an edge's `path:line` origin,
    mirroring `frob.gates._docenum._site_from_origin`'s shape."""
    file_part, _, line_part = origin.rpartition(":")
    if line_part.isdigit():
        return file_part, int(line_part)
    return origin, 0


# frob:doc docs/modules/gates.md#negexist001-gate-t-1229
# frob:enforces CHK-GATE-NEGEXIST001
# frob:tests tests/unit/gates/test_negexist.py::TestNegexist001Gate.test_unbound_claim_is_flagged  # noqa: E501
# frob:tests tests/unit/gates/test_negexist.py::TestNegexist001Gate.test_claim_bound_to_open_ticket_is_clean  # noqa: E501
# frob:tests tests/unit/gates/test_negexist.py::TestNegexist001Gate.test_claim_bound_to_closed_ticket_is_stale  # noqa: E501
# frob:tests tests/unit/gates/test_negexist.py::TestNegexist001Gate.test_claim_bound_to_missing_ticket_is_stale  # noqa: E501
# frob:tests tests/unit/gates/test_negexist.py::TestNegexist001Gate.test_no_claims_at_all_is_clean  # noqa: E501
def negexist001_gate(
    snapshot: GraphSnapshot, queue: TicketQueue
) -> tuple[Violation, ...]:
    """NEGEXIST001 (T-1229): every `CLAIMS_ABSENCE` heuristic-matched
    negative-existence prose claim must share its doc anchor (`<doc>#
    <anchor>`) with a `frob:until T-####` `UNTIL` edge naming a currently
    OPEN ticket -- unbound (no `UNTIL` edge at all) or stale (the named
    ticket already closed/archived) both fire, at WARN (a heuristic prose
    match, never a hard structural fact the way DOCENUM001's AST diff is)."""
    from frob.gates import _OPEN_STATES

    claims = [e for e in snapshot.edges if e.kind == EdgeKind.CLAIMS_ABSENCE]
    if not claims:
        _log.info("negexist001: 0 violation(s)")
        return ()

    until_by_anchor: dict[str, list[str]] = {}
    for edge in snapshot.edges:
        if edge.kind == EdgeKind.UNTIL:
            until_by_anchor.setdefault(edge.src, []).append(edge.target)

    violations: list[Violation] = []
    for claim in claims:
        file, line = _site_from_origin(claim.origin)
        ticket_ids = until_by_anchor.get(claim.src, [])
        if not ticket_ids:
            violations.append(
                Violation(
                    rule="NEGEXIST001",
                    severity=Severity.WARN,
                    file=file,
                    line=line,
                    message=(
                        f"NEGEXIST001: negative-existence claim {claim.target!r} "
                        f"at {claim.src} has no `frob:until T-####` directive "
                        f"binding it to the ticket that will build it -- add "
                        f"`<!-- frob:until T-#### -->` under the same heading, "
                        f"or the claim will silently rot once shipped"
                    ),
                )
            )
            continue
        open_tickets = [
            tid
            for tid in ticket_ids
            if (t := queue.tickets.get(tid)) is not None and t.state in _OPEN_STATES
        ]
        if open_tickets:
            continue
        _log.debug(
            "NEGEXIST001: %s stale (bound tickets closed: %s)", claim.src, ticket_ids
        )
        violations.append(
            Violation(
                rule="NEGEXIST001",
                severity=Severity.WARN,
                file=file,
                line=line,
                message=(
                    f"NEGEXIST001: negative-existence claim {claim.target!r} "
                    f"at {claim.src} is bound to {ticket_ids!r}, but none is "
                    f"open (missing or already closed/archived) -- the claim "
                    f"is likely stale now; verify the thing still does not "
                    f"exist and rebind, or update the prose"
                ),
            )
        )
    _log.info("negexist001: %d violation(s)", len(violations))
    return tuple(violations)
