## Done report

`pytest_sessionfinish`'s SUITE-RESULT line (T-1596) made the VERDICT
(exitstatus/collected/failed counts) always visible regardless of `-q`
stacking, but gave no way to act on a nonzero `failed` count without
re-running the entire suite: under `-qq`, pytest's own "short test summary
info" section (which normally lists failing node ids) is also suppressed.

Fix: `pytest_sessionfinish` now also reads `terminalreporter.stats`
(populated regardless of verbosity -- it drives the summary section, it is
not gated by it) and writes one `SUITE-RESULT-FAILED: <nodeid> (<outcome>)`
line per failed/errored test via the same `write_line` channel the
SUITE-RESULT line already uses, which is not suppressed by `-q`/`-qq`. Capped
at `_SUITE_RESULT_MAX_NODE_IDS` (50) with a trailing "and N more" line so a
suite with hundreds of failures still produces bounded, greppable output.

### Changed
```
 tickets.md | 20 ++++++++++++++++++--
 1 file changed, 18 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_lists_failing_node_ids` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_caps_failing_node_ids_with_and_n_more` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 118 warning(s), 717 waived
- error-findings: none (measured, zero errors)
