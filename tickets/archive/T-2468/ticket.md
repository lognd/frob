---
id: T-2468
title: fleet_status NEEDS DECOMPOSITION conflates finished epics, unlinked blockers
  and unreachable tickets
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_epic_all_terminal_children_prints_under_needs_close
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_epic_with_no_children_at_all_still_prints_under_needs_decomposition
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_blocked_leaf_never_appears_under_needs_dispatch
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_unresolved_blocker_also_keeps_leaf_out_of_needs_dispatch
designated_repro_test: null
acceptance:
- text: Given an epic whose children are all terminal, when the rot report runs, then
    it appears under a close-shaped bucket naming the rollup-and-close remedy, not
    NEEDS DECOMPOSITION -- using T-1135's shape as the fixture.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_epic_all_terminal_children_prints_under_needs_close
- text: Given an epic with no children at all, when the rot report runs, then it still
    appears under NEEDS DECOMPOSITION, proving the bucket was not emptied by reclassification.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_epic_with_no_children_at_all_still_prints_under_needs_decomposition
- text: Given T-2449's BLOCKED bucket and its NEEDS DISPATCH consistency invariant,
    when this change lands, then both still hold.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_blocked_leaf_never_appears_under_needs_dispatch
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_unresolved_blocker_also_keeps_leaf_out_of_needs_dispatch
threat: null
component: tooling
anchor: false
anchor_reason: null
land_commit: null
---
`scripts/fleet_status.py`'s `NEEDS DECOMPOSITION` bucket conflates three
materially different states, so the alarm cannot be acted on without a
manual investigation every time.

Measured: five tickets sat in that bucket (or adjacent rot buckets) for
13-21 days, flagged on every coordinator tick. A triage pass found they
were in FOUR different states, needing four different actions:

    T-1135  all children done   -> CLOSE (rollup Done report)
    T-1137  all children done   -> CLOSE (rollup Done report)
    T-1219  all children done   -> CLOSE (rollup Done report)
    T-1599  work genuinely      -> BLOCK on an existing ticket (T-2411);
            remains                 it was never linked, so it looked
                                    stalled when it was merely unwired
    T-1614  runs_last, 48 open  -> RESHAPE (structurally unreachable,
            tickets, continuous      not merely late) -- now T-2467
            inflow

The bucket's only real distinction today is "has a live child" versus
"does not". It has no notion of "all children are terminal, so this
needs a CLOSE" -- which is why three finished epics, one mislabelled
blocked story, and one unreachable-by-construction ticket all raise the
same undifferentiated alarm.

COST. This is the coordinator's primary queue-health signal, and it was
read on many consecutive ticks without producing action, because the
label named the wrong remedy. An alarm that reliably means "go
investigate manually" trains its reader to skip it -- the same erosion
pattern as a gate emitting thousands of warnings, and the same as
T-2400's cry-wolf filer. Three epics stayed open for three weeks with
their work already finished and shipped.

FIX SHAPE: split the bucket by the state that determines the ACTION:
  - `NEEDS CLOSE` -- every child terminal, epic still open. Name the
    remedy: rollup Done report and close.
  - `NEEDS DECOMPOSITION` -- no children at all, or children exist but
    the epic's own acceptance clearly demands more. Reserve the current
    label for this genuine case.
  - `BLOCKED (unlinked)` -- worth detecting separately if cheap: an open
    ticket whose remaining work is already covered by another OPEN
    ticket that is not recorded in its `blocked_by`. T-1599 sat
    mislabelled for 13 days purely for want of that edge.

Note the related fix already landed in T-2449, which taught the
dispatchability check to resolve archived blockers and added a
`BLOCKED (dependency not yet resolved)` bucket. This is the same class
of imprecision one level up: the rot detector's categories must name the
action the reader should take, not merely the shape of the graph.

POSITIVE CONTROLS:
  - must-now-distinguish: an epic whose children are all done reports
    under a CLOSE-shaped bucket, not NEEDS DECOMPOSITION -- use T-1135's
    exact shape as the fixture.
  - must-still-fire: an epic with no children at all still reports as
    NEEDS DECOMPOSITION. Do not empty the bucket by reclassifying
    everything out of it.
  - must-not-regress: T-2449's `BLOCKED (dependency not yet resolved)`
    bucket and the NEEDS DISPATCH consistency invariant it added
    continue to hold.