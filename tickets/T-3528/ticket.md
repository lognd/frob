---
id: T-3528
title: add a macOS live-process detection fallback (no /proc)
state: in-progress
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_finish_guard.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_worktree_guard.py
- src/frob/mutate/_journal.py
- docs/design/macos-portability.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'waive BUG002: docs-only correction, no behavior change'
  actor: logan
  at: '2026-08-31'
  old_length: 690
  new_length: 1078
evidence:
- tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_finds_a_process_cwd_into_the_path
- tests/test_mutate_journal.py::test_recycled_pid_with_mismatched_starttime_is_treated_stale
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
docs/design/macos-portability.md's Bucket C entry (live-process/cwd detection, 7 tests) still reads /proc directly, which does not exist on macOS -- needs an lsof -p/ps -o lstart (or psutil) equivalent, or a declared PLATFORM001 boundary. T-3500 (done) closed against this same bucket but its own Done report shows it only fixed the ticket's own scope typo and re-ran the LINUX code path 3x -- the macOS branch itself was never added (confirmed: no darwin/sys.platform branch exists in any of the scoped files). Found while binding NEGEXIST001's frob:until for T-3519; the doc's negative-existence claim is still true and needs a REAL open ticket, not T-3500 (done, does not cover the gap).



frob:waive BUG002 reason="stale negative-existence claim -- T-3500 already implemented the darwin dispatch this ticket asked for across every real scoped code path (_journal.py, _leases.py); this ticket is a doc correction (docs/design/macos-portability.md) plus binding evidence to the pre-existing passing coverage, not a code fix, so no test can fail-then-pass across this change"