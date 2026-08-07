---
id: T-1458
title: 'arch: LARGE001 split of tickets _new_renumber v2 backend (T-1420 delivered
  portion 4)'
state: done
kind: feature
origin: agent
created: '2026-08-02'
priority: high
parent: T-1420
tier: ticket
sprint: null
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_renumber_v2.py
- src/frob/tickets/_store.py
- tests/test_tickets_collision.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_collision.py::TestRenumberOneV2::test_git_mv_renames_directory_and_rewrites_id_field
- tests/test_tickets_collision.py::TestRenumberOneV2::test_sibling_ticket_prose_citation_rewritten
- tests/test_tickets_collision.py::TestRenumberOneV2::test_locks_acquired_in_sorted_id_order_no_deadlock
designated_repro_test: null
acceptance:
- text: GIVEN the split WHEN frob check --only archgate --only drift runs THEN 0 errors
    and _new_renumber.py is off the LARGE001 list
  evidence:
  - tests/test_tickets_collision.py::TestRenumberOneV2::test_git_mv_renames_directory_and_rewrites_id_field
  - tests/test_tickets_collision.py::TestRenumberOneV2::test_sibling_ticket_prose_citation_rewritten
  - tests/test_tickets_collision.py::TestRenumberOneV2::test_locks_acquired_in_sorted_id_order_no_deadlock
threat: null
component: null
---
Leaf carrier for T-1420's fourth delivered portion (T-1441/T-1442/T-1446 precedent). The comment-delimited v2-mode git-mv renumber backend moved verbatim from _new_renumber.py (989 to 730 lines) into new _renumber_v2.py (288 lines); renumber_one dispatches via a local import to avoid a circular import. Five frob:tests edges repointed in tests/test_tickets_collision.py and _store.py's DUP002 waiver prose renamed to the new path. DRIFT002 went 5 errors to 0 after the repoint; archgate/wire/dead_symbols/doclink/docanchor/fmt scoped checks 0 errors; LARGE001 48 to 47 unwaived. Also carries the vet _capability seam-analysis design draft (parent T-1420) filed this session.