---
id: T-4634
title: land spends 10+ minutes AFTER publishing the commit in _record_verify_intent_for_landed_commit
  -> _load_snapshot_for_intent (full snapshot load in the land's critical path); the
  serial land queue idles for every minute of it -- defer the verify-intent snapshot
  to the async sweep or reuse the pre-land snapshot
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/ticket_land_suite/test_verify_intent.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/ticket_land_suite/test_verify_intent.py
  reason: 'positive control: snapshot loader must not be called after publish'
  actor: logan
  at: '2026-09-19'
evidence:
- tests/ticket_land_suite/test_verify_intent.py::TestRecordVerifyIntentForLandedCommit::test_given_snapshot_is_reused_never_reloaded
- tests/ticket_land_suite/test_verify_intent.py::TestRecordVerifyIntentForLandedCommit::test_real_land_records_an_intent_entry
- tests/ticket_land_suite/test_verify_intent.py::TestRecordVerifyIntentForLandedCommit::test_dry_run_is_a_noop
designated_repro_test: tests/ticket_land_suite/test_verify_intent.py::TestRecordVerifyIntentForLandedCommit::test_given_snapshot_is_reused_never_reloaded
acceptance:
- text: the post-publish _record_verify_intent_for_landed_commit call reuses a caller-supplied
    pre-publish graph snapshot instead of loading/building one after the commit is
    published
  evidence:
  - tests/ticket_land_suite/test_verify_intent.py::TestRecordVerifyIntentForLandedCommit::test_given_snapshot_is_reused_never_reloaded
  - tests/ticket_land_suite/test_verify_intent.py::TestRecordVerifyIntentForLandedCommit::test_real_land_records_an_intent_entry
  - tests/ticket_land_suite/test_verify_intent.py::TestRecordVerifyIntentForLandedCommit::test_dry_run_is_a_noop
- text: a positive-control test proves the snapshot loader (_load_snapshot_for_intent)
    is never called when a snapshot is supplied, alongside the existing verify-intent
    tests still passing
  evidence:
  - tests/ticket_land_suite/test_verify_intent.py::TestRecordVerifyIntentForLandedCommit::test_given_snapshot_is_reused_never_reloaded
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
