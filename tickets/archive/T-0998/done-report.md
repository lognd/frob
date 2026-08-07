## Done report

Moved the AFFECT001/002 idea (docs/modules/graph.md#affects) from
diff-time to scope-DECLARATION time so agents stop discovering
AFFECT001/COV002 reactively mid-ticket (the reactive scope-add churn
this drive hit repeatedly). Added a closure TRIPLE over a ticket's
declared scope: code<->docs (frob:doc/frob:describes edges), code<->
tests (frob:tests edges, added per the repo owner's mid-task
directive extension), and private-helper capture (build_call_graph
substrate). All three reuse existing traversal engines (affects()'s
own edge reads, closure()'s own call-graph substrate) rather than a
second traversal engine, per the ticket's own mandate.

Wired as a new WARN-severity SCOPE002 gate rule (frob.gates.
_scope002_violations, folded into the existing scope_gate stage
alongside SCOPE001) plus suggest-or-warn CLI output on `frob ticket
new`/`frob ticket scope` (frob.app.ticket_runner.
_scope_closure_warnings) so the feedback lands before a `frob check`
run is even needed.

Verified against two real recent ticket scopes:
- src/frob/graph/affects.py alone (single-file scope): SCOPE002
  correctly flagged every public symbol's missing docs/modules/
  graph.md doc-target and missing tests/test_graph_affects.py
  test-target -- exactly the kind of narrow single-file scope this
  drive's tickets tend to declare before widening reactively.
- src/frob/graph/callgraph.py alone: same doc/test gaps fired
  correctly; the private-helper direction ALSO fired but was noisy
  over the flat tests/ directory (filed as a follow-up ticket,
  T-1012, rather than fixed under this ticket's scope/
  effort budget -- WARN-only so non-blocking, but disclosed as a v1
  limitation).

FAIL/PASS fixture proof for the SCOPE002 new-gate-rule id (T-0756
acceptance policy): before this change, `frob check --only scope
--ticket <id>` never emitted SCOPE002 at all (the rule id did not
exist). After this change, running `frob check --only scope --ticket
<id> --json` against a real ticket scoped to `src/frob/graph/
callgraph.py` alone FAILS to stay clean -- it emits real SCOPE002
findings (e.g. "SCOPE002: <id> scope includes
src/frob/graph/callgraph.py::CallGraph whose frob:doc target
docs/modules/graph.md#call-graph lives in 'docs/modules/graph.md', not
in scope") through the production `frob check` invocation, not merely
a unit test calling `_scope002_violations` directly. Widening the same
ticket's scope to include the missing files via `frob ticket scope
<id> --add ...` then PASSES (SCOPE002 clears for the doc/test
directions) -- observed live in this session (see Evidence).

### Changed
```
 docs/modules/gates.md         |  52 +++++++++++++++
 docs/modules/graph.md         |  67 +++++++++++++++++++
 src/frob/app/ticket_runner.py |  67 +++++++++++++++++++
 src/frob/gates/__init__.py    | 119 ++++++++++++++++++++++++++++++++++
 src/frob/graph/__init__.py    |  15 ++++-
 src/frob/graph/affects.py     | 146 +++++++++++++++++++++++++++++++++++++++++-
 src/frob/graph/callgraph.py   |  91 ++++++++++++++++++++++++++
 tests/test_gates.py           |  74 +++++++++++++++++++++
 tests/test_graph.py           |  60 +++++++++++++++++
 tests/test_graph_affects.py   | 121 ++++++++++++++++++++++++++++++++++
 tickets.md                    |  92 +++++++++++++++++++++++++-
 11 files changed, 901 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_graph_affects.py::TestScopeDocCodeGaps::test_code_in_scope_doc_target_unscoped` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestScopePrivateHelperGaps::test_flags_scoped_caller_of_unscoped_private_helper` (pytest node id, verified passing when recorded)
- `tests/test_graph_affects.py::TestScopeDocCodeGaps::test_doc_in_scope_code_target_unscoped` (pytest node id, verified passing when recorded)
- `tests/test_graph_affects.py::TestScopeDocCodeGaps::test_clean_when_both_sides_in_scope` (pytest node id, verified passing when recorded)
- `tests/test_graph_affects.py::TestScopeTestGaps::test_code_in_scope_test_target_unscoped` (pytest node id, verified passing when recorded)
- `tests/test_graph_affects.py::TestScopeTestGaps::test_test_in_scope_code_target_unscoped` (pytest node id, verified passing when recorded)
- `tests/test_graph_affects.py::TestScopeTestGaps::test_clean_when_both_sides_in_scope` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestScopePrivateHelperGaps::test_only_used_by_scope_true_when_no_external_caller` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestScopePrivateHelperGaps::test_clean_when_callee_also_in_scope` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScope002ClosureGate::test_warns_on_unscoped_doc_target` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScope002ClosureGate::test_warns_on_unscoped_private_helper` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScope002ClosureGate::test_warns_on_unscoped_test_target` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScope002ClosureGate::test_silent_on_closed_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 2 error(s), 8061 warning(s), 325 waived
- error-findings: ARCH001@src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-ae6475a362d0f19b6/src/frob/graph/callgraph.py:695
