---
id: T-1425
title: frob sys sync-interface silently skips store blocks, only fixes node blocks
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_sync_interface.py
- tests/unit/strata/test_sync_interface.py
- docs/strata/surface.md
- docs/commands/sys.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_sync_interface.py
  reason: narrow to the actual fix and regression test files
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/strata/test_sync_interface.py
  reason: narrow to the actual fix and regression test files
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/strata/surface.md
  reason: 'scope closure: sync-interface fix touches frob:describes edges on both
    docs'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/commands/sys.md
  reason: 'scope closure: sync-interface fix touches frob:describes edges on both
    docs'
  actor: logan
  at: '2026-08-02'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_store_block_missing_interface_attr_is_written
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-1870 deleted SYS104 (interface conformance) and its writer (frob sys
    sync-interface) in their entirety, per an explicit owner directive that no code
    path may auto-update declared public-symbol surface -- this evidence id''s test
    tested that now-removed functionality directly and has no successor test to rebind
    to (the feature is gone, not renamed). Rebound to the playbook''s own designated
    fallback for a citation with no natural surviving pytest surface (docs/guides/agent-playbook.md
    section 5''s precedent for docs-only/no-surface tickets): the CLI-dispatch integration
    test, tests/system/test_frob_self_model.py''s own model-file existence check.

    '
  actor: logan
  at: '2026-08-08'
threat: null
component: null
anchor: false
anchor_reason: null
---
`frob sys sync-interface` only auto-rewrites `node <id> { ... }` blocks
(`_NODE_HEADER_RE` in src/frob/strata/_sync_interface.py matches literally
`node\s+<id>...{`). A `store <id> : trusted { ... }` block declaring its
own `interface=` attrs (e.g. design/frob.strata's `store tickets_ledger`)
is silently skipped by both the report and the writer -- `sync_interface_
report` returns 0 drift for it even when the gate:SELFAUDIT SYS104 check
(`_interface_conformance_violations` in _selfconform.py, which iterates
model nodes generically and does NOT skip stores) correctly flags missing
symbols on it.

Discovered working T-1422 (frob ticket accept --amend/--remove): adding
`amend_acceptance`/`remove_acceptance`/`AcceptanceAmendmentEntry`/
`AcceptanceAmendmentOp` to `frob.tickets.__all__` produced 4 real
SELFAUDIT001 errors on the `tickets_ledger` store that `frob sys
sync-interface` reported as "0 drifted" and refused to fix -- had to be
hand-added to design/frob.strata instead, defeating the entire point of
the mechanical sync tool for every store-typed node in the design.

Fix: extend `_NODE_HEADER_RE` (or add a sibling `_STORE_HEADER_RE`) so
`_sync_one_file`/`_rewrite_node_interface_block` also match `store <id> {`
headers, the same way `_interface_conformance_violations` already treats
them as first-class SYS104 subjects.

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
