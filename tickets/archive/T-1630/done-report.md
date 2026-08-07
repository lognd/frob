## Done report

`renumber(root)` (the plain contiguous-renumber path, distinct from
`renumber_one`) always snapshotted a v1 monofile `ledger_digest(ledger_path
(root))` string before its `write_all` call, even in v2 mode. In v2 mode
`ledger_path(root)` does not exist, and `write_all` (T-1588) treats a bare
`str` `expected_digest` given in v2 mode as "no check requested" rather
than a per-id digest -- so a v2-mode `renumber(root)` had NO stale-snapshot
protection at all: a sibling process's write landing between this
function's `load_all` and its own `write_all` was silently clobbered by
the wholesale rewrite, the same T-0680 shape T-1588 already closed for
`write_all`/`write_archive`'s own primitive.

Fix: `renumber(root)` now dispatches on `_store_mode(root)`, same as
`renumber_one` already does -- v1 keeps the existing `ledger_digest` str
snapshot, v2 captures `ledger_digest_map(root)` (the per-ticket digest map
`write_all`'s v2 branch actually compares against). Added a regression
test (`TestRenumberV2StaleSnapshotGuard`) that monkeypatches `load_all` to
perform a concurrent ticket write in the exact gap between `renumber`'s
digest snapshot and its internal load, and asserts `renumber` now refuses
with `Err(TicketError.LedgerChangedSinceLoad)` instead of silently
reverting the concurrent write -- fails without the fix (the old code path
would have proceeded and clobbered it).

### Changed
```
 rapid-debt.jsonl                          |  1 +
 src/frob/tickets/_new_renumber.py         | 24 ++++++++++-
 tests/conftest.py                         | 39 ++++++++++++++++-
 tests/test_ticket_store_stale_snapshot.py | 72 +++++++++++++++++++++++++++++++
 tests/unit/test_conftest_stackdump.py     | 56 ++++++++++++++++++++++++
 tickets.md                                | 55 +++++++++++++++++++++--
 6 files changed, 240 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_ticket_store_stale_snapshot.py::TestRenumberV2StaleSnapshotGuard::test_renumber_root_refuses_when_a_ticket_changes_under_it` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 5905 warning(s), 717 waived
- error-findings: none (measured, zero errors)
