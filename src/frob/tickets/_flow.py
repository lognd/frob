"""frob.tickets._flow -- the sprint/flow analytics family (T-2834), split out
of `frob.tickets._setters` following T-1103's per-family extraction pattern
(verbatim moves, directives intact, public surface re-exported via explicit
imports, zero caller-visible behavior change).

`sprint_view` (T-0715), `sprint_velocity` (T-0938), and `ticket_flow`
(T-1100) all mine the same git-history-derived done-transition data
(`_mine_done_transitions`) -- one cohesive "which tickets are committed to
X, and what happened to them" concern, distinct from `_setters.py`'s
single-field mutation concern (the setters mutate one ticket's field; this
module mines git history across the whole queue to report burn-down/
velocity). `_setters.py` imports the three public names back from here and
re-exports them, so `frob.tickets.__init__`'s existing `from frob.tickets.
_setters import (sprint_velocity, sprint_view, ticket_flow)` needs no
change at all (T-2834's own verified premise -- see that ticket's Done
report).
"""

# frob:ticket T-2834

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median

from frob.logging import get_logger
from frob.tickets._models import (
    SprintReport,
    SprintTransition,
    SprintVelocityReport,
    Ticket,
    TicketFlowReport,
    TicketFlowRow,
    TicketQueue,
    TicketState,
)
from frob.tickets._store import _store_mode, load_archive, v2_state_transitions

_log = get_logger(__name__)


# frob:ticket T-0938
def _tickets_committed_to(queue: TicketQueue, sprint: str) -> tuple[Ticket, ...]:
    """Every ticket in `queue` carrying `sprint` as its `Ticket.sprint`
    label, id-sorted -- the shared "who's committed to this sprint"
    lookup both `sprint_view` (T-0715, a current-state rollup) and
    `sprint_velocity` (T-0938, a history-mined rollup) start from,
    extracted to keep the two in lock-step rather than drifting two
    copies of the same filter/sort (DUP001)."""
    return tuple(
        sorted(
            (t for t in queue.tickets.values() if t.sprint == sprint),
            key=lambda t: t.id,
        )
    )


# frob:ticket T-0715
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_tiers.py::TestSprintShow.test_state_rollup_and_velocity
def sprint_view(queue: TicketQueue, sprint: str) -> SprintReport:
    """`frob ticket sprint show <label>`: every ticket committed to
    `sprint` (T-0715), a `TicketState -> count` rollup, and `closed`
    (done-count, the mandate's "closed-count velocity" -- derived from
    current ledger state, not a separate tracked counter). Always returns
    a report, even when no ticket carries this sprint label (`tickets`
    empty, every rollup count zero) -- there is no NotFound case, a sprint
    label is a free-form tag, not an id that must resolve."""
    tickets = _tickets_committed_to(queue, sprint)
    rollup: dict[TicketState, int] = {}
    for t in tickets:
        rollup[t.state] = rollup.get(t.state, 0) + 1
    closed = rollup.get(TicketState.DONE, 0)
    return SprintReport(sprint=sprint, tickets=tickets, rollup=rollup, closed=closed)


_STATE_LINE_RE = re.compile(r"(?m)^state:\s*(\S+)\s*$")


# frob:ticket T-0938
def _ticket_state_in_blob(text: str, ticket_id: str) -> str | None:
    """Read `ticket_id`'s `state:` value out of a full `tickets.md` blob
    (any revision's text, not necessarily the working tree's), by slicing
    the text between this ticket's `<!-- ticket:ID -->` anchor and the
    next one -- the same anchor `_store._LEDGER_MARKER_RE` splits sections
    on. Returns `None` if the anchor is absent from this revision (the
    ticket did not exist yet) or its block has no `state:` line (never
    happens in a well-formed ledger, but a malformed/mid-conflict blob
    must not raise)."""
    anchor = f"<!-- ticket:{ticket_id} -->"
    start = text.find(anchor)
    if start == -1:
        return None
    next_start = text.find("<!-- ticket:", start + len(anchor))
    block = text[start : next_start if next_start != -1 else len(text)]
    match = _STATE_LINE_RE.search(block)
    return match.group(1) if match else None


# frob:ticket T-0938
def _ledger_commit_history(root: Path) -> tuple[tuple[str, str], ...]:
    """Every commit that ever touched `tickets.md` in `root`'s clone,
    oldest-first, as `(sha, author-date-iso)` pairs (`git log --reverse
    --format=%H%x1f%aI -- tickets.md`) -- fetched ONCE per
    `sprint_velocity` call and re-used across every ticket in the sprint,
    since the ledger is one shared file and a per-ticket `git log` call
    would re-walk the same commit list once per ticket for no reason.
    Returns an empty tuple (never raises) if `root` is not a git
    checkout, `tickets.md` has no history yet, or the `git` call fails --
    a caller must treat that the same as "no history observed", matching
    `compute_changed_lines`'s existing best-effort git contract in this
    module."""
    from frob.gitio import run_argv

    spawned = run_argv(
        [
            "git",
            "-C",
            str(root),
            "log",
            "--reverse",
            "--format=%H%x1f%aI",
            "--",
            "tickets.md",
        ]
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return ()
    commits: list[tuple[str, str]] = []
    for line in spawned.danger_ok.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, _, iso = line.partition("\x1f")
        if sha and iso:
            commits.append((sha, iso))
    return tuple(commits)


# frob:ticket T-0938
def _blob_at(root: Path, sha: str) -> str | None:
    """`tickets.md`'s full text at commit `sha` (`git show
    <sha>:tickets.md`), or `None` if that revision can't be read (an
    unresolvable sha, a `git` failure) -- caller treats `None` the same
    as "this revision has no readable ticket state"."""
    from frob.gitio import run_argv

    spawned = run_argv(["git", "-C", str(root), "show", f"{sha}:tickets.md"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    return spawned.danger_ok.stdout


# frob:ticket T-1330
def _mine_done_transitions_v1(
    root: Path, ticket_ids: Sequence[str]
) -> tuple[SprintTransition, ...]:
    """v1 (monofile-ledger) done-transition mining -- `_mine_done_
    transitions`'s original body, split out unchanged when T-1330 added
    the v2 dispatch (`_mine_done_transitions_v2`): walk `_ledger_commit_
    history` oldest-first, reading each commit's `tickets.md` blob ONCE
    (`_blob_at`) and checking every tracked id's `state:` value against
    that one blob -- a `done` value that differs from the id's previous
    observed state is a transition.

    A `git log -G<anchor>` pickaxe restriction was tried first and
    rejected: the `<!-- ticket:ID -->` anchor line itself never changes
    across a state edit (only the `state:` line inside its block does),
    so `-G` on the anchor structurally misses every transition after the
    ticket's own creation commit -- a full walk is the only correct
    approach here, not an optimization left undone. This walk costs one
    `_blob_at` (subprocess `git show`) call per commit in `tickets.md`'s
    ENTIRE history, times every caller -- the ~6-minute `frob ticket
    flow`/`list --stats` cost T-1330 fixed for v2-mode repos by mining
    each ticket's own small file instead (`_mine_done_transitions_v2`)."""
    if not ticket_ids:
        return ()
    transitions: list[SprintTransition] = []
    prev_state: dict[str, str | None] = dict.fromkeys(ticket_ids)
    for sha, iso in _ledger_commit_history(root):
        blob = _blob_at(root, sha)
        if blob is None:
            continue
        for ticket_id in ticket_ids:
            state = _ticket_state_in_blob(blob, ticket_id)
            if state is None:
                continue
            try:
                if state == TicketState.DONE.value and state != prev_state[ticket_id]:
                    try:
                        committed_at = datetime.fromisoformat(iso)
                    except ValueError:
                        prev_state[ticket_id] = state
                        continue
                    transitions.append(
                        SprintTransition(
                            ticket_id=ticket_id,
                            sha=sha,
                            committed_at=committed_at,
                            from_state=prev_state[ticket_id],
                            to_state=state,
                        )
                    )
                prev_state[ticket_id] = state
            except KeyError:
                # `prev_state` is seeded from the exact same `ticket_ids`
                # this loop iterates (`dict.fromkeys` above), so this
                # should be unreachable in practice -- but a history-
                # mining pass over untrusted git blob content must not
                # crash on a surprise, only mis-derive one ticket's own
                # transition list (EXHAUST002, T-1371).
                continue
            except Exception:
                continue
    return tuple(transitions)


# frob:ticket T-1330
# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to v2_state_transitions, \
# a cross-module git-history walk the resolver cannot see through; the one real raise \
# path (datetime.fromisoformat on a malformed timestamp) is caught below"
def _mine_done_transitions_v2(
    root: Path, ticket_ids: Sequence[str]
) -> tuple[SprintTransition, ...]:
    """v2 (file-per-ticket) done-transition mining (T-1330): for each id,
    `v2_state_transitions` walks ONLY that ticket's own small `ticket.md`
    file's git history (`git log --follow -p`, one subprocess call per
    ticket) instead of re-reading the ENTIRE shared ledger's blob at
    every commit in its history (`_mine_done_transitions_v1`'s cost, the
    ~6-minute `frob ticket flow`/`list --stats` regression this ticket
    fixes for v2-mode repos) -- fast because each ticket's own file
    history is a small, disjoint slice of the repo's total commit count,
    not the whole thing walked once per caller. Same `SprintTransition`
    output shape as the v1 path, so every downstream reader
    (`sprint_velocity`, `ticket_flow`) is unaffected by which mode ran."""
    if not ticket_ids:
        return ()
    transitions: list[SprintTransition] = []
    for ticket_id in ticket_ids:
        prev_state: str | None = None
        for sha, iso, state in v2_state_transitions(root, ticket_id):
            if state == TicketState.DONE.value and state != prev_state:
                try:
                    committed_at = datetime.fromisoformat(iso)
                except ValueError:
                    prev_state = state
                    continue
                transitions.append(
                    SprintTransition(
                        ticket_id=ticket_id,
                        sha=sha,
                        committed_at=committed_at,
                        from_state=prev_state,
                        to_state=state,
                    )
                )
            prev_state = state
    return tuple(transitions)


# frob:ticket T-0938
# frob:ticket T-1330
def _mine_done_transitions(
    root: Path, ticket_ids: Sequence[str]
) -> tuple[SprintTransition, ...]:
    """Mine every `state: done` transition each id in `ticket_ids` has
    ever made (T-0938's derivation source -- see `sprint_velocity`'s
    docstring for the honest tradeoffs of this approach), dispatched on
    `_store_mode(root)` (T-1330): v2-mode repos mine each ticket's own
    small file (`_mine_done_transitions_v2`, fast -- see its docstring
    for the cost this avoids); v1-mode repos keep the original whole-
    ledger walk (`_mine_done_transitions_v1`) unchanged, since the fast
    path requires per-ticket files to exist at all."""
    if _store_mode(root) == "v2":
        return _mine_done_transitions_v2(root, ticket_ids)
    return _mine_done_transitions_v1(root, ticket_ids)


# frob:ticket T-0938
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_velocity.py::TestSprintVelocity.test_transitions_mined_from_history
def sprint_velocity(
    root: Path, queue: TicketQueue, sprint: str
) -> SprintVelocityReport:
    """`frob ticket sprint velocity <label>` (T-0938): history-derived
    burndown/velocity for every ticket currently committed to `sprint`.

    Derivation source, decided honestly per this ticket's acceptance
    criterion: `tickets.md` carries no transition-history field of its
    own (only each ticket's CURRENT `state`, same as `sprint_view`
    reads) and the "no new storage" mandate rules out adding one. The
    only place a past transition is actually recoverable is git's own
    commit history of `tickets.md` -- so this mines it directly, walking
    every commit that ever touched the ledger (oldest-first) and reading
    each tracked ticket's `state:` field out of that commit's blob, to
    find the specific commits where it flipped INTO `done`. This is
    genuinely history, not a state snapshot -- unlike `sprint_view.
    closed`, `sprint_velocity` sees a ticket that was done and later
    reopened (both transitions appear) and gives each closure a real
    commit + timestamp for a burndown chart's x-axis.

    Known, disclosed gaps (not silently papered over): (1) a ticket's
    CURRENT `sprint` label is used to select which tickets to mine --
    `tickets.md` does not retain sprint-REASSIGNMENT history, so a
    ticket closed under a different sprint label before being
    reassigned will not appear in either sprint's velocity; (2) if
    `tickets.md` was ever squash-merged or hand-edited such that a
    `done` transition never appears as its own commit, that transition
    is invisible to this mining (git history is a lower bound on
    real-world transitions, not a guarantee of completeness) -- both are
    accepted tradeoffs of "no new storage", not bugs.

    Always returns a report, even for a sprint label no ticket carries or
    a `root` with no git history -- same no-NotFound-case contract as
    `sprint_view`."""
    tickets = _tickets_committed_to(queue, sprint)
    transitions = list(_mine_done_transitions(root, tuple(t.id for t in tickets)))
    transitions.sort(key=lambda tr: tr.committed_at)
    closed = len(transitions)
    remaining = sum(1 for t in tickets if t.state != TicketState.DONE)
    return SprintVelocityReport(
        sprint=sprint,
        transitions=tuple(transitions),
        closed=closed,
        remaining=remaining,
        total=len(tickets),
    )


# frob:ticket T-1100
_FLOW_TRAILING_DAYS = 3


# frob:ticket T-1162
def _load_flow_ticket_universe(root: Path, queue: TicketQueue) -> dict:
    """T-1162: pure I/O -- merge `queue.tickets` with `tickets-archive.md`
    (best-effort; logs and degrades to `{}` on a load failure rather than
    blocking the whole report), the T-1142 fix so filed/landed counts
    include already-archived tickets. Extracted from `ticket_flow`."""
    archived = load_archive(root)
    archive_tickets = archived.danger_ok if archived.is_ok else {}
    if archived.is_err:
        _log.warning(
            "tickets: ticket_flow could not load tickets-archive.md (%s) -- "
            "landed/filed counts for already-archived tickets are omitted "
            "this run",
            archived.danger_err,
        )
    return {**archive_tickets, **queue.tickets}


# frob:ticket T-1162
def _count_filed_by_day(all_tickets: dict) -> dict[date, int]:
    """T-1162: pure formatting -- tally each ticket's `created` date into a
    filed-per-day histogram. Extracted from `ticket_flow`."""
    filed_by_day: dict[date, int] = {}
    for ticket in all_tickets.values():
        filed_by_day[ticket.created] = filed_by_day.get(ticket.created, 0) + 1
    return filed_by_day


# frob:ticket T-1528
# frob:ticket T-1162
def _count_landed_by_day(
    root: Path, all_tickets: dict
) -> tuple[dict[date, int], dict[str, date]]:
    """T-1162: pure I/O -- mine `tickets.md`'s git history
    (`_mine_done_transitions`) for done-transition commits across every
    ticket id in `all_tickets` and tally them into a landed-per-day
    histogram. Extracted from `ticket_flow`. T-1528: ALSO returns each
    id's FIRST observed done date from the same single mining pass, so
    `ticket_flow`'s median cycle-time needs no second history walk."""
    transitions = _mine_done_transitions(root, tuple(all_tickets.keys()))
    landed_by_day: dict[date, int] = {}
    first_done: dict[str, date] = {}
    for transition in transitions:
        day = transition.committed_at.date()
        landed_by_day[day] = landed_by_day.get(day, 0) + 1
        if (
            transition.ticket_id not in first_done
            or day < first_done[transition.ticket_id]
        ):
            first_done[transition.ticket_id] = day
    return landed_by_day, first_done


# frob:ticket T-1162
def _build_flow_rows(
    filed_by_day: dict[date, int], landed_by_day: dict[date, int], today: date
) -> list["TicketFlowRow"]:
    """T-1162: pure formatting -- zero-filled `TicketFlowRow` per calendar
    day from the earliest observed filing/landing event through `today`,
    so a quiet day still gets a row instead of being skipped. Extracted
    from `ticket_flow`."""
    observed_days = list(filed_by_day) + list(landed_by_day) + [today]
    earliest = min(observed_days)

    rows: list[TicketFlowRow] = []
    day = earliest
    while day <= today:
        rows.append(
            TicketFlowRow(
                day=day,
                filed=filed_by_day.get(day, 0),
                landed=landed_by_day.get(day, 0),
            )
        )
        day += timedelta(days=1)
    return rows


# frob:ticket T-1528
# frob:ticket T-1100
# frob:ticket T-1142
# frob:ticket T-1162
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_velocity.py::TestTicketFlow.test_filed_and_landed_counted_per_day
# frob:tests tests/test_tickets_velocity.py::TestTicketFlow.test_zero_activity_days_are_filled_not_sparse  # noqa: E501
# frob:tests \
# tests/test_tickets_velocity.py::TestTicketFlow.test_eta_none_when_queue_not_shrinking
# frob:tests \
# tests/test_tickets_velocity.py::TestTicketFlow.test_eta_computed_when_queue_shrinking
# frob:tests tests/test_tickets_velocity.py::TestTicketFlow.test_archived_ticket_still_counts_toward_landed  # noqa: E501
# frob:tests tests/test_tickets_velocity.py::TestTicketFlow.test_archived_ticket_still_counts_toward_filed  # noqa: E501
# frob:waive AFFECT001 reason="T-1162 is a pure internal extraction \
# (archive-merge/histogram/row-building helpers pulled out to cut the function under \
# the 60-line ARCH threshold); behavior, inputs, outputs, and the documented contract \
# are all unchanged, so docs/modules/ tickets.md's own content needs no edit"
def ticket_flow(
    root: Path, queue: TicketQueue, *, today: date | None = None
) -> TicketFlowReport:
    """`frob ticket flow` (T-1100): filed/day vs landed/day vs net, plus a
    naive burn-down ETA -- reuses `sprint_velocity`'s T-0938 git-history
    transition mining for the landed side (over the WHOLE queue, not one
    sprint) and each ticket's `created` field for the filed side; no new
    storage, same "no new storage" mandate T-0938 already established.

    T-1142: `queue` alone (whatever the caller passed -- the CLI's own
    `_flow` handler passes `load_active`'s active-only view) UNDERCOUNTS
    both sides for any ticket that has since been archived out of
    `tickets.md` into `tickets-archive.md` by `frob ticket archive`: its
    id is simply absent from `queue.tickets`, so `_mine_done_transitions`
    is never even ASKED to look for its done-transition commit (which
    still exists, readably, in `tickets.md`'s own git history from BEFORE
    the archive-sweep commit removed it -- `_mine_done_transitions`/
    `_ledger_commit_history` walk `tickets.md`'s FULL history, not just
    its current tip, so no separate `tickets-archive.md` mining is even
    needed for the landed side), and its `created` date is missing from
    the filed side the same way. This was T-1100's first real-world run
    (2026-07-28): landed=0 for two days the zero-drive record shows ~50
    lands each, both days followed by an archive sweep. Fixed by merging
    `tickets-archive.md`'s own tickets (`load_archive`, best-effort --
    degrades to `{}` on any load failure rather than blocking the whole
    report) into BOTH the filed-by-day source and the landed-mining id
    set, unconditionally, regardless of what view of the ACTIVE queue the
    caller happened to pass in. `open_count` still only ever counts
    `queue`'s own (active) tickets -- an archived ticket is always
    done/dropped, never a member of `_OPEN_STATES`, so merging the
    archive in cannot change that count either way.

    Builds one `TicketFlowRow` per calendar day from the EARLIEST observed
    filing/landing event through `today` (defaults to `date.today()`,
    injectable for deterministic tests), zero-filled -- a day with no
    activity still gets a row, so the trailing-window average always
    covers a real fixed-size span instead of skipping silently over quiet
    days. Returns an all-zero, single-`today`-row report (no crash, no
    `NotFound`) for an empty queue, same no-error-case contract
    `sprint_velocity` already keeps.

    T-1162 split the archive-merge I/O into `_load_flow_ticket_universe`,
    the filed/landed histograms into `_count_filed_by_day`/
    `_count_landed_by_day`, and the row-building into `_build_flow_rows` --
    this function is now their composition plus the trailing-window/
    open-count decisions and the final report build."""
    from frob.tickets import _OPEN_STATES

    all_tickets = _load_flow_ticket_universe(root, queue)
    filed_by_day = _count_filed_by_day(all_tickets)
    landed_by_day, first_done = _count_landed_by_day(root, all_tickets)

    today = today if today is not None else date.today()
    rows = _build_flow_rows(filed_by_day, landed_by_day, today)

    trailing = rows[-_FLOW_TRAILING_DAYS:] if rows else []
    trailing_net_rate = (
        sum(r.net for r in trailing) / len(trailing) if trailing else 0.0
    )
    open_count = sum(1 for t in queue.tickets.values() if t.state in _OPEN_STATES)
    median_cycle = _median_cycle_days(all_tickets, first_done)
    return TicketFlowReport(
        rows=tuple(rows),
        open_count=open_count,
        trailing_net_rate=trailing_net_rate,
        median_cycle_days=median_cycle,
    )


# frob:ticket T-1528
def _median_cycle_days(all_tickets: dict, first_done: dict[str, date]) -> float | None:
    """Median calendar days from `created` to first done transition across
    every ticket appearing in both inputs (T-1528's "time to-complete"
    stat); None when nothing has completed yet -- render layers must
    label that "n/a", never omit the stat silently."""
    cycles = [
        (first_done[tid] - ticket.created).days
        for tid, ticket in all_tickets.items()
        if tid in first_done and ticket.created is not None
    ]
    return float(median(cycles)) if cycles else None
