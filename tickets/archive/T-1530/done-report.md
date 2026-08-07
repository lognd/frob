## Done report

The T-1528 summary footer tallied raw ledger state while the rows above it render display_state(t, root) with the live lease overlay, so a leased-but-ledger-queued ticket showed [in-progress@worktree] in the rows and counted as queued in the footer on the same screen (user-reported). The census now counts display_state's base state (the segment before any @worktree decoration), guaranteeing footer==rows by construction; state names route through the same style_state helper and _stdout_color gate the rows use, and all output already flowed through the module logger. Regression test pins the leased-queued case; existing footer tests updated for the root-aware signature.

### Changed
```
 src/frob/app/ticket_runner/_query.py   | 35 ++++++++++++++++-------
 tests/unit/test_ticket_list_summary.py | 28 +++++++++++++++++--
 tickets.md                             | 51 +++++++++++++++++++++++++++++++++-
 3 files changed, 100 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_list_summary.py::TestSummaryFooter::test_leased_queued_ticket_counts_as_in_progress` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_list_summary.py::TestSummaryFooter::test_counts_per_state` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_list_summary.py::TestListFooterEndToEnd::test_list_always_prints_summary` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
