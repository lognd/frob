---
id: T-1509
title: dup._legacy_cpp never collects C++ function params as locals (params field
  looked up on the wrong node)
state: done
kind: bug
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_legacy_cpp.py
- tests/unit/test_dup_legacy_cpp.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_dup_legacy_cpp.py
  reason: regression test for the params-collection fix lives in the existing test
    file for this module
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_covers_bindings
- tests/unit/test_dup_legacy_cpp.py::test_enclosing_class_cpp_none_for_top_level_function
- tests/unit/test_dup_legacy_cpp.py::test_enclosing_class_cpp_names_the_struct_or_class
- tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_method_params_too
- tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_param_folds_to_positional_token
- tests/unit/test_dup_legacy_cpp.py::test_serialize_cpp_body_normalizes_locals_strings_and_numbers
- tests/unit/test_dup_legacy_cpp.py::test_iter_functions_cpp_yields_qualified_names
designated_repro_test: null
threat: null
component: null
---
`frob.dup._legacy_cpp._collect_locals_cpp` calls `_child(func_node, "parameters")`
where `func_node` is the C++ `function_definition` node -- but tree-sitter's
cpp grammar puts the `parameters` field on the `function_declarator` child
(`func_node`'s `declarator` field), not on `function_definition` itself.
Verified directly: a real parse of `int f(int a, int* b, int& c) { ... }`
shows `child_by_field_name("parameters")` returns None on the
`function_definition` node.

Effect: C++ function parameters are NEVER added to `_collect_locals_cpp`'s
local-name set for the legacy dup scanner, so `_serialize_cpp_body` never
folds a parameter identifier to a positional `_vN` token the way it does
for every other local (loop bindings, plain declarations). Two C++
functions that are structurally identical except for parameter NAMES will
fail to fingerprint as clones under the legacy scanner -- a real
detection-quality gap, not just a coverage gap.

Fix: harvest `parameters` from `func_node`'s declarator (walk through
pointer/reference declarator wrapping the same way `_cpp_func_name`
already does) rather than from `func_node` directly.

Found while working T-1307 (TEST005 burn-down: src/frob/dup) -- writing a
real behavioral test for `_collect_locals_cpp` against a params-bearing
fixture surfaced this; not fixed here since T-1307's scope is tests, not
scanner correctness.