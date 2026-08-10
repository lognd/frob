---
id: T-2075
title: Split _commit_orphaned_new_ticket_dir_only_drift/_refuse_if_main_dirty under
  ARCH001's threshold
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
evidence_scope:
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_well_formed_orphaned_dir_is_committed
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestRefuseIfMainDirtyOrphanedTicketHeal::test_orphaned_ticket_dir_no_longer_refuses
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestRefuseIfMainDirtyOrphanedTicketHeal::test_genuinely_human_dirty_root_still_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2026's own land (and T-2046's widening) grew _commit_orphaned_new_ticket_dir_only_drift to 95 lines and _refuse_if_main_dirty to 74, both past ARCH001's 60-line threshold -- ERRORS on the unscoped floor, not warnings. Genuine seam: validate-candidates (_orphaned_new_ticket_dir_candidates) vs stage-and-commit for the first; apply-auto-heals (_apply_dirty_main_auto_heals) vs decide-refuse for the second -- same split shape the repo's own precedent (_orphaned_evidence_findings pure-data vs _refuse_orphaned_evidence action) already uses.

frob:no-behavior-change reason="pure function-extraction split of two ARCH001-flagged functions into a validate/apply half and an act/decide half; control flow verified unchanged line-by-line against the pre-split diff (every early return preserved via the same Result/bool shape), and the existing T-2026/T-2046 orphaned-ticket-dir test suite (13 tests) plus the DirtyMain-heal subset of test_ticket_land.py (5 tests) all pass unchanged -- no new behavior, only a line-count-driven seam"