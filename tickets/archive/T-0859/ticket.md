---
id: T-0859
title: 'DERIVED001 cross-process TOCTOU: a concurrent frob process can rewrite .frob
  between the integrity precheck and a stage''s read'
state: done
kind: security
origin: agent
created: '2026-07-23'
priority: medium
parent: T-0603
tier: ticket
sprint: null
scope:
- src/frob/check/**
- src/frob/process/**
- docs/modules/process.md
- tests/unit/test_process_lock.py
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/process.md
  reason: 'T-0859''s fix ships a new process/_lock.py primitive that needs its

    docs/modules/process.md entry (frob:doc target) and its own test file

    (tests/unit/test_process_lock.py) updated in the same change, per this

    repo''s COV001/TEST001 discipline -- extending scope to cover them rather

    than leaving doc/test additions perpetually out of scope for a ticket

    that adds a new public symbol.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_process_lock.py
  reason: 'T-0859''s fix ships a new process/_lock.py primitive that needs its

    docs/modules/process.md entry (frob:doc target) and its own test file

    (tests/unit/test_process_lock.py) updated in the same change, per this

    repo''s COV001/TEST001 discipline -- extending scope to cover them rather

    than leaving doc/test additions perpetually out of scope for a ticket

    that adds a new public symbol.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_check.py
  reason: 'T-0859''s fix ships a new process/_lock.py primitive that needs its

    docs/modules/process.md entry (frob:doc target) and its own test file

    (tests/unit/test_process_lock.py) updated in the same change, per this

    repo''s COV001/TEST001 discipline -- extending scope to cover them rather

    than leaving doc/test additions perpetually out of scope for a ticket

    that adds a new public symbol.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_lock_file_created_under_frob_dir
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_reentrant_same_mode_in_same_thread
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_reentrant_opposite_mode_raises
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_two_threads_serialize_exclusive
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_shared_locks_do_not_block_each_other
- tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_holds_shared_lock_across_precheck_and_stages
- tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_precheck_failure_short_circuits_under_lock
- tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_cpp_holds_shared_lock_across_precheck_and_stages
- tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_cpp_build_failure_skips_tests_under_held_lock
- tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_rust_holds_shared_lock_across_precheck_and_stages
- tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_ts_holds_shared_lock_across_precheck_and_stages
designated_repro_test: null
threat: null
component: null
---
T-0603 runs verify_derived_state once, synchronously, before stage dispatch -- sound against the in-process ThreadPoolExecutor race it caught, but a concurrent frob process (frob serve daemon, a parallel agent's frob check in the same checkout, a mutate run) can corrupt or mid-rebuild-rewrite .frob/cache.db AFTER the precheck verified it and BEFORE a later stage reads it: verified-then-corrupted is still trusted. T-0603's docs never claim cross-process safety (reviewer: honest, not a false claim), so this is the disclosed residual as its own obligation. Fix directions to evaluate: an flock-style shared/exclusive lock on .frob during a check run (the ledger_lock precedent), or per-read integrity at each consumer seam, or documenting single-process-per-checkout as an explicit operating assumption with a lock that ENFORCES it. Filed at T-0603's land per its reviewer's recommendation.