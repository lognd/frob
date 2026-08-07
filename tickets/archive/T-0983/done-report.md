## Done report

Fixed the id-conversion bug at the boundary where `frob test`'s stability-
capture pass hands node ids to pytest.

Root cause: `report.selected["python"]` holds the graph's dotted symref
form (`path::Class.method`, the `frob:tests` directive convention) --
the same form `run_selected`'s primary pytest invocation converts via
`_runners._to_node_id` (`path::Class.method` -> `path::Class::method`)
before spawning pytest. `_track_python_stability_and_gate`
(src/frob/app/test_runner.py) read `report.selected["python"]` directly
and passed the dotted form straight to `capture_python_outcomes`, which
spawns `uv run pytest <ids>` verbatim -- pytest does not recognize a dot
between class and method as node-id syntax, so it collected 0 tests
(exit 5) and `capture_python_outcomes`/`record_outcomes` silently no-oped
every single `frob test` run.

Fix: convert `report.selected["python"]`'s dotted symrefs through the
same `_to_node_id` helper `run_selected` already uses for the primary
run, before handing them to `capture_python_outcomes`. This confirms
the resolver-convention split from today's other T-0940 lesson runs the
other direction for this caller: the obligation GRAPH keys stay dotted
(`Class.method`), but this caller talks to pytest directly, so it needs
the `::`-joined form, not the graph's own key form.

Downstream effect of the bug, checked per the ticket's ask: since
`capture_python_outcomes` always returned an empty dict, `record_outcomes`
was always called with `{}`, so `.frob/test-stability.json` never
accumulated real pass/fail history for any node id. `evaluate_gate`
(src/frob/testing/_stability.py) reads `quarantined_node_ids(entries)`
from that same history -- with `entries` permanently empty, a
quarantined-and-genuinely-flaky test's node id was NEVER found in
`quarantined_node_ids`, so `evaluate_gate` could never promote a
quarantined failure back to green. Net effect: the quarantine-promotion
half of the flake gate has been silently inert since T-0635 shipped it --
quarantined flaky tests have still been failing the build the whole
time, exactly as if quarantine did not exist. No strict-xfail mechanism
exists in this codebase (grepped; the only hit was a docs/audits
prose mention), so there is no separate strict-xfail logic being masked
beyond this quarantine-gate inertness.

Changed:
- src/frob/app/test_runner.py::_track_python_stability_and_gate -- convert
  `report.selected["python"]`'s dotted symrefs to real pytest node ids via
  `frob.testing._runners._to_node_id` before calling
  `capture_python_outcomes`, matching the conversion `run_selected` already
  applies to the primary run.
- tests/test_app.py::TestStabilityGate.test_dotted_symref_converted_to_pytest_node_id
  -- new regression test: asserts `capture_python_outcomes` is invoked with
  the `::`-joined node id ("tests/t.py::A::b") when selection holds the
  dotted symref ("tests/t.py::A.b"), proving the boundary conversion fires.

Evidence:
tests/test_app.py::TestStabilityGate::test_dotted_symref_converted_to_pytest_node_id
(collected and passing, `uv run pytest tests/test_app.py -q`: 14 passed).

Gates: `uv run frob check --ticket T-0983` clean after extending scope
(+tests/test_app.py, reason recorded via `frob ticket scope`) and
re-sweeping (`frob ticket sweep T-0983`) -- 0 errors across ty/ruff/all
gate groups (gates-fast, gates-native, gates-security, lint, static).

Filed: none -- no out-of-scope issue found.

### Changed
(no changed files detected)

### Evidence
- `tests/test_app.py::TestStabilityGate::test_dotted_symref_converted_to_pytest_node_id` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4857 warning(s), 304 waived
- error-findings: none (measured, zero errors)
