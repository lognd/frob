---
id: T-draft-be070c06
title: test_tickets_triage_dates.py fixtures use a semver-shaped sprint label, refused
  by T-5133's SprintIsSemverShaped
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_tickets_triage_dates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35819358270 (ubuntu/macos); re-verified failing on dev tip 39b89ed091: tests/test_tickets_triage_dates.py::TestSetSprintRecordsTriageChange::test_assigning_a_sprint_records_a_triage_change_entry, test_reassigning_the_same_sprint_still_records_an_entry, and test_reloaded_ticket_carries_the_recorded_entry all fail with Err(TicketError.SprintIsSemverShaped) -- each calls set_sprint(tmp_path, ticket_id, 'v0.531.0'), a semver-shaped label, which T-5133 (landed 2026-09-22 evening, BRIEF item 12) now refuses since a sprint must be goal-named and a version belongs in --milestone. Fix: change the fixtures' sprint label to a goal-named string (e.g. 'burn-down') so the tests exercise set_sprint's real contract again.