---
id: T-1865
title: Document T-1847's warm-tree quarantine re-check in docs/modules/tickets.md
state: queued
kind: docs
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1847 added `_warm_tree_clears_unattributed_native_noise` to
src/frob/app/ticket_runner/_rapid_sweep.py (the warm-tree re-check before
raising quarantine on an UNATTRIBUTED, native-extension-adjacent
finding). The corresponding docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
paragraph could not be added in T-1847 itself because that file was
leased in-scope by the concurrently in-progress T-1686
(ScopeLeaseConflict on `frob ticket scope T-1847 --add
docs/modules/tickets.md`). AFFECT001 is waived on both changed symbols in
_rapid_sweep.py citing this ticket as the follow-up. Add the doc
paragraph once T-1686's lease on docs/modules/tickets.md releases.
