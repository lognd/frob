---
id: T-1423
title: frob check crashes with an unhandled database is locked under concurrent load
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/cache.py
- tests/test_graph_lock.py
- src/frob/graph/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/__init__.py
  reason: Acceptance criterion 1 requires the failure to surface as a typani Result
    the caller handles; the only caller of cache.connect/store_file_data/set_root
    that can observe that Result is frob.graph.__init__ (build_graph/load_graph).
    Minimal call site the ticket's own acceptance criteria require, re-applied after
    the 10b ledger restore.
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_graph_lock.py::TestCacheLockRetry::test_retries_then_succeeds_past_a_transient_lock
- tests/test_graph_lock.py::TestCacheLockRetry::test_raises_cache_locked_once_budget_exhausted
- tests/test_graph_lock.py::TestCacheLockRetry::test_non_locked_operational_error_is_not_retried
- tests/test_graph_lock.py::TestCacheLockRetry::test_store_file_data_retries_past_a_held_exclusive_lock
- tests/test_graph_lock.py::TestCacheLockRetry::test_build_graph_reports_err_instead_of_crashing_on_cache_locked
designated_repro_test: null
acceptance:
- text: GIVEN the graph cache lock is held by another connection WHEN frob check runs
    THEN it completes and reports rather than crashing with an unhandled exception
  evidence:
  - tests/test_graph_lock.py::TestCacheLockRetry::test_retries_then_succeeds_past_a_transient_lock
  - tests/test_graph_lock.py::TestCacheLockRetry::test_raises_cache_locked_once_budget_exhausted
  - tests/test_graph_lock.py::TestCacheLockRetry::test_non_locked_operational_error_is_not_retried
  - tests/test_graph_lock.py::TestCacheLockRetry::test_store_file_data_retries_past_a_held_exclusive_lock
  - tests/test_graph_lock.py::TestCacheLockRetry::test_build_graph_reports_err_instead_of_crashing_on_cache_locked
- text: GIVEN a contended cache operation WHEN the lock cannot be acquired after retry
    THEN the failure surfaces as a typani Result the caller handles, never as an escaping
    exception
  evidence:
  - tests/test_graph_lock.py::TestCacheLockRetry::test_retries_then_succeeds_past_a_transient_lock
  - tests/test_graph_lock.py::TestCacheLockRetry::test_raises_cache_locked_once_budget_exhausted
  - tests/test_graph_lock.py::TestCacheLockRetry::test_non_locked_operational_error_is_not_retried
  - tests/test_graph_lock.py::TestCacheLockRetry::test_store_file_data_retries_past_a_held_exclusive_lock
  - tests/test_graph_lock.py::TestCacheLockRetry::test_build_graph_reports_err_instead_of_crashing_on_cache_locked
threat: null
component: null
---
frob check dies with an unhandled exception when the graph cache is contended:

    ERROR: main: unhandled exception during dispatch: database is locked
    frob: database is locked

Measured on main 2026-08-02 with four agents running concurrently against the shared repo. The check had already produced its full warning output; it crashed at the end, so the entire run was lost and the exit code was a hard failure rather than a report.

TWO DEFECTS, and they should be fixed together.

1. It escapes as a raw exception. sqlite3.OperationalError "database is locked" is an expected, recoverable outcome of contending for a shared cache -- not a programmer bug. This repo's own convention is that a fallible operation a caller must handle returns a typani Result, and exceptions are reserved for unrecoverable programmer errors. A lock timeout is the former. Right now it reaches main's top-level handler and prints as an unhandled crash.

2. It does not retry. T-1239 and T-1416 already established the pattern for this exact class in the same subsystem: a locked OperationalError means another process got there first, so poll and re-read rather than treating it as fatal. T-1239 applied that to schema application; T-1416 extended it to the meta.key IntegrityError. This is the third instance of the same family -- a lock encountered on a normal read/write path, outside schema application, with no retry at all. Fix it in the same shape, and check whether a single shared helper should own "retry a contended cache operation" for all three call sites rather than a third bespoke handler. This repo's no-duplication rule applies.

WHY IT MATTERS BEYOND THE CRASH. The practical effect is that frob check is not safe to run while agents are working, which is precisely when a coordinator most wants to measure. Every gate reading taken during this session's concurrent dispatches was therefore suspect, and at least one pair of consecutive runs disagreed (5 errors then 0, with no intervening change) before this crash made the problem explicit. A measurement tool that is unreliable under the conditions it is used in is a hole in the "if frob passes, the code is good" guarantee -- you cannot trust a green you could not reproduce.

ACCEPTANCE SHOULD BE BEHAVIOURAL, not just a caught exception: with a concurrently-held lock on the cache, frob check must complete and report, not crash. A test that holds the sqlite lock from another connection while a check runs is the honest reproduction.