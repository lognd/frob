## Done report

frob ticket list now always ends with a one-line state census (summary: N active (X queued, Y in-progress, ...)) computed from the queue the list already loaded -- zero extra IO -- replacing the 'list | grep queued | wc -l' shell idiom. A new --stats flag appends a second line with trailing-3-day filed/landed/net rates, median created-to-first-done cycle time, and the naive burn-down ETA, all off the existing T-1100 ticket_flow report; TicketFlowReport gained median_cycle_days, mined in the same single git-history pass _count_landed_by_day already makes (no second walk). The help text discloses --stats inherits frob ticket flow's full-history mining cost until T-1330 lands. User-requested 2026-08-04.

### Changed
```
 design/frob.strata                      | 553 ++++++++++++++++----------------
 docs/modules/tickets.md                 |  11 +-
 frob.lock                               |   2 +-
 src/frob/_cli_parsers/_ticket/_query.py |  10 +
 src/frob/app/_config_external.py        |   2 +
 src/frob/app/config.py                  |   2 +
 src/frob/app/ticket_runner/_query.py    |  59 ++++
 src/frob/tickets/_models.py             |   6 +
 src/frob/tickets/_setters.py            |  38 ++-
 tests/test_tickets_velocity.py          |  46 +++
 tests/unit/test_ticket_list_summary.py  | 128 ++++++++
 tickets.md                              | 111 ++++++-
 12 files changed, 685 insertions(+), 283 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_list_summary.py::TestSummaryFooter::test_counts_per_state` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_list_summary.py::TestSummaryFooter::test_empty_queue` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_list_summary.py::TestStatsLine::test_renders_rates_cycle_and_eta` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_list_summary.py::TestStatsLine::test_labels_unshrinking_and_missing_cycle` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_list_summary.py::TestListFooterEndToEnd::test_list_always_prints_summary` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_median_cycle_days_from_created_to_first_done` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
