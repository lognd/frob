---
id: T-0610
title: 'arch: refactor python/cpp checks onto normalized model (no regression)'
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
- src/frob/arch/_python.py
- src/frob/arch/_normalized.py
- tests/unit/test_arch.py
- uv.lock
- pyproject.toml
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: uv.lock
  reason: 'merge-artifact: main merge touched uv.lock''s diff-vs-ticket-start range,
    though final content matches main''s tip (T-0431 precedent)'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: pyproject.toml
  reason: REL001 minor version bump for new public API (PythonAdapter, NormalizedFunction.max_nesting_depth/cyclomatic)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: REL001 minor version bump for new public API (PythonAdapter, NormalizedFunction.max_nesting_depth/cyclomatic)
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_arch.py::TestPythonAdapter::test_is_a_language_adapter
- tests/unit/test_arch.py::TestPythonAdapter::test_adapt_arch_python_fixture_shape
- tests/unit/test_arch.py::TestPythonAdapter::test_adapt_long_func_fixture_structural_events
- tests/unit/test_arch.py::TestPythonAdapter::test_adapt_deep_nest_fixture_nesting_depth
designated_repro_test: null
threat: null
component: null
---
Add a python-adapter (and cpp-adapter) mapping the existing tree-sitter walks onto the T-0609 normalized model, then re-point the existing arch checks (long-function, god-class, high-coupling, deep-nesting, abstraction-opportunity, large-file, T-0332 pattern recommender) to read from the normalized tree instead of raw tree-sitter nodes. Acceptance: existing test_arch.py suite passes unchanged (same suggestions on the same fixtures) proving zero regression; checks now take a normalized tree, not a language-specific one.