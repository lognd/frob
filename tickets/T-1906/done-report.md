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
