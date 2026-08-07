---
id: T-0612
title: 'arch: Rust adapter for normalized code model'
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
- src/frob/lang/_walk_rust.py
- src/frob/arch/_normalized.py
- tests/unit/test_arch.py
- src/frob/arch/_rust.py
- pyproject.toml
- .frob-release.json
- CHANGELOG.md
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_rust.py
  reason: adapter placed in its own module per T-0611 review precedent, mirroring
    _typescript.py
  actor: logan
  at: '2026-07-22'
- op: add
  glob: pyproject.toml
  reason: REL001 minor version bump for new public RustAdapter API
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: REL001 minor version bump for new public RustAdapter API
  actor: logan
  at: '2026-07-22'
- op: add
  glob: CHANGELOG.md
  reason: REL001 minor version bump for new public RustAdapter API
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: uv.lock version pin updated by pyproject.toml's REL001 bump
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_arch.py::TestRustAdapter::test_is_a_language_adapter
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_imports
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_struct_named_and_tuple_fields
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_enum_variants_as_fields
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_function_params_and_return_type
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_trait_methods_and_impl_attach
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_trait_impl_notes_trait_as_base_and_sets_overrides
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_branches_loops_calls_field_accesses
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_method_chain_does_not_confuse_calls_with_field_accesses
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_match_arms_are_branches_and_loop_kinds
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_panic_macro_and_unwrap_expect_are_raises
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_err_return_and_try_operator_are_raises
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_result_match_err_arm_is_a_catch
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_stays_sane_on_realistic_snippet
- tests/unit/test_arch.py::TestSharedCheckOnPythonAndRust::test_long_complex_function_flags_identically_across_languages
designated_repro_test: null
threat: null
component: null
---
Implement the Rust adapter mapping tree-sitter-rust node types onto the T-0609 normalized model (fn, impl/trait methods, match arms as branches, loop, use as import, Result-returning fns, panic!/unwrap as raise-equivalent). Acceptance: a shared arch check written once against the model fires correctly on an equivalent Rust fixture.