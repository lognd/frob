---
id: T-3659
title: windows gates_suite failure denominator tracking (post win32 fix)
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: high
blocked_by:
- T-3651
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/gates_suite/
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: decompose run 33521416410's 20 failures into 6 buckets
  actor: logan
  at: '2026-09-01'
  old_length: 2167
  new_length: 4915
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33513484322: the Windows suite RAN for the first time (13123
collected before the interrupt) and produced a real failing set:
21 SUITE-RESULT-FAILED lines, all in tests/gates_suite/*:
- test_protocol.py: 10 (protocol ordering/verification/cleanup gates)
- test_fix_engine.py: 4 (scope-lease + Tier-A shapes)
- test_waive.py: 2 (WAIVE004 examined-sites guard)
- test_run.py: 3 (process-pool preload, perf gate paths)
- test_debt.py: 1 (REL001 land-owned lease)
List is INCOMPLETE (run interrupted). File this as the tracking ticket
for the win32 suite campaign, blocked_by TICKET D's id: after D lands
and a full un-interrupted Windows run completes, RE-MEASURE the full
failing set, decompose into buckets (macOS-campaign style), and update
this ticket's body with the real denominator. Do not fix anything under
this ticket directly.

UPDATE (run 33521416410, post T-3651 land): the Windows suite completed
to collected=13126, failed=20 this time -- died at TEARDOWN, not
mid-run (an improvement over the prior interrupted-at-13123 shape, but
still not a clean completion; win32 round 15's persisting SIGINT,
tracked separately, is the suspected cause and is NOT this ticket's
scope). The 20 failures are all under tests/gates_suite, same shape as
the round-14 partial list:
- test_protocol.py: 10 (protocol ordering/verification/cleanup gates)
- test_fix_engine.py: 4 (scope-lease + Tier-A shapes)
- test_waive.py: 2 (WAIVE004 examined-sites guard)
- test_run.py: 3 (process-pool preload, perf gate paths)
- test_debt.py: 1 (REL001 land-owned lease)
This matches round-14's partial list count-for-count per bucket (10/4/
2/3/1 = 20), suggesting the round-14 list was actually complete despite
the interrupt, not merely a partial sample -- but this still needs a
genuinely clean (non-teardown-death) run to confirm no further failures
were hiding past whatever point round 14's interrupt or round 15's
teardown death cut the run short. Once win32 round 15 (or whatever
replaces it) lands and a fully clean Windows run completes, re-measure
and decompose into buckets (macOS-campaign style) for real, and update
this ticket's body with the confirmed denominator.


UPDATE (this session, decomposition of run 33521416410's 20 win32 gates_suite failures into buckets, per this ticket's own instructions):

- test_debt.py (1) + part of test_fix_engine.py (1) -> T-3661: lease
  records' `worktree` field rejected by a POSIX-only argv-safety regex
  in src/frob/tickets/_leases.py, silently dropping every Windows lease.
- test_fix_engine.py (2 of 4) + test_run.py (2 of 3) -> T-3662: FMT001
  and PERF004 producers build `Violation.file`/`FixApplied.file` via
  `str(path.relative_to(root))` instead of `.as_posix()`, leaking
  native backslash separators into fields every other gate/waiver
  match assumes are POSIX.
- test_waive.py (2) -> T-3664: src/frob/arch/__init__.py's
  `files_examined` uses bare `str(path.relative_to(scan_root))` (same
  class of bug as T-3662, different module), breaking WAIVE004's
  examined-sites guard on win32.
- test_run.py (1 of 3) -> T-3665: a genuine platform-capability
  assertion (`"forkserver" in multiprocessing.get_all_start_methods()`)
  hardcoded unconditionally at the end of an otherwise-correct test;
  win32 never has forkserver. Confirmed NOT a product bug -- product's
  own `_process_pool_start_method()` already falls back to spawn
  correctly. Test-only fix.
- test_fix_engine.py (2 of 4) -> T-3666: filed against tests/conftest.py
  (out of my declared scope, sibling-owned) -- `_write`'s
  `path.write_text(text)` with no `newline=` translates `\n` to `\r\n`
  on write on win32, so the CRLF the two failing snapshot-byte-equality
  tests see is the FIXTURE corrupting its own input, not the product
  under test.
- test_protocol.py (10) -> T-3667: all 10 share one shape (`protocol_
  summary_gate` returns zero violations across every fixture/language/
  rule family). Strong diagnostic lead from the captured log (an
  ABSOLUTE-path symref appearing in `compute_protocol_summaries`'s
  reachability universe where a relative one is expected) but the exact
  call site that leaks the absolute path could NOT be confirmed from
  source alone -- every symref-construction site checked already
  normalizes correctly, and the failure did not reproduce on POSIX with
  an equivalent absolute-tmp-dir setup. Filed with the full diagnostic
  trail and a concrete next step (log `callgraph.calls` keys on an
  actual win32 run) rather than skipped, since nothing here proves the
  bug is unfixable from source -- only that pinning the exact line
  needs windows-side instrumentation this WSL environment cannot
  produce.

20/20 failures accounted for across 6 tickets (T-3661/T-3662/T-3664/
T-3665/T-3666/T-3667). Not fixing anything under this tracking ticket
itself, per its own standing instruction -- see each linked ticket for
its own root cause and fix.
