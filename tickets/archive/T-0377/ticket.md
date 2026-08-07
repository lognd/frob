---
id: T-0377
title: 'vet: TypeScript/JS binding-aware capability resolution'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_default_import_alias_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_require_bare_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_require_destructure_rename_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_namespace_import_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_ts_import_require_clause_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_operation_names_registry_entry_for_aliased_import
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_param_named_get_not_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_param_shadowing_import_not_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_method_on_unrelated_object_not_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_bare_name_call_with_no_import_not_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_direct_unaliased_call_still_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_bracket_access_inline_require_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_bracket_access_aliased_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_dynamic_import_then_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_await_dynamic_import_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_child_process_bracket_and_dynamic_import_caught
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_computed_subscript_not_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_static_template_literal_subscript_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_interpolated_template_subscript_not_detected
designated_repro_test: null
threat: null
component: null
---
Extend scan_file_capabilities/_scan_file_operations binding-aware resolution (currently Python-only, T-0328/T-0337) to TypeScript/JS: resolve ES import/require/destructure/alias bindings and scope-shadowing using the existing tree-sitter parse, mirroring the Python import-table/alias-copy-propagation/scope-bound-names discipline. Acceptance: an aliased import like `import {run} from 'child_process'` (renamed binding) is still flagged, while a locally-shadowed identifier of the same name is NOT flagged; adversarial tests added for both cases.