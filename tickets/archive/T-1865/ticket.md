---
id: T-1865
title: Document T-1847's warm-tree quarantine re-check in docs/modules/tickets.md
state: done
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
- src/frob/app/ticket_runner/_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: plan requires removing the two AFFECT001 waivers this ticket's doc paragraph
    resolves
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_drops_cold_worktree_native_noise
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_keeps_finding_when_native_still_broken
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_never_drops_an_attributed_finding
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
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