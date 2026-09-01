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
