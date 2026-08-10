---
id: T-2066
title: OrphanedEvidenceDeletion land refusal misattributes a pre-existing main-history
  deletion to the landing branch
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Attempting to land T-1959 (`fix(gates): DEAD001 recurses into with/async-with
bodies for constant-fold`, 2 files: `src/frob/gates/_dead_symbols.py`,
`tests/test_gates.py`) refuses with:

```
ERROR: land: T-1959 branch deletes or renames test node(s) bound as
evidence on T-1579, which no longer resolve:
['tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_with_live_finding_elsewhere_proceeds']
ERROR: ticket land failed: OrphanedEvidenceDeletion: this branch's own
committed changes delete or rename a pytest test node bound as evidence
on a DIFFERENT ticket...
```

This is a false attribution. That test node was deleted by commit
`7597ba37a` (`revert(gates): T-1579 WAIVE004 self-heal escape deleted 55
live waivers`), already on `main` long before this worktree's base --
verified via `git log --oneline --all -S"test_mass_invalidation_with_live_finding_elsewhere_proceeds"
-- tests/test_gates.py`, one hit, `7597ba37a`, not present in T-1959's
own diff at all (`grep -n ... tests/test_gates.py` at the T-1959 branch
tip: zero hits, meaning the test was already gone before T-1959 ever
touched the file). T-1959's own diff only ADDS two new tests to
`TestDeadSymbolGate`; it never touches `TestWaive004DegradedRunGuard`.

T-1579 itself is `dropped` ("the work as specified should NOT be done"),
not an open ticket -- its own Done report documents that the escape it
asked for was implemented once, found unsound (deleted 55 live
waivers), and reverted, and that the reverting commit added a LOCKING
regression test (implying the mass-invalidation guard tests were
deliberately renamed/restructured as part of that revert, not lost).

Reproduced twice (git-merge-main retried in between, same refusal both
times) -- this is not a transient race. The `OrphanedEvidenceDeletion`
check appears to attribute a deletion to whichever branch happens to
land next, regardless of whether that branch's own diff touched the
file at all, when the deleting commit is already baked into main and a
dropped ticket's stale evidence citation is still checked as if live.

Filed rather than worked around: the fix (scoping the check to lines the
landing branch's OWN diff actually touches, and/or skipping evidence
citations on `dropped` tickets) is outside T-1959's scope
(`src/frob/gates/_dead_symbols.py`, `tests/test_gates.py`) and touches
land-internal machinery T-1959 has no lease over.
