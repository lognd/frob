---
id: T-2425
title: a land finalizes other agents' pending drafts, so epic decomposition blocks
  unrelated lands
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_models.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_finalize.py
  reason: land finalizes only its own drafts, queues/skips-with-notice foreign drafts
    instead of failing the whole land, and names the owner in the refusal message
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/tickets/_models.py
  reason: land finalizes only its own drafts, queues/skips-with-notice foreign drafts
    instead of failing the whole land, and names the owner in the refusal message
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_ticket_land.py
  reason: land finalizes only its own drafts, queues/skips-with-notice foreign drafts
    instead of failing the whole land, and names the owner in the refusal message
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_ticket_land.py::TestForeignOwnedSiblingDraftSkipped::test_land_succeeds_and_skips_the_foreign_draft
- tests/test_ticket_land.py::TestForeignOwnedSiblingDraftSkipped::test_land_still_refuses_a_genuine_scope_conflict_on_its_own_ticket
- tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_no_leases_is_none
- tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_own_worktree_lease_is_not_foreign
- tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_foreign_live_lease_names_the_worktree
- tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_ttl_expired_foreign_lease_is_not_foreign
designated_repro_test: null
acceptance:
- text: Given ten pending drafts created by a different agent's epic decomposition,
    when a land with clean content runs, then it completes rather than failing with
    ScopeLeaseConflict on a draft it does not own.
  evidence:
  - tests/test_ticket_land.py::TestForeignOwnedSiblingDraftSkipped::test_land_succeeds_and_skips_the_foreign_draft
  - tests/test_ticket_land.py::TestForeignOwnedSiblingDraftSkipped::test_land_still_refuses_a_genuine_scope_conflict_on_its_own_ticket
  - tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_no_leases_is_none
  - tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_own_worktree_lease_is_not_foreign
  - tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_foreign_live_lease_names_the_worktree
  - tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_ttl_expired_foreign_lease_is_not_foreign
- text: Given a land whose own ticket has a genuine scope conflict, when it runs,
    then it is still refused, proving conflict detection was not disabled.
  evidence:
  - tests/test_ticket_land.py::TestForeignOwnedSiblingDraftSkipped::test_land_succeeds_and_skips_the_foreign_draft
  - tests/test_ticket_land.py::TestForeignOwnedSiblingDraftSkipped::test_land_still_refuses_a_genuine_scope_conflict_on_its_own_ticket
  - tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_no_leases_is_none
  - tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_own_worktree_lease_is_not_foreign
  - tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_foreign_live_lease_names_the_worktree
  - tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_ttl_expired_foreign_lease_is_not_foreign
- text: Given a land refused over a foreign draft, when it reports, then the message
    names which ticket owns that draft and why the land needed to finalize it.
  evidence:
  - tests/test_ticket_land.py::TestForeignOwnedSiblingDraftSkipped::test_land_succeeds_and_skips_the_foreign_draft
  - tests/test_ticket_land.py::TestForeignOwnedSiblingDraftSkipped::test_land_still_refuses_a_genuine_scope_conflict_on_its_own_ticket
  - tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_no_leases_is_none
  - tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_own_worktree_lease_is_not_foreign
  - tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_foreign_live_lease_names_the_worktree
  - tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_ttl_expired_foreign_lease_is_not_foreign
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-18. Series AA's T-2394 land was refused repeatedly with
`ScopeLeaseConflict` while finalizing `T-2428` -- a draft it
does not own, belonging to an unrelated ticket. The harness flagged it
as a stuck repeated failure after 3 identical attempts. AA's own content
was clean and its branch (`agent/dev-friction`, tip `4dc086933`) was
committed and ready throughout.

ROOT CAUSE: a land finalizes the SHARED pending-draft pool, not just its
own drafts. At the time of the refusal, `tickets/T-draft-*` held TEN
drafts, all created 01:42-01:44 by a DIFFERENT agent decomposing epic
T-2390 into children. So one agent filing tickets blocks another
agent's completely unrelated land, for as long as the decomposition
takes.

Confirmed the drafts are on MAIN, not worktree-local -- every worktree
carries a checkout copy, which is why the failure initially looked like
another worktree "holding" the draft. It is not a worktree lease; it is
shared ledger state that any land will try to finalize.

WHY THIS MATTERS BEYOND ONE BLOCKED LAND. Filing tickets is the single
most common non-code operation in this repo, and epic decomposition
files them in BATCHES. Coupling that to every concurrent land means
throughput drops exactly when planning work is happening, and the
failure surfaces as a confusing conflict naming a ticket id the blocked
agent has never heard of. Two agents already misdiagnosed it as a
worktree lease problem.

It also compounds a known family: land-time draft handling has caused
trouble before (T-0577 splice regression -- drafts dropped and
renumbered during land).

FIX SHAPE (design judgement wanted, not a mechanical patch):
  - A land should finalize only the drafts it OWNS (those it created, or
    those belonging to its own ticket), and leave the rest alone. A
    draft another agent is actively writing is not this land's business.
  - Where finalization of a foreign draft genuinely is required, it must
    QUEUE or skip-with-notice rather than fail the whole land -- an
    unrelated agent's in-progress filing should never be able to fail a
    land whose own content is clean.
  - The refusal message must name WHOSE draft it is and why the land
    cares. "ScopeLeaseConflict on T-2428" sent two agents
    hunting for a worktree lease that did not exist.

POSITIVE CONTROLS:
  - must-still-refuse: a land whose OWN ticket has a genuine scope
    conflict must still be refused (do not solve this by disabling
    conflict detection).
  - must-now-succeed: a land with clean content must complete while
    another agent holds ten unrelated pending drafts -- the exact state
    measured here.