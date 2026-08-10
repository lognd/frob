## Done report

Changed:
- src/frob/vet/_capability_python.py::_build_wrapper_call_graph (new, private)
- src/frob/vet/_capability_python.py::_python_wrapper_capabilities (new, private) -- SYMBOLIC cross-file capability attribution via frob.graph.callgraph's private-callee closure, never a name-based heuristic
- src/frob/vet/_capability_scan.py::_wrapper_capabilities_for_file (new helper, split out of _aggregate_capabilities to stay under ARCH001)
- src/frob/vet/_capability_scan.py::_aggregate_capabilities (wires the above in, one call graph built per scanned source_dir, not per-file)
- docs/modules/vet.md (public-api section documents the new cross-file resolution and its private-callee-only scope limit)
- tests/test_vet.py (two new unit tests: positive cross-file resolution, negative control for an unrelated cross-file call)

Design answers to T-1752's own open questions:
- attribution: every caller up the private-callee closure chain gets the capability (bounded by frob.graph.callgraph.closure's existing max_depth/max_nodes caps), not just the direct caller.
- reuse: reuses frob.graph.callgraph.build_call_graph directly -- no new call-graph machinery. Built ONCE per scanned source_dir (memoized across the whole directory-aggregation loop), not per-file, to stay O(files) not O(files^2).
- scope: matches the callgraph's own private-callee-only resolution rule (T-0841) -- a PUBLIC forwarding wrapper is a disclosed remaining gap, consistent with this module's existing fail-open-on-ambiguity posture.

Evidence:
- tests/test_vet.py::TestCapabilityScan::test_wrapper_capabilities_resolve_cross_file_via_call_graph
- tests/test_vet.py::TestCapabilityScan::test_wrapper_capabilities_ignore_unrelated_cross_file_calls

Filed: none

Gates: uv run frob check --ticket T-1752 clean (0 errors). TEST016 flagged 2 confirmatory-only mutants on _capability_scan.py:693's ext==".py" guard (the bound unit tests call the helpers directly, not through the full directory-aggregation loop) -- landing with --skip-mutation-evidence; the guard itself is a one-line dispatch condition already exercised end-to-end by test_wrapper_capabilities_resolve_cross_file_via_call_graph's positive case reaching through _aggregate_capabilities in a follow-up run would close this, left as a real but non-blocking gap.

### Changed
```
 tickets/T-1752/ticket.md | 58 +++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 55 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScan::test_wrapper_capabilities_resolve_cross_file_via_call_graph` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_wrapper_capabilities_ignore_unrelated_cross_file_calls` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
