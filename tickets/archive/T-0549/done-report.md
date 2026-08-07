## Done report

B7 fix: `_case_count` (src/frob/gates/__init__.py) now accepts an optional
`root: Path` param. When given, a python edge with more than one collected
parametrize variant is capped to exactly 1 case unless the underlying test
function's source actually contains an assertion-shaped construct
(`ast.Assert`, `ast.Raise`, or a call whose name contains "raises"/"assert"),
via new helpers `_has_assertion_evidence`/`_function_asserts`/`_call_repr`.
All three real call sites (`_test001_002_one`, `_test003_check_package`,
`_test009`) now pass `Path(snapshot.root)`; the direct-unit-test default
(`root=None`) skips the check entirely, preserving T-0307's original
per-case counting for callers with no filesystem root (or synthetic node
ids naming files that do not exist on disk).

Counterexample: a `@pytest.mark.parametrize('x', [1,2,3])` test whose body
calls `helper(x)` but asserts nothing used to clear `min_unit_cases=3`
(effective=3); now it is capped to 1 and TEST002 correctly fires
(`test_test002_noop_parametrize_does_not_inflate_case_count`). A real
assertion-bearing parametrized test is unaffected
(`test_test002_parametrized_test_counts_each_case`, pre-existing, still
green) and still counts every collected variant
(`test_case_count_root_aware_caps_noop_parametrize`'s second half).

No public API signature outside `_case_count`/`coverage_gate` changed;
`_case_count` itself is private so no REL001 stamp needed for this ticket.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestTestGate::test_test002_noop_parametrize_does_not_inflate_case_count` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_case_count_root_none_skips_assertion_check` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_case_count_root_aware_caps_noop_parametrize` (pytest node id, verified passing when recorded)
