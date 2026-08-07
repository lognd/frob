---
id: T-0322
title: 'coverage --wait / push contract: agents block on a socket recv, never background-and-stall'
state: done
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/**
- src/frob/testing/**
- src/frob/serve/**
- tickets.md
- tests/test_app.py
- src/frob/__main__.py
- pyproject.toml
- CHANGELOG.md
- docs/modules/testing.md
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_app.py
  reason: T-0322 app work maps to tests/test_app.py
  actor: logan
  at: '2026-07-20'
- op: add
  glob: src/frob/__main__.py
  reason: frob test --wait-coverage needs one new argparse flag on the existing test
    subcommand; no new CLI surface added
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: 'REL001: new public testing.CoverageWaitError/CoverageWaitOutcome/coverage_lock_path/run_coverage_wait
    API requires a version bump + changelog entry'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: 'REL001: new public testing.CoverageWaitError/CoverageWaitOutcome/coverage_lock_path/run_coverage_wait
    API requires a version bump + changelog entry'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/testing.md
  reason: doc anchors for the new testing.CoverageWait* API; uv.lock refreshed by
    the pyproject.toml version bump
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: doc anchors for the new testing.CoverageWait* API; uv.lock refreshed by
    the pyproject.toml version bump
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_app.py::TestRunCoverageWait::test_coverage_lock_path_is_under_frob_dir
- tests/test_app.py::TestRunCoverageWait::test_no_stamp_runs_command_and_reports_ran
- tests/test_app.py::TestRunCoverageWait::test_fresh_stamp_skips_the_run
- tests/test_app.py::TestRunCoverageWait::test_failed_command_is_err
- tests/test_app.py::TestWaitCoverage::test_wait_coverage_flag_dispatches_and_exits_zero_on_success
- tests/test_app.py::TestWaitCoverage::test_wait_coverage_flag_exits_1_on_failure
designated_repro_test: null
threat: null
component: null
---
THE stall-killer, extractable before the full daemon. Observed: implementer agents run make coverage in the background and stall waiting for a Monitor notification they cannot act on -- work done, uncommitted, looping 'waiting for coverage'; coordinator had to take over ~5 agents this session. Provide a blocking-until-fresh coverage/test contract (a foreground  that blocks on completion, backed by single-flight so concurrent callers share one run) so an agent gets a definitive fresh-or-failed result inline instead of babysitting a detached job. Interim (pre-daemon): a proper foreground make-coverage wrapper + single-flight file lock so 6 agents don't each run the full suite.