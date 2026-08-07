---
id: T-1189
title: 'arch: split _land_merge.py/_land_finalize.py further -- T-1186 residue'
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
- tests/test_ticket_land.py
- src/frob/tickets/_land_merge_zones.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: union-zone conflict-resolution family moved to a new module (_land_merge_zones.py);
    tests/test_ticket_land.py accesses several of its functions via the frob.tickets._land_merge
    module attribute directly and needs repointing
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/tickets/_land_merge_zones.py
  reason: the union-zone conflict-resolution family this ticket split out of _land_merge.py
    into its own file
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_composes
- tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_refuses
- tests/test_ticket_land.py::TestUnionZoneMerge::test_resolve_stages
- tests/test_ticket_land.py::TestUnionZoneMerge::test_append_only_union_concatenates
designated_repro_test: null
threat: null
component: null
---
## Description

T-1186 split src/frob/tickets/_land.py (4973 lines) into
_land.py/_land_merge.py/_land_verify.py/_land_finalize.py. _land_merge.py
(~1720 lines) and _land_finalize.py (~1730 lines) still individually
exceed LARGE001's 800-line threshold -- T-1186's own note anticipated
this ("likely its own multi-land series ... consider splitting the plan
into 2-3 tickets"), and budget only allowed the first cut in that land.

## Plan

Split _land_merge.py further along its own natural seams (e.g. the
union-zone conflict-resolution family vs the ledger-merge/newest-wins
family vs the wip-commit family), and _land_finalize.py similarly (e.g.
draft-finalization/sibling-renumbering vs squash-apply/close vs the
release-bump/uv.lock/native-rebuild family), following the same verbatim-
move pattern (zero caller-visible behavior change, frob:ticket/frob:tests
directives carried verbatim, watch for tests monkeypatching a moved
function via the module attribute directly -- T-1186's Done report has
the exact per-site verification recipe that caught this).