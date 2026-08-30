---
id: T-2957
title: 'frob-dup: burn the family to zero and promote WARN to ERROR (restores T-2378''s
  original commitment)'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_setters.py
- tickets/T-draft-0e88662f/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_setters.py
  reason: 'real de-duplication burn-down: extracted _set_reasoned_field from set_priority/set_tier/set_component;
    filed the src/ residue triage follow-up under this ticket''s own tickets dir'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tickets/T-draft-0e88662f/**
  reason: 'real de-duplication burn-down: extracted _set_reasoned_field from set_priority/set_tier/set_component;
    filed the src/ residue triage follow-up under this ticket''s own tickets dir'
  actor: logan
  at: '2026-08-30'
triage_changes:
- field: parent
  old_value: null
  new_value: T-0969
  reason: T-2378 was marked done after amending its acceptance criteria from burn-to-zero-and-promote
    down to the single pair it fixed (1 of 557 findings); T-2957 restores the original
    commitment and is gated on the two triage children
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_tickets_priority.py::TestSetPriority::test_updates_priority_field
- tests/test_tickets_priority.py::TestSetPriority::test_reason_missing_refuses
- tests/test_tickets_priority.py::TestSetPriority::test_reasoned_change_records_triage_entry
- tests/test_tickets_tiers.py::TestSetTier::test_updates_tier_field
- tests/test_tickets_tiers.py::TestSetTier::test_reason_missing_refuses
- tests/test_tickets_organization.py::TestSetComponent::test_updates_component_field
- tests/test_tickets_organization.py::TestSetComponent::test_reason_missing_refuses
- tests/test_ticket_evidence.py::TestSetKind::test_updates_kind_field
- tests/test_ticket_evidence.py::TestSetKind::test_reason_missing_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
