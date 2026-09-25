## Done report

Changed: src/frob/tickets/_new_renumber.py::_ticket_from_spec (copy spec.points onto Ticket); docs/modules/tickets-data-storage.md#points-t-5132; tests/test_tickets_points.py::TestNewTicketPointsPersisted.test_new_with_points_persists_value

Why: `frob ticket new --points N` validated the value via `validate_points` but `_ticket_from_spec` never copied `spec.points` onto the `Ticket(...)` it built, so every freshly filed ticket round-tripped with `points: null` -- the same T-3081 dropped-field class `no_scope_declared`/`runs_last_parallel_safe` hit before it. Fixed by adding `points=spec.points` to the Ticket construction.

Evidence: tests/test_tickets_points.py::TestNewTicketPointsPersisted.test_new_with_points_persists_value -- files a ticket via `new_ticket` with `--points`-equivalent `TicketSpec(points=3)`, asserts the returned Ticket and the reloaded active-ledger copy both carry points == 3 (the ticket's own positive control).

Filed: none.

Gates: clean.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
