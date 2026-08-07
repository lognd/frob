## Done report

Fixed the three co-located findings in src/frob/gates/_debt_deprecated.py:

- ARCH001 (line 644, _depr005_violations 74/60 lines): extracted the
  per-edge violation-building body into a new private helper,
  _depr005_edge_violations, so _depr005_violations itself now only does
  the eligible-edge filter plus a thin dispatch loop.

- PERF003 (line 592, nested-loop-shaped equality comparison in
  _references_from_index): collapsed the two full sequential passes over
  `hits` into one pass that both records import-line references and
  buckets call-shaped candidates into a dict keyed by file, then a second
  pass iterates only `importing_files` and looks candidates up by that
  same key -- "index the inner collection by the compared key", exactly
  as the gate's own suggested fix says, instead of re-scanning the full
  hits list a second time.

- PERF008 (line 683, _build_deprecated_ref_index called inside the
  eligible-edge loop with loop-invariant args): the `if index is None`
  memoization guard was already limiting it to one real build, but that
  guard is invisible to PERF008's syntactic loop-invariant-call detector
  (call site is still lexically inside the loop body). Restructured
  _depr005_violations into two passes: a first pass filters edges down to
  those with an open ticket and a baseline entry (no index needed yet),
  and only if that eligible set is non-empty does the index get built --
  once, entirely outside any loop -- before a second loop hands each
  eligible edge to the new helper.

Verified behavior is unchanged: re-ran the file's own perf_rules check
directly (PERF003/PERF008 findings for this file are gone, the
pre-existing waived PERF004 is still the only perf finding), and re-ran
`frob check --only static --ticket T-1338` (the ARCH001 long-function
finding for _depr005_violations is gone; the pre-existing large-file and
abstraction-opportunity ARCH001 findings are untouched, out of this
ticket's scope). All 17 tests in
tests/unit/gates/test_deprecated_baseline.py and all 29 tests across
tests/test_gates.py::TestDebtGate/TestDeprecatedGate still pass.

Added one new regression test,
TestDepr005ViolationsGrowth.test_two_baselined_symbols_each_evaluated_independently,
covering two DIFFERENT baselined deprecated symbols evaluated in one
gate run -- protects the PERF008 restructuring specifically (the shared,
hoisted-once _DeprecatedRefIndex must still resolve each symbol's own
reference set correctly and independently).

Scope was widened by one file
(tests/unit/gates/test_deprecated_baseline.py) via `frob ticket scope
--add` to cover the new test.

No residue filed, no ticket needed -- the two out-of-scope ARCH001 findings already
present in this file (large-file, abstraction-opportunity) are
pre-existing, not co-located with this ticket's three named findings,
and not touched by this change.

### Changed
```
 tickets.md | 204 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 200 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_two_baselined_symbols_each_evaluated_independently` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_growth_beyond_baseline_fires_at_the_right_file_and_line` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_unrelated_same_name_call_in_non_importing_file_is_excluded` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_clean_debt_produces_no_violations` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeprecatedGate::test_clean_deprecated_produces_no_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 7 error(s), 417 warning(s), 686 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, ARCH001@src/frob/tickets/_land_finalize.py, COV001@design/frob.strata, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, RENDER001@src/frob/refactor/_cli.py, TICK003@tickets.md
