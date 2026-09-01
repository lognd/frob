---
id: T-3654
title: 'cache round 5: exponential backoff for readonly-database contention on darwin'
state: in-progress
kind: bug
origin: human
created: '2026-09-01'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/cache.py
- tests/unit/test_graph_cache.py
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
Run 33513484322 macOS (only cache failure left; ubuntu clean on this):
  test_two_processes_connecting_concurrently_never_see_no_such_table_meta
  sibling loop observed: ERRORS:CacheLocked('attempt to write a readonly
  database')

T-3644 retired WAL (TRUNCATE mode) and widened the lock-retry matching
to include "readonly database" -- but the sibling still surfaced
CacheLocked after the bounded retries exhausted under darwin's slower
fs contention. Fix: for the readonly-database/locked shapes in the
connect/rebuild path, retry with exponential backoff against a DEADLINE
(a few seconds), not a fixed small count; keep it loud (WARNING per
retry) and keep a final hard error past the deadline. Acceptance: the
two-process test 10x consecutively locally; note CI (macOS) is the true
verifier. Scope: src/frob/graph/cache.py + tests/unit/test_graph_cache.py.

Root cause: `_with_lock_retry`, `_open`, and `_poll_and_reread` all
sleep a FIXED `_LOCK_POLL_SECONDS` (2.0s) between polls against the
30s deadline -- effectively a small fixed retry count (~15) rather than
backoff, so under darwin's slower fs contention (T-3644's body cites
this exact class) the fixed 2s cadence can miss a narrow contention
window and exhaust the budget while a tighter, faster-polling retry
would have caught it. Replace the fixed-interval sleep with exponential
backoff (small initial delay, doubling, capped at the existing 2.0s) in
all three lock-retry call sites, and promote every retry's log line to
WARNING (not just the first) per this ticket's "keep it loud"
acceptance criterion.
