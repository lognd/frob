---
id: T-1151
title: 'arch: extract remaining tickets/__init__.py families (setters/evidence/done-report)
  + split _land.py -- T-1123 residue'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_priority.py::TestSetPriority::test_updates_priority_field
- tests/test_ticket_evidence.py::TestSetKind::test_updates_kind_field
- tests/test_tickets_tiers.py::TestSetTier::test_updates_tier_field
- tests/test_tickets_tiers.py::TestSprintAssign::test_updates_sprint_field
- tests/test_tickets_tiers.py::TestSprintShow::test_state_rollup_and_velocity
- tests/test_tickets_velocity.py::TestSprintVelocity::test_transitions_mined_from_history
- tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day
- tests/test_tickets_organization.py::TestSetComponent::test_updates_component_field
designated_repro_test: null
threat: null
component: null
---
T-1123 extracted ONE family (scope mutation: mutate_scope + its private
helpers) into src/frob/tickets/_scope.py, following T-1103/T-1108's
per-family extraction pattern. tickets/__init__.py: 3070 -> 2740 lines
(330 carved) -- still above the <2000 acceptance target from T-1108's
own scope note.

Remaining families (per T-1123's own body, none yet touched by this
follow-up):
- field setters/sprint (set_priority/set_kind/set_tier/set_sprint/
  set_component, sprint_view/sprint_velocity, ticket_flow) --
  _set_ticket_field is the shared single-writer helper all four setters
  lean on
- evidence/transition (transition, add_evidence, the
  _done_transition_* guard family) -- BEWARE the load-time circular
  import T-1103's Done report flagged for this exact family
  (new_ticket/finalize_draft already late-import from the package to
  work around it)
- done-report/review/drop/attach (brief_ticket, mutate_labels,
  record_review, attach, drop helpers, compose_done_report/
  set_done_report)

_land.py (4762 lines) was not touched at all across T-1108/T-1123 --
still needs its own split (preflight/splice/verify/sweep families per
T-1108's original plan) before LARGE001 stops flagging it.

Follow the same pattern each time: one cohesive family per dispatch,
private module re-exported from __init__ via explicit imports (never
`import *`), zero caller-visible behavior change, existing tests as the
safety net, watch for tests that monkeypatch a moved function via the
PACKAGE attribute (tickets_mod.<name>) -- those need a late `from
frob.tickets import <name>` inside the moved function body instead of a
module-top-level binding.