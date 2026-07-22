"""`frob ticket land` -- one-command landing (docs/modules/tickets.md#frob-ticket-land).

The landing procedure used to be manual coordinator surgery repeated per
ticket: wip-commit in the worktree, merge main into it, a deletion-filter
check (a stale worktree base can silently drop files main already has),
squash-apply onto main, a ledger splice on conflict, close (evidence +
Done-report validation), and a conventional commit. `land()` does the
whole chain atomically, with a `--dry-run` mode that runs every check and
every git operation the real run would, then unwinds it, so a dry run can
never green-light a landing that would actually fail (T-0176).

Every abort path logs the exact manual remedy alongside its `Err` -- the
`--dry-run` output IS the incident report a human would otherwise have to
reconstruct by hand.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/tickets/_land.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import fnmatch
import importlib
import os
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

from typani.result import Err, Ok, Result

from frob.gitio import current_branch, run_argv
from frob.logging import get_logger
from frob.tickets._journal import clear_intent, write_intent
from frob.tickets._models import (
    CMD_EVIDENCE_ALLOWED_KINDS,
    LandError,
    LandReport,
    Ticket,
    TicketError,
    TicketState,
    has_substantive_done_report,
    is_cmd_evidence,
    matches_collected,
    scope_matches,
)
from frob.tickets._provisional import is_draft_id
from frob.tickets._store import _parse_ledger, _render_ledger, archive_path, ledger_path

# T-0577: same posix-only degradation as `frob.tickets._store`'s
# `ledger_lock` -- `_land_lock` degrades to a documented no-op (see its
# docstring) on a platform without `fcntl`, rather than failing import.
fcntl: ModuleType | None
try:
    fcntl = importlib.import_module("fcntl")
except ImportError:  # pragma: no cover -- posix-only in this repo's CI
    fcntl = None

_log = get_logger(__name__)

# T-0577: dedicated lock file for serializing `land()` calls against the
# SAME `root`, deliberately a DIFFERENT name from `_store.lock_path`'s
# `.frob/tickets.lock`. Reusing that exact path was tried first and broke:
# a worktree's own `.frob/tickets.lock` (created the moment ANY ticket
# operation runs in the worktree, then committed into the branch by
# `land`'s own `git add -A` wip-commit/finalize-commit steps) collides,
# by identical relative path, with the untracked lock file `root`'s own
# lock would have created -- git's squash-merge refuses outright ("would
# be overwritten by merge") rather than silently picking a side. A
# distinct filename `root` never shares with anything a worktree branch
# legitimately commits sidesteps that collision entirely.
_LAND_LOCK_REL = Path(".frob") / "land.lock"


def _land_lock_path(root: Path) -> Path:
    """The advisory lock file path `_land_lock` holds, serializing every
    `land()` call against `root` (T-0577)."""
    return root / _LAND_LOCK_REL


@contextmanager
def _land_lock(root: Path) -> Iterator[None]:
    """Exclusive, blocking, cross-process lock serializing every `land()`
    call against `root` (T-0577) -- see `land`'s docstring for why this
    closes the REL001 version-bump-collision incident class. Degrades to a
    documented no-op (logged at WARNING) on a platform without `fcntl`,
    matching `frob.tickets._store.ledger_lock`'s same documented
    degradation."""
    if fcntl is None:  # pragma: no cover -- posix-only in this repo's CI
        _log.warning(
            "land: _land_lock: fcntl unavailable on this platform, lock is "
            "a NO-OP -- concurrent `land()` calls against %s are NOT "
            "serialized here",
            root,
        )
        yield
        return
    path = _land_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    _log.debug("land: _land_lock acquired (%s)", path)
    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        _log.debug("land: _land_lock released (%s)", path)


# frob:doc docs/modules/tickets.md#frob-ticket-land
_STATE_RANK: dict[TicketState, int] = {
    TicketState.QUEUED: 0,
    TicketState.PLANNED: 1,
    TicketState.IN_PROGRESS: 2,
    TicketState.BLOCKED: 2,
    TicketState.DROPPED: 3,
    TicketState.DONE: 3,
}


def _has_done_report(body: str) -> bool:
    """Whether `body` has a substantive '## Done report' section (D-03):
    thin wrapper delegating to the single shared implementation in
    `frob.tickets._models` -- dedupes the twin copy `tickets/__init__.py`
    used to carry (D-11)."""
    return has_substantive_done_report(body)


_TERMINAL_RANK = 3  # rank shared by TicketState.DONE and TicketState.DROPPED


# frob:ticket T-0682
# frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_report_side_still_wins_when_it_also_outranks_the_reportless_side  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_stale_report_on_lower_rank_still_loses_to_a_strictly_outranking_reportless_side  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_stale_report_on_lower_rank_still_loses_regardless_of_which_side_it_is_on  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_neither_side_reporting_still_falls_back_to_state_rank  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestMergeMainIntoWorktreeRicherState.test_landing_tickets_in_progress_report_survives_the_merge_stage  # noqa: E501
def _newer(a: Ticket, b: Ticket) -> Ticket:
    """Which of two same-id ticket versions is "newer" (T-0682: Done-report
    presence now qualifies state-rank whenever NEITHER side has already
    reached a terminal state -- but does not blanket-override it).

    Three tiers, checked in order:

    1. TERMINAL SUPREMACY (unchanged from before T-0682): if either side is
       `done`/`dropped` (rank 3) and the other is not, the terminal side
       always wins, Done report or not -- a ticket main has already closed
       or dropped must never be resurrected to a lesser state just because
       a stale worktree copy happens to carry Done-report text (T-0537's
       regression lock; also the T-0479-adjacent race where main
       independently drops a ticket a worktree is still mid-flight on --
       `close` must still fail against the terminal state, not silently
       resurrect the worktree's in-progress copy).
    2. Otherwise, if Done-report presence DIFFERS between the two
       non-terminal sides, the reported side wins ONLY IF the reportless
       side does not STRICTLY outrank it. A substantive Done report is
       strong evidence of real, committed-to-land progress -- stronger
       than the bare `state:` field, which a stale copy can carry at an
       EQUAL or LOWER rank than a richer one for free (`queued`/`planned`/
       `in-progress` are all trivially reachable by hand-editing or a
       requeue) -- but it is not proof against a genuinely more-advanced
       rework on the OTHER side: a reviewer-caught inverse of the T-0682
       field incident found that an unqualified "report always wins" rule
       let a STALE report on a lower-rank block (e.g. a ticket requeued
       back down without ever stripping its old report body) beat a
       reportless side that had since made real further progress at a
       strictly higher rank. So: reportless-but-strictly-higher-rank wins
       over reported-but-lower-or-equal-rank; reported wins over
       reportless in every other differing-presence case (equal rank, or
       reported side itself at the higher rank). This still closes the
       original T-0682 incident (the reported side there was ALSO the
       higher-rank side -- in-progress+report vs main's bare queued --
       so it wins either way) while no longer resurrecting a stale report
       over genuine forward progress.
    3. Otherwise (Done-report presence is a wash -- both sides carry one,
       or neither does), fall back to the plain state-rank comparison,
       tie-broken by `b` (the incoming/theirs side) as the final
       deterministic pick -- never a coin flip.

    Either way, the winner's evidence is UNIONED with the loser's
    (`_union_evidence`, D-09) rather than the loser's evidence being
    silently dropped -- the old `len(a.evidence) != len(b.evidence)`
    tiebreak used to pick ONE side's evidence set wholesale, discarding
    the other side's ids entirely when two worktrees closed the same
    ticket with disjoint evidence."""
    rank_a, rank_b = _STATE_RANK[a.state], _STATE_RANK[b.state]
    if _TERMINAL_RANK in (rank_a, rank_b) and rank_a != rank_b:
        winner = a if rank_a > rank_b else b
    else:
        done_a, done_b = _has_done_report(a.body), _has_done_report(b.body)
        if done_a != done_b:
            reported, reported_rank = (a, rank_a) if done_a else (b, rank_b)
            reportless, reportless_rank = (b, rank_b) if done_a else (a, rank_a)
            winner = reportless if reportless_rank > reported_rank else reported
        else:
            winner = b if rank_a == rank_b else (a if rank_a > rank_b else b)
    return _union_evidence(winner, a, b)


def _union_evidence(winner: Ticket, a: Ticket, b: Ticket) -> Ticket:
    """D-09: never let a splice silently drop one side's evidence -- return
    `winner` with its evidence extended (deduplicated, winner's own ids
    first) by any id the OTHER of `a`/`b` carries that `winner` lacks."""
    if a.evidence == b.evidence:
        return winner
    other = b if winner is a else a
    merged = list(winner.evidence)
    merged.extend(e for e in other.evidence if e not in merged)
    if tuple(merged) == winner.evidence:
        return winner
    _log.info(
        "tickets: land splice -- unioned evidence for %s (%d -> %d id(s))",
        winner.id,
        len(winner.evidence),
        len(merged),
    )
    return winner.model_copy(update={"evidence": tuple(merged)})


# frob:doc docs/modules/tickets.md#frob-ticket-land
# `archived_ids` (from main's `tickets-archive.md`, the only authoritative
# archive) is excluded from the merged result unconditionally, from
# EITHER side -- without this, a ticket main already archived reappears
# in the active ledger the moment a stale branch (whose own tickets.md
# still carries it as active, from before it was archived) lands,
# resurrecting exactly the active/archive duplicate-id class a human
# would otherwise have to hand-resolve at merge time (reviewer-caught,
# T-0176).
def splice_ledger(
    ours_text: str,
    theirs_text: str,
    *,
    archived_ids: frozenset[str] = frozenset(),
) -> Result[str, TicketError]:
    """Merge two `tickets.md` ledger texts at the ticket-id level, keeping the
    newest state per section (`_newer`) instead of trusting git's line-level
    textual merge -- the fix for the "both sides append a new ticket near
    the same line" false-conflict class (T-0176), and the tiebreak for a
    genuine same-id divergence (e.g. one side closed a ticket the other
    side is still mid-editing)."""
    ours_parsed = _parse_ledger(ours_text)
    if ours_parsed.is_err:
        return Err(ours_parsed.danger_err)
    theirs_parsed = _parse_ledger(theirs_text)
    if theirs_parsed.is_err:
        return Err(theirs_parsed.danger_err)
    ours, theirs = ours_parsed.danger_ok, theirs_parsed.danger_ok

    merged = _merge_ledger_tickets(ours, theirs)
    _drop_resurrected_ids(merged, archived_ids)
    _log.info(
        "tickets: land splice -- ours=%d theirs=%d merged=%d",
        len(ours),
        len(theirs),
        len(merged),
    )
    return Ok(_render_ledger(merged))


def _merge_ledger_tickets(
    ours: dict[str, Ticket], theirs: dict[str, Ticket]
) -> dict[str, Ticket]:
    """Union `ours`/`theirs` by ticket id, keeping the newer state
    (`_newer`) on any id present in both with a genuine divergence."""
    merged: dict[str, Ticket] = dict(ours)
    for ticket_id, ticket in theirs.items():
        if ticket_id not in merged:
            merged[ticket_id] = ticket
        elif merged[ticket_id] != ticket:
            merged[ticket_id] = _newer(merged[ticket_id], ticket)
    return merged


def _drop_resurrected_ids(
    merged: dict[str, Ticket], archived_ids: frozenset[str]
) -> None:
    """Delete from `merged`, in place, any id already present in
    `archived_ids` (see `splice_ledger`'s resurrection-prevention doc)."""
    resurrected = archived_ids & set(merged)
    for ticket_id in resurrected:
        del merged[ticket_id]
    if resurrected:
        # frob:waive PERF004 reason="runs once after the loop above, not inside it"
        _log.info(
            "tickets: land splice -- dropped %d already-archived id(s): %s",
            len(resurrected),
            sorted(resurrected),
        )


# frob:ticket T-0577
def _preserve_sibling_done_reports(
    merged: dict[str, Ticket], worktree_tickets: dict[str, Ticket], landed_id: str
) -> None:
    """After `_splice_only_ticket` overlays ONLY `landed_id` from the
    worktree, every OTHER (sibling) ticket id comes from `main_tickets`
    untouched -- correct for the T-0479/T-0475 resurrection class (a
    worktree's stale, requeued-on-main sibling must never win), but it has
    a real cost: in a multi-ticket worktree, a sibling that is ALSO done
    (in-progress with a substantive Done report already written, awaiting
    its own `frob ticket land`) has that Done report silently discarded the
    moment ANY ticket in the same worktree lands first, because main's copy
    of that sibling is still a bare `queued`/`planned` block from before
    the worktree ever touched it (real incident: landing T-0386 erased
    T-0387/T-0388's Done reports and regressed them to queued).

    This closes that gap without reopening T-0479: for each sibling id
    present in `merged` (from main) that also exists in `worktree_tickets`,
    keep the WORKTREE's copy in place of main's ONLY when main's side has
    no substantive Done report yet worktree's does -- richer state
    (a Done report) always wins over a bare state block, but a genuine
    main-side requeue (main's side already carries no Done report AND the
    worktree's side is merely a stale advanced state with no Done report
    either, the T-0479 case) is untouched, since neither side satisfies
    the swap condition and main's existing entry is left as-is."""
    for ticket_id, ticket in worktree_tickets.items():
        if ticket_id == landed_id or ticket_id not in merged:
            continue
        main_side = merged[ticket_id]
        if main_side == ticket:
            continue
        main_has_done = _has_done_report(main_side.body)
        worktree_has_done = _has_done_report(ticket.body)
        if worktree_has_done and not main_has_done:
            _log.info(
                "tickets: land splice -- preserved %s's Done report from "
                "worktree (main's copy had none) while landing %s",
                ticket_id,
                landed_id,
            )
            merged[ticket_id] = _union_evidence(ticket, main_side, ticket)


# frob:ticket T-0637
# frob:tests tests/test_ticket_land.py::TestStandaloneSiblingDraftSurvivesLand.test_sibling_draft_ticket_finalized_and_lands_alongside  # noqa: E501
def _carry_forward_new_worktree_tickets(
    merged: dict[str, Ticket], worktree_tickets: dict[str, Ticket], landed_id: str
) -> None:
    """Carry over any ticket id present ONLY in `worktree_tickets` -- never
    yet on main/`merged`'s base -- that is not `landed_id` itself.

    `_splice_only_ticket`'s T-0479 scoping deliberately never lets a
    worktree's STALE view of an ALREADY-ON-MAIN ticket win (that is the
    sibling-resurrection class it closes) -- but a ticket main has never
    seen at all carries no stale state to protect against, so silently
    dropping it is pure data loss with no matching safety benefit. This was
    the T-0637 field incident: a standalone sibling draft ticket
    (`frob ticket new` filed mid-session off the default branch, T-0162)
    present only in the worktree's ledger vanished the moment ANY ticket
    from that worktree landed, because neither this overlay (before this
    fix) nor `_preserve_sibling_done_reports` (which only ever touches ids
    `merged` already has) ever considered an id absent from BOTH main and
    the overlay target. Skips `landed_id` (the caller's own overlay already
    handles it) and anything `merged` already has an entry for (that path
    is `_preserve_sibling_done_reports`'s job, not this one's)."""
    for ticket_id, ticket in worktree_tickets.items():
        if ticket_id == landed_id or ticket_id in merged:
            continue
        merged[ticket_id] = ticket
        _log.info(
            "tickets: land splice -- carried forward new sibling ticket %s "
            "(not previously on main) while landing %s",
            ticket_id,
            landed_id,
        )


# frob:ticket T-0479
def _splice_only_ticket(
    main_text: str,
    worktree_text: str,
    ticket_id: str,
    *,
    archived_ids: frozenset[str] = frozenset(),
) -> Result[str, TicketError]:
    """Merge `tickets.md` by taking MAIN's ledger as the base and overlaying
    ONLY `ticket_id`'s own block from `worktree_text` (T-0479): every other
    ticket id comes from `main_text` untouched. `splice_ledger`'s original
    whole-ledger, keep-newest-per-id merge let a worktree's stale view of a
    SIBLING ticket (in-progress in the worktree from before that sibling was
    later requeued back to queued on main) win the `_newer` state-rank
    comparison and resurrect the stale state on main (T-0475) -- state-rank
    assumes forward-only progress and cannot tell a genuine advance from a
    requeue's backward transition. Scoping the overlay to just the one
    ticket actually being landed makes that whole class of resurrection
    structurally impossible: a sibling ticket's ledger entry is never even
    considered here, no matter what the worktree's copy says. If `ticket_id`
    is present in both with a genuine divergence, `_newer` still resolves
    the winner (and unions evidence) for that one id, exactly as before.
    A `ticket_id` that exists only in `worktree_text` (not yet in
    `main_text`, e.g. a fresh/draft ticket) is still applied -- `land`
    lands one ticket per call, and this is that ticket's own first entry
    onto main."""
    main_parsed = _parse_ledger(main_text)
    if main_parsed.is_err:
        return Err(main_parsed.danger_err)
    worktree_parsed = _parse_ledger(worktree_text)
    if worktree_parsed.is_err:
        return Err(worktree_parsed.danger_err)
    main_tickets, worktree_tickets = main_parsed.danger_ok, worktree_parsed.danger_ok

    merged = dict(main_tickets)
    incoming = worktree_tickets.get(ticket_id)
    if incoming is not None:
        if ticket_id in merged and merged[ticket_id] != incoming:
            merged[ticket_id] = _newer(merged[ticket_id], incoming)
        else:
            merged[ticket_id] = incoming
    _preserve_sibling_done_reports(merged, worktree_tickets, ticket_id)
    _carry_forward_new_worktree_tickets(merged, worktree_tickets, ticket_id)
    _drop_resurrected_ids(merged, archived_ids)
    _log.info(
        "tickets: land splice (ticket-scoped) -- %s only, main=%d ticket(s), merged=%d",
        ticket_id,
        len(main_tickets),
        len(merged),
    )
    return Ok(_render_ledger(merged))


def _porcelain_dirty(root: Path) -> Result[bool, LandError]:
    """Whether `root`'s working tree has any uncommitted change (tracked or
    not), ignoring `.frob/` (T-0577): `land`'s own `ledger_lock` creates
    `.frob/tickets.lock` in `root` BEFORE this check ever runs (the whole
    `land()` body, `_refuse_if_main_dirty` included, now runs under that
    lock -- see `land`'s docstring), and `.frob/` is frob-local scratch
    state a repo is expected to `.gitignore` anyway (baseline/coverage
    stamps, journal records, this same lock file) -- never a real
    "uncommitted change" a landing should refuse on."""
    spawned = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.error("land: git status failed in %s", root)
        return Err(LandError.GitFailed)
    dirty_lines = [
        line
        for line in spawned.danger_ok.stdout.splitlines()
        if line.strip() and not line[3:].strip().startswith(".frob/")
    ]
    return Ok(bool(dirty_lines))


def _conflicted_files(root: Path) -> set[str]:
    """Paths git currently reports unmerged (`U`) in `root`'s index."""
    spawned = run_argv(
        ["git", "-C", str(root), "diff", "--name-only", "--diff-filter=U"]
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return set()
    return {
        line.strip() for line in spawned.danger_ok.stdout.splitlines() if line.strip()
    }


def _deletion_glob_too_broad(glob: str) -> bool:
    """Whether a scope glob is too broad to trust for authorizing a
    DELETION (D-12): a bare top-level directory (`src/`, expanded to
    `src/**`) or the whole-tree `.`/`*` pattern. `scope_matches`'s
    ordinary dir-glob expansion (T-0241) is correct for the general
    "is this file in scope" question, but a ticket scoped only to a
    single top-level directory silently authorizes deleting ANYTHING
    under it -- exactly the stale-base incident class this filter exists
    to catch. A more specific glob (`src/frob/`, `src/frob/tickets/**`)
    is still trusted."""
    stripped = glob.removesuffix("/**").removesuffix("/*").rstrip("/")
    if stripped in ("", ".", "*"):
        return True
    return "/" not in stripped


def _deletion_owned(path: str, scope: tuple[str, ...]) -> bool:
    """Whether `path` is authorized as an OWNED deletion by `scope`: matches
    `scope_matches` AND is not matched only via an over-broad glob (D-12).
    Deliberately stricter than plain `scope_matches`, and used only
    by the deletion filter -- every other scope-consulting site (SCOPE001,
    pre-work digests, ordinary in-scope checks) keeps the normal
    `scope_matches` semantics unchanged."""
    from frob.tickets._models import _scope_globs, _split_scope_entries

    narrow_globs = [
        glob
        for glob in _scope_globs(_split_scope_entries(scope))
        if not _deletion_glob_too_broad(glob)
    ]
    return any(fnmatch.fnmatch(path, glob) for glob in narrow_globs)


def _validate_closeable(ticket: Ticket) -> Result[None, LandError]:
    """The evidence + Done-report preconditions `transition(..., DONE)` will
    enforce anyway -- checked here FIRST, before any git mutation, so a
    landing never merges main into the worktree only to discover at close
    time that it must be unwound (the exact ordering hazard T-0176 exists
    to close). Also re-checks the T-0215 kind-consistency rule
    (`_transition_guard`'s DONE-path twin): a non-docs-kind ticket carrying
    any `cmd:` evidence entry -- kind hand-edited after the entry was
    recorded, or the entry hand-pasted directly into the ledger -- must
    never land, mirroring the write-time gate in `add_cmd_evidence`."""
    if not ticket.evidence or not _has_done_report(ticket.body):
        _log.error(
            "land: %s cannot land -- missing evidence or a Done report; "
            "record evidence (`frob ticket evidence %s <node-id>...`, or for "
            "a docs-kind ticket `frob ticket close %s --evidence-cmd "
            "'<command>'`) and add a '## Done report' section under %s's "
            "entry in tickets.md, then retry `frob ticket land %s`",
            ticket.id,
            ticket.id,
            ticket.id,
            ticket.id,
            ticket.id,
        )
        return Err(LandError.NotCloseable)
    return _validate_evidence_kind_consistency(ticket)


def _validate_evidence_kind_consistency(ticket: Ticket) -> Result[None, LandError]:
    """`Err(NotCloseable)` if `ticket`'s kind disallows cmd: evidence but it
    carries some anyway (see `_validate_closeable`'s T-0215 doc)."""
    if ticket.kind not in CMD_EVIDENCE_ALLOWED_KINDS and any(
        is_cmd_evidence(e) for e in ticket.evidence
    ):
        _log.error(
            "land: %s cannot land -- kind=%s carries cmd: evidence, only "
            "allowed for kind in %s; fix the ticket's kind or replace the "
            "cmd: entry with real pytest --evidence node ids, then retry "
            "`frob ticket land %s`",
            ticket.id,
            ticket.kind,
            sorted(k.value for k in CMD_EVIDENCE_ALLOWED_KINDS),
            ticket.id,
        )
        return Err(LandError.NotCloseable)
    return Ok(None)


def _abort_merge(worktree: Path) -> None:
    """Best-effort `git merge --abort` to leave the worktree exactly as found."""
    run_argv(["git", "-C", str(worktree), "merge", "--abort"])


def _archived_ids(root: Path) -> frozenset[str]:
    """Every ticket id in `root`'s `tickets-archive.md` -- the authoritative
    "already archived, must never re-enter the active ledger" set a splice
    guards against (T-0176 reviewer fix). An unreadable/malformed archive
    degrades to empty rather than blocking the land -- archive resurrection
    is a correctness bug worth guarding against, not a reason to hard-fail
    a landing whose archive happens to be unparseable for an unrelated
    reason."""
    path = archive_path(root)
    if not path.exists():
        return frozenset()
    parsed = _parse_ledger(path.read_text(encoding="utf-8"))
    if parsed.is_err:
        _log.warning(
            "land: %s unreadable (%s), archive-resurrection guard degraded to empty",
            path,
            parsed.danger_err,
        )
        return frozenset()
    return frozenset(parsed.danger_ok)


def _splice_and_stage(
    checkout: Path,
    pre_text: str,
    incoming_text: str,
    *,
    archived_ids: frozenset[str] = frozenset(),
    ticket_id: str | None = None,
) -> Result[str, LandError]:
    """Write the ledger splice of `pre_text`/`incoming_text` to `checkout`'s
    tickets.md and `git add` it; overrides whatever git's own textual merge
    produced -- tickets.md is ALWAYS resolved via a splice, never via git's
    line-level algorithm, so a both-sides-append never false-conflicts and a
    same-id divergence always keeps the newest state (T-0176).

    `ticket_id`, when given, scopes the splice to ONLY that ticket's own
    block via `_splice_only_ticket` (T-0479) -- every other id comes from
    `pre_text` untouched, so a worktree's stale sibling-ticket state can
    never overlay main's newer one. `ticket_id=None` (the default) keeps the
    original whole-ledger `splice_ledger` merge, used only where BOTH sides
    are pulling in each other's full set of tickets on purpose (there is no
    "one ticket being landed" to scope to). `archived_ids` excludes anything
    main has already archived from ever re-entering the merged active
    ledger, either way."""
    if ticket_id is not None:
        spliced = _splice_only_ticket(
            pre_text, incoming_text, ticket_id, archived_ids=archived_ids
        )
    else:
        spliced = splice_ledger(pre_text, incoming_text, archived_ids=archived_ids)
    if spliced.is_err:
        _log.error(
            "land: tickets.md splice failed (%s) -- resolve manually in %s",
            spliced.danger_err,
            checkout,
        )
        return Err(LandError.GitFailed)
    ledger_path(checkout).write_text(spliced.danger_ok, encoding="utf-8")
    add = run_argv(["git", "-C", str(checkout), "add", "tickets.md"])
    if add.is_err or add.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(spliced.danger_ok)


def _read_ledger_text_or_empty(checkout: Path) -> str:
    """`tickets.md`'s text under `checkout`, or `""` if it does not exist."""
    path = ledger_path(checkout)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _merge_main_into_worktree(
    root: Path, worktree: Path, ticket: Ticket, main_branch: str
) -> Result[bool, LandError]:
    """Stage (`--no-commit`) main into the worktree, resolving any tickets.md
    conflict via `splice_ledger`; any OTHER conflicted file aborts loudly.
    Returns whether a merge actually happened (False = worktree was already
    up to date with main, a no-op)."""
    pre_text = _read_ledger_text_or_empty(worktree)
    main_text = _read_ledger_text_or_empty(root)

    merged = run_argv(
        ["git", "-C", str(worktree), "merge", "--no-commit", "--no-ff", main_branch]
    )
    if merged.is_err:
        return Err(LandError.GitFailed)
    if (
        merged.danger_ok.returncode == 0
        and "up to date" in merged.danger_ok.stdout.lower()
    ):
        return Ok(False)

    conflict_check = _check_only_tickets_conflicted(worktree, ticket, main_branch)
    if conflict_check.is_err:
        return Err(conflict_check.danger_err)

    # T-0479/T-0475: base the splice on MAIN's ledger (main_text), not the
    # worktree's, and overlay ONLY the ticket being landed (`ticket.id`)
    # from the worktree's pre-merge copy. This is the exact site of the
    # T-0475 incident: the old whole-ledger merge based the splice on the
    # worktree's stale `pre_text`, so a sibling ticket the worktree still
    # remembered as in-progress (from before it was later requeued back to
    # queued on main) beat main's newer queued state on `_newer`'s state-
    # rank comparison and resurrected it. Scoping to `ticket.id` makes every
    # sibling ticket's state come from main untouched, unconditionally --
    # only the ticket actually being landed is ever taken from the
    # worktree.
    spliced = _splice_and_stage(
        worktree,
        main_text,
        pre_text,
        archived_ids=_archived_ids(root),
        ticket_id=ticket.id,
    )
    if spliced.is_err:
        _abort_merge(worktree)
        return Err(spliced.danger_err)
    return Ok(True)


# frob:ticket T-0479
def _auto_resolve_out_of_scope_conflicts(
    cwd: Path, ticket: Ticket, *, keep: str
) -> Result[frozenset[str], LandError]:
    """After a merge/squash leaves paths conflicted in `cwd`, auto-resolve
    every conflicted path OUTSIDE `ticket.scope` by `git checkout --<keep>`
    (`keep` is "ours" or "theirs", matching git's own vocabulary for the
    merge direction in play) and staging it, then return whatever is STILL
    conflicted (i.e. paths inside `ticket.scope`, plus any out-of-scope path
    the checkout itself failed on) for the caller to treat as a real
    conflict (T-0479).

    `ticket.scope` genuinely never authorized the worktree to change a file
    outside it -- a conflict there is definitionally noise from an
    unrelated concurrent main change, not an editorial decision belonging
    to this ticket, so taking `keep`'s side is always correct rather than a
    guess. `tickets.md` is excluded unconditionally; it is always resolved
    via a ledger splice (`_splice_and_stage`), never via `git checkout`."""
    conflicted = _conflicted_files(cwd) - {"tickets.md"}
    if not conflicted:
        return Ok(frozenset())
    still_conflicted = {f for f in conflicted if scope_matches(f, ticket.scope)}
    for path in sorted(conflicted - still_conflicted):
        resolved = _checkout_and_stage(cwd, keep, path)
        if resolved.is_err:
            _log.warning(
                "land: %s auto-resolve of out-of-scope conflict %s (keep=%s) "
                "failed -- leaving it conflicted for manual resolution",
                ticket.id,
                path,
                keep,
            )
            still_conflicted.add(path)
            continue
        _log.info(
            "land: %s auto-resolved out-of-scope conflict in %s by keeping "
            "%s's side (not in scope %s)",
            ticket.id,
            path,
            keep,
            list(ticket.scope),
        )
    return Ok(frozenset(still_conflicted))


def _checkout_and_stage(cwd: Path, keep: str, path: str) -> Result[None, LandError]:
    """`git checkout --<keep> -- <path> && git add <path>` in `cwd`."""
    checkout = run_argv(["git", "-C", str(cwd), "checkout", f"--{keep}", "--", path])
    if checkout.is_err or checkout.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    add = run_argv(["git", "-C", str(cwd), "add", "--", path])
    if add.is_err or add.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(None)


def _check_only_tickets_conflicted(
    worktree: Path, ticket: Ticket, main_branch: str
) -> Result[None, LandError]:
    """`Err(MergeConflict)` (aborting the merge) if any IN-SCOPE file besides
    tickets.md is still conflicted after `_merge_main_into_worktree`'s
    merge; any OUT-OF-SCOPE conflict is auto-resolved by taking main's side
    first (T-0479), since main is `theirs` in this merge direction (main
    merged into the worktree)."""
    resolved = _auto_resolve_out_of_scope_conflicts(worktree, ticket, keep="theirs")
    if resolved.is_err:
        _abort_merge(worktree)
        return Err(resolved.danger_err)
    remaining = resolved.danger_ok
    if remaining:
        _abort_merge(worktree)
        _log.error(
            "land: %s merging %s into %s conflicts in scoped file(s): %s -- "
            "resolve manually (cd %s && git merge %s), commit, then retry "
            "`frob ticket land %s --worktree %s`",
            ticket.id,
            main_branch,
            worktree,
            sorted(remaining),
            worktree,
            main_branch,
            ticket.id,
            worktree,
        )
        return Err(LandError.MergeConflict)
    return Ok(None)


def _unowned_deletions(
    root: Path, worktree: Path, scope: tuple[str, ...], main_branch: str
) -> Result[tuple[str, ...], LandError]:
    """Files main has that the worktree (post-merge) deletes, outside `scope`
    -- the stale-base guard: a worktree branched from an old main can end up
    silently deleting a feature main already landed, and this is the check
    that catches it before it reaches main (T-0176)."""
    diff = run_argv(
        [
            "git",
            "-C",
            str(worktree),
            "diff",
            main_branch,
            "--diff-filter=D",
            "--name-only",
        ]
    )
    if diff.is_err or diff.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    deleted = [
        line.strip() for line in diff.danger_ok.stdout.splitlines() if line.strip()
    ]
    unowned = tuple(f for f in deleted if not _deletion_owned(f, scope))
    return Ok(unowned)


def _wip_commit(
    worktree: Path, ticket_id: str, *, dry_run: bool
) -> Result[bool, LandError]:
    """Commit any uncommitted worktree changes as a WIP snapshot before
    landing -- the manual "wip-commit in the worktree" step folded into
    `land` so nothing an agent forgot to commit is silently dropped by the
    merge that follows."""
    dirty = _porcelain_dirty(worktree)
    if dirty.is_err:
        return Err(dirty.danger_err)
    if not dirty.danger_ok:
        return Ok(False)
    if dry_run:
        _log.info(
            "land: %s would wip-commit uncommitted changes in %s", ticket_id, worktree
        )
        return Ok(True)
    return _do_wip_commit(worktree, ticket_id)


def _do_wip_commit(worktree: Path, ticket_id: str) -> Result[bool, LandError]:
    """`git add -A && git commit` a WIP snapshot in `worktree`."""
    add = run_argv(["git", "-C", str(worktree), "add", "-A"])
    if add.is_err or add.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    commit = run_argv(
        [
            "git",
            "-C",
            str(worktree),
            "commit",
            "-m",
            f"wip: pre-land snapshot for {ticket_id}",
        ]
    )
    if commit.is_err or commit.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    _log.info("land: %s wip-committed uncommitted worktree changes", ticket_id)
    return Ok(True)


_KIND_TO_COMMIT_TYPE = {
    "feature": "feat",
    "bug": "fix",
    "security": "fix",
    "ux": "fix",
    "docs": "docs",
    "invariant": "test",
    "incident": "fix",
}


def _commit_message(ticket: Ticket, final_id: str) -> str:
    """Conventional-commit message for the landing commit (ASCII, no
    trailing period, no Co-Authored-By -- repo convention)."""
    commit_type = _KIND_TO_COMMIT_TYPE.get(ticket.kind.value, "chore")
    subject = f"{commit_type}(tickets): land {final_id} {ticket.title}"
    return subject[:120]


# frob:ticket T-0176
# frob:doc docs/modules/tickets.md#frob-ticket-land
# `dry_run` runs every check and every git mutation the real run would
# (merge, splice, deletion-check) then unwinds it via
# `merge --abort`/`reset --hard`, so a clean dry run is a real guarantee,
# not a guess (T-0176).
def land(
    root: Path,
    ticket_id: str,
    worktree: Path,
    *,
    dry_run: bool = False,
    collected: Callable[[], frozenset[str]] | None = None,
    passed: Callable[[Sequence[str]], frozenset[str]] | None = None,
    covers_scope: Callable[[Ticket], bool | None] | None = None,
    bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]]
    | None = None,
    rebuild_natives: Callable[[Path], bool] | None = None,
) -> Result[LandReport, LandError]:
    """Land `ticket_id` from `worktree` onto `root`'s current branch:
    precheck, wip-commit + merge + deletion-check, finalize + close, then
    squash-apply onto main with a conventional-commit message.

    T-0338: `bump_version` and `rebuild_natives` let a caller fold the two
    remaining coordinator-plumbing steps (REL001 version bump/stamp, and
    a native-extension rebuild trigger) into the same one-command land
    instead of leaving them as manual follow-ups. Both are invoked AFTER
    the squash-apply is staged onto `root` (so their writes land in the
    SAME commit) but BEFORE the T-0463 completeness assertion and the
    final commit -- a failure from either unwinds the squash exactly like
    any other land failure. `bump_version(root, ticket, final_id)`
    computes and applies whatever `frob.release` says the just-squashed
    public API demands (pyproject.toml + CHANGELOG.md + `.frob-release.
    json`, all staged), returning `Ok(new_version)` if a bump was applied,
    `Ok(None)` if none was needed. `rebuild_natives(root)` is invoked only
    when the landed changeset touches a native source tree (frob-core/,
    strata-core/) and returns whether the rebuild succeeded (best-effort:
    a `False` is logged but does not fail the land, matching the T-0248
    stale-native warning's existing non-blocking severity). Both default
    to `None` (skip), matching every caller before T-0338 -- computing
    either needs `frob.release`/`frob.graph`/subprocess access
    `frob.tickets` deliberately does not have (docs/rework.md cycle-
    avoidance); the `frob ticket land` CLI supplies both by default (see
    `ticket_runner.py`'s `_land`).

    D-05: `collected`/`passed`/`covers_scope` let a caller with a fresh
    test-collection/run/graph-binding oracle re-verify the ticket's
    evidence against the POST-MERGE worktree tree (after
    `_merge_main_into_worktree` has run -- NOT the pre-merge worktree
    report `_land_precheck` validated) before it is finalized and closed,
    instead of `land` trusting whatever the worktree's `Done report`
    claims. They are CALLABLES, not precomputed values, because the
    caller cannot know the post-merge tree state before `land` has
    actually performed the merge internally -- `land` invokes them at the
    right point instead: `collected()` (no args, run against `worktree`
    after the merge) re-checks every non-cmd evidence id still resolves;
    `passed(non_cmd_evidence_ids)` (given the reloaded post-merge ticket's
    ids) returns the subset actually observed passing; `covers_scope
    (ticket)` (given the reloaded post-merge ticket) answers the D-02
    scope-binding question the same way `transition`'s own `covers_scope`
    parameter does (`True`/`False`/`None`-skip). All three default to
    `None` (skip, matching every caller before D-05) since computing them
    needs `frob.testing`/`frob.graph` access `frob.tickets` deliberately
    does not have (docs/rework.md cycle-avoidance) -- a caller that sits
    above both (today, `frob.gates` for `covers_scope`'s computation, and
    the `frob ticket land` CLI, which supplies all three by default --
    see `ticket_runner.py`'s `_land`) provides them. Passing nothing
    preserves the exact pre-D-05 behavior, which is why the library
    default stays permissive even though the CLI's default is strict.

    T-0577: the ENTIRE precheck-through-squash-commit body runs under
    `root`'s dedicated `_land_lock` (a cross-process `flock`, same
    primitive family as `frob.tickets._store.ledger_lock`'s T-0458
    single-writer lock but its OWN file -- see `_land_lock`'s doc for why
    it cannot reuse `ledger_lock`'s path) -- a second `land()` against the
    SAME `root` (a different agent/coordinator process landing a different
    ticket concurrently) blocks at the lock acquire instead of racing this
    one. This is what makes the REL001 version bump (`bump_version`,
    computed against `root`'s tree from INSIDE this critical section)
    collision-free: two lands can no longer both read the same
    pre-bump manifest version and each compute the same "next" version,
    the real incident (6 version-number collisions from parallel branches
    in one session) this closes. Manual, non-`land` coordinator surgery
    that mutates `root` while holding no lock is not protected by this --
    only concurrent `land()` calls are serialized against each other."""
    root, worktree = root.resolve(), worktree.resolve()

    with _land_lock(root):
        return _land_locked(
            root,
            ticket_id,
            worktree,
            dry_run=dry_run,
            collected=collected,
            passed=passed,
            covers_scope=covers_scope,
            bump_version=bump_version,
            rebuild_natives=rebuild_natives,
        )


# frob:waive ARCH001 reason="already the decomposed orchestrator (T-0577): delegates to _land_precheck/_land_merge_stage/_reverify_evidence_post_merge/_land_finalize_and_close/_land_squash_apply; remaining length is the try/finally intent-marker sequencing plus the D-05/T-0456 ordering-rationale comments themselves, not undecomposed logic"  # noqa: E501
def _land_locked(
    root: Path,
    ticket_id: str,
    worktree: Path,
    *,
    dry_run: bool,
    collected: Callable[[], frozenset[str]] | None,
    passed: Callable[[Sequence[str]], frozenset[str]] | None,
    covers_scope: Callable[[Ticket], bool | None] | None,
    bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]] | None,
    rebuild_natives: Callable[[Path], bool] | None,
) -> Result[LandReport, LandError]:
    """`land`'s actual body (T-0577), run by the caller already holding
    `root`'s `ledger_lock` -- split out only so `land`'s docstring can state
    the locking contract once at the public entry point rather than
    interleaved with the implementation."""
    precheck = _land_precheck(root, worktree, ticket_id)
    if precheck.is_err:
        return Err(precheck.danger_err)
    ticket, main_branch_name = precheck.danger_ok

    # T-0456: record that a multi-step land is starting BEFORE any of the
    # steps below mutate the worktree/root -- cleared in the `finally` below
    # on every exit (success or a clean, handled Err) so a marker that
    # OUTLIVES this process means it crashed mid-land, the condition `frob
    # ticket reconcile` surfaces as an anomaly instead of it going unnoticed.
    write_intent(root, ticket_id, worktree)
    try:
        stage = _land_merge_stage(
            root, worktree, ticket, ticket_id, main_branch_name, dry_run
        )
        if stage.is_err:
            return Err(stage.danger_err)
        wip_committed, did_merge, dry_run_report = stage.danger_ok

        # D-05: re-verify BEFORE the dry-run early return -- otherwise a
        # `--dry-run` would report clean without ever running the
        # post-merge check, defeating T-0176's "a clean dry run is a real
        # guarantee, not a guess" design intent.
        post_merge_check = _reverify_evidence_post_merge(
            worktree, ticket_id, collected, passed
        )
        if post_merge_check.is_err:
            if did_merge:
                _abort_merge(worktree)
            return Err(post_merge_check.danger_err)

        if dry_run_report is not None:
            return Ok(dry_run_report)

        _refresh_prework_sweep(worktree, ticket)

        finalized = _land_finalize_and_close(
            worktree, ticket_id, did_merge, main_branch_name, covers_scope=covers_scope
        )
        if finalized.is_err:
            return Err(finalized.danger_err)
        final_id = finalized.danger_ok

        return _land_squash_apply(
            root,
            worktree,
            ticket,
            ticket_id,
            final_id,
            wip_committed,
            did_merge,
            main_branch_name,
            bump_version=bump_version,
            rebuild_natives=rebuild_natives,
        )
    finally:
        clear_intent(root, ticket_id)


def _reverify_evidence_post_merge(
    worktree: Path,
    ticket_id: str,
    collected: Callable[[], frozenset[str]] | None,
    passed: Callable[[Sequence[str]], frozenset[str]] | None,
) -> Result[None, LandError]:
    """D-05: re-load `ticket_id` from the POST-MERGE worktree ledger and
    re-check every non-cmd evidence id still resolves against
    `collected()` and still shows passing in `passed(non_cmd_ids)` -- the
    ledger state `land` is about to finalize/close/squash-apply may differ
    from what `_land_precheck` validated pre-merge (a splice can rewrite
    `ticket.evidence`, see `_newer`/`_union_evidence`). `collected=None`
    and `passed=None` (both defaults) skip this entirely, so `land`'s
    behavior is unchanged unless a caller opts in."""
    if collected is None and passed is None:
        return Ok(None)
    from frob.tickets import _load_one

    loaded = _load_one(worktree, ticket_id)
    if loaded.is_err:
        _log.error(
            "land: %s not found post-merge in %s -- cannot re-verify evidence",
            ticket_id,
            worktree,
        )
        return Err(LandError.NotFound)
    ticket = loaded.danger_ok
    non_cmd = [e for e in ticket.evidence if not is_cmd_evidence(e)]

    if collected is not None:
        collected_ids = collected()
        unresolved = [e for e in non_cmd if not matches_collected(e, collected_ids)]
        if unresolved:
            _log.error(
                "land: %s evidence no longer resolves post-merge: %s -- "
                "the merged tree may have renamed/removed the covering "
                "test(s); refresh evidence (`frob ticket evidence %s "
                "<node-id>...`) and retry",
                ticket_id,
                unresolved,
                ticket_id,
            )
            return Err(LandError.NotCloseable)

    if passed is not None:
        passing_ids = passed(non_cmd)
        failing = [e for e in non_cmd if e not in passing_ids]
        if failing:
            _log.error(
                "land: %s evidence did not pass post-merge: %s -- fix the "
                "failure and re-record evidence before retrying",
                ticket_id,
                failing,
            )
            return Err(LandError.NotCloseable)
    return Ok(None)


def _refuse_if_main_dirty(
    root: Path, worktree: Path, ticket_id: str
) -> Result[None, LandError]:
    """`Err(DirtyMain)` if `root` has any uncommitted change."""
    main_dirty = _porcelain_dirty(root)
    if main_dirty.is_err:
        return Err(main_dirty.danger_err)
    if main_dirty.danger_ok:
        _log.error(
            "land: %s refused -- %s has uncommitted changes; commit or stash "
            "them first (git -C %s status), then retry `frob ticket land %s "
            "--worktree %s`",
            ticket_id,
            root,
            root,
            ticket_id,
            worktree,
        )
        return Err(LandError.DirtyMain)
    return Ok(None)


def _land_precheck(
    root: Path, worktree: Path, ticket_id: str
) -> Result[tuple[Ticket, str], LandError]:
    """Refuse on a dirty main, load+validate the worktree's ticket is
    closeable, and resolve main's current branch name -- everything `land`
    must check BEFORE any git mutation."""
    from frob.tickets import _load_one

    dirty_check = _refuse_if_main_dirty(root, worktree, ticket_id)
    if dirty_check.is_err:
        return Err(dirty_check.danger_err)

    loaded = _load_one(worktree, ticket_id)
    if loaded.is_err:
        _log.error("land: %s not found in worktree store at %s", ticket_id, worktree)
        return Err(LandError.NotFound)
    ticket = loaded.danger_ok

    validated = _validate_closeable(ticket)
    if validated.is_err:
        return Err(validated.danger_err)

    main_branch = current_branch(root)
    if main_branch.is_err:
        return Err(LandError.GitFailed)
    return Ok((ticket, main_branch.danger_ok))


def _land_merge_stage(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    ticket_id: str,
    main_branch_name: str,
    dry_run: bool,
) -> Result[tuple[bool, bool, LandReport | None], LandError]:
    """wip-commit, merge main into the worktree, and check for unowned
    deletions; returns `(wip_committed, did_merge, dry_run_report)` where
    `dry_run_report` is the early-return report for a clean dry run, else
    `None`."""
    wip = _wip_commit(worktree, ticket_id, dry_run=dry_run)
    if wip.is_err:
        return Err(wip.danger_err)
    wip_committed = wip.danger_ok

    merged = _merge_main_into_worktree(root, worktree, ticket, main_branch_name)
    if merged.is_err:
        return Err(merged.danger_err)
    did_merge = merged.danger_ok

    unowned_check = _check_unowned_deletions(
        root, worktree, ticket, ticket_id, main_branch_name, did_merge
    )
    if unowned_check.is_err:
        return Err(unowned_check.danger_err)

    if not dry_run:
        return Ok((wip_committed, did_merge, None))

    report = _dry_run_report(
        worktree, ticket_id, main_branch_name, wip_committed, did_merge
    )
    return Ok((wip_committed, did_merge, report))


# frob:ticket T-0236
def _refresh_prework_sweep(worktree: Path, ticket: Ticket) -> None:
    """Re-record `ticket`'s pre-work sweep against the just-merged worktree
    state, post-merge and pre-close.

    Landing can pull in unrelated main commits that touch the ticket's scope
    globs, moving the recorded sweep's scope digest out from under it -- if
    `land` then fails before reaching close (evidence or Done-report issue),
    the ticket is left in-progress carrying a sweep that `frob check`'s
    PRE001 will flag as stale on the very next check, even though nothing
    about THIS ticket's own work was actually un-swept (T-0236). Refreshing
    here, unconditionally, before the close attempt below means a retried
    land (or a reviewer's `frob check --ticket` in the interim) sees a sweep
    that matches the current tree, not a stale one caused by drift outside
    this ticket's control.

    Best-effort: a refresh failure is logged and does not block landing --
    the close step's own evidence/Done-report gates are what actually gate
    `land`, not this sweep's freshness.
    """
    from frob.gates import sweep_ticket

    swept = sweep_ticket(worktree, ticket)
    if swept.is_err:
        _log.warning(
            "land: %s post-merge pre-work sweep refresh failed (%s) -- "
            "PRE001 may report staleness until `frob ticket sweep %s` "
            "is run manually",
            ticket.id,
            swept.danger_err,
            ticket.id,
        )


def _dry_run_report(
    worktree: Path,
    ticket_id: str,
    main_branch_name: str,
    wip_committed: bool,
    did_merge: bool,
) -> LandReport:
    """Abort any staged merge and build the early-return `LandReport` for a
    clean dry run."""
    if did_merge:
        _abort_merge(worktree)
    _log.info(
        "land: %s dry-run clean -- would merge=%s, would close, would "
        "squash-apply onto %s",
        ticket_id,
        did_merge,
        main_branch_name,
    )
    return LandReport(
        ticket_id=ticket_id,
        final_id=ticket_id,
        dry_run=True,
        wip_committed=wip_committed,
        merged_main_into_worktree=did_merge,
        ledger_spliced=did_merge,
        unowned_deletions=(),
    )


def _check_unowned_deletions(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    ticket_id: str,
    main_branch_name: str,
    did_merge: bool,
) -> Result[None, LandError]:
    """`Err(UnownedDeletions)` (aborting the merge first) if the worktree
    deletes any file outside `ticket.scope`."""
    unowned = _unowned_deletions(root, worktree, ticket.scope, main_branch_name)
    if unowned.is_err:
        if did_merge:
            _abort_merge(worktree)
        return Err(unowned.danger_err)
    if unowned.danger_ok:
        if did_merge:
            _abort_merge(worktree)
        _log.error(
            "land: %s refused -- worktree deletes file(s) outside its scope "
            "%s: %s. If intentional, add the path(s) to the ticket's scope; "
            "if accidental (a stale worktree base), restore them: "
            "cd %s && git checkout %s -- %s ; then retry "
            "`frob ticket land %s --worktree %s`",
            ticket_id,
            list(ticket.scope),
            list(unowned.danger_ok),
            worktree,
            main_branch_name,
            " ".join(unowned.danger_ok),
            ticket_id,
            worktree,
        )
        return Err(LandError.UnownedDeletions)
    return Ok(None)


def _land_finalize_and_close(
    worktree: Path,
    ticket_id: str,
    did_merge: bool,
    main_branch_name: str,
    *,
    covers_scope: Callable[[Ticket], bool | None] | None = None,
) -> Result[str, LandError]:
    """Commit the merge (if any), finalize a draft id, close the ticket,
    and commit those writes too -- returns the ticket's final id."""
    if did_merge:
        commit = run_argv(
            [
                "git",
                "-C",
                str(worktree),
                "commit",
                "-m",
                f"merge {main_branch_name} into worktree for landing {ticket_id}",
            ]
        )
        if commit.is_err or commit.danger_ok.returncode != 0:
            return Err(LandError.GitFailed)

    finalized = _finalize_and_close_ticket(
        worktree, ticket_id, covers_scope=covers_scope
    )
    if finalized.is_err:
        return Err(finalized.danger_err)
    final_id = finalized.danger_ok

    siblings_finalized = _finalize_sibling_drafts(worktree, final_id)
    if siblings_finalized.is_err:
        return Err(siblings_finalized.danger_err)

    committed = _commit_finalize_writes(worktree, final_id)
    if committed.is_err:
        return Err(committed.danger_err)
    return Ok(final_id)


def _finalize_and_close_ticket(
    worktree: Path,
    ticket_id: str,
    *,
    covers_scope: Callable[[Ticket], bool | None] | None = None,
) -> Result[str, LandError]:
    """Finalize a draft id (if `ticket_id` is one) and transition it to
    DONE; returns the ticket's final id."""
    final_id_result = _finalize_draft_id(worktree, ticket_id)
    if final_id_result.is_err:
        return Err(final_id_result.danger_err)
    final_id = final_id_result.danger_ok

    return _close_finalized_ticket(
        worktree, ticket_id, final_id, covers_scope=covers_scope
    )


def _finalize_draft_id(worktree: Path, ticket_id: str) -> Result[str, LandError]:
    """`finalize_draft` if `ticket_id` is a draft id; else `ticket_id`
    unchanged."""
    from frob.tickets import finalize_draft

    if not is_draft_id(ticket_id):
        return Ok(ticket_id)
    finalized = finalize_draft(worktree, ticket_id)
    if finalized.is_err:
        _log.error(
            "land: %s draft finalize failed after merge landed in the "
            "worktree only (main untouched) -- inspect %s, retry "
            "`frob ticket land %s --worktree %s`, or "
            "`git -C %s reset --hard HEAD~1` to undo the merge commit",
            ticket_id,
            worktree,
            ticket_id,
            worktree,
            worktree,
        )
        return Err(LandError.GitFailed)
    return Ok(finalized.danger_ok)


# frob:ticket T-0637
# frob:tests tests/test_ticket_land.py::TestStandaloneSiblingDraftSurvivesLand.test_sibling_draft_ticket_finalized_and_lands_alongside  # noqa: E501
def _finalize_sibling_drafts(
    worktree: Path, landed_final_id: str
) -> Result[tuple[str, ...], LandError]:
    """Finalize every OTHER draft ticket (T-draft-...) still in `worktree`'s
    active ledger after the ticket actually being landed has already been
    finalized (T-0637).

    A worktree can accumulate STANDALONE sibling draft tickets (features/
    bugs filed mid-session via `frob ticket new` off the default branch,
    T-0162 mints a draft id there since final sequential ids are only ever
    minted against the default branch) that have nothing to do with the
    ticket actually being landed. Left unfinalized, a draft id block would
    either land verbatim onto main (violating the T-0162 invariant that a
    T-draft-<hex> id must never persist on the default branch) or -- before
    T-0637's `_carry_forward_new_worktree_tickets` fix -- get silently
    dropped outright by the ledger splice, the real field incident this
    closes (T-0575's own T-draft-3d5f6965 sibling block, and again two
    drafts filed in T-0576's worktree). Every remaining draft ticket is
    finalized here (via `finalize_draft`, i.e. `renumber_one` against the
    worktree's CURRENT merged view, same primitive `_finalize_draft_id`
    uses for the landing ticket itself) so the later ledger splice onto
    main carries a real sequential id, not a draft one.

    Returns the tuple of newly-finalized ids (old draft ids resolved to
    their final T-#### form), for logging/observability; the caller does
    not need to thread these through further -- once finalized, each
    sibling's fresh section is picked up by `_carry_forward_new_worktree_
    tickets` at squash-splice time the same way any other new-to-main
    ticket is."""
    from frob.tickets import finalize_draft, load_all

    loaded = load_all(worktree)
    if loaded.is_err:
        _log.error(
            "land: could not load %s's active ledger to finalize sibling draft tickets",
            worktree,
        )
        return Err(LandError.GitFailed)
    draft_ids = sorted(
        tid for tid in loaded.danger_ok if is_draft_id(tid) and tid != landed_final_id
    )
    finalized_ids: list[str] = []
    for draft_id in draft_ids:
        result = finalize_draft(worktree, draft_id)
        if result.is_err:
            _log.error(
                "land: sibling draft %s finalize failed (%s) after %s "
                "already finalized -- inspect %s and retry",
                draft_id,
                result.danger_err,
                landed_final_id,
                worktree,
            )
            return Err(LandError.GitFailed)
        finalized_ids.append(result.danger_ok)
        _log.info(
            "land: finalized sibling draft %s -> %s (alongside %s)",
            draft_id,
            result.danger_ok,
            landed_final_id,
        )
    return Ok(tuple(finalized_ids))


def _close_finalized_ticket(
    worktree: Path,
    ticket_id: str,
    final_id: str,
    *,
    covers_scope: Callable[[Ticket], bool | None] | None = None,
) -> Result[str, LandError]:
    """Transition `final_id` to DONE. `covers_scope`, if supplied, is a
    callable invoked with the just-finalized `Ticket` (loaded fresh here,
    post-finalize) -- see `land`'s docstring for why this is lazy."""
    from frob.tickets import _load_one, transition

    resolved_covers_scope: bool | None = None
    if covers_scope is not None:
        loaded = _load_one(worktree, final_id)
        if loaded.is_err:
            _log.error(
                "land: %s not found post-finalize in %s -- cannot compute covers_scope",
                final_id,
                worktree,
            )
            return Err(LandError.NotFound)
        resolved_covers_scope = covers_scope(loaded.danger_ok)

    closed = transition(
        worktree, final_id, TicketState.DONE, covers_scope=resolved_covers_scope
    )
    if closed.is_err:
        _log.error(
            "land: %s close failed (%s) after the merge already landed in "
            "the worktree (main untouched) -- fix evidence/Done report in "
            "%s and retry `frob ticket land %s --worktree %s`, or "
            "`git -C %s reset --hard HEAD~1` to undo the merge commit first",
            final_id,
            closed.danger_err,
            worktree,
            ticket_id,
            worktree,
            worktree,
        )
        return Err(LandError.CloseFailed)
    return Ok(final_id)


# finalize_draft (renumber_one) and transition/close both write directly to
# the worktree's working tree, UNCOMMITTED -- the squash-apply below reads
# from the branch's last COMMIT, which predates these writes. Left
# uncommitted, the finalize rewrite of every frob:ticket <draft-id>
# reference in code (not just the ledger) would never reach main, and the
# worktree would be left dirty after a successful land (reviewer repro,
# T-0176). Commit them now so the squash-apply below sees everything, and
# the worktree ends up clean.
def _commit_finalize_writes(worktree: Path, final_id: str) -> Result[None, LandError]:
    """Commit any working-tree changes finalize/close made, if any."""
    finalize_dirty = _porcelain_dirty(worktree)
    if finalize_dirty.is_err:
        return Err(finalize_dirty.danger_err)
    if not finalize_dirty.danger_ok:
        return Ok(None)
    add = run_argv(["git", "-C", str(worktree), "add", "-A"])
    if add.is_err or add.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    finalize_commit = run_argv(
        [
            "git",
            "-C",
            str(worktree),
            "commit",
            "-m",
            f"finalize and close {final_id} for landing",
        ]
    )
    if finalize_commit.is_err or finalize_commit.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(None)


def _check_squash_conflicted(
    root: Path, worktree: Path, ticket: Ticket, branch_name: str
) -> Result[None, LandError]:
    """`Err(SquashConflict)` (unwinding the squash) if any IN-SCOPE file
    besides tickets.md is still conflicted after the squash merge; any
    OUT-OF-SCOPE conflict is auto-resolved by taking main's side first
    (T-0479) -- main is `ours` here (root's checked-out branch, with the
    worktree's finalized branch squash-merged in as `theirs`)."""
    resolved = _auto_resolve_out_of_scope_conflicts(root, ticket, keep="ours")
    if resolved.is_err:
        run_argv(["git", "-C", str(root), "reset", "--hard"])
        run_argv(["git", "-C", str(root), "clean", "-fd"])
        return Err(resolved.danger_err)
    remaining = resolved.danger_ok
    if remaining:
        run_argv(["git", "-C", str(root), "reset", "--hard"])
        run_argv(["git", "-C", str(root), "clean", "-fd"])
        _log.error(
            "land: %s squash-apply onto %s conflicts in scoped file(s): %s "
            "-- resolve manually (cd %s && git merge --squash %s), commit, "
            "then retry `frob ticket land %s --worktree %s`",
            ticket.id,
            root,
            sorted(remaining),
            root,
            branch_name,
            ticket.id,
            worktree,
        )
        return Err(LandError.SquashConflict)
    return Ok(None)


def _squash_and_splice_ledger(
    root: Path, worktree: Path, ticket: Ticket, final_id: str, branch_name: str
) -> Result[None, LandError]:
    """`git merge --squash --no-commit` the worktree's finalized `branch_name`
    onto `root`, then splice tickets.md; unwinds the squash on any
    conflict outside `ticket.scope` (or a true in-scope conflict), or a
    splice failure."""
    root_pre_text = _read_ledger_text_or_empty(root)

    squash = run_argv(
        ["git", "-C", str(root), "merge", "--squash", "--no-commit", branch_name]
    )
    if squash.is_err:
        return Err(LandError.GitFailed)

    conflict_check = _check_squash_conflicted(root, worktree, ticket, branch_name)
    # (ticket-scoped; final_id is used only for the ledger splice below)
    if conflict_check.is_err:
        return Err(conflict_check.danger_err)

    worktree_final_text = ledger_path(worktree).read_text(encoding="utf-8")
    # T-0479: base on root's CURRENT tickets.md, overlay only `final_id`'s
    # own block from the worktree's finalized copy -- see the analogous
    # comment in `_merge_main_into_worktree`. This is the final splice that
    # actually lands on main, so it is the last line of defense against
    # sibling-ticket resurrection even if something upstream missed it.
    spliced = _splice_and_stage(
        root,
        root_pre_text,
        worktree_final_text,
        archived_ids=_archived_ids(root),
        ticket_id=final_id,
    )
    if spliced.is_err:
        run_argv(["git", "-C", str(root), "reset", "--hard"])
        run_argv(["git", "-C", str(root), "clean", "-fd"])
        return Err(spliced.danger_err)
    return Ok(None)


# frob:ticket T-0463
def _worktree_full_changeset(
    worktree: Path, main_branch_name: str
) -> Result[frozenset[str], LandError]:
    """The COMPLETE set of paths `worktree`'s finalized branch changes
    relative to `main_branch_name`: tracked edits, untracked new files, AND
    deletions, all in one git-native call.

    `land()`'s wip-commit step (`git add -A`) has already turned every
    untracked new file and every deletion into a tracked change on the
    branch by the time this runs, so a plain `git diff --name-only
    <main>...HEAD` walks the merge-base and reports the true full
    changeset -- unlike a hand `git diff HEAD` / patch-based land, which
    only ever sees tracked deltas against the CURRENT commit and silently
    omits anything that was untracked (T-0463: the root cause of the
    T-0448 `docs/modules/render.md` loss, where a surgical git-diff-patch
    land dropped an untracked file with no error)."""
    diff = run_argv(
        [
            "git",
            "-C",
            str(worktree),
            "diff",
            "--name-only",
            f"{main_branch_name}...HEAD",
        ]
    )
    if diff.is_err or diff.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(
        frozenset(
            line.strip() for line in diff.danger_ok.stdout.splitlines() if line.strip()
        )
    )


# frob:ticket T-0463
def _staged_files(root: Path) -> Result[frozenset[str], LandError]:
    """The paths currently staged in `root`'s index relative to `HEAD`
    (`git diff --cached --name-only`) -- used to assert the squash-apply
    actually staged everything the worktree changed BEFORE the landing
    commit is made, so an incomplete land aborts loudly instead of
    committing a silently-partial changeset."""
    diff = run_argv(["git", "-C", str(root), "diff", "--cached", "--name-only"])
    if diff.is_err or diff.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(
        frozenset(
            line.strip() for line in diff.danger_ok.stdout.splitlines() if line.strip()
        )
    )


# frob:ticket T-0463
def _assert_land_complete(
    root: Path, worktree: Path, ticket_id: str, main_branch_name: str
) -> Result[frozenset[str], LandError]:
    """Post-squash, pre-commit completeness assertion (T-0463): the set of
    paths staged in `root`'s index must be a SUPERSET of everything the
    worktree changed relative to `main_branch_name` (tracked edits,
    untracked new files, deletions). If any worktree-changed file is
    missing from staging, the squash is unwound (`reset --hard`, `clean
    -fd`) and this returns `Err(IncompleteLand)` with the exact missing
    paths logged -- the land never commits a silently-partial changeset.
    Returns the worktree's full changeset on success (for the report)."""
    expected = _worktree_full_changeset(worktree, main_branch_name)
    if expected.is_err:
        run_argv(["git", "-C", str(root), "reset", "--hard"])
        run_argv(["git", "-C", str(root), "clean", "-fd"])
        return Err(expected.danger_err)

    staged = _staged_files(root)
    if staged.is_err:
        run_argv(["git", "-C", str(root), "reset", "--hard"])
        run_argv(["git", "-C", str(root), "clean", "-fd"])
        return Err(staged.danger_err)

    missing = expected.danger_ok - staged.danger_ok
    if missing:
        run_argv(["git", "-C", str(root), "reset", "--hard"])
        run_argv(["git", "-C", str(root), "clean", "-fd"])
        _log.error(
            "land: %s refused -- the staged squash-apply onto %s is missing "
            "file(s) the worktree changed: %s. This is the T-0463 "
            "completeness gap (a stale git-diff/patch land silently drops "
            "untracked or deleted files) -- inspect `git -C %s status` and "
            "`git -C %s diff --name-only %s...HEAD`, then retry "
            "`frob ticket land %s --worktree %s`",
            ticket_id,
            root,
            sorted(missing),
            worktree,
            worktree,
            main_branch_name,
            ticket_id,
            worktree,
        )
        return Err(LandError.IncompleteLand)

    return Ok(expected.danger_ok)


def _land_commit_details(root: Path) -> tuple[str | None, tuple[str, ...]]:
    """The just-made HEAD commit's sha and changed-file list, best-effort
    (`None`/`()` if the git calls fail)."""
    sha = run_argv(["git", "-C", str(root), "rev-parse", "HEAD"])
    sha_str = (
        sha.danger_ok.stdout.strip()
        if sha.is_ok and sha.danger_ok.returncode == 0
        else None
    )

    stat = run_argv(
        [
            "git",
            "-C",
            str(root),
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "HEAD",
        ]
    )
    files = (
        tuple(
            line.strip() for line in stat.danger_ok.stdout.splitlines() if line.strip()
        )
        if stat.is_ok and stat.danger_ok.returncode == 0
        else ()
    )
    return sha_str, files


def _commit_squash_apply(
    root: Path, ticket: Ticket, final_id: str
) -> Result[None, LandError]:
    """Commit the staged squash-apply with a conventional-commit message."""
    commit = run_argv(
        ["git", "-C", str(root), "commit", "-m", _commit_message(ticket, final_id)]
    )
    if commit.is_err or commit.danger_ok.returncode != 0:
        _log.error(
            "land: %s squash-apply staged onto %s but the final commit "
            "failed -- inspect `git -C %s status`, commit manually with a "
            "conventional-commit message, or `git -C %s reset --hard` to "
            "unwind the staged squash",
            final_id,
            root,
            root,
            root,
        )
        return Err(LandError.CommitFailed)
    return Ok(None)


# frob:ticket T-0248
def _warn_if_native_stale(root: Path, final_id: str) -> None:
    """LOUD, non-blocking log warning if `root`'s just-squashed source tree
    now outpaces its own built native extension(s) (T-0248): the incident
    class from T-0166's review, where a landed `strata-core/**` grammar
    change left main's built `strata_core` behind and `frob check` silently
    ran the OLD grammar until a human noticed a confusing SYS004. Fires
    regardless of whether a `rebuild_natives` callback is also supplied --
    a rebuild that runs but is not this warning's business to suppress, and
    a `rebuild_natives=None` caller still gets the loud heads-up either way."""
    from frob.strata._native_staleness import stale_native_warning

    warning = stale_native_warning(root)
    if warning is not None:
        _log.warning("land: %s -- %s", final_id, warning)


# frob:ticket T-0338
_NATIVE_SOURCE_PREFIXES = ("frob-core/", "strata-core/")


def _touches_native_source(changeset: frozenset[str]) -> bool:
    """Whether any path in `changeset` falls under a native-extension source
    tree (T-0338) -- the trigger condition for `rebuild_natives`: a landed
    change that never touched frob-core/strata-core has nothing stale to
    rebuild, so the (potentially slow, minutes-long cargo) rebuild is only
    ever invoked when it can actually matter."""
    return any(path.startswith(_NATIVE_SOURCE_PREFIXES) for path in changeset)


# frob:ticket T-0338
def _apply_release_bump(
    root: Path,
    ticket: Ticket,
    final_id: str,
    bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]] | None,
) -> Result[str | None, LandError]:
    """Invoke `bump_version(root, ticket, final_id)` if supplied, unwinding
    the staged squash (`reset --hard`, `clean -fd`) on failure (T-0338).
    `bump_version=None` (the library default) is a no-op returning
    `Ok(None)` -- see `land`'s docstring for why this is a caller-supplied
    callback rather than computed here."""
    if bump_version is None:
        return Ok(None)
    bumped = bump_version(root, ticket, final_id)
    if bumped.is_err:
        _log.error(
            "land: %s REL001 version-bump callback failed (%s) -- unwinding "
            "the staged squash; bump pyproject.toml/CHANGELOG.md by hand "
            "(`frob release stamp` once fixed) and retry",
            final_id,
            bumped.danger_err,
        )
        run_argv(["git", "-C", str(root), "reset", "--hard"])
        run_argv(["git", "-C", str(root), "clean", "-fd"])
        return Err(bumped.danger_err)
    if bumped.danger_ok is not None:
        _log.info(
            "land: %s REL001 version bump applied and staged: -> %s",
            final_id,
            bumped.danger_ok,
        )
    return bumped


# frob:ticket T-0338
def _maybe_rebuild_natives(
    root: Path,
    final_id: str,
    changeset: frozenset[str],
    rebuild_natives: Callable[[Path], bool] | None,
) -> bool:
    """Invoke `rebuild_natives(root)` when `changeset` touches a native
    source tree (T-0338); best-effort -- a `False`/exception-free failure
    is logged but never unwinds or blocks the land (the T-0248 stale-native
    warning already covers the "you must rebuild before trusting checks"
    heads-up; this is the "land tried to do it for you" upgrade, not a new
    hard gate). `rebuild_natives=None` (the library default) or a changeset
    that never touches frob-core/strata-core is a no-op returning `False`."""
    if rebuild_natives is None or not _touches_native_source(changeset):
        return False
    rebuilt = rebuild_natives(root)
    if rebuilt:
        _log.info("land: %s native extension(s) rebuilt after landing", final_id)
    else:
        _log.warning(
            "land: %s native source changed but the rebuild callback "
            "reported failure -- run `make core` manually before trusting "
            "`frob check`/`frob test` against %s",
            final_id,
            root,
        )
    return rebuilt


def _land_squash_apply(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    ticket_id: str,
    final_id: str,
    wip_committed: bool,
    did_merge: bool,
    main_branch_name: str,
    *,
    bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]]
    | None = None,
    rebuild_natives: Callable[[Path], bool] | None = None,
) -> Result[LandReport, LandError]:
    """Squash-apply the worktree's finalized branch onto `root`, splice
    tickets.md, apply an optional REL001 version bump (T-0338), assert
    completeness (T-0463) BEFORE committing, commit, trigger an optional
    native rebuild, and build the final `LandReport`."""
    branch = current_branch(worktree)
    if branch.is_err:
        return Err(LandError.GitFailed)
    branch_name = branch.danger_ok

    squashed = _squash_and_splice_ledger(root, worktree, ticket, final_id, branch_name)
    if squashed.is_err:
        return Err(squashed.danger_err)

    bumped = _apply_release_bump(root, ticket, final_id, bump_version)
    if bumped.is_err:
        return Err(bumped.danger_err)
    release_bumped_to = bumped.danger_ok

    completeness = _assert_land_complete(root, worktree, ticket_id, main_branch_name)
    if completeness.is_err:
        return Err(completeness.danger_err)
    worktree_changeset = completeness.danger_ok

    _warn_if_native_stale(root, final_id)
    natives_rebuilt = _maybe_rebuild_natives(
        root, final_id, worktree_changeset, rebuild_natives
    )

    committed = _commit_squash_apply(root, ticket, final_id)
    if committed.is_err:
        return Err(committed.danger_err)

    sha_str, files = _land_commit_details(root)
    _log.info("land: %s landed as %s onto %s at %s", ticket_id, final_id, root, sha_str)
    return Ok(
        LandReport(
            ticket_id=ticket_id,
            final_id=final_id,
            dry_run=False,
            wip_committed=wip_committed,
            merged_main_into_worktree=did_merge,
            ledger_spliced=True,
            unowned_deletions=(),
            commit_sha=sha_str,
            files_changed=files,
            worktree_changeset=tuple(sorted(worktree_changeset)),
            release_bumped_to=release_bumped_to,
            natives_rebuilt=natives_rebuilt,
        )
    )
