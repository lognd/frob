---
id: T-2633
title: 'CLI test drift: renumber/land SystemExit + stamp-baseline output string (4
  tests red)'
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
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_app_runners_batch7.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_dry_run_without_old_new_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_whole_ledger_already_contiguous
- tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_success_prints_files
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps
designated_repro_test: tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_dry_run_without_old_new_exits_1
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from T-2623's tests/unit/ red-test sweep (measured at main sha
5a15dbd92, 18 red of 5237 collected). This is the "renumber-CLI SystemExit"
class the T-2602 fixer flagged but never enumerated.

  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps
    (assert 'baseline stamp written' in captured output -- string no
    longer present, output format likely changed)
  - tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_dry_run_without_old_new_exits_1
    (Failed: DID NOT RAISE SystemExit)
  - tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_whole_ledger_already_contiguous
    (SystemExit: 1 -- raises where the test expects it not to)
  - tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_success_prints_files
    (SystemExit: 1)

Shape: CLI exit-code/output-format behavior for `frob ticket renumber` and
`frob ticket land` (plus a `check --stamp-baseline` output string) has
drifted from these tests' expectations. Needs investigation per test to
tell "test assumptions are stale" from "CLI regressed" -- do not blanket-
adjust exit codes to match current behavior without checking which side is
wrong.

Not fixed in T-2623 due to a time-boxed land window (T-2611 draining the
fleet for a repo-wide renormalization land).