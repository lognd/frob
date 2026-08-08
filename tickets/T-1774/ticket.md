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

## Done report

Not a production defect: T-1625 (already landed, unrelated to this
ticket) legitimately narrowed SYS104's REQUIRED interface surface to
`real AND cross-node-referenced` symbols
(`_selfconform._cross_node_referenced_symbols`) -- a node's own real
public surface alone no longer implies it needs an `interface=`
declaration; some file owned by a DIFFERENT node must import the symbol
BY NAME first. The failing fixture
(`tests/test_gates.py::TestFixEngineTierA::test_sys104_interface_union_applies_via_apply_tier_a_fixes`)
declared only the ONE node whose public symbol it expected to be
flagged, so under the current (correct) narrower semantics nothing was
ever required and `apply_tier_a_fixes` legitimately applied zero SYS104
fixes -- the test's own fixture had gone stale against a real, intended
behavior change, not a regression in `_fix_engine_sync.py` or
`_sync_interface.py` (both files in this ticket's original scope are
unmodified; confirmed no production code needed a change).

Fixed the fixture to match `tests/unit/strata/test_sync_interface.py`'s
own T-1625 pattern: added a `consumer` node whose file does `from
widget._io import public_fn`, so `public_fn` is now genuinely
cross-node-referenced and SYS104's fix engine flags/fixes it as before.

Root cause confirmed by reading `_sync_one_file`
(`src/frob/strata/_sync_interface.py:377`, `required = real &
cross_referenced.get(node_id, frozenset())`) and
`_interface_conformance_violations`
(`src/frob/strata/_selfconform.py:1349`), both consulting the SAME
`_cross_node_referenced_symbols` join the fix-engine handler
(`fix_sys104_interface_union`) delegates to via `sync_interface_report`.

### Changed
```
 tickets/T-1774/ticket.md | 17 ++++++++++++++++-
 1 file changed, 16 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 1240 warning(s), 731 waived
- error-findings: none (measured, zero errors)
