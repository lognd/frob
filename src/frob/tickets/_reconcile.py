"""`frob ticket reconcile` -- heal ticket<->worktree binding drift (T-0476).

Regular multi-agent operation drifts out of sync with reality in two ways
that neither the ledger nor the T-0473 lease side-channel self-heal:

1. **Stale hold**: `tickets.md` shows a ticket `IN_PROGRESS`, but the agent
   worktree that started it crashed, was force-removed, or never released
   its lease before exiting -- the ticket is dead-in-the-water, blocking
   `doable` for everyone (via T-0453's collision filter) with no live agent
   ever going to finish or close it.
2. **Orphan worktree**: a linked git worktree still exists on disk (a real,
   live checkout under `git worktree list`) but holds no lease at all --
   an agent whose ticket was closed/requeued/failed out from under it (or
   that never actually started one), left sitting there.

Both are judged STRUCTURALLY off state `frob.tickets._leases` (T-0473)
already tracks -- no coordinator polling of output-file mtimes, no
guessing: a stale hold is a local `IN_PROGRESS` ticket with no
corresponding lease; an orphan worktree is a `git worktree list` entry
with no lease naming it.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel
from typani.result import Err, Ok, Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._journal import _clear_intent, _read_all_intents
from frob.tickets._leases import (
    _land_in_progress_for_ticket,
    read_all_leases,
    refuse_if_land_in_progress,
    release_lease,
)
from frob.tickets._models import TicketError, TicketState
from frob.tickets._store import load_all
from frob.tickets._unlanded import _unlanded_branch_work

_log = get_logger(__name__)


# frob:doc docs/modules/tickets-lifecycle.md#frob-ticket-reconcile-t-0476
# frob:doc docs/modules/tickets-lifecycle.md#unlanded-branch-work-t-1934t-1948
class ReconcileReport(BaseModel):
    """The anomalies `reconcile` found (and, if `applied`, healed) --
    (T-0476) `requeued_tickets` (stale holds) and `orphan_worktrees` (live
    worktrees with no lease), plus whichever of the two mutation flags were
    actually acted on. `orphaned_land_intents` (T-0456) is the third
    anomaly class: a `frob ticket land` intent-journal record
    (`frob.tickets._journal`) still present, meaning the process that
    started that land never reached its own cleanup -- cleared (aborted,
    never resumed/rolled-forward) when `apply` is set, same as the other
    two classes' own report-then-heal shape."""

    model_config = {}

    requeued_tickets: tuple[str, ...]
    orphan_worktrees: tuple[str, ...]
    removed_worktrees: tuple[str, ...]
    orphaned_land_intents: tuple[str, ...] = ()
    cleared_land_intents: tuple[str, ...] = ()
    # frob:ticket T-1934
    # A FOURTH anomaly class (T-1934): a ticket that reads finished
    # (done-report or `state: done`/`dropped`) on some OTHER local branch
    # but is not terminal on `main`, including through the archive
    # (`frob.tickets._unlanded._unlanded_branch_work`). Formatted
    # "T-XXXX@branch" strings, one per finding. Deliberately NEVER healed
    # by `apply` -- landing a dead agent's branch unattended is exactly
    # the failure mode this anomaly class exists to surface, not fix; a
    # human or a freshly dispatched agent decides what to do with it.
    unlanded_branch_work: tuple[str, ...] = ()
    applied: bool
    removed_orphans: bool


def _live_worktrees(root: Path) -> tuple[Path, ...]:
    """Every linked `git worktree` path for `root`'s repository, EXCLUDING
    the main checkout itself (`git worktree list --porcelain`'s first
    entry) -- these are the candidates `reconcile` checks for an orphan
    (T-0476). Degrades to `()` if `root` is not a git work tree or the git
    call fails, matching every other best-effort git-derived read in this
    package."""
    spawned = run_argv(["git", "-C", str(root), "worktree", "list", "--porcelain"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("tickets: git worktree list failed under %s", root)
        return ()
    paths: list[Path] = []
    for line in spawned.danger_ok.stdout.splitlines():
        if line.startswith("worktree "):
            paths.append(Path(line[len("worktree ") :]).resolve())
    if not paths:
        return ()
    main = paths[0]
    return tuple(p for p in paths[1:] if p != main)


# T-2276@T-2291's own default worktree-cutting convention
# (`_default_work_worktree`/`frob.app.ticket_runner._lifecycle`): a
# worktree `frob ticket work`/`start` creates is branched
# `ticket_id.lower()`, never anything else. Matches a sequential id
# (t-1234) or a draft id (t-draft-xxxxxxxx), case-insensitively -- kept
# deliberately narrow to the ONE naming shape this repo's own tooling
# actually produces, not a broad "anything T-shaped" grep (T-2287's own
# lexical-match lesson: match a known GRAMMAR, not a loose pattern).
_DEFAULT_WORKTREE_BRANCH_RE = re.compile(
    r"^t-(?:(?P<seq>\d{4})|draft-(?P<draft>[0-9a-f]{8}))$"
)


def _live_worktree_ticket_ids(root: Path) -> frozenset[str]:
    """Ticket ids inferable from a LIVE `git worktree`'s own branch name
    (T-2292), via `_DEFAULT_WORKTREE_BRANCH_RE` -- best-effort defense-in-
    depth alongside the lease-based liveness check `_stale_in_progress_
    ticket_ids` already runs: a worktree that still exists on disk, whose
    branch is literally named after the ticket, is strong independent
    evidence the hold is not abandoned, regardless of whatever the lease
    file happens to read at the sampled instant (the T-2292 incident:
    `frob ticket reconcile --apply` requeued T-2276 while its worktree
    and agent were both still live, because the lease read absent/
    reclaimed at the exact instant reconcile sampled it -- see T-2292's
    own ticket body). A worktree cut with a custom `--worktree` path or a
    non-default branch name (a coordinator's own manual `git worktree
    add`, or a ticket resumed under a differently-named branch across
    sessions) is simply invisible to this check and falls back to the
    lease-only signal, unchanged from before this ticket -- this narrows
    false positives (never requeuing a live default-convention worktree),
    it does not widen them."""
    spawned = run_argv(["git", "-C", str(root), "worktree", "list", "--porcelain"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return frozenset()
    ids: set[str] = set()
    for line in spawned.danger_ok.stdout.splitlines():
        if not line.startswith("branch "):
            continue
        ref = line[len("branch ") :]
        name = ref.rsplit("/", 1)[-1]
        match = _DEFAULT_WORKTREE_BRANCH_RE.match(name)
        if match is None:
            continue
        if match.group("seq") is not None:
            ids.add(f"T-{match.group('seq')}")
        else:
            ids.add(f"T-draft-{match.group('draft')}")
    return frozenset(ids)


def _stale_in_progress_ticket_ids(
    root: Path,
    tickets: dict,
    leased_ticket_ids: frozenset[str],
    live_worktree_ticket_ids: frozenset[str],
) -> tuple[str, ...]:
    """Ticket ids the LOCAL ledger shows `IN_PROGRESS` with no corresponding
    LIVE lease (T-0476's stale-hold anomaly) -- `leased_ticket_ids` already
    excludes any lease `read_all_leases` judged stale (worktree path gone,
    T-0473's own liveness guard), so this only needs to check absence, not
    re-derive liveness itself.

    T-2292: a lease-absence read alone is NOT sufficient to call a hold
    stale -- the false-positive direction (requeuing genuinely live work)
    is far more expensive than the false-negative direction (missing a
    stale hold for one more reconcile cycle, see T-2292's own "WHY THIS IS
    THE DANGEROUS DIRECTION" reasoning), so TWO additional independent
    signals must also be absent before a ticket is called stale:
    `_land_in_progress_for_ticket` (a live `frob ticket land` process
    currently landing exactly this ticket -- the same T-1619 land-process
    scan `refuse_if_land_in_progress` already runs, reused here per-ticket
    rather than only once at `apply`'s own entry) and
    `live_worktree_ticket_ids` (`_live_worktree_ticket_ids`'s
    branch-name-convention signal, computed once by the caller and passed
    in rather than re-derived per ticket)."""
    return tuple(
        ticket_id
        for ticket_id, ticket in sorted(tickets.items())
        if ticket.state is TicketState.IN_PROGRESS
        and ticket_id not in leased_ticket_ids
        and ticket_id not in live_worktree_ticket_ids
        and not _land_in_progress_for_ticket(root, ticket_id)
    )


def _orphan_worktree_paths(
    root: Path, leased_worktrees: frozenset[str]
) -> tuple[Path, ...]:
    """Live linked worktrees (T-0476's orphan-worktree anomaly): a real
    `git worktree` entry that no lease names, i.e. holding no in-progress
    ticket at all."""
    return tuple(
        path for path in _live_worktrees(root) if str(path) not in leased_worktrees
    )


def _requeue_stale_holds(root: Path, stale_ids: tuple[str, ...]) -> tuple[str, ...]:
    """Transition each of `stale_ids` back to `QUEUED` (the same legal
    reverse-of-`start` transition `frob ticket requeue` uses, T-0472) and
    release any lingering lease file for it; returns the ids actually
    requeued (a transition failure for one id is logged and skipped, never
    aborting the rest)."""
    from frob.tickets import transition

    requeued: list[str] = []
    for ticket_id in stale_ids:
        result = transition(root, ticket_id, TicketState.QUEUED)
        if result.is_err:
            _log.warning(
                "tickets: reconcile could not requeue stale hold %s: %s",
                ticket_id,
                result.danger_err,
            )
            continue
        release_lease(root, ticket_id)
        _log.info(
            "tickets: reconcile requeued stale hold %s (in-progress -> queued, "
            "no live lease found)",
            ticket_id,
        )
        requeued.append(ticket_id)
    return tuple(requeued)


# frob:ticket T-0601
def _clear_orphaned_intents(root: Path, ticket_ids: tuple[str, ...]) -> tuple[str, ...]:
    """Clear each of `ticket_ids`' land-intent journal record (T-0456);
    returns the ids actually cleared (`_clear_intent` is itself always
    best-effort/never-raises, so this is really just a pass-through, kept
    as its own helper for symmetry with `_requeue_stale_holds`/
    `_remove_orphan_worktrees`)."""
    for ticket_id in ticket_ids:
        _clear_intent(root, ticket_id)
        _log.info(
            "tickets: reconcile cleared orphaned land intent for %s "
            "(process that started it never reached its own cleanup)",
            ticket_id,
        )
    return ticket_ids


def _remove_orphan_worktrees(root: Path, orphans: tuple[Path, ...]) -> tuple[str, ...]:
    """`git worktree remove --force <path>` for each of `orphans`; returns
    the paths actually removed (a removal failure -- e.g. uncommitted
    changes git itself refuses to discard even with `--force`'s
    stronger-than-default semantics for a NON-`--force` case, or a locked
    worktree -- is logged and skipped, never aborting the rest, and NEVER
    removes `root` itself since `orphans` is already `_orphan_worktree_
    paths`'s output, which excludes the main checkout by construction)."""
    removed: list[str] = []
    for path in orphans:
        result = run_argv(
            ["git", "-C", str(root), "worktree", "remove", "--force", str(path)]
        )
        if result.is_err or result.danger_ok.returncode != 0:
            _log.warning("tickets: reconcile could not remove orphan worktree %s", path)
            continue
        _log.info(
            "tickets: reconcile removed orphan worktree %s (no lease held it)", path
        )
        removed.append(str(path))
    return tuple(removed)


# frob:ticket T-2291
def _refuse_apply_if_land_in_progress(
    root: Path, *, apply: bool, wait_timeout_s: float | None
) -> Result[None, TicketError]:
    """`reconcile`'s own pre-write guard (T-2291), split out to keep
    `reconcile` under ARCH001's line threshold: when `apply` is set,
    checks `refuse_if_land_in_progress` BEFORE any transition/lease/
    worktree write runs, so a refusal leaves the tree untouched instead
    of the pre-T-2291 shape (write first, refuse only later at the
    caller's ledger-commit step, stranding the write uncommitted -- the
    real 9246d4b5a incident). `Ok(None)` when `apply` is unset (a dry-run
    never writes, so there is nothing to guard) or when no land is in
    progress."""
    if not apply:
        return Ok(None)
    land_check = refuse_if_land_in_progress(root, wait_timeout_s=wait_timeout_s)
    if land_check.is_err:
        _log.warning(
            "tickets: reconcile --apply refused (land in progress under "
            "%s) -- no ledger/lease/worktree write attempted",
            root,
        )
        return Err(TicketError.ReconcileLandInProgress)
    return Ok(None)


# frob:doc docs/modules/tickets-lifecycle.md#frob-ticket-reconcile-t-0476
# frob:tests tests/test_ticket_reconcile.py::TestReconcileStaleHold.test_apply_requeues_stale_hold_and_releases_lease kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree.test_apply_and_remove_orphans_actually_removes_it kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_reports_the_confirmed_leak_shape kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_reconcile.py::TestReconcileApplyLandInProgressGuard.test_apply_refuses_and_writes_nothing_while_land_lock_held kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_reconcile.py::TestReconcileApplyLandInProgressGuard.test_apply_still_requeues_when_no_land_in_progress kind="unit"  # noqa: E501
# frob:ticket T-0601
# frob:ticket T-1934
# frob:ticket T-2291
# frob:doc docs/modules/tickets-lifecycle.md#unlanded-branch-work-t-1934t-1948
def reconcile(
    root: Path,
    *,
    apply: bool = False,
    remove_orphans: bool = False,
    wait_timeout_s: float | None = None,
) -> Result[ReconcileReport, TicketError]:
    """Detect (and, if `apply`, heal) T-0476's two anomaly classes under
    `root`: stale `IN_PROGRESS` holds with no live lease (requeued to
    `QUEUED`, releasing the lease) and orphan live worktrees with no lease
    at all (always reported; only actually `git worktree remove`d when
    BOTH `apply` and `remove_orphans` are set -- removing a worktree is a
    strictly more destructive action than requeuing a ticket, so it is
    gated behind its own explicit opt-in rather than riding along on
    `apply` alone).

    `apply=False` (the default) is a pure dry-run: every anomaly is still
    detected and returned, nothing is mutated -- the same "report first,
    mutate only when asked" posture `frob.clean.scan`/`clean` use.

    `wait_timeout_s` forwards to `refuse_if_land_in_progress`'s own bounded
    wait (T-2291, `None` = its normal configured default) -- exposed here
    only so a test can force an immediate refusal (`wait_timeout_s=0`)
    without burning real wall-clock time on a lock that is held for the
    whole test.

    T-2291: when `apply` is set, this checks `refuse_if_land_in_progress`
    FIRST, before any transition/lease/worktree write runs (see
    `_refuse_apply_if_land_in_progress`) -- previously the equivalent
    guard only fired later, at the caller's ledger-commit step
    (`commit_full_ledger_change` -> `_add_and_commit_tickets_md`), by
    which point `_requeue_stale_holds` had already mutated ticket.md
    files on disk. A refusal now leaves the tree exactly as it found it:
    `Err(TicketError.ReconcileLandInProgress)`, no write attempted."""
    guard = _refuse_apply_if_land_in_progress(
        root, apply=apply, wait_timeout_s=wait_timeout_s
    )
    if guard.is_err:
        return Err(guard.danger_err)

    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    tickets = loaded.danger_ok

    leases = read_all_leases(root)
    leased_ticket_ids = frozenset(lease.ticket_id for lease in leases)
    leased_worktrees = frozenset(
        str(Path(lease.worktree).resolve()) for lease in leases
    )

    live_worktree_ticket_ids = _live_worktree_ticket_ids(root)
    stale_ids = _stale_in_progress_ticket_ids(
        root, tickets, leased_ticket_ids, live_worktree_ticket_ids
    )
    orphans = _orphan_worktree_paths(root, leased_worktrees)
    orphaned_intents = tuple(intent.ticket_id for intent in _read_all_intents(root))
    # frob:ticket T-1934
    # Report-only, unconditionally -- no `apply`-gated healing exists for
    # this anomaly class (see `ReconcileReport.unlanded_branch_work`'s own
    # docstring for why).
    unlanded = tuple(
        f"{finding.ticket_id}@{finding.branch}"
        for finding in _unlanded_branch_work(root)
    )

    requeued = _requeue_stale_holds(root, stale_ids) if apply else stale_ids
    removed = (
        _remove_orphan_worktrees(root, orphans) if apply and remove_orphans else ()
    )
    cleared_intents = _clear_orphaned_intents(root, orphaned_intents) if apply else ()

    return Ok(
        ReconcileReport(
            requeued_tickets=requeued,
            orphan_worktrees=tuple(str(p) for p in orphans),
            removed_worktrees=removed,
            orphaned_land_intents=orphaned_intents,
            cleared_land_intents=cleared_intents,
            unlanded_branch_work=unlanded,
            applied=apply,
            removed_orphans=apply and remove_orphans,
        )
    )
