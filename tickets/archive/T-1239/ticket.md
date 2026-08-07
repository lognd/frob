---
id: T-1239
title: 'graph cache.db lock contention: schema application fails under parallel load
  -- no such table: files'
state: done
kind: bug
origin: agent
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/cache.py
- src/frob/process/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestSchemaLockContentionRecovery::test_locked_error_retries_instead_of_recreating
- tests/test_graph.py::TestSchemaLockContentionRecovery::test_non_locked_database_error_still_recreates
designated_repro_test: null
acceptance:
- text: 'GIVEN concurrent frob processes racing on a cold cache.db THEN schema application
    retries/serializes instead of surfacing database is locked followed by no such
    table: files unhandled-exception dispatch failures'
  evidence:
  - tests/test_graph.py::TestSchemaLockContentionRecovery::test_locked_error_retries_instead_of_recreating
  - tests/test_graph.py::TestSchemaLockContentionRecovery::test_non_locked_database_error_still_recreates
threat: null
component: null
---
Real CI/coverage-run failure reproduced 2026-07-29 in tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_fails_loud_with_sys004_when_strata_present: cache.db failed schema application: database is locked then ERROR main unhandled exception: no such table: files. Sibling of T-1224 (derived_state_write_lock contention) but distinct: sqlite schema-init race, fail-open into a broken half-initialized db.