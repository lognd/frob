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

### Changed
```
 tickets/T-1135/done-report.md      | 126 +++++++++++++++++++++++++++++++++++++
 tickets/T-1135/ticket.md           |  41 ++++++++++--
 tickets/T-1137/done-report.md      |  97 ++++++++++++++++++++++++++++
 tickets/T-1137/ticket.md           |  35 +++++++++--
 tickets/T-1219/done-report.md      |  88 ++++++++++++++++++++++++++
 tickets/T-1219/ticket.md           |  23 ++++++-
 tickets/T-2468/ticket.md           |  19 ++++--
 tickets/T-2475/ticket.md |  48 ++++++++++++++
 8 files changed, 463 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_epic_all_terminal_children_prints_under_needs_close` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_epic_with_no_children_at_all_still_prints_under_needs_decomposition` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_blocked_leaf_never_appears_under_needs_dispatch` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_unresolved_blocker_also_keeps_leaf_out_of_needs_dispatch` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2468, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py
