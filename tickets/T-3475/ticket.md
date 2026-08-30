---
id: T-3475
title: triage two new EXHAUST002 findings unrelated to the isdigit-guard class
state: done
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
- scripts/fleet_status.py
- src/frob/tickets/_new_renumber.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-3475: land requires this since the bound evidence is confirmatory-only
    by construction -- the fix changes no observable runtime behavior, only what the
    may-raise resolver can prove'
  actor: logan
  at: '2026-08-30'
  old_length: 552
  new_length: 996
evidence:
- tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_finds_the_true_holder
- tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_ignores_a_lock_on_a_different_inode
- tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_unreadable_proc_locks_is_indeterminate
- tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_missing_lock_file_is_true_none
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-2568 (may-raise resolver isdigit-guard discharge). Two EXHAUST002 findings appeared in the corpus since T-2568 was filed that are NOT guard-predicate cases at all -- a different bug class, out of T-2568's scope: scripts/fleet_status.py::_true_flock_holder_pid (T-3093) leaks StopIteration uncaught; src/frob/tickets/_new_renumber.py::_open_and_lock_counter_file (T-3026/T-2952) leaks TicketLockUnavailable uncaught. Triage each: catch/declare/frob:raises as appropriate, or waive with a specific reason if intentional propagation.

frob:no-behavior-change reason="Both changes are pure static-analysis-visibility fixes with no runtime behavior change. fleet_status.py: len(matches)==1 already guarantees next(iter(matches)) cannot raise; passing an explicit None default only makes that guarantee visible to the resolver, never actually used at runtime. _new_renumber.py: adds a frob:waive comment annotating an existing intentional raise, no code semantics touched at all."