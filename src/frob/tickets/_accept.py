"""frob.tickets._accept -- the acceptance-AMENDMENT mutation family
(T-1422): `amend_acceptance`/`remove_acceptance`, split out following the
same per-family extraction pattern `_scope.py` (T-0455/T-1123) established
for `mutate_scope`.

`frob ticket accept` was previously restricted to APPENDING criteria
(`add_acceptance`, `frob.tickets.__init__`) -- there was no supported way
to correct a mis-specified criterion or drop one that was never valid, so
the available workarounds were hand-editing `tickets.md` (which has
corrupted the ledger for real, taking every gate down) or filing a
successor ticket just to carry the same acceptance forward under a new id.

This module is the accountable replacement, mirroring `mutate_scope`'s
shape exactly: every mutation appends an `AcceptanceAmendmentEntry` to the
ticket's `acceptance_amendments` audit list (never edits or removes a
prior entry), REQUIRES a non-blank `reason`, and is refused outright on a
ticket already in a terminal (DONE/DROPPED) state -- amending after close
is exactly the "quietly move the goalposts after the fact" case this
ticket exists to make impossible."""

from __future__ import annotations

import getpass
from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import (
    AcceptanceAmendmentEntry,
    AcceptanceAmendmentOp,
    Ticket,
    TicketError,
    TicketState,
)
from frob.tickets._store import ledger_lock, write_ticket
from frob.tickets._worktree_guard import enforce_worktree_lease

_log = get_logger("frob.tickets")

# frob:ticket T-1422
_TERMINAL_STATES = frozenset({TicketState.DONE, TicketState.DROPPED})


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to getpass.getuser, a \
# stdlib call the resolver cannot statically bound; the one documented raise path \
# (OSError) is caught below"
def _current_actor() -> str:
    """Best-effort identity for an `acceptance_amendments` audit entry's
    `actor` field (T-1422) -- the OS login name, or `"unknown"` if the
    platform/sandbox refuses to report one (never raises). Duplicated
    one-liner from `_scope._current_actor` rather than imported: importing
    across the two sibling mutation-family modules for a single `getpass`
    call would create a needless load-order coupling between them, the
    same tradeoff `_scope.py` itself already accepts relative to
    `frob.tickets.__init__`."""
    try:
        return getpass.getuser()
    except OSError:
        return "unknown"


# frob:ticket T-1422
# frob:waive DUP001 reason="T-1422: DUP001's rung=r2 template matcher hits this and \
# _validate_amend_mutation against a wide, unrelated pool (gates/invariants.py's \
# _validate_invariant_shape, strata/_elaborate.py's trust/KRB/refine-bind checks, \
# _scope.py's own _validate_scope_request, _evidence.py's _check_cmd_evidence_kind, \
# _land_merge.py's _validate_evidence_kind_consistency) purely on the 'if cond: log; \
# return Err(...)' guard-clause shape every fail-loud validator in this codebase \
# shares -- none of those functions touch acceptance criteria, tickets, or even the \
# same domain; a genuine shared abstraction across a request-shape check this narrow \
# would be less readable than the two lines it replaces, not more"
# frob:waive DUP002 reason="T-1422: same rung=r2 guard-clause-shape false positive as \
# the DUP001 waiver above, this time against its own sibling _validate_amend_mutation \
# -- the two functions validate genuinely different things (request shape vs. \
# ticket-state/index-range) and happen to share the 'if cond: log; return Err' idiom \
# every validator here uses, same as _scope.py's own _validate_scope_request/ \
# _validate_scope_mutation pair (unflagged only because DUP002 is diff-scoped to \
# functions BOTH new in one change, which this ticket's parallel two-function shape \
# triggers)"
def _validate_amend_request(
    index: int | None, reason: str
) -> Result[None, TicketError]:
    """The two request-shape checks `amend_acceptance`/`remove_acceptance`
    both reject before ever touching the ledger: a valid 1-based index,
    and a non-blank `reason` (T-1422, mirrors `_scope._validate_scope_
    request`). T-3908: `index` is 1-based (matching `frob ticket show`'s
    own `[1] ...`/`[2] ...` display and `--accepts`'s T-3837 convention),
    so 0 -- the most likely leftover habit from the old 0-based scheme --
    is refused here, not silently treated as "the first criterion"."""
    if index is None or index < 1:
        _log.error(
            "tickets: acceptance amendment requires a valid 1-based --index "
            "(0 and negative indices are never valid; see `frob ticket show`)"
        )
        return Err(TicketError.AcceptanceAmendIndexOutOfRange)
    if not reason.strip():
        _log.error("tickets: acceptance amendment requires --reason")
        return Err(TicketError.AcceptanceAmendReasonMissing)
    return Ok(None)


# frob:ticket T-1422
# frob:ticket T-3908
def _validate_amend_mutation(
    ticket_id: str, ticket: Ticket, index: int
) -> Result[None, TicketError]:
    """The per-request FAIL-LOUD checks shared by amend and remove
    (T-1422): the ticket must not already be in a terminal state, and
    `index` must actually name a declared acceptance criterion. T-3908:
    `index` is 1-based here, so the valid range is `1..len(acceptance)`
    inclusive -- an index past the end (`index > len(...)`) is refused
    the same way `--accepts` refuses one (T-3837), naming the valid range
    rather than a raw 0-based bracket position."""
    if ticket.state in _TERMINAL_STATES:
        _log.error(
            "tickets: %s cannot amend acceptance -- ticket is already %s "
            "(terminal state)",
            ticket_id,
            ticket.state.value,
        )
        return Err(TicketError.AcceptanceAmendTerminalState)
    if index > len(ticket.acceptance):
        _log.error(
            "tickets: %s cannot amend acceptance -- index %d out of range, "
            "%d criteria declared (valid range: 1..%d)",
            ticket_id,
            index,
            len(ticket.acceptance),
            len(ticket.acceptance),
        )
        return Err(TicketError.AcceptanceAmendIndexOutOfRange)
    return Ok(None)


# frob:ticket T-1422
# frob:ticket T-3908
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_acceptance.py::TestAmendAcceptance.test_amend_replaces_text_and_records_reason  # noqa: E501
# frob:tests tests/test_tickets_acceptance.py::TestAmendAcceptance.test_amend_refuses_on_terminal_ticket  # noqa: E501
def amend_acceptance(
    root: Path,
    ticket_id: str,
    index: int,
    new_text: str,
    *,
    reason: str,
) -> Result[Ticket, TicketError]:
    """Replace `ticket_id`'s acceptance criterion at 1-based `index` with
    `new_text` (T-1422) -- the supported alternative to hand-editing
    `tickets.md` when a criterion was WRONG (mis-specified, e.g. T-1411's
    first criterion, which implemented faithfully would have silenced the
    exact case the rule exists for). The OLD text is always preserved in
    the appended `AcceptanceAmendmentEntry` (never discarded), so the
    ledger keeps a full record of what changed and why -- never a silent
    rewrite. Any evidence already bound to the criterion is carried
    forward unchanged (amending the TEXT does not invalidate a binding a
    reviewer already made; a caller that wants the binding re-verified
    rebinds it via `frob ticket evidence --accepts` as normal).

    T-3908: `index` is 1-based, matching `frob ticket show`'s own display
    and `--accepts`'s T-3837 convention -- `--amend`/`--remove` were left
    0-based when T-3837 moved those two surfaces, which let an operator
    reading the 1-based display pass an index that lands INSIDE the valid
    0-based range and silently amends/removes the WRONG criterion. `index`
    is converted to the internal 0-based list position only at the point
    of use, after `_validate_amend_mutation` has confirmed it is in range;
    the `AcceptanceAmendmentEntry.index` recorded below stays 1-based, so
    `frob ticket show`'s `acceptance_amendments:` block names the same
    position its `acceptance:` block does.

    FAILS LOUDLY (`Err`, no partial write) for: an empty `reason`
    (`AcceptanceAmendReasonMissing`), an out-of-range `index`
    (`AcceptanceAmendIndexOutOfRange`), an empty `new_text`
    (`AcceptanceAmendTextMissing`), or a ticket already DONE/DROPPED
    (`AcceptanceAmendTerminalState`) -- amending acceptance criteria after
    close is the exact "quietly move the goalposts" case this ticket
    exists to make impossible.

    Held under `ledger_lock` end to end (load, validate, write) so this can
    never interleave with a concurrent ledger mutation (T-0458 single-
    writer invariant)."""
    from frob.tickets import _load_ticket_and_queue

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    request_check = _validate_amend_request(index, reason)
    if request_check.is_err:
        return Err(request_check.danger_err)
    if not new_text.strip():
        _log.error("tickets: amend requires non-empty --text")
        return Err(TicketError.AcceptanceAmendTextMissing)

    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok

        mutation_check = _validate_amend_mutation(ticket_id, ticket, index)
        if mutation_check.is_err:
            return Err(mutation_check.danger_err)

        # T-3908: index is 1-based (matching the display/--accepts); the
        # list is 0-based, so convert only at the point of use, after
        # _validate_amend_mutation has already confirmed 1 <= index <=
        # len(acceptance).
        list_index = index - 1
        old_criterion = ticket.acceptance[list_index]
        new_criterion = old_criterion.model_copy(update={"text": new_text.strip()})
        new_acceptance = (
            ticket.acceptance[:list_index]
            + (new_criterion,)
            + ticket.acceptance[list_index + 1 :]
        )
        entry = AcceptanceAmendmentEntry(
            op=AcceptanceAmendmentOp.REPLACE,
            index=index,
            old_text=old_criterion.text,
            new_text=new_criterion.text,
            reason=reason,
            actor=_current_actor(),
            at=date.today(),
        )
        updated = ticket.model_copy(
            update={
                "acceptance": new_acceptance,
                "acceptance_amendments": ticket.acceptance_amendments + (entry,),
            }
        )
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s acceptance[%d] amended (%r -> %r): %s",
        ticket_id,
        index,
        old_criterion.text,
        new_criterion.text,
        reason,
    )
    return Ok(updated)


# frob:ticket T-1422
# frob:ticket T-3908
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_acceptance.py::TestAmendAcceptance.test_remove_drops_criterion_and_records_reason  # noqa: E501
# frob:tests tests/test_tickets_acceptance.py::TestAmendAcceptance.test_remove_refuses_on_terminal_ticket  # noqa: E501
def remove_acceptance(
    root: Path, ticket_id: str, index: int, *, reason: str
) -> Result[Ticket, TicketError]:
    """Drop `ticket_id`'s acceptance criterion at 1-based `index` outright
    (T-1422) -- the supported alternative for a criterion that is
    UNSATISFIABLE by construction (the "0 findings under package X"
    burn-down shape) rather than merely mis-worded. Same validation and
    audit-trail discipline as `amend_acceptance`: a non-blank `reason` is
    required, the removal is refused on a terminal ticket, and the
    removed criterion's text is preserved verbatim in the appended
    `AcceptanceAmendmentEntry` (`new_text=None` marks it as a removal, not
    a replace) so the ledger records exactly what was dropped and why,
    never a silent shrink of the list.

    T-3908: `index` is 1-based, matching `frob ticket show` and
    `--accepts` (see `amend_acceptance`'s docstring for the full
    reasoning) -- this is the DESTRUCTIVE half of that fix: under the old
    0-based convention, an operator reading the 1-based display and
    typing what they saw would drop the WRONG criterion outright, with
    the audit trail recording a reason against a criterion that was never
    the one removed.

    FAILS LOUDLY the same way `amend_acceptance` does; see its docstring
    for the full error list. Held under `ledger_lock` end to end."""
    from frob.tickets import _load_ticket_and_queue

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    request_check = _validate_amend_request(index, reason)
    if request_check.is_err:
        return Err(request_check.danger_err)

    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok

        mutation_check = _validate_amend_mutation(ticket_id, ticket, index)
        if mutation_check.is_err:
            return Err(mutation_check.danger_err)

        # T-3908: see amend_acceptance's identical conversion note above.
        list_index = index - 1
        removed_criterion = ticket.acceptance[list_index]
        new_acceptance = (
            ticket.acceptance[:list_index] + ticket.acceptance[list_index + 1 :]
        )
        entry = AcceptanceAmendmentEntry(
            op=AcceptanceAmendmentOp.REMOVE,
            index=index,
            old_text=removed_criterion.text,
            new_text=None,
            reason=reason,
            actor=_current_actor(),
            at=date.today(),
        )
        updated = ticket.model_copy(
            update={
                "acceptance": new_acceptance,
                "acceptance_amendments": ticket.acceptance_amendments + (entry,),
            }
        )
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s acceptance[%d] removed (%r): %s",
        ticket_id,
        index,
        removed_criterion.text,
        reason,
    )
    return Ok(updated)
