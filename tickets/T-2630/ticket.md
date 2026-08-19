---
id: T-2630
title: 'tests/unit/strata/test_export_golden.py red on main: golden export drift'
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/strata/test_export_golden.py
- src/frob/strata/export/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
designated_repro_test: tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from T-2623's tests/unit/ red-test sweep (measured at main sha
5a15dbd92, 18 red of 5237 collected).

TestExportGolden::test_seccomp / test_k8s / test_iam are red on unmodified
main. All three assert generated export output equals a committed golden
fixture; the failure shape (string-equality assert on generated JSON/YAML)
suggests either the export renderer drifted from its golden fixtures or the
fixtures are stale -- not yet determined which. Investigate and fix the
renderer, or refresh the goldens if the renderer's new output is correct,
whichever is true; do not just re-record fixtures without checking the
renderer is right.

Not fixed in T-2623 due to a time-boxed land window (T-2611 draining the
fleet for a repo-wide renormalization land).