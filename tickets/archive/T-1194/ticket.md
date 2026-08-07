---
id: T-1194
title: 'arch: split remaining seams of _land_merge.py/_land_finalize.py -- T-1189
  residue'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land_ledger_merge.py
- tests/test_ticket_land.py
- tests/test_tickets_collision.py
- tests/test_evidence_integrity.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_ledger_merge.py
  reason: 'T-1194 pure-move split: new module + updated frob:tests/frob:doc bindings
    and doc anchor'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-1194 pure-move split: new module + updated frob:tests/frob:doc bindings
    and doc anchor'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_tickets_collision.py
  reason: 'T-1194 pure-move split: new module + updated frob:tests/frob:doc bindings
    and doc anchor'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_evidence_integrity.py
  reason: 'T-1194 pure-move split: new module + updated frob:tests/frob:doc bindings
    and doc anchor'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-1194 pure-move split: new module + updated frob:tests/frob:doc bindings
    and doc anchor'
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_ticket_land.py::TestSpliceLedger::test_same_id_newer_state_wins
- tests/test_ticket_land.py::TestSpliceOnlyTicket::test_render_that_would_drop_an_id_is_refused
- tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_render_that_would_drop_an_id_is_refused
- tests/test_ticket_land.py::TestSiblingDoneReportPreserved::test_sibling_done_report_survives_landing_another_ticket
- tests/test_ticket_land.py::TestArchiveResurrection::test_archived_id_never_resurrected
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch
- tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty::test_terminal_side_always_wins_over_non_terminal
- tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty::test_strictly_higher_rank_poorer_side_always_wins
- tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty::test_richer_side_wins_at_equal_or_lower_rank
- tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_id_title_mismatch_is_refused_not_silently_overwritten
- tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_same_id_same_title_still_resolves_via_newer
designated_repro_test: null
threat: null
component: null
---
## Description

T-1189 extracted ONE cohesive family (the union-zone conflict-block
resolution machinery: `_UnionZone`/`_zone_for_path`/`_union_keyed_chunks`/
`_union_append_only`/`_resolve_conflict_blocks`/
`_resolve_union_zone_conflicts`) out of _land_merge.py into a new
src/frob/tickets/_land_merge_zones.py (1722 -> 1506 lines), continuing the
same one-family-per-land discipline T-1186/T-1187/T-1188 established.
Budget did not allow the other seams T-1189's own plan named.
_land_merge.py is still 1506 lines and _land_finalize.py is still 1735
lines, both above the 800-line LARGE001 threshold.

Still remaining, in the same one-family-per-land shape:

- `_land_merge.py`: the ledger-merge/newest-wins family (`splice_ledger`,
  `_merge_ledger_tickets`, `_resolve_divergence`, `_newer`/`_newer_winner`/
  `_richness`, `_union_evidence`/`_union_acceptance`,
  `_drop_resurrected_ids`, `_preserve_sibling_done_reports`,
  `_carry_forward_new_worktree_tickets`, `_overlay_landed_ticket`,
  `_splice_only_ticket`) vs. the git-plumbing/wip-commit family
  (`_merge_main_into_worktree`, `_auto_resolve_out_of_scope_conflicts`,
  `_wip_commit`/`_wip_add_excluding_frob`/`_do_wip_commit`,
  `_splice_and_stage`/`_splice_and_stage_archive`, `_verify_archive_merge`,
  `_rev_parse`/`_true_merge_base`) -- the deletion-authorization pair
  (`_deletion_glob_too_broad`/`_deletion_owned`) can go with whichever side
  ends up using `_unowned_deletions`.
- `_land_finalize.py`: draft-finalization/sibling-renumbering vs.
  squash-apply/close vs. the release-bump/uv.lock/native-rebuild family
  (T-1189's own plan named this split, not yet started).

Re-filed (not re-derived from scratch) rather than letting T-1189 close
with silent residue, per TICK011.