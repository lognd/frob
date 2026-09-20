## Done report

The win32 test-portability drain (T-3076) needs the COMPLETE failing-node-id list from one CI run, but pytest_sessionfinish caps the SUITE-RESULT-FAILED list at 50 and collapses the rest into 'and N more' (run 33839329030 emitted 52 + 'and 146 more' of ~198 failures). Added FROB_TEST_SUITE_RESULT_MAX_NODE_IDS to override the cap (via _suite_result_max_node_ids()), set to 500 in all three CI Test steps so the whole list is emitted; the default 50 is unchanged for local runs. Pinned the default in the existing 'and N more' bound test (else the CI-raised cap defeats it) and added test_sessionfinish_node_id_cap_env_override as evidence. WIRE001 waived (the helper is called from the pytest_sessionfinish hook, untraced by the callgraph). DEPR006 pre-existing/out-of-scope.

### Changed
```
 .github/workflows/ci.yml              | 12 ++++++++++++
 tests/conftest.py                     | 29 +++++++++++++++++++++++++++-
 tests/unit/test_conftest_stackdump.py | 36 ++++++++++++++++++++++++++++++++++-
 tickets/T-3755/ticket.md              |  5 ++++-
 4 files changed, 79 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_node_id_cap_env_override` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_caps_failing_node_ids_with_and_n_more` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 4320 warning(s), 920 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json, PRE001@tickets/T-3755
