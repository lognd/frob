---
id: T-2200
title: TICKET ROT lists a runs_last ticket under NEEDS DISPATCH, but frob ticket start
  structurally refuses it with RunsLastBlocked, so the report recommends an action
  the tool rejects
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- src/frob/gates/_tickets_gate.py
- docs/guides/coordinator-scripts.md
evidence_scope:
- tests/unit/test_coordinator_scripts.py
- tests/test_tickets_priority.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: 'Ticket body acceptance criterion 3 explicitly requires auditing TICK004

    (src/frob/gates/_tickets_gate.py) for the same runs_last omission and

    fixing the gate/report contradiction together, not just the report. The

    originally declared scope only listed scripts/fleet_status.py; widening to

    include the gate module so the fix can land as one coherent change per the

    ticket''s own explicit requirement.

    '
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: 'Doc-coverage closure requires docs/guides/coordinator-scripts.md in scope

    since every public fleet_status.py symbol has a frob:doc edge into it and

    this ticket touches several of those symbols'' docstrings.

    '
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_splits_by_tier_under_distinct_action_headings
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_runs_last_ticket_gets_its_own_deferred_bucket_not_needs_dispatch
- tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_reads_runs_last_as_a_structured_field_not_from_title
- tests/test_tickets_priority.py::TestTick004QueueRot::test_stale_critical_ticket_flags
- tests/test_tickets_priority.py::TestTick004QueueRot::test_stale_runs_last_ticket_gets_a_distinct_message_not_work_it
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_runs_last_ticket_gets_its_own_deferred_bucket_not_needs_dispatch
acceptance:
- text: 'Reproduced live: T-1614''s title is literally ''RUNS LAST: audit every frob:waive
    for cop-outs, after all other work is complete''. I ran ''frob ticket runs-last
    T-1614 on'' (runs_last: true confirmed in the ledger), and scripts/fleet_status.py
    still reports it under ''NEEDS DISPATCH (2)''. Meanwhile frob ticket start refuses
    any runs_last ticket while other tickets are open -- measured earlier today on
    T-1780, which failed with RunsLastBlocked and could not be worked until the flag
    was cleared. So the report recommends dispatching a ticket the tool will reject.
    This test MUST fail against current main.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_runs_last_ticket_gets_its_own_deferred_bucket_not_needs_dispatch
- text: 'Read runs_last from the ledger frontmatter the report ALREADY parses (_parse_ticket_ledger_file)
    and route those tickets to a third bucket naming the real action -- they are neither
    dispatchable nor decomposable, they are deliberately deferred. Do NOT drop them
    from the report: a runs_last ticket aging past threshold is still real information,
    and T-1614 at 11 days is genuinely waiting on a queue that is not draining.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_reads_runs_last_as_a_structured_field_not_from_title
- text: 'Audit the same omission in TICK004 itself: src/frob/gates/_tickets_gate.py
    contains ZERO references to runs_last, so the gate rot-alarms a ticket another
    subsystem structurally forbids anyone from starting. Two subsystems in direct
    contradiction. Do NOT fix only the report -- the gate and the report should agree
    on what a runs_last ticket''s rot means, and fixing the display while leaving
    the gate contradictory just moves the confusion.'
  evidence:
  - tests/test_tickets_priority.py::TestTick004QueueRot::test_stale_runs_last_ticket_gets_a_distinct_message_not_work_it
threat: null
component: null
anchor: false
anchor_reason: null
---
