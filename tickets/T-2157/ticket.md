---
id: T-2157
title: A land killed by its shell timeout leaves its staged merge in the shared root
  index, DirtyMain-blocking every other agent until someone lands or clears it by
  hand
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_land_squash.py
- tests/unit/test_land_squash_residue_reclaim.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: 'Coordinator''s original scope (src/frob/tickets/_land_git_ops.py alone)
    was

    a guess and misses the actual mutation site. Traced directly: the

    `git merge --squash --no-commit` that stages a land''s squash-merge into

    the SHARED ROOT''s real index -- the operation whose kill-during-merge

    leaves the DirtyMain residue this ticket is about -- runs in

    `_squash_and_splice_ledger`/`_squash_and_splice_ledger_v2` in

    src/frob/tickets/_land_squash.py, not in _land_git_ops.py (which only

    holds the recovery/unwind side: _verified_reset_root, describe_root_dirt,

    etc., that _land_squash.py imports). The GIT_INDEX_FILE private-index fix

    this ticket calls for belongs at the squash-merge call site itself.

    Confirmed src/frob/tickets/_land_squash.py is not currently leased by any

    other ticket (checked .git/frob-leases/ and the coordinator''s own

    leased-file list: T-1966 holds _land.py/_unlanded.py, T-2132 holds

    _quarantine.py, T-2108 holds _land_cmd.py, T-2114/T-2118 hold

    test_ticket_land.py/_leases.py -- _land_squash.py is in none of these).

    '
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/modules/tickets.md
  reason: 'Widening src/frob/tickets/_land_squash.py''s scope surfaced doc-closure

    warnings naming docs/modules/tickets.md and docs/design/ledger-v2.md as

    the frob:doc targets for symbols this ticket''s fix will touch

    (_squash_and_splice_ledger[_v2] and neighbors). Adding both so the fix and

    its doc update land together (D-05/COV001 discipline) rather than leaving

    drift for a follow-up.

    '
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/design/ledger-v2.md
  reason: 'Widening src/frob/tickets/_land_squash.py''s scope surfaced doc-closure

    warnings naming docs/modules/tickets.md and docs/design/ledger-v2.md as

    the frob:doc targets for symbols this ticket''s fix will touch

    (_squash_and_splice_ledger[_v2] and neighbors). Adding both so the fix and

    its doc update land together (D-05/COV001 discipline) rather than leaving

    drift for a follow-up.

    '
  actor: logan
  at: '2026-08-11'
- op: remove
  glob: docs/modules/tickets.md
  reason: 'Reverting the previous --add: docs/modules/tickets.md is a whole-module

    omnibus doc whose closure snowballs to 469 unrelated warnings (every

    public tickets symbol''s doc anchor), not a scoped edit target for this

    bug fix. This ticket fixes an internal git-staging mechanism

    (_squash_and_splice_ledger[_v2]''s use of the shared root index), not a

    new/changed PUBLIC symbol signature, so COV001 doc-edge discipline does

    not require a doc file in scope; if the fix does end up needing a doc

    note, it will be a small, targeted addition handled via frob:doc directly

    without carrying the whole module doc''s blast radius into this ticket''s

    scope.

    '
  actor: logan
  at: '2026-08-11'
- op: remove
  glob: docs/design/ledger-v2.md
  reason: 'Reverting the previous --add: docs/modules/tickets.md is a whole-module

    omnibus doc whose closure snowballs to 469 unrelated warnings (every

    public tickets symbol''s doc anchor), not a scoped edit target for this

    bug fix. This ticket fixes an internal git-staging mechanism

    (_squash_and_splice_ledger[_v2]''s use of the shared root index), not a

    new/changed PUBLIC symbol signature, so COV001 doc-edge discipline does

    not require a doc file in scope; if the fix does end up needing a doc

    note, it will be a small, targeted addition handled via frob:doc directly

    without carrying the whole module doc''s blast radius into this ticket''s

    scope.

    '
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tests/unit/test_land_squash_residue_reclaim.py
  reason: 'Adding a new, dedicated test file for reclaim_orphaned_squash_residue

    rather than extending tests/test_ticket_land.py, which T-2114/T-2118 hold

    a lease on this session -- avoids any lease collision.

    '
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_reclaims_when_no_live_land_holds_the_lock
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_does_not_touch_a_live_lands_own_staging
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_clean_root_is_a_no_op
designated_repro_test: tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_reclaims_when_no_live_land_holds_the_lock
threat: null
component: null
anchor: false
anchor_reason: null
---
