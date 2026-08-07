## Done report

Changed: src/frob/gates/_models.py::TestPolicy,
src/frob/testing/_models.py::TestRunReport,
src/frob/testing/_runners.py::TestingError -- each gains
`__test__: bool = False` matching the TestCase precedent in
process/parsers/common.py. Coordinator-applied direct user request
(exact locations user-supplied); swept via frob ticket start before close.

Evidence: tests/test_testing.py::TestSelect::test_direct_hit and
tests/test_gates.py::TestCoverageGate::test_waive002_honors_loaded_policy_rule_ids
(both suites collect warning-free and pass; verified
`pytest --collect-only` emits zero PytestCollectionWarning across
tests/test_gates.py + tests/test_testing.py).

Filed: none. Gates: ruff format stable on all three files.
