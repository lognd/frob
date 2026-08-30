---
id: T-3470
title: 'test_fs_change_notifies_the_cached_verify_worker fails on CI: FS-watch change
  did not notify the verify worker'
state: in-progress
kind: bug
origin: agent
created: '2026-08-30'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_serve_daemon.py
- src/frob/serve/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'waive BUG002: CI-only scheduling race, not locally reproducible as FAILED_AT_PARENT'
  actor: logan
  at: '2026-08-30'
  old_length: 1026
  new_length: 1789
evidence:
- tests/test_serve_daemon.py::TestWatchThreadNotifiesVerifyWorker::test_fs_change_notifies_the_cached_verify_worker
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on GitHub Actions run 33298117154 (ubuntu-latest, HEAD f821615ca, 2026-08-30), the first run where ubuntu completes the suite (17.7 min, 8 failures of 12777). Reproduce locally by node id with -p no:xdist first; a test that passes locally but fails on CI has an environment dependency and must be made hermetic, never skipped.

FAILING: tests/test_serve_daemon.py::TestWatchThreadNotifiesVerifyWorker::test_fs_change_notifies_the_cached_verify_worker
    AssertionError: FS-watch change did not notify() the cached verify worker
First appearance of this failure in the CI history of this drive (not in the run-3 denominator). Either a timing dependency in the watch-thread test (inotify latency on the runner; check the wait budget and whether the test polls or sleeps once) or a real regression from a recent land in src/frob/serve. Measure locally 10x by node id; if it never fails locally, make the wait event-driven with a generous bounded deadline; if it fails locally, bisect the serve/ changes since b94cea5d0.

frob:waive BUG002 reason="the defect is a CI-only scheduling race between the daemon socket becoming reachable (bind/listen) and WatchThread completing its first poll tick (which always captures whatever state exists at that moment as its baseline, never reporting a change on tick 1 by construction) -- measured 10/10 passing locally on main before this fix, matching the ticket's own instruction that a local-clean CI-only failure means timing, not a code regression. It is not reproducible as FAILED_AT_PARENT in a local/parent-commit repro check by construction. The fix makes the test's write event-driven (repeated with distinct content until observed, within a bounded deadline) rather than changing production behavior a local repro could distinguish."