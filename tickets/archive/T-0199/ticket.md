---
id: T-0199
title: 'dup exhaustiveness meta-test: (clone-type 1-4 x language x rung) matrix registry
  + litmus fixtures'
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: T-0187
tier: ticket
sprint: null
scope:
- tickets.md
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_no_unclaimed_cells
- tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_matrix_covers_every_rung_clone_type_and_language
- tests/test_dup_exhaustiveness.py::TestMatrixClaimsFire::test_r1_python_type1
designated_repro_test: null
threat: null
component: null
---
Survey sec 5, user mandate: registry of detectors/rungs/claimed clone types; parametrized fixture pairs per claimed cell (fire + negative); unclaimed cells need written exclusions; a detector or clone-type claim added without a fixture fails the suite -- T-0158 capability-matrix mold. Meta-test must be green over the CURRENT detector set before any new detector lands (acceptance from T-0187).