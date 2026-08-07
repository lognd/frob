## Done report

Landed C static-binding resolver (#define macro alias, fn-ptr var init,
typedef'd fn-ptr, assignment/struct-field/array-element fn-ptr binding).
Two pre-existing helper gaps (_c_declared_name's missing
parenthesized_declarator fallback, _c_collect_declaration_names missing
the uninitialized fn-ptr declarator shape) fixed alongside the new
resolver code since neither could work without them. Round 2 added
8 mutation-kill predicate tests (_c_declared_name, _c_collect_
declaration_names) closing coverage gaps left from the first pass,
verified against a fresh merge of main and a from-scratch natives build.
All 25 acceptance tests pass foreground; deletion filter against main is
empty.

### Changed
```
 docs/modules/vet.md         |   5 +-
 src/frob/vet/_capability.py | 944 +++++++++++++++++++++++++++++++++++++++++--
 tests/test_vet.py           | 960 ++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                  | 791 +++++++++++++++++++++++++++++-------
 4 files changed, 2508 insertions(+), 192 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_typedef_fn_ptr_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_address_of_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_bare_name_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_struct_field_static_init_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_constant_index_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_nonconstant_index_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_chained_var_alias_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_param_shadowing_var_alias_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_unaliased_local_shadow_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_unwraps_address_of` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_address_of` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_non_pointer` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_via_macro_table` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_record_field_alias_skips_non_field_designator` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_rejects_non_constant_field_type` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_subscript_non_number_index` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_none_node` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_direct_identifier` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_walks_declarator_field_to_identifier` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_parenthesized_declarator_fallback` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_abstract_declarator` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_bare_identifier` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_init_declarator` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_uninitialized_fn_ptr` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 25 passed (from 25 evidence id(s))
- gates: 0 error(s), 4539 warning(s), 359 waived
- error-findings: none (measured, zero errors)
