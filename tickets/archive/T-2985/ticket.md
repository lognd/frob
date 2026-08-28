---
id: T-2985
title: 'gh_io part 3: CI result validity -- classify each outcome STILL VALID / STALE
  / UNKNOWN against the affects graph, never render stale as green'
state: done
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: T-2982
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/ci_validity.py
- tests/test_ci_validity.py
- docs/modules/ci_validity.md
- tickets/T-2985/*
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/ci_validity.py
  reason: CI result validity classifier on top of ci_report + graph.affects + verify
    watermark
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_ci_validity.py
  reason: CI result validity classifier on top of ci_report + graph.affects + verify
    watermark
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/ci_validity.md
  reason: CI result validity classifier on top of ci_report + graph.affects + verify
    watermark
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-2985/*
  reason: CI result validity classifier on top of ci_report + graph.affects + verify
    watermark
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: parent
  old_value: null
  new_value: T-2982
  reason: 'T-2982 decomposition: seam, reporting, validity'
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_ci_validity.py::TestClassifyTest::test_still_valid_when_nothing_relevant_changed
- tests/test_ci_validity.py::TestClassifyTest::test_stale_when_reached_by_a_touched_symbol
- tests/test_ci_validity.py::TestClassifyTest::test_stale_when_test_itself_touched
- tests/test_ci_validity.py::TestClassifyTest::test_unknown_when_symbol_unresolvable
- tests/test_ci_validity.py::TestClassifyTest::test_unknown_when_closure_truncated
- tests/test_ci_validity.py::TestValidityForRunHeadSha::test_diff_failure_is_err
- tests/test_ci_validity.py::TestValidityForRunHeadSha::test_classifies_every_failing_node
- tests/test_ci_validity.py::TestJobAndRunValidity::test_job_validity_covers_named_failures
- tests/test_ci_validity.py::TestJobAndRunValidity::test_run_validity_covers_every_job
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 0b2fa37da441375d56a021f718ed0a0ebd84f0e7
---
