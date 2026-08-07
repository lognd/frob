## Done report

Carrier for T-1433's mitigation branch (the ticket itself stays open
pending a clean full-suite run). Delivered: the three known full-repo
self-scan tests now share one xdist_group ("frob_self_scan_heavy") via
pytest_collection_modifyitems in tests/conftest.py, so --dist=loadgroup
serializes them onto one worker -- the well-evidenced OOM trigger was
several of these landing on different coverage-instrumented workers
concurrently. The remainder of THIS ticket (capture direct kernel OOM
evidence; broaden the allowlist to the other full-repo scan tests
outside T-1433's scope) stays open here.

### Changed
```
 tests/conftest.py                     |  46 ++++++
 tests/unit/test_conftest_stackdump.py |  40 +++++
 tickets.md                            | 300 ++++++++++++++++++++++------------
 3 files changed, 286 insertions(+), 100 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 423 warning(s), 742 waived
- error-findings: WIRE001@tests/conftest.py
