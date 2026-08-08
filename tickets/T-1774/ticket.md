---
id: T-1774
title: TestFixEngineTierA::test_sys104_interface_union_applies_via_apply_tier_a_fixes
  fails on clean main
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_sync.py
- src/frob/strata/_sync_interface.py
- tests/test_gates.py
- tickets/T-1774/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: fix a stale-fixture test assertion (T-1625's cross-node-reference narrowing
    changed what SYS104 requires; no production code changed)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1774/ticket.md
  reason: v2 ledger per-ticket file; LEDGER_PATH's implicit-scope rule only covers
    legacy tickets.md
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_sys104_interface_union_applies_via_apply_tier_a_fixes
designated_repro_test: null
threat: null
component: null
---
tests/test_gates.py::TestFixEngineTierA::test_sys104_interface_union_applies_via_apply_tier_a_fixes fails on a clean main checkout (identical test body copied from git show main:tests/test_gates.py, run against a freshly-built natives checkout): expects sync_interface_report(root, 'design') to report has_drift=True for a node with a public_fn symbol and no attr interface=[] line, and apply_tier_a_fixes to insert one SYS104 fix. Currently 0 fixes are applied. Reproduced in isolation, not a parallelism/xdist artifact, not a pyproject.toml version-fingerprint artifact (retested after pyproject.toml read 0.367.0 matching main). Not caused by T-1763 (INV006/AFFECT001/DUP001 work) -- this touches frob.strata._sync_interface's own SYS104 drift detection, unrelated subsystem. Root-cause and fix, or determine which recent strata/sync-interface change (T-1440/T-1627 via-grammar work is one candidate given the timing) altered has_drift's behavior for a node with no attr interface= line at all.