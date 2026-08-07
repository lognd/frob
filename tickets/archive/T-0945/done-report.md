## Done report

Two frob:tests edges from T-0926 could not resolve against the obligation graph: one used pytest's :: class-method separator where the graph keys on dotted Class.method (the exact T-0940 class), the other named a module-level test that does not exist. Both repointed at real dotted node ids; DRIFT is back to zero.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_conftest_parse_reset.py::TestConftestParseReset::test_b_does_not_see_a_leaked_partial_parse` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4507 warning(s), 351 waived
- error-findings: none (measured, zero errors)
