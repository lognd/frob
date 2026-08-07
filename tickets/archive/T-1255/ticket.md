---
id: T-1255
title: 'ledger v2: renumber via git mv + multi-file reference rewrite'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-1254
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_draft_finalize.py
- src/frob/tickets/_store.py
- tests/test_tickets_collision.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_collision.py::TestRenumberOneV2::test_git_mv_renames_directory_and_rewrites_id_field
- tests/test_tickets_collision.py::TestRenumberOneV2::test_sibling_ticket_prose_citation_rewritten
- tests/test_tickets_collision.py::TestRenumberOneV2::test_locks_acquired_in_sorted_id_order_no_deadlock
- tests/test_tickets_collision.py::TestRenumberOneV2::test_dry_run_mutates_nothing
- tests/test_tickets_collision.py::TestRenumberOneV2::test_target_id_already_exists_is_duplicate_id
- tests/test_tickets_collision.py::TestRenumberOneV2::test_unknown_old_id_is_not_found
designated_repro_test: null
acceptance:
- text: 'Ledger v2 design (docs/design/ledger-v2.md section 4.1) needs renumber

    (and finalize-draft) to operate on the v2 tree: `git mv tickets/<old>

    tickets/<new>` plus rewriting the moved ticket''s own `id:` field, plus a

    multi-file reference-rewrite pass reusing T-1125''s

    `_rewrite_body_prose_references` matching core, re-pointed at a glob over

    `tickets/**/*.md` instead of one ledger''s rendered text. Blocked by the

    store-backend ticket (needs v2 file layout to exist first).'
  evidence:
  - tests/test_tickets_collision.py::TestRenumberOneV2::test_git_mv_renames_directory_and_rewrites_id_field
  - tests/test_tickets_collision.py::TestRenumberOneV2::test_sibling_ticket_prose_citation_rewritten
  - tests/test_tickets_collision.py::TestRenumberOneV2::test_dry_run_mutates_nothing
  - tests/test_tickets_collision.py::TestRenumberOneV2::test_target_id_already_exists_is_duplicate_id
  - tests/test_tickets_collision.py::TestRenumberOneV2::test_unknown_old_id_is_not_found
- text: 'GIVEN a v2-mode draft ticket directory `tickets/T-draft-<hex>/`

    WHEN it is renumbered to a real id

    THEN `git mv` relocates the directory, the frontmatter `id:` field is

    updated, and the operation is a single small commit touching only the

    renamed directory (no other ticket''s file is touched unless it actually

    cited the old id).'
  evidence:
  - tests/test_tickets_collision.py::TestRenumberOneV2::test_git_mv_renames_directory_and_rewrites_id_field
- text: 'GIVEN another ticket''s body prose cites the draft id being renumbered

    WHEN the renumber runs

    THEN that citation is rewritten to the final id in the same operation

    (reusing the T-1125 rewrite engine), and a post-renumber `frob doctor`

    sweep finds zero dangling references to the old id.'
  evidence:
  - tests/test_tickets_collision.py::TestRenumberOneV2::test_sibling_ticket_prose_citation_rewritten
- text: 'GIVEN two ticket directories are both being finalized in one land

    WHEN their per-ticket locks are acquired for the git-mv + rewrite

    THEN they are acquired in sorted-by-id order (no lock-ordering deadlock),

    verified by a concurrent regression test mirroring T-1090''s shape.'
  evidence:
  - tests/test_tickets_collision.py::TestRenumberOneV2::test_locks_acquired_in_sorted_id_order_no_deadlock
threat: null
component: null
---
Ledger v2 design (docs/design/ledger-v2.md section 4.1) needs renumber
(and finalize-draft) to operate on the v2 tree: `git mv tickets/<old>
tickets/<new>` plus rewriting the moved ticket's own `id:` field, plus a
multi-file reference-rewrite pass reusing T-1125's
`_rewrite_body_prose_references` matching core, re-pointed at a glob over
`tickets/**/*.md` instead of one ledger's rendered text. Blocked by the
store-backend ticket (needs v2 file layout to exist first).

GIVEN a v2-mode draft ticket directory `tickets/T-draft-<hex>/`
WHEN it is renumbered to a real id
THEN `git mv` relocates the directory, the frontmatter `id:` field is
updated, and the operation is a single small commit touching only the
renamed directory (no other ticket's file is touched unless it actually
cited the old id).

GIVEN another ticket's body prose cites the draft id being renumbered
WHEN the renumber runs
THEN that citation is rewritten to the final id in the same operation
(reusing the T-1125 rewrite engine), and a post-renumber `frob doctor`
sweep finds zero dangling references to the old id.

GIVEN two ticket directories are both being finalized in one land
WHEN their per-ticket locks are acquired for the git-mv + rewrite
THEN they are acquired in sorted-by-id order (no lock-ordering deadlock),
verified by a concurrent regression test mirroring T-1090's shape.