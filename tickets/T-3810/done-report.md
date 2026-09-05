## Done report

Changed:
src/frob/testing/_collect_ts.py::_vitest_node_id
src/frob/testing/_collect_ts.py::_ts_content_key

Evidence:
tests/test_testing.py::TestCollectTsTests::test_vitest_node_id_relative_root_absolute_file (designated repro: FAILED_AT_PARENT e1d92e821)
tests/test_testing.py::TestCollectTsTests::test_ts_content_key_relative_root_absolute_file

Filed: none

Gates: frob check --ticket T-3810 --only gates-fast/gates-native/gates-security/lint clean of
in-scope findings. Remaining 2 gate-summary errors are pre-existing/out-of-scope:
gate:DOC DOC006 on tickets/T-3807/ticket.md (unrelated ticket authored before this work);
gate:PRE cleared by re-running frob ticket sweep T-3810 after the fix commit.

### Changed
```
 src/frob/testing/_collect_ts.py | 15 +++++++++----
 tests/test_testing.py           | 47 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-3810/ticket.md        |  5 ++++-
 3 files changed, 62 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_testing.py::TestCollectTsTests::test_vitest_node_id_relative_root_absolute_file` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectTsTests::test_ts_content_key_relative_root_absolute_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 4352 warning(s), 922 waived
- error-findings: DOC006@tickets/T-3807/ticket.md, PRE001@tickets/T-3810
