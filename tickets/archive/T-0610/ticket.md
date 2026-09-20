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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_python.py
- src/frob/arch/_normalized.py
- tests/unit/test_arch.py
- uv.lock
- pyproject.toml
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
body_changes:
- mode: append
  reason: condense NormalizedModule migration history into T-0610 body
  actor: logan
  at: '2026-09-19'
  old_length: 524
  new_length: 2725
evidence:
- tests/unit/arch_suite/test_lang_adapters.py::TestPythonAdapter::test_is_a_language_adapter
- tests/unit/arch_suite/test_lang_adapters.py::TestPythonAdapter::test_adapt_arch_python_fixture_shape
- tests/unit/arch_suite/test_lang_adapters.py::TestPythonAdapter::test_adapt_long_func_fixture_structural_events
- tests/unit/arch_suite/test_lang_adapters.py::TestPythonAdapter::test_adapt_deep_nest_fixture_nesting_depth
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add a python-adapter (and cpp-adapter) mapping the existing tree-sitter walks onto the T-0609 normalized model, then re-point the existing arch checks (long-function, god-class, high-coupling, deep-nesting, abstraction-opportunity, large-file, T-0332 pattern recommender) to read from the normalized tree instead of raw tree-sitter nodes. Acceptance: existing test_arch.py suite passes unchanged (same suggestions on the same fixtures) proving zero regression; checks now take a normalized tree, not a language-specific one.

<!-- narrative-moved:src/frob/arch/_python.py:370:T-0610 -->
---------------------------------------------------------------------------
T-0610: python `LanguageAdapter` -- maps this module's tree-sitter walks
onto the T-0609 `NormalizedModule` shape, and the checks migrated to
consume it (long-function, god-class, deep-nesting).

T-0632: `NormalizedCall` now also carries per-argument position/keyword +
bare-identifier detail (`NormalizedCall.args`, `_py_call_args`), and
`_extract_signatures` is migrated onto `NormalizedModule` for its
name/param-types/return-type fields (see its own docstring for the one
piece -- body-fingerprinting -- that stays raw-AST-based by reasoned
decision, not oversight).

`_collect_file_dispatch_refs`/`_collect_dispatch_refs` (abstraction-
opportunity's cross-file dispatch-family corpus) stay on the raw tree-
sitter walk, by the same kind of reasoned decision: dispatch detection
needs every dict/list/set-literal element and every call argument
ANYWHERE in the file -- module-level statements and class-body
expressions included, not just inside a function/method body.
`NormalizedModule` deliberately only models classes/functions/imports
(T-0609's scope), with no top-level-statement or literal-expression
projection at all; `_py_collect_body_events` (which DOES walk function
bodies) also does not walk into container literals that are not call
arguments (a bare `TABLE = {"a": handler}` module constant, for
instance) because no current check needs that generality outside
dispatch detection. Re-deriving a NormalizedModule shape general enough
to carry arbitrary whole-file container literals would mean modeling
nearly the entire expression grammar on the shared model for this one
consumer -- not migrating a raw walk, but rebuilding it as normalized
events one-for-one. `_collect_dispatch_refs` remains the single, already
cohesive recursive walk it was before (T-0360); `NormalizedCall.args`
added here is available for any FUTURE detector that only needs
call-argument identifiers inside a function body, without forcing this
one to give up its whole-file reach to use it.
---------------------------------------------------------------------------