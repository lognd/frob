---
id: T-3585
title: macOS-only flake in test_clean_dry_run_removes_nothing (test_clean.py)
state: done
kind: bug
origin: agent
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_clean.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'mark no-behavior-change: test-robustness-only fix'
  actor: logan
  at: '2026-08-31'
  old_length: 307
  new_length: 508
evidence:
- tests/test_clean.py::test_clean_dry_run_removes_nothing
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Recurring occasionally on macOS jobs (see run 33385515507 macos job log for the current traceback). Pull the traceback, diagnose or make diagnosable (print raw diff/state on failure). If genuinely macOS-CI-only and not reproducible locally, BUG002-waive with a reasoned frob:waive citing the CI-only nature.

frob:no-behavior-change reason="only widens the test's own before/after snapshot filter to exclude a git-internal transient lock path; does not change clean()'s behavior or any other test assertion"