---
id: T-0611
title: 'arch: TypeScript adapter for normalized code model'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0329
tier: ticket
sprint: null
scope:
- src/frob/lang/_walk_typescript.py
- src/frob/arch/_normalized.py
- tests/unit/test_arch.py
- pyproject.toml
- .frob-release.json
- uv.lock
- src/frob/arch/_typescript.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: pyproject.toml
  reason: REL001 minor version bump for new public API (TypeScriptAdapter and TS-adapter
    build helpers in frob.arch._normalized)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: REL001 minor version bump for new public API (TypeScriptAdapter and TS-adapter
    build helpers in frob.arch._normalized)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: REL001 minor version bump for new public API (TypeScriptAdapter and TS-adapter
    build helpers in frob.arch._normalized)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/arch/_typescript.py
  reason: 'reviewer-required placement fix: TypeScriptAdapter moved out of the pure,
    tree_sitter-free _normalized.py model module into its own file mirroring _python.py''s
    placement'
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_is_a_language_adapter
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_imports
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_class_bases_and_fields
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_function_params_and_return_type
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_arrow_function_bound_to_const
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_branches_loops_calls_field_accesses
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_for_of_and_ternary
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_raise_and_catch
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_override_modifier
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_constructor_is_a_method
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_export_wrapped_declarations
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_stays_sane_on_realistic_snippet
- tests/unit/test_arch.py::TestSharedCheckOnPythonAndTypeScript::test_long_complex_function_flags_identically_across_languages
designated_repro_test: null
threat: null
component: null
---
Implement the TS adapter mapping tree-sitter-typescript node types onto the T-0609 normalized model (functions, classes, methods, arrow fns, imports/exports, try/catch, throw). Acceptance: a shared arch check (e.g. long-function or god-class) written once against the model fires correctly on an equivalent TS fixture, matching the python fixture's result shape.