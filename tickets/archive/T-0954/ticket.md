---
id: T-0954
title: T-0590 repro scratch A
state: done
kind: docs
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/scratch_repro_a.md
- tests/test_scratch_repro_a.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/scratch_repro_a.py
  reason: repro needs a symbol-bearing file
  actor: logan
  at: '2026-07-27'
- op: remove
  glob: tests/scratch_repro_a.py
  reason: renamed to match pytest discovery pattern
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_scratch_repro_a.py
  reason: renamed to match pytest discovery pattern
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov002_done_ticket_covers_own_closing_diff
- tests/test_gates.py::TestCoverageGate::test_cov002_grace_covers_ticket_created_and_closed_in_same_diff
designated_repro_test: null
threat: null
component: null
---
throwaway repro ticket for T-0590, will be dropped

## Drop reason
- 2026-07-27: throwaway manual repro fixture for T-0590, superseded by the real regression test