---
id: T-0586
title: Wire frob check --stamp-coverage to refresh committed coverage lock
state: done
kind: feature
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- tests/unit/test_app_runners_batch6.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners_batch6.py
  reason: existing stamp-coverage runner tests monkeypatch stamp_coverage with a 1-arg
    lambda; the T-0586 snapshot-wiring change now calls it with 2 positional args,
    breaking collection
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_passes_loaded_snapshot
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1
designated_repro_test: null
threat: null
component: null
---
T-0545 added frob.gates._coverage.write_coverage_lock (a committed frob-coverage.lock.json summary) and made stamp_coverage(root, snapshot=None) refresh it when passed a GraphSnapshot -- but src/frob/app/check_runner.py::_run_stamp_coverage (the frob check --stamp-coverage CLI entry point) is out of T-0545's scope (src/frob/gates/ only) and still calls stamp_coverage(root) with no snapshot, so the lock is never refreshed by the existing CLI path today. Wire a GraphSnapshot through (the same one run_gates/other stamping paths already build) so --stamp-coverage keeps the lock current with zero extra flags. Once adopted, also consider promoting TEST012 (frob.gates.__init__::_test012_lock, currently WARN) to ERROR -- see T-0545's Done report for the promotion rationale.