---
id: T-1906
title: 'post-land sweep regression from T-1900: 1 new error(s) (invalid-argument-type)'
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
- old_node: tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_empty_interface_one_line_form_is_not_read_as_a_name
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
- old_node: tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_round_trip_every_node_shape_reparses
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
- old_node: tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_rewrite_that_would_not_parse_is_refused
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
The deferred post-land unscoped sweep (T-1684) for T-1900 at commit 89cf432c34fcbf97cf8801cdf6b0ed3cc838de1b found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- invalid-argument-type  tests/unit/gates/test_sys_interface_canonical_order.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- invalid-argument-type  tests/unit/gates/test_sys_interface_canonical_order.py  -> attributed to T-1900 (commit 89cf432c34fc, already closed/dropped -- filed below) via tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.
frob:no-behavior-change reason="The diff is confined to three test call sites that passed bare None into fix_sys_interface_canonical_order's non-Optional snapshot parameter, swapping them for the _EMPTY_SNAPSHOT fixture already established in this same file by T-1896. The function's body does 'del snapshot' immediately -- the parameter exists only for Tier-A handler signature uniformity -- so None and _EMPTY_SNAPSHOT are observationally identical at runtime. No test can fail at the parent commit and pass at the fix; the proof is the ty gate reporting 'All checks passed!' on the touched file where it previously reported invalid-argument-type at three sites."

## Done report

Root cause: the same shape as T-1894/T-1896. `fix_sys_interface_canonical_order`
takes `root: Path, snapshot: GraphSnapshot` for Tier-A fix-handler signature
uniformity (the body never reads `snapshot` -- `del snapshot` right at the top,
it re-reads the design tree itself). T-1896 had already established the honest
fix for exactly this shape: a `_EMPTY_SNAPSHOT = GraphSnapshot(root="",
symbols={}, edges=())` fixture, satisfying the real declared (non-Optional)
type without changing what the handler under test does. T-1900 then added
three NEW test cases to this same file and reverted to passing bare `None`
for the same parameter, regressing the exact pattern T-1896 had fixed one
ticket ago in the same file.

Fix: replaced the three `None` call-site arguments (lines 135, 179, 207
pre-fix) with `_EMPTY_SNAPSHOT`, and folded the accidentally-doubled
`_EMPTY_SNAPSHOT` docstring-comment-block + assignment (an unrelated small
duplication in the same file, still in scope) into one, noting T-1906 in the
comment so a future edit to this file does not repeat the None regression a
third time.

No source change: this is a test-only, pure static-type fix with no
behavior difference (both `None` and `_EMPTY_SNAPSHOT` were already ignored
by the function body). No fail-then-pass runtime proof is possible for a
pure type-check fix -- see `frob:no-behavior-change` directive.

Confirmed `_iface_rewrite_parses` and `_IFACE_EMPTY_LINE_RE` from T-1900 were
NOT touched -- this fix is entirely inside the test file's call arguments and
its own duplicated comment/fixture block.

### Changed
```
 .../gates/test_sys_interface_canonical_order.py    | 22 +++++++---------------
 tickets/T-1906/ticket.md                           |  8 +++++++-
 2 files changed, 14 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_groups_by_kind_then_alpha` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_order_only_multiset_preserved_and_idempotent` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_empty_interface_one_line_form_is_not_read_as_a_name` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_round_trip_every_node_shape_reparses` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_rewrite_that_would_not_parse_is_refused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 2 error(s), 783 warning(s), 695 waived
- error-findings: PRE001@tickets/T-1906, REG002@docs/design/registry/check-coverage.yaml
