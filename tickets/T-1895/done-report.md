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
