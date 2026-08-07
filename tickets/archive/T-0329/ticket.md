---
id: T-0329
title: 'EPIC arch multi-language: normalized code model + Rust/TypeScript/Kotlin adapters'
state: done
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: epic
sprint: null
scope:
- src/frob/arch/**
- src/frob/lang/**
- docs/modules/arch.md
- tickets.md
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_arch.py
  reason: T-0329 arch work maps to tests/unit/test_arch.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/unit/test_arch.py::TestNormalizedModel::test_hand_built_python_snippet_shape
- tests/unit/test_arch.py::TestSharedCheckOnPythonAndTypeScript::test_long_complex_function_flags_identically_across_languages
- tests/unit/test_arch.py::TestSharedCheckOnPythonAndRust::test_long_complex_function_flags_identically_across_languages
- tests/unit/test_arch.py::TestSharedCheckOnPythonAndKotlin::test_long_complex_function_flags_identically_across_languages
designated_repro_test: null
threat: null
component: null
---
frob arch today has per-language walkers (_python.py, _cpp.py) only. To extend cleanly (not N copies of each check), introduce a NORMALIZED CODE MODEL: a language-agnostic view (module, class, function, method, param, branch, loop, call, import, override, field-access, return, raise/throw, catch) that each language adapter maps its tree-sitter grammar onto. Checks are written ONCE against the model; adapters supply per-grammar node-type maps. Then add adapters for TypeScript, Rust, Kotlin (Kotlin needs tree-sitter-kotlin added to frob.lang; ts/rust/cpp/c already parse via tree-sitter-language-pack). Language-specific checks (Rust must_use/ownership, TS any/strict-null) live in per-language extensions on top of the shared model. Acceptance: an arch check written once fires correctly across python+ts+rust+kotlin on equivalent code; Kotlin grammar wired; the existing python/cpp checks refactored onto the model with no regression. Children: normalized-model, ts-adapter, rust-adapter, kotlin-grammar+adapter.