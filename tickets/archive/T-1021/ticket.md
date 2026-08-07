---
id: T-1021
title: 'WAIVE004 stale-waiver sweep: remove ~655 waivers matching 0 findings (full-run
  verified)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/
- tests/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_lease.py::TestDoable::test_ignore_lease_returns_raw_list
- tests/test_tickets_tiers.py::TestDoableLeafOnly::test_epic_and_story_never_surface
- tests/test_gates.py::TestTick008UnknownLedgerFields::test_fires_on_unknown_field
designated_repro_test: null
acceptance:
- text: GIVEN a full unscoped frob check THEN WAIVE004 warnings are zero and gate
    errors remain zero
  evidence:
  - tests/test_gates.py::TestTick008UnknownLedgerFields::test_fires_on_unknown_field
threat: null
component: null
---
WAIVE004 flags waivers that match 0 findings. Its own message warns the signal is only trustworthy from a FULL unscoped run -- verify against a full run, never --only. For each stale waiver: remove it, unless git history shows it guards a known-flaky/diff-scoped rule (leave those with a comment upgrading them to deliberate). Re-run full check after removal batches to confirm no gate flips to error (a waiver whose removal surfaces a live finding was NOT stale -- restore it and ticket the finding instead).