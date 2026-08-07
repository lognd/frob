---
id: T-1173
title: 'bug: cross-worktree lease not renamed when a draft ticket is renumbered at
  land'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/_new_renumber.py
- tests/test_ticket_leases.py
- docs/modules/tickets.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: T-1173's fix (rename_lease in _leases.py, wired into _new_renumber.py's
    renumber_one) needs a real draft+lease regression test, added to the existing
    tests/test_ticket_leases.py fixture file rather than a new one
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/tickets.md
  reason: T-1173's fix needed a docs/modules/tickets.md paragraph on the new rename_lease
    lease-migration behavior (AFFECT001) and design/frob.strata interface-registry
    entries for rename_lease/TestRenameLease/TestRenumberMigratesLeaseEndToEnd (SELFAUDIT001)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: T-1173's fix needed a docs/modules/tickets.md paragraph on the new rename_lease
    lease-migration behavior (AFFECT001) and design/frob.strata interface-registry
    entries for rename_lease/TestRenameLease/TestRenumberMigratesLeaseEndToEnd (SELFAUDIT001)
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_ticket_leases.py::TestRenameLease::test_rename_migrates_the_lease_file_and_updates_its_ticket_id_field
- tests/test_ticket_leases.py::TestRenameLease::test_rename_is_a_no_op_when_no_lease_exists_for_old_id
- tests/test_ticket_leases.py::TestRenumberMigratesLeaseEndToEnd::test_renumber_one_migrates_the_lease_the_worktree_still_holds
- tests/test_ticket_leases.py::TestRenumberMigratesLeaseEndToEnd::test_finalize_draft_for_land_migrates_the_lease_the_worktree_still_holds
designated_repro_test: null
threat: null
component: null
---
Observed while landing T-1165/T-1172 in the same worktree: frob ticket start T-draft-XXXXXXXX records a lease at .git/frob-leases/T-draft-XXXXXXXX.json. When the draft is renumbered to a real id (T-1172) at land time, the lease file is never renamed/migrated -- a subsequent frob check --ticket T-1172 in the SAME worktree that started it fails with 'no recorded lease', even though the worktree genuinely holds the ticket. Worked around by hand-copying the lease json with the new id; the renumber path should do this automatically.