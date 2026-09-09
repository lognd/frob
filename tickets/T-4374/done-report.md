## Done report

T-4374: bare pytest argv in the worker-crash-retry test was unresolvable on a macOS xdist worker (FileNotFoundError). Fix is test-only: use sys.executable -m pytest, matching the sibling test in the same file and the T-4369 precedent. Verified locally; production argv is already resolved via project_tool_argv and unaffected.

### Changed
```
 tests/test_coverage.py   | 24 ++++++++++++++++++++++--
 tickets/T-4374/ticket.md |  2 ++
 2 files changed, 24 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestWorkerCrashRetryRealSubprocessRecoversFromAddopts::test_real_pytest_subprocess_recovers_and_produces_coverage_xml` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 4777 warning(s), 955 waived
- error-findings: COV003@tickets/T-4364/ticket.md, COV007@src/frob/tickets/_mutation_evidence.py
