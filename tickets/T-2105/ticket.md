---
id: T-2105
title: Detect a duplicate ticket id after a merge silently resolves two records (T-2092
  half 2)
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land.py
- tests/unit/test_land_duplicate_ticket_id.py
evidence_scope:
- tests/unit/test_land_duplicate_ticket_id.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/modules/tickets.md
  reason: T-1860 holds live lease on docs/modules/tickets.md; narrowing to code-only
    scope
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_land_duplicate_ticket_id.py
  reason: repro/coverage test for the T-2105 fix
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_flags_id_with_genuinely_different_content_on_both_sides
- tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_the_landing_tickets_own_id
- tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_identical_content_on_both_sides
- tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_an_id_that_already_existed_at_the_merge_base
- tests/unit/test_land_duplicate_ticket_id.py::TestLandRefusesOnDuplicateTicketIdCollision::test_land_refuses_instead_of_silently_discarding_a_colliding_record
designated_repro_test: tests/unit/test_land_duplicate_ticket_id.py::TestLandRefusesOnDuplicateTicketIdCollision::test_land_refuses_instead_of_silently_discarding_a_colliding_record
acceptance:
- text: given two ticket records that once briefly both existed at the same id, when
    the ledger/history is inspected, then this is detectable/flagged rather than silently
    invisible
  evidence:
  - tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_flags_id_with_genuinely_different_content_on_both_sides
- text: given a git merge that would resolve two DIFFERENT ticket.md contents onto
    the same tickets/<id>/ticket.md path, when the merge happens, then it is refused
    or loudly flagged instead of silently picking one side
  evidence:
  - tests/unit/test_land_duplicate_ticket_id.py::TestLandRefusesOnDuplicateTicketIdCollision::test_land_refuses_instead_of_silently_discarding_a_colliding_record
threat: null
component: tickets
anchor: false
anchor_reason: null
---
## What this covers

T-2092 fixed half 1 (allocator_lock now wires renumber_one/renumber_one_v2
into the same lock new_ticket and finalize_draft/finalize_draft_for_land
already share, closing the in-process TOCTOU that let a renumber and a
concurrent new_ticket silently claim the same id). T-2092's body explicitly
scoped out half 2 as its own follow-up if large: a collision must be
DETECTABLE after the fact, not merely prevented in-process.

The lock fix closes the race for two operations running against the SAME
in-memory process/root. It does nothing about the actual T-2083/T-2090
field incident's real mechanism: two DIFFERENT worktrees/roots (a landing
worktree finalizing a draft, and a `frob ticket new` direct on main) each
successfully write their own ticket at the same id, in DIFFERENT working
trees, so neither write itself ever errors -- the collision only surfaces
later, at a `git merge`, and that merge resolved it silently (no conflict,
no warning), overwriting one ticket's content with the other's.

## Required

- A detector for two ticket records (in a v2-mode repo: two DIFFERENT
  `tickets/<id>/ticket.md` blobs both once present in history for the SAME
  id, one now missing) that were both real, distinct content at any point,
  so a merge that silently picked one over the other is caught after the
  fact rather than only reconstructible by re-reading an agent's Done
  report by hand (T-2092's own incident: recovery required exactly that).
- Alternatively (or additionally): a merge-time guard specific to
  `tickets/**/ticket.md` paths -- akin to the `tickets.md` merge driver
  (docs/modules/tickets.md#git-merge-driver) -- that refuses (or at minimum
  loudly flags) an add/add or modify/modify resolution on a per-ticket
  `ticket.md` path where BOTH sides' content differs and neither is an
  ancestor of the other, instead of allowing git's normal merge resolution
  (which, per the T-2083/T-2090 incident, can resolve without a conflict at
  all under some circumstances -- worth re-investigating exactly which
  merge shape produced "no conflict, no warning" there, since a genuine
  two-sided add of the same NEW path should ordinarily conflict).

## Evidence this session already has

- The T-2092 repro test
  (`tests/test_tickets_ledger_concurrency.py::TestRenumberVsNewTicketAllocationRace`)
  demonstrates the SAME-ROOT half of this shape concretely: both writers
  report `Ok`, and the surviving on-disk content silently belongs to
  whichever wrote last -- no error, no log line naming the collision.
- The real field incident (T-2092's own body) is the cross-root/merge
  half of the same shape; T-2092 does not attempt to reproduce that half
  (would need real git worktrees + an actual merge, out of the file-scope
  this ticket declared).

## Out of scope for this follow-up unless investigation says otherwise

Do not resolve a duplicate id by picking a winner (that IS the bug this
whole ticket lineage exists to fix). Do not rely on an agent/report
noticing.