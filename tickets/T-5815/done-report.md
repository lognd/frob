## Done report

`frob ticket new --points N` validated the value via `validate_points` but `_ticket_from_spec` never copied `spec.points` onto the `Ticket(...)` it built, so every freshly filed ticket round-tripped with `points: null` -- the same T-3081 dropped-field class `no_scope_declared`/`runs_last_parallel_safe` hit before it. Fixed by adding `points=spec.points` to the Ticket construction.

### Changed
```
 CHANGELOG.md                         |  3 +++
 docs/modules/tickets-data-storage.md |  7 +++++++
 src/frob/tickets/_new_renumber.py    | 14 +++++++++++++-
 tests/test_tickets_points.py         | 29 +++++++++++++++++++++++++++++
 tickets/T-5815/ticket.md             |  5 ++++-
 5 files changed, 56 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_tickets_points.py::TestNewTicketPointsPersisted::test_new_with_points_persists_value` (pytest node id, verified passing when recorded)
