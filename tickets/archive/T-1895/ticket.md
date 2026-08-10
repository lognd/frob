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
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_groups_by_kind_then_alpha
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_order_only_multiset_preserved_and_idempotent
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_round_trip_every_node_shape_reparses
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_rewrite_that_would_not_parse_is_refused
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1872's fix_sys_interface_canonical_order needed its own _iface_node_body_span, a byte-identical brace-depth node-body scanner to _sync_may.py::_node_body_span (both independently mirror the deleted _sync_interface.py's own copy). DUP001 waived in T-1872 rather than fixed, since extracting a shared helper module both files import from is a real refactor outside that order-only ticket's declared scope. Extract the shared scanner into one home (e.g. frob.strata._strata_text or similar) and have both call sites use it.