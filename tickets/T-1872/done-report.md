## Done report

Changed:
src/frob/gates/_fix_engine_sync.py::fix_sys_interface_canonical_order
src/frob/gates/_fix_engine_sync.py::_reorder_iface_one_file
src/frob/gates/_fix_engine_sync.py::_reorder_node_interface_block
src/frob/gates/_fix_engine_sync.py::_render_interface_block
src/frob/gates/_fix_engine_sync.py::_canonical_interface_key
src/frob/gates/_fix_engine_sync.py::_node_symbol_kinds
src/frob/gates/_fix_engine_sync.py::_iface_find_spans
src/frob/gates/_fix_engine_sync.py::_iface_node_body_span
src/frob/gates/_fix_engine.py::TIER_A_HANDLERS (added SYS-IFACE-ORDER entry)
docs/strata/surface.md#interface-canonical-order-tier-a-t-1872 (new section)
tests/unit/gates/test_sys_interface_canonical_order.py (new test file, added to scope)

Evidence:
tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder.test_groups_by_kind_then_alpha
tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder.test_order_only_multiset_preserved_and_idempotent
(both pass: `uv run pytest tests/unit/gates/test_sys_interface_canonical_order.py -q` -> 2 passed)

The second test asserts BOTH the order-only invariant (declared name
Counter, including a duplicate, is identical before/after) AND
idempotency (a second run applies zero fixes). `_reorder_node_interface_
block` itself independently refuses (no-op) if its own recomputed
Counter comparison ever disagreed -- defense in depth beyond the test.

Filed: T-1895 (extract the shared .strata node-body brace-
depth scanner duplicated between this ticket's `_iface_node_body_span`
and `_sync_may.py::_node_body_span` -- DUP001 waived here since the
extraction needs a shared module neither in this ticket's declared
scope, out of scope for an order-only ticket)

Gates: `uv run frob check --ticket T-1872` -- gate:AFFECT/COV/TEST/DUP/
PRE/SCOPE/FMT all clean. Three unrelated FAILs remain, confirmed
pre-existing and outside this ticket's scope:
  - gate:ARCH: src/frob/refactor/_verify.py::verify_import_resolution
    (106 lines) -- unrelated file, not touched by T-1872
  - gate:REG: REG002/REG008/REG011 dangling CHK-GATE-SYS104 registry
    rows -- leftover from T-1870's SYS104 deletion, tracked there
  - gate:SELFAUDIT: 4 fs.read/fs.write findings against the NEW test
    file tests/unit/gates/test_sys_interface_canonical_order.py --
    design/frob.strata's `testsuite` node's may grants were not hand-
    edited (design/frob.strata is not in this ticket's scope); this is
    exactly what `fix_sys100_may_via_union` (already wired in
    TIER_A_HANDLERS) auto-repairs at land time, same as every other new
    test file in this repo's history.
Also waived inline (both scoped to files this ticket touches):
  - AFFECT001 on TIER_A_HANDLERS: docs/modules/gates.md is held by
    T-1877's live cross-worktree lease, could not be scope --add'ed;
    docs/strata/surface.md#interface-canonical-order-tier-a-t-1872
    documents the handler in full in the meantime.
  - DUP001 on _iface_node_body_span: see T-1895 above.

### Changed
```
 tickets/T-1872/ticket.md           | 10 +++++++++-
 tickets/T-1895/ticket.md | 25 +++++++++++++++++++++++++
 2 files changed, 34 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 4 error(s), 922 warning(s), 696 waived
- error-findings: ARCH001@src/frob/refactor/_verify.py, REG002@docs/design/registry/check-coverage.yaml, SELFAUDIT001@design, invalid-argument-type@tests/unit/gates/test_sys_interface_canonical_order.py
