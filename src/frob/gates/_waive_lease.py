"""frob.gates._waive_lease -- `active_ticket`/`ticket_lease_pin`, the
`--ticket` resolution and cross-worktree lease-pin helpers that ride
along in `frob.gates._waive` (T-1081, clearing that module's ARCH102
finding -- this pair has nothing to do with waiver matching at all; it
happened to travel with the waiver family in T-1072's original tier-1
extraction and is its own cohesive cluster).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from typani import Err, Ok
from typani.option import Nothing, Option, Some
from typani.result import Result

if TYPE_CHECKING:
    from frob.tickets._leases import LeaseError

from frob.gitio import current_branch
from frob.logging import get_logger

_log = get_logger(__name__)


_BRANCH_TICKET_RE = re.compile(r"^(T-\d{4})-")


# frob:doc docs/modules/gates.md#public-api
def active_ticket(root: Path, explicit: str | None) -> Option[str]:
    """`--ticket` wins; else the branch name matching `^(T-\\d{4})-`; else Nothing."""
    if explicit:
        _log.debug("active_ticket: explicit=%s", explicit)
        return Some(explicit)
    branch_result = current_branch(root)
    if branch_result.is_err:
        _log.debug("active_ticket: no branch context")
        return Nothing()
    match = _BRANCH_TICKET_RE.match(branch_result.danger_ok)
    if match is None:
        _log.debug(
            "active_ticket: branch %r has no ticket prefix", branch_result.danger_ok
        )
        return Nothing()
    _log.debug("active_ticket: branch-derived %s", match.group(1))
    return Some(match.group(1))


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0787
# frob:ticket T-1556
# frob:tests tests/test_tickets_leases.py::TestTicketLeasePin.test_no_lease_mechanism_engaged_passes_through kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestTicketLeasePin.test_pinned_lease_for_this_worktree_passes kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestTicketLeasePin.test_lease_absent_for_this_worktree_refuses kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestTicketLeasePin.test_lease_recorded_elsewhere_refuses kind="unit"  # noqa: E501
# frob:tests \
# tests/test_tickets_leases.py::TestTicketLeasePin.test_mutating_false_skips_the_pin_ch\
# eck_entirely
def ticket_lease_pin(
    root: Path, ticket_id: str, *, mutating: bool = True
) -> Result[None, LeaseError]:
    """Validate `ticket_id`'s cross-worktree lease pins to `root` (T-0787,
    promoting T-0766's `resolve_lease` primitive into the live `--ticket`
    resolution path -- previously nothing in `frob check` consulted it at
    all, a reviewer-flagged hard dependency: the T-0695 stale/cross-worktree
    lease-resolution guard prevented nothing until something called it).

    `Ok(None)` both when the lease genuinely pins to `root`, AND when the
    cross-worktree lease mechanism has never been engaged for this repo at
    all: no shared git common dir (a non-git fixture, or a "plain" repo
    with no git worktree context), or a leases directory that has never
    been created because no ticket has ever been `frob ticket start`ed
    anywhere in this repo. Those are the no-lease paths T-0787 must leave
    working exactly as before -- non-agent/manual `--ticket` invocations of
    a repo that never opted into the lease side-channel at all.

    `Err(LeaseError.NoLeaseForTicket | LeaseError.LeaseWorktreeMismatch)`
    once the mechanism IS engaged elsewhere in this repo (the leases
    directory exists) but `ticket_id` itself has no lease recorded for
    `root` specifically -- absent entirely, or recorded for a different
    worktree. The caller (`frob check`'s CLI entry point) turns either into
    a loud refusal naming `frob ticket start <ticket_id>`, closing the
    T-0695 hole `resolve_lease` was built to fix but nothing invoked.

    T-1556: `mutating=False` skips the pin check entirely, always returning
    `Ok(None)` -- the lease exists to protect a worktree's OWN state
    (baseline/coverage stamps, gate-cache writes) from a concurrent
    cross-worktree collision; a genuinely READ-ONLY `--ticket` invocation
    (no `--stamp-baseline`/`--stamp-coverage`, nothing else that writes)
    touches none of that state, so there is nothing for the lease to
    protect and no reason to refuse it. Reviewers repeatedly could not
    re-verify a ticket's gate claims with `frob check --ticket` for
    exactly this reason -- the pin check fired even for a plain read.
    Defaults to `True` (the pre-T-1556 behavior) so every existing caller
    is unaffected until it explicitly opts in; wiring an actual `--ticket`
    invocation's mutating-ness into this parameter is `frob.app.
    check_runner`'s job (`_refuse_ticket_lease_mismatch`), outside this
    file's own declared scope -- see this ticket's Done report for the
    follow-up."""
    if not mutating:
        _log.debug(
            "ticket_lease_pin: mutating=False, skipping pin check for %s "
            "(read-only invocation, nothing leased state could collide "
            "with)",
            ticket_id,
        )
        return Ok(None)
    from frob.tickets._leases import leases_dir, resolve_lease

    leases_root_result = leases_dir(root)
    if leases_root_result.is_err:
        _log.debug(
            "ticket_lease_pin: no shared git common dir under %s; lease "
            "mechanism not engaged, skipping pin check for %s",
            root,
            ticket_id,
        )
        return Ok(None)
    leases_root = leases_root_result.danger_ok
    if not leases_root.is_dir():
        _log.debug(
            "ticket_lease_pin: %s never created (no ticket ever started in "
            "this repo); skipping pin check for %s",
            leases_root,
            ticket_id,
        )
        return Ok(None)
    lease_result = resolve_lease(root, ticket_id, root)
    if lease_result.is_err:
        return Err(lease_result.danger_err)
    return Ok(None)
