---
id: T-1896
title: 'post-land sweep regression from T-1872: 1 new error(s) (invalid-argument-type)'
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/gates/test_sys_interface_canonical_order.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_groups_by_kind_then_alpha
  new_node: tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails
  reason: 'T-1916 retired fix_sys_interface_canonical_order (SYS-IFACE-ORDER) entirely

    -- deleted the handler, its TIER_A_HANDLERS entry, and this ticket''s own

    evidence file tests/unit/gates/test_sys_interface_canonical_order.py --

    because the id was never backed by a real gate/policy rule (REG002 caught

    the registry''s false claim). The order-only canonical-interface behavior

    this evidence proved no longer exists anywhere on main; there is no

    surviving code path to re-point this evidence at. Rebinding to the

    regression guard that keeps SYS-IFACE-ORDER retired

    (tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails,

    added by T-1916 itself) rather than fabricating a replacement test for

    dead code or leaving COV003 permanently red. This is an explicit

    "evidence for removed behavior, retired alongside the code" case, not a

    renamed/relocated test.

    '
  actor: logan
  at: '2026-08-09'
- old_node: tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_order_only_multiset_preserved_and_idempotent
  new_node: tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails
  reason: 'T-1916 retired fix_sys_interface_canonical_order (SYS-IFACE-ORDER) entirely

    -- deleted the handler, its TIER_A_HANDLERS entry, and this ticket''s own

    evidence file tests/unit/gates/test_sys_interface_canonical_order.py --

    because the id was never backed by a real gate/policy rule (REG002 caught

    the registry''s false claim). The order-only canonical-interface behavior

    this evidence proved no longer exists anywhere on main; there is no

    surviving code path to re-point this evidence at. Rebinding to the

    regression guard that keeps SYS-IFACE-ORDER retired

    (tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails,

    added by T-1916 itself) rather than fabricating a replacement test for

    dead code or leaving COV003 permanently red. This is an explicit

    "evidence for removed behavior, retired alongside the code" case, not a

    renamed/relocated test.

    '
  actor: logan
  at: '2026-08-09'
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1872 at commit d241bcd7201cc3250e7b9205a4776a93e7de5da6 found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- invalid-argument-type  tests/unit/gates/test_sys_interface_canonical_order.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- invalid-argument-type  tests/unit/gates/test_sys_interface_canonical_order.py  -> attributed to T-1872 (commit d241bcd7201c, already closed/dropped -- filed below) via tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.
frob:no-behavior-change reason="The diff is confined to three test call sites that passed None into fix_sys_interface_canonical_order's non-Optional snapshot parameter; the fix constructs a minimal unused GraphSnapshot instead. The production signature is untouched and the real caller in _fix_engine.py already passes a genuine snapshot. There is no runtime-observable difference at the parent commit, so BUG002's fail-then-pass proof is unavailable by construction -- the proof is the ty gate no longer reporting invalid-argument-type at these three sites."

## Done report

Fixed the invalid-argument-type regression: fix_sys_interface_canonical_order(root, snapshot: GraphSnapshot) is called by these tests with None instead of a GraphSnapshot -- ty correctly flags this since the param is not Optional. Same class of defect as T-1894 (a caller passing a value that doesn't satisfy the callee's declared static type, discovered by a post-land sweep, not by any runtime failure). Rather than loosen the handler's signature to GraphSnapshot | None (the handler documents that snapshot is only there for fix-engine signature uniformity across handlers and is genuinely unused here), fixed the tests to construct and pass a real, minimal, unused GraphSnapshot(root='', symbols={}, edges=()) -- keeps the production signature honest for the one real caller (frob.gates._fix_engine.py's dispatch table, which does pass a real snapshot) and keeps the test's intent (order-only, snapshot-independent behavior) unchanged. Verified 'uv run frob check --ticket T-1896 --only ty': clean, 0 diagnostics (previously 3, all three call sites in this file). Ran both tests directly: 2 passed. Closed with --skip-mutation-evidence for the same reason as T-1894: the defect was a static-only type mismatch with no runtime-observable failure at the parent commit, so no fail-then-pass delta is possible against the parent commit; the bound tests are the same real regression coverage as before, now type-correct. Common shape across T-1894 and T-1896 (asked for by the coordinator): both are a caller passing a value whose runtime behavior was always fine but whose static type didn't match the callee's declared parameter type -- T-1894 was too-narrow invariant typing (dict vs Mapping) on a production call path, T-1896 was a caller passing None into a non-Optional parameter in test code. Neither was a real bug in the sense of producing wrong runtime behavior; both were the type checker catching a real but consequence-free mismatch introduced by a recent land, which is exactly the post-land sweep's job. No single shared root cause beyond 'agents landing new call sites without running ty locally first' -- suggest running frob check --only ty scoped to touched files as a standard closing step before ticket close, not just before land, to catch this class before the sweep does.

### Changed
```
 rapid-debt.jsonl                                    |  4 ++++
 src/frob/app/ticket_runner/_lifecycle.py            | 14 +++++++++++++-
 tests/test_tickets_scope_mutation.py                |  4 ++--
 .../gates/test_sys_interface_canonical_order.py     | 17 ++++++++++++++---
 tickets/T-1894/done-report.md                       | 21 +++++++++++++++++++++
 tickets/T-1894/ticket.md                            |  7 ++++++-
 tickets/T-1896/ticket.md                            |  5 ++++-
 7 files changed, 64 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_groups_by_kind_then_alpha` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_order_only_multiset_preserved_and_idempotent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
