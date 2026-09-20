---
id: T-4474
title: PassengerTickets fires on MOVED directives (5 false refusals in one day); compare
  directive identities, not diff lines
state: done
kind: bug
origin: agent
created: '2026-09-13'
priority: high
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_passenger*.py
- src/frob/tickets/_land.py
- tests/unit/test_land_cross_ticket_leakage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_moved_and_rewrapped_directive_does_not_refuse
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_refusal_message_distinguishes_new_from_moved_ids
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_brand_new_directive_still_refuses
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_refuses_and_lists_every_passenger_by_id
  new_node: ''
  reason: not repro evidence for T-4474 -- these predate the fix and already pass
    at parent; T-4474's own repro evidence is the 3 new normalized-identity tests
  actor: logan
  at: '2026-09-13'
- old_node: tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_allow_cross_ticket_logs_and_proceeds
  new_node: ''
  reason: not repro evidence for T-4474 -- these predate the fix and already pass
    at parent; T-4474's own repro evidence is the 3 new normalized-identity tests
  actor: logan
  at: '2026-09-13'
- old_node: tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_no_op_when_only_the_landing_tickets_own_directives_are_present
  new_node: ''
  reason: not repro evidence for T-4474 -- these predate the fix and already pass
    at parent; T-4474's own repro evidence is the 3 new normalized-identity tests
  actor: logan
  at: '2026-09-13'
- old_node: tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_a_dropped_siblings_still_present_code_is_still_reported
  new_node: ''
  reason: not repro evidence for T-4474 -- these predate the fix and already pass
    at parent; T-4474's own repro evidence is the 3 new normalized-identity tests
  actor: logan
  at: '2026-09-13'
- old_node: tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_pure_relocation_of_a_preexisting_directive_does_not_refuse
  new_node: ''
  reason: not repro evidence for T-4474 -- these predate the fix and already pass
    at parent; T-4474's own repro evidence is the 3 new normalized-identity tests
  actor: logan
  at: '2026-09-13'
- old_node: tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_relocation_that_also_edits_the_directive_line_still_refuses
  new_node: ''
  reason: not repro evidence for T-4474 -- these predate the fix and already pass
    at parent; T-4474's own repro evidence is the 3 new normalized-identity tests
  actor: logan
  at: '2026-09-13'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-09-13, five lands in one day refused with PassengerTickets (T-1618): T-4443 (frob:ticket T-4431/T-4434 directives MOVED with the functions extracted to _native_staleness_digest.py), T-4465 (T-3935), T-4448 (T-1934), T-4179 (T-0991), and T-4463's sibling case; in every one the "passenger" was an existing directive line that the ticket's refactor moved, re-wrapped, or split across a helper extraction -- no other ticket's code rode along. The coordinator landed each with --allow-cross-ticket, which is the escape hatch T-1618 reserved for genuinely joint landings, so the guard now buys overrides instead of catching passengers (the unwaivable-error-buys-excuses shape). FIX: the passenger detector must compare directive IDENTITIES, not diff lines: a `frob:ticket T-XXXX` (or frob:tests / frob:doc naming another ticket) that appears as an addition is a passenger only if the SAME directive (same anchor symbol or same normalized text) is not also present in the base tree at any location -- a move, re-wrap, or split of an existing directive is not a passenger. Token/grammar comparison (parse the directive, compare (ticket id, kind, anchor)), never line-text diffing. ACCEPTANCE: (1) a unit test that moves a `frob:ticket T-OTHER` directive from one file to another in the branch asserts NO PassengerTickets finding; (2) a test that adds a brand-new `frob:ticket T-OTHER` directive still fires; (3) the refusal message lists, per id, whether the directive is new or moved. Sprint v0.532.0.