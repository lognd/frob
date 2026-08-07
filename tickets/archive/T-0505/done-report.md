## Done report

Root cause: `write_ticket`'s single-file-ledger path (src/frob/tickets/_store.py)
read the whole ledger into an id->Ticket dict, upserted one id, and re-rendered
EVERY section from scratch via `_render_ledger`. Every ticket-write command
(`start`/`evidence`/`done-report`/`sweep`, all via `transition`/`add_evidence`
calling `write_ticket`) therefore rewrote the ENTIRE file even though it only
ever touched one ticket's state. On a branch whose on-disk tickets.md predates
a sibling ticket's later state on main (a finalize, close, or requeue), that
whole-file rewrite silently reproduced the WORKTREE's stale copy of every
other ticket, and the moment it landed/merged, a sibling ticket's already-
finalized state (e.g. T-0503) reverted even though no command ever targeted
it.

Fix: added `_splice_ticket_section` (single-block text splice, the write-time
analogue of `_land._splice_only_ticket`'s T-0479 own-block-only merge) and
rewired `write_ticket`'s single mode to use it: only the target ticket's own
marker-delimited span in the raw ledger TEXT is replaced (or appended, if
new); every other ticket's bytes pass through completely untouched, never
round-tripped through parse-then-render. `write_ticket` still calls
`_parse_ledger` first to Err-propagate on a malformed ledger (unchanged
safety net), but only for validation -- the actual write uses the raw text
splice, not the re-rendered dict.

Regression test: TestSingleFileLedger.test_write_ticket_never_touches_a_
sibling_ticket_bytes creates two tickets, transitions one, and asserts the
other ticket's on-disk section is byte-identical before and after (not just
value-equal after a fresh parse).

### Changed
```
 src/frob/tickets/_store.py | 98 +++++++++++++++++++++++++++++++++++++---------
 tests/test_tickets.py      | 32 +++++++++++++++
 2 files changed, 111 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestSingleFileLedger::test_write_ticket_never_touches_a_sibling_ticket_bytes` (pytest node id, verified passing when recorded)
