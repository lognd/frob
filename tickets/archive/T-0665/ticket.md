---
id: T-0665
title: 'vet/strata: fail-closed opaque-capability-indirection obligation for runtime-resolved
  dispatch'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0339
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/strata/**
- tests/test_vet.py
- src/frob/gates/**
- src/frob/check/__init__.py
- docs/design/registry/check-coverage.yaml
- docs/modules/gates.md
- docs/modules/vet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/**
  reason: T-0665 needs a new gate module (src/frob/gates/_opaque.py), its stage-group/dispatch
    wiring in src/frob/gates/__init__.py and src/frob/check/__init__.py, and its rule-catalog/registry
    entries in docs/modules/gates.md and check-coverage.yaml
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/check/__init__.py
  reason: T-0665 needs a new gate module (src/frob/gates/_opaque.py), its stage-group/dispatch
    wiring in src/frob/gates/__init__.py and src/frob/check/__init__.py, and its rule-catalog/registry
    entries in docs/modules/gates.md and check-coverage.yaml
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: T-0665 needs a new gate module (src/frob/gates/_opaque.py), its stage-group/dispatch
    wiring in src/frob/gates/__init__.py and src/frob/check/__init__.py, and its rule-catalog/registry
    entries in docs/modules/gates.md and check-coverage.yaml
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: T-0665 needs a new gate module (src/frob/gates/_opaque.py), its stage-group/dispatch
    wiring in src/frob/gates/__init__.py and src/frob/check/__init__.py, and its rule-catalog/registry
    entries in docs/modules/gates.md and check-coverage.yaml
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/vet.md
  reason: T-0665 also extends vet.md's public-api section with RUNTIME_OPAQUE_CONSTRUCTS/OPAQUE_SOURCE_INVISIBLE
    doc bullets
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_vet.py::TestOpaqueIndirectionGate::test_python_getattr_non_literal_name_fires
- tests/test_vet.py::TestOpaqueIndirectionGate::test_python_getattr_literal_name_does_not_fire
- tests/test_vet.py::TestOpaqueIndirectionGate::test_python_eval_always_fires_regardless_of_argument
- tests/test_vet.py::TestOpaqueIndirectionGate::test_python_import_module_non_literal_fires
- tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_dynamic_import_non_literal_specifier_fires
- tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_dynamic_import_literal_specifier_does_not_fire
- tests/test_vet.py::TestOpaqueIndirectionGate::test_c_dlsym_non_literal_symbol_fires
- tests/test_vet.py::TestOpaqueIndirectionGate::test_c_dlsym_literal_symbol_does_not_fire
- tests/test_vet.py::TestOpaqueIndirectionGate::test_kotlin_class_forname_always_fires
- tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_libloading_get_fires_only_when_file_uses_libloading
- tests/test_vet.py::TestOpaqueIndirectionGate::test_finding_inside_comment_span_does_not_fire
- tests/test_vet.py::TestOpaqueIndirectionGate::test_finding_inside_string_literal_does_not_fire
- tests/test_vet.py::TestOpaqueIndirectionGate::test_arg_looks_literal_rejects_fstring_interpolation
- tests/test_vet.py::TestOpaqueIndirectionGate::test_split_top_level_args_balances_nested_parens
- tests/test_vet.py::TestOpaqueIndirectionGate::test_split_top_level_args_returns_none_when_unterminated
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_emits_warn_severity_violation
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set
- tests/test_vet.py::TestOpaqueIndirectionGate::test_waived_finding_is_suppressed_and_reason_recorded
designated_repro_test: null
acceptance:
- text: Given code containing a spec-defined runtime-resolved indirection construct
    with no waiver, when checked, then the obligation fires
  evidence:
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_python_getattr_non_literal_name_fires
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_python_getattr_literal_name_does_not_fire
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_python_eval_always_fires_regardless_of_argument
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_python_import_module_non_literal_fires
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_dynamic_import_non_literal_specifier_fires
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_dynamic_import_literal_specifier_does_not_fire
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_c_dlsym_non_literal_symbol_fires
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_c_dlsym_literal_symbol_does_not_fire
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_kotlin_class_forname_always_fires
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_libloading_get_fires_only_when_file_uses_libloading
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_finding_inside_comment_span_does_not_fire
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_finding_inside_string_literal_does_not_fire
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_arg_looks_literal_rejects_fstring_interpolation
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_split_top_level_args_balances_nested_parens
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_split_top_level_args_returns_none_when_unterminated
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_emits_warn_severity_violation
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set
- text: Given the same construct with a reasoned waiver, when checked, then it passes
    and the waiver reason is recorded
  evidence:
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_waived_finding_is_suppressed_and_reason_recorded
threat: null
component: null
---
Per-language, every spec-defined runtime-resolved indirection construct (Python getattr/eval/importlib; TS dynamic import()/eval; Rust reflection-via-trait-object-from-data; C/C++ dlopen/dlsym/fn-ptr-from-data; Kotlin reflection API) becomes an 'opaque capability indirection' obligation: fires by default, requires a reasoned waiver (T-0174), never a silent pass. Consistent with strata's prove-or-reject philosophy (T-0290).