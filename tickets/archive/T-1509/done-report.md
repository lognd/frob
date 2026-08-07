## Done report

Fixed the real detection-quality bug: `_collect_locals_cpp` looked up the
`parameters` field on `func_node` (`function_definition`) directly, but
tree-sitter's cpp grammar puts that field on the function's
`function_declarator` child instead (`func_node`'s `declarator` field).
Verified directly against a real parse of `int f(int a, int* b, int& c)
{ ... }` before the fix: `child_by_field_name("parameters")` returned
`None` on the `function_definition` node.

Fix: `_cpp_function_declarator` unwraps any pointer/reference declarator
wrapping (mirroring `_cpp_func_name`'s existing unwrap) to reach the real
`function_declarator` node, then `_collect_locals_cpp` reads
`parameters` off THAT node.

While writing the regression test for a reference parameter (`int& c`),
found and fixed a second, related bug in the same file:
`_harvest_cpp_declarator_name`'s `reference_declarator` branch assumed
`child_by_field_name("declarator")` would find the wrapped identifier the
same way it does for `pointer_declarator` -- verified this tree-sitter-cpp
grammar version does NOT label `reference_declarator`'s identifier child
with a `declarator` field (only `pointer_declarator` does), so a `None`
field lookup silently dropped reference parameters even after the params
field fix above. Falls back to iterating `named_children` when the field
lookup misses -- a no-op for `pointer_declarator` (whose lookup already
succeeds), and correctly reaches the identifier for
`reference_declarator`. Both fixes are in this ticket's declared scope
(src/frob/dup/_legacy_cpp.py).

Added tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_method_params_too
(a class method's plain params are collected too, not just free-function
pointer/reference ones) and
::test_collect_locals_cpp_param_folds_to_positional_token (the real
detection-quality assertion: two functions identical except for
parameter NAMES now fingerprint identically via
`_serialize_cpp_body`'s positional `_vN` folding -- they did not before
this fix). Updated the existing
::test_collect_locals_cpp_covers_bindings to assert params ARE now
collected (it previously documented the bug as expected behavior).

Ticket scope was `src/frob/dup/_legacy_cpp.py` only; narrowed-added
`tests/unit/test_dup_legacy_cpp.py` via `frob ticket scope --add` since
the regression test lives in the module's existing test file.

`frob check --only test --ticket T-1509`: 0 errors, 8 pre-existing
warnings unrelated to this ticket's scope, 3 waived.
`frob check --land-parity`: clean -- 0 unscoped errors.
`pytest tests/unit/test_dup_legacy_cpp.py`: 7/7 passed.
`ruff check`/`ruff format`: clean.

Filed: none.

### Changed
```
 design/frob.strata                            |   4 +-
 src/frob/dup/_legacy_cpp.py                   |  47 +-
 tests/unit/test_check.py                      | 476 ++++++++++++++++-
 tests/unit/test_check_native_cargo_runners.py | 530 ++++++++++++++++++-
 tests/unit/test_dup_legacy_cpp.py             |  83 ++-
 tickets.md                                    | 705 +++++++++++++++++++++++++-
 6 files changed, 1801 insertions(+), 44 deletions(-)
```

### Evidence
- `tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_covers_bindings` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_legacy_cpp.py::test_enclosing_class_cpp_none_for_top_level_function` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_legacy_cpp.py::test_enclosing_class_cpp_names_the_struct_or_class` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_method_params_too` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_param_folds_to_positional_token` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_legacy_cpp.py::test_serialize_cpp_body_normalizes_locals_strings_and_numbers` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_legacy_cpp.py::test_iter_functions_cpp_yields_qualified_names` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
