---
id: T-0422
title: 'dead-symbol gate: an unreferenced private symbol is dead code (symbol-level
  analog of REF001; catches written-but-never-wired)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0407
tier: ticket
sprint: null
scope:
- src/frob/gates/
- src/frob/graph/
- src/frob/gates/__init__.py
- tests/test_gates.py
- tests/test_graph.py
- src/frob/tickets/__init__.py
- tests/test_tickets_scope_mutation.py
- pyproject.toml
- CHANGELOG.md
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: additive-only registration lines (import + frozenset entry + canonical-order
    entry + process-job entry) wiring the new dead_symbol_gate module into frob check,
    per this wave's gates/** ownership split
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_gates.py
  reason: DEAD001 gate regression tests
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_graph.py
  reason: build_reference_graph regression test (T-0422's new callgraph.py addition)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: re-tag COV002-flagged symbols with T-0422 now that T-0561 (their own ticket)
    is closed -- same precedent as T-0543's Done report
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_tickets_scope_mutation.py
  reason: same re-tag reason
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 requires a version bump for T-0422's new public callgraph.build_reference_graph
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 version-bump artifact
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 version-bump artifact
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: mechanical lockfile refresh alongside version bump
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_called_private_helper_is_not_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_dunder_method_is_not_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_test_function_is_not_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_tests_edge_target_is_not_flagged
- tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry
designated_repro_test: null
threat: null
component: null
---
Root cause of the arch double-run (T-0418): _arch_violations_from_suggestions was WRITTEN to prevent the duplication but NEVER WIRED -- zero callers, dead code, and no gate flagged it. Generalize: a private symbol (leading-underscore function/class/method) with NO in-repo references (not called, not re-exported, not a test target, not a registered dispatch entry, not a dunder/protocol method) is DEAD -- either wire it or delete it. This is the SYMBOL-level analog of the anti-orphan FILE gate (REF001/T-0396): a file with no inbound refs is an orphan file; a private symbol with no inbound refs is an orphan symbol. Reuse the graph the orphan-file/callgraph work already builds (references/uses edges). Fail-tier WARN (advisory-but-tracked, like REF). Careful about FALSE POSITIVES: exempt dunders, protocol/ABC methods, pytest test_ functions, registered-via-decorator handlers, and anything reached only dynamically WITH an explicit frob:used-by-style declaration (verified). Acceptance: a written-but-unwired private function like _arch_violations_from_suggestions is flagged; a genuinely-used private helper is not; a decorator-registered handler is not. This stops the entire "intended code silently rots unwired" class.