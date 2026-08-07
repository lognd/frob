---
id: T-1334
title: 'arch: split _land_finalize.py''s draft/squash/release families -- T-1251 residue'
state: done
kind: feature
origin: human
created: '2026-07-30'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
- docs/modules/tickets.md
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: 'Adding docs/modules/tickets.md: playbook non-negotiable "docs move with
    the

    code" -- the split moves _assert_land_complete/_worktree_full_changeset/

    _apply_release_bump/_maybe_rebuild_natives (and possibly other symbols) to

    new module file(s); their existing frob:describes anchors in this doc must

    be updated to the new source paths in the same change, or DOCLINK/COV gates

    will red on a stale path.

    '
  actor: logan
  at: '2026-07-31'
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: 'Adding the two new files this split creates: src/frob/tickets/_land_squash.py

    (squash-apply/close family) and src/frob/tickets/_land_release.py

    (release-bump/uv.lock/native-rebuild family). COV002 flags every symbol in a

    brand-new file as "changed with no open ticket" unless the file path itself

    is in an open ticket''s declared scope -- the ticket''s original scope only

    named the pre-split _land_finalize.py, which cannot cover paths that did not

    exist yet when the ticket was filed.

    '
  actor: logan
  at: '2026-07-31'
- op: add
  glob: src/frob/tickets/_land_release.py
  reason: 'Adding the two new files this split creates: src/frob/tickets/_land_squash.py

    (squash-apply/close family) and src/frob/tickets/_land_release.py

    (release-bump/uv.lock/native-rebuild family). COV002 flags every symbol in a

    brand-new file as "changed with no open ticket" unless the file path itself

    is in an open ticket''s declared scope -- the ticket''s original scope only

    named the pre-split _land_finalize.py, which cannot cover paths that did not

    exist yet when the ticket was filed.

    '
  actor: logan
  at: '2026-07-31'
evidence:
- tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
- tests/test_ticket_land.py::TestWarnIfNativeStale::test_real_land_logs_stale_native_warning
- tests/test_ticket_land.py::TestTick005LandRegressions::test_no_regression_when_terminal_ticket_stays_terminal
- tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_none_is_noop
- tests/test_ticket_land.py::TestLandCompleteness::test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty
designated_repro_test: null
threat: null
component: null
---
T-1251 split _land_merge.py's git-plumbing/wip-commit family out into a
new src/frob/tickets/_land_git_ops.py (_land_merge.py: 1183 -> 172 lines,
clearing its LARGE001 finding). Budget did not extend to the second named
seam.

_land_finalize.py is still 1840 lines, above the 800-line LARGE001
threshold. T-1189's own plan (re-cited by T-1251) named the split:
draft-finalization/sibling-renumbering vs. squash-apply/close vs. the
release-bump/uv.lock/native-rebuild family. Not yet started.

Re-filed (not re-derived from scratch) rather than letting T-1251 close
with silent residue, per TICK011.