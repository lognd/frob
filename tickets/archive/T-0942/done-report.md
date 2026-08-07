## Done report

PARSE002 fired an unwaivable ERROR on tests/fixtures/lang/broken.py: the fixture is graph-excluded, and waivers only bind through graph-ingested edges, so the gate's own recommended in-file waive could never attach (the same excluded-path class T-0897 fixed for PII010/RENDER001/SEC-CVE). _partial_parse_violations now consults frob.excludes and skips graph-excluded paths, where the missing-symbols claim is vacuous anyway; non-excluded partial parses still fire. Regression test proves excluded-silent plus non-excluded-fires in one run.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestParseFailureGate::test_partial_parse_in_graph_excluded_path_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestParseFailureGate::test_partial_parse_is_an_error_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 4514 warning(s), 351 waived
- error-findings: none (measured, zero errors)
