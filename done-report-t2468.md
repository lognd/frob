## Done report

: T-2468 fleet_status NEEDS DECOMPOSITION conflates finished epics,
unlinked blockers and unreachable tickets

Root cause confirmed directly (T-1135/T-1137/T-1219 all closed earlier
this session, precisely the shape the ticket describes): `_epics_with_
active_children` only counts a NON-terminal child and never looks in
`tickets/archive/**` at all -- an epic whose every child has landed and
archived structurally cannot distinguish itself from an epic with zero
children under that one predicate, so both land in NEEDS DECOMPOSITION.

Fix: a new `_epics_with_any_children()` (`scripts/fleet_status.py`)
scans both active `TICKETS_DIR` and `tickets/archive/**` for a
`parent == <this id>` edge in ANY state, distinct from the existing
`_epics_with_active_children` (non-terminal only, active dir only).
`_rotting_entry` now carries `has_any_child` alongside the existing
`has_active_child`; `_print_ticket_rot` uses the pair to split non-leaf
tickets three ways instead of two:

- `has_active_child` -> DECOMPOSED, BEING WORKED (unchanged)
- `not has_active_child and has_any_child` -> NEEDS CLOSE (new)
- `not has_active_child and not has_any_child` -> NEEDS DECOMPOSITION
  (same bucket as before, now correctly emptied of the finished-epic
  case)

Verified live against this repo's real ledger (`uv run python
scripts/fleet_status.py`, post-close of T-1135/T-1137/T-1219): the
TICKET ROT section now shows T-1599 under NEEDS CLOSE (it does have a
terminal child, T-2365) and the three now-closed epics no longer appear
at all (they are no longer QUEUED/PLANNED). `_print_ticket_rot`'s three
unit-test acceptance controls (below) exercise the T-1135 shape directly
via mocked `rotting_tickets()` output, independent of the live ledger's
current state.

## Acceptance

- [0] an epic with all-terminal children reports under a CLOSE-shaped
  bucket using T-1135's shape as the fixture: bound to
  `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_epic_all_terminal_children_prints_under_needs_close`
- [1] an epic with no children at all still reports under NEEDS
  DECOMPOSITION (bucket not emptied by reclassification): bound to
  `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_epic_with_no_children_at_all_still_prints_under_needs_decomposition`
- [2] T-2449's BLOCKED bucket and NEEDS DISPATCH consistency invariant
  still hold (regression check, unchanged code path, re-run to confirm
  no regression from this session's edits): bound to
  `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_blocked_leaf_never_appears_under_needs_dispatch`,
  `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_unresolved_blocker_also_keeps_leaf_out_of_needs_dispatch`

All 4 evidence ids plus the full `TestPrintTicketRot` class (7 tests)
and the full `tests/unit/test_coordinator_scripts.py` file (137 tests)
re-run fresh this session, all passing
(`SUITE-RESULT: exitstatus=0 collected=137 failed=0`).

## Filed

T-2475: "fleet_status NEEDS CLOSE bucket can misclassify a
partially-split, still-blocked story as closeable" -- found during live
verification: T-1599 (tier=story, one archived-done child T-2365
covering 2 of 5 deliverables, `blocked_by` naming an open T-2411) now
prints under NEEDS CLOSE, which is not quite right -- there is real
remaining work, not a rollup. This is the exact "BLOCKED (unlinked) --
worth detecting separately if cheap" case the ticket's own body already
flagged as deferred and out of this ticket's 3 acceptance criteria; not
folded in here, filed as a follow-up instead of expanding scope
silently.

## Cuts

None disclosed as outstanding against this ticket's own 3 acceptance
criteria. The `BLOCKED (unlinked)` detection the ticket's FIX SHAPE
section mentioned as "worth detecting separately if cheap" was
deliberately NOT built here (not required by acceptance; the T-1599
edge case above shows it is not actually cheap -- it needs the
non-leaf-tier blocked-check T-2475 now tracks).

### Changed
- `scripts/fleet_status.py`: `_epics_with_any_children` (new),
  `_rotting_entry` (`has_any_child` field), `rotting_tickets` (wires the
  new set through), `_print_ticket_rot` (three-way non-leaf split, new
  NEEDS CLOSE bucket)
- `docs/guides/coordinator-scripts.md`: new `_epics_with_any_children`
  section, updated `rotting_tickets`/`_rotting_entry`/`_print_ticket_rot`
  prose
- `tests/unit/test_coordinator_scripts.py`: two new
  `TestPrintTicketRot` tests (T-2468 acceptance [0]/[1])

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_epic_all_terminal_children_prints_under_needs_close`
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_epic_with_no_children_at_all_still_prints_under_needs_decomposition`
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_blocked_leaf_never_appears_under_needs_dispatch`
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_unresolved_blocker_also_keeps_leaf_out_of_needs_dispatch`
