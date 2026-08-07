## Done report

Verified each of the three 0.0%-branch flagged symbols against the T-1279
stale-stamp precedent before writing any new code.

- _core.py::core_available: exercised behaviorally by
  TestResolveCallEdgesNative.test_core_available_true_dispatches_to_native_spy_and_false_does_not,
  which pins BOTH the True (native import succeeds) and False (ImportError)
  branches observably via a spy, killing the exact mutants a 0.0% stamp
  implies were never exercised.
- _core.py::resolve_call_edges_native: exercised by
  test_native_matches_python_fallback_on_a_real_package (golden-parity test
  against a real package's callgraph) and the synthetic-edge-case sibling --
  both call it directly and assert its return value.
- _waive_presets.py::resolve_preset: live caller at
  src/frob/graph/dsl.py::_attrs_verb_error_waive (frob:waive preset= resolution);
  exercised directly by TestWaivePresets.test_resolve_preset_known_name and
  test_resolve_preset_unknown_name_is_none, both asserting real return values
  for the known/unknown branches.

All tests were run scoped and pass. No new tests were needed -- this is a
stale coverage-stamp finding, matching the T-1289/T-1291/T-1292/T-1308
precedent. No dead code found; all three symbols have live callers/entry
points.

### Changed
```
 tickets.md | 83 +++++++++++++++++++++++++++++++++++++++++++++++++++++++-------
 1 file changed, 74 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestResolveCallEdgesNative::test_native_matches_python_fallback_on_a_real_package` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestResolveCallEdgesNative::test_core_available_true_dispatches_to_native_spy_and_false_does_not` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaivePresets::test_resolve_preset_known_name` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaivePresets::test_resolve_preset_unknown_name_is_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 5 error(s), 608 warning(s), 679 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design
