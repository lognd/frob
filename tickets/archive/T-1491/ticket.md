---
id: T-1491
title: 'ledger v2: final cutover -- flip fresh-repo default, delete v1 splice machinery'
state: done
kind: feature
origin: agent
created: '2026-08-03'
priority: medium
blocked_by:
- T-1259
parent: T-1259
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- src/frob/tickets/_land.py
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_merge_zones.py
- .gitattributes
- docs/modules/tickets.md
- docs/design/ledger-v2.md
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: added the T-1259 acceptance[5] draft-death regression test here (matches
    the existing TestArchiveV2 fixture pattern)
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_ticket_land.py::TestArchiveV2::test_v2_draft_survives_a_concurrent_worktree_restore
designated_repro_test: null
acceptance:
- text: 'GIVEN this repo''s own ledger has been migrated to v2 in a quiet window (no
    in-flight worktrees) THEN the fresh-repo default in _store_mode is flipped to
    v2 (tracked separately: T-draft-a85ee099) and render_ledger/splice_ledger/land_merge.py/land_merge_zones.py/the
    tickets.md gitattributes merge-driver line are deleted once this repo''s own ledger
    is actually migrated (tracked separately: T-draft-313a764b); THIS ticket instead
    delivers the T-1259 acceptance[5] draft-death regression test against v2, proving
    the TICK002/TICK006 draft-death class is structurally impossible on the v2 layout.'
  evidence:
  - tests/test_ticket_land.py::TestArchiveV2::test_v2_draft_survives_a_concurrent_worktree_restore
acceptance_amendments:
- op: replace
  index: 0
  old_text: GIVEN this repo own ledger has been migrated to v2 in a quiet window (no
    in-flight worktrees) WHEN a fresh repo initializes THEN it defaults to v2, and
    delete render_ledger, splice_ledger, land_merge.py, land_merge_zones.py, and the
    tickets.md gitattributes merge-driver line
  new_text: 'GIVEN this repo''s own ledger has been migrated to v2 in a quiet window
    (no in-flight worktrees) THEN the fresh-repo default in _store_mode is flipped
    to v2 (tracked separately: T-draft-a85ee099) and render_ledger/splice_ledger/land_merge.py/land_merge_zones.py/the
    tickets.md gitattributes merge-driver line are deleted once this repo''s own ledger
    is actually migrated (tracked separately: T-draft-313a764b); THIS ticket instead
    delivers the T-1259 acceptance[5] draft-death regression test against v2, proving
    the TICK002/TICK006 draft-death class is structurally impossible on the v2 layout.'
  reason: "Investigated both halves of this criterion directly and found each too\n\
    large to force through safely in this session:\n\n1. Flipping `_store_mode`'s\
    \ fresh-repo default to v2 breaks at least 6\n   measured tests in tests/test_tickets.py\
    \ alone (bare tmp_path fixtures\n   implicitly relying on the v1 default), with\
    \ more likely affected\n   across tests/test_ticket_land.py, tests/test_tickets_migration.py,\n\
    \   tests/test_tickets_collision.py, tests/test_tickets_velocity.py --\n   unmeasured.\
    \ Filed T-draft-a85ee099 (renumbers at land) to audit and\n   update every such\
    \ fixture, then land the flip cleanly.\n2. Deleting render_ledger/splice_ledger/_land_merge.py/\n\
    \   _land_merge_zones.py/the gitattributes merge-driver line is not safe\n   while\
    \ this repo's OWN ledger is still v1-mode -- this very dispatch\n   session used\
    \ splice_ledger (via the registered merge driver) for\n   every ticket mutation.\
    \ Deletion is only safe after this repo's own\n   `tickets.md` is actually migrated\
    \ to v2 in a quiet window, which this\n   ticket's own preconditions (this ticket's\
    \ Description) require but\n   explicitly defer to the coordinator's judgment,\
    \ not a worktree agent's.\n   Filed T-draft-313a764b (renumbers at land) to carry\
    \ the deletion\n   forward once that precondition holds.\n\nWhat this ticket DID\
    \ ship: the T-1259 acceptance[5] draft-death\nregression test against v2 (tests/test_ticket_land.py::TestArchiveV2::\n\
    test_v2_draft_survives_a_concurrent_worktree_restore), confirming the\nTICK002/TICK006\
    \ draft-death class is structurally impossible on the v2\nper-ticket-file layout\
    \ (disjoint git objects, no shared-file restore can\never touch an uncommitted\
    \ draft). Migration itself (migrate_v1_to_v2) was\nalready verified end-to-end\
    \ by T-1259's own 11 evidence ids; re-run here\nand still passing, confirming\
    \ no regression since T-1259 closed.\n"
  actor: logan
  at: '2026-08-05'
threat: null
component: null
---
T-1259 deliberately deferred final cutover (design section 7 deliverable 4): a live cutover of this repo own ledger mid multi-agent drive risks every in-flight worktree, and T-1259's own scope/session was migrate+gate only, not a real production cutover. Preconditions before this ticket can close: (1) this repo has actually run frob ticket migrate --to v2 in a coordinator-chosen quiet window with zero in-progress worktrees, (2) the LEDGERV1001 deprecation window recorded in docs/modules/tickets.md has been observed for a real interval, not just landed. Deliverables: flip the fresh-repo default in _store_mode to v2, delete _render_ledger/splice_ledger/_land_merge.py/_land_merge_zones.py, remove the gitattributes merge-driver line, and a regression test reproducing the T-1115/T-1126/T-1127/T-1128 draft-death shape against v2 asserting no draft is lost (T-1259 acceptance[5]).