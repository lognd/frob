---
id: T-1392
title: 'Main''s test suite is red: 5 deterministic failures while frob check gates
  read 0 errors'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_app_runners_batch5.py
- tests/unit/perf/test_persist_run_cli.py
- tests/test_coverage_wait_shared.py
- src/frob/app/stats_runner.py
- src/frob/app/release_runner.py
- src/frob/app/perf_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/stats_runner.py
  reason: 'test_json_mode_prints_json fails: stats run() never wraps --json path in
    quiet_stdout_logs, unlike every sibling runner, so daemon_proxy/ticket-loader
    log lines leak into --json stdout'
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/app/release_runner.py
  reason: 'test_stamp_err_result_exits_1: T-1381 added allow_unbumped kwarg to release_runner.py''s
    stamp() call at line 63; caller-side test stub is scoped fix target'
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/app/perf_runner.py
  reason: 'TestHotSortKeyMetricSelection/TestPersistRunUnattributedExclusionAndWeightSum:
    _hot()''s --json path (_hot_json) is not wrapped in quiet_stdout_logs unlike _heat/_collect,
    so daemon_proxy log line leaks into --json stdout'
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_coverage_wait_shared.py::TestWorktreeLock::test_uses_daemon_lease_when_daemon_up
- tests/unit/perf/test_persist_run_cli.py::TestPersistRunUnattributedExclusionAndWeightSum::test_only_attributed_section_persists_with_summed_weight
- tests/unit/perf/test_persist_run_cli.py::TestHotSortKeyMetricSelection::test_by_p90_and_by_p50xcount_disagree_on_order
- tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_json_mode_prints_json
- tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_stamp_err_result_exits_1
designated_repro_test: null
acceptance:
- text: GIVEN a clean checkout of main WHEN the full pytest suite runs unscoped THEN
    it exits 0 with no failures
  evidence:
  - tests/test_coverage_wait_shared.py::TestWorktreeLock::test_uses_daemon_lease_when_daemon_up
  - tests/unit/perf/test_persist_run_cli.py::TestPersistRunUnattributedExclusionAndWeightSum::test_only_attributed_section_persists_with_summed_weight
  - tests/unit/perf/test_persist_run_cli.py::TestHotSortKeyMetricSelection::test_by_p90_and_by_p50xcount_disagree_on_order
  - tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_json_mode_prints_json
  - tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_stamp_err_result_exits_1
- text: GIVEN frob stats --json WHEN the daemon-proxy emits its 'computing in-process'
    INFO line THEN stdout carries only parseable JSON
  evidence:
  - tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_json_mode_prints_json
- text: GIVEN frob perf hot --json WHEN the same INFO line is emitted THEN stdout
    carries only parseable JSON
  evidence:
  - tests/unit/perf/test_persist_run_cli.py::TestHotSortKeyMetricSelection::test_by_p90_and_by_p50xcount_disagree_on_order
  - tests/unit/perf/test_persist_run_cli.py::TestPersistRunUnattributedExclusionAndWeightSum::test_only_attributed_section_persists_with_summed_weight
- text: GIVEN the release stamp and daemon-lease tests WHEN they run against current
    production contracts THEN they pass without stale-stub TypeErrors
  evidence:
  - tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_stamp_err_result_exits_1
  - tests/test_coverage_wait_shared.py::TestWorktreeLock::test_uses_daemon_lease_when_daemon_up
threat: null
component: null
---
Measured 2026-08-01 on main at 0.299.0. 'make coverage' fails at exit 2 because the pytest run fails. All five reproduce serially in 6s with -p no:randomly and empty addopts, so they are genuine, not xdist or ordering artifacts:

  tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_stamp_err_result_exits_1
  tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_json_mode_prints_json
  tests/unit/perf/test_persist_run_cli.py::TestPersistRunUnattributedExclusionAndWeightSum::test_only_attributed_section_persists_with_summed_weight
  tests/unit/perf/test_persist_run_cli.py::TestHotSortKeyMetricSelection::test_by_p90_and_by_p50xcount_disagree_on_order
  tests/test_coverage_wait_shared.py::TestWorktreeLock::test_uses_daemon_lease_when_daemon_up

At least one is a landed-work regression: T-1381 added an 'allow_unbumped' keyword to the stamp() call in src/frob/app/release_runner.py:63, but the test's lambda stub was never updated, so it raises TypeError.

The systemic point this ticket exists to record: main read 0 gate errors, 0 ruff errors and 0 ty diagnostics throughout, while the suite was red the entire time. Gate greenness is not suite greenness. This blocks T-1235, whose remaining acceptance criterion can only be discharged by a successful unscoped coverage run.