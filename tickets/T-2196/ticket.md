---
id: T-2196
title: 'fleet_status --ticket prints ''ticket does not exist on main'' and then reports
  dispatchable: True on the next line, so the pre-dispatch check endorses dispatching
  a nonexistent ticket'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: repro + regression tests for the dispatchable-verdict fix (nonexistent-ticket
    and blocked_by cases)
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_ticket_does_not_exist_on_main
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_a_blocker_is_still_open
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_dispatchable_when_every_blocker_is_done
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_flags_scope_divergence_between_the_live_lease_and_main
- tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_reads_blocked_by
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_ticket_does_not_exist_on_main
acceptance:
- text: 'Reproduced verbatim: ''python3 scripts/fleet_status.py --ticket T-2195''
    printed ''main: ticket does not exist on main'' and then ''dispatchable: True''
    on the very next line, while a real leased ticket (T-2183) correctly printed ''dispatchable:
    False''. So the verdict is computed from lease state alone and ignores the existence
    fact it just measured and displayed. The coordinator dispatched a nonexistent
    ticket to an agent; this check would have endorsed it. This test MUST fail against
    current main.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_ticket_does_not_exist_on_main
- text: dispatchable must be FALSE whenever the ticket does not exist on main, and
    the reason must be stated in the same terms as the measured fact -- do NOT print
    a bare False. Derive it from the ledger read that already happens (the code clearly
    performs it, since it prints the nonexistence), not from a second lookup that
    could disagree with the first.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_flags_scope_divergence_between_the_live_lease_and_main
  - tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_reads_blocked_by
- text: 'Audit every other input to the dispatchable verdict for the same shape: a
    fact measured, displayed, and then omitted from the decision. At minimum check
    terminal state (a done/dropped ticket is not dispatchable), blocked_by edges (a
    blocked ticket is not dispatchable), and SCOPE DIVERGES. Do NOT fix only the nonexistence
    case -- the defect class is ''the report knows more than the verdict uses'', and
    fixing one instance leaves the rest.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_a_blocker_is_still_open
  - tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_dispatchable_when_every_blocker_is_done
  - tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_flags_scope_divergence_between_the_live_lease_and_main
  - tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_reads_blocked_by
threat: null
component: null
anchor: false
anchor_reason: null
---
