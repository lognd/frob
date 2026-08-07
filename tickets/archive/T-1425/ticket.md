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
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_store_block_missing_interface_attr_is_written
designated_repro_test: null
threat: null
component: null
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