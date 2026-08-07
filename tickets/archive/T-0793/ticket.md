---
id: T-0793
title: 'land: re-sync uv.lock in the release-bump commit so per-invocation lock flap
  stops tripping DirtyMain/SCOPE001'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Regression tests for the uv.lock resync/dirty-tolerance behavior added
    to

    src/frob/tickets/_land.py live in this file per repo convention (one test

    module per source module); adding scope so COV002/SCOPE001 can bind them.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_ticket_land.py::TestUvLockSync::test_bump_then_lock_synced_in_commit
- tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_line_only_does_not_refuse
- tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_with_other_change_still_refuses
- tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses
- tests/test_ticket_land.py::TestUvLockSync::test_lock_sync_spawn_failure_unwinds_squash
designated_repro_test: null
acceptance:
- text: GIVEN a land whose version bump changes pyproject WHEN the land commits THEN
    uv.lock is re-synced and committed in the same land commit and a subsequent uv
    run in any checkout produces no lock drift
  evidence:
  - tests/test_ticket_land.py::TestUvLockSync::test_bump_then_lock_synced_in_commit
  - tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_line_only_does_not_refuse
  - tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_with_other_change_still_refuses
  - tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses
  - tests/test_ticket_land.py::TestUvLockSync::test_lock_sync_spawn_failure_unwinds_squash
threat: null
component: null
---
Promotion of T-0767's worktree draft db4263e7 (manual land skipped the renumber path). The uv.lock version line flaps on every uv run against a bumped pyproject, tripping DirtyMain at land and SCOPE001/PRE001 in every worktree. Land owns the version bump; it should own the lock sync too.