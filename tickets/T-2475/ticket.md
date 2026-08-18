---
id: T-2475
title: fleet_status NEEDS CLOSE bucket can misclassify a partially-split, still-blocked
  story as closeable
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
- docs/guides/coordinator-scripts.md
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: T-2475's fix needs a repro test + doc update alongside the fleet_status.py
    change
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: T-2475's fix needs a repro test + doc update alongside the fleet_status.py
    change
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_blocked_story_with_terminal_child_prints_under_blocked_not_needs_close
- tests/unit/test_coordinator_scripts.py::TestLandProcessRows::test_watcher_pgrep_pattern_is_not_counted_as_a_land
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_blocked_story_with_terminal_child_prints_under_blocked_not_needs_close
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: ca56da99d71c351df13d21531c014ebb7bf52d3c
---
`scripts/fleet_status.py`'s new NEEDS CLOSE bucket (T-2468) classifies a
non-leaf ticket as closeable whenever it has at least one child
anywhere and none of them are active -- but a story/epic can have a
real, still-open `blocked_by` edge (T-1599's exact live shape: one
archived-done child T-2365 covers 2 of 5 deliverables, the other 3
remain genuinely open and blocked on T-2411) and still show up under
NEEDS CLOSE, which is the wrong remedy (there is no rollup to write --
the work is not finished).

T-2468's own body flagged this as a separate, deferred concern ("BLOCKED
(unlinked) -- worth detecting separately if cheap") and its acceptance
criteria did not require it; T-2468 itself only fixed the T-1135-shaped
case (genuinely 100% finished epic). This ticket tracks the follow-up:
extend `_print_ticket_rot`'s non-leaf classification to check
`blocked_by`/`_classify_blockers_local` the same way the leaf-tier
BLOCKED bucket already does (T-2449), and route a non-leaf ticket with
an open/unresolved blocker into BLOCKED (or a NEEDS CLOSE-adjacent
bucket disclosing partial completion) rather than NEEDS CLOSE, even when
it also has a terminal child.

Positive control: T-1599's live shape (tier=story, one archived-done
child, blocked_by naming an open id) must NOT print under NEEDS CLOSE.