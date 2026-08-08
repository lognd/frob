"""frob.tickets._doable -- the dispatchable-queue family (T-1108, T-1103
residue): `doable`/`doable_blocked` and everything they lean on (scope-lease
collision detection, over-broad-scope breadth measurement, the display-
state/live-lease overlay, and the undispatched-staleness alarm), split out
of `frob.tickets.__init__` following T-1103's per-family extraction pattern
(smallest cohesive unit first, public surface re-exported via `__all__`,
zero caller edits, `frob:tests`/`frob:doc` edges moved verbatim with the
functions they annotate).

Kept together because every function here ultimately answers "is this
ticket dispatchable right now, and if not, why" -- one shared question, not
several concerns bolted together. `_doable_sort_key` (the priority/age
ordering `doable`/`doable_blocked` both sort by) and `_open_blockers`'s
sibling `_OPEN_STATES` constant intentionally STAY in `frob.tickets.__init__`
(the former is also `board_view`'s sort key, the latter is a module-wide
constant several non-doable functions still reference) -- this module
late-imports both from the package at call time rather than at load time,
the same load-order-safe indirection T-1103 used for `renumber_one`/
`finalize_draft`, since `__init__` imports THIS module before either name
exists yet at its own module scope.
"""


from __future__ import annotations

import fnmatch
import tomllib
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from frob.logging import get_logger
from frob.tickets._leases import read_all_leases
from frob.tickets._models import (
    LEDGER_PATH,
    OVER_BROAD_LITERAL_GLOBS,
    Priority,
    Ticket,
    TicketQueue,
    TicketState,
    TicketTier,
    scope_overlap_globs,
)

_log = get_logger(__name__)


# frob:ticket T-1613
def _other_open_tickets(queue: TicketQueue, ticket: Ticket) -> tuple[str, ...]:
    """Ids of every ticket in `queue` OTHER than `ticket` itself, and OTHER
    than any fellow runs-last ticket, whose state is non-terminal (T-1613,
    same `_OPEN_STATES` set `_open_blockers`/`_start_blockers` already use).

    This is the "any other ticket open" test a runs-last marker gates on --
    fellow runs-last tickets are excluded from the count so two or more
    runs-last tickets can coexist and order among THEMSELVES via ordinary
    `blocked_by` edges instead of deadlocking each other (a runs-last
    ticket counting another runs-last ticket as "open" would mean neither
    could ever start while the other existed, unrelated to `blocked_by`
    entirely)."""
    from frob.tickets import _OPEN_STATES

    return tuple(
        sorted(
            t.id
            for t in queue.tickets.values()
            if t.id != ticket.id
            and not t.runs_last
            and t.state in _OPEN_STATES
        )
    )


# frob:invariant INV-032
# frob:tests tests/test_tickets.py::TestDoable.test_blocked_excluded
# frob:ticket T-0715
# frob:ticket T-1613
# invariant spec: [INV-032](invariants/INV-032.md)
def _doable_candidates(queue: TicketQueue) -> list[Ticket]:
    """Queued/planned LEAF tickets (tier=TICKET) that currently have no open
    blockers, unordered. T-0715: an EPIC/STORY never surfaces here even if
    it has no `blocked_by` of its own -- only a leaf ticket is ever
    dispatchable work; an epic/story is pure organization, not a unit an
    agent starts directly.

    T-1613: a `runs_last` ticket additionally never surfaces here while
    `_other_open_tickets` is non-empty -- it stays structurally undoable,
    not merely warned-about, until every OTHER non-runs-last ticket in the
    ledger has reached a terminal state (done/dropped)."""
    return [
        t
        for t in queue.tickets.values()
        if t.state in (TicketState.QUEUED, TicketState.PLANNED)
        and t.tier is TicketTier.TICKET
        and not _open_blockers(queue, t)
        and (not t.runs_last or not _other_open_tickets(queue, t))
    ]


# frob:ticket T-0453
# T-0524: frob:doc removed -- this feeds `leased_by` (public), which
# already carries the same docs/modules/tickets.md#public-api anchor
# (COV007: a private helper does not need its own copy).
def _in_progress_leases(queue: TicketQueue) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """`(ticket_id, scope)` for every IN_PROGRESS ticket, id-ordered -- the
    active scope-leases `doable`'s default collision filter and
    `leased_by`'s explanation both check candidates against (T-0453
    scope-lease model)."""
    return tuple(
        (t.id, t.scope)
        for t in sorted(queue.tickets.values(), key=lambda t: t.id)
        if t.state is TicketState.IN_PROGRESS
    )


# frob:ticket T-0473
def _cross_worktree_leases(
    queue: TicketQueue, root: Path
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """`(ticket_id, scope)` for every lease `frob.tickets._leases` reports
    from ANY worktree of `root`'s repository (T-0473) -- the fix for the
    T-0453 lease model being inert across worktrees, since a ticket started
    in an isolated worktree never reaches THIS worktree's own
    `tickets.md`. A lease whose ticket id the LOCAL ledger already shows as
    `DONE`/`DROPPED` is dropped as stale (a crashed worktree's unreleased
    lease for an already-finished ticket must not block `doable` forever;
    full liveness reconciliation across worktrees is T-0476's job, this is
    only a cheap local-ledger staleness guard, not a substitute for it)."""
    leases = read_all_leases(root)
    kept: list[tuple[str, tuple[str, ...]]] = []
    for lease in leases:
        local = queue.tickets.get(lease.ticket_id)
        if local is not None and local.state in (TicketState.DONE, TicketState.DROPPED):
            continue
        kept.append((lease.ticket_id, lease.scope))
    return tuple(kept)


# frob:ticket T-0473
def _all_leases(
    queue: TicketQueue, root: Path | None
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """`_in_progress_leases(queue)` (the local ledger's own view) UNIONED
    with `_cross_worktree_leases` (every OTHER worktree's recorded lease),
    deduplicated by ticket id with the LOCAL ledger's entry always winning
    (it is authoritative for any ticket this worktree's own `tickets.md`
    already knows about) (T-0473). `root=None` (no repo to consult the
    shared lease directory from -- e.g. a caller with no filesystem root)
    keeps the exact pre-T-0473 local-only behavior."""
    local = _in_progress_leases(queue)
    if root is None:
        return local
    merged: dict[str, tuple[str, ...]] = dict(local)
    for ticket_id, scope in _cross_worktree_leases(queue, root):
        merged.setdefault(ticket_id, scope)
    return tuple(sorted(merged.items()))


# frob:ticket T-0453
# T-0524: frob:doc removed -- feeds `_repo_files`/`scope_breadth_context`
# (public), which already carries the same
# docs/modules/tickets.md#public-api anchor (COV007).
def _is_excluded_breadth_path(path: str) -> bool:
    """Whether `path` should never count toward the T-0453 breadth measure
    regardless of tracking status -- `.git`/`.venv`/`__pycache__`/... (any
    `frob.excludes.is_skipped_dir` name) and `.claude/worktrees/` (the
    per-agent worktree tree, ~129 of them observed in this repo, whose
    file count would otherwise massively over-count breadth and -- before
    this fix -- made `_repo_files`'s old full-tree `rglob` walk take
    minutes per call)."""
    from frob.excludes import is_skipped_dir

    parts = path.split("/")
    if any(is_skipped_dir(part) for part in parts[:-1]):
        return True
    return path.startswith(".claude/worktrees/")


# frob:ticket T-0453
# T-0524: frob:doc removed -- feeds `_repo_files`/`scope_breadth_context`
# (public), which already carries the same
# docs/modules/tickets.md#public-api anchor (COV007).
def _repo_files_git(root: Path) -> tuple[str, ...] | None:
    """`git ls-files` under `root` -- tracked files only, `root`-relative
    posix paths, breadth-excluded paths dropped -- or `None` if `root` is
    not a git work tree / `git` is unavailable (T-0453 perf fix: this
    replaces a full-tree `rglob` walk, which used to include the ~129
    stale worktrees under `.claude/worktrees/` and made `frob ticket
    doable` take minutes).

    T-0803: routed through `frob.gitio.run_argv` (gains `guarded_subprocess_
    run`'s `FROB_DISABLE_EXEC` kill switch transitively, T-0778) instead of
    a bare `subprocess.run` -- this was the one remaining git spawn in the
    package bypassing the guard."""
    from frob.gitio import run_argv

    spawned = run_argv(["git", "-C", str(root), "ls-files"], timeout_s=10)
    if spawned.is_err:
        _log.warning("tickets: git ls-files failed under %s", root)
        return None
    result = spawned.danger_ok
    if result.returncode != 0:
        return None
    return tuple(
        sorted(
            line
            for line in result.stdout.splitlines()
            if line and not _is_excluded_breadth_path(line)
        )
    )


# frob:ticket T-0453
# T-0524: frob:doc removed -- feeds `_repo_files`/`scope_breadth_context`
# (public), which already carries the same
# docs/modules/tickets.md#public-api anchor (COV007).
def _repo_files_walk_fallback(root: Path) -> tuple[str, ...]:
    """Every real file under `root` as `root`-relative posix paths, with
    built-in skip dirs (`.git`, `.venv`, `__pycache__`, ...) and
    `.claude/worktrees/` pruned -- the `_repo_files` fallback for a `root`
    that is not a git work tree (T-0453). Never the default path in a real
    git checkout; `_repo_files_git` is."""
    from frob.excludes import walk_pruned

    files: list[str] = []
    for path in sorted(walk_pruned(root)):
        rel = path.relative_to(root).as_posix()
        if _is_excluded_breadth_path(rel):
            continue
        files.append(rel)
    return tuple(files)


# frob:ticket T-0453
# T-0524: frob:doc removed -- feeds `scope_breadth_context` (public),
# which already carries the same docs/modules/tickets.md#public-api
# anchor (COV007).
def _repo_files(root: Path) -> tuple[str, ...]:
    """The T-0453 breadth-check file universe under `root`: `git ls-files`
    (tracked files, fast) when `root` is a git work tree, else a pruned
    tree walk (`_repo_files_walk_fallback`). Callers should invoke this
    (via `scope_breadth_context`) ONCE per `doable` call, never once per
    candidate x holder pair -- see `scope_breadth_context`."""
    tracked = _repo_files_git(root)
    if tracked is not None:
        return tracked
    return _repo_files_walk_fallback(root)


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_lease.py::TestBreadthPerf.test_computed_once_per_doable_call
def scope_breadth_context(root: Path) -> tuple[int, tuple[str, ...]]:
    """`(large_glob_max_files threshold, repo_files)` computed ONCE -- the
    shared input `_over_broad_scope_entries`/`large_glob_warnings` reuse
    instead of each re-running `git ls-files`/re-walking the tree per
    candidate x holder pair (T-0453 perf fix: this repo's real `frob
    ticket doable` used to take minutes -- a full-tree `rglob`, including
    ~129 stale `.claude/worktrees/` checkouts, called once per candidate
    per in-progress holder). `doable`/`doable_blocked` compute this a
    single time per call and thread it through `leased_by`. Both helpers
    are late-imported from the package rather than called via this
    module's own top-level binding: `tests/test_tickets_lease.py::
    TestBreadthPerf` monkeypatches `frob.tickets._repo_files` (the
    package-level attribute) to count calls, and a module-local `import`
    binding at load time would not see that patch -- the same
    monkeypatch-indirection hazard T-1103 hit for `renumber_one`."""
    from frob.tickets import _load_large_glob_max_files, _repo_files

    return (_load_large_glob_max_files(root), _repo_files(root))


# frob:ticket T-0453
# T-0524: frob:doc removed -- feeds `_over_broad_scope_entries`, whose own
# caller `leased_by` (public) already carries the same
# docs/modules/tickets.md#public-api anchor (COV007).
def _entry_to_glob(entry: str) -> str:
    """Expand a bare directory-prefix scope entry (`"docs/"`, no wildcard
    metacharacters) into its recursive glob (`"docs/**"`) -- the SAME
    expansion `frob.tickets._models._scope_globs` applies, duplicated here
    (rather than imported) only because this needs the single-entry form
    to build a per-entry warning/breadth message; `_scope_globs` itself
    remains the one place actual scope MATCHING expands from (T-0453)."""
    if entry.endswith("/") and not any(ch in entry for ch in "*?["):
        return entry + "**"
    return entry


# frob:ticket T-0453
# T-0524: frob:doc removed -- called from `leased_by` (public), which
# already carries the same docs/modules/tickets.md#public-api anchor
# (COV007).
def _over_broad_scope_entries(
    scope: Sequence[str], threshold: int, files: Sequence[str]
) -> tuple[str, ...]:
    """Declared scope entries of `scope` that are over-broad (T-0453): a
    named chronically-broad glob (`OVER_BROAD_LITERAL_GLOBS`) unconditionally,
    or one matching more of `files` than `threshold`. `LEDGER_PATH` is never
    flagged (every ticket implicitly leases it).

    Takes a PRECOMPUTED `(threshold, files)` pair (`scope_breadth_context`)
    rather than a `root` to walk -- this is the hot inner loop callers run
    once per candidate x holder pair, and re-deriving `files` (a `git
    ls-files`/tree-walk) on every call is exactly the T-0453 perf bug
    (`frob ticket doable` taking minutes on this repo's real worktree
    count) this signature avoids.

    THE single breadth criterion both `large_glob_warnings` (nudge the
    ticket author to narrow it) and `leased_by` (an over-broad in-progress
    lease demotes to warn-only rather than hard-blocking the ENTIRE queue,
    T-0453 real-repo verification) consult -- one signal driving two
    behaviors, not a `tests/**`/`docs/` directory special-case (the fix the
    T-0453 DESIGN CORRECTION explicitly forbids): any glob this broad by
    this SAME measure is treated the same way, regardless of which
    directory it names.
    """
    broad: list[str] = []
    for entry in scope:
        if entry == LEDGER_PATH:
            continue
        if entry in OVER_BROAD_LITERAL_GLOBS:
            broad.append(entry)
            continue
        # fnmatch.filter translates the glob ONCE and matches all files in
        # one pass (T-0453 perf fix: was 624k fnmatch.fnmatch calls
        # re-deriving the same glob per file on the real repo).
        if len(fnmatch.filter(files, _entry_to_glob(entry))) > threshold:
            broad.append(entry)
    return tuple(broad)


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_lease.py::TestLargeGlobWarnings.test_fires_on_broad_tests_glob
# frob:tests \
# tests/test_tickets_lease.py::TestLargeGlobWarnings.test_silent_on_precise_test_file
def large_glob_warnings(
    ticket: Ticket,
    root: Path,
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> tuple[str, ...]:
    """Human-readable nudges for any of `ticket`'s declared scope entries
    `_over_broad_scope_entries` flags (T-0453 DESIGN CORRECTION). Empty for
    a precisely-scoped ticket (e.g. `tests/test_gates.py`).

    Pass a precomputed `breadth` (`scope_breadth_context(root)`) when
    calling this in a loop over several tickets so the breadth walk runs
    once, not once per ticket (`root` is still required to label warnings
    consistently and for the `breadth is None` single-call convenience
    path, which computes it internally).

    This is a NUDGE, not a hard gate: it exists to fix over-hiding at the
    scope-DECLARATION level (narrow the glob to the files actually
    touched) instead of ignoring `tests/**`/`docs/` in the lease-overlap
    check itself, which the T-0453 design correction says would mask real
    per-file collisions under those trees.
    """
    threshold, files = breadth if breadth is not None else scope_breadth_context(root)
    warnings: list[str] = []
    for entry in _over_broad_scope_entries(ticket.scope, threshold, files):
        if entry in OVER_BROAD_LITERAL_GLOBS:
            warnings.append(
                f"{ticket.id} scope {entry!r} is a chronically over-broad "
                "glob -- narrow it to the specific files this ticket "
                "touches"
            )
            continue
        matched = len(fnmatch.filter(files, _entry_to_glob(entry)))
        warnings.append(
            f"{ticket.id} scope {entry!r} matches {matched} files "
            f"(> {threshold}) -- narrow it to the specific files this "
            "ticket touches"
        )
    return tuple(warnings)


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_lease.py::TestLeasedBy.test_precise_in_progress_does_not_hide_disjoint  # noqa: E501
# frob:tests \
# tests/test_tickets_lease.py::TestLeasedBy.test_real_source_scope_collision_is_hidden
# frob:tests \
# tests/test_tickets_lease.py::TestLeasedBy.test_over_broad_lease_demotes_to_warn_only
def leased_by(
    queue: TicketQueue,
    ticket: Ticket,
    root: Path | None = None,
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
    all_leases: tuple[tuple[str, tuple[str, ...]], ...] | None = None,
) -> tuple[tuple[str, str], ...]:
    """`(holding_ticket_id, glob_that_leases_it)` for every IN_PROGRESS
    ticket whose scope-lease overlaps `ticket`'s own scope (T-0453) --
    empty means `ticket` is free to dispatch right now. Powers both
    `doable`'s default exclusion and `--show-blocked`'s per-ticket
    explanation ("T-0xxx held: scope src/frob/gates/** leased by
    in-progress T-0yyy").

    When `root` is given, a holder's OVER-BROAD scope entries
    (`_over_broad_scope_entries`) are dropped before the overlap check --
    an over-broad DECLARED lease demotes to warn-only (`large_glob_warnings`
    still nudges narrowing it) rather than hard-blocking the entire doable
    queue, so one repo-wide `src/frob/**` in-progress ticket cannot zero
    out `doable` for everyone. Precise scope entries on the SAME holder
    still enforce normally -- this is breadth-driven demotion, not a
    directory-specific carve-out, and does not weaken the sound overlap
    test itself (`root=None` keeps the strict, undemoted check, e.g. for
    callers with no repo root to walk).

    Pass a precomputed `breadth` (`scope_breadth_context(root)`) when
    calling this per-candidate in a loop (`doable`/`doable_blocked` do) so
    the breadth walk runs ONCE for the whole call, not once per candidate
    x holder pair (T-0453 perf fix -- this is what made `frob ticket
    doable` take minutes on this repo's real worktree count before the
    fix). Omitting it while `root` is given computes it internally, for
    standalone/test callers.

    Likewise, pass a precomputed `all_leases` (`_all_leases(queue, root)`)
    when calling this per-candidate in a loop (`doable`/`doable_blocked`
    do) so the local-ledger-union-with-cross-worktree-leases computation
    runs ONCE for the whole call, not once per candidate (T-0773 perf fix
    -- `frob.tickets._leases.read_all_leases` is itself memoized per
    process now, so this second layer of threading is belt-and-suspenders
    rather than the only fix, but it matches the existing `breadth`
    pattern and avoids even the memoized read's dict-lookup/tuple-copy
    overhead per candidate). Omitting it computes it internally, same
    default-to-internal convention as `breadth`.
    """
    if root is not None and breadth is None:
        breadth = scope_breadth_context(root)
    if all_leases is None:
        all_leases = _all_leases(queue, root)
    hits: list[tuple[str, str]] = []
    for holder_id, holder_scope in all_leases:
        if holder_id == ticket.id:
            continue
        effective_scope = holder_scope
        if breadth is not None:
            threshold, files = breadth
            broad = frozenset(_over_broad_scope_entries(holder_scope, threshold, files))
            effective_scope = tuple(s for s in holder_scope if s not in broad)
            if not effective_scope:
                continue
        collision = scope_overlap_globs(ticket.scope, effective_scope)
        if collision is not None:
            hits.append((holder_id, collision[1]))
    return tuple(hits)


# frob:ticket T-0716
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_lease_overlay.py::TestDisplayState.test_queued_with_live_lease_decorated  # noqa: E501
# frob:tests tests/test_tickets_lease_overlay.py::TestDisplayState.test_queued_with_stale_lease_undecorated  # noqa: E501
# frob:tests tests/test_tickets_lease_overlay.py::TestDisplayState.test_ledger_in_progress_undecorated  # noqa: E501
# frob:tests \
# tests/test_tickets_lease_overlay.py::TestDisplayState.test_no_root_never_decorates
def display_state(ticket: Ticket, root: Path | None) -> str:
    """`ticket`'s display state for `frob ticket list`/`show` (T-0716): the
    ledger `state.value`, OVERLAID (never written back to the ledger --
    writing a worktree's view into main's ledger is exactly the
    corruption class T-0633/T-0682 fixed) with `@<worktree-basename>` when
    the ledger still shows `ticket` QUEUED/PLANNED but a live cross-worktree
    lease for it exists (`read_all_leases`, which already drops leases
    whose worktree path no longer exists -- T-0473/T-0476 stale-lease
    handling reused here verbatim, not re-implemented).

    A ledger-recorded `IN_PROGRESS` ticket is returned undecorated (plain
    `"in-progress"`) -- that state is already visible without a lease, and
    the `@worktree` marker exists specifically to surface the OTHER case:
    a ticket a worktree has started that main's own ledger hasn't learned
    about yet. `root=None` (no repo to consult the shared lease directory
    from) always returns the plain ledger state, matching `leased_by`'s
    own `root=None` degrade-quietly convention.

    Late-imports `read_all_leases` from the package rather than calling
    this module's own top-level binding: several tests (`tests/
    test_tickets_lease_overlay.py::TestDisplayState`, `tests/
    test_tickets_dispatch_stale.py::TestHasLiveLease`) monkeypatch
    `frob.tickets.read_all_leases` (the package-level attribute) to a
    fake, and a module-local `import` binding at load time would not see
    that patch -- the same monkeypatch-indirection hazard T-1103 hit for
    `renumber_one`."""
    from frob.tickets import read_all_leases

    if root is not None and ticket.state in (TicketState.QUEUED, TicketState.PLANNED):
        for lease in read_all_leases(root):
            if lease.ticket_id == ticket.id:
                worktree_name = Path(lease.worktree).name
                return f"in-progress@{worktree_name}"
    return ticket.state.value


# frob:ticket T-0752
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_dispatch_stale.py::TestHasLiveLease.test_queued_with_live_lease_is_in_flight  # noqa: E501
# frob:tests tests/test_tickets_dispatch_stale.py::TestHasLiveLease.test_queued_with_no_lease_is_not_in_flight  # noqa: E501
# frob:tests \
# tests/test_tickets_dispatch_stale.py::TestHasLiveLease.test_no_root_never_in_flight
def has_live_lease(ticket: Ticket, root: Path | None) -> bool:
    """Whether `ticket` itself (not a scope collision with some OTHER
    ticket -- that is `leased_by`'s job) currently has a live lease against
    it, per the same `display_state`/`read_all_leases` overlay `frob ticket
    list` already uses (T-0716) -- reused verbatim here rather than
    re-reading the lease directory a second way. Powers `doable`'s
    in-flight/dispatchable row split (T-0752): a row this returns `True`
    for is being worked by SOME worktree already, even though the local
    ledger may still show it `queued`/`planned`, so it belongs in the
    IN-FLIGHT section, not the "next thing to dispatch" one."""
    return display_state(ticket, root) != ticket.state.value


#: Default per-priority staleness threshold (hours) past which a
#: dispatchable (unleased, unblocked) CRITICAL/HIGH ticket is considered
#: dangerously undispatched (T-0752, user mandate: T-0731 sat
#: filed-but-undispatched for hours). Only CRITICAL/HIGH carry a default --
#: MEDIUM/LOW are not alarmed on by default (a queue always has some).
_DISPATCH_STALE_DEFAULT_HOURS: dict[Priority, float] = {
    Priority.CRITICAL: 4.0,
    Priority.HIGH: 24.0,
}


# frob:ticket T-0752
def _dispatch_stale_thresholds(root: Path) -> dict[Priority, float]:
    """Per-priority undispatched-staleness thresholds, in hours (T-0752),
    from `frob.toml`'s `[tickets]` table (`dispatch_stale_critical_hours`/
    `dispatch_stale_high_hours`), defaulting to
    `_DISPATCH_STALE_DEFAULT_HOURS`. Same fail-open-to-defaults shape as
    `_tick004_rot_thresholds`/`_load_large_glob_max_files` -- a missing or
    malformed `frob.toml` degrades to the defaults rather than erroring."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return dict(_DISPATCH_STALE_DEFAULT_HOURS)
    try:
        with toml_path.open("rb") as handle:
            table = tomllib.load(handle).get("tickets", {})
        return {
            priority: float(
                table.get(f"dispatch_stale_{priority.value}_hours", default)
            )
            for priority, default in _DISPATCH_STALE_DEFAULT_HOURS.items()
        }
    except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError) as exc:
        _log.warning(
            "tickets: dispatch-stale thresholds unreadable/malformed in %s (%s), "
            "using defaults",
            toml_path,
            exc,
        )
        return dict(_DISPATCH_STALE_DEFAULT_HOURS)


# frob:ticket T-0752
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours.test_same_day_is_zero_hours  # noqa: E501
# frob:tests tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours.test_one_day_old_is_24_hours  # noqa: E501
def dispatch_stale_hours(ticket: Ticket, *, today: date | None = None) -> float:
    """Hours `ticket` has been sitting since filing (T-0752's "last state
    change or filing" measurement) -- `Ticket.created` is the only
    timestamp this model carries (no per-transition history exists yet, so
    "last state change" degrades to "filing" here; a finer-grained
    transition timestamp is a follow-on, not built by this pass), converted
    from whole days to hours (`(today - ticket.created).days * 24`). `today`
    is injectable for deterministic tests; omitted, it defaults to
    `date.today()`."""
    if today is None:
        today = date.today()
    return (today - ticket.created).days * 24.0


# frob:ticket T-0752
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_dispatch_stale.py::TestUndispatchedStale.test_critical_past_threshold_alarms  # noqa: E501
# frob:tests tests/test_tickets_dispatch_stale.py::TestUndispatchedStale.test_critical_under_threshold_no_alarm  # noqa: E501
# frob:tests tests/test_tickets_dispatch_stale.py::TestUndispatchedStale.test_medium_priority_never_alarms  # noqa: E501
def undispatched_stale(
    tickets: Sequence[Ticket],
    root: Path,
    *,
    today: date | None = None,
) -> tuple[tuple[Ticket, float, float], ...]:
    """`(ticket, hours_elapsed, threshold_hours)` for every CRITICAL/HIGH
    ticket in `tickets` whose `dispatch_stale_hours` has crossed its
    `_dispatch_stale_thresholds` entry (T-0752) -- the single staleness-
    alarm computation both `frob ticket doable`'s row rendering and a
    future TICK-family `frob check` gate (T-0714/T-0752 coordination, gate
    wiring itself is out of this ticket's declared scope --
    `src/frob/gates/**` -- and tracked separately) are meant to call, so
    the "past threshold" judgment lives in exactly one place. `tickets`
    should already be the DISPATCHABLE set (unblocked, unleased) -- this
    function does not itself re-derive that; pass `doable(...)`'s result
    filtered to non-in-flight rows (`has_live_lease`)."""
    thresholds = _dispatch_stale_thresholds(root)
    alarms: list[tuple[Ticket, float, float]] = []
    for t in tickets:
        threshold = thresholds.get(t.priority)
        if threshold is None:
            continue
        elapsed = dispatch_stale_hours(t, today=today)
        if elapsed > threshold:
            alarms.append((t, elapsed, threshold))
    return tuple(alarms)


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_lease.py::TestDoable.test_ignore_lease_returns_raw_list
# frob:tests \
# tests/test_tickets_tiers.py::TestDoableLeafOnly.test_epic_and_story_never_surface
# frob:invariant INV-024
# frob:ticket T-0715
# invariant spec: [INV-024](invariants/INV-024.md)
def doable(
    queue: TicketQueue,
    root: Path | None = None,
    *,
    ignore_lease: bool = False,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> tuple[Ticket, ...]:
    """Tickets in {queued, planned} with no open blockers, ordered by
    priority (highest first, T-0411) then oldest-first within a priority tier.

    By DEFAULT also excludes any candidate whose declared scope overlaps
    an in-progress ticket's active scope-lease (T-0453 scope-lease model,
    `leased_by`) -- two agents dispatched straight off this list can never
    collide on the same files, with no hand-maintained blocklist. Pass
    `root` (the repo root) so an over-broad holder lease demotes to
    warn-only instead of blocking everything (`leased_by`'s `root`
    parameter); omit it only when no repo root is available to walk (the
    check then stays strict/undemoted). Pass `ignore_lease=True`
    (`frob ticket doable --ignore-lease`) for the raw, blocker-only list
    with no collision filtering at all.

    T-0773: `_all_leases(queue, root)` is computed ONCE here and threaded
    through every `leased_by` call in the filter loop below (same pattern
    as `breadth`), instead of each candidate re-deriving the union of
    local-ledger and cross-worktree leases for itself.

    T-0752: pass a precomputed `breadth` (`scope_breadth_context(root)`,
    the same kwarg `doable_blocked` already accepts) when the caller has
    already walked the tree for it -- omitting it while `root` is given
    computes it internally, same default-to-internal convention as
    `doable_blocked`. This is what keeps `frob ticket doable`'s default
    render (which also needs `breadth` for its own warnings) down to a
    single `git ls-files` walk instead of two.
    """
    from frob.tickets import _doable_sort_key

    candidates = _doable_candidates(queue)
    if not ignore_lease:
        if root is not None and breadth is None:
            breadth = scope_breadth_context(root)
        all_leases = _all_leases(queue, root)
        candidates = [
            t
            for t in candidates
            if not leased_by(queue, t, root, breadth=breadth, all_leases=all_leases)
        ]
    return tuple(sorted(candidates, key=_doable_sort_key))


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_lease.py::TestShowBlocked.test_show_blocked_lists_reasons
def doable_blocked(
    queue: TicketQueue,
    root: Path | None = None,
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> tuple[tuple[Ticket, tuple[tuple[str, str], ...]], ...]:
    """Doable-candidates hidden by an in-progress scope-lease, paired with
    WHY (`(holding_ticket_id, overlapping_glob)` per collision) -- the data
    `frob ticket doable --show-blocked` renders (T-0453). See `leased_by`
    for what passing `root` does (over-broad-lease demotion) and what
    passing a precomputed `breadth` (`scope_breadth_context(root)`) avoids
    (re-walking the tree when the caller already has one). T-0773:
    `_all_leases(queue, root)` is likewise computed ONCE here and threaded
    through every `leased_by` call below, rather than each candidate
    re-deriving it."""
    from frob.tickets import _doable_sort_key

    candidates = _doable_candidates(queue)
    if root is not None and breadth is None:
        breadth = scope_breadth_context(root)
    all_leases = _all_leases(queue, root)
    blocked: list[tuple[Ticket, tuple[tuple[str, str], ...]]] = []
    for t in sorted(candidates, key=_doable_sort_key):
        hits = leased_by(queue, t, root, breadth=breadth, all_leases=all_leases)
        if hits:
            blocked.append((t, hits))
    return tuple(blocked)


# frob:ticket T-1744
def _ticket_directive_marker(ticket_id: str) -> str:
    """The exact `frob:ticket <id>` directive text a landed change for
    `ticket_id` stamps onto the symbols it touches -- the literal needle
    `already_landed_markers` greps scoped files for (T-1744 case 1)."""
    return f"frob:ticket {ticket_id}"


# frob:ticket T-1744
def _narrow_scope_files(
    ticket: Ticket, threshold: int, files: tuple[str, ...]
) -> tuple[str, ...]:
    """Files under `ticket`'s declared scope, EXCLUDING any glob entry
    `_over_broad_scope_entries` flags (T-1744): `already_landed_markers`
    is a positive-signal content scan, and scanning every file a
    `src/**`-shaped over-broad glob matches for one ticket's marker would
    be noise, not signal -- the same T-0453 design-correction discipline
    `leased_by`'s over-broad demotion already applies, reused here rather
    than duplicated."""
    kept: list[str] = []
    for entry in ticket.scope:
        if entry == LEDGER_PATH:
            continue
        if _over_broad_scope_entries([entry], threshold, files):
            continue
        kept.extend(fnmatch.filter(files, _entry_to_glob(entry)))
    return tuple(kept)


# frob:ticket T-1744
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_dispatch_stale.py::TestAlreadyLandedMarkers.test_own_directive_present_flags_the_ticket  # noqa: E501
# frob:tests tests/test_tickets_dispatch_stale.py::TestAlreadyLandedMarkers.test_absent_directive_is_silent  # noqa: E501
# frob:tests tests/test_tickets_dispatch_stale.py::TestAlreadyLandedMarkers.test_over_broad_scope_entry_is_not_scanned  # noqa: E501
# frob:waive WIRE001 reason="T-1744's own declared scope is \
# src/frob/tickets/_doable.py and docs/modules/tickets.md only -- CLI/alarm wiring \
# belongs in frob.app.ticket_runner, outside this scope" follow_up="T-1822"
def already_landed_markers(
    queue: TicketQueue,
    root: Path,
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> tuple[Ticket, ...]:
    """Doable candidates (queued/planned, unblocked) whose OWN
    `frob:ticket <id>` directive already appears, verbatim, in a file
    their declared scope names (T-1744 case 1: a fix that landed OUTSIDE
    the ticket workflow -- a direct commit that never ran through `frob
    ticket land` -- leaves the ledger stuck at queued/planned forever
    with nothing distinguishing it from genuinely undone work; two
    confirmed instances, T-1487 and T-1587, each cost an agent real
    budget re-verifying a fix that had already shipped).

    POSITIVE signal only, the same discipline T-1675 established for the
    LAND-time twin of this check (`_check_already_landed`'s `state: done`
    read): this never infers from an empty diff, a stale-looking ticket,
    or ledger prose -- it reads the FILES the code actually lives in
    (`_narrow_scope_files`, itself skipping any over-broad scope entry to
    stay a precise scan rather than a repo sweep) and only flags a hit
    when that ticket's own directive text is found there. Never trusts
    `state: done` in the ledger either way -- `_doable_candidates` already
    restricts the input to queued/planned tickets, so a ticket the
    ledger already marks done never reaches this check at all; a ticket
    this flags is one the ledger STILL calls open despite the code
    already being present, which is exactly the incoherence T-1487/
    T-1587 exhibited.

    This is a DIFFERENT check from T-1675's `_check_already_landed`: that
    one runs at LAND time, against the ticket BEING landed, using a
    `state: done` positive signal already recorded elsewhere in the
    ledger. This one runs at DISPATCH time (`frob ticket doable`), before
    any agent has been assigned, against every OPEN candidate, using the
    directive marker itself as the positive signal -- there is no
    `state: done` to consult yet, because nothing about the direct commit
    ever touched this ticket's own ledger entry."""
    threshold, files = breadth if breadth is not None else scope_breadth_context(root)
    hits: list[Ticket] = []
    for ticket in _doable_candidates(queue):
        needle = _ticket_directive_marker(ticket.id)
        for rel in _narrow_scope_files(ticket, threshold, files):
            path = root / rel
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if needle in text:
                hits.append(ticket)
                break
    return tuple(sorted(hits, key=lambda t: t.id))


def _open_blockers(queue: TicketQueue, ticket: Ticket) -> tuple[str, ...]:
    """Blocker ids of ticket whose current state is not done/dropped (or unknown)."""
    from frob.tickets import _OPEN_STATES

    open_ids: list[str] = []
    for blocker_id in ticket.blocked_by:
        blocker = queue.tickets.get(blocker_id)
        if blocker is None or blocker.state in _OPEN_STATES:
            open_ids.append(blocker_id)
    return tuple(open_ids)
