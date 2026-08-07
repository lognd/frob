---
id: T-0998
title: 'scope generation: doc-edge + code-edge closure validation (no code without
  its docs in scope and vice versa) + private-helper capture'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- src/frob/graph/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph_affects.py::TestScopeDocCodeGaps::test_code_in_scope_doc_target_unscoped
- tests/test_graph.py::TestScopePrivateHelperGaps::test_flags_scoped_caller_of_unscoped_private_helper
- tests/test_graph_affects.py::TestScopeDocCodeGaps::test_doc_in_scope_code_target_unscoped
- tests/test_graph_affects.py::TestScopeDocCodeGaps::test_clean_when_both_sides_in_scope
- tests/test_graph_affects.py::TestScopeTestGaps::test_code_in_scope_test_target_unscoped
- tests/test_graph_affects.py::TestScopeTestGaps::test_test_in_scope_code_target_unscoped
- tests/test_graph_affects.py::TestScopeTestGaps::test_clean_when_both_sides_in_scope
- tests/test_graph.py::TestScopePrivateHelperGaps::test_only_used_by_scope_true_when_no_external_caller
- tests/test_graph.py::TestScopePrivateHelperGaps::test_clean_when_callee_also_in_scope
- tests/test_gates.py::TestScope002ClosureGate::test_warns_on_unscoped_doc_target
- tests/test_gates.py::TestScope002ClosureGate::test_warns_on_unscoped_private_helper
- tests/test_gates.py::TestScope002ClosureGate::test_warns_on_unscoped_test_target
- tests/test_gates.py::TestScope002ClosureGate::test_silent_on_closed_scope
designated_repro_test: null
acceptance:
- text: given a ticket scoped to a code file with a frob:doc edge to an unscoped doc,
    when the scope is declared or validated, then the missing doc counterpart is surfaced
    (suggestion or warning) naming the exact file
  evidence:
  - tests/test_graph_affects.py::TestScopeDocCodeGaps::test_code_in_scope_doc_target_unscoped
- text: given scoped code calling a private helper defined outside the scope, when
    scope validation runs, then the helper is flagged as probable under-capture with
    its definition site
  evidence:
  - tests/test_graph.py::TestScopePrivateHelperGaps::test_flags_scoped_caller_of_unscoped_private_helper
threat: null
component: null
---
User directive 2026-07-27: when generating or validating a ticket scope, run the doc-edge and code-edge closures over the declared files so scope encapsulation provably grabs BOTH sides -- a scope containing code files whose frob:doc/affects-closure doc targets are absent is under-captured (and vice versa: docs scoped without their code counterparts). This moves the AFFECT001 idea from diff-time to scope-declaration time: frob ticket new/scope should compute the closure and either auto-suggest the missing counterpart files or refuse/warn, so agents stop discovering AFFECT001/COV002 mid-ticket and scope-adding reactively (a dozen occurrences this drive). The same closure math discourages over-broad scopes: a scope whose closure balloons is visibly over-broad at declaration time, complementing the existing over-broad-glob heuristics. Additionally check private-helper usage: if scoped code calls underscore-private helpers defined OUTSIDE the scope, flag probable under-capture (you will likely touch them); private helpers used ONLY by scoped code get auto-suggested into scope. Deliverables: a scope-closure computation on the obligation graph (reuse the affects()/doc-edge machinery, do not build a second traversal), wiring into frob ticket new/scope (suggest-or-warn mode first; a SCOPE-family gate rule for enforcement second, WARN at turn-on per the promotion playbook), tests for all three directions (code-missing-docs, docs-missing-code, private-helper leakage), and docs.