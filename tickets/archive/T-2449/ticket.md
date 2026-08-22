---
id: T-2449
title: archived blockers read as still-open, making a ticket permanently undispatchable
  while the rot detector demands it
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
- docs/guides/coordinator-scripts.md
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: doc updates for _classify_blockers/_classify_blockers_local/_parse_ticket_frontmatter_text
    anchors
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: new/extended TestClassifyBlockers, TestClassifyBlockersLocal, TestPrintTicketRot,
    TestRottingTickets, TestTicketFrontmatterOnMain tests
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_archived_done_blockers_do_not_keep_a_ticket_permanently_blocked
- tests/unit/test_coordinator_scripts.py::TestClassifyBlockers::test_archived_done_blocker_is_closed
- tests/unit/test_coordinator_scripts.py::TestClassifyBlockersLocal::test_done_archived_blocker_is_closed
- tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_falls_back_to_archive_when_active_ledger_has_no_such_ticket
- tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_a_genuinely_open_blocker_still_blocks
- tests/unit/test_coordinator_scripts.py::TestClassifyBlockers::test_in_progress_blocker_is_open
- tests/unit/test_coordinator_scripts.py::TestClassifyBlockersLocal::test_queued_blocker_is_open
- tests/unit/test_coordinator_scripts.py::TestClassifyBlockers::test_missing_blocker_is_unresolved_not_open
- tests/unit/test_coordinator_scripts.py::TestClassifyBlockersLocal::test_missing_blocker_is_unresolved
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_blocked_leaf_never_appears_under_needs_dispatch
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_unresolved_blocker_also_keeps_leaf_out_of_needs_dispatch
designated_repro_test: null
acceptance:
- text: Given a queued ticket whose blockers are all done and archived, when dispatchability
    is checked, then it reports dispatchable true rather than blocked.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_archived_done_blockers_do_not_keep_a_ticket_permanently_blocked
  - tests/unit/test_coordinator_scripts.py::TestClassifyBlockers::test_archived_done_blocker_is_closed
  - tests/unit/test_coordinator_scripts.py::TestClassifyBlockersLocal::test_done_archived_blocker_is_closed
  - tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_falls_back_to_archive_when_active_ledger_has_no_such_ticket
- text: Given a ticket with a genuinely open blocker, when dispatchability is checked,
    then it still reports not dispatchable, proving blocked_by was not simply ignored.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_a_genuinely_open_blocker_still_blocks
  - tests/unit/test_coordinator_scripts.py::TestClassifyBlockers::test_in_progress_blocker_is_open
  - tests/unit/test_coordinator_scripts.py::TestClassifyBlockersLocal::test_queued_blocker_is_open
- text: Given a ticket naming a blocker id that exists in neither the active ledger
    nor the archive, when checked, then the unresolvable id is reported distinctly
    rather than silently treated as blocking.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestClassifyBlockers::test_missing_blocker_is_unresolved_not_open
  - tests/unit/test_coordinator_scripts.py::TestClassifyBlockersLocal::test_missing_blocker_is_unresolved
- text: Given any ticket, when the report is produced, then it can never appear under
    NEEDS DISPATCH while also reporting dispatchable false.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_blocked_leaf_never_appears_under_needs_dispatch
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_unresolved_blocker_also_keeps_leaf_out_of_needs_dispatch
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: e0d5c56f2e1b980d6744cae4cfd8a469d8887be0
---
A ticket whose blockers have been COMPLETED AND ARCHIVED reads as
permanently blocked, so it can never be dispatched and the rot detector
flags it forever. Measured on T-1696 (high priority, queued 12 days):

    frob ticket show T-1696   -> blocked_by=['T-1692','T-1693']
    tickets/archive/T-1692/ticket.md -> state: done
    tickets/archive/T-1693/ticket.md -> state: done

    scripts/fleet_status.py --ticket T-1696
      BLOCKED BY (still open): T-1692, T-1693
      dispatchable: False

Both blockers are done. Neither is open. The resolver reports them as
open because it looks tickets up in the ACTIVE ledger directory only and
never consults `tickets/archive/`, so a completed-and-archived blocker is
indistinguishable from a missing one -- and the code resolves that
ambiguity as "still blocking".

THE SAME TOOL CONTRADICTS ITSELF. `fleet_status.py` simultaneously
reports T-1696 under `TICKET ROT / NEEDS DISPATCH (1)` -- telling the
operator to dispatch it -- and `dispatchable: False` on the per-ticket
query, telling them it cannot be. Three consecutive coordinator ticks
read the rot alarm, went to dispatch, and were turned away. That is the
whole cost: not a wrong number, but a high-priority ticket made
invisible-to-work for 12 days while loudly advertising itself.

FROB'S OWN RESOLVER ALREADY GETS THIS RIGHT. `tests/test_ticket_land.py
::TestArchiveV2::test_archived_v2_ticket_still_resolves_as_blocker`
exists precisely to pin this behaviour for the core ledger code. The
script re-implements ledger reading independently (see its own
`blocked_by` parsing at scripts/fleet_status.py:200-219) and diverges
from the implementation that has a regression test. This is a NO
DUPLICATION defect first and a lookup bug second -- two implementations
of blocker resolution, only one of them correct, and the wrong one is
what the coordinator actually reads.

FIX SHAPE:
  - Resolve blockers through frob's own ledger API rather than a second
    hand-rolled parse. If the script cannot import frob (it is run as a
    standalone coordinator script), that constraint should be stated and
    solved deliberately -- it already requires the project venv
    (`uv run python scripts/fleet_status.py`, it refuses bare python3),
    so importing frob is available.
  - A blocker id that resolves NOWHERE (neither active nor archive) must
    be reported distinctly from one that resolves to a done ticket.
    Silently treating "not found" as "still blocking" is the
    fail-loudly violation at the heart of this (epic T-2391): an
    unresolvable id is unmeasured, not blocked.
  - The rot detector and the dispatchability gate must agree. Whatever
    the fix, add a check that no ticket can appear under NEEDS DISPATCH
    while also reporting dispatchable: False.

POSITIVE CONTROLS:
  - must-now-dispatch: T-1696's exact shape -- a queued ticket whose
    blockers are all done-and-archived -- reports dispatchable: True.
  - must-still-block: a ticket with a genuinely OPEN blocker still
    reports dispatchable: False. Do not fix this by ignoring blocked_by.
  - must-report-unknown: a ticket naming a blocker id that exists
    nowhere reports that distinctly, not as "blocked".