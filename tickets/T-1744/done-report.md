## Done report

Added `frob.tickets._doable.already_landed_markers` (T-1744 case 1):
a DISPATCH-time positive-signal check, distinct from T-1675's LAND-time
`_check_already_landed`. For every doable candidate (queued/planned,
unblocked), it greps the files the ticket's own declared scope names
(excluding any over-broad scope entry, matching `leased_by`'s existing
breadth discipline) for that ticket's own `frob:ticket <id>` directive
text, verbatim. A hit flags a ticket whose code already carries its own
attribution marker despite the ledger still calling it open -- the exact
T-1487/T-1587 shape (a fix that landed by a direct commit, never through
`frob ticket land`).

Case 3 (a ticket whose premise was falsified by a DIFFERENT ticket's
work, with no directive marker of its own to find) is a distinct, harder
problem this function does not attempt -- there is no positive textual
signal to grep for. Left for a future design pass per the ticket's own
acceptance criteria discussion; not silently dropped.

CLI/dispatch-alarm wiring is intentionally out of this ticket's declared
scope (`frob.app.ticket_runner`) -- `already_landed_markers` is read-only
data, matching `large_glob_warnings`'s existing shape, ready for a
consumer. Filed T-1822 to wire it into `frob ticket doable`'s
render / the dispatch-stale-alarm path.

Changed: already_landed_markers, _ticket_directive_marker,
_narrow_scope_files (src/frob/tickets/_doable.py); re-export
(src/frob/tickets/__init__.py); interface + fs.read capability
(design/frob.strata); doc section "Already-landed markers at DISPATCH
time (T-1744 case 1)" (docs/modules/tickets.md).

Evidence: tests/test_tickets_dispatch_stale.py::TestAlreadyLandedMarkers
(test_own_directive_present_flags_the_ticket,
test_absent_directive_is_silent, test_over_broad_scope_entry_is_not_scanned).

Filed: T-1822 (CLI/alarm wiring follow-up).

Gates: `uv run frob check --ticket T-1744` clean (0 errors, WIRE001
waived with the T-1822 follow-up cited above; ruff-check/
ruff-format pre-existing repo-wide, unrelated to this diff, handled by
`frob ticket land`'s own auto-fmt step).

### Changed
```
 tickets/T-1744/ticket.md           | 49 ++++++++++++++++++++++++++++++++++----
 tickets/T-1822/ticket.md | 34 ++++++++++++++++++++++++++
 2 files changed, 79 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_tickets_dispatch_stale.py::TestAlreadyLandedMarkers::test_own_directive_present_flags_the_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestAlreadyLandedMarkers::test_absent_directive_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestAlreadyLandedMarkers::test_over_broad_scope_entry_is_not_scanned` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 1041 warning(s), 735 waived
- error-findings: none (measured, zero errors)
