---
id: T-2182
title: Ticket rot is measured by TICK004 in the gates layer but never surfaced where
  dispatch happens, so 15 tickets aged past threshold (3 critical, up to 20d) while
  every wave picked freshly-filed work
state: done
kind: feature
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_splits_by_tier_under_distinct_action_headings
- tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_flags_a_ticket_past_its_priority_threshold
- tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_ignores_tickets_still_under_threshold
- tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_distinguishes_epic_and_story_tier_from_ticket_tier
- tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_only_queued_and_planned_states_are_considered
designated_repro_test: null
acceptance:
- text: 'Surface rotting tickets in the place a coordinator ALREADY looks before dispatching
    (scripts/fleet_status.py''s standing report), not behind a new command. Precedent:
    T-2049 did exactly this for the verify quarantine, and it was read and acted on
    by an agent within two hours of landing, having gone unnoticed for an hour before.
    A command someone must know to run is not surfacing. This test MUST fail against
    current main.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_splits_by_tier_under_distinct_action_headings
- text: Derive the rotting set from the ticket ledger's own STRUCTURED fields (state,
    priority, and the queued-since timestamp) compared against the configured TICK004
    thresholds -- never by parsing frob check's rendered diagnostic text. The gate
    message is a rendering; the ledger is the source of truth, and a text parse would
    break the moment the message wording changes.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_flags_a_ticket_past_its_priority_threshold
  - tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_ignores_tickets_still_under_threshold
- text: Given 15 tickets past the rot threshold including 3 critical, when a coordinator
    runs the standing fleet report, then the count and the oldest/highest-priority
    entries appear WITHOUT passing any flag -- reproducing today's state where TICK004
    fired 11 times inside a 19-error frob check list and was read as noise for the
    whole session.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_splits_by_tier_under_distinct_action_headings
- text: 'Distinguish rot by TIER, because the required ACTION differs and a single
    count conflates them. Measured on the 15 tickets currently past threshold: 10
    are tier=epic, 1 is tier=story, only 4 are tier=ticket. A rotting TICKET means
    nobody dispatched it -- the fix is to dispatch it. A rotting EPIC means nobody
    decomposed it -- it is not directly workable, and ''work it'' is the wrong instruction.
    Surfacing them as one undifferentiated number tells a coordinator to do something
    impossible for two thirds of the set, which is why I read the alarm as noise all
    session. This test MUST fail against current main.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_distinguishes_epic_and_story_tier_from_ticket_tier
- text: Do NOT fix this by exempting epics from TICK004 -- a rotting epic is a real
    problem (T-1662, the semantics-not-lexical epic, has sat 10 days while its own
    subject matter caused active defects). Report them under a distinct heading naming
    the action, e.g. 'needs decomposition into leaves' versus 'needs dispatch', derived
    from the ledger's tier field rather than from the ticket title.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_splits_by_tier_under_distinct_action_headings
threat: null
component: null
anchor: false
anchor_reason: null
---
