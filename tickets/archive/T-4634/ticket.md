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
body_changes:
- mode: append
  reason: 'T-4634: the T-1736 verify-intent graph snapshot is loaded (or built)

    here, before _squash_apply_on_disposable_stage mutates root, because at

    this instant root''s .frob/cache.db still matches root_pre_land_tip (the

    prior land''s own squash-apply is what last wrote it), so

    _load_snapshot_for_intent''s load_graph call is ordinarily a cache HIT.

    The pre-T-4634 shape loaded (or, on a miss, fully rebuilt) this same

    snapshot AFTER publish instead -- but the squash-apply''s own file

    writes are exactly what load_graph''s staleness check

    (_first_stale_cached_file) flags as drifted, so that post-publish load

    ALWAYS missed and fell through to a full build_graph rebuild, on every

    single land, in the critical section between LAND-PROOF and process

    exit (T-4634/T-4635''s own measurement: 10+ minutes under fleet load).'
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 872
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
<!-- narrative-moved:src/frob/tickets/_land.py:3096:T-4634 -->
T-4634: load (or build) the T-1736 verify-intent graph snapshot
NOW, before `_squash_apply_on_disposable_stage` mutates `root` --
at this instant `root`'s `.frob/cache.db` still matches
`root_pre_land_tip` (the PRIOR land's own squash-apply is what
last wrote it), so `_load_snapshot_for_intent`'s `load_graph`
call is ordinarily a cache HIT. The pre-T-4634 shape loaded (or,
on a miss, fully rebuilt) this same snapshot AFTER publish
instead -- but the squash-apply's own file writes are exactly
what `load_graph`'s staleness check (`_first_stale_cached_file`)
flags as drifted, so that post-publish load ALWAYS missed and
fell through to a full `build_graph` rebuild, on every single
land, in the critical section between LAND-PROOF and process
exit (T-4634/T-4635's own measurement: 10+ minutes under fleet