---
id: T-1895
title: Extract shared .strata node-body brace-depth scanner (SYS-IFACE-ORDER/_sync_may
  duplicate)
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_sync.py
- src/frob/strata/_sync_may.py
- tests/unit/strata/test_sync_may.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_sync_may.py
  reason: T-1895's node_body_span extraction added direct unit tests for the newly-public
    scanner in its existing test file
  actor: logan
  at: '2026-08-09'
evidence:
- tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_flat_body_returns_closing_brace_line
- tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_nested_braces_do_not_close_early
- tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_malformed_input_returns_last_line_best_effort
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
T-1872's fix_sys_interface_canonical_order needed its own _iface_node_body_span, a byte-identical brace-depth node-body scanner to _sync_may.py::_node_body_span (both independently mirror the deleted _sync_interface.py's own copy). DUP001 waived in T-1872 rather than fixed, since extracting a shared helper module both files import from is a real refactor outside that order-only ticket's declared scope. Extract the shared scanner into one home (e.g. frob.strata._strata_text or similar) and have both call sites use it.

## Done report

Changed:
- src/frob/strata/_sync_may.py::node_body_span (renamed from private
  `_node_body_span`, made public, docstring updated, `frob:tests` edges
  added; module docstring updated to reflect T-1895's extraction and
  drop the stale "inlined as private, single-importer" claim)
- src/frob/gates/_fix_engine_sync.py::_reorder_node_interface_block
  (removed the duplicate `_iface_node_body_span` function and its
  `frob:waive DUP001`; now does a lazy
  `from frob.strata._sync_may import node_body_span` and calls that)
- tests/unit/strata/test_sync_may.py::TestNodeBodySpan (new: three unit
  tests directly covering the shared scanner's flat/nested/malformed
  cases)

Evidence:
- tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_flat_body_returns_closing_brace_line
- tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_nested_braces_do_not_close_early
- tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_malformed_input_returns_last_line_best_effort
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_groups_by_kind_then_alpha
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_order_only_multiset_preserved_and_idempotent
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_round_trip_every_node_shape_reparses
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_rewrite_that_would_not_parse_is_refused
(all 5 SYS-interface-order tests plus the new sync_may tests pass
in full; T-1900's regression lock, the empty-interface re-parse guard,
and `_IFACE_EMPTY_LINE_RE` handling are untouched by this extraction.)

Filed: none

Gates: `frob check --ticket T-1895 --only prework --only test --only
registry --only dup` clean for gate:PRE, gate:TEST, frob-dup; gate:REG's
one error (CHK-GATE-SYS-IFACE-ORDER dangling registry reference) is
pre-existing repo-wide debt in docs/design/registry/check-coverage.yaml,
outside this ticket's scope and untouched by this change (confirmed via
git log on that file -- last touched by T-1877's land, unrelated).
DUP001's waiver on `_iface_node_body_span` is gone because the function
itself is gone; the `frob-dup` tool run above reports the codebase's dup
groups with no new hit on `_sync_may.py`/`_fix_engine_sync.py`.

Addendum: added `# frob:ticket T-1895` on the new test class/methods
(COV002), a `# frob:waive COV001` on `node_body_span` (a frob:doc anchor
would live in docs/modules/gates.md, out of this two-file ticket's scope
and under a live T-1579 lease at the time -- same precedent as
`_rule_id_scan.py::SCANNED_BASES`'s own COV001 waiver), and added
`tests/unit/strata/test_sync_may.py` to the ticket's declared scope
(the new direct unit tests live there). Remaining `frob check --ticket
T-1895` errors after these fixes: 3 pre-existing `ty` invalid-argument-type
findings in tests/unit/gates/test_sys_interface_canonical_order.py
(already tracked/landed via T-1896's post-land sweep regression, git log
confirms, untouched by this ticket) and the one pre-existing REG002
dangling-registry-reference finding noted above. Both out of scope and
pre-existing.

### Changed
```
 tickets/T-1895/done-report.md | 58 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1895/ticket.md      | 18 +++++++++++++-
 2 files changed, 75 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_flat_body_returns_closing_brace_line` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_nested_braces_do_not_close_early` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_malformed_input_returns_last_line_best_effort` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_groups_by_kind_then_alpha` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_order_only_multiset_preserved_and_idempotent` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_round_trip_every_node_shape_reparses` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_rewrite_that_would_not_parse_is_refused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 2 error(s), 854 warning(s), 695 waived
- error-findings: REG002@docs/design/registry/check-coverage.yaml, invalid-argument-type@tests/unit/gates/test_sys_interface_canonical_order.py
