"""frob.gates._milestone -- MILE00x milestone-resolution gate family
(T-2576 M2).

M2 was originally scoped as a bulk backfill of `milestone: 1.0.0` into
every open ticket file plus MILE003. The coordinator redesigned it
(T-2576's own ticket body, "SCOPE REDESIGN" section): the backfill would
have required a write lease on every ticket file simultaneously, which
could only run with the whole fleet stopped. A read-time default
(`[tickets].default_milestone` in `frob.toml`, resolved by
`frob.tickets._doable.effective_milestone`'s TERMINAL fallback) gives the
identical result with zero ticket-file writes. This module is only the
MILE003 gate on top of that resolution -- M1 (T-2574, `Ticket.milestone`
+ semver ordering) and M3 (T-2577, the declared/inherited walk) already
landed; this module reuses `effective_milestone` verbatim rather than
re-deriving any part of that chain (T-2576's own coordination note: "the
resolution function must have exactly ONE home").
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.logging import get_logger
from frob.tickets import Ticket, TicketQueue, TicketState

_log = get_logger(__name__)

#: Terminal `TicketState`s -- same set `_tickets_gate.py`'s own
#: `_TERMINAL_STATES` uses; duplicated here rather than imported since
#: `_tickets_gate` is a sibling family module, not a shared dependency
#: this one should reach into.
_TERMINAL_STATES = (TicketState.DONE, TicketState.DROPPED)


# frob:enforces CHK-GATE-MILE003
# frob:ticket T-2576
# frob:tests tests/test_gates_milestone.py::TestMile003.test_fires_on_open_ticket_with_no_resolvable_milestone  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_silent_once_stamped  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_silent_on_configured_default  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_silent_on_inherited_value  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_terminal_ticket_never_fires  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_no_default_configured_still_fires  # noqa: E501
def _mile003_unresolved_milestone(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """MILE003 (ERROR): one violation per OPEN ticket (any tier -- an
    epic/story with no declared milestone is just as unresolved as a leaf)
    whose EFFECTIVE milestone (`frob.tickets._doable.effective_milestone`,
    given `root` so the configured `[tickets].default_milestone` is
    consulted as the terminal fallback) cannot be RESOLVED: no milestone
    declared on the ticket itself, none on any ancestor, AND no repo
    default configured. This is what stops a new ticket silently skipping
    the field after M1 added it (T-2576's own Description) -- and, per the
    redesign, is now the ONLY enforcement mechanism; nothing backfills the
    ledger to make this vacuously pass.

    Fires on ANY value of `None` from `effective_milestone` regardless of
    the (irrelevant, since there is no value) `MilestoneSource` -- a
    `DECLARED`/`INHERITED`/`DEFAULTED` resolution never reaches here at
    all, `effective_milestone` returned a real string for each of those
    three.

    A terminal ticket (done/dropped, `_TERMINAL_STATES`) never fires --
    it does not sequence again, so an unresolved milestone on it is not a
    live finding (same reasoning T-2576's Description gives for excluding
    terminal tickets from the abandoned backfill).

    `queue` is the gate's already-loaded `TicketQueue` (`st.queue`,
    `run_gates`'s own `_load_graph_queue_lock` step) -- a queue-load
    failure never reaches this function at all; `run_gates` hard-Errs the
    WHOLE run via `GateError.QueueUnavailable` before any gate (this one
    included) runs, so MILE003 finding zero here is never confusable with
    "the queue could not be read" -- that failure mode produces no gate
    report whatsoever, not a clean one. Same defense-in-depth posture
    `_tick001_duplicate_ids`'s own docstring documents for TICK001."""
    from frob.tickets._doable import effective_milestone

    violations: list[Violation] = []
    for t in sorted(queue.tickets.values(), key=lambda t: t.id):
        if t.state in _TERMINAL_STATES:
            continue
        milestone, _source = effective_milestone(queue, t, root)
        if milestone is not None:
            continue
        violations.append(
            Violation(
                rule="MILE003",
                severity=Severity.ERROR,
                file="tickets.md",
                line=0,
                message=(
                    f"MILE003: {t.id} ({t.state.value}) has no resolvable "
                    f"milestone -- no `milestone` declared on the ticket "
                    f"itself, none on any ancestor, and this repo "
                    f"configures no `[tickets].default_milestone` in "
                    f"frob.toml; set one with `frob ticket milestone "
                    f"{t.id} --set VALUE`, or configure a repo default"
                ),
            )
        )
    return tuple(violations)


# frob:enforces CHK-GATE-MILE001
# frob:ticket T-2580
# frob:tests tests/test_gates_milestone.py::TestMile001.test_blocked_by_later_milestone_fires  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile001.test_blocked_by_earlier_milestone_does_not_fire  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile001.test_blocked_by_same_milestone_does_not_fire  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile001.test_terminal_blocker_does_not_fire  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile001.test_terminal_ticket_never_fires  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile001.test_unresolved_milestone_does_not_fire  # noqa: E501
def _mile001_blocked_by_later_milestone(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """MILE001 (ERROR): an OPEN ticket `blocked_by` another OPEN ticket
    whose EFFECTIVE milestone (`effective_milestone`) is LATER (real
    semver order, `packaging.version.Version` -- same comparison
    `_doable_sort_key` uses, never a string compare) than the blocked
    ticket's own effective milestone. This is a provable release
    deadlock: the earlier milestone can never ship, since it depends on
    work the later milestone has not done yet.

    A blocker that has already gone terminal (done/dropped) is not a live
    deadlock -- the dependency is satisfied regardless of what milestone
    it was ever filed against, so it is excluded here the same way
    `_TERMINAL_STATES` excludes a terminal blocked-ticket outright. An
    unresolved id in `blocked_by` (no matching ticket in `queue`) is
    TICK-family's concern, not this one's -- skipped, not flagged twice.
    Either side's milestone failing to resolve at all is MILE003's
    concern -- this gate only compares two REAL values, never guesses one
    is "later" than an absent one."""
    from packaging.version import Version

    from frob.tickets._doable import effective_milestone

    violations: list[Violation] = []
    for t in sorted(queue.tickets.values(), key=lambda t: t.id):
        if t.state in _TERMINAL_STATES:
            continue
        t_milestone, _t_source = effective_milestone(queue, t, root)
        if t_milestone is None:
            continue
        # frob:waive PERF004 reason="t.blocked_by is a single ticket's own blocked-by set, bounded by how many other tickets one ticket names (tens at most, never repo-scale); re-sorting it is required for deterministic MILE001 output ordering, not a hot-path re-sort"  # noqa: E501
        for blocker_id in sorted(t.blocked_by):
            blocker = queue.tickets.get(blocker_id)
            if blocker is None or blocker.state in _TERMINAL_STATES:
                continue
            blocker_milestone, _b_source = effective_milestone(queue, blocker, root)
            if blocker_milestone is None:
                continue
            if Version(blocker_milestone) <= Version(t_milestone):
                continue
            violations.append(
                Violation(
                    rule="MILE001",
                    severity=Severity.ERROR,
                    file="tickets.md",
                    line=0,
                    message=(
                        f"MILE001: {t.id} (milestone {t_milestone}) is "
                        f"blocked_by {blocker.id} (milestone "
                        f"{blocker_milestone}) -- a release deadlock, "
                        f"{t_milestone} can never ship while it depends "
                        f"on work scheduled for the later milestone "
                        f"{blocker_milestone}"
                    ),
                )
            )
    return tuple(violations)


# frob:ticket T-2580
def _children_by_parent(queue: TicketQueue) -> dict[str, list[Ticket]]:
    """`{parent_id: [direct children]}` over every ticket in `queue` --
    the adjacency map both `_mile002_descendant_later_milestone`'s BFS
    and any future hierarchy walk in this module can reuse, factored out
    so the caller stays under the module's line-count budget rather than
    building it inline."""
    children_of: dict[str, list[Ticket]] = {}
    for t in queue.tickets.values():
        if t.parent is not None:
            children_of.setdefault(t.parent, []).append(t)
    return children_of


# frob:ticket T-2580
def _descendants_of(
    ticket_id: str, children_of: dict[str, list[Ticket]]
) -> list[Ticket]:
    """Every descendant of `ticket_id` at any depth, via BFS over
    `children_of` (`_children_by_parent`'s output) -- same walk shape
    `_open_descendant_ids` (`frob.tickets._evidence`) uses for its own
    open-descendant check, kept as a local helper rather than importing
    that private one since this caller needs the full `Ticket` objects
    for milestone comparison, not a bare open/closed id list."""
    frontier = [ticket_id]
    seen = {ticket_id}
    descendants: list[Ticket] = []
    while frontier:
        current = frontier.pop()
        for child in children_of.get(current, ()):
            if child.id in seen:
                continue
            seen.add(child.id)
            descendants.append(child)
            frontier.append(child.id)
    return descendants


# frob:enforces CHK-GATE-MILE002
# frob:ticket T-2580
# frob:tests tests/test_gates_milestone.py::TestMile002.test_descendant_in_later_milestone_fires  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile002.test_descendant_in_earlier_or_same_milestone_does_not_fire  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile002.test_terminal_descendant_does_not_fire  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile002.test_terminal_ancestor_never_fires  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile002.test_grandchild_descendant_fires  # noqa: E501
def _mile002_descendant_later_milestone(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """MILE002 (ERROR): an OPEN ticket with an OPEN descendant (any depth
    via `parent`, `_descendants_of`) whose EFFECTIVE milestone is LATER
    than the ancestor's own. Same deadlock as MILE001, reached via the
    hierarchy instead of `blocked_by`: `_done_transition_guard` already
    forbids an epic/story from closing DONE while any descendant is
    still open, so an ancestor can never close before its later-milestone
    descendant does -- meaning the ancestor's own (earlier) milestone can
    never ship either. This is that existing structural rule projected
    onto milestones, caught statically instead of only at close time."""
    from packaging.version import Version

    from frob.tickets._doable import effective_milestone

    children_of = _children_by_parent(queue)

    violations: list[Violation] = []
    for ancestor in sorted(queue.tickets.values(), key=lambda t: t.id):
        if ancestor.state in _TERMINAL_STATES:
            continue
        ancestor_milestone, _a_source = effective_milestone(queue, ancestor, root)
        if ancestor_milestone is None:
            continue
        descendants = _descendants_of(ancestor.id, children_of)
        # frob:waive PERF004 reason="descendants is one ancestor ticket's own child subtree, bounded by ticket-tree fanout (tens at most); re-sorting is required for deterministic output ordering, not a hot-path re-sort"  # noqa: E501
        for descendant in sorted(descendants, key=lambda t: t.id):
            if descendant.state in _TERMINAL_STATES:
                continue
            descendant_milestone, _d_source = effective_milestone(
                queue, descendant, root
            )
            if descendant_milestone is None:
                continue
            if Version(descendant_milestone) <= Version(ancestor_milestone):
                continue
            violations.append(
                Violation(
                    rule="MILE002",
                    severity=Severity.ERROR,
                    file="tickets.md",
                    line=0,
                    message=(
                        f"MILE002: {ancestor.id} (milestone "
                        f"{ancestor_milestone}) has descendant "
                        f"{descendant.id} (milestone "
                        f"{descendant_milestone}) -- a release deadlock, "
                        f"{ancestor.id} cannot close over an open "
                        f"descendant (_done_transition_guard) so "
                        f"{ancestor_milestone} can never ship before the "
                        f"later milestone {descendant_milestone} does"
                    ),
                )
            )
    return tuple(violations)


# frob:ticket T-2579
def _ordered(a: Ticket, b: Ticket) -> bool:
    """`True` if `a`/`b` (both `Ticket`) are ordered against each other by
    a real `blocked_by` edge, in EITHER direction -- MILE004's own
    definition of "not ambiguous". A `blocked_by` edge naming an id that
    does not resolve in `queue` never reaches here (the id strings are
    compared directly, no lookup needed)."""
    return a.id in b.blocked_by or b.id in a.blocked_by


# frob:ticket T-2579
def _group_runs_last_by_milestone(
    root: Path, queue: TicketQueue
) -> dict[str, list[Ticket]]:
    """OPEN (non-terminal) `runs_last` tickets grouped by EFFECTIVE
    milestone (`frob.tickets._doable.effective_milestone`) -- MILE004's
    own candidate pool. A `runs_last` ticket with NO resolvable effective
    milestone is excluded (nothing to share a milestone WITH); that
    ticket's own lack of a milestone is MILE003's concern, not this
    one's."""
    from frob.tickets._doable import effective_milestone

    groups: dict[str, list[Ticket]] = {}
    for t in queue.tickets.values():
        if not t.runs_last or t.state in _TERMINAL_STATES:
            continue
        milestone, _source = effective_milestone(queue, t, root)
        if milestone is None:
            continue
        groups.setdefault(milestone, []).append(t)
    return groups


# frob:enforces CHK-GATE-MILE004
# frob:ticket T-2579
def _mile004_pair_violation(milestone: str, a: Ticket, b: Ticket) -> Violation | None:
    """One MILE004 `Violation` for the `(a, b)` pair if their order is
    AMBIGUOUS -- neither a real `blocked_by` edge between them (either
    direction, `_ordered`) nor an explicit `runs_last_parallel_safe=True`
    declaration on BOTH sides (T-2579's own body: a one-sided declaration
    is not a decision, both tickets must independently claim safety) --
    else `None`."""
    if _ordered(a, b):
        return None
    if a.runs_last_parallel_safe and b.runs_last_parallel_safe:
        return None
    return Violation(
        rule="MILE004",
        severity=Severity.ERROR,
        file="tickets.md",
        line=0,
        message=(
            f"MILE004: {a.id} and {b.id} are both runs_last in milestone "
            f"{milestone} with no ordering between them -- add a "
            f"blocked_by edge (either direction), or declare BOTH "
            f"runs_last_parallel_safe=True with a reason"
        ),
    )


# frob:ticket T-2579
# frob:doc docs/modules/tickets-data-storage.md#mile004-t-2579-m4b
# frob:tests tests/test_gates_milestone.py::TestMile004.test_two_unordered_runs_last_in_one_milestone_fires  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile004.test_blocked_by_edge_resolves_the_pair  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile004.test_declared_parallel_safe_resolves_the_pair  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile004.test_single_runs_last_ticket_never_fires  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile004.test_different_milestones_never_pair  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile004.test_terminal_sibling_excluded  # noqa: E501
def _mile004_unordered_runs_last(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """MILE004 (ERROR): flag every PAIR of `runs_last` tickets that share
    one EFFECTIVE milestone and whose relative order is AMBIGUOUS
    (`_mile004_pair_violation`).

    This is a genuinely REQUESTED design (T-2579's body: "do not
    relitigate"), not a rediscovery. The pre-existing T-1613 sibling
    carve-out in `frob.tickets._doable._other_open_tickets` (fellow
    runs-last tickets never count as "open" against each other) is
    UNTOUCHED by this gate -- that carve-out is what lets two runs-last
    tickets coexist as dispatchable candidates at all; MILE004 only
    detects when their coexistence needed an explicit decision that was
    never made, exactly the gap that carve-out leaves open (concrete
    instance: T-1614 auditing every `frob:waive` while a sibling
    runs-last ticket in the same milestone retargets waivers underneath
    it)."""
    groups = _group_runs_last_by_milestone(root, queue)
    violations: list[Violation] = []
    for milestone, tickets in groups.items():
        # frob:waive PERF004 reason="tickets is one milestone's own runs-last group, bounded by how many tickets share a milestone (small); resort is required for deterministic pairwise-comparison ordering below, not a hot-path re-sort"  # noqa: E501
        ordered_tickets = sorted(tickets, key=lambda t: t.id)
        for i, a in enumerate(ordered_tickets):
            for b in ordered_tickets[i + 1 :]:
                violation = _mile004_pair_violation(milestone, a, b)
                if violation is not None:
                    violations.append(violation)
    return tuple(violations)


# frob:ticket T-2576
# frob:ticket T-2579
# frob:ticket T-2580
# frob:doc docs/modules/tickets-data-storage.md#mile003-t-2576-m2
# frob:doc docs/modules/tickets-data-storage.md#mile001--mile002-t-2580-m5
# frob:tests tests/test_gates_milestone.py::TestMile003.test_fires_on_open_ticket_with_no_resolvable_milestone  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_silent_once_stamped  # noqa: E501
def milestone_gate(root: Path, queue: TicketQueue) -> tuple[Violation, ...]:
    """MILE001 + MILE002 + MILE003 + MILE004: the full T-2573 milestone
    gate family (M5 T-2580 added MILE001/MILE002, the two provable
    release-deadlock checks, alongside M2/M4b's MILE003/MILE004)."""
    return (
        _mile001_blocked_by_later_milestone(root, queue)
        + _mile002_descendant_later_milestone(root, queue)
        + _mile003_unresolved_milestone(root, queue)
        + _mile004_unordered_runs_last(root, queue)
    )


__all__ = ["milestone_gate"]
