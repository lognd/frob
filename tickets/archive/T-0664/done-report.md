## Done report

Lands the first import/alias-aware capability resolver for kotlin
(capability-evasion-taxonomy.md's Kotlin table), covering the ticket's
three named deliverables: import-as, ::-callable-reference, and
typealias (verified the latter needs no new code -- the type annotation
is a different child than the value, same finding T-0663 made for C++'s
using-alias). Uses a flat file-wide alias table (no per-scope shadow
discipline like the C/rust resolvers), a disclosed reduced-fidelity
scope cut given the ticket's time budget; a follow-up tightening this to
per-function scoping is a natural next step, not attempted here. Round 2
added 6 mutation-kill predicate tests (import table dispatch, property
name/value extraction) closing coverage gaps from the first pass. All 21
acceptance tests pass foreground; gates-native/security/fast/lint/static
all clean against a fresh merge of main and from-scratch natives build;
deletion filter against main is empty.

### Changed
(no changed files detected)

### Evidence
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_plain_import_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_bare_constructor_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_bare_callable_reference_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typed_callable_reference_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typealias_for_function_type_needs_no_special_resolution` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_chained_val_alias_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_curated_wildcard_import_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_uncurated_wildcard_import_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_unaliased_bare_reference_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_rejects_non_identifier_member` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_typed_falls_back_to_literal_receiver` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_returns_none_for_unbound_identifier` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_call_expression_wraps_with_parens` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_kt_call_callee_picks_last_non_call_suffix_child` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_plain_import_binds_last_segment` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_as_alias_binds_alias_name` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_curated_wildcard_recorded` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_uncurated_wildcard_not_recorded` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_returns_none_none_without_variable_declaration` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_extracts_name_and_value` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 21 passed (from 21 evidence id(s))
- gates: 0 error(s), 2889 warning(s), 339 waived
- error-findings: none (measured, zero errors)
