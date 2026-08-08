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
