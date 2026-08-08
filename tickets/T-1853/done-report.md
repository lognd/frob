## Done report

`_check_live_tracker_citations` in `src/frob/tickets/_land.py` now only
fires when the land would move the ticket to a TERMINAL state
(`done`/`dropped`) -- a land leaving it `queued`/`in-progress`/`blocked`
threatens no citation and is no longer refused. This directly fixes the
observed incident: T-1820, an anchor ticket permanently cited by three
`frob:waive WIRE001 follow_up="T-1820"` directives (WIRE002 disqualifies
`done`/`dropped` follow_up targets, so an anchor must stay non-terminal
forever), could not land ANY ledger record -- not just close.

Touched `tests/test_ticket_land.py` (leased by in-progress T-1686) with
`--allow-cross-ticket`: one pre-existing fixture in
`TestLiveTrackerCitationPrecheck.test_citations_found_blocks` used
`state=IN_PROGRESS`, which the fix now correctly treats as non-blocking;
updated it to `state=DONE` (via `model_copy`) so it keeps exercising the
still-blocking terminal-state case, with a comment explaining why. No
other change to that file.

Item 2 of the ticket body's REQUIRED list -- a first-class `anchor`
marker so intent is declared rather than inferred from body prose --
is filed as a follow-up draft rather than done here; it needs a schema
change plus close/land-guidance wiring beyond this ticket's declared
scope (`src/frob/tickets/_land.py`).

### Changed
```
 src/frob/tickets/_land.py          | 35 +++++++++++++++++++++++++------
 tests/test_ticket_land.py          | 10 ++++++---
 tests/test_tickets_live_tracker.py | 42 ++++++++++++++++++++++++++++++++++++++
 tickets/T-1853/ticket.md           | 16 +++++++++++++--
 tickets/T-1856/ticket.md | 22 ++++++++++++++++++++
 5 files changed, 114 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_tickets_live_tracker.py::TestLandCheckSkipsNonTerminalAnchor::test_in_progress_land_not_blocked_by_citation` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLandCheckSkipsNonTerminalAnchor::test_done_land_still_blocked_by_citation` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLiveTrackerCitationPrecheck::test_citations_found_blocks` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLiveTrackerCitationPrecheck::test_no_citations_is_ok` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 5 error(s), 777 warning(s), 741 waived
- error-findings: DOCENUM001@docs/modules/gates.md, PRE001@tickets/T-1853, SEC110@.claude/hooks/dispatch-telemetry.py, invalid-argument-type@src/frob/strata/_sync_may.py, invalid-type-form@src/frob/strata/_sync_may.py
