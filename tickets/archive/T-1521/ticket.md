---
id: T-1521
title: 'strata: decide whether flow src/dst validation belongs inside elaborate()
  itself'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'decision + narrow fix: elaborate() itself should validate flow src/dst
    so direct callers (frob sys export) are not blind to the gap check_cross_file_references
    only pre-checks for the merged path'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/_elaborate.py
  reason: 'decision + narrow fix: elaborate() itself should validate flow src/dst
    so direct callers (frob sys export) are not blind to the gap check_cross_file_references
    only pre-checks for the merged path'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/strata/test_elaborate.py
  reason: 'decision + narrow fix: elaborate() itself should validate flow src/dst
    so direct callers (frob sys export) are not blind to the gap check_cross_file_references
    only pre-checks for the merged path'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/strata/surface.md
  reason: 'decision + narrow fix: elaborate() itself should validate flow src/dst
    so direct callers (frob sys export) are not blind to the gap check_cross_file_references
    only pre-checks for the merged path'
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/strata/_elaborate.py
  reason: code approach reverted after decision landed on NO; only the doc (surface.md)
    records the decision now
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: tests/unit/strata/test_elaborate.py
  reason: code approach reverted after decision landed on NO; only the doc (surface.md)
    records the decision now
  actor: logan
  at: '2026-08-08'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
Disclosed cut from T-1196: check_cross_file_references only covers the two
reference shapes elaborate() itself does not already validate at all
(flow src/dst). Whether flow src/dst validation belongs inside elaborate()
itself (so a single-file design also gets it too) is left as a design
question for this follow-up.