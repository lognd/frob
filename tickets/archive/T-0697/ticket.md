---
id: T-0697
title: 'shared-mutable-state race approximation: unguarded writes on thread/task-reachable
  paths'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: medium
parent: T-0693
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_same_write_under_with_lock_does_not_fire
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_write_reachable_via_callee_of_dispatched_function_fires
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_write_not_reachable_from_any_dispatch_does_not_fire
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_async_create_task_dispatch_fires_same_as_thread_submit
designated_repro_test: null
acceptance:
- text: GIVEN a module-level dict written from a thread-submitted function with no
    enclosing lock WHEN the check runs THEN an advisory names the write site and the
    spawn path; GIVEN the same write under a "with lock:" block THEN silence
  evidence:
  - tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
  - tests/unit/test_arch.py::TestSharedStateRaceHazards::test_same_write_under_with_lock_does_not_fire
threat: null
component: null
---
Child 4 of T-0693. Approximate data-race detection: a WRITE to module-level or class-level mutable state (assignment, mutating method on list/dict/set) on a call path reachable from a thread target/executor submission/async task, where no lock acquisition encloses the write in that path's context, is an advisory finding (suggestion tier -- approximation, false positives possible; waivable with reason). Reuses the lock-identification machinery from T-0694 and thread-target reachability from T-0695. Single-process cousin of strata's distributed no-shared-mutable-state check (T-0656) -- coordinate rule naming, do not duplicate its model-level logic.