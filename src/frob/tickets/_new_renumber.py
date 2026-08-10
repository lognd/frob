"""
frob.tickets._new_renumber -- ticket id allocation, `new_ticket`, and the whole-tree
`renumber`/`renumber_one` id-rewrite family
(T-1103 split residue of frob.tickets.__init__: carved out verbatim with its
T-0102/T-0140/T-0162/T-0398/T-0458/T-0577/T-0633/T-0889/T-1090 directives intact).

T-1103: `renumber_one` is externally monkeypatched at the `frob.tickets` package
attribute by tests exercising `frob.app.ticket_runner`'s CLI dispatch.

T-1192: the `finalize_draft`/`finalize_draft_for_land` provisional-draft-id
finalization pair (LARGE001 residue: this module alone was 847 lines) moved
to `frob.tickets._draft_finalize`, which imports `_next_ticket_id` back from
here -- `finalize_draft`/`finalize_draft_for_land` still re-import
`renumber_one` from the PACKAGE at call time (rather than this module's own
name), preserving the same package-level-monkeypatch indirection T-1103
established, now just from a different caller module.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.gitio import repo_root
from frob.logging import get_logger
from frob.tickets._archive import _load_merged
from frob.tickets._leases import is_lease_ttl_expired, read_all_leases, rename_lease
from frob.tickets._models import (
    RenumberReport,
    Ticket,
    TicketError,
    TicketKind,
    TicketSpec,
    TicketState,
)
from frob.tickets._provisional import mint_draft_id, on_default_branch
from frob.tickets._store import (
    _store_mode,
    archive_path,
    atomic_write,
    ledger_digest,
    ledger_digest_map,
    ledger_lock,
    ledger_path,
    load_all,
    load_archive,
    sanitize_narrative_for_ledger,
    write_all,
    write_archive,
    write_ticket,
)
from frob.tickets._worktree_guard import enforce_worktree_lease

# T-1103: shared "frob.tickets" logger name kept explicit (not get_logger(__name__),
# which would read "frob.tickets._new_renumber") -- several tests filter caplog
# records by the package's own logger name, the same monkeypatch/logger-name hazard
# T-1089's ticket_runner split report documented for this family of split.
_log = get_logger("frob.tickets")


# frob:ticket T-0162
# frob:doc docs/modules/tickets.md#decision-record-t-0162
# frob:waive COV007 reason="the decision-record anchor documents THIS private \
# function's own allocation algorithm/design rationale (why provisional ids vs \
# branch-tip scanning vs content-nonce were compared, T-0162), not the public API \
# surface -- the private symbol genuinely is the documented contract here, not a \
# caller-side summary"
def _allocate_ticket_id(
    root: Path, existing: dict[str, Ticket], merged: dict[str, Ticket]
) -> str:
    """The id a fresh ticket should get: the next sequential T-#### when
    `root` is on the default branch (the merged view is authoritative there),
    otherwise a provisional T-draft-<hex> id -- final sequential ids are only
    ever minted against the default branch's view, so two checkouts filing
    independently structurally cannot converge on the same final id (T-0162:
    three real collisions were all sequential max+1 races across checkouts).
    """
    if not on_default_branch(root):
        draft_id = mint_draft_id()
        while draft_id in existing or draft_id in merged:
            draft_id = mint_draft_id()
        _log.info("tickets: off-default-branch, minted provisional id %s", draft_id)
        return draft_id
    return _next_ticket_id(merged)


def _next_ticket_id(existing: dict[str, Ticket]) -> str:
    """The next sequential `T-####` id above the highest existing ticket number
    in `existing` -- callers must pass the id space they want ids kept clear
    of (T-0140: `new_ticket` passes active+archive merged, not active alone)."""
    max_num = 0
    for tid in existing:
        try:
            max_num = max(max_num, int(tid.split("-", 1)[1]))
        except IndexError:
            continue
        except ValueError:
            continue
        except KeyError:
            continue
        except TypeError:
            continue
        except Exception:
            # A malformed/unexpected ticket id shape must not abort the
            # whole id-space scan over every OTHER ticket (EXHAUST001/
            # EXHAUST002, T-1371) -- same "skip it" posture as the two
            # named branches above.
            continue
    return f"T-{max_num + 1:04d}"


# frob:ticket T-1613
def _ticket_from_spec(
    ticket_id: str, spec: TicketSpec, evidence: tuple[str, ...]
) -> Ticket:
    """Build a fresh QUEUED ticket from `spec`, applying the incident
    template. T-1541: `spec.body` (`ticket new --body-file`) is
    caller-authored free text spliced directly into the ticket's body --
    the same marker-lookalike-corruption class T-1536 defused for the
    Done-report `why` path -- so it is run through
    `sanitize_narrative_for_ledger` here too, before the incident-template
    fallback (an empty/whitespace-only body is unaffected either way)."""
    body = sanitize_narrative_for_ledger(spec.body)
    if spec.kind == TicketKind.INCIDENT and not body.strip():
        body = _INCIDENT_TEMPLATE
    return Ticket(
        id=ticket_id,
        title=spec.title,
        state=TicketState.QUEUED,
        kind=spec.kind,
        origin=spec.origin,
        created=date.today(),
        priority=spec.priority,
        blocked_by=spec.blocked_by,
        parent=spec.parent,
        tier=spec.tier,
        sprint=spec.sprint,
        runs_last=spec.runs_last,
        scope=spec.scope,
        evidence=evidence,
        attachments=(),
        acceptance=spec.acceptance,
        threat=spec.threat,
        component=spec.component,
        labels=spec.labels,
        body=body,
    )


# frob:ticket T-1613
def _warn_if_runs_last_ticket_in_progress(root: Path) -> None:
    """Log a WARNING naming every IN_PROGRESS `runs_last` ticket, if any,
    when filing a fresh ordinary ticket (T-1613): the precondition a
    runs-last ticket started under -- "nothing else is open" -- was true
    the moment it started, but filing new work right now invalidates it
    again, and nothing else in the queue graph would ever say so. Reads
    the queue via `load_queue` (the active-ledger view `doable` itself
    reads from); a load failure degrades to no warning rather than
    blocking `frob ticket new` on a read-side problem unrelated to the
    ticket being filed."""
    from frob.tickets import TicketState
    from frob.tickets._archive import load_queue

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.warning(
            "tickets: could not check for an in-progress runs-last ticket "
            "before filing (%s) -- proceeding without the T-1613 warning",
            queue_result.danger_err,
        )
        return
    running = sorted(
        t.id
        for t in queue_result.danger_ok.tickets.values()
        if t.runs_last and t.state is TicketState.IN_PROGRESS
    )
    if running:
        _log.warning(
            "tickets: filing a new ticket while runs-last ticket(s) %s "
            "are IN_PROGRESS -- the precondition they started under "
            "(nothing else open) is now invalidated; review whether "
            "their conclusions still hold",
            running,
        )


# frob:ticket T-1744
def _find_exact_duplicate(root: Path, spec: TicketSpec) -> Ticket | None:
    """The first currently-active, non-`dropped` ticket whose `title` and
    `scope` EXACTLY match `spec`'s, or `None` if none does (T-1744).

    Deliberately HIGH-PRECISION, not fuzzy: exact string equality on
    `title`, exact set equality on `scope` (order-independent -- two
    tickets declaring the same globs in a different order are still the
    same ticket) -- never a similarity/distance heuristic. This repo
    files near-identical titles for genuinely distinct follow-ups
    constantly (a scope-corrected re-file, a phase-2 continuation); a
    fuzzy matcher would refuse legitimate tickets at creation time,
    which is far more damaging than letting an occasional true duplicate
    through. Measured 2026-08-07: six duplicate tickets (exact title
    AND exact scope, including two triplicates) reached the queue before
    being caught and dropped by hand -- 5% phantom backlog with nothing
    in the tool comparing a new ticket against existing ones.

    `dropped` tickets are excluded: a ticket dropped as obsolete/absorbed
    does not mean the same title+scope can never legitimately be filed
    again later (circumstances change) -- refusing against a dropped
    ticket would itself be a false positive this ticket's own precision
    requirement rules out. Best-effort: an unreadable ledger returns
    `None` (never blocks filing on "cannot verify") -- the DUPLICATE
    class this check exists to catch is strictly worse than an occasional
    unnoticed one, but blocking every `frob ticket new` on a ledger read
    failure would be worse still."""
    from frob.tickets._store import load_all

    loaded = load_all(root)
    if loaded.is_err:
        return None
    spec_scope = frozenset(spec.scope)
    for ticket in loaded.danger_ok.values():
        if ticket.state is TicketState.DROPPED:
            continue
        if ticket.title == spec.title and frozenset(ticket.scope) == spec_scope:
            return ticket
    return None


# frob:ticket T-1744
def _refuse_exact_duplicate(root: Path, spec: TicketSpec) -> Result[None, TicketError]:
    """`new_ticket`'s own duplicate-refusal step, split out to keep that
    function under ARCH001's line threshold: `Err(TicketError.
    DuplicateTicket)` (logged, naming the existing ticket) when
    `_find_exact_duplicate` finds a match, `Ok(None)` otherwise."""
    duplicate = _find_exact_duplicate(root, spec)
    if duplicate is None:
        return Ok(None)
    _log.error(
        "tickets: refusing to file %r -- %s already has this exact title "
        "and this exact scope (drop or reuse %s instead of filing a "
        "duplicate)",
        spec.title,
        duplicate.id,
        duplicate.id,
    )
    return Err(TicketError.DuplicateTicket)


# frob:ticket T-1813
def _validate_new_ticket_spec(
    root: Path, spec: TicketSpec, collected: frozenset[str] | None
) -> Result[tuple[str, ...], TicketError]:
    """`new_ticket`'s pre-write validation gauntlet, split out to keep that
    function under ARCH001's line threshold (T-1813): runs-last warning,
    worktree-lease enforcement, exact-duplicate refusal, evidence schema
    validation, and evidence resolution checking, in that order. Returns
    the validated (and normalized) evidence tuple on success, or the
    first stage's `Err` -- the caller passes this straight through to
    `_ticket_from_spec`."""
    from frob.tickets import _check_evidence_resolution, _validate_evidence_list

    if not spec.runs_last:
        _warn_if_runs_last_ticket_in_progress(root)

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    duplicate_check = _refuse_exact_duplicate(root, spec)
    if duplicate_check.is_err:
        return Err(duplicate_check.danger_err)
    validated = _validate_evidence_list(spec.evidence)
    if validated.is_err:
        return Err(validated.danger_err)
    resolution = _check_evidence_resolution(
        "new_ticket", validated.danger_ok, collected
    )
    if resolution.is_err:
        return Err(resolution.danger_err)
    return Ok(validated.danger_ok)


# frob:ticket T-1813
def _allocate_and_write_new_ticket(
    root: Path, spec: TicketSpec, validated_evidence: tuple[str, ...]
) -> Result[Ticket, TicketError]:
    """`new_ticket`'s id-allocation-and-write step, split out to keep that
    function under ARCH001's line threshold (T-1813). Allocation (read
    the current max id) and the write that claims it MUST happen under
    one held lock -- two processes each reading the pre-write max id and
    then writing, unlocked in between, is exactly the sequential-id race
    that produced T-0465's duplicate T-0427. `write_ticket` re-acquires
    the same lock internally (reentrant, see `ledger_lock`), so this
    outer hold is what actually closes the gap. (T-0458 established this
    invariant.)"""
    with ledger_lock(root):
        ticket_id_result = _allocate_and_check_ticket_id(root)
        if ticket_id_result.is_err:
            return Err(ticket_id_result.danger_err)
        ticket_id = ticket_id_result.danger_ok
        ticket = _ticket_from_spec(ticket_id, spec, validated_evidence)
        write_result = write_ticket(root, ticket)
        if write_result.is_err:
            return Err(write_result.danger_err)
    return Ok(ticket)


# frob:ticket T-1813
# frob:ticket T-1891
def _commit_new_ticket(
    root: Path, ticket: Ticket, no_commit: bool, *, warn_if_dirty: bool = True
) -> None:
    """`new_ticket`'s post-write ledger-commit step, split out to keep
    that function under ARCH001's line threshold (T-1813). A commit
    failure here is logged but never turns a successful ticket creation
    into an `Err` -- the ticket is already durably written by the time
    this runs; degrading to "created, but the ledger is dirty and logged
    as such" is strictly better than losing the created ticket over a
    commit failure.

    T-1891: `warn_if_dirty` (threaded straight from `new_ticket`'s own
    same-named parameter) lets an INTERNAL CALLER that passes `no_commit
    =True` purely to BATCH this write into a real commit it issues
    itself moments later in the SAME operation
    (`frob.app.ticket_runner._new._new`, `frob.app.ticket_runner.
    _rapid_sweep._file_regression_ticket` -- both call `new_ticket(...,
    no_commit=True, warn_if_dirty=False)` and immediately follow with
    their OWN unconditional `commit_ticket_ledger_change` call, which is
    where a real end-user `--no-commit` flag, if any, is actually
    threaded through and warns correctly) suppress the misleading warning
    here. Confirmed live 2026-08-09: a coordinator ran plain `frob ticket
    new` (no `--no-commit` anywhere) and still saw 'left DIRTY by
    --no-commit' from THIS call, even though the ledger was committed for
    real moments later by `_new`'s own outer call -- true about
    dirtiness at this instant, false about the outcome. Left at its
    default `True` for a caller that invokes `new_ticket` DIRECTLY as a
    library function with a genuine `no_commit=True` (no follow-up commit
    of its own) -- that caller's tree really is left dirty, and must
    still be warned (`TestNewTicketProgrammaticAutoCommit.test_no_
    commit_leaves_ledger_dirty_and_warns`, T-1758's own precedent)."""
    from frob.tickets._leases import commit_ticket_ledger_change

    committed = commit_ticket_ledger_change(
        root,
        ticket.id,
        f"chore(tickets): file {ticket.id}",
        no_commit=no_commit,
        warn_if_dirty=warn_if_dirty,
    )
    if committed.is_err:
        _log.error(
            "tickets: %s created but the ledger commit failed (%s) -- "
            "root is now DIRTY and will DirtyMain-block a concurrent "
            "`frob ticket land` until committed by hand",
            ticket.id,
            committed.danger_err,
        )
    _log.info("tickets: created %s", ticket.id)


# frob:ticket T-0102
# frob:ticket T-0140
# frob:ticket T-0398
# frob:ticket T-1613
# frob:doc docs/modules/tickets.md#public-api
# frob:ticket T-1758
# frob:ticket T-1813
# frob:waive AFFECT001 reason="T-1813 only splits new_ticket's existing body into \
# three private helpers (_validate_new_ticket_spec/_allocate_and_write_ \
# new_ticket/_commit_new_ticket) to clear ARCH001 -- no observable behavior, \
# signature, or contract change, so docs/modules/tickets.md#public-api needs no \
# update; that file is also out of this ticket's scope (held by other in-flight agents)"
def new_ticket(
    root: Path,
    spec: TicketSpec,
    collected: frozenset[str] | None = None,
    *,
    no_commit: bool = False,
    warn_if_dirty: bool = True,
) -> Result[Ticket, TicketError]:
    """Allocate the next sequential id and upsert the ticket into the store.

    T-1758: auto-commits the ledger write itself (`commit_ticket_ledger_
    change`) before returning -- moved HERE, to the write boundary, rather
    than left for each caller to remember, because T-1615's uniform
    auto-commit only ever covered the `frob ticket new` CLI DISPATCH path
    (`_auto_commit_ledger_after_dispatch` wraps the dispatch call site,
    not this library function). Every call to `new_ticket` that bypasses
    the CLI -- confirmed at the time of this fix:
    `frob.app.ticket_runner._rapid_sweep._file_regression_ticket`,
    `frob.tickets._mutation_sweep_queue`, `frob.testing._stability`,
    `frob.app.sys_runner`, `frob.fleet` -- inherited the exact silent-
    DirtyMain hazard T-1755 fixed for the FIRST of those, one call site
    at a time, with a bespoke wrapper (`_commit_regression_ticket`) that
    only closed the hole IT called through. This fix closes it for all
    five at once, and for any future caller, with nothing new to
    remember: the guarantee lives at the one place every caller must
    already pass through to create a ticket at all.

    Commits AFTER `ledger_lock` is released (matching the CLI dispatch
    layer's own timing: `_auto_commit_ledger_after_dispatch` runs after
    the verb handler returns, never while it still holds a lock) -- a
    `git commit` does not need this process's in-memory lock held, and
    holding it across a subprocess spawn would serialize unrelated
    concurrent ticket creation against a git call that does not need to
    be inside that critical section.

    `no_commit=True` is `frob ticket new --no-commit`'s existing escape
    hatch (a caller that wants to batch several ledger writes into one
    commit of its own) threaded through unchanged -- same semantics as
    `commit_ticket_ledger_change`'s own `no_commit`: still WARNS loudly
    when it leaves the ledger dirty, never silently. A commit failure
    here is logged (by `commit_ticket_ledger_change` itself) but does
    NOT turn a successful ticket creation into an `Err` -- the ticket is
    already durably written by the time the commit step runs; degrading
    to "created, but the ledger is dirty and logged as such" is strictly
    better than losing the created ticket over a commit failure, the
    same posture `_commit_regression_ticket`'s now-redundant wrapper
    already established for this exact call site.

    T-1891: `warn_if_dirty=False` is the escape hatch for a caller that
    passes `no_commit=True` purely to BATCH this write into a real commit
    IT issues itself moments later in the same operation (`frob.app.
    ticket_runner._new._new`, `frob.app.ticket_runner._rapid_sweep.
    _file_regression_ticket`) -- suppresses only the WARNING above, never
    the underlying skip-the-commit behavior. Left at its default `True`
    for every other caller (a genuine programmatic `no_commit=True` with
    no follow-up commit of its own must still be warned, since its tree
    really is left dirty).

    Any `spec.evidence` entries are schema-validated (validate_evidence)
    before the ticket is ever built, so a malformed entry cannot land via
    `frob ticket new` either (T-0102 companion fix). The id is allocated from
    the max across BOTH the active ledger and the archive (T-0140) -- scanning
    only the active store restarts numbering at T-0001 the moment a queue has
    been archived, colliding with archived ids and making the merged queue
    unloadable (DuplicateId) on the very next `load_queue`. A malformed
    archive fails loudly here too, via the same `_load_merged` path
    `load_queue` uses -- never silently ignored.

    D-08: `spec.evidence` is now ALSO resolution-checked via the same
    `_check_evidence_resolution` `add_evidence` uses, whenever a caller
    supplies `collected` -- previously `new_ticket --evidence` only
    schema-validated, so a bogus id (`tests/ghost.py::test_x`) was stored
    unresolved and surfaced only if/when the ticket later reached DONE and
    `frob check` ran COV003. `collected=None` (default, matching every
    caller before D-08) preserves that schema-only behavior for a context
    with no collector available, but now logs the same explicit UNRESOLVED
    warning `add_evidence` does, so the gap is never silent.

    T-1103: `_validate_evidence_list`/`_check_evidence_resolution` stay
    defined in `frob.tickets` proper (the evidence family) -- imported here
    from the PACKAGE rather than a submodule to avoid a load-time circular
    import (this module is imported BY `frob.tickets.__init__` itself).

    T-1613: filing a fresh ordinary (non-runs-last) ticket while a
    runs-last ticket is IN_PROGRESS logs a loud WARNING before the write
    -- this is the requirement that makes runs-last real rather than
    cosmetic: the failure mode is not starting the runs-last ticket too
    early, it is finishing it and then having new work land that silently
    invalidates its conclusions. Best-effort: a load failure here degrades
    to no warning (never blocks filing), matching this module's existing
    fail-open-on-read posture elsewhere.
    T-1813: the validation gauntlet, the locked allocate-and-write, and
    the post-write commit each moved to their own helper
    (`_validate_new_ticket_spec`/`_allocate_and_write_new_ticket`/
    `_commit_new_ticket`) to keep this function under ARCH001's line
    threshold -- this body is now just the three-step pipeline.
    """
    validation = _validate_new_ticket_spec(root, spec, collected)
    if validation.is_err:
        return Err(validation.danger_err)
    written = _allocate_and_write_new_ticket(root, spec, validation.danger_ok)
    if written.is_err:
        return Err(written.danger_err)
    ticket = written.danger_ok
    _commit_new_ticket(root, ticket, no_commit, warn_if_dirty=warn_if_dirty)
    return Ok(ticket)


def _allocate_and_check_ticket_id(root: Path) -> Result[str, TicketError]:
    """Load the active+archived ticket state and allocate a fresh id,
    erroring on an archive-load failure or an id collision."""
    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    existing = loaded.danger_ok
    merged = _load_merged(root)
    if merged.is_err:
        _log.error("tickets: id allocation aborted, archive unreadable")
        return Err(merged.danger_err)
    ticket_id = _allocate_ticket_id(root, existing, merged.danger_ok)
    if ticket_id in existing:
        _log.error("tickets: id collision allocating %s", ticket_id)
        return Err(TicketError.DuplicateId)
    return Ok(ticket_id)


_INCIDENT_TEMPLATE = (
    "## Summary\n\n"
    "## Timeline\n\n"
    "## Root cause (blameless)\n\n"
    "## Action items\n"
    "<!-- each action item MUST become a ticket -- link them here as T-#### -->\n"
)


def _is_contiguous(ordered: list[Ticket], mapping: dict[str, str]) -> bool:
    """Whether every ticket already carries the id `mapping` would assign it."""
    return all(t.id == mapping[t.id] for t in ordered)


# frob:ticket T-1882
def _refuse_if_other_worktree_holds_live_lease(root: Path) -> Result[None, TicketError]:
    """Refuse a renumber (bulk or single-id) while ANY OTHER worktree holds
    a live, non-TTL-expired lease on ANY ticket (T-1882 incident: a bulk
    renumber rewrote all 273 ticket ids in one shot; had any of those ids
    been leased to a live sibling worktree at the time, every lease file
    naming that id by string would have been silently orphaned -- a lease
    file is keyed by ticket id and nothing re-derives it from content).

    A lease held by THIS SAME worktree is not a conflict -- nothing else
    can be racing itself, and `renumber_one` already migrates its own
    ticket's lease (`rename_lease`, T-1173) after a successful single-id
    rename. TTL-expired leases are excluded (same posture `_scope_add_
    live_lease_conflict`, T-1868, already applies): a lease with no live
    holder behind it in practice is not a real collision, matching
    `read_all_leases`'s own dead-worktree pruning for the liveness half.
    """
    leases = read_all_leases(root)
    if not leases:
        return Ok(None)
    actual = repo_root(root)
    current_path = actual.danger_ok.resolve() if actual.is_ok else None
    foreign = [
        lease
        for lease in leases
        if not is_lease_ttl_expired(lease)
        and (current_path is None or Path(lease.worktree).resolve() != current_path)
    ]
    if not foreign:
        return Ok(None)
    holders = sorted(f"{lease.ticket_id}@{lease.worktree}" for lease in foreign)
    _log.error(
        "tickets: refusing renumber -- %d other worktree lease(s) still live "
        "(%s); renumbering ids out from under them would corrupt every lease "
        "file that references a ticket by id",
        len(foreign),
        ", ".join(holders),
    )
    return Err(TicketError.ScopeLeaseConflict)


# frob:ticket T-1125
def _rewrite_body_prose_references(
    body: str, mapping: dict[str, str]
) -> tuple[str, int]:
    """Rewrite every whole-word PROSE occurrence of a renumbered id in
    `body` to its new id, for every `old != new` pair in `mapping` -- the
    Done-report/description-prose analog of `_apply_renumber`'s structural
    `blocked_by`/`parent` rewrite.

    T-1125: `_apply_renumber` used to rewrite only the structured id/
    blocked_by/parent fields, leaving free-text prose (a Done report citing
    a draft id like "T-1109", or a description referencing a now-renumbered
    ticket) permanently stale after `renumber_one`/`finalize_draft` --
    either a dead-id TICK006 phantom once the draft id no longer resolves,
    or worse (invisible to any gate) a citation of the WRONG real ticket if
    a hand-guessed final id happened to already exist. Four wave-17
    incidents (T-1077/T-1084/T-1095's phantom citations, T-0668's 8-site
    wrong-id citation) motivated this. Skips any pair where `old_id ==
    new_id` (nothing moved) or `old_id` is not even present in `body`
    (the common case -- most tickets' bodies reference nothing that moved),
    so a ticket whose prose mentions no renumbered id is left byte-for-byte
    unchanged."""
    hits = 0
    for old_id, new_id in mapping.items():
        if old_id == new_id or old_id not in body:
            continue
        id_re = re.compile(rf"\b{re.escape(old_id)}\b")
        body, n = id_re.subn(new_id, body)
        hits += n
    return body, hits


def _apply_renumber(
    ordered: list[Ticket], mapping: dict[str, str]
) -> tuple[dict[str, Ticket], int, int]:
    """Rewrite each ticket's id, blocked_by/parent refs, AND body prose
    citations of any renumbered id, via `mapping` (T-1125: body prose used
    to be left stale -- see `_rewrite_body_prose_references`).

    Returns `(new_map, touched, prose_hits)`: `touched` is "tickets touched"
    (id changed OR body prose rewritten), not "ids changed" alone -- a
    ticket whose own id is stable but whose Done-report prose cited a
    SIBLING id that moved must still be persisted, so `_persist_renumber`'s
    write-trigger (built from this count) has to see it as a change too.
    `prose_hits` is the total count of individual prose substitutions made
    across every ticket's body, folded into `RenumberReport.occurrences`
    alongside code-reference hits."""

    def remap(tid: str) -> str:
        return mapping.get(tid, tid)

    new_map: dict[str, Ticket] = {}
    touched = 0
    prose_hits_total = 0
    for ticket in ordered:
        new_id = mapping[ticket.id]
        id_changed = new_id != ticket.id
        new_body, prose_hits = _rewrite_body_prose_references(ticket.body, mapping)
        prose_hits_total += prose_hits
        if id_changed or prose_hits:
            touched += 1
        new_map[new_id] = ticket.model_copy(
            update={
                "id": new_id,
                "blocked_by": tuple(remap(b) for b in ticket.blocked_by),
                "parent": remap(ticket.parent) if ticket.parent else None,
                "body": new_body,
            }
        )
    return new_map, touched, prose_hits_total


# frob:ticket T-1882
def _log_bulk_renumber_preview(mapping: dict[str, str], *, dry_run: bool) -> int:
    """Log the count plus first/last few OLD -> NEW pairs of a bulk
    contiguous-renumber `mapping`, BEFORE any write happens (T-1882
    requirement 1/2: the whole-ledger form must show what it is about to
    do, not just how many). Returns the number of ids that would actually
    change (`old != new`) -- callers use this both for the dry-run report
    and as the real "how many tickets moved" count, so a preview and a
    real run always agree on the number."""
    moved = [(old, new) for old, new in mapping.items() if old != new]
    verb = "would renumber" if dry_run else "about to renumber"
    _log.warning(
        "tickets: bulk renumber -- %s %d ticket id(s) (whole-ledger form, T-1882)",
        verb,
        len(moved),
    )
    # First/last few pairs (T-1882 requirement 1): the two slices never
    # overlap once len(moved) > 10, and for a small mapping the tail slice
    # naturally starts past wherever the head slice ended (Python slicing
    # on a short list just returns fewer, never duplicate, entries).
    shown = moved[:5]
    for old, new in shown:
        _log.warning("tickets: bulk renumber preview: %s -> %s", old, new)
    if len(moved) > 10:
        _log.warning(
            "tickets: bulk renumber preview: ... (%d more) ...", len(moved) - 10
        )
    if len(moved) > 5:
        for old, new in moved[max(5, len(moved) - 5) :]:
            _log.warning("tickets: bulk renumber preview: %s -> %s", old, new)
    return len(moved)


# frob:ticket T-1882
def _renumber_dry_run(root: Path) -> Result[int, TicketError]:
    """`renumber`'s `dry_run=True` path, split out to keep `renumber`
    itself under ARCH001's line threshold (T-1882): computes the same
    contiguous-id mapping a real run would, logs the full preview via
    `_log_bulk_renumber_preview`, and returns the would-be-renumbered
    count -- never takes `ledger_lock`, never writes."""
    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ordered = sorted(loaded.danger_ok.values(), key=lambda t: t.id)
    mapping = {t.id: f"T-{i + 1:04d}" for i, t in enumerate(ordered)}
    if _is_contiguous(ordered, mapping):
        _log.info("tickets: renumber --dry-run -- already contiguous, nothing to do")
        return Ok(0)
    return Ok(_log_bulk_renumber_preview(mapping, dry_run=True))


# frob:doc docs/modules/tickets.md#public-api
# frob:ticket T-0633
# frob:ticket T-0889
# frob:ticket T-1630
# frob:ticket T-1882
# frob:tests tests/test_tickets_ledger_concurrency.py::TestLedgerLockSpansWholesaleOperations.test_concurrent_ledger_lock_acquisition_serializes  # noqa: E501
# frob:tests tests/test_ticket_store_stale_snapshot.py::TestRenumberV2StaleSnapshotGuard.test_renumber_root_refuses_when_a_ticket_changes_under_it  # noqa: E501
# frob:tests \
# tests/test_tickets.py::TestSchemaExtras.test_renumber_dry_run_previews_without_writing
# frob:tests \
# tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease.test_bulk_renumber_refused_by_unmerged_sibling_worktrees_live_lease  # noqa: E501
# frob:tests \
# tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease.test_bulk_renumber_dry_run_still_works_under_a_live_lease  # noqa: E501
def renumber(root: Path, *, dry_run: bool = False) -> Result[int, TicketError]:
    """Reassign ticket ids to a contiguous T-0001.. sequence (ordered by
    current id), rewriting blocked_by/parent references so the queue stays
    consistent. The remedy for sequential-id collisions after a worktree
    merge (T-0012). Returns the number of tickets renumbered.

    T-1882: refuses outright (`ScopeLeaseConflict`) while any OTHER
    worktree holds a live lease (`_refuse_if_other_worktree_holds_live_
    lease`) -- a bulk rewrite renames every id at once, corrupting any
    live lease file that names one by string. `dry_run=True` logs the
    full preview (count plus first/last few OLD -> NEW pairs, `_log_
    bulk_renumber_preview`) and returns the would-be-renumbered count
    WITHOUT taking the ledger lock or writing anything -- the CLI's
    `--dry-run` path (T-1882 requirement 2) and the mandatory preview a
    real (non-dry-run) call also prints before it writes (requirement 1).

    T-0633: `load_all` and the eventual `write_all` are now held under one
    `ledger_lock` span (same fix and rationale as `archive`'s docstring) --
    previously the load ran unlocked, so a concurrent single-ticket write
    landing before this function's own locked `write_all` was silently
    reverted by the stale wholesale rewrite.

    T-1630: the stale-snapshot digest passed to `write_all` is now mode-
    aware, mirroring `renumber_one`'s own v1/v2 split (though this function,
    unlike `renumber_one`, still does the wholesale read-modify-write
    itself in both modes -- only the SNAPSHOT shape changes). Previously
    this always captured `ledger_digest(ledger_path(root))`, a v1 monofile
    digest of a path that does not exist in v2 mode -- `write_all` treats a
    bare `str` digest given in v2 mode as "no check requested" (T-1588), so
    a v2-mode `renumber(root)` had NO stale-snapshot protection at all: a
    sibling process's write between this function's `load_all` and its
    `write_all` was silently clobbered by the wholesale rewrite, the same
    T-0680 shape T-1588 closed for `write_all`/`write_archive`'s own
    primitive. `ledger_digest_map(root)` is the v2-shaped per-ticket digest
    snapshot `write_all` actually compares against in that mode."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    if dry_run:
        # T-1882: the preview-and-return path never takes the ledger lock,
        # never writes, and (deliberately) is NOT gated on the live-lease
        # check below -- a read-only preview cannot corrupt anyone's
        # lease, so it must stay available even while another worktree is
        # live (the whole point of a dry-run is to be safe to run anytime).
        return _renumber_dry_run(root)
    lease_conflict = _refuse_if_other_worktree_holds_live_lease(root)
    if lease_conflict.is_err:
        return Err(lease_conflict.danger_err)
    with ledger_lock(root):
        digest: str | dict[str, str]
        if _store_mode(root) == "v2":
            digest = ledger_digest_map(root)
        else:
            digest = ledger_digest(ledger_path(root))
        loaded = load_all(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ordered = sorted(loaded.danger_ok.values(), key=lambda t: t.id)
        mapping = {t.id: f"T-{i + 1:04d}" for i, t in enumerate(ordered)}
        if _is_contiguous(ordered, mapping):
            _log.info("tickets: renumber -- already contiguous, nothing to do")
            return Ok(0)
        # T-1882 requirement 1: print the preview BEFORE the write happens.
        _log_bulk_renumber_preview(mapping, dry_run=False)
        new_map, renumbered, _prose_hits = _apply_renumber(ordered, mapping)
        result = write_all(root, new_map, expected_digest=digest)
        if result.is_err:
            return Err(result.danger_err)
    _log.info("tickets: renumbered %d ticket(s)", renumbered)
    return Ok(renumbered)


_DIRECTIVE_LINE_RE = re.compile(r"frob:(ticket|waive|todo|tests|invariant|doc)\b")

# T-0577: registry disposition targets (docs/design/registry/*.yaml's
# `disposition: "deferred:<ticket>"` / `"duplicate_of:<ticket>"` values, per
# `frob.registry._models.parse_disposition`'s grammar) are ticket-id
# REFERENCES exactly like a `frob:ticket` directive line, but they live in
# YAML data files, not source comments -- `_DIRECTIVE_LINE_RE` never matched
# them. A draft id finalized at land time used to leave every registry
# yaml's `deferred:T-draft-...` pointing at a now-dead id, silently
# breaking REG003 (deferred-to-missing-ticket) until a human hand-swapped it
# (the real T-0388/compliance.yaml incident this pattern closes). Matched
# independent of `_DIRECTIVE_LINE_RE` so a bare `disposition:
# "deferred:T-draft-xxxx"` line (no `frob:` prefix at all) still rewrites.
_REGISTRY_REF_RE = re.compile(r"(?:deferred|duplicate[_-]of):\S+")


def _rewrite_registry_references(
    text: str, old_id: str, new_id: str
) -> tuple[str, int]:
    """Replace whole-word `old_id` with `new_id` wherever it appears as the
    target of a `deferred:`/`duplicate_of:` registry disposition (T-0577,
    see `_REGISTRY_REF_RE`'s doc) -- never elsewhere, so a ticket id
    mentioned only in registry prose/free text is left alone."""
    id_re = re.compile(rf"\b{re.escape(old_id)}\b")
    hits = 0

    def _sub_ref(match: re.Match[str]) -> str:
        nonlocal hits
        rewritten, n = id_re.subn(new_id, match.group(0))
        hits += n
        return rewritten

    return _REGISTRY_REF_RE.sub(_sub_ref, text), hits


def _tracked_files(root: Path) -> list[Path]:
    """Every git-tracked file under `root`, or (no git repo) every file not
    under a build/vendor/cache directory -- the search space `renumber_one`
    scans for code directive references. Falling back to a filesystem walk
    keeps renumber usable in a non-git fixture/test tree."""
    from frob.excludes import iter_files

    return list(iter_files(root))


def _rewrite_directive_references(
    text: str, old_id: str, new_id: str
) -> tuple[str, int]:
    """Replace whole-word `old_id` with `new_id` on every line that carries a
    `frob:` directive -- never elsewhere in the file (a ticket id mentioned
    in prose/a docstring/an unrelated string is left alone; only directive
    lines are code REFERENCES this command owns rewriting)."""
    id_re = re.compile(rf"\b{re.escape(old_id)}\b")
    lines = text.splitlines(keepends=True)
    hits = 0
    for i, line in enumerate(lines):
        if _DIRECTIVE_LINE_RE.search(line) and id_re.search(line):
            lines[i], n = id_re.subn(new_id, line)
            hits += n
    return "".join(lines), hits


def _scan_code_references(
    root: Path, old_id: str, new_id: str
) -> dict[Path, tuple[str, int]]:
    """Every tracked non-ledger file whose directive lines OR registry
    disposition targets (`_rewrite_registry_references`, T-0577) mention
    `old_id`, mapped to its rewritten text and the number of references
    replaced (both classes combined)."""
    skip_names = {ledger_path(root).name, archive_path(root).name}
    changed: dict[Path, tuple[str, int]] = {}
    for path in _tracked_files(root):
        if path.name in skip_names:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if old_id not in text:
            continue
        try:
            directive_text, directive_hits = _rewrite_directive_references(
                text, old_id, new_id
            )
            rewritten, registry_hits = _rewrite_registry_references(
                directive_text, old_id, new_id
            )
        except Exception:
            # One file's directive/registry text confusing the rewrite
            # helpers must not abort the whole renumber scan over every
            # OTHER tracked file (EXHAUST001/EXHAUST002, T-1371) -- skip
            # just this one, same as the read-failure branch above.
            continue
        hits = directive_hits + registry_hits
        if hits:
            changed[path] = (rewritten, hits)
    return changed


# frob:ticket T-0889
def _load_and_validate_renumber_ids(
    root: Path, old_id: str, new_id: str
) -> Result[
    tuple[dict[str, Ticket], dict[str, Ticket], str | None, str | None], TicketError
]:
    """Load the active+archive ledgers and validate `old_id`/`new_id` are
    renumber-able: not equal, `old_id` present, `new_id` free.

    Also returns each ledger's `ledger_digest` snapshot at load time
    (T-0889), so `_persist_renumber`'s eventual wholesale `write_all`/
    `write_archive` can refuse instead of clobbering if either file changed
    on disk since this load."""
    if old_id == new_id:
        _log.warning("tickets: renumber_one %s -> %s is a no-op id", old_id, new_id)
        return Err(TicketError.InvalidTransition)

    active_digest = ledger_digest(ledger_path(root))
    active_loaded = load_all(root)
    if active_loaded.is_err:
        return Err(active_loaded.danger_err)
    archive_digest = ledger_digest(archive_path(root))
    archived_loaded = load_archive(root)
    if archived_loaded.is_err:
        return Err(archived_loaded.danger_err)
    active_map, archive_map = active_loaded.danger_ok, archived_loaded.danger_ok

    if old_id not in active_map and old_id not in archive_map:
        _log.error("tickets: renumber_one: %s not found", old_id)
        return Err(TicketError.NotFound)
    if new_id in active_map or new_id in archive_map:
        _log.error("tickets: renumber_one: target id %s already exists", new_id)
        return Err(TicketError.DuplicateId)
    return Ok((active_map, archive_map, active_digest, archive_digest))


# frob:ticket T-0889
def _persist_renumber(
    root: Path,
    *,
    new_active_map: dict[str, Ticket],
    active_changed: int,
    new_archive_map: dict[str, Ticket],
    archive_changed: int,
    code_changes: dict[Path, tuple[str, int]],
    active_digest: str | None = None,
    archive_digest: str | None = None,
) -> Result[None, TicketError]:
    """Write back the renumbered active/archive ledgers (if changed) and
    every rewritten code-reference file.

    `active_digest`/`archive_digest` (T-0889) are the `ledger_digest`
    snapshots `_load_and_validate_renumber_ids` took at load time, threaded
    through to `write_all`/`write_archive` as `expected_digest` so a
    wholesale rewrite refuses rather than clobbers if either ledger changed
    on disk since that load."""
    if active_changed:
        write_result = write_all(root, new_active_map, expected_digest=active_digest)
        if write_result.is_err:
            return Err(write_result.danger_err)
    if archive_changed:
        archive_write = write_archive(
            root, new_archive_map, expected_digest=archive_digest
        )
        if archive_write.is_err:
            return Err(archive_write.danger_err)
    for path, (rewritten, _hits) in code_changes.items():
        written = atomic_write(path, rewritten)
        if written.is_err:
            return Err(written.danger_err)
    return Ok(None)


def _apply_renumber_mapping(
    active_map: dict[str, Ticket],
    archive_map: dict[str, Ticket],
    old_id: str,
    new_id: str,
) -> tuple[dict[str, Ticket], int, dict[str, Ticket], int, int]:
    """Build the id-rename mapping (`old_id -> new_id`, every other id
    fixed) and apply it to both the active and archive ticket maps.

    Returns `(new_active_map, active_changed, new_archive_map,
    archive_changed, prose_hits)` -- `prose_hits` (T-1125) is the combined
    count of Done-report/description-prose substitutions across BOTH maps,
    folded into the eventual `RenumberReport.occurrences`."""
    all_ids = set(active_map) | set(archive_map)
    full_mapping = {tid: tid for tid in all_ids}
    full_mapping[old_id] = new_id

    new_active_map, active_changed, active_prose_hits = _apply_renumber(
        list(active_map.values()), full_mapping
    )
    new_archive_map, archive_changed, archive_prose_hits = _apply_renumber(
        list(archive_map.values()), full_mapping
    )
    return (
        new_active_map,
        active_changed,
        new_archive_map,
        archive_changed,
        active_prose_hits + archive_prose_hits,
    )


def _build_renumber_report(
    root: Path,
    old_id: str,
    new_id: str,
    active_changed: int,
    archive_changed: int,
    code_changes: dict[Path, tuple[str, int]],
    dry_run: bool,
    ledger_prose_hits: int = 0,
) -> RenumberReport:
    """Assemble the `RenumberReport` for a rename, from the computed
    ledger-changed flags and code-reference scan results.

    `ledger_prose_hits` (T-1125) folds Done-report/description-prose
    substitutions made directly in tickets.md/tickets-archive.md into
    `occurrences` alongside code-reference hits, so a caller inspecting the
    report sees the full picture of what got rewritten, not just the code
    side."""
    return RenumberReport(
        old_id=old_id,
        new_id=new_id,
        ledger_changed=bool(active_changed or archive_changed),
        files_changed=tuple(sorted(str(p.relative_to(root)) for p in code_changes)),
        occurrences=sum(hits for _text, hits in code_changes.values())
        + ledger_prose_hits,
        dry_run=dry_run,
    )


def _log_renumber_dry_run(old_id: str, new_id: str, report: RenumberReport) -> None:
    """Log the DRY RUN summary line for `renumber_one`."""
    _log.info(
        "tickets: renumber_one DRY RUN %s -> %s: ledger_changed=%s "
        "code_files=%d occurrences=%d",
        old_id,
        new_id,
        report.ledger_changed,
        len(report.files_changed),
        report.occurrences,
    )


# First-class replacement for the hand-run sed that fixed the T-0157
# incident's ~100 stray waiver references -- a single command,
# `--dry-run`-able, that can never miss a reference class the old sed
# invocation didn't happen to cover. Also the rename primitive
# `finalize_draft` (T-0162's provisional-id mechanism) and, later,
# T-0176's `frob ticket land` reuse.
#
# T-1420: the v2-mode git-mv renumber backend (ledger v2 design section 4.1,
# T-1255) moved verbatim to `frob.tickets._renumber_v2` (LARGE001 split);
# `renumber_one` below still dispatches to `renumber_one_v2` there.


# frob:doc docs/modules/tickets.md#public-api
# frob:ticket T-0162
# frob:ticket T-0633
# frob:ticket T-0889
# frob:ticket T-1255
# frob:tests tests/test_tickets_ledger_concurrency.py::TestRenumberOneRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_renumber_one  # noqa: E501
def renumber_one(
    root: Path, old_id: str, new_id: str, *, dry_run: bool = False
) -> Result[RenumberReport, TicketError]:
    """Atomically rewrite ONE ticket's id everywhere: its ledger section
    (active or archive, id + every blocked_by/parent reference across BOTH
    stores), every OTHER ticket's Done-report/description PROSE citation of
    it in tickets.md/tickets-archive.md (T-1125, see
    `_rewrite_body_prose_references`), and every `frob:ticket`/`frob:waive`/
    `frob:todo`/`frob:tests`/`frob:invariant`/`frob:doc` directive line
    across the tracked tree that names it.

    T-0633: the load (`_load_and_validate_renumber_ids`) and the eventual
    persist (`_persist_renumber`, which calls `write_all`/`write_archive`)
    are held under one `ledger_lock` span for a non-dry-run call -- this is
    `finalize_draft`'s rename primitive (T-0162), so the same TOCTOU that
    `archive`/`renumber` had (an unlocked load, then a locked wholesale
    write built from that stale snapshot silently reverting a concurrent
    single-ticket write in between) applied here too, and matters more:
    `finalize_draft` runs at `frob ticket land` time, exactly when a
    concurrent worktree's ledger write is most likely to be in flight.

    T-1255: a v2-mode repo (`_store_mode(root) == "v2"`) dispatches to
    `renumber_one_v2` instead -- design section 4.1's `git mv` + per-ticket-
    file reference rewrite, in place of this function's whole-ledger
    read-modify-write. Checked FIRST, before `enforce_worktree_lease` even
    runs, since `renumber_one_v2` does its own lease check."""
    if _store_mode(root) == "v2":
        # Local import: `_renumber_v2` imports helpers back from this module
        # (`_rewrite_body_prose_references`, `_scan_code_references`,
        # `_log_renumber_dry_run`, `_log_renumber_done`) -- a top-level
        # import here would be circular.
        from frob.tickets._renumber_v2 import renumber_one_v2

        return renumber_one_v2(root, old_id, new_id, dry_run=dry_run)
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    if not dry_run:
        lease_conflict = _refuse_if_other_worktree_holds_live_lease(root)
        if lease_conflict.is_err:
            return Err(lease_conflict.danger_err)
    with ledger_lock(root):
        loaded = _load_and_validate_renumber_ids(root, old_id, new_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        active_map, archive_map, active_digest, archive_digest = loaded.danger_ok
        (
            new_active_map,
            active_changed,
            new_archive_map,
            archive_changed,
            ledger_prose_hits,
        ) = _apply_renumber_mapping(active_map, archive_map, old_id, new_id)
        code_changes = _scan_code_references(root, old_id, new_id)
        report = _build_renumber_report(
            root,
            old_id,
            new_id,
            active_changed,
            archive_changed,
            code_changes,
            dry_run,
            ledger_prose_hits=ledger_prose_hits,
        )
        if dry_run:
            _log_renumber_dry_run(old_id, new_id, report)
            return Ok(report)

        persisted = _persist_renumber(
            root,
            new_active_map=new_active_map,
            active_changed=active_changed,
            new_archive_map=new_archive_map,
            archive_changed=archive_changed,
            code_changes=code_changes,
            active_digest=active_digest,
            archive_digest=archive_digest,
        )
        return _finish_renumber(persisted, old_id, new_id, code_changes, report, root)


def _finish_renumber(
    persisted: Result[None, TicketError],
    old_id: str,
    new_id: str,
    code_changes: dict[Path, tuple[str, int]],
    report: RenumberReport,
    root: Path,
) -> Result[RenumberReport, TicketError]:
    """Propagate a persist failure, else migrate `old_id`'s cross-worktree
    lease (if any) to `new_id` (T-1173), log completion, and return the
    report. The lease rename runs AFTER the ledger persist succeeds --
    never before -- so a persist failure never leaves a lease renamed to
    an id the ledger itself never actually claimed."""
    if persisted.is_err:
        return Err(persisted.danger_err)
    rename_lease(root, old_id, new_id)
    _log_renumber_done(old_id, new_id, code_changes, report)
    return Ok(report)


def _log_renumber_done(
    old_id: str,
    new_id: str,
    code_changes: dict[Path, tuple[str, int]],
    report: RenumberReport,
) -> None:
    """Log the completed-rename summary line for `renumber_one`."""
    _log.info(
        "tickets: renumbered %s -> %s (%d code file(s), %d reference(s) updated)",
        old_id,
        new_id,
        len(code_changes),
        report.occurrences,
    )
