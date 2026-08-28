---
id: T-2984
title: 'gh_io part 2: structured CI failure reporting -- typed run/job/step/test-node
  records, clustered by signature, no raw log grepping'
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
- src/frob/ci_report.py
- tests/test_ci_report.py
- docs/modules/ci_report.md
- tickets/T-2984/*
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/ci_report.py
  reason: structured CI failure reporting on top of ghio
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_ci_report.py
  reason: structured CI failure reporting on top of ghio
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/ci_report.md
  reason: structured CI failure reporting on top of ghio
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-2984/*
  reason: structured CI failure reporting on top of ghio
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
- tests/test_ci_report.py::TestParsePytestLog::test_parses_named_failures
- tests/test_ci_report.py::TestParsePytestLog::test_clean_run_is_no_failures
- tests/test_ci_report.py::TestParsePytestLog::test_no_result_line_is_not_recoverable
- tests/test_ci_report.py::TestParsePytestLog::test_truncated_with_no_evidence_is_not_recoverable
- tests/test_ci_report.py::TestParsePytestLog::test_never_reports_clean_for_a_truncated_run_with_apparent_result
- tests/test_ci_report.py::TestBuildJobReport::test_clean_job
- tests/test_ci_report.py::TestBuildJobReport::test_failures_clustered
- tests/test_ci_report.py::TestBuildJobReport::test_empty_log_propagates_gherror
- tests/test_ci_report.py::TestBuildRunReport::test_all_jobs_reported
- tests/test_ci_report.py::TestBuildRunReport::test_one_job_log_failure_degrades_not_aborts
- tests/test_ci_report.py::test_test_failure_model_is_frozen
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: e2c7ab9b975fea3d60039e77954096dc80185dad
---
