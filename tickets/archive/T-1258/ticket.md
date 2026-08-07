---
id: T-1258
title: 'ledger v2: land merge story on native git per-file merge, retire frob-ledger
  driver'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-1254
- T-1255
- T-1256
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land_verify.py
- .gitattributes
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_disjoint_v2_tickets_land_with_no_custom_merge
- tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice
designated_repro_test: null
acceptance:
- text: 'Ledger v2 design (docs/design/ledger-v2.md section 5) needs `frob ticket

    land`''s merge story rebuilt around git''s native per-file 3-way merge:

    disjoint-scope branches touching different `tickets/T-####/` directories

    need no custom resolution at all. Retires the `merge.frob-ledger` git

    merge driver, `splice_ledger`, `_merge_ledger_tickets`, the archive-

    specific splice (T-0959''s fix), and the sibling-Done-report preservation

    heuristic (T-0577 item 2) -- ALL as dead code once every land runs in

    v2-only mode. Blocked by store backend, renumber, and archive tickets

    (land must be able to finalize/renumber/archive in v2 before its old

    monofile-splice logic can be safely removed).'
  evidence:
  - tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_disjoint_v2_tickets_land_with_no_custom_merge
- text: 'Do NOT delete `_land_merge.py`/`_land_merge_zones.py` in the same diff

    as adding v2 land support -- land a v2-aware land path FIRST, gated

    alongside v1 support during the compatibility window; deletion of the

    retired monofile-merge code is the migration ticket''s final-cutover step

    (design section 7.4), not this ticket''s.'
  evidence:
  - tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_disjoint_v2_tickets_land_with_no_custom_merge
- text: 'GIVEN two branches each editing a DIFFERENT ticket''s `tickets/T-####/`

    directory

    WHEN both land

    THEN git''s own merge produces zero conflicts (no custom driver invoked),

    verified by an end-to-end land test with two disjoint-scope v2 tickets.'
  evidence:
  - tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_disjoint_v2_tickets_land_with_no_custom_merge
- text: 'GIVEN two branches BOTH editing the SAME ticket''s `ticket.md`

    WHEN both attempt to land

    THEN the conflict surfaces as an ordinary git conflict on that one file

    (no `splice_ledger`-class resolution needed), verified by a test asserting

    land refuses loudly rather than silently picking a side.'
  evidence:
  - tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice
- text: 'GIVEN `.gitattributes` currently registers `tickets.md merge=frob-ledger`

    WHEN v2-only mode is reached (post-migration, this ticket''s own scope)

    THEN that line is removed and no replacement driver is registered.'
  evidence:
  - tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_disjoint_v2_tickets_land_with_no_custom_merge
threat: null
component: null
---
Ledger v2 design (docs/design/ledger-v2.md section 5) needs `frob ticket
land`'s merge story rebuilt around git's native per-file 3-way merge:
disjoint-scope branches touching different `tickets/T-####/` directories
need no custom resolution at all. Retires the `merge.frob-ledger` git
merge driver, `splice_ledger`, `_merge_ledger_tickets`, the archive-
specific splice (T-0959's fix), and the sibling-Done-report preservation
heuristic (T-0577 item 2) -- ALL as dead code once every land runs in
v2-only mode. Blocked by store backend, renumber, and archive tickets
(land must be able to finalize/renumber/archive in v2 before its old
monofile-splice logic can be safely removed).

Do NOT delete `_land_merge.py`/`_land_merge_zones.py` in the same diff
as adding v2 land support -- land a v2-aware land path FIRST, gated
alongside v1 support during the compatibility window; deletion of the
retired monofile-merge code is the migration ticket's final-cutover step
(design section 7.4), not this ticket's.

GIVEN two branches each editing a DIFFERENT ticket's `tickets/T-####/`
directory
WHEN both land
THEN git's own merge produces zero conflicts (no custom driver invoked),
verified by an end-to-end land test with two disjoint-scope v2 tickets.

GIVEN two branches BOTH editing the SAME ticket's `ticket.md`
WHEN both attempt to land
THEN the conflict surfaces as an ordinary git conflict on that one file
(no `splice_ledger`-class resolution needed), verified by a test asserting
land refuses loudly rather than silently picking a side.

GIVEN `.gitattributes` currently registers `tickets.md merge=frob-ledger`
WHEN v2-only mode is reached (post-migration, this ticket's own scope)
THEN that line is removed and no replacement driver is registered.