---
id: T-2283
title: 4 pre-existing test_ticket_land.py failures on main (found during T-2274)
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_ticket_land.py
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: All 4 named tests pass
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2274 (2026-08-17): these 4 tests in
tests/test_ticket_land.py fail on unmodified main (verified at commit
78d33cbd8, T-2274's own diff fully reverted) -- pre-existing, not a
regression from any change in this session:

    TestLand::test_refuses_on_dirty_main
    TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice
    TestUvLockSync::test_dirty_lock_with_other_change_still_refuses
    TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses

Not investigated further (out of T-2274's own declared scope, and
isolating the actual cause is its own piece of work) -- filed so these
are honestly tracked rather than silently left as red on main.
