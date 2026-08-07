## Done report

COV006's Violation now carries symref=edge.src (the offending frob:tests
edge's own test symref), mirroring TEST005/T-0148's existing precedent for
symbol-exact waiver matching. _match_waiver's symref-is-not-None branch
already existed and required no changes -- only COV006's Violation
construction (_cov006_edge_violation, src/frob/gates/__init__.py) needed
to start populating it.

Blast-radius check (grep for every `frob:waive COV006` in the tree, 4
existed before this change, one more added by this change's own tests):
- tests/test_graph.py:764 and tests/unit/strata/test_selfconform.py:921,969
  -- each already sat directly above the one test method it was meant to
  cover; unaffected, still match after the symref change.
- tests/test_gates.py:5830 (TestProcessPoolGates.
  test_process_job_runs_in_a_separate_process) was the one genuine
  file-blanket case: its own reason text said outright "COV006 waivers
  match at file granularity ... so one waiver here covers both" --
  covering a SECOND, unrelated finding on
  TestGateOrderSetEquality.test_canonical_gate_order_matches_all_gates
  "below" in the same file purely because both were in the same file.
  This is the exact over-waiving this ticket describes. Split into two
  waivers, each bound to its own test, same reasoning per site
  (T-0525 is the T-0516 calibration ticket the old comment referenced).
  A third sibling, test_all_gates_is_subset_of_canonical_order, had NO
  waiver before and genuinely needed its own (same never-calls-the-
  bound-symbol shape) -- added. A fourth sibling,
  test_canonical_order_names_no_nonexistent_gate, does NOT need one: its
  frob:tests directive lives inside its docstring text, not a `#`
  comment, so DSL parsing never creates a TESTS edge for it in the first
  place -- verified empirically (a waiver placed there fired WAIVE004,
  "0 matching findings"; removed rather than left as a dead waiver).

Added two regression tests directly exercising the new symref plumbing:
tests/test_gates.py::TestCoverageGate::
test_cov006_violation_carries_edge_src_as_symref (asserts the emitted
Violation.symref equals the edge's src) and
::test_cov006_waiver_does_not_blanket_suppress_the_whole_file (two
independent unsound frob:tests edges in one file; a waiver bound to only
one must not touch the other -- kept/waived split via _apply_waivers).
Mutation check: reverting symref=edge.src back to symref=None in
_cov006_edge_violation makes both new tests fail
(`uv run pytest tests/test_gates.py::TestCoverageGate::
test_cov006_violation_carries_edge_src_as_symref
tests/test_gates.py::TestCoverageGate::
test_cov006_waiver_does_not_blanket_suppress_the_whole_file` -> 2 failed
under the mutant, 2 passed after reverting), confirming they kill the
predicate this ticket changes, not just execute it.

Measured: `uv run pytest tests/test_gates.py -p no:cacheprovider -q` ->
all pass (348 collected in this file, none newly failing).
`frob check --ticket T-0525 --only gates-fast` -> 0 errors, 931 warnings,
160 waived (clean); no new unwaived COV006 finding anywhere in the tree,
confirmed by grepping the full gates-fast output for "COV006" outside a
"[waived: ...]" annotation (only the one now-removed dead waiver's
WAIVE004 showed up mid-iteration, gone after removing it).

No cuts: the ticket's own ask (give COV006 a symref so `_match_waiver`
stops falling back to file-scope) is implemented as scoped, plus the
concrete over-waiving instance it names (tests/test_gates.py) is repaired
in the same change.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_cov006_violation_carries_edge_src_as_symref` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov006_waiver_does_not_blanket_suppress_the_whole_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
