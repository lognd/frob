---
id: T-1618
title: A land merges the whole worktree branch, carrying unrelated and even REJECTED
  tickets onto main
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land*.py
- src/frob/app/ticket_runner/**
- docs/**
- tests/**
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: LandError needs a new PassengerTickets variant for the T-1618 passenger-disclosure
    refusal
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_refuses_and_lists_every_passenger_by_id
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_allow_cross_ticket_logs_and_proceeds
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_no_op_when_only_the_landing_tickets_own_directives_are_present
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_a_dropped_siblings_still_present_code_is_still_reported
- tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_refuses_with_a_diagnostic_message_when_scope_diff_is_empty
- tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_when_the_ticket_has_real_changes_in_its_own_scope
- tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_when_the_ticket_declares_no_scope_at_all
designated_repro_test: null
threat: null
component: null
---
`frob ticket land <id> --worktree W` merges W's BRANCH, not the commits belonging to <id>. When W holds a series of tickets worked sequentially, the first land carries every sibling's code onto main -- including tickets that were never reviewed, and including tickets that were deliberately REJECTED.

Observed 2026-08-05, the damaging case: worktree w24-waive-family held T-1581, T-1577, T-1579, T-1578, T-1580. T-1579's change (a WAIVE004 self-heal escape) was judged unsafe and reverted IN THE WORKTREE. Landing T-1581 nonetheless put T-1579's code on main, where it proceeded to delete 55 live frob:waive directives across arch/strata/perf/graph/vet on every subsequent land until it was found and reverted on main separately. Reverting the ticket in its own worktree accomplished nothing, because the code had already left by another ticket's door.

The benign-but-confusing case, seen three times the same session: after the first land carries the siblings, those siblings can no longer land. Their fix is already on main, so BUG002 finds the repro test passing at the parent and TEST016 finds an empty diff with no mutants to kill. Both gates are CORRECT; the tickets are simply already done. Resolution each time was to verify the content on main by hand and `frob ticket close` directly, with --skip-mutation-evidence for the empty diff.

Two things to fix:

1. A land must not silently carry unrelated tickets. Either merge only the landing ticket's own commits, or -- if whole-branch merge is deliberate, which is defensible for a series -- REFUSE unless the operator acknowledges the passengers, listing every other ticket whose commits are about to ride along. Silence is the bug: nothing in the output said T-1579 was going to main.

2. Landing a ticket whose content is ALREADY on main should be a recognized, first-class outcome, not a BUG002/TEST016 refusal the operator has to diagnose and route around by hand. Detect "diff is empty because this already landed", verify the content is genuinely present, and offer the close path directly.

Related, and worth deciding here: CrossTicketLeakage already exists as a concept (`--allow-cross-ticket` is its escape hatch). Determine why it did not fire for this case, since a rejected ticket's code reaching main is exactly what that check is named for. If it fires only for uncommitted leakage and not for committed sibling commits, say so and close the gap.