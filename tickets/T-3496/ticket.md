---
id: T-3496
title: 'macOS-only: text/citation scans return 0 hits (bucket D, T-3488)'
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
- tests/test_tickets_live_tracker.py;tests/test_gates.py
- src/frob/tickets/_live_tracker.py
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_live_tracker.py
  reason: 'T-3496: root cause is a git grep -E pattern using \b/\s (GNU regex extensions,
    not portable POSIX ERE) in these two source files; macOS git links a regex backend
    that silently fails to match them, producing 0 hits'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_wire.py
  reason: 'T-3496: root cause is a git grep -E pattern using \b/\s (GNU regex extensions,
    not portable POSIX ERE) in these two source files; macOS git links a regex backend
    that silently fails to match them, producing 0 hits'
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: append
  reason: 'T-3496: BUG002 waiver -- macOS-only defect cannot fail-then-pass on this
    Linux worktree host'
  actor: logan
  at: '2026-08-30'
  old_length: 1309
  new_length: 1867
evidence:
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_registry_deferred_disposition
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_registry_tracked_by_disposition
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_strata_waiver_ticket_clause
- tests/test_tickets_live_tracker.py::TestTransitionRefusesOnLiveTrackerCitation::test_close_refused_when_registry_cites_this_ticket
- tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while characterizing T-3488's macOS-only CI set (bucket D, 13 tests).

MEASURED (GitHub Actions run 33311990183, macos-latest): 13 tests fail,
all in the same shape -- a scan that finds N citations/references on
Linux finds 0 on macOS:

- tests/test_tickets_live_tracker.py (11 tests, all "assert 0 == N")
- tests/test_gates.py::TestWireGate (2 tests, "assert not True")

Suspected root causes (need measuring against a real macOS box or the
CI log with -vv, per the parent ticket's note -- this ticket owns that
measurement):
- "git grep" flag differences between GNU grep (Linux runner) and BSD
  grep (macOS's /usr/bin/grep, or a different "git grep" backend).
- "-P" (PCRE) support: BSD grep does not support -P at all; if any
  scan shells out to grep -P instead of using Python's re module,
  that call fails/returns empty on macOS.
- APFS case-insensitivity: a path-keyed match built against a
  case-sensitive assumption (ext4 on the Linux runner) could silently
  miss on APFS's default case-insensitive-but-preserving mode.

Fix shape: identify the ONE shared root cause (the ticket body's own
read is that this is one bug, not 13), then either fix it to work
identically on both filesystems/grep flavors, or declare a PLATFORM001
boundary if the primitive is genuinely POSIX-only-in-practice.

frob:waive BUG002 reason="T-3496 fixes a macOS-only git-grep-backend defect (\b/\s GNU regex extensions silently unmatched by macOS's git grep -E backend, T-3488 bucket D). The designated repro tests genuinely PASS at main on Linux (glibc's git regex backend honors \b/\s fine) and would only genuinely fail-then-pass on macos-latest CI, which this implementer cannot dispatch from a Linux worktree. Evidence is confirmatory-only on this host by the nature of the defect, not by a weak test -- same shape and same reasoning as T-3488's own BUG002 waiver."