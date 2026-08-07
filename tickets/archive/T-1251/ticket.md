---
id: T-1251
title: 'arch: split remaining seams of _land_merge.py/_land_finalize.py -- T-1194
  residue'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land.py
- src/frob/tickets/_land_ledger_merge.py
- src/frob/tickets/_land_*.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_merge.py
  reason: 'T-1251 arch seam split: the land-machinery module family (_land_merge.py

    git-plumbing/wip-commit seam, _land_finalize.py draft/squash/release

    family split) plus _land.py (imports/wires the split modules) and their

    comprehensive test surface, so a pure-refactor extraction can move code

    and update call sites/imports/tests within one declared scope.

    '
  actor: logan
  at: '2026-07-30'
- op: add
  glob: src/frob/tickets/_land_finalize.py
  reason: 'T-1251 arch seam split: the land-machinery module family (_land_merge.py

    git-plumbing/wip-commit seam, _land_finalize.py draft/squash/release

    family split) plus _land.py (imports/wires the split modules) and their

    comprehensive test surface, so a pure-refactor extraction can move code

    and update call sites/imports/tests within one declared scope.

    '
  actor: logan
  at: '2026-07-30'
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-1251 arch seam split: the land-machinery module family (_land_merge.py

    git-plumbing/wip-commit seam, _land_finalize.py draft/squash/release

    family split) plus _land.py (imports/wires the split modules) and their

    comprehensive test surface, so a pure-refactor extraction can move code

    and update call sites/imports/tests within one declared scope.

    '
  actor: logan
  at: '2026-07-30'
- op: add
  glob: src/frob/tickets/_land_ledger_merge.py
  reason: 'T-1251 arch seam split: the land-machinery module family (_land_merge.py

    git-plumbing/wip-commit seam, _land_finalize.py draft/squash/release

    family split) plus _land.py (imports/wires the split modules) and their

    comprehensive test surface, so a pure-refactor extraction can move code

    and update call sites/imports/tests within one declared scope.

    '
  actor: logan
  at: '2026-07-30'
- op: add
  glob: src/frob/tickets/_land_*.py
  reason: 'T-1251 arch seam split: the land-machinery module family (_land_merge.py

    git-plumbing/wip-commit seam, _land_finalize.py draft/squash/release

    family split) plus _land.py (imports/wires the split modules) and their

    comprehensive test surface, so a pure-refactor extraction can move code

    and update call sites/imports/tests within one declared scope.

    '
  actor: logan
  at: '2026-07-30'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-1251 arch seam split: the land-machinery module family (_land_merge.py

    git-plumbing/wip-commit seam, _land_finalize.py draft/squash/release

    family split) plus _land.py (imports/wires the split modules) and their

    comprehensive test surface, so a pure-refactor extraction can move code

    and update call sites/imports/tests within one declared scope.

    '
  actor: logan
  at: '2026-07-30'
evidence:
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_merges_by_id_never_overwrites
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish
- tests/test_ticket_land.py::TestUvLockSync::test_worktree_side_lock_flap_auto_restored_before_wip_commit
- tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
designated_repro_test: null
threat: null
component: null
---
T-1194 extracted the ledger-merge/newest-wins family (`splice_ledger`,
`_merge_ledger_tickets`, `_resolve_divergence`, `_newer`/`_newer_winner`/
`_richness`, `_union_evidence`/`_union_acceptance`, `_drop_resurrected_ids`,
`_preserve_sibling_done_reports`, `_carry_forward_new_worktree_tickets`,
`_overlay_landed_ticket`, `_splice_only_ticket`) out of _land_merge.py into
a new src/frob/tickets/_land_ledger_merge.py (1507 -> 1006 lines),
continuing the same one-family-per-land discipline T-1186/T-1187/T-1188/
T-1189/T-1192 established. Budget did not allow the other seams T-1189's
own plan named. _land_merge.py is still 1006 lines and _land_finalize.py is
still 1735 lines; _land_finalize.py is above the 800-line LARGE001
threshold.

Still remaining, in the same one-family-per-land shape:

- `_land_merge.py`: the git-plumbing/wip-commit family
  (`_merge_main_into_worktree`, `_auto_resolve_out_of_scope_conflicts`,
  `_wip_commit`/`_wip_add_excluding_frob`/`_do_wip_commit`,
  `_splice_and_stage`/`_splice_and_stage_archive`, `_verify_archive_merge`,
  `_rev_parse`/`_true_merge_base`) -- the deletion-authorization pair
  (`_deletion_glob_too_broad`/`_deletion_owned`) can go with whichever side
  ends up using `_unowned_deletions`.
- `_land_finalize.py`: draft-finalization/sibling-renumbering vs.
  squash-apply/close vs. the release-bump/uv.lock/native-rebuild family
  (T-1189's own plan named this split, not yet started).

Re-filed (not re-derived from scratch) rather than letting T-1194 close
with silent residue, per TICK011.