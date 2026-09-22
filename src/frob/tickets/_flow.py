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
from frob.tickets._store import _store_mode, load_archive, tickets_dir

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
    # frob:ticket T-5132
    total_points = sum(t.points or 0 for t in tickets)
    points_done = sum(t.points or 0 for t in tickets if t.state == TicketState.DONE)
    sized_count = sum(1 for t in tickets if t.points is not None)
    remaining_points = total_points - points_done
    points_eta_days = None
    if remaining_points > 0 and points_done > 0 and tickets:
        earliest_created = min(t.created for t in tickets)
        span_days = max((date.today() - earliest_created).days, 1)
        velocity = points_done / span_days
        if velocity > 0:
            points_eta_days = remaining_points / velocity
    return SprintReport(
        sprint=sprint,
        tickets=tickets,
        rollup=rollup,
        closed=closed,
        total_points=total_points,
        points_done=points_done,
        sized_count=sized_count,
        points_eta_days=points_eta_days,
    )


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
# frob:waive ARCH001 reason="T-5132: crossed the threshold by adding a single \
# target_state parameter and a docstring paragraph explaining it to an already-large \
# pre-existing v1 walk (T-1330's own docstring already explains why this function is a \
# full, unsplit ledger-history walk); the actual control flow is unchanged from before \
# this diff, so a structural split here would separate one cohesive walk into two \
# halves that must stay in lock-step, not a genuine decomposition"
def _mine_done_transitions_v1(
    root: Path,
    ticket_ids: Sequence[str],
    target_state: str = TicketState.DONE.value,
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
    each ticket's own small file instead (`_mine_done_transitions_v2`).

    `target_state` (T-5132) generalizes this from a done-only miner to
    ANY single-state transition finder -- `_ticket_flow_hours` reuses it
    with `TicketState.IN_PROGRESS.value` to find each ticket's start
    transition alongside its done one, same walk, no second mining pass."""
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
                if state == target_state and state != prev_state[ticket_id]:
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


# frob:ticket T-5131
_V2_STATE_ADD_RE = re.compile(r"^\+state:\s*(\S+)\s*$")
# frob:ticket T-5131
_V2_DIFF_FILE_RE = re.compile(r"^diff --git a/\S+ b/(?P<new>\S+)$")
# frob:ticket T-5131
_V2_COMMIT_HEADER_RE = re.compile(r"^--frob-v2-commit-- ([0-9a-f]+)\x1f(\S+)$")
# frob:ticket T-5131
_V2_TICKET_PATH_RE = re.compile(r"(?:^|/)T-(?:draft-[0-9a-fA-F]+|[0-9]+)/ticket\.md$")


# frob:ticket T-5131
def _v2_tree_rel(root: Path) -> str:
    """`tickets/`'s path relative to `root`, POSIX-slashed -- the single
    pathspec every batched v2 git walk below scopes itself to, so a v2
    mining pass costs one spawn over the whole ticket tree instead of one
    spawn per ticket id (T-5131's fix, see `_mine_done_transitions_v2`'s
    docstring for the N+1 cost this replaces)."""
    return tickets_dir(root).relative_to(root).as_posix()


# frob:ticket T-5131
def _v2_path_transitions_raw_log(root: Path) -> str:
    """The raw `git log --reverse -p -- tickets/` output `_v2_all_path_
    transitions` parses (T-5131) -- split out so the spawn itself (empty
    string on any git failure, matching this module's best-effort git
    contract) and the pure line-by-line parse below each stay under
    ARCH001's long-AND-complex threshold on their own."""
    from frob.gitio import run_argv

    spawned = run_argv(
        [
            "git",
            "-C",
            str(root),
            "log",
            "--reverse",
            "-p",
            "--format=--frob-v2-commit-- %H%x1f%aI",
            "--",
            _v2_tree_rel(root),
        ]
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return ""
    return spawned.danger_ok.stdout


# frob:ticket T-5131
# tests/test_tickets_velocity.py::TestSprintVelocityV2Mode.test_v2_mode_mines_via_v2_state_transitions  # noqa: E501
def _v2_all_path_transitions(root: Path) -> dict[str, list[tuple[str, str, str]]]:
    """ONE `git log --reverse -p -- tickets/` walk over the WHOLE v2
    ticket tree, parsed into `{path: [(sha, iso, state), ...]}` (T-5131).
    Replaces the per-ticket `git log --follow -p` spawn
    `_store.v2_state_transitions` used to run once per ticket id (~1400
    full-history walks over 11436 commits, measured 10+ minutes on this
    repo) with a single walk whose per-commit diff output already
    partitions by path via `diff --git a/... b/...` headers -- the same
    'last added +state: line this commit leaves the file holding' rule
    `_store._mine_v2_path_transitions` used, now tracked per
    currently-open path across one shared walk instead of per ticket.
    Returns an empty dict (never raises) if `root` has no git history or
    the tree has never existed, matching this module's existing
    best-effort git contract."""
    raw_log = _v2_path_transitions_raw_log(root)
    by_path: dict[str, list[tuple[str, str, str]]] = {}
    current_commit: tuple[str, str] | None = None
    current_path: str | None = None
    pending_state: str | None = None

    def flush() -> None:
        if (
            current_commit is not None
            and current_path is not None
            and pending_state is not None
            and _V2_TICKET_PATH_RE.search(current_path) is not None
        ):
            by_path.setdefault(current_path, []).append(
                (current_commit[0], current_commit[1], pending_state)
            )

    for line in raw_log.splitlines():
        commit_match = _V2_COMMIT_HEADER_RE.match(line)
        if commit_match is not None:
            flush()
            current_commit = (commit_match.group(1), commit_match.group(2))
            current_path = None
            pending_state = None
            continue
        diff_match = _V2_DIFF_FILE_RE.match(line)
        if diff_match is not None:
            flush()
            current_path = diff_match.group("new")
            pending_state = None
            continue
        state_match = _V2_STATE_ADD_RE.match(line)
        if state_match is not None:
            pending_state = state_match.group(1)
    flush()
    return by_path


# frob:ticket T-5131
def _v2_all_renames(root: Path) -> dict[str, str]:
    """ONE `git log --diff-filter=R -M100% --name-status -- tickets/`
    walk over the WHOLE v2 ticket tree, mapping each `ticket.md` path to
    its exact-content-similarity rename predecessor (T-5131's tree-wide
    replacement for `_store._v2_rename_source`'s one-spawn-per-ticket
    variant) -- `-M100%` keeps the same T-1543 exact-rename-only
    semantics (a merely template-similar sibling ticket can never satisfy
    it). An ambiguous target (more than one detected source in the whole
    tree's history) is dropped, same 'never guess' contract as the
    per-ticket original."""
    from frob.gitio import run_argv

    spawned = run_argv(
        [
            "git",
            "-C",
            str(root),
            "log",
            "--diff-filter=R",
            "-M100%",
            "--name-status",
            "--format=--frob-v2-rename-commit--",
            "--",
            _v2_tree_rel(root),
        ]
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return {}
    sources: dict[str, set[str]] = {}
    for line in spawned.danger_ok.stdout.splitlines():
        if not line.startswith("R"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        _status, old_path, new_path = parts
        sources.setdefault(new_path, set()).add(old_path)
    return {new: next(iter(olds)) for new, olds in sources.items() if len(olds) == 1}


# frob:ticket T-5131
def _v2_lineage_from(rename_map: dict[str, str], rel_path: str) -> list[str]:
    """Reconstruct `rel_path`'s full rename lineage, oldest-first, by
    walking `rename_map` backward (T-5131's in-memory replacement for
    `_store._v2_path_lineage`'s per-ticket `git log` recursion) -- same
    bounded-depth-64 loop-guard against a pathological rename cycle."""
    lineage = [rel_path]
    seen = {rel_path}
    current = rel_path
    for _ in range(64):
        prev = rename_map.get(current)
        if prev is None or prev in seen:
            break
        lineage.insert(0, prev)
        seen.add(prev)
        current = prev
    return lineage


# frob:ticket T-1330
# frob:ticket T-5131
# tests/test_tickets_velocity.py::TestSprintVelocityV2Mode.test_v2_mining_spawns_git_a_constant_number_of_times  # noqa: E501
# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to the batched v2 \
# git-history walks (T-5131), which the resolver cannot see through; the one real \
# raise path (datetime.fromisoformat on a malformed timestamp) is caught below"
def _mine_done_transitions_v2(
    root: Path,
    ticket_ids: Sequence[str],
    target_state: str = TicketState.DONE.value,
) -> tuple[SprintTransition, ...]:
    """v2 (file-per-ticket) done-transition mining (T-1330): TWO batched
    git spawns total (`_v2_all_path_transitions`, `_v2_all_renames`) over
    the whole `tickets/` tree, regardless of how many ids are requested,
    replacing the one-`git log --follow -p`-subprocess-per-ticket cost
    T-5131 measured at 10+ minutes on this repo's 11436-commit history
    (~1400 full-history walks) -- see those two helpers' docstrings for
    the batching. Same `SprintTransition` output shape and same 'last
    added +state: line per commit, first observed transition into done
    per ticket' semantics as the original per-ticket walk, so every
    downstream reader (`sprint_velocity`, `ticket_flow`) is unaffected by
    which mode ran or how it was mined."""
    if not ticket_ids:
        return ()
    by_path = _v2_all_path_transitions(root)
    rename_map = _v2_all_renames(root)
    tree_rel = _v2_tree_rel(root)
    transitions: list[SprintTransition] = []
    for ticket_id in ticket_ids:
        rel_path = f"{tree_rel}/{ticket_id}/ticket.md"
        lineage = _v2_lineage_from(rename_map, rel_path)
        seen_shas: set[str] = set()
        prev_state: str | None = None
        for path in lineage:
            for sha, iso, state in by_path.get(path, ()):
                if sha in seen_shas:
                    continue
                seen_shas.add(sha)
                if state == target_state and state != prev_state:
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
    root: Path,
    ticket_ids: Sequence[str],
    target_state: str = TicketState.DONE.value,
) -> tuple[SprintTransition, ...]:
    """Mine every `state: <target_state>` transition each id in
    `ticket_ids` has ever made (T-0938's derivation source -- see
    `sprint_velocity`'s docstring for the honest tradeoffs of this
    approach), dispatched on `_store_mode(root)` (T-1330): v2-mode repos
    mine each ticket's own small file (`_mine_done_transitions_v2`, fast
    -- see its docstring for the cost this avoids); v1-mode repos keep
    the original whole-ledger walk (`_mine_done_transitions_v1`)
    unchanged, since the fast path requires per-ticket files to exist at
    all. `target_state` defaults to `done` (the name's original meaning)
    but T-5132's `_ticket_flow_hours` also calls this with `in-progress`
    to find each ticket's start transition, reusing the same mining."""
    if _store_mode(root) == "v2":
        return _mine_done_transitions_v2(root, ticket_ids, target_state)
    return _mine_done_transitions_v1(root, ticket_ids, target_state)


# frob:ticket T-0938
# frob:doc docs/modules/tickets.md#public-api
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


# frob:ticket T-5132
# frob:doc docs/modules/tickets-data-storage.md#points-t-5132
def _ticket_points_per_hour(
    root: Path, all_tickets: dict, first_done: dict[str, date]
) -> tuple[float | None, int]:
    """T-5132: `points-per-actual-hour` calibration -- reuses `_mine_
    done_transitions`'s generalized `target_state` (T-5132) to mine BOTH
    each closed, sized ticket's first `in-progress` transition and its
    first `done` transition from the same git-history source `sprint_
    velocity`/`ticket_flow` already trust, then sums `points` over sum
    of actual (done - start) hours across every ticket where both
    transitions were minable and the resulting duration is positive.
    Returns `(None, 0)` when no ticket qualifies -- render layers must
    label that "n/a", never a fabricated ratio."""
    candidate_ids = tuple(
        tid
        for tid, t in all_tickets.items()
        if tid in first_done and t.points is not None
    )
    if not candidate_ids:
        return None, 0
    starts = _mine_done_transitions(root, candidate_ids, TicketState.IN_PROGRESS.value)
    dones = _mine_done_transitions(root, candidate_ids, TicketState.DONE.value)
    first_start: dict[str, datetime] = {}
    for tr in starts:
        if (
            tr.ticket_id not in first_start
            or tr.committed_at < first_start[tr.ticket_id]
        ):
            first_start[tr.ticket_id] = tr.committed_at
    first_done_dt: dict[str, datetime] = {}
    for tr in dones:
        if (
            tr.ticket_id not in first_done_dt
            or tr.committed_at < first_done_dt[tr.ticket_id]
        ):
            first_done_dt[tr.ticket_id] = tr.committed_at
    total_points = 0
    total_hours = 0.0
    sample = 0
    for tid in candidate_ids:
        if tid not in first_start or tid not in first_done_dt:
            continue
        hours = (first_done_dt[tid] - first_start[tid]).total_seconds() / 3600.0
        if hours <= 0:
            continue
        total_points += all_tickets[tid].points  # type: ignore[operator]
        total_hours += hours
        sample += 1
    if sample == 0 or total_hours <= 0:
        return None, 0
    return total_points / total_hours, sample


# frob:ticket T-5132
# frob:doc docs/modules/tickets-data-storage.md#points-t-5132
def _ticket_tokens_per_point(all_tickets: dict) -> float | None:
    """T-5132 amendment: `tokens-per-point` calibration -- sums `tokens_
    in + tokens_out` over sum of `points` across every ticket carrying
    BOTH (no history mining needed, both are plain ledger fields).
    `None` when no ticket carries both."""
    total_tokens = 0
    total_points = 0
    for ticket in all_tickets.values():
        if ticket.points is None:
            continue
        if ticket.tokens_in is None and ticket.tokens_out is None:
            continue
        total_tokens += (ticket.tokens_in or 0) + (ticket.tokens_out or 0)
        total_points += ticket.points
    if total_points <= 0 or total_tokens <= 0:
        return None
    return total_tokens / total_points


# frob:ticket T-1528
# frob:ticket T-1100
# frob:ticket T-1142
# frob:ticket T-1162
# frob:doc docs/modules/tickets.md#public-api
# tests/test_tickets_velocity.py::TestTicketFlow.test_filed_and_landed_counted_per_day
# tests/test_tickets_velocity.py::TestTicketFlow.test_eta_none_when_queue_not_shrinking
# tests/test_tickets_velocity.py::TestTicketFlow.test_eta_computed_when_queue_shrinking
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
    # frob:ticket T-5132
    points_per_hour, points_per_hour_sample = _ticket_points_per_hour(
        root, all_tickets, first_done
    )
    tokens_per_point = _ticket_tokens_per_point(all_tickets)
    return TicketFlowReport(
        rows=tuple(rows),
        open_count=open_count,
        trailing_net_rate=trailing_net_rate,
        median_cycle_days=median_cycle,
        points_per_hour=points_per_hour,
        points_per_hour_sample=points_per_hour_sample,
        tokens_per_point=tokens_per_point,
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
