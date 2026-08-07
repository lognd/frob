---
id: T-1437
title: ledger splice driver resurrects archived tickets, breaking every in-flight
  worktree land after an archive
state: done
kind: bug
origin: agent
created: '2026-08-02'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_reporting.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_archive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: "Investigation (frob ticket start T-1437) shows the real defect and its\n\
    repair both live outside the originally-declared scope\n(src/frob/tickets/_land_merge.py,\
    \ src/frob/tickets/_reporting.py):\n\n- The actual git-merge-driver entry point\
    \ (_merge_driver, whose\n  _archived_ids(root) disk read is the root cause --\
    \ it reads the\n  live checkout's tickets-archive.md, which git has NOT yet written\
    \ to\n  disk mid-merge, so it always sees the pre-merge/stale archive) lives in\n\
    \  src/frob/app/ticket_runner/_land_cmd.py.\n- The archive-refuses-on-collision\
    \ half (AC[1], frob ticket archive's\n  idempotent collapse) lives in src/frob/tickets/_archive.py\n\
    \  (_write_archived_and_active).\n\nWidening scope to the files the fix and its\
    \ tests actually touch.\n"
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_archive.py
  reason: "Investigation (frob ticket start T-1437) shows the real defect and its\n\
    repair both live outside the originally-declared scope\n(src/frob/tickets/_land_merge.py,\
    \ src/frob/tickets/_reporting.py):\n\n- The actual git-merge-driver entry point\
    \ (_merge_driver, whose\n  _archived_ids(root) disk read is the root cause --\
    \ it reads the\n  live checkout's tickets-archive.md, which git has NOT yet written\
    \ to\n  disk mid-merge, so it always sees the pre-merge/stale archive) lives in\n\
    \  src/frob/app/ticket_runner/_land_cmd.py.\n- The archive-refuses-on-collision\
    \ half (AC[1], frob ticket archive's\n  idempotent collapse) lives in src/frob/tickets/_archive.py\n\
    \  (_write_archived_and_active).\n\nWidening scope to the files the fix and its\
    \ tests actually touch.\n"
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk
- tests/test_tickets.py::TestArchive::test_id_present_in_both_active_and_archive_collapses_not_refuses
- tests/test_ticket_merge_driver.py::TestArchivedIdsForMergeDriver::test_not_mid_merge_falls_back_to_disk_based_archived_ids
designated_repro_test: null
acceptance:
- text: GIVEN a worktree cut before an archive on main WHEN its ticket lands THEN
    the splice drops main-archived blocks from the active ledger and the land completes
    without DuplicateId
  evidence:
  - tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk
  - tests/test_tickets.py::TestArchive::test_id_present_in_both_active_and_archive_collapses_not_refuses
- text: GIVEN a ledger with the same id in tickets.md and tickets-archive.md WHEN
    frob ticket archive runs THEN it collapses the duplicate to the archive copy instead
    of refusing
  evidence:
  - tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk
  - tests/test_tickets.py::TestArchive::test_id_present_in_both_active_and_archive_collapses_not_refuses
threat: null
component: null
---
Observed 2026-08-02: after frob ticket archive ran on main (61 tickets moved to tickets-archive.md), every worktree cut before the archive fails to land: the frob-ledger merge driver unions ticket ids across base/ours/theirs, so blocks archived on main but still active in the worktree ledger are resurrected into tickets.md, and the next ledger write fails with DuplicateId (present in both active and archive). frob ticket archive inside the worktree also refuses (id collision), leaving no CLI path to repair; the only recovery is the playbook 10b restore recipe (checkout main's ledger wholesale, re-apply every worktree delta by hand via start/evidence/done-report), which was needed for the w1b-daemon series and costs 15+ commands per worktree. Fix: make the splice archive-aware -- a ticket id present in tickets-archive.md on either side ranks above any active-side copy and must be dropped from the active ledger during the splice (state-rank already exists; add archived as the top rank). Also give frob ticket archive an idempotent mode that collapses an active/archive duplicate to the archive copy instead of refusing, as the recovery path.