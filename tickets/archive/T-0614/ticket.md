---
id: T-0614
title: 'arch: Kotlin adapter for normalized code model'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0613
- T-0610
parent: T-0329
tier: ticket
sprint: null
scope:
- src/frob/lang/_walk_kotlin.py
- src/frob/arch/_normalized.py
- tests/unit/test_arch.py
- src/frob/arch/_kotlin.py
- pyproject.toml
- .frob-release.json
- uv.lock
- CHANGELOG.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_kotlin.py
  reason: own adapter module, mirroring T-0611/T-0612 placement precedent
  actor: logan
  at: '2026-07-22'
- op: add
  glob: pyproject.toml
  reason: REL001 minor version bump (0.88.0 -> 0.89.0) for the new public KotlinAdapter
    API
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: frob release stamp output for the version bump
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: lockfile re-resolved as a side effect of the pyproject.toml version bump
    (T-0610/T-0611/T-0612 precedent)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: CHANGELOG.md
  reason: REL001 version-bump changelog entry (T-0610/T-0611/T-0612 precedent)
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_arch.py::TestKotlinAdapter::test_is_a_language_adapter
- tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_imports
- tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_class_bases_fields_and_methods
- tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_data_class_constructor_properties
- tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_sealed_class_with_no_body
- tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_override_modifier
- tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_function_params_and_return_type
- tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_branches_loops_calls_field_accesses
- tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_method_chain_does_not_confuse_calls_with_field_accesses
- tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_when_entries_are_branches_and_loop_kinds
- tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_throw_and_catch
- tests/unit/test_arch.py::TestKotlinAdapter::test_adapt_stays_sane_on_realistic_snippet
- tests/unit/test_arch.py::TestSharedCheckOnPythonAndKotlin::test_long_complex_function_flags_identically_across_languages
designated_repro_test: null
threat: null
component: null
---
Implement the Kotlin adapter mapping tree-sitter-kotlin node types onto the T-0609 normalized model. Acceptance: a shared arch check written once against the model fires correctly on an equivalent Kotlin fixture, matching python/ts/rust fixture result shapes.