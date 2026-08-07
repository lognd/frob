## Done report

Split the union-zone conflict-block resolution family (`_UnionZone`, the
`_UNION_ZONES` registry, `_zone_for_path`, `_chunk_by_key`,
`_union_keyed_chunks`, `_union_append_only`, `_resolve_conflict_blocks`,
`_resolve_union_zone_conflicts`) out of _land_merge.py (1722 lines) into
a new src/frob/tickets/_land_merge_zones.py (257 lines), following T-1186/
T-1188's verbatim-move precedent. _land_merge.py imports
`_resolve_union_zone_conflicts`/`_zone_for_path` back for its own
`_auto_resolve_out_of_scope_conflicts` use; every other moved symbol stays
private to the new module.

tests/test_ticket_land.py::TestUnionZoneMerge accessed several of these
functions via the `frob.tickets._land_merge` module attribute directly
(the exact T-1186-flagged hazard) -- repointed to a new
`_land_merge_zones_mod` import alias for the 4 call sites that moved.
Scope was extended to cover the new file and this test file for that
reason.

This is one cohesive seam of T-1189's own multi-land plan, not the whole
ticket -- _land_merge.py (1722 -> 1506 lines) and _land_finalize.py
(1735 lines, untouched this land) both still exceed the 800-line LARGE001
threshold; the remaining seams (ledger-merge/newest-wins family,
draft-finalization/squash-apply/release-bump families) are left for a
follow-up land in this same ticket.

### Changed
```
 tickets.md | 24 ++++++++++++++++++++++--
 1 file changed, 22 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_composes` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_resolve_stages` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_append_only_union_concatenates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 350 warning(s), 671 waived
- error-findings: none (measured, zero errors)
