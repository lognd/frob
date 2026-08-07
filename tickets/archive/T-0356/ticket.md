---
id: T-0356
title: 'dup/_legacy_py: _harvest_with never collects with-as binding names (grammar
  mismatch)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_legacy_py.py
- tests/unit/test_dup_legacy_py.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_dup_legacy_py.py::test_collect_locals_py_covers_every_binding_shape
- tests/unit/test_dup_legacy_py.py::test_collect_locals_py_with_tuple_target
designated_repro_test: null
threat: null
component: null
---
Found while writing coverage tests for T-0160 batch 3. _harvest_with (src/frob/dup/_legacy_py.py) looks up child_by_field_name('alias') on with_item nodes, but the tree-sitter-python grammar in use here nests with_item under a with_clause and represents the bound name via an as_pattern/as_pattern_target child, not an 'alias' field -- item.child_by_field_name('alias') is always None. Net effect: 'with X as name:' binding names are never added to the alpha-rename local set for Python dup-fingerprinting, so 'with' bindings leak into the un-renamed token stream, potentially causing false-negative (missed) or false-positive (spurious) Type-2 clone matches whenever two fragments differ only in their with-target variable name. Verified interactively: with_item.child_by_field_name('alias') returns None for 'with open("f") as fh:'. Fix: walk with_item's as_pattern/as_pattern_target (or with_clause's with_item children) the same way _harvest_pattern already does for for-loop/assignment targets.