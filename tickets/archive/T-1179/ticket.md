---
id: T-1179
title: 'land: draft renumbering allocated an id already taken on main, clobbering
  a main-side block (T-1090 gap on the land path)'
state: done
kind: bug
origin: human
created: '2026-07-29'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets_collision.py
- docs/modules/tickets.md
- design/frob.strata
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: T-1179 docstring/interface-sync fixes touch both files
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: T-1179 docstring/interface-sync fixes touch both files
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_ticket_land.py
  reason: T-1179's finalize_draft_for_land wiring changed which symbol test_finalize_draft_failure
    must monkeypatch
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_tickets_collision.py::TestFinalizeDraftForLandMainFreshCeiling::test_id_ceiling_reads_current_main_not_stale_worktree_view
- tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_id_title_mismatch_is_refused_not_silently_overwritten
- tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_same_id_same_title_still_resolves_via_newer
- tests/test_ticket_land.py::TestLandDeeperBranches::test_finalize_draft_failure
designated_repro_test: null
acceptance:
- text: GIVEN a worktree land whose draft renumbering runs WHEN main has allocated
    new ids since the worktree's last merge THEN renumbering reads the id ceiling
    from CURRENT main (not the worktree's stale view) under the ledger lock, and a
    would-be collision with any existing main-side id is impossible by construction,
    proven by a regression test reproducing the 2026-07-29 shape
  evidence:
  - tests/test_tickets_collision.py::TestFinalizeDraftForLandMainFreshCeiling::test_id_ceiling_reads_current_main_not_stale_worktree_view
  - tests/test_ticket_land.py::TestLandDeeperBranches::test_finalize_draft_failure
- text: GIVEN the splice THEN a landing block may never overwrite a different-titled
    existing block under the same id -- a detected id/title mismatch refuses the land
    loudly instead of silently replacing content
  evidence:
  - tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_id_title_mismatch_is_refused_not_silently_overwritten
  - tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_same_id_same_title_still_resolves_via_newer
threat: null
component: null
---
2026-07-29 incident (5th id-collision, first SINCE T-1090): coordinator filed a ticket on main (46a115c4, auto-committed); minutes later T-1170's land (17c6ca89) renumbered its residue draft to the SAME id, and the splice replaced the coordinator's block wholesale -- content lost from the live ledger (recovered from git history and refiled). T-1090's atomic allocation apparently guards concurrent new_ticket calls against a shared counter but the LAND-path renumber derived its next-id from the worktree's stale ledger view. Two independent guards per acceptance: allocation-from-current-main under lock, and a splice-level id/title-mismatch refusal (defense in depth, T-0959 style).