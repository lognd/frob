## Done report

Fixed `frob sys sync-interface` silently skipping `store` blocks: extended
`_NODE_HEADER_RE` to match `store <id> { ... }` headers the same as
`node <id> { ... }` headers (a store is a node -- `_interface_conformance_
violations`/`model.nodes` already treats it as a first-class SYS104
subject). Also fixed a second, independent gap in `sync_interface_report`'s
own fast-path file skip: it only checked for the literal substring
"node " before scanning a `.strata` file, so a store-only design file
(no bare `node ` text anywhere) was silently skipped even after the
header regex fix -- now also checks for "store ".

Verified against the real repo: `frob sys sync-interface --check` now
scans and reports on `store tickets_ledger` in design/frob.strata (visible
in its own debug log line), reporting "no drift" correctly since that
store's interface= list is already current (hand-fixed by the coordinator
per the ticket description). Before this fix the store was invisible to
the tool entirely.

Added a regression test
(TestSyncInterfaceReport::test_store_block_missing_interface_attr_is_written)
that creates a store block missing an interface= attr and asserts both
sync_interface_report detects the drift and apply_sync_interface writes
the corrected text -- this is the exact scenario from the ticket
description (T-1345's five new symbols on tickets_ledger).

### Changed
```
 docs/commands/sys.md                     |  6 +++
 docs/strata/surface.md                   |  7 +++-
 src/frob/strata/_sync_interface.py       | 25 ++++++++---
 tests/unit/strata/test_sync_interface.py | 39 ++++++++++++++++++
 tickets.md                               | 71 +++++++++++++++++++++++++++++++-
 5 files changed, 140 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_store_block_missing_interface_attr_is_written` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 332 warning(s), 729 waived
- error-findings: none (measured, zero errors)
