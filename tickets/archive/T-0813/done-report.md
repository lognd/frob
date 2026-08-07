## Done report

## Done report

Changed:
src/frob/graph/callgraph.py::_unresolved_exempt_names
src/frob/graph/callgraph.py::build_call_graph
src/frob/graph/callgraph.py::_resolve_edges
src/frob/gates/_protocol_summary.py::protocol_summary_gate
src/frob/gates/_protocol_summary.py::_package_files
src/frob/gates/_protocol_summary.py::_package_edges
src/frob/gates/__init__.py (registered "protocol_summary" gate name / PROTO001 rule id in _ALL_GATES, _build_jobs, _PROCESS_POOL_GATES, _CANONICAL_GATE_ORDER, _KNOWN_GATE_RULES, __all__)

Evidence:
tests/test_gates.py::TestProtocolSummaryGate::test_unresolved_callee_poisons_a_protocol_tagged_symbol
tests/test_gates.py::TestProtocolSummaryGate::test_clean_protocol_tagged_symbol_is_not_flagged
tests/test_gates.py::TestProtocolSummaryGate::test_untagged_symbol_with_unresolved_call_is_not_flagged
tests/test_gates.py::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing
tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_attribute_call_on_foreign_receiver_from_unresolved
tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_super_dunder_call_from_unresolved
tests/test_graph.py::TestCallGraph::test_build_call_graph_still_marks_unresolved_self_attribute_call

Wiring choice: gate-side integration (PROTO001, frob.gates._protocol_summary.protocol_summary_gate),
not a CLI subcommand -- src/frob/__main__.py is outside this ticket's scope globs, but
frob.gates.run_gates's dispatch tables live in src/frob/gates/__init__.py, which is in scope.
Registered as a real process-pool job so a plain `frob check` now runs a genuine repo scan:
build_call_graph(..., mark_unresolved=True) + compute_protocol_summaries over every package
containing a frob:requires/frob:transition-tagged symbol, flagging (WARN, waivable) any tagged
symbol whose summary comes back poisoned.

False-positive adjudication: filtered, not just documented. frob.graph.callgraph
._unresolved_exempt_names (wired through a new exempt_extractor parameter on
_resolve_edges/build_call_graph) exempts a call-token name from ever becoming UNRESOLVED_CALLEE
when EVERY occurrence of it in a function body is an attribute call (<expr>.name() on a receiver
other than self) -- kills both the obj._method(...) and super().__init__(...) false-positive
shapes the T-0809 reviewer named. self._foo(...) is deliberately NOT exempted (verified by a
dedicated negative test) since that is exactly the intra-package private-helper call this graph
exists to catch.

Real-repo smoke test: TestProtocolSummaryGate.test_real_repo_scan_runs_end_to_end_without_crashing
runs protocol_summary_gate against this repo's OWN live GraphSnapshot (not a fixture) -- 0
violations today (no production symbol is yet protocol-tagged), proving the wiring completes
without the IndexError/crash class T-0809's own Done report disclosed as the reason
mark_unresolved defaulted to False.

Filed: none

Gates: frob check --ticket T-0813 clean (0 errors, protocol_summary gate ran in ~0.7s alongside
every other gate; verified twice after the scope-add + pre-work re-sweep). frob test --base main
exit 0. ruff check clean on all touched files.

Deviations: scope extended twice via `frob ticket scope --add` (both reasoned, recorded in the
ticket's audit trail): docs/modules/gates.md + docs/modules/graph.md (companion documentation for
the new PROTO001 rule and false-positive disposition), then tests/test_gates.py +
tests/test_graph.py (file-level, not tests/**, to avoid colliding with any other ticket's lease on
the broader tests/ tree) once COV002 flagged the new/touched test symbols as unaccounted-for.

### Changed
```
 docs/modules/gates.md               |  46 +++++++++
 docs/modules/graph.md               |  11 +++
 src/frob/gates/__init__.py          |  27 +++++-
 src/frob/gates/_protocol_summary.py | 179 ++++++++++++++++++++++++++++++++++++
 src/frob/graph/callgraph.py         |  65 ++++++++++++-
 tests/test_gates.py                 |  91 ++++++++++++++++++
 tests/test_graph.py                 |  54 +++++++++++
 7 files changed, 471 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestProtocolSummaryGate::test_unresolved_callee_poisons_a_protocol_tagged_symbol` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolSummaryGate::test_clean_protocol_tagged_symbol_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolSummaryGate::test_untagged_symbol_with_unresolved_call_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_attribute_call_on_foreign_receiver_from_unresolved` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_super_dunder_call_from_unresolved` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_still_marks_unresolved_self_attribute_call` (pytest node id, verified passing when recorded)
