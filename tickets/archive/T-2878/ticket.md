---
id: T-2878
title: close's draft auto-promote sweeps ANOTHER ticket's pending draft, races its
  rightful promotion
state: done
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- tests/unit/test_close_promote_drafts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_never_sweeps_a_draft_it_did_not_claim
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_ignores_an_already_dropped_draft
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_with_no_drafts_is_unchanged
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_reports_and_exits_nonzero_when_a_draft_cannot_be_promoted
designated_repro_test: tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_never_sweeps_a_draft_it_did_not_claim
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: bc439433a8d983ff49b2a9fa99a55e570f7b1500
---
Live-hit during T-2872's land (2026-08-22): `frob ticket close T-2872`
auto-promoted `T-draft-90b2bcf5` -- "Write 36 individual COV007 waivers
(all but the T-2849-blocked _reap.py finding)" -- a draft that had
nothing to do with T-2872 and belonged to another agent's in-flight
COV007 work. My worktree's close promoted it to T-2876; main
independently promoted the SAME draft to T-2873 around the same time
(presumably via that draft's actual owning ticket's own close/land).
The two renames collided as a rename/rename git conflict
(`tickets/T-draft-90b2bcf5/ticket.md renamed to tickets/T-2876/ticket.md
in HEAD and to tickets/T-2873/ticket.md in main`) plus a content
conflict on T-2872's own ticket.md, on `frob ticket land T-2872`.
Recovered by cherry-picking every real T-2872 commit onto fresh main
and dropping the spurious promote commit -- refused to hand-resolve
the renumbering conflict per this repo's documented corruption-risk
guidance on hand-splicing ledger renumbers.

## Why close promotes pending drafts at all (read, not inferred)

T-2738 (`src/frob/app/ticket_runner/_close_cmd.py`,
`_promote_pending_drafts_after_close`) added this specifically because
`frob ticket close` (as opposed to `land`) used to leave a closing
ticket's OWN `T-draft-*` follow-ups stranded forever -- caught live via
T-2718, whose draft `T-draft-cf0b0af7` existed only on a detached
branch and had to be hand-recovered as T-2737. T-2738's own "Required"
section is explicit: "a ticket that filed a draft: the draft is
promoted ... or the close refuses, naming them" -- the stated intent
is scoped to drafts THE CLOSING TICKET FILED.

## The implementation does not honor that scope

`_pending_draft_ids_after_close` (same file) does not filter by
provenance at all -- it loads the WHOLE merged queue (`load_queue`)
and returns every `T-draft-*` id in it that is not yet DONE/DROPPED,
with no check for which ticket created it:

    return sorted(
        tid
        for tid, t in all_tickets.items()
        if is_draft_id(tid) and t.state not in (TicketState.DONE, TicketState.DROPPED)
    )

`_promote_pending_drafts_after_close` then calls `finalize_draft` on
every id that function returns. So ANY ticket's close sweeps in and
finalizes EVERY still-pending draft fleet-wide, not just its own --
directly contradicting T-2738's own stated intent.

Root structural gap: there is no field on `Ticket`/the draft record
that names which ticket FILED a given `T-draft-*` id (checked
`src/frob/tickets/_models.py` -- `parent`/`blocked_by` exist, filing
provenance does not). `_pending_draft_ids_after_close` could not
filter by ownership even if it tried to -- the data it would need
does not exist. This is very likely why the T-2738 implementation
took the "promote everything pending" shortcut: enforcing the stated
scope needs a new field, not just a filter predicate.

## Is this the documented stale-merge-base-view allocator race?

No -- verified by reading `finalize_draft`/`_next_ticket_id_shared`
(`src/frob/tickets/_new_renumber.py`, T-2122). The id allocator itself
worked CORRECTLY here: it minted two DISTINCT ids (T-2876, T-2873) via
the shared `<git-common-dir>/frob-ticket-id-counter` file, flocked, so
no id collision occurred -- the documented "renumbering reruns the
broken allocation" class (one ticket consuming 3 ids from a stale
per-checkout view) is about two callers computing the SAME id for
DIFFERENT drafts. This is the opposite shape: two independent,
un-coordinated callers each legitimately finalizing the SAME draft id
into two DIFFERENT final tickets, because nothing stops a second
caller from finalizing a draft another caller is already in the
process of finalizing (or already promoted, in a tree this caller's
snapshot has not observed yet). This is a NEW race class: unscoped,
unsynchronized DUPLICATE PROMOTION of one draft, not an id-uniqueness
defect.

## Positive controls needed (both directions)

Existing tests (`tests/unit/test_close_promote_drafts.py`) only cover:
- close promotes a draft ITS OWN ticket filed (positive, exists)
- close with no drafts is unchanged (negative, exists)
- close reports+exits nonzero on a stranding failure (exists)

MISSING, and the exact shape of this incident: close must NOT promote
a draft that belongs to (was filed by) a DIFFERENT, still-open ticket
-- there is currently no test where a second ticket's own pending
draft exists in the queue while ticket A closes, asserting A's close
leaves it untouched.

## Scope note

This ticket is investigation + control-gap documentation only, per
explicit instruction not to patch high-blast-radius ledger-allocation
code in the same breath as filing. A real fix needs, at minimum, a
provenance field (which ticket filed a given draft) threaded through
`new_ticket`'s draft-creation path before `_pending_draft_ids_after_close`
can filter correctly -- that is schema/migration work touching ticket
creation broadly, not a narrow `_close_cmd.py` patch, and deserves its
own scoped ticket and design pass rather than a rushed change here.

frob:no-behavior-change reason="This ticket only records an investigation (root cause read from source, control-gap analysis, race classification) with no code change -- there is no behavior difference for a designated repro test to exercise between the parent commit and this ticket's diff, which touches only this ticket's own ledger entry."